from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from openmedia.sources import ErrorCategory, SourceAdapterError
from openmedia.sources.ytdlp import merge_streams


def tool(name: str) -> str:
    path = shutil.which(name)
    assert path is not None, f"{name} is required for stream-copy validation; install FFmpeg"
    return path


def make_sources(root: Path, container: str) -> tuple[Path, Path, str, str]:
    ffmpeg = tool("ffmpeg")
    if container == "mp4":
        video, audio = root / "video.mp4", root / "audio.m4a"
        video_codec, audio_codec = "h264", "aac"
        video_args = ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
        audio_args = ["-c:a", "aac"]
    else:
        video, audio = root / "video.webm", root / "audio.webm"
        video_codec, audio_codec = "vp9", "opus"
        video_args = ["-c:v", "libvpx-vp9", "-deadline", "realtime"]
        audio_args = ["-c:a", "libopus"]
    subprocess.run(
        [ffmpeg, "-nostdin", "-v", "error", "-f", "lavfi", "-i", "color=size=32x32:rate=5:duration=1", *video_args, "-an", str(video)],
        check=True,
    )
    subprocess.run(
        [ffmpeg, "-nostdin", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=1", *audio_args, "-vn", str(audio)],
        check=True,
    )
    return video, audio, video_codec, audio_codec


@pytest.mark.parametrize("container", ["mp4", "webm"])
def test_stream_copy_preserves_exactly_selected_codecs(tmp_path: Path, container: str) -> None:
    video, audio, video_codec, audio_codec = make_sources(tmp_path, container)
    output = tmp_path / f"merged.{container}"
    result = merge_streams(
        video,
        audio,
        output,
        owned_directory=tmp_path,
        extension=container,
        video_codec=video_codec,
        audio_codec=audio_codec,
        output_limit=1_000_000,
        workspace_limit=2_000_000,
    )
    assert result == output.stat().st_size
    probe = subprocess.run(
        [tool("ffprobe"), "-v", "error", "-show_entries", "stream=codec_type,codec_name", "-of", "json", str(output)],
        check=True,
        text=True,
        capture_output=True,
    )
    streams = json.loads(probe.stdout)["streams"]
    assert [(item["codec_type"], item["codec_name"]) for item in streams] == [
        ("video", video_codec),
        ("audio", audio_codec),
    ]


def test_merge_refuses_incompatible_or_network_input_and_caps_output(tmp_path: Path) -> None:
    video, audio, _, _ = make_sources(tmp_path, "mp4")
    with pytest.raises(SourceAdapterError) as incompatible:
        merge_streams(video, audio, tmp_path / "bad.webm", owned_directory=tmp_path, extension="webm", video_codec="h264", audio_codec="aac", output_limit=1_000_000, workspace_limit=2_000_000)
    assert incompatible.value.category is ErrorCategory.FORMAT_UNAVAILABLE
    with pytest.raises(SourceAdapterError):
        merge_streams(Path("https://example.com/video.mp4"), audio, tmp_path / "url.mp4", owned_directory=tmp_path, extension="mp4", video_codec="h264", audio_codec="aac", output_limit=1_000_000, workspace_limit=2_000_000)
    refused = subprocess.run(
        [tool("ffmpeg"), "-nostdin", "-v", "error", "-protocol_whitelist", "file", "-i", "https://127.0.0.1/nope", "-f", "null", "-"],
        text=True,
        capture_output=True,
    )
    assert refused.returncode != 0
    assert "not on whitelist 'file'" in refused.stderr
    with pytest.raises(SourceAdapterError) as too_large:
        merge_streams(video, audio, tmp_path / "small.mp4", owned_directory=tmp_path, extension="mp4", video_codec="h264", audio_codec="aac", output_limit=10, workspace_limit=2_000_000)
    assert too_large.value.category is ErrorCategory.TOO_LARGE


def test_merge_enforces_peak_workspace_limit(tmp_path: Path) -> None:
    video, audio, _, _ = make_sources(tmp_path, "mp4")
    (tmp_path / "filler.bin").write_bytes(b"x" * 1_000_000)
    with pytest.raises(SourceAdapterError) as caught:
        merge_streams(video, audio, tmp_path / "peak.mp4", owned_directory=tmp_path, extension="mp4", video_codec="h264", audio_codec="aac", output_limit=1_000_000, workspace_limit=1_000_000)
    assert caught.value.category is ErrorCategory.STORAGE_EXHAUSTED


def test_actual_stream_validation_rejects_changed_dimensions_and_audio(tmp_path):
    from openmedia.models import FormatOption
    from openmedia.sources.ytdlp import _validate_selected_streams
    from dataclasses import replace
    video, _, _, _ = make_sources(tmp_path, "mp4")
    option = FormatOption(0, "yt_dlp", "v", "video", "mp4", "video/mp4", height=32,
        includes_audio=False, transport_ref={"vcodec": "avc1"})
    _validate_selected_streams(video, option)
    for changed in (replace(option, height=720), replace(option, includes_audio=True)):
        with pytest.raises(SourceAdapterError):
            _validate_selected_streams(video, changed)


def test_expired_url_refreshes_once_through_real_download_validation(tmp_path, monkeypatch):
    import io, time
    from types import SimpleNamespace
    from dataclasses import replace
    from openmedia.models import FormatOption, MediaMetadata
    from openmedia.sources import SourceRouter, InspectResult, DownloadInput
    from openmedia.sources.ytdlp import YtDlpAdapter
    from openmedia.network import GuardedHTTPTransport
    video, _, _, _ = make_sources(tmp_path, "mp4")
    body = video.read_bytes()
    option = FormatOption(0, "yt_dlp", "v", "video", "mp4", "video/mp4", height=32, includes_audio=False,
        transport_ref={"url": "https://cdn.invalid/expired", "vcodec": "avc1", "acodec": "none"})
    metadata = MediaMetadata("youtube", "https://youtu.be/abcDEF12345", "abcDEF12345")
    refreshed = replace(option, transport_ref={**option.transport_ref, "url": "https://cdn.invalid/fresh"})
    adapter = YtDlpAdapter()
    inspections = []
    def inspect(*args, **kwargs):
        inspections.append(True)
        return InspectResult(metadata, (refreshed,))
    monkeypatch.setattr(adapter, "inspect", inspect)
    transport = GuardedHTTPTransport()
    urls = []
    def opened(url, **kwargs):
        urls.append(url)
        response = SimpleNamespace(status=403 if len(urls) == 1 else 200,
            getheader=lambda name: str(len(body)), read=io.BytesIO(body).read)
        return SimpleNamespace(close=lambda: None), response, url
    monkeypatch.setattr(transport, "_open", opened)
    rate = SimpleNamespace(acquire=lambda *args, **kwargs: None)
    result = SourceRouter(ytdlp=adapter).download(DownloadInput("a" * 32, metadata, option, tmp_path,
        time.monotonic()+10, 1_000_000, 2_000_000), transport=transport, rate_control=rate)
    assert result.path.read_bytes() == body
    assert len(inspections) == 1 and len(urls) == 2 and urls[-1].endswith("fresh")


# --- T007: post-download codec check for unknown-codec MP4 video (research R1, analysis C1) ---


def make_clip(root: Path, name: str, video_args: list[str] | None, audio_args: list[str] | None) -> Path:
    """Encode one tiny local clip from lavfi sources with real ffmpeg."""
    output = root / name
    inputs: list[str] = []
    maps: list[str] = []
    codecs: list[str] = []
    if video_args is not None:
        inputs += ["-f", "lavfi", "-i", "color=size=32x32:rate=5:duration=1"]
        maps += ["-map", f"{len(maps) // 2}:v"]
        codecs += video_args
    if audio_args is not None:
        inputs += ["-f", "lavfi", "-i", "sine=frequency=440:duration=1"]
        maps += ["-map", f"{len(maps) // 2}:a"]
        codecs += audio_args
    subprocess.run(
        [tool("ffmpeg"), "-nostdin", "-v", "error", *inputs, *maps, *codecs, "-shortest", str(output)],
        check=True,
    )
    return output


H264 = ["-c:v", "libx264", "-pix_fmt", "yuv420p"]
MPEG4 = ["-c:v", "mpeg4"]
VP9 = ["-c:v", "libvpx-vp9", "-deadline", "realtime"]
AAC = ["-c:a", "aac"]
AC3 = ["-c:a", "ac3"]


def unknown_codec_option(*, includes_audio: bool, extension: str = "mp4", **reference: str):
    from openmedia.models import FormatOption

    mime = "video/mp4" if extension == "mp4" else f"video/{extension}"
    return FormatOption(
        0,
        "yt_dlp",
        "progressive",
        "video",
        extension,
        mime,
        height=32,
        includes_audio=includes_audio,
        transport_ref={"url": "https://cdn.invalid/progressive", **reference},
    )


@pytest.mark.parametrize("includes_audio", [False, True])
def test_unknown_codec_mp4_with_h264_and_aac_passes(tmp_path: Path, includes_audio: bool) -> None:
    from openmedia.sources.ytdlp import _validate_selected_streams

    clip = make_clip(tmp_path, "clip.mp4", H264, AAC if includes_audio else None)
    _validate_selected_streams(clip, unknown_codec_option(includes_audio=includes_audio))


@pytest.mark.parametrize(
    ("video_args", "audio_args", "includes_audio"),
    [
        pytest.param(MPEG4, None, False, id="mpeg4-video-no-sound"),
        pytest.param(MPEG4, AAC, True, id="mpeg4-video-aac-audio"),
        pytest.param(VP9, None, False, id="vp9-video-no-sound"),
        pytest.param(H264, AC3, True, id="h264-video-ac3-audio"),
    ],
)
def test_unknown_codec_mp4_rejects_non_phone_playable_streams(
    tmp_path: Path, video_args: list[str], audio_args: list[str] | None, includes_audio: bool
) -> None:
    from openmedia.sources.ytdlp import _validate_selected_streams

    clip = make_clip(tmp_path, "clip.mp4", video_args, audio_args)
    with pytest.raises(SourceAdapterError) as caught:
        _validate_selected_streams(clip, unknown_codec_option(includes_audio=includes_audio))
    assert caught.value.category is ErrorCategory.FORMAT_UNAVAILABLE
    assert caught.value.stage == "download"


def test_unknown_codec_mp4_rejection_deletes_downloaded_file(tmp_path: Path) -> None:
    import time
    from types import SimpleNamespace

    from openmedia.models import MediaMetadata
    from openmedia.sources import DownloadInput
    from openmedia.sources.ytdlp import YtDlpAdapter

    source = tmp_path / "source"
    source.mkdir()
    body = make_clip(source, "clip.mp4", MPEG4, None).read_bytes()
    work = tmp_path / "work"
    work.mkdir()
    option = unknown_codec_option(includes_audio=False)
    metadata = MediaMetadata("linkedin", "https://www.linkedin.com/posts/example", "example")

    def download(url, destination, **kwargs):
        Path(destination).write_bytes(body)
        return len(body)

    transport = SimpleNamespace(download=download)
    rate = SimpleNamespace(acquire=lambda *args, **kwargs: None)
    request = DownloadInput("a" * 32, metadata, option, work, time.monotonic() + 10, 1_000_000, 2_000_000)
    with pytest.raises(SourceAdapterError) as caught:
        YtDlpAdapter().download(request, transport=transport, rate_control=rate)
    assert caught.value.category is ErrorCategory.FORMAT_UNAVAILABLE
    assert caught.value.stage == "download"
    assert not (work / "selected.mp4").exists()
    assert list(work.iterdir()) == []


def test_known_codec_options_keep_existing_validation(tmp_path: Path) -> None:
    from openmedia.sources.ytdlp import _validate_selected_streams

    h264 = make_clip(tmp_path, "h264.mp4", H264, None)
    mpeg4 = make_clip(tmp_path, "mpeg4.mp4", MPEG4, None)
    vp9 = make_clip(tmp_path, "vp9.webm", VP9, None)
    # Known codec that matches the file: still accepted.
    _validate_selected_streams(h264, unknown_codec_option(includes_audio=False, vcodec="avc1.64000c"))
    # Known codec that the file contradicts: still rejected as a changed codec.
    with pytest.raises(SourceAdapterError) as caught:
        _validate_selected_streams(mpeg4, unknown_codec_option(includes_audio=False, vcodec="avc1.64000c"))
    assert caught.value.category is ErrorCategory.FORMAT_UNAVAILABLE
    # The new rule is scoped to MP4: an unknown-codec WebM video is unaffected.
    _validate_selected_streams(vp9, unknown_codec_option(includes_audio=False, extension="webm"))


@pytest.mark.parametrize("includes_audio", [False, True])
def test_validation_returns_the_measured_frame_and_duration(tmp_path: Path, includes_audio: bool) -> None:
    from openmedia.sources.ytdlp import _validate_selected_streams

    clip = make_clip(tmp_path, "clip.mp4", H264, AAC if includes_audio else None)
    option = unknown_codec_option(includes_audio=includes_audio)
    width, height, duration = _validate_selected_streams(clip, option)
    assert (width, height) == (32, 32)
    assert duration == pytest.approx(1.0, abs=0.2)


def test_download_result_carries_measured_video_metadata(tmp_path: Path) -> None:
    import time
    from dataclasses import replace
    from types import SimpleNamespace

    from openmedia.models import MediaMetadata
    from openmedia.sources import DownloadInput
    from openmedia.sources.ytdlp import YtDlpAdapter

    source = tmp_path / "source"
    source.mkdir()
    body = make_clip(source, "clip.mp4", H264, AAC).read_bytes()
    work = tmp_path / "work"
    work.mkdir()
    # Instagram progressive formats list no codec, dimensions, or duration.
    option = replace(unknown_codec_option(includes_audio=True), height=None)
    metadata = MediaMetadata("instagram", "https://www.instagram.com/reel/example/", "example")

    def download(url, destination, **kwargs):
        Path(destination).write_bytes(body)
        return len(body)

    transport = SimpleNamespace(download=download)
    rate = SimpleNamespace(acquire=lambda *args, **kwargs: None)
    request = DownloadInput("a" * 32, metadata, option, work, time.monotonic() + 10, 1_000_000, 2_000_000)
    result = YtDlpAdapter().download(request, transport=transport, rate_control=rate)
    assert (result.width, result.height) == (32, 32)
    assert result.duration_seconds == pytest.approx(1.0, abs=0.2)

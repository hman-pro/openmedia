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

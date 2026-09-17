"""Exact-output refresh through the real adapters and the real guarded transport.

Only the socket layer (`GuardedHTTPTransport._open`) is scripted; status classification,
file writing, artifact cleanup, and media validation are the production code paths.
"""

from __future__ import annotations

import io
import subprocess
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from openmedia.models import FormatOption, MediaMetadata
from openmedia.network import GuardedHTTPTransport
from openmedia.sources import (
    DownloadInput,
    ErrorCategory,
    InspectResult,
    SourceAdapterError,
    SourceRouter,
)
from openmedia.sources.instagram import InstagramImageAdapter
from openmedia.sources.linkedin import LinkedInImageAdapter
from openmedia.sources.ytdlp import YtDlpAdapter

from tests.integration.test_merge import make_sources, tool


RATE = SimpleNamespace(acquire=lambda *args, **kwargs: None)
ARTIFACTS = ("selected.mp4", "selected.jpg", "component-video", "component-audio")


class Script:
    """Replay (status, body) responses and record what each open could see on disk."""

    def __init__(self, monkeypatch, work: Path, responses: list[tuple[int, bytes]]) -> None:
        self.transport = GuardedHTTPTransport()
        self.work = work
        self.responses = list(responses)
        self.urls: list[str] = []
        self.visible: list[list[str]] = []
        self.error_bodies_read = 0
        monkeypatch.setattr(self.transport, "_open", self.open)

    def open(self, url, **kwargs):
        self.urls.append(url)
        self.visible.append([name for name in ARTIFACTS if (self.work / name).exists()])
        status, body = self.responses.pop(0)
        stream = io.BytesIO(body)

        def read(size=-1):
            if status >= 300:
                self.error_bodies_read += 1
            return stream.read(size)

        response = SimpleNamespace(status=status, getheader=lambda name: str(len(body)), read=read)
        return SimpleNamespace(close=lambda: None), response, url


def refreshing(monkeypatch, adapter, metadata, option) -> list[bool]:
    inspections: list[bool] = []

    def inspect(*args, **kwargs):
        inspections.append(True)
        return InspectResult(metadata, (option,))

    monkeypatch.setattr(adapter, "inspect", inspect)
    return inspections


def download_input(work: Path, metadata: MediaMetadata, option: FormatOption) -> DownloadInput:
    return DownloadInput("a" * 32, metadata, option, work, time.monotonic() + 30, 1_000_000, 4_000_000)


YOUTUBE = MediaMetadata("youtube", "https://youtu.be/abcDEF12345", "abcDEF12345")


def merged_option(prefix: str = "old", **reference: str) -> FormatOption:
    return FormatOption(0, "yt_dlp", "137+140", "video", "mp4", "video/mp4", width=32, height=32,
        includes_audio=True, transport_ref={"video_url": f"https://cdn.invalid/{prefix}-v",
            "audio_url": f"https://cdn.invalid/{prefix}-a", "vcodec": "avc1.64001f", "acodec": "mp4a.40.2",
            **reference})


def single_option(name: str = "old") -> FormatOption:
    return FormatOption(0, "yt_dlp", "18", "video", "mp4", "video/mp4", width=32, height=32,
        includes_audio=False, transport_ref={"url": f"https://cdn.invalid/{name}", "vcodec": "avc1", "acodec": "none"})


@pytest.mark.parametrize("expired_status", [403, 410])
def test_expired_component_refreshes_once_after_removing_attempt_artifacts(tmp_path, monkeypatch, expired_status):
    sources = tmp_path / "sources"; sources.mkdir()
    work = tmp_path / "work"; work.mkdir()
    video, audio, _, _ = make_sources(sources, "mp4")
    script = Script(monkeypatch, work, [(200, video.read_bytes()), (expired_status, b"<html>expired</html>"),
        (200, video.read_bytes()), (200, audio.read_bytes())])
    adapter = YtDlpAdapter()
    inspections = refreshing(monkeypatch, adapter, YOUTUBE, merged_option("new"))

    result = SourceRouter(ytdlp=adapter).download(download_input(work, YOUTUBE, merged_option()),
        transport=script.transport, rate_control=RATE)

    assert len(inspections) == 1
    assert [url.rsplit("/", 1)[1] for url in script.urls] == ["old-v", "old-a", "new-v", "new-a"]
    assert script.visible[2] == [], "the retry must start from a workspace without failed-attempt files"
    assert script.error_bodies_read == 0
    probe = subprocess.run([tool("ffprobe"), "-v", "error", "-show_entries", "stream=codec_name",
        "-of", "csv=p=0", str(result.path)], check=True, capture_output=True, text=True)
    assert sorted(probe.stdout.split()) == ["aac", "h264"]
    assert sorted(path.name for path in work.iterdir()) == ["selected.mp4"]


@pytest.mark.parametrize("status", [404, 500, 503])
def test_non_expiry_media_failures_are_terminal_without_refresh_or_error_body(tmp_path, monkeypatch, status):
    script = Script(monkeypatch, tmp_path, [(status, b"<html>upstream error page</html>")])
    adapter = YtDlpAdapter()
    inspections = refreshing(monkeypatch, adapter, YOUTUBE, single_option("new"))

    with pytest.raises(SourceAdapterError) as caught:
        SourceRouter(ytdlp=adapter).download(download_input(tmp_path, YOUTUBE, single_option()),
            transport=script.transport, rate_control=RATE)

    assert caught.value.category is ErrorCategory.UNAVAILABLE
    assert inspections == [] and len(script.urls) == 1
    assert script.error_bodies_read == 0 and list(tmp_path.iterdir()) == []


def test_second_expiry_after_the_single_refresh_is_terminal(tmp_path, monkeypatch):
    script = Script(monkeypatch, tmp_path, [(403, b""), (403, b"")])
    adapter = YtDlpAdapter()
    inspections = refreshing(monkeypatch, adapter, YOUTUBE, single_option("new"))

    with pytest.raises(SourceAdapterError) as caught:
        SourceRouter(ytdlp=adapter).download(download_input(tmp_path, YOUTUBE, single_option()),
            transport=script.transport, rate_control=RATE)

    assert caught.value.category is ErrorCategory.UNAVAILABLE
    assert len(inspections) == 1 and len(script.urls) == 2
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize("changed", [{"acodec": "opus"}, {"vcodec": "vp09.00.10.08"}])
def test_refresh_rejects_a_changed_merged_component_codec(tmp_path, monkeypatch, changed):
    script = Script(monkeypatch, tmp_path, [(403, b"")])
    adapter = YtDlpAdapter()
    inspections = refreshing(monkeypatch, adapter, YOUTUBE, merged_option("new", **changed))

    with pytest.raises(SourceAdapterError) as caught:
        SourceRouter(ytdlp=adapter).download(download_input(tmp_path, YOUTUBE, merged_option()),
            transport=script.transport, rate_control=RATE)

    assert caught.value.category is ErrorCategory.FORMAT_UNAVAILABLE
    assert len(inspections) == 1 and len(script.urls) == 1, "a changed choice is never downloaded"


def test_media_failing_real_stream_validation_is_removed_and_not_refreshed(tmp_path, monkeypatch):
    fake = b"\x00\x00\x00\x18ftypisom" + b"not really an mp4" * 64
    script = Script(monkeypatch, tmp_path, [(200, fake)])
    adapter = YtDlpAdapter()
    inspections = refreshing(monkeypatch, adapter, YOUTUBE, single_option("new"))

    with pytest.raises(SourceAdapterError):
        SourceRouter(ytdlp=adapter).download(download_input(tmp_path, YOUTUBE, single_option()),
            transport=script.transport, rate_control=RATE)

    assert inspections == [] and len(script.urls) == 1
    assert list(tmp_path.iterdir()) == []


def make_jpeg(root: Path) -> bytes:
    image = root / "source.jpg"
    subprocess.run([tool("ffmpeg"), "-nostdin", "-v", "error", "-f", "lavfi", "-i", "color=size=32x32:duration=1",
        "-frames:v", "1", str(image)], check=True)
    body = image.read_bytes()
    image.unlink()
    return body


IMAGE_CASES = {
    "instagram": (InstagramImageAdapter, "instagram_image",
        MediaMetadata("instagram", "https://www.instagram.com/p/gbStjFIaB4/", "gbStjFIaB4")),
    "linkedin": (LinkedInImageAdapter, "linkedin_image",
        MediaMetadata("linkedin", "https://www.linkedin.com/feed/update/urn:li:activity:7505650038253965312/",
            "7505650038253965312")),
}


class NoVideo:
    """LinkedIn refresh inspects with yt-dlp first; an image post falls through to the image adapter."""

    def inspect(self, request, **kwargs):
        raise SourceAdapterError(ErrorCategory.NO_FORMATS, stage="inspection")


def image_router(platform: str, adapter) -> SourceRouter:
    return SourceRouter(**{platform: adapter, "ytdlp": NoVideo()})


def image_option(adapter_name: str, name: str = "old") -> FormatOption:
    return FormatOption(0, adapter_name, "image-0", "image", "jpg", "image/jpeg",
        transport_ref={"url": f"https://cdn.invalid/{name}"})


@pytest.mark.parametrize("platform", sorted(IMAGE_CASES))
def test_image_adapters_refresh_an_expired_url_and_deliver_the_exact_bytes(tmp_path, monkeypatch, platform):
    adapter_class, adapter_name, metadata = IMAGE_CASES[platform]
    sources = tmp_path / "sources"; sources.mkdir()
    work = tmp_path / "work"; work.mkdir()
    body = make_jpeg(sources)
    script = Script(monkeypatch, work, [(403, b"<html>expired</html>"), (200, body)])
    adapter = adapter_class()
    inspections = refreshing(monkeypatch, adapter, metadata, image_option(adapter_name, "new"))

    result = image_router(platform, adapter).download(
        download_input(work, metadata, image_option(adapter_name)), transport=script.transport, rate_control=RATE)

    assert len(inspections) == 1 and script.urls[-1].endswith("/new")
    assert result.path.read_bytes() == body and script.visible[1] == []


@pytest.mark.parametrize("platform", sorted(IMAGE_CASES))
def test_image_with_a_valid_prefix_but_undecodable_content_is_rejected(tmp_path, monkeypatch, platform):
    adapter_class, adapter_name, metadata = IMAGE_CASES[platform]
    script = Script(monkeypatch, tmp_path, [(200, b"\xff\xd8\xff\xe0" + b"<html>not an image</html>" * 40)])
    adapter = adapter_class()
    inspections = refreshing(monkeypatch, adapter, metadata, image_option(adapter_name, "new"))

    with pytest.raises(SourceAdapterError) as caught:
        image_router(platform, adapter).download(
            download_input(tmp_path, metadata, image_option(adapter_name)), transport=script.transport, rate_control=RATE)

    assert caught.value.category is ErrorCategory.INVALID_SOURCE_RESPONSE
    assert inspections == [] and list(tmp_path.iterdir()) == []

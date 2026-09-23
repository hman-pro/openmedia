from __future__ import annotations

from pathlib import Path
import socket

import pytest

from openmedia.models import FormatOption, MediaMetadata
from openmedia.sources import (
    EXPIRED_URL,
    DownloadInput,
    InspectInput,
    InspectResult,
    TransportResponse,
    SourceAdapterError,
    ErrorCategory,
    SourceRouter,
    fetch_optional_thumbnail,
)
from openmedia.sources.instagram import InstagramImageAdapter
from openmedia.sources.linkedin import LinkedInImageAdapter
from openmedia.sources.ytdlp import YtDlpAdapter
from openmedia.network import GuardedHTTPTransport, PublicEndpointPolicy, UnsafeDestination


class Rate:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def acquire(self, platform, request_class, *, deadline):
        self.calls.append((platform, request_class))
        return 0

    def limited(self, platform, request_class, *, retry_after):
        self.calls.append((platform, "limited"))


class Transport:
    def __init__(self, html: str = "") -> None:
        self.html = html
        self.calls: list[tuple[str, int | None]] = []

    def fetch(self, url, *, limit, **kwargs):
        self.calls.append(("fetch", limit))
        body = self.html.encode() if self.html else b"\xff\xd8\xffthumbnail"
        content_type = "text/html" if self.html else "image/jpeg"
        return TransportResponse(url, 200, {"content-type": content_type}, body)

    def head(self, url, **kwargs):
        self.calls.append(("head", None))
        return TransportResponse(url, 200, {"content-type": "image/jpeg", "content-length": "100"}, b"")

    def download(self, url, destination, **kwargs):
        self.calls.append(("download", kwargs["output_limit"]))
        body = b"\x00\x00\x00\x18ftypisomfixture"
        if str(destination).endswith(".jpg"):
            body = b"\xff\xd8\xff\xe0fixture"
        Path(destination).write_bytes(body)
        return len(body)


def inspect_input(tmp_path: Path, url: str) -> InspectInput:
    return InspectInput(
        source_url=url,
        request_id="0123456789abcdef0123456789abcdef",
        work_directory=tmp_path,
        deadline=100,
    )


def test_image_adapters_use_only_supplied_guarded_transport(tmp_path: Path) -> None:
    instagram_transport = Transport()
    post = {
        "shortcode": "gbStjFIaB4",
        "typename": "GraphImage",
        "mediacount": 1,
        "is_video": False,
        "url": "https://media.example.invalid/image",
    }
    instagram = InstagramImageAdapter(post_loader=lambda _: post)
    instagram.inspect(
        inspect_input(tmp_path, "https://www.instagram.com/p/gbStjFIaB4/"),
        transport=instagram_transport,
        rate_control=Rate(),
    )
    assert instagram_transport.calls == [("head", None)]

    html = (Path(__file__).parents[1] / "fixtures/linkedin/linkedin-image-single.html").read_text()
    linkedin_transport = Transport(html)
    linkedin = LinkedInImageAdapter()
    linkedin.inspect(
        inspect_input(tmp_path, "https://www.linkedin.com/posts/example_activity-7505650038253965312-x"),
        transport=linkedin_transport,
        rate_control=Rate(),
    )
    assert linkedin_transport.calls == [("fetch", 8 * 1024 * 1024), ("head", None)]


def test_ytdlp_exact_download_and_thumbnail_use_guard_limits(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("openmedia.sources.ytdlp._validate_selected_streams", lambda *args: None)
    transport = Transport()
    metadata = MediaMetadata(
        platform="youtube",
        canonical_url="https://www.youtube.com/watch?v=abcDEF12345",
        media_id="abcDEF12345",
        thumbnail_url="https://thumb.example.invalid/x.jpg",
    )
    option = FormatOption(
        option_id=0,
        adapter="yt_dlp",
        source_format_id="18",
        media_type="video",
        extension="mp4",
        mime_type="video/mp4",
        includes_audio=True,
        transport_ref={"url": "https://media.example.invalid/video", "headers": {}},
    )
    result = YtDlpAdapter().download(
        DownloadInput(
            request_id="0123456789abcdef0123456789abcdef",
            metadata=metadata,
            option=option,
            work_directory=tmp_path,
            deadline=100,
            output_limit=50_000_000,
            workspace_limit=128 * 1024 * 1024,
        ),
        transport=transport,
        rate_control=Rate(),
    )
    assert result.source_format_id == "18"
    inspected = InspectResult(metadata, (option,))
    with_thumbnail = fetch_optional_thumbnail(
        inspected,
        inspect_input(tmp_path, metadata.canonical_url),
        transport=transport,
    )
    assert with_thumbnail.thumbnail_path is not None
    assert ("fetch", 1024 * 1024) in transport.calls


def test_single_refresh_keeps_exact_selected_identity_and_quality(tmp_path: Path) -> None:
    metadata = MediaMetadata(
        platform="youtube",
        canonical_url="https://www.youtube.com/watch?v=abcDEF12345",
        media_id="abcDEF12345",
    )
    original = FormatOption(
        option_id=0,
        adapter="yt_dlp",
        source_format_id="137+140",
        media_type="video",
        extension="mp4",
        mime_type="video/mp4",
        height=1080,
        includes_audio=True,
        transport_ref={"video_url": "https://old.invalid/v", "audio_url": "https://old.invalid/a"},
    )

    class Adapter:
        def __init__(self, changed=False):
            self.downloads = 0
            self.changed = changed

        def inspect(self, request, **kwargs):
            refreshed = FormatOption(
                option_id=0,
                adapter="yt_dlp",
                source_format_id="137+140",
                media_type="video",
                extension="mp4",
                mime_type="video/mp4",
                height=720 if self.changed else 1080,
                includes_audio=True,
                transport_ref={"video_url": "https://new.invalid/v", "audio_url": "https://new.invalid/a"},
            )
            return InspectResult(metadata, (refreshed,))

        def download(self, request, **kwargs):
            self.downloads += 1
            if self.downloads == 1:
                raise SourceAdapterError(ErrorCategory.UNAVAILABLE, stage="download", detail=EXPIRED_URL)
            path = tmp_path / "refreshed.mp4"
            path.write_bytes(b"bytes")
            return __import__("openmedia.sources", fromlist=["DownloadResult"]).DownloadResult(
                path, 5, metadata.media_id, request.option.source_format_id, "video", "mp4", "video/mp4"
            )

    request = DownloadInput(
        request_id="0123456789abcdef0123456789abcdef",
        metadata=metadata,
        option=original,
        work_directory=tmp_path,
        deadline=100,
        output_limit=50_000_000,
        workspace_limit=128 * 1024 * 1024,
    )
    adapter = Adapter()
    router = SourceRouter(ytdlp=adapter, instagram=adapter, linkedin=adapter)
    assert router.download(request, transport=Transport(), rate_control=Rate()).actual_bytes == 5
    assert adapter.downloads == 2

    changed = Adapter(changed=True)
    router = SourceRouter(ytdlp=changed, instagram=changed, linkedin=changed)
    with pytest.raises(SourceAdapterError) as caught:
        router.download(request, transport=Transport(), rate_control=Rate())
    assert caught.value.category is ErrorCategory.FORMAT_UNAVAILABLE
    assert changed.downloads == 1


@pytest.mark.parametrize(
    ("adapter", "platform", "media_type", "extension", "mime_type"),
    [
        (YtDlpAdapter(), "youtube", "video", "mp4", "video/mp4"),
        (InstagramImageAdapter(post_loader=lambda _: {}), "instagram", "image", "jpg", "image/jpeg"),
        (LinkedInImageAdapter(), "linkedin", "image", "jpg", "image/jpeg"),
    ],
)
def test_every_adapter_download_uses_the_public_destination_guard(
    tmp_path: Path,
    adapter: object,
    platform: str,
    media_type: str,
    extension: str,
    mime_type: str,
) -> None:
    resolved: list[tuple[str, int]] = []

    def private_resolver(host: str, port: int, **_kwargs: object):
        resolved.append((host, port))
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("127.0.0.1", port))]

    transport = GuardedHTTPTransport(policy=PublicEndpointPolicy(resolver=private_resolver))
    metadata = MediaMetadata(
        platform=platform,
        canonical_url="https://source.example.invalid/item",
        media_id="item",
        media_kind=media_type,
    )
    option = FormatOption(
        option_id=0,
        adapter=getattr(adapter, "name"),
        source_format_id="source-id",
        media_type=media_type,
        extension=extension,
        mime_type=mime_type,
        includes_audio=True if media_type == "video" else None,
        transport_ref={"url": "https://127.0.0.1/private"},
    )
    request = DownloadInput(
        request_id="0123456789abcdef0123456789abcdef",
        metadata=metadata,
        option=option,
        work_directory=tmp_path,
        deadline=100,
        output_limit=50_000_000,
        workspace_limit=128 * 1024 * 1024,
    )

    with pytest.raises((UnsafeDestination, SourceAdapterError)):
        adapter.download(request, transport=transport, rate_control=Rate())
    assert resolved == [("127.0.0.1", 443)]
    assert list(tmp_path.iterdir()) == []


def test_adapter_limits_and_fixed_output_paths_are_forwarded(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("openmedia.sources.ytdlp._validate_selected_streams", lambda *args: None)
    class RecordingTransport(Transport):
        def __init__(self) -> None:
            super().__init__()
            self.download_call: tuple[Path, int, int] | None = None

        def download(self, url, destination, **kwargs):
            self.download_call = (
                Path(destination),
                kwargs["output_limit"],
                kwargs["workspace_limit"],
            )
            return super().download(url, destination, **kwargs)

    transport = RecordingTransport()
    metadata = MediaMetadata(
        platform="youtube",
        canonical_url="https://www.youtube.com/watch?v=abcDEF12345",
        media_id="abcDEF12345",
        thumbnail_url="https://thumb.example.invalid/x.jpg",
    )
    option = FormatOption(
        option_id=0,
        adapter="yt_dlp",
        source_format_id="18",
        media_type="video",
        extension="mp4",
        mime_type="video/mp4",
        includes_audio=True,
        transport_ref={"url": "https://media.example.invalid/video", "headers": {}},
    )
    request = DownloadInput(
        request_id="0123456789abcdef0123456789abcdef",
        metadata=metadata,
        option=option,
        work_directory=tmp_path,
        deadline=100,
        output_limit=50_000_000,
        workspace_limit=128 * 1024 * 1024,
    )
    YtDlpAdapter().download(request, transport=transport, rate_control=Rate())
    assert transport.download_call == (
        tmp_path / "selected.mp4",
        50_000_000,
        128 * 1024 * 1024,
    )

    inspected = InspectResult(metadata, (option,))
    fetch_optional_thumbnail(
        inspected,
        inspect_input(tmp_path, metadata.canonical_url),
        transport=transport,
    )
    assert ("fetch", 1024 * 1024) in transport.calls


def test_adapter_forwards_range_bytes_for_each_merge_component(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr("openmedia.sources.ytdlp._validate_selected_streams", lambda *args: None)
    monkeypatch.setattr("openmedia.sources.ytdlp.merge_streams", lambda video, audio, destination, **kwargs: destination.write_bytes(b"merged") or 6)
    class RecordingTransport(Transport):
        def __init__(self) -> None:
            super().__init__()
            self.ranges: list[tuple[str, int | None]] = []

        def download(self, url, destination, **kwargs):
            self.ranges.append((Path(destination).name, kwargs.get("range_bytes")))
            return super().download(url, destination, **kwargs)

    transport = RecordingTransport()
    metadata = MediaMetadata(platform="youtube", canonical_url="https://www.youtube.com/watch?v=abcDEF12345",
        media_id="abcDEF12345")
    option = FormatOption(option_id=0, adapter="yt_dlp", source_format_id="137+140", media_type="video",
        extension="mp4", mime_type="video/mp4", includes_audio=True,
        transport_ref={"video_url": "https://media.example.invalid/v", "audio_url": "https://media.example.invalid/a",
            "video_headers": {}, "audio_headers": {}, "vcodec": "avc1", "acodec": "mp4a",
            "video_range_bytes": 10_485_760, "audio_range_bytes": None})
    request = DownloadInput(request_id="0123456789abcdef0123456789abcdef", metadata=metadata, option=option,
        work_directory=tmp_path, deadline=100, output_limit=50_000_000, workspace_limit=128 * 1024 * 1024)
    YtDlpAdapter().download(request, transport=transport, rate_control=Rate())
    assert transport.ranges == [("component-video", 10_485_760), ("component-audio", None)]

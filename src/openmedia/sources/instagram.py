"""Instagram single-image normalization and native-byte validation."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any

from openmedia.models import FormatOption, MediaKind, MediaMetadata, SizeKind
from openmedia.sources import (
    DownloadInput,
    DownloadResult,
    ErrorCategory,
    GuardedTransport,
    InspectInput,
    InspectResult,
    RateController,
    SourceAdapterError,
    recognize_source_url,
    validate_image_file,
)


_IMAGE_TYPES = {
    "image/jpeg": ("jpg", "image/jpeg"),
    "image/webp": ("webp", "image/webp"),
}


def _optional_text(value: object) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def detect_image_format(content_type: str | None, prefix: bytes) -> tuple[str, str]:
    """Require the declared type and downloaded signature to agree."""
    normalized = (content_type or "").split(";", 1)[0].strip().lower()
    declared = _IMAGE_TYPES.get(normalized)
    detected: tuple[str, str] | None = None
    if prefix.startswith(b"\xff\xd8\xff"):
        detected = _IMAGE_TYPES["image/jpeg"]
    elif len(prefix) >= 12 and prefix.startswith(b"RIFF") and prefix[8:12] == b"WEBP":
        detected = _IMAGE_TYPES["image/webp"]
    if declared is None or detected is None or declared != detected:
        raise SourceAdapterError(ErrorCategory.INVALID_SOURCE_RESPONSE, stage="download")
    return detected


def normalize_post(
    post: Mapping[str, Any],
    *,
    content_type: str,
    content_length: int | None,
) -> InspectResult:
    """Normalize an anonymous Instaloader GraphImage after a headers-only probe."""
    typename = post.get("typename")
    media_count = post.get("mediacount", 1)
    if typename == "GraphSidecar" or not isinstance(media_count, int) or media_count != 1:
        raise SourceAdapterError(ErrorCategory.UNSUPPORTED_COLLECTION, stage="inspection")
    if typename != "GraphImage" or post.get("is_video") is True:
        raise SourceAdapterError(ErrorCategory.INVALID_SOURCE_RESPONSE, stage="inspection")
    shortcode = _optional_text(post.get("shortcode"))
    image_url = _optional_text(post.get("url"))
    if shortcode is None or image_url is None:
        raise SourceAdapterError(ErrorCategory.INVALID_SOURCE_RESPONSE, stage="inspection")
    normalized_type = content_type.split(";", 1)[0].strip().lower()
    image_format = _IMAGE_TYPES.get(normalized_type)
    if image_format is None:
        raise SourceAdapterError(ErrorCategory.INVALID_SOURCE_RESPONSE, stage="inspection")
    if content_length is not None and content_length < 0:
        raise SourceAdapterError(ErrorCategory.INVALID_SOURCE_RESPONSE, stage="inspection")
    extension, mime_type = image_format
    metadata = MediaMetadata(
        platform="instagram",
        canonical_url=f"https://www.instagram.com/p/{shortcode}/",
        media_id=shortcode,
        title_or_caption=_optional_text(post.get("caption")),
        creator=_optional_text(post.get("owner_username")),
        thumbnail_url=_optional_text(post.get("thumbnail_url")),
        media_kind=MediaKind.IMAGE,
    )
    option = FormatOption(
        option_id=0,
        adapter="instagram_image",
        source_format_id=f"image:{shortcode}",
        media_type="image",
        extension=extension,
        mime_type=mime_type,
        size_bytes=content_length,
        size_kind=SizeKind.EXACT if content_length is not None else SizeKind.UNKNOWN,
        transport_ref={"url": image_url},
    )
    return InspectResult(metadata=metadata, options=(option,))


def post_to_mapping(post: Any) -> dict[str, Any]:
    """Extract only the fields the adapter contract permits from an Instaloader Post."""
    return {
        "shortcode": post.shortcode,
        "typename": post.typename,
        "mediacount": post.mediacount,
        "is_video": post.is_video,
        "caption": post.caption,
        "owner_username": post.owner_username,
        "url": post.url,
        # Instaloader's display URL is the primary image. A preview is optional and must be
        # independently supplied; never pretend the primary image is a thumbnail.
        "thumbnail_url": None,
    }


class InstagramImageAdapter:
    name = "instagram_image"

    def __init__(self, *, post_loader: Any | None = None) -> None:
        self._post_loader = post_loader

    def _load(self, shortcode: str, transport: GuardedTransport, request=None, rate_control=None) -> Mapping[str, Any]:
        if self._post_loader is not None:
            loaded = self._post_loader(shortcode)
            if not isinstance(loaded, Mapping):
                loaded = post_to_mapping(loaded)
            return loaded
        try:
            import instaloader

            from openmedia.sources.http import MetadataHTTP
            client = MetadataHTTP(transport, rate_control, request, "instagram")
            loader = instaloader.Instaloader(
                download_pictures=False,
                download_videos=False,
                download_video_thumbnails=False,
                save_metadata=False,
                compress_json=False,
                quiet=True,
                # One guarded request per worker: the parent paces Instagram, so the library's
                # random post-request sleep and its own retries only burn the 60s deadline.
                sleep=False,
                max_connection_attempts=1,
            )
            with client.requests():
                post = instaloader.Post.from_shortcode(loader.context, shortcode)
                return post_to_mapping(post)
        except SourceAdapterError:
            raise
        except Exception as exc:
            raise SourceAdapterError(ErrorCategory.UNAVAILABLE, stage="inspection") from exc

    def inspect(
        self,
        request: InspectInput,
        *,
        transport: GuardedTransport,
        rate_control: RateController,
    ) -> InspectResult:
        route = recognize_source_url(request.source_url)
        if route.platform != "instagram":
            raise SourceAdapterError(ErrorCategory.UNSUPPORTED_URL, stage="inspection")
        rate_control.acquire("instagram", "metadata", deadline=request.deadline)
        post = self._load(route.media_id, transport, request, rate_control)
        # A HEAD probe establishes the CDN-selected native representation without fetching
        # the primary image body during inspection.
        try:
            response = transport.head(str(post["url"]), deadline=request.deadline)
        except Exception as exc:
            raise SourceAdapterError(ErrorCategory.UNAVAILABLE, stage="inspection") from exc
        if response.status == 429:
            retry = response.headers.get("retry-after")
            retry_after = float(retry) if retry and retry.isdigit() else None
            rate_control.limited("instagram", "metadata", retry_after=retry_after)
            raise SourceAdapterError(
                ErrorCategory.RATE_LIMITED,
                stage="inspection",
                retry_after=retry_after,
            )
        if not 200 <= response.status < 300:
            raise SourceAdapterError(ErrorCategory.UNAVAILABLE, stage="inspection")
        raw_length = response.headers.get("content-length")
        try:
            length = int(raw_length) if raw_length is not None else None
        except ValueError as exc:
            raise SourceAdapterError(ErrorCategory.INVALID_SOURCE_RESPONSE, stage="inspection") from exc
        result = normalize_post(
            post,
            content_type=response.headers.get("content-type", ""),
            content_length=length,
        )
        if result.metadata.media_id != route.media_id:
            raise SourceAdapterError(ErrorCategory.INVALID_SOURCE_RESPONSE, stage="inspection")
        return result

    def download(
        self,
        request: DownloadInput,
        *,
        transport: GuardedTransport,
        rate_control: RateController,
    ) -> DownloadResult:
        option = request.option
        reference = option.transport_ref
        if not isinstance(reference, Mapping) or not isinstance(reference.get("url"), str):
            raise SourceAdapterError(ErrorCategory.FORMAT_UNAVAILABLE, stage="download")
        rate_control.acquire("instagram", "media", deadline=request.deadline)
        destination = request.work_directory / f"selected.{option.extension}"
        try:
            actual = transport.download(
                reference["url"],
                destination,
                output_limit=request.output_limit,
                workspace_limit=request.workspace_limit,
                deadline=request.deadline,
            )
        except Exception as exc:
            if isinstance(exc, (SourceAdapterError, OSError)):
                raise
            from openmedia.network import ResponseTooLarge
            if isinstance(exc, ResponseTooLarge):
                raise SourceAdapterError(ErrorCategory.TOO_LARGE, stage="download") from exc
            raise SourceAdapterError(ErrorCategory.UNAVAILABLE, stage="download") from exc
        detected_extension, detected_mime = detect_image_format(
            option.mime_type, destination.read_bytes()[:16]
        )
        if detected_extension != option.extension or detected_mime != option.mime_type:
            destination.unlink(missing_ok=True)
            raise SourceAdapterError(ErrorCategory.FORMAT_UNAVAILABLE, stage="download")
        validate_image_file(destination, detected_extension)
        return DownloadResult(
            path=destination,
            actual_bytes=actual,
            media_id=request.metadata.media_id,
            source_format_id=option.source_format_id,
            media_type="image",
            extension=detected_extension,
            mime_type=detected_mime,
        )

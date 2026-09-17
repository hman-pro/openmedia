"""Narrow LinkedIn public-embed image parser.

The route choice was informed by ShareXtract 0.23.4's Apache-2.0 LinkedIn extractor, but
this parser is an independent implementation against the reviewed guest-page shape; no
ShareXtract source was copied. It deliberately ignores Open Graph, avatar, reaction, and
article-preview images.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import replace
from html.parser import HTMLParser
from urllib.parse import urlsplit

from openmedia.models import Availability, FormatOption, MediaKind, MediaMetadata, SizeKind
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


_ACTIVITY_URL = re.compile(
    r"^/embed/feed/update/urn:li:(?:share|ugcPost|activity):(\d{8,32})/?$"
)


_ACTOR_NAME_CONTROL = "public_post_embed_feed-actor-name"
_COMMENTARY_TEST_ID = "main-feed-activity-embed-card__commentary"


class _EmbedParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.attachments: list[tuple[str, str | None]] = []
        self.creator_parts: list[str] | None = None
        self.caption_parts: list[str] | None = None
        # (field, tag, open depth) while collecting one element's text; never nested.
        self._capture: tuple[str, str, int] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        values = dict(attrs)
        if self._capture is not None:
            field, captured_tag, depth = self._capture
            if tag == "br" and field == "caption":
                self.caption_parts.append("\n")  # type: ignore[union-attr]
            elif tag == captured_tag:
                self._capture = (field, captured_tag, depth + 1)
            # An unclosed <p> must not hide a later attachment, so images are still checked.
            if tag != "img":
                return
        # Only the post's own actor link and commentary paragraph describe the post; alt
        # text, aria-labels, and Open Graph values are never promoted to metadata.
        if tag == "a" and values.get("data-tracking-control-name") == _ACTOR_NAME_CONTROL:
            if self.creator_parts is None:
                self.creator_parts = []
                self._capture = ("creator", tag, 1)
            return
        if tag == "p" and values.get("data-test-id") == _COMMENTARY_TEST_ID:
            if self.caption_parts is None:
                self.caption_parts = []
                self._capture = ("caption", tag, 1)
            return
        if tag != "img":
            return
        classes = frozenset((values.get("class") or "").split())
        # This is the explicit high-resolution feed attachment shape observed on the
        # guest embed. Requiring all structural classes excludes avatars/reactions and
        # article/OG previews rather than guessing from image order.
        if not {"lazy-load", "w-full", "object-cover", "object-center"}.issubset(classes):
            return
        url = values.get("data-delayed-url")
        if not url:
            return
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.hostname:
            return
        self.attachments.append((url, values.get("alt")))

    def handle_endtag(self, tag: str) -> None:
        if self._capture is None:
            return
        field, captured_tag, depth = self._capture
        if tag.lower() == captured_tag:
            self._capture = None if depth == 1 else (field, captured_tag, depth - 1)

    def handle_data(self, data: str) -> None:
        if self._capture is None:
            return
        target = self.creator_parts if self._capture[0] == "creator" else self.caption_parts
        target.append(data)  # type: ignore[union-attr]

    @property
    def creator(self) -> str | None:
        if self.creator_parts is None:
            return None
        return " ".join("".join(self.creator_parts).split()) or None

    @property
    def caption(self) -> str | None:
        if self.caption_parts is None:
            return None
        lines = ("".join(self.caption_parts)).splitlines()
        return "\n".join(line.strip() for line in lines).strip() or None


def embed_url(activity_id: str) -> str:
    if not activity_id.isdigit() or not 8 <= len(activity_id) <= 32:
        raise ValueError("LinkedIn activity ID must be numeric")
    return f"https://www.linkedin.com/embed/feed/update/urn:li:share:{activity_id}"


def parse_embed(
    html: str,
    *,
    requested_activity_id: str,
    fetched_url: str,
) -> InspectResult:
    """Parse one matching guest embed and require one explicit feed attachment."""
    parts = urlsplit(fetched_url)
    match = _ACTIVITY_URL.fullmatch(parts.path)
    if (
        parts.scheme != "https"
        or (parts.hostname or "").rstrip(".").lower() not in {"linkedin.com", "www.linkedin.com"}
        or match is None
        or match.group(1) != requested_activity_id
    ):
        raise SourceAdapterError(ErrorCategory.INVALID_SOURCE_RESPONSE, stage="inspection")
    parser = _EmbedParser()
    try:
        parser.feed(html)
        parser.close()
    except Exception as exc:
        raise SourceAdapterError(ErrorCategory.INVALID_SOURCE_RESPONSE, stage="inspection") from exc
    if not parser.attachments:
        raise SourceAdapterError(ErrorCategory.UNAVAILABLE, stage="inspection")
    if len(parser.attachments) != 1:
        raise SourceAdapterError(ErrorCategory.UNSUPPORTED_COLLECTION, stage="inspection")
    attachment, alt = parser.attachments[0]
    suffix = urlsplit(attachment).path.rsplit(".", 1)[-1].lower()
    extension = suffix if suffix in {"jpg", "jpeg", "png", "webp"} else "jpg"
    if extension == "jpeg":
        extension = "jpg"
    mime = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}[extension]
    metadata = MediaMetadata(
        platform="linkedin",
        canonical_url=f"https://www.linkedin.com/feed/update/urn:li:activity:{requested_activity_id}",
        media_id=requested_activity_id,
        # Alt text describes the attachment but is not necessarily the post caption, so only
        # the explicit commentary and actor-name elements supply these optional fields.
        title_or_caption=parser.caption,
        creator=parser.creator,
        media_kind=MediaKind.IMAGE,
    )
    option = FormatOption(
        option_id=0,
        adapter="linkedin_image",
        source_format_id=f"image:{requested_activity_id}",
        media_type="image",
        extension=extension,
        mime_type=mime,
        transport_ref={"url": attachment, "alt": alt},
    )
    return InspectResult(metadata=metadata, options=(option,))


_CONTENT_TYPES = {
    "image/jpeg": ("jpg", "image/jpeg"),
    "image/png": ("png", "image/png"),
    "image/webp": ("webp", "image/webp"),
}


def _image_signature(path, content_type: str) -> tuple[str, str]:
    prefix = path.read_bytes()[:16]
    detected = None
    if prefix.startswith(b"\xff\xd8\xff"):
        detected = _CONTENT_TYPES["image/jpeg"]
    elif prefix.startswith(b"\x89PNG\r\n\x1a\n"):
        detected = _CONTENT_TYPES["image/png"]
    elif len(prefix) >= 12 and prefix.startswith(b"RIFF") and prefix[8:12] == b"WEBP":
        detected = _CONTENT_TYPES["image/webp"]
    declared = _CONTENT_TYPES.get(content_type.split(";", 1)[0].strip().lower())
    if detected is None or detected != declared:
        raise SourceAdapterError(ErrorCategory.INVALID_SOURCE_RESPONSE, stage="download")
    return detected


class LinkedInImageAdapter:
    name = "linkedin_image"

    def inspect(
        self,
        request: InspectInput,
        *,
        transport: GuardedTransport,
        rate_control: RateController,
    ) -> InspectResult:
        route = recognize_source_url(request.source_url)
        if route.platform != "linkedin":
            raise SourceAdapterError(ErrorCategory.UNSUPPORTED_URL, stage="inspection")
        rate_control.acquire("linkedin", "metadata", deadline=request.deadline)
        response = transport.fetch(
            embed_url(route.media_id),
            limit=request.metadata_limit,
            deadline=request.deadline,
        )
        if not 200 <= response.status < 300:
            raise SourceAdapterError(ErrorCategory.UNAVAILABLE, stage="inspection")
        try:
            html = response.body.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise SourceAdapterError(ErrorCategory.INVALID_SOURCE_RESPONSE, stage="inspection") from exc
        result = parse_embed(
            html,
            requested_activity_id=route.media_id,
            fetched_url=response.url,
        )
        reference = result.options[0].transport_ref
        assert isinstance(reference, Mapping)
        attachment = str(reference["url"])
        probe = transport.head(attachment, deadline=request.deadline)
        # Classify the status first: an error response's content-type/length describe the
        # error, not the attachment, so they are never used to build an image choice.
        if probe.status == 429:
            retry = probe.headers.get("retry-after")
            retry_after = float(retry) if retry and retry.isdigit() else None
            rate_control.limited("linkedin", "metadata", retry_after=retry_after)
            raise SourceAdapterError(ErrorCategory.RATE_LIMITED, stage="inspection", retry_after=retry_after)
        if probe.status in {403, 404, 410}:
            raise SourceAdapterError(ErrorCategory.UNAVAILABLE, stage="inspection")
        if not 200 <= probe.status < 300:
            raise SourceAdapterError(ErrorCategory.INVALID_SOURCE_RESPONSE, stage="inspection")
        content_type = probe.headers.get("content-type", "").split(";", 1)[0].lower()
        image_format = _CONTENT_TYPES.get(content_type)
        if image_format is None:
            raise SourceAdapterError(ErrorCategory.INVALID_SOURCE_RESPONSE, stage="inspection")
        raw_length = probe.headers.get("content-length")
        try:
            size = int(raw_length) if raw_length is not None else None
        except ValueError as exc:
            raise SourceAdapterError(ErrorCategory.INVALID_SOURCE_RESPONSE, stage="inspection") from exc
        availability = Availability.SELECTABLE
        reason = None
        if size is not None and size > 50_000_000:
            availability = Availability.EXCLUDED
            reason = "File exceeds the 50000000-byte delivery limit"
        option = replace(
            result.options[0],
            extension=image_format[0],
            mime_type=image_format[1],
            size_bytes=size,
            size_kind=SizeKind.EXACT if size is not None else SizeKind.UNKNOWN,
            availability=availability,
            unavailable_reason=reason,
        )
        return InspectResult(result.metadata, (option,))

    def download(
        self,
        request: DownloadInput,
        *,
        transport: GuardedTransport,
        rate_control: RateController,
    ) -> DownloadResult:
        reference = request.option.transport_ref
        if not isinstance(reference, Mapping) or not isinstance(reference.get("url"), str):
            raise SourceAdapterError(ErrorCategory.FORMAT_UNAVAILABLE, stage="download")
        rate_control.acquire("linkedin", "media", deadline=request.deadline)
        destination = request.work_directory / f"selected.{request.option.extension}"
        actual = transport.download(
            reference["url"],
            destination,
            output_limit=request.output_limit,
            workspace_limit=request.workspace_limit,
            deadline=request.deadline,
        )
        extension, mime = _image_signature(destination, request.option.mime_type)
        if extension != request.option.extension:
            destination.unlink(missing_ok=True)
            raise SourceAdapterError(ErrorCategory.FORMAT_UNAVAILABLE, stage="download")
        validate_image_file(destination, extension)
        return DownloadResult(
            path=destination,
            actual_bytes=actual,
            media_id=request.metadata.media_id,
            source_format_id=request.option.source_format_id,
            media_type="image",
            extension=extension,
            mime_type=mime,
        )

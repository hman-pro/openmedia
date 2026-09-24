"""Normalized, Telegram-independent source adapter contract."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from dataclasses import replace
from typing import Any, Iterable, Mapping, Protocol, runtime_checkable
from urllib.parse import parse_qs, urlsplit, urlunsplit

from openmedia.models import FormatOption, MediaMetadata


MAX_INSPECTION_RESULT_BYTES = 2 * 1024 * 1024
MAX_METADATA_BYTES = 8 * 1024 * 1024
MAX_THUMBNAIL_BYTES = 1024 * 1024
_REQUEST_ID = re.compile(r"^[0-9a-f]{32}$")
_YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{6,64}$")
_INSTAGRAM_ID = re.compile(r"^[A-Za-z0-9_-]{5,64}$")
# LinkedIn activity, ugcPost, and share URNs are distinct objects even when their digits match,
# so the type is part of a post's identity for every request made on its behalf.
_LINKEDIN_URN = re.compile(r"^urn:li:(activity|ugcPost|share):(\d{8,32})$")
_LINKEDIN_SHORT_CODE = re.compile(r"^[A-Za-z0-9_-]{1,32}$")
# Research R6: the greedy prefix makes the identity the rightmost type word, and the trailing
# code may hold hyphens. A post with no text joins author and type with "_" (`<author>_share-`).
# Slugs without a type word predate typed slugs and name an activity.
_LINKEDIN_POST_SLUG = re.compile(
    r"^(?P<prefix>[^/?#\s]+)[-_](?P<type>activity|ugcPost|share)-(?P<id>\d{8,32})(?:-(?P<code>[A-Za-z0-9_-]{1,32}))?$"
)
_LINKEDIN_UNTYPED_POST_SLUG = re.compile(r"^[^/?#\s]+?-(?P<id>\d{8,32})(?:-[A-Za-z0-9_-]{1,32})?$")
SUPPORTED_HOSTS = frozenset(
    {
        "youtube.com",
        "www.youtube.com",
        "m.youtube.com",
        "youtu.be",
        "instagram.com",
        "www.instagram.com",
        "linkedin.com",
        "www.linkedin.com",
        "lnkd.in",
    }
)
_SCHEME = re.compile(r"https?://", re.IGNORECASE)
_BARE_SUPPORTED_HOST = re.compile(
    r"^(?:www\.|m\.)?(?:youtube\.com|youtu\.be|instagram\.com|linkedin\.com|lnkd\.in)(?:/|$)",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class SourceRoute:
    """A canonical, single-item route recognized before source inspection."""

    platform: str
    media_id: str
    canonical_url: str
    route_kind: str
    urn_kind: str | None = None  # LinkedIn activity/ugcPost/share; None for other platforms


def supported_host(url: str) -> bool:
    """Return whether an HTTPS URL names one of the three supported platforms.

    LinkedIn's app share host ``lnkd.in`` counts as LinkedIn: its ``/p/<code>`` short links
    are resolved to a post address inside the inspect worker, never here.
    """
    try:
        parts = urlsplit(url)
    except ValueError:
        return False
    return (
        parts.scheme.lower() == "https"
        and parts.hostname is not None
        and parts.hostname.rstrip(".").lower() in SUPPORTED_HOSTS
        and parts.username is None
        and parts.password is None
    )


def normalize_supported_link(raw: str) -> str | None:
    """Return an HTTPS form of a supported-platform link, or None for anything else.

    Telegram marks scheme-less and ``http://`` links as URL entities; every route is rebuilt
    as a canonical HTTPS URL later, so upgrading the scheme here changes no source identity.
    """
    candidate = raw.strip().rstrip(".,;:!?)]}\"'")
    if _SCHEME.match(candidate):
        if candidate[:7].lower() == "http://":
            candidate = "https://" + candidate[7:]
    elif _BARE_SUPPORTED_HOST.match(candidate):
        candidate = "https://" + candidate
    else:
        return None
    return candidate if supported_host(candidate) else None


def supported_links(candidates: Iterable[str]) -> tuple[str, ...]:
    """Normalize link candidates, keeping only supported-platform links in order."""
    return tuple(link for raw in candidates if (link := normalize_supported_link(raw)))


def supported_urls_in_text(text: str) -> tuple[str, ...]:
    """Return supported-platform links found in plain text, ignoring unrelated links.

    Each whitespace-separated token yields at most one candidate, so a supported host named
    inside another site's URL (for example in a query string) is never counted as a link.
    """
    candidates: list[str] = []
    for token in text.split():
        scheme = _SCHEME.search(token)
        if scheme is not None:
            candidates.append(token[scheme.start():])
        else:
            candidates.append(token.lstrip("(<[{\"'"))
    return supported_links(candidates)


def recognize_source_url(url: str) -> SourceRoute:
    """Recognize a supported single-item route without contacting the source.

    Host recognition and route recognition are deliberately separate: callers can explain
    that a playlist/live/collection route is unsupported instead of claiming no link exists.
    """
    try:
        parts = urlsplit(url)
    except ValueError as exc:
        raise SourceAdapterError(ErrorCategory.UNSUPPORTED_URL, stage="input") from exc
    if not supported_host(url) or parts.fragment:
        raise SourceAdapterError(ErrorCategory.UNSUPPORTED_URL, stage="input")
    host = (parts.hostname or "").rstrip(".").lower()
    segments = [segment for segment in parts.path.split("/") if segment]

    if host == "lnkd.in":
        # A share short link names no post by itself; its code is a placeholder identity until
        # the inspect worker resolves it. The query (tracking only) is dropped.
        if len(segments) == 2 and segments[0] == "p" and _LINKEDIN_SHORT_CODE.fullmatch(segments[1]):
            code = segments[1]
            return SourceRoute("linkedin", code, f"https://lnkd.in/p/{code}", "short_link")
        raise SourceAdapterError(ErrorCategory.UNSUPPORTED_URL, stage="input")

    if host in {"youtu.be", "youtube.com", "www.youtube.com", "m.youtube.com"}:
        media_id: str | None = None
        if host == "youtu.be" and len(segments) == 1:
            media_id = segments[0]
        elif segments == ["watch"]:
            values = parse_qs(parts.query).get("v", [])
            if len(values) == 1:
                media_id = values[0]
        elif len(segments) == 2 and segments[0] == "shorts":
            media_id = segments[1]
        if "list" in parse_qs(parts.query) or (segments and segments[0] in {"playlist", "live"}):
            raise SourceAdapterError(ErrorCategory.UNSUPPORTED_COLLECTION, stage="input")
        if media_id is None or not _YOUTUBE_ID.fullmatch(media_id):
            raise SourceAdapterError(ErrorCategory.UNSUPPORTED_URL, stage="input")
        canonical = f"https://www.youtube.com/watch?v={media_id}"
        return SourceRoute("youtube", media_id, canonical, "video")

    if host in {"instagram.com", "www.instagram.com"}:
        # Instagram app shares may insert a username before /p/ or /reel/.
        route_index = next(
            (index for index, value in enumerate(segments) if value in {"p", "reel"}),
            -1,
        )
        if route_index < 0 or route_index + 2 != len(segments):
            raise SourceAdapterError(ErrorCategory.UNSUPPORTED_URL, stage="input")
        media_id = segments[route_index + 1]
        if not _INSTAGRAM_ID.fullmatch(media_id):
            raise SourceAdapterError(ErrorCategory.UNSUPPORTED_URL, stage="input")
        kind = segments[route_index]
        canonical = f"https://www.instagram.com/{kind}/{media_id}/"
        return SourceRoute(
            "instagram",
            media_id,
            canonical,
            "video" if kind == "reel" else "image_or_video",
        )

    if host in {"linkedin.com", "www.linkedin.com"}:
        if len(segments) == 2 and segments[0] == "posts":
            match = _LINKEDIN_POST_SLUG.fullmatch(segments[1]) or _LINKEDIN_UNTYPED_POST_SLUG.fullmatch(segments[1])
            if match is None:
                raise SourceAdapterError(ErrorCategory.UNSUPPORTED_URL, stage="input")
            # The share link itself is kept: it is the only posts form LinkedIn serves (R5).
            urn_kind, media_id = match.groupdict().get("type") or "activity", match.group("id")
            canonical = f"https://www.linkedin.com/posts/{segments[1]}"
            return SourceRoute("linkedin", media_id, canonical, "post", urn_kind)
        decoded = [segment.replace("%3A", ":").replace("%3a", ":") for segment in segments]
        match = _LINKEDIN_URN.fullmatch(decoded[2]) if len(decoded) == 3 and decoded[:2] == ["feed", "update"] else None
        if match is None:
            raise SourceAdapterError(ErrorCategory.UNSUPPORTED_URL, stage="input")
        urn_kind, media_id = match.group(1), match.group(2)
        canonical = f"https://www.linkedin.com/feed/update/urn:li:{urn_kind}:{media_id}"
        # The pinned LinkedInIE matches feed/update only for activity URNs; other types can
        # reach the guest-embed image path but never the video extractor.
        return SourceRoute("linkedin", media_id, canonical, "post" if urn_kind == "activity" else "embed", urn_kind)

    raise SourceAdapterError(ErrorCategory.UNSUPPORTED_URL, stage="input")


class Operation(StrEnum):
    INSPECT = "inspect"
    DOWNLOAD = "download"


class ErrorCategory(StrEnum):
    UNSUPPORTED_URL = "unsupported_url"
    UNSUPPORTED_COLLECTION = "unsupported_collection"
    UNAVAILABLE = "unavailable"
    NO_FORMATS = "no_formats"
    FORMAT_UNAVAILABLE = "format_unavailable"
    TOO_LARGE = "too_large"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    STORAGE_EXHAUSTED = "storage_exhausted"
    UNSAFE_DESTINATION = "unsafe_destination"
    INVALID_SOURCE_RESPONSE = "invalid_source_response"
    SHORT_LINK_UNRESOLVED = "short_link_unresolved"
    SHORT_LINK_NOT_POST = "short_link_not_post"
    INTERNAL = "internal"


# Detail marker for a signed media URL the CDN no longer honors (HTTP 403/410). It is the
# only download failure a metadata refresh can repair, so it is the only one that triggers it.
EXPIRED_URL = "expired_url"

# The failed outcomes of resolving a LinkedIn short link (specs/004-linkedin-share-links/
# data-model.md "ResolutionOutcome"). Only these may travel as an error detail between the
# worker and the supervisor; anything else is dropped so no URL or free text crosses over.
RESOLUTION_FAILURES = frozenset(
    {
        "not_found",
        "no_redirect",
        "too_many_redirects",
        "timed_out",
        "unreachable",
        "outside_linkedin",
        "not_a_post",
    }
)


class SourceAdapterError(RuntimeError):
    """Sanitized adapter failure suitable for the worker protocol."""

    def __init__(
        self,
        category: ErrorCategory | str,
        *,
        stage: str,
        detail: str | None = None,
        retry_after: float | None = None,
    ) -> None:
        self.category = ErrorCategory(category)
        self.stage = stage
        self.detail = detail
        self.retry_after = retry_after
        super().__init__(f"{self.category.value} during {stage}")


def _validate_common(request_id: str, work_directory: Path, deadline: float) -> None:
    if not _REQUEST_ID.fullmatch(request_id):
        raise ValueError("request_id must be 32 lowercase hexadecimal characters")
    if not work_directory.is_absolute():
        raise ValueError("work_directory must be an absolute parent-created path")
    if deadline <= 0:
        raise ValueError("deadline must be an absolute positive monotonic value")


@dataclass(frozen=True, slots=True)
class InspectInput:
    source_url: str
    request_id: str
    work_directory: Path
    deadline: float
    response_limit: int = MAX_INSPECTION_RESULT_BYTES
    metadata_limit: int = MAX_METADATA_BYTES
    thumbnail_limit: int = MAX_THUMBNAIL_BYTES
    output_limit: int = 50_000_000
    operation: Operation = field(default=Operation.INSPECT, init=False)

    def __post_init__(self) -> None:
        _validate_common(self.request_id, self.work_directory, self.deadline)
        if not self.source_url.startswith("https://"):
            raise ValueError("source_url must already be a validated canonical HTTPS URL")
        for name in ("response_limit", "metadata_limit", "thumbnail_limit", "output_limit"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")


@dataclass(frozen=True, slots=True)
class DownloadInput:
    request_id: str
    metadata: MediaMetadata
    option: FormatOption
    work_directory: Path
    deadline: float
    output_limit: int
    workspace_limit: int
    operation: Operation = field(default=Operation.DOWNLOAD, init=False)

    def __post_init__(self) -> None:
        _validate_common(self.request_id, self.work_directory, self.deadline)
        if self.output_limit <= 0 or self.workspace_limit <= 0:
            raise ValueError("output and workspace limits must be positive")
        if self.workspace_limit < self.output_limit:
            raise ValueError("workspace_limit cannot be smaller than output_limit")
        if self.option.availability != "selectable":
            raise ValueError("only a selectable server-bound option can be downloaded")


@dataclass(frozen=True, slots=True)
class InspectResult:
    metadata: MediaMetadata
    options: tuple[FormatOption, ...]
    thumbnail_path: Path | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "options", tuple(self.options))
        if not self.options:
            raise ValueError("inspection must return at least one normalized option")


@dataclass(frozen=True, slots=True)
class DownloadResult:
    path: Path
    actual_bytes: int
    media_id: str
    source_format_id: str
    media_type: str
    extension: str
    mime_type: str
    # Measured from the delivered file, not the source listing: Telegram's player shapes the
    # frame and shows the length only from these hints.
    width: int | None = None
    height: int | None = None
    duration_seconds: float | None = None

    def __post_init__(self) -> None:
        if not self.path.is_absolute():
            raise ValueError("download result path must be absolute")
        if self.actual_bytes < 0:
            raise ValueError("actual_bytes must be nonnegative")
        if not self.media_id or not self.source_format_id:
            raise ValueError("download result must retain source identity")


@dataclass(frozen=True, slots=True)
class TransportResponse:
    url: str
    status: int
    headers: Mapping[str, str]
    body: bytes
    # Repeated Set-Cookie headers cannot share the header mapping; values stay out of repr.
    set_cookies: tuple[str, ...] = field(default=(), repr=False)


@runtime_checkable
class GuardedTransport(Protocol):
    """The only network capability supplied to an adapter."""

    def fetch(
        self,
        url: str,
        *,
        limit: int,
        headers: Mapping[str, str] | None = None,
        deadline: float | None = None,
    ) -> TransportResponse: ...

    def head(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        deadline: float | None = None,
        follow_redirects: bool = True,
    ) -> TransportResponse: ...

    def download(
        self,
        url: str,
        destination: Path,
        *,
        output_limit: int,
        workspace_limit: int,
        headers: Mapping[str, str] | None = None,
        deadline: float | None = None,
        range_bytes: int | None = None,
    ) -> int: ...


@runtime_checkable
class RateController(Protocol):
    """Parent-owned rate state queried before each adapter request."""

    def acquire(
        self, platform: str, request_class: str, *, deadline: float
    ) -> float: ...

    def limited(
        self, platform: str, request_class: str, *, retry_after: float | None
    ) -> None: ...


@runtime_checkable
class SourceAdapter(Protocol):
    name: str

    def inspect(
        self,
        request: InspectInput,
        *,
        transport: GuardedTransport,
        rate_control: RateController,
    ) -> InspectResult: ...

    def download(
        self,
        request: DownloadInput,
        *,
        transport: GuardedTransport,
        rate_control: RateController,
    ) -> DownloadResult: ...


class SourceRouter:
    """Route only the five planned platform/media combinations."""

    def __init__(self, *, ytdlp: SourceAdapter | None = None, instagram: SourceAdapter | None = None, linkedin: SourceAdapter | None = None) -> None:
        if ytdlp is None:
            from openmedia.sources.ytdlp import YtDlpAdapter

            ytdlp = YtDlpAdapter()
        if instagram is None:
            from openmedia.sources.instagram import InstagramImageAdapter

            instagram = InstagramImageAdapter()
        if linkedin is None:
            from openmedia.sources.linkedin import LinkedInImageAdapter

            linkedin = LinkedInImageAdapter()
        self.adapters = {
            "yt_dlp": ytdlp,
            "instagram_image": instagram,
            "linkedin_image": linkedin,
        }

    def inspect(self, request: InspectInput, *, transport: GuardedTransport, rate_control: RateController) -> InspectResult:
        result = self._inspect(request, transport=transport, rate_control=rate_control)
        options = tuple(replace(option, availability="excluded", unavailable_reason=f"File exceeds the {request.output_limit}-byte delivery limit")
            if option.size_bytes is not None and option.size_bytes > request.output_limit
            and (option.size_kind == "exact" or "+" in option.source_format_id) else option for option in result.options)
        return replace(result, options=options)

    def _inspect(self, request: InspectInput, *, transport: GuardedTransport, rate_control: RateController) -> InspectResult:
        route = recognize_source_url(request.source_url)
        if route.route_kind == "short_link":
            from openmedia.sources.linkedin import resolve_short_link

            resolved = resolve_short_link(
                request.source_url,
                transport=transport,
                rate_control=rate_control,
                deadline=request.deadline,
            )
            # A resolved route cannot be `short_link` again: resolve_short_link only returns an
            # address on linkedin.com or www.linkedin.com, so this recursion is one level deep.
            return self._inspect(replace(request, source_url=resolved), transport=transport, rate_control=rate_control)
        if route.platform == "youtube" or route.route_kind == "video":
            return self.adapters["yt_dlp"].inspect(request, transport=transport, rate_control=rate_control)
        if route.platform == "instagram":
            try:
                return self.adapters["instagram_image"].inspect(request, transport=transport, rate_control=rate_control)
            except SourceAdapterError as exc:
                if exc.category is not ErrorCategory.INVALID_SOURCE_RESPONSE:
                    raise
                return self.adapters["yt_dlp"].inspect(request, transport=transport, rate_control=rate_control)
        if route.platform == "linkedin":
            if route.route_kind != "post":
                return self.adapters["linkedin_image"].inspect(request, transport=transport, rate_control=rate_control)
            try:
                return self.adapters["yt_dlp"].inspect(request, transport=transport, rate_control=rate_control)
            except SourceAdapterError as exc:
                if exc.category not in {ErrorCategory.UNAVAILABLE, ErrorCategory.NO_FORMATS}:
                    raise
                return self.adapters["linkedin_image"].inspect(request, transport=transport, rate_control=rate_control)
        raise SourceAdapterError(ErrorCategory.UNSUPPORTED_URL, stage="inspection")

    def download(self, request: DownloadInput, *, transport: GuardedTransport, rate_control: RateController) -> DownloadResult:
        adapter = self.adapters.get(request.option.adapter)
        if adapter is None:
            raise SourceAdapterError(ErrorCategory.FORMAT_UNAVAILABLE, stage="download")
        try:
            return adapter.download(request, transport=transport, rate_control=rate_control)
        except SourceAdapterError as first:
            if first.detail != EXPIRED_URL:
                raise
            refreshed = self.inspect(
                InspectInput(
                    source_url=request.metadata.canonical_url,
                    request_id=request.request_id,
                    work_directory=request.work_directory,
                    deadline=request.deadline,
                    output_limit=request.output_limit,
                ),
                transport=transport,
                rate_control=rate_control,
            )
            if refreshed.metadata.media_id != request.metadata.media_id:
                raise SourceAdapterError(ErrorCategory.FORMAT_UNAVAILABLE, stage="download") from first
            replacement = next(
                (
                    candidate
                    for candidate in refreshed.options
                    if _same_option(request.option, candidate)
                ),
                None,
            )
            if replacement is None:
                raise SourceAdapterError(ErrorCategory.FORMAT_UNAVAILABLE, stage="download") from first
            # Only remove known files owned by this attempt, never arbitrary worker paths.
            for basename in (f"selected.{request.option.extension}", "component-video", "component-audio"):
                (request.work_directory / basename).unlink(missing_ok=True)
            refreshed_request = replace(request, option=replacement)
            return adapter.download(
                refreshed_request,
                transport=transport,
                rate_control=rate_control,
            )


def _same_option(original: FormatOption, refreshed: FormatOption) -> bool:
    """Signed URLs and size estimates may change; selected identity/quality never may."""
    return all(
        (
            original.adapter == refreshed.adapter,
            original.source_format_id == refreshed.source_format_id,
            original.media_type == refreshed.media_type,
            original.extension == refreshed.extension,
            original.mime_type == refreshed.mime_type,
            original.width == refreshed.width,
            original.height == refreshed.height,
            original.bitrate == refreshed.bitrate,
            original.includes_audio == refreshed.includes_audio,
            refreshed.availability == "selectable",
            all((original.transport_ref or {}).get(key) == (refreshed.transport_ref or {}).get(key)
                for key in ("vcodec", "acodec")
                if isinstance(original.transport_ref, Mapping) and isinstance(refreshed.transport_ref, Mapping)),
        )
    )


def codec_family(value: str) -> str:
    """Map a yt-dlp or ffprobe codec string to its family name (h264, av1, aac, vp9, opus)."""
    lowered = value.lower()
    if lowered.startswith(("avc1", "h264")):
        return "h264"
    if lowered.startswith(("av01", "av1")):
        return "av1"
    if lowered.startswith(("mp4a", "aac")):
        return "aac"
    if lowered.startswith("vp9"):
        return "vp9"
    if lowered.startswith("opus"):
        return "opus"
    return lowered


_IMAGE_CODECS = {"jpg": "mjpeg", "png": "png", "webp": "webp"}


def validate_image_file(path: Path, extension: str) -> None:
    """Decode-probe a downloaded image; a matching signature prefix alone proves nothing."""
    import json
    import subprocess

    try:
        probe = subprocess.run(["ffprobe", "-v", "error", "-protocol_whitelist", "file",
            "-show_entries", "stream=codec_type,codec_name,width,height", "-of", "json", str(path)],
            check=True, capture_output=True, text=True, timeout=10)
        streams = json.loads(probe.stdout)["streams"]
        if len(streams) != 1 or streams[0].get("codec_name") != _IMAGE_CODECS[extension]:
            raise ValueError("image content does not match the selected format")
        if int(streams[0].get("width") or 0) <= 0 or int(streams[0].get("height") or 0) <= 0:
            raise ValueError("image has no decodable dimensions")
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError) as exc:
        Path(path).unlink(missing_ok=True)
        raise SourceAdapterError(ErrorCategory.INVALID_SOURCE_RESPONSE, stage="download") from exc


def fetch_optional_thumbnail(
    result: InspectResult,
    request: InspectInput,
    *,
    transport: GuardedTransport,
) -> InspectResult:
    """Fetch a distinct optional thumbnail; omission/failure never fails inspection."""
    url = result.metadata.thumbnail_url
    if not url:
        return result
    try:
        response = transport.fetch(url, limit=request.thumbnail_limit, deadline=request.deadline)
        if not 200 <= response.status < 300:
            return result
        content_type = response.headers.get("content-type", "").split(";", 1)[0].lower()
        signatures = {
            "image/jpeg": response.body.startswith(b"\xff\xd8\xff"),
            "image/png": response.body.startswith(b"\x89PNG\r\n\x1a\n"),
            "image/webp": len(response.body) >= 12 and response.body.startswith(b"RIFF") and response.body[8:12] == b"WEBP",
        }
        if not signatures.get(content_type, False):
            return result
        extension = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[content_type]
        path = request.work_directory / f"thumbnail.{extension}"
        path.write_bytes(response.body)
        return replace(result, thumbnail_path=path)
    except Exception:
        return result


__all__ = [
    "DownloadInput",
    "DownloadResult",
    "ErrorCategory",
    "GuardedTransport",
    "InspectInput",
    "InspectResult",
    "Operation",
    "RESOLUTION_FAILURES",
    "RateController",
    "SourceAdapter",
    "SourceAdapterError",
    "SourceRoute",
    "SourceRouter",
    "TransportResponse",
    "codec_family",
    "fetch_optional_thumbnail",
    "normalize_supported_link",
    "recognize_source_url",
    "supported_host",
    "supported_links",
    "supported_urls_in_text",
]

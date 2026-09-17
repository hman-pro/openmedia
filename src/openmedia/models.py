"""Validated in-memory entities for one media-download request."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping
from urllib.parse import urlsplit


_REQUEST_ID = re.compile(r"^[0-9a-f]{32}$")
_SAFE_EXTENSION = re.compile(r"^[a-z0-9][a-z0-9_-]{0,15}$")


class RequestState(StrEnum):
    CHECKING = "checking"
    AWAITING_SELECTION = "awaiting_selection"
    DOWNLOADING = "downloading"
    SENDING = "sending"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    REPLACED = "replaced"


class MediaKind(StrEnum):
    VIDEO = "video"
    IMAGE = "image"
    COLLECTION = "collection"
    LIVE = "live"


class MediaType(StrEnum):
    VIDEO = "video"
    AUDIO = "audio"
    IMAGE = "image"


class SizeKind(StrEnum):
    EXACT = "exact"
    ESTIMATED = "estimated"
    UNKNOWN = "unknown"


class Availability(StrEnum):
    SELECTABLE = "selectable"
    EXCLUDED = "excluded"


class DeliveryStatus(StrEnum):
    CONFIRMED = "confirmed"
    FAILED = "failed"
    UNKNOWN = "unknown"


def _enum_value(enum_type: type[StrEnum], value: StrEnum | str, field_name: str) -> StrEnum:
    try:
        return enum_type(value)
    except ValueError as exc:
        allowed = ", ".join(member.value for member in enum_type)
        raise ValueError(f"{field_name} must be one of: {allowed}") from exc


def _source_url(value: str, field_name: str = "canonical_url") -> None:
    parts = urlsplit(value)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise ValueError(f"{field_name} must be a canonical public HTTPS URL")


def _optional_positive(value: int | float | None, field_name: str) -> None:
    if value is not None and value <= 0:
        raise ValueError(f"{field_name} must be positive when supplied")


@dataclass(frozen=True, slots=True)
class MediaMetadata:
    platform: str
    canonical_url: str
    media_id: str
    title_or_caption: str | None = None
    creator: str | None = None
    duration_seconds: float | None = None
    thumbnail_url: str | None = None
    media_count: int = 1
    media_kind: MediaKind | str = MediaKind.VIDEO

    def __post_init__(self) -> None:
        if not self.platform or not self.media_id:
            raise ValueError("platform and media_id are required")
        _source_url(self.canonical_url)
        kind = _enum_value(MediaKind, self.media_kind, "media_kind")
        object.__setattr__(self, "media_kind", kind)
        if self.duration_seconds is not None and self.duration_seconds < 0:
            raise ValueError("duration_seconds must be nonnegative")
        if kind is MediaKind.IMAGE and self.duration_seconds is not None:
            raise ValueError("duration_seconds must be absent for images")
        if self.media_count < 1:
            raise ValueError("media_count must be at least one")
        if kind in (MediaKind.VIDEO, MediaKind.IMAGE) and self.media_count != 1:
            raise ValueError("single video/image metadata cannot hide multiple media items")
        if kind is MediaKind.COLLECTION and self.media_count < 2:
            raise ValueError("collection metadata must identify multiple media items")
        if self.thumbnail_url is not None:
            _source_url(self.thumbnail_url, "thumbnail_url")
        for field_name in ("title_or_caption", "creator"):
            value = getattr(self, field_name)
            if value is not None and not value.strip():
                raise ValueError(f"{field_name} must be absent rather than fabricated/blank")


@dataclass(frozen=True, slots=True)
class FormatOption:
    option_id: int
    adapter: str
    source_format_id: str
    media_type: MediaType | str
    extension: str
    mime_type: str
    width: int | None = None
    height: int | None = None
    bitrate: float | None = None
    includes_audio: bool | None = None
    size_bytes: int | None = None
    size_kind: SizeKind | str = SizeKind.UNKNOWN
    transport_ref: str | Mapping[str, Any] | None = field(default=None, repr=False)
    availability: Availability | str = Availability.SELECTABLE
    unavailable_reason: str | None = None

    def __post_init__(self) -> None:
        if self.option_id < 0:
            raise ValueError("option_id must be a nonnegative request-local integer")
        if not self.adapter or not self.source_format_id:
            raise ValueError("adapter and source_format_id are required")
        media_type = _enum_value(MediaType, self.media_type, "media_type")
        size_kind = _enum_value(SizeKind, self.size_kind, "size_kind")
        availability = _enum_value(Availability, self.availability, "availability")
        object.__setattr__(self, "media_type", media_type)
        object.__setattr__(self, "size_kind", size_kind)
        object.__setattr__(self, "availability", availability)
        extension = self.extension.removeprefix(".").lower()
        if not _SAFE_EXTENSION.fullmatch(extension):
            raise ValueError("extension must be a supported native file extension")
        object.__setattr__(self, "extension", extension)
        if "/" not in self.mime_type or any(char.isspace() for char in self.mime_type):
            raise ValueError("mime_type must be a valid detected media type")
        _optional_positive(self.width, "width")
        _optional_positive(self.height, "height")
        _optional_positive(self.bitrate, "bitrate")
        if media_type is MediaType.VIDEO:
            if not isinstance(self.includes_audio, bool):
                raise ValueError("includes_audio must be true/false for video")
        elif self.includes_audio is not None:
            raise ValueError("includes_audio must be absent for audio and image options")
        if self.size_bytes is not None and self.size_bytes < 0:
            raise ValueError("size_bytes must be nonnegative or absent")
        if size_kind is SizeKind.UNKNOWN and self.size_bytes is not None:
            raise ValueError("unknown size cannot carry a byte count")
        if size_kind is not SizeKind.UNKNOWN and self.size_bytes is None:
            raise ValueError("exact/estimated size requires a byte count")
        if availability is Availability.SELECTABLE and self.unavailable_reason is not None:
            raise ValueError("selectable options cannot have an exclusion reason")
        if availability is Availability.EXCLUDED and not self.unavailable_reason:
            raise ValueError("excluded options require a user-facing reason")
        if isinstance(self.transport_ref, Mapping):
            object.__setattr__(self, "transport_ref", MappingProxyType(dict(self.transport_ref)))


@dataclass(frozen=True, slots=True)
class DeliveryResult:
    status: DeliveryStatus | str
    message_id: int | None = None
    actual_bytes: int | None = None
    error_category: str | None = None
    failed_stage: str | None = None
    next_step: str | None = None
    notification_sent: bool = False

    def __post_init__(self) -> None:
        status = _enum_value(DeliveryStatus, self.status, "status")
        object.__setattr__(self, "status", status)
        if not isinstance(self.notification_sent, bool):
            raise ValueError("notification_sent must be a boolean")
        if status is DeliveryStatus.CONFIRMED:
            if self.message_id is None or self.message_id <= 0:
                raise ValueError("confirmed delivery requires a Telegram message_id")
            if self.actual_bytes is None or self.actual_bytes < 0:
                raise ValueError("confirmed delivery requires the actual byte count")
            if any((self.error_category, self.failed_stage, self.next_step)):
                raise ValueError("confirmed delivery cannot carry failure details")
        else:
            if self.message_id is not None:
                raise ValueError("failed/unknown delivery cannot claim a message_id")
            if not self.error_category or not self.failed_stage or not self.next_step:
                raise ValueError("failed/unknown delivery requires sanitized failure details")


@dataclass(slots=True)
class DownloadRequest:
    request_id: str
    user_id: int
    chat_id: int
    source_url: str
    platform: str
    media_id: str
    state: RequestState | str = RequestState.CHECKING
    metadata: MediaMetadata | None = None
    options: tuple[FormatOption, ...] = ()
    selected_option_id: int | None = None
    created_at: float = 0.0
    preview_expires_at: float | None = None
    processing_deadline: float | None = None
    preview_message_id: int | None = None
    work_directory: Path | None = field(default=None, repr=False)
    worker_pid: int | None = field(default=None, repr=False)
    delivery_result: DeliveryResult | None = None

    def __post_init__(self) -> None:
        if not _REQUEST_ID.fullmatch(self.request_id):
            raise ValueError("request_id must be a random 128-bit value encoded as 32 hex characters")
        if isinstance(self.user_id, bool) or not isinstance(self.user_id, int):
            raise ValueError("user_id must be a Telegram integer identity")
        if isinstance(self.chat_id, bool) or not isinstance(self.chat_id, int):
            raise ValueError("chat_id must be a Telegram integer identity")
        _source_url(self.source_url, "source_url")
        if not self.platform or not self.media_id:
            raise ValueError("platform and media_id are required")
        self.state = _enum_value(RequestState, self.state, "state")  # type: ignore[assignment]
        self.options = tuple(self.options)
        option_ids = [option.option_id for option in self.options]
        if len(option_ids) != len(set(option_ids)):
            raise ValueError("option_id values must be unique within a request")
        if self.selected_option_id is not None and self.selected_option_id not in option_ids:
            raise ValueError("selected_option_id must name an option bound to this request")
        if self.created_at < 0:
            raise ValueError("created_at must be monotonic and nonnegative")
        for name in ("preview_expires_at", "processing_deadline"):
            value = getattr(self, name)
            if value is not None and value < self.created_at:
                raise ValueError(f"{name} cannot precede created_at")
        if self.preview_message_id is not None and self.preview_message_id <= 0:
            raise ValueError("preview_message_id must be a positive Telegram message ID")
        if self.worker_pid is not None and self.worker_pid <= 0:
            raise ValueError("worker_pid must be positive")

    def option(self, option_id: int) -> FormatOption:
        for option in self.options:
            if option.option_id == option_id:
                return option
        raise KeyError(option_id)


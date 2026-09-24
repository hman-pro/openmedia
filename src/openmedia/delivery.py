"""Native-byte Telegram delivery (inline video or document) with explicit uncertainty semantics."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable
from datetime import timedelta
from pathlib import Path
from typing import Any

from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter, TelegramError, TimedOut

from openmedia.models import DeliveryResult, DownloadRequest, FormatOption, MediaType
from openmedia.network import FileBoundaryError, ResponseTooLarge, validate_owned_file
from openmedia.sources import DownloadResult


def _failure(status: str, category: str, next_step: str) -> DeliveryResult:
    return DeliveryResult(
        status=status,
        error_category=category,
        failed_stage="sending",
        next_step=next_step,
        notification_sent=False,
    )


async def _send(
    bot: Any,
    *,
    request: DownloadRequest,
    selected: FormatOption,
    downloaded: DownloadResult,
    file: Any,
    duration_seconds: float | None,
    timeout: float,
) -> Any:
    """``video``/``silent`` play inline via ``sendVideo``; audio and pictures stay documents."""
    common = {
        "chat_id": request.chat_id,
        "filename": f"media.{selected.extension}",
        "read_timeout": timeout,
        "write_timeout": timeout,
    }
    if selected.media_type == MediaType.VIDEO:
        # Metadata hints only; the uploaded bytes are the downloaded file, unchanged (R7).
        # Telegram's player draws the frame from these, so the measured file wins over the
        # source listing, which some sources (Instagram progressive MP4) leave empty.
        hints: dict[str, int] = {}
        width = downloaded.width or selected.width
        height = downloaded.height or selected.height
        if downloaded.duration_seconds is not None:
            duration_seconds = downloaded.duration_seconds
        if width:
            hints["width"] = width
        if height:
            hints["height"] = height
        if duration_seconds is not None and duration_seconds >= 0:
            hints["duration"] = int(round(duration_seconds))
        return await bot.send_video(video=file, supports_streaming=True, **hints, **common)
    # Pictures too: never `sendPhoto`, that recompresses (contracts/telegram-bot.md).
    return await bot.send_document(document=file, **common)


async def deliver_media(
    bot: Any,
    *,
    request: DownloadRequest,
    downloaded: DownloadResult,
    owned_directory: Path,
    max_file_bytes: int,
    deadline: float,
    duration_seconds: float | None = None,
    monotonic: Callable[[], float] = time.monotonic,
    sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
) -> DeliveryResult:
    """Send once, except for a definite RetryAfter rejection inside the same deadline."""
    try:
        actual = validate_owned_file(
            downloaded.path,
            owned_directory,
            max_bytes=max_file_bytes,
        )
    except (FileBoundaryError, ResponseTooLarge):
        return _failure("failed", "invalid_output", "Submit the link again for fresh choices.")
    try:
        selected = request.option(request.selected_option_id)  # type: ignore[arg-type]
    except (KeyError, TypeError):
        return _failure("failed", "invalid_selection", "Submit the link again for fresh choices.")
    if (
        actual != downloaded.actual_bytes
        or downloaded.media_id != request.media_id
        or downloaded.source_format_id != selected.source_format_id
        or downloaded.extension != selected.extension
        or downloaded.mime_type != selected.mime_type
        or str(downloaded.media_type) != selected.media_type.value
    ):
        return _failure("failed", "format_changed", "Submit the link again to review current choices.")

    while True:
        if monotonic() >= deadline:
            return _failure("failed", "timeout", "Retry with the link later.")
        try:
            with downloaded.path.open("rb") as file:
                message = await _send(
                    bot,
                    request=request,
                    selected=selected,
                    downloaded=downloaded,
                    file=file,
                    duration_seconds=duration_seconds,
                    timeout=max(0.1, deadline - monotonic()),
                )
            message_id = getattr(message, "message_id", None)
            if not isinstance(message_id, int) or message_id <= 0:
                return _failure(
                    "unknown",
                    "ambiguous_upload",
                    "Check this chat before submitting the link again.",
                )
            return DeliveryResult(
                status="confirmed",
                message_id=message_id,
                actual_bytes=actual,
            )
        except RetryAfter as exc:
            retry = exc.retry_after
            seconds = retry.total_seconds() if isinstance(retry, timedelta) else float(retry)
            if seconds < 0 or monotonic() + seconds >= deadline:
                return _failure("failed", "rate_limited", "Retry the link later.")
            await sleep(seconds)
        except Forbidden:
            return _failure("failed", "blocked", "Unblock the bot and submit the link again.")
        except BadRequest:
            return _failure("failed", "telegram_rejected", "Choose another option or link.")
        except (TimedOut, NetworkError):
            # Telegram may have accepted the body before the connection failed.
            return _failure(
                "unknown",
                "ambiguous_upload",
                "Check this chat before submitting the link again.",
            )
        except TelegramError:
            return _failure("failed", "telegram_error", "Retry the link later.")
        except OSError:
            return _failure("failed", "local_file", "Submit the link again.")


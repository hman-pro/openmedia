"""Pure presentation helpers shared by Telegram handlers and contract tests."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Protocol

from openmedia.models import FormatOption, MediaMetadata, MediaType, SizeKind


# Fixed user-facing text (research R9, contracts/telegram-bot.md). Kinds are the plain string
# values of `choices.ChoiceKind`, so this module stays free of policy imports.
CHECKING_TEXT = "Checking link…"
MAX_TITLE_CHARACTERS = 200
MAX_CAPTION_CHARACTERS = 1024
UNTITLED = "Untitled video"
_CHOICE_LABELS = {
    "video": "Video",
    "silent": "Video (no sound)",
    "audio": "Audio only",
    "image": "Picture",
}
_KIND_ORDER = ("video", "silent", "audio")
_MISSING_SENTENCES = (("not_offered", "Not available"), ("too_large", "Too large to send"))
_UNCONFIRMED = "could not confirm sending. Check this chat before sending the link again."


class _ChoiceSetLike(Protocol):
    missing: Mapping[Any, str]


def choice_label(kind: str) -> str:
    """Plain label for a choice kind: ``Video``, ``Video (no sound)``, ``Audio only``, ``Picture``."""
    return _CHOICE_LABELS[str(kind)]


def _title_line(title: str | None) -> str:
    # Captions may span lines; the card keeps the title on one line.
    flattened = " ".join((title or "").split())
    if not flattened:
        return UNTITLED
    if len(flattened) > MAX_TITLE_CHARACTERS:
        return flattened[: MAX_TITLE_CHARACTERS - 1].rstrip() + "…"
    return flattened


def _duration_line(seconds: float | None) -> str | None:
    if seconds is None or seconds < 0:
        return None
    total = int(seconds)
    hours, rest = divmod(total, 3600)
    minutes, secs = divmod(rest, 60)
    return f"{hours}:{minutes:02d}:{secs:02d}" if hours else f"{minutes}:{secs:02d}"


def _unavailable_line(missing: Mapping[Any, str]) -> str | None:
    reasons = {str(kind): reason for kind, reason in missing.items()}
    sentences = []
    for reason, lead in _MISSING_SENTENCES:
        labels = [choice_label(kind) for kind in _KIND_ORDER if reasons.get(kind) == reason]
        if labels:
            sentences.append(f"{lead}: {', '.join(labels)}.")
    return " ".join(sentences) or None


def card_text(metadata: MediaMetadata, choice_set: _ChoiceSetLike, status: str | None = None) -> str:
    """Card text: title, duration, one unavailable line, then the status line when given."""
    tail = [line for line in (
        _duration_line(metadata.duration_seconds),
        _unavailable_line(choice_set.missing),
        status,
    ) if line]
    title = _title_line(metadata.title_or_caption)
    text = "\n".join((title, *tail))
    if len(text) > MAX_CAPTION_CHARACTERS:
        # Only the title can be shortened; the fixed lines always fit a Telegram caption.
        room = max(1, MAX_CAPTION_CHARACTERS - len(text) + len(title) - 1)
        text = "\n".join((title[:room] + "…", *tail))
    return text


def status_text(
    label: str,
    stage: str,
    *,
    automatic: bool = False,
    next_step: str | None = None,
    unknown: bool = False,
) -> str:
    """One status line: ``<Label> — downloading…``, ``— sending…``, ``— sent.``, or a failure."""
    if unknown:
        return f"{label} — {_UNCONFIRMED}"
    if stage == "downloading":
        return f"{label} — only version available, downloading…" if automatic else f"{label} — downloading…"
    if stage == "sending":
        return f"{label} — sending…"
    if stage == "completed":
        return f"{label} — sent."
    failed = f"{label} — {stage} failed."
    return f"{failed} {next_step}" if next_step else failed


def sort_options(options: tuple[FormatOption, ...] | list[FormatOption]) -> tuple[FormatOption, ...]:
    order = {
        (MediaType.VIDEO, True): 0,
        (MediaType.AUDIO, None): 1,
        (MediaType.VIDEO, False): 2,
        (MediaType.IMAGE, None): 3,
    }

    def quality(option: FormatOption) -> float:
        return float(option.height or option.width or option.bitrate or 0)

    return tuple(
        sorted(
            options,
            key=lambda option: (
                order[(option.media_type, option.includes_audio)],
                -quality(option),
                option.option_id,
            ),
        )
    )


def format_size(option: FormatOption) -> str:
    if option.size_kind is SizeKind.UNKNOWN or option.size_bytes is None:
        return "size unknown"
    value = option.size_bytes
    units = ("B", "KiB", "MiB", "GiB")
    shown = float(value)
    unit = units[0]
    for unit in units:
        if shown < 1024 or unit == units[-1]:
            break
        shown /= 1024
    rendered = f"{shown:.1f} {unit}" if unit != "B" else f"{value} B"
    if option.size_kind is SizeKind.ESTIMATED:
        return f"about {rendered} (estimated)"
    return rendered


def option_label(option: FormatOption) -> str:
    details: list[str] = [option.media_type.value, option.extension.upper()]
    if option.height:
        details.append(f"{option.height}p")
    elif option.width:
        details.append(f"{option.width}px")
    elif option.bitrate:
        details.append(f"{option.bitrate:g} kbps")
    if option.media_type is MediaType.VIDEO:
        details.append("with sound" if option.includes_audio else "silent")
        if "+" in option.source_format_id:
            details.append("combined")
    details.append(format_size(option))
    return " · ".join(details)


"""Pure presentation helpers shared by Telegram handlers and contract tests."""

from __future__ import annotations

from openmedia.models import FormatOption, MediaType, SizeKind


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


"""Pure three-choice policy between source inspection and the Telegram card.

``choose`` keeps at most one native option per kind (``video``, ``silent``, ``audio``), or the
single picture for an image post. It never creates, splits, or re-encodes an option; it only
selects among adapter options and rebinds their ``option_id`` to ``0..n-1``. No I/O, no
clock, no Telegram types (contracts/choice-policy.md, research R1-R3).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, replace
from enum import StrEnum
from types import MappingProxyType

from openmedia.models import FormatOption, MediaKind
from openmedia.sources import codec_family


TIER_ONE_MAX_SHORTER_SIDE = 720
NOT_OFFERED = "not_offered"
TOO_LARGE = "too_large"


class ChoiceKind(StrEnum):
    VIDEO = "video"
    SILENT = "silent"
    AUDIO = "audio"
    IMAGE = "image"


_BUTTON_KINDS = (ChoiceKind.VIDEO, ChoiceKind.SILENT, ChoiceKind.AUDIO)


@dataclass(frozen=True, slots=True)
class ChoiceSet:
    options: tuple[FormatOption, ...]
    missing: Mapping[ChoiceKind, str] = field(default_factory=dict)
    automatic: bool = False


def kind_of(option: FormatOption) -> ChoiceKind:
    """Derive the user-facing kind from the option's media type and audio flag."""
    if option.media_type == "video":
        return ChoiceKind.VIDEO if option.includes_audio else ChoiceKind.SILENT
    if option.media_type == "audio":
        return ChoiceKind.AUDIO
    if option.media_type == "image":
        return ChoiceKind.IMAGE
    raise ValueError(f"no choice kind for media type {option.media_type!r}")


def choose(options: Sequence[FormatOption], *, media_kind: MediaKind | str, max_file_bytes: int) -> ChoiceSet:
    """Return the kept choices; never raises for empty or all-excluded input."""
    if media_kind == MediaKind.AUDIO:
        audio = [option for option in options if option.media_type == "audio"]
        compatible = [option for option in audio if _mobile_audio(option)]
        picked = _pick_audio(compatible, max_file_bytes) or _pick_audio(audio, max_file_bytes)
        return _result([picked], {}) if picked is not None else _result(
            [], {ChoiceKind.AUDIO: TOO_LARGE if audio else NOT_OFFERED})

    if media_kind == MediaKind.IMAGE:
        images = [option for option in options if option.media_type == "image" and _selectable(option)]
        fitting = _size_filter(images, max_file_bytes)
        kept = [min(fitting, key=lambda option: option.option_id)] if fitting else []
        return _result(kept, {})

    kept: list[FormatOption] = []
    missing: dict[ChoiceKind, str] = {}
    for kind in _BUTTON_KINDS:
        of_kind = [option for option in options if option.media_type != "image" and kind_of(option) == kind]
        picked = _pick_audio(of_kind, max_file_bytes) if kind is ChoiceKind.AUDIO else _pick_video(of_kind, kind, max_file_bytes)
        if picked is not None:
            kept.append(picked)
        else:
            eligible = of_kind if kind is ChoiceKind.AUDIO else [option for option in of_kind if _codec_class(option, kind) is not None]
            missing[kind] = TOO_LARGE if eligible else NOT_OFFERED
    return _result(kept, missing)


def _result(kept: list[FormatOption], missing: dict[ChoiceKind, str]) -> ChoiceSet:
    rebound = tuple(replace(option, option_id=index) for index, option in enumerate(kept))
    return ChoiceSet(options=rebound, missing=MappingProxyType(missing), automatic=len(rebound) == 1)


def _selectable(option: FormatOption) -> bool:
    return option.availability == "selectable"


def _size_filter(candidates: Sequence[FormatOption], max_file_bytes: int) -> list[FormatOption]:
    """Known sizes that fit; unknown-size candidates only when no candidate has a known size."""
    known = [option for option in candidates if option.size_bytes is not None]
    if known:
        return [option for option in known if option.size_bytes <= max_file_bytes]  # type: ignore[operator]
    return list(candidates)


def _codec_class(option: FormatOption, kind: ChoiceKind) -> str | None:
    """``known`` for a phone-playable MP4, ``unknown`` for a last-resort MP4, else None (R1)."""
    if option.extension != "mp4":
        return None
    reference = option.transport_ref if isinstance(option.transport_ref, Mapping) else {}
    vcodec, acodec = reference.get("vcodec"), reference.get("acodec")
    with_audio = kind is ChoiceKind.VIDEO
    if not vcodec and (not with_audio or not acodec):
        return "unknown"
    if not vcodec or (with_audio and not acodec):
        return None
    if codec_family(str(vcodec)) != "h264":
        return None
    if with_audio and codec_family(str(acodec)) != "aac":
        return None
    return "known"


def _shorter_side(option: FormatOption) -> int | None:
    sides = [side for side in (option.width, option.height) if side is not None]
    return min(sides) if sides else None


def _tie_key(option: FormatOption) -> tuple[float, int, int]:
    # Higher bitrate, then exact before estimated, then lower option_id.
    return (-(option.bitrate or 0.0), 0 if option.size_kind == "exact" else 1, option.option_id)


def _best(candidates: Sequence[FormatOption], key: Callable[[FormatOption], tuple]) -> FormatOption | None:
    return min(candidates, key=key) if candidates else None


def _pick_video(of_kind: Sequence[FormatOption], kind: ChoiceKind, max_file_bytes: int) -> FormatOption | None:
    selectable = [option for option in of_kind if _selectable(option)]
    known = [option for option in selectable if _codec_class(option, kind) == "known"]
    pool = known or [option for option in selectable if _codec_class(option, kind) == "unknown"]
    candidates = _size_filter(pool, max_file_bytes)
    codec_rank = {id(option): 0 if _codec_class(option, kind) == "known" else 1 for option in candidates}

    tier_one = [option for option in candidates if (_shorter_side(option) or 0) <= TIER_ONE_MAX_SHORTER_SIDE]
    if tier_one:
        # Largest known shorter side first; unknown dimensions rank below every known one.
        return _best(tier_one, lambda option: (
            _shorter_side(option) is None, -(_shorter_side(option) or 0), codec_rank[id(option)], *_tie_key(option)))
    return _best(candidates, lambda option: (
        _shorter_side(option), codec_rank[id(option)], *_tie_key(option)))


def _mobile_audio(option: FormatOption) -> bool:
    """Prefer native AAC in an MP4-family container for music downloads."""
    reference = option.transport_ref if isinstance(option.transport_ref, Mapping) else {}
    return option.extension in {"m4a", "mp4"} and codec_family(str(reference.get("acodec") or "")) == "aac"


def _pick_audio(of_kind: Sequence[FormatOption], max_file_bytes: int) -> FormatOption | None:
    candidates = _size_filter([option for option in of_kind if _selectable(option)], max_file_bytes)
    return _best(candidates, _tie_key)


__all__ = ["ChoiceKind", "ChoiceSet", "choose", "kind_of"]

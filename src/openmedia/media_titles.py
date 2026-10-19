"""Pure, request-local labels for media uploads.

Labels are upload metadata only, never local paths. Do not include their values in
diagnostic events or exception messages.
"""

from dataclasses import dataclass, field
import re
import unicodedata

import regex


TITLE_CODE_POINT_LIMIT = 64
FILENAME_BYTE_LIMIT = 240
FALLBACK_TITLE = "Untitled media"

_JOINERS = frozenset(("\u200c", "\u200d"))
# Keep a complete black-flag/tag-spec/cancel-tag sequence as one token. Tags
# outside that sequence remain non-display controls and are removed below.
_TITLE_PARTS = re.compile(r"\U0001f3f4[\U000e0020-\U000e007e]+\U000e007f|.", re.DOTALL)
_DEFAULT_IGNORABLE = regex.compile(r"\p{Default_Ignorable_Code_Point}")
_UNSAFE_FILENAME_RUN = re.compile(r'[<>:"/\\|?*]+')
_RESERVED_BASENAME = re.compile(r"(?:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])", re.IGNORECASE)


@dataclass(frozen=True)
class DeliveryLabels:
    """Immutable labels whose source text is excluded from representations."""

    caption: str = field(repr=False)
    filename: str = field(repr=False)


def _is_invisible(character: str) -> bool:
    """Identify characters that cannot make a title or filename stem visible.

    This predicate only decides fallback eligibility; retained characters remain
    unchanged when they accompany visible text.
    """
    return _DEFAULT_IGNORABLE.fullmatch(character) is not None


def _normalize_title(title: str | None) -> str:
    # Convert whitespace first: tabs/newlines are controls but separate words.
    spaced = " ".join((title or "").split())
    cleaned = "".join(
        part
        for match in _TITLE_PARTS.finditer(spaced)
        if len(part := match.group()) > 1
        or part in _JOINERS
        or unicodedata.category(part) not in {"Cc", "Cs", "Cf"}
    )
    normalized = " ".join(cleaned.split())
    if not any(
        not character.isspace() and not _is_invisible(character)
        for character in normalized
    ):
        return FALLBACK_TITLE
    return normalized


def _safe_stem(title: str) -> str:
    stem = " ".join(_UNSAFE_FILENAME_RUN.sub("_", title).split()).strip(" .")
    if not any(
        character not in " _." and not _is_invisible(character)
        for character in stem
    ):
        return FALLBACK_TITLE
    if _RESERVED_BASENAME.fullmatch(stem.partition(".")[0]):
        stem = f"_{stem}"
    return stem



def _shorten(text: str, *, byte_limit: int | None = None, trim_stem: bool = False) -> str:
    """Keep a whole-grapheme prefix within the independent label budgets."""
    if len(text) <= TITLE_CODE_POINT_LIMIT and (
        byte_limit is None or len(text.encode("utf-8")) <= byte_limit
    ):
        return text

    # A terminal ellipsis costs one code point and three UTF-8 bytes. Iterate
    # clusters rather than materializing all matches, and never normalize Unicode.
    point_budget = TITLE_CODE_POINT_LIMIT - 1
    byte_budget = None if byte_limit is None else byte_limit - 3
    points = 0
    encoded_bytes = 0
    prefix_end = 0
    for match in regex.finditer(r"\X", text):
        cluster = match.group()
        cluster_points = len(cluster)
        cluster_bytes = len(cluster.encode("utf-8")) if byte_budget is not None else 0
        if points + cluster_points > point_budget or (
            byte_budget is not None and encoded_bytes + cluster_bytes > byte_budget
        ):
            break
        points += cluster_points
        encoded_bytes += cluster_bytes
        prefix_end = match.end()
    prefix = text[:prefix_end]
    if trim_stem:
        prefix = prefix.rstrip(" .")
    return prefix + "…"


def derive_media_titles(title: str | None, extension: str) -> DeliveryLabels:
    """Derive upload labels using an already validated selected extension.

    Normalize display text and derive a safe stem from its full text independently.
    Source suffixes are retained; the selected extension is always appended.
    No source text is logged or persisted.
    """
    display_title = _normalize_title(title)
    suffix = f".{extension}"
    stem = _shorten(
        _safe_stem(display_title),
        byte_limit=FILENAME_BYTE_LIMIT - len(suffix.encode("utf-8")),
        trim_stem=True,
    )
    return DeliveryLabels(
        caption=_shorten(display_title),
        filename=f"{stem}{suffix}",
    )

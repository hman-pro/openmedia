"""Short-title delivery labels follow the feature 006 data model.

Filename constraint: "Safe stem plus dot and selected extension; extension outside
stem budget; at most 240 UTF-8 bytes for the complete filename, including any
ellipsis; upload label only".

These tests derive upload labels without creating or renaming a local media file.
Normalization constraint: "One line, whitespace collapsed, non-display controls
removed, Unicode text preserved; neutral fallback when display-empty".
Shortening preserves whole graphemes without NFC/NFKC rewriting.
"""

import pytest

from openmedia.media_titles import DeliveryLabels, derive_media_titles


def assert_filename_constraint(labels: DeliveryLabels, stem: str, extension: str) -> None:
    """Verify the selected extension is appended outside the safe stem budget."""
    assert labels.filename == f"{stem}.{extension}"
    assert len(stem) <= 64
    assert len(labels.filename.encode("utf-8")) <= 240


def test_short_safe_title_supplies_caption_and_filename() -> None:
    labels = derive_media_titles("Summer walk", "mp4")

    assert isinstance(labels, DeliveryLabels)
    assert labels.caption == "Summer walk"
    assert_filename_constraint(labels, "Summer walk", "mp4")


def test_identical_title_uses_each_selected_extension() -> None:
    labels_by_extension = {
        extension: derive_media_titles("Summer walk", extension)
        for extension in ("mp4", "m4a", "jpg")
    }

    for extension, labels in labels_by_extension.items():
        assert labels.caption == "Summer walk"
        assert_filename_constraint(labels, "Summer walk", extension)
    assert len({labels.filename for labels in labels_by_extension.values()}) == 3


@pytest.mark.parametrize(
    ("title", "extension"),
    [("Summer walk.mp4", "m4a"), ("Summer walk.mp4", "mp4")],
)
def test_source_suffix_is_preserved_before_selected_extension(
    title: str, extension: str
) -> None:
    labels = derive_media_titles(title, extension)

    assert labels.caption == title
    assert_filename_constraint(labels, title, extension)


@pytest.mark.parametrize(
    "title",
    [
        None,
        "",
        " ",
        "\t\r\n\u00a0\u2003",
        "\x00\x01\x1f\x7f",
        "\ud800\udfff",
        "\u200b\u200e\u202e\ufeff",
        "\u200c\u200d\ufe0f",
    ],
    ids=["missing", "empty", "space", "unicode-whitespace", "controls", "surrogates", "invisible", "joiners-and-selector"],
)
def test_display_empty_title_uses_neutral_fallback(title: str | None) -> None:
    labels = derive_media_titles(title, "mp4")

    assert labels.caption == "Untitled media"
    assert_filename_constraint(labels, "Untitled media", "mp4")


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("  First\t\r\nsecond\u00a0\u2003third  ", "First second third"),
        ("First\nsecond\tthird", "First second third"),
        ("A\x00\x01\x7fB\ud800C\u200b\u202eD", "ABCD"),
        (" A\x00  \u200b B ", "A B"),
    ],
    ids=["collapse-unicode-whitespace", "whitespace-before-control-removal", "remove-controls", "collapse-after-removal"],
)
def test_title_normalization_produces_one_readable_line(
    title: str, expected: str
) -> None:
    labels = derive_media_titles(title, "m4a")

    assert labels.caption == expected
    assert_filename_constraint(labels, expected, "m4a")


@pytest.mark.parametrize(
    ("title", "stem"),
    [
        ("<b>Track</b> & [artist](link) *live*", "_b_Track_b_ & [artist](link) _live_"),
        ("Café e\u0301 日本語 العربية", "Café e\u0301 日本語 العربية"),
        ("👩\u200d💻 ❤️ می\u200cروم", "👩\u200d💻 ❤️ می\u200cروم"),
        ("ＡＢＣ ①", "ＡＢＣ ①"),
    ],
    ids=["literal-markup", "unicode-and-decomposed-accent", "visible-joiners-and-selector", "no-compatibility-normalization"],
)
def test_literal_markup_and_unicode_are_preserved_in_caption(
    title: str, stem: str
) -> None:
    labels = derive_media_titles(title, "jpg")

    assert labels.caption == title
    assert_filename_constraint(labels, stem, "jpg")


@pytest.mark.parametrize(
    ("title", "stem"),
    [
        ('A<>:"/\\|?*B', "A_B"),
        ("A/B:C", "A_B_C"),
        ("../../clip", "_.._clip"),
        ("..\\..\\clip", "_.._clip"),
        ("... clip ...", "clip"),
        (" . clip. . ", "clip"),
    ],
    ids=["unsafe-run", "separate-unsafe-runs", "forward-traversal", "backward-traversal", "outer-dots", "outer-spaces-and-dots"],
)
def test_filename_sanitization_preserves_literal_caption(
    title: str, stem: str
) -> None:
    labels = derive_media_titles(title, "mp4")

    assert labels.caption == title.strip()
    assert_filename_constraint(labels, stem, "mp4")


@pytest.mark.parametrize(
    "title",
    ["CON", "prn", "AuX", "nul", *[f"COM{i}" for i in range(1, 10)], *[f"lpt{i}" for i in range(1, 10)], "con.txt", "LPT9.track.mp4"],
)
def test_reserved_device_basename_is_prefixed(title: str) -> None:
    labels = derive_media_titles(title, "m4a")

    assert labels.caption == title
    assert_filename_constraint(labels, f"_{title}", "m4a")


@pytest.mark.parametrize("title", ["CONCERT", "COM0", "COM10", "LPT0", "LPT10", "auxiliary"])
def test_reserved_name_prefix_does_not_modify_ordinary_names(title: str) -> None:
    labels = derive_media_titles(title, "mp4")

    assert labels.caption == title
    assert_filename_constraint(labels, title, "mp4")


@pytest.mark.parametrize("title", ["/\\|", '<>:"?*', "...", "___", " . / . "])
def test_unusable_filename_stem_falls_back_independently(title: str) -> None:
    labels = derive_media_titles(title, "jpg")

    assert labels.caption == title.strip()
    assert_filename_constraint(labels, "Untitled media", "jpg")


def test_filename_sanitization_uses_full_title_before_shortening() -> None:
    title = "Start" + "/" * 70 + "end"

    labels = derive_media_titles(title, "mp4")

    # Sanitizing a shortened caption would lose the meaningful final word.
    assert_filename_constraint(labels, "Start_end", "mp4")


# Contract: "At most 64 code points; truncated only at grapheme boundaries,
# terminal ellipsis included in budget". The sanitized stem is "Derived
# independently from full normalized title; unsafe runs replaced, reserved names
# protected, at most 64 code points". Complete filenames have "at most 240 UTF-8
# bytes for the complete filename, including any ellipsis".
@pytest.mark.parametrize("length", [63, 64, 65])
def test_ascii_code_point_boundary_and_extension_exclusion(length: int) -> None:
    title = "a" * length
    expected = title if length <= 64 else "a" * 63 + "…"

    labels = derive_media_titles(title, "webm")

    assert labels.caption == expected
    assert_filename_constraint(labels, expected, "webm")


@pytest.mark.parametrize(
    ("cluster", "prefix_count", "stem_count"),
    [("界", 63, 63), ("e\u0301", 31, 31), ("🇫🇮", 31, 29), ("👍🏽", 31, 29), ("👩\u200d💻", 21, 21)],
    ids=["cjk", "decomposed-accent", "flag", "modifier", "zwj-emoji"],
)
def test_shortening_keeps_longest_whole_grapheme_prefix(
    cluster: str, prefix_count: int, stem_count: int
) -> None:
    title = cluster * 70
    expected = cluster * prefix_count + "…"
    # Flags and modified emoji reach the filename byte limit first.
    labels = derive_media_titles(title, "mp4")

    assert labels.caption == expected
    assert_filename_constraint(labels, cluster * stem_count + "…", "mp4")


def test_first_cluster_larger_than_code_point_budget_yields_only_ellipsis() -> None:
    title = "e" + "\u0301" * 64

    labels = derive_media_titles(title, "mp4")

    assert labels.caption == "…"
    assert_filename_constraint(labels, "…", "mp4")


@pytest.mark.parametrize("separator", [" ", "."])
def test_shortened_filename_prefix_trims_final_spaces_and_dots(separator: str) -> None:
    title = "a" * 62 + separator + "bc"

    labels = derive_media_titles(title, "mp4")

    assert labels.caption == "a" * 62 + separator + "…"
    assert_filename_constraint(labels, "a" * 62 + "…", "mp4")


@pytest.mark.parametrize("complete_bytes", [239, 240, 241])
def test_complete_filename_byte_boundary_reserves_suffix_and_ellipsis(
    complete_bytes: int,
) -> None:
    title = "😀" * 58 + "a" * (complete_bytes - 236)
    assert len(f"{title}.mp4".encode("utf-8")) == complete_bytes
    expected = title if complete_bytes <= 240 else "😀" * 58 + "a…"

    labels = derive_media_titles(title, "mp4")

    assert labels.caption == title
    assert_filename_constraint(labels, expected, "mp4")
    assert len(labels.filename.encode("utf-8")) == min(complete_bytes, 240)


def test_sixty_four_four_byte_characters_need_only_filename_shortening() -> None:
    title = "😀" * 64

    labels = derive_media_titles(title, "mp4")

    assert labels.caption == title
    assert_filename_constraint(labels, "😀" * 58 + "…", "mp4")
    assert len(labels.filename.encode("utf-8")) == 239


def test_first_cluster_larger_than_byte_budget_yields_only_ellipsis_stem() -> None:
    # Supplementary variation selectors are preserved and belong to the base's
    # cluster: 60 points fit the caption, but its 237 bytes exceed 233 stem bytes.
    title = "a" + "\U000e0100" * 59
    assert len(title) == 60
    assert len(title.encode("utf-8")) == 237

    labels = derive_media_titles(title, "mp4")

    assert labels.caption == title
    assert_filename_constraint(labels, "…", "mp4")


def test_source_suffix_remains_text_while_selected_extension_is_reserved() -> None:
    title = "😀" * 58 + ".mp4"

    labels = derive_media_titles(title, "webm")

    assert labels.caption == title
    assert_filename_constraint(labels, "😀" * 58 + "…", "webm")


def test_sanitization_runs_before_independent_caption_and_stem_shortening() -> None:
    title = "Start" + "/" * 70 + "end"

    labels = derive_media_titles(title, "mp4")

    assert labels.caption == "Start" + "/" * 58 + "…"
    assert_filename_constraint(labels, "Start_end", "mp4")

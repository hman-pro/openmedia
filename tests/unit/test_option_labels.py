"""Fixed user-facing text for the streamlined bot UX (research R9, contracts/telegram-bot.md).

The new helpers are looked up on the module at call time, so each test fails on its own
missing name rather than the whole file failing at import.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field

import pytest

from openmedia import presentation
from openmedia.models import FormatOption, MediaMetadata
from openmedia.presentation import sort_options

EM = "—"
ELLIPSIS = "…"
FORBIDDEN = ("Platform:", "Source:", "Creator:", "http", "MiB", "kbps", "avc1", "mp4a", "webm", "opus")


def make(option_id: int, media_type: str, *, height: int | None = None, audio: bool | None = None, size: int | None = None, size_kind: str = "unknown") -> FormatOption:
    return FormatOption(
        option_id=option_id,
        adapter="fixture",
        source_format_id=str(option_id),
        media_type=media_type,
        extension={"video": "mp4", "audio": "m4a", "image": "jpg"}[media_type],
        mime_type={"video": "video/mp4", "audio": "audio/mp4", "image": "image/jpeg"}[media_type],
        height=height,
        includes_audio=audio,
        size_bytes=size,
        size_kind=size_kind,
    )


@dataclass(frozen=True)
class StubChoiceSet:
    """Shape of `choices.ChoiceSet`; kinds are plain strings, equal to the `ChoiceKind` StrEnum."""

    options: tuple[FormatOption, ...] = ()
    missing: Mapping[str, str] = field(default_factory=dict)
    automatic: bool = False


def metadata(title: str | None = "Sunset timelapse", duration: float | None = 125) -> MediaMetadata:
    return MediaMetadata(
        platform="youtube",
        canonical_url="https://www.youtube.com/watch?v=abcdefghijk",
        media_id="abcdefghijk",
        title_or_caption=title,
        creator="Some Creator",
        duration_seconds=duration,
        thumbnail_url="https://i.ytimg.com/vi/abcdefghijk/hq.jpg",
    )


def three_choices(missing: Mapping[str, str] | None = None) -> StubChoiceSet:
    options = (
        FormatOption(
            option_id=0, adapter="youtube", source_format_id="18", media_type="video",
            extension="mp4", mime_type="video/mp4", width=640, height=360, bitrate=500.0,
            includes_audio=True, size_bytes=12 * 1024 * 1024, size_kind="exact",
            transport_ref={"vcodec": "avc1.42001E", "acodec": "mp4a.40.2"},
        ),
        FormatOption(
            option_id=1, adapter="youtube", source_format_id="137", media_type="video",
            extension="mp4", mime_type="video/mp4", width=1920, height=1080, bitrate=4000.0,
            includes_audio=False, size_bytes=40 * 1024 * 1024, size_kind="estimated",
            transport_ref={"vcodec": "avc1.640028", "acodec": None},
        ),
        FormatOption(
            option_id=2, adapter="youtube", source_format_id="140", media_type="audio",
            extension="m4a", mime_type="audio/mp4", bitrate=129.5,
            size_bytes=3 * 1024 * 1024, size_kind="exact",
            transport_ref={"vcodec": None, "acodec": "mp4a.40.2"},
        ),
    )
    return StubChoiceSet(options=options, missing=dict(missing or {}), automatic=False)


# --- kept from 001: sort_options is still used by ytdlp.normalize_info -----------------


def test_options_sort_by_semantic_type_then_quality() -> None:
    options = [
        make(0, "image"),
        make(1, "video", height=720, audio=False),
        make(2, "audio"),
        make(3, "video", height=360, audio=True),
        make(4, "video", height=1080, audio=True),
    ]
    assert [option.option_id for option in sort_options(options)] == [4, 3, 2, 1, 0]


# --- choice_label ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("kind", "label"),
    [("video", "Video"), ("silent", "Video (no sound)"), ("audio", "Audio only"), ("image", "Picture")],
)
def test_choice_label_is_the_fixed_plain_label(kind: str, label: str) -> None:
    assert presentation.choice_label(kind) == label


# --- CHECKING_TEXT ----------------------------------------------------------------------


def test_checking_text() -> None:
    assert presentation.CHECKING_TEXT == f"Checking link{ELLIPSIS}"


# --- card_text --------------------------------------------------------------------------


def test_card_has_title_then_duration_and_nothing_else_when_all_kinds_kept() -> None:
    text = presentation.card_text(metadata(), three_choices())
    assert text.split("\n") == ["Sunset timelapse", "2:05"]


@pytest.mark.parametrize(
    ("seconds", "shown"),
    [(5, "0:05"), (59, "0:59"), (60, "1:00"), (605, "10:05"), (3600, "1:00:00"), (3725, "1:02:05"), (36061, "10:01:01")],
)
def test_duration_is_m_ss_or_h_mm_ss(seconds: int, shown: str) -> None:
    lines = presentation.card_text(metadata(duration=seconds), three_choices()).split("\n")
    assert lines == ["Sunset timelapse", shown]


def test_duration_line_is_omitted_when_unknown() -> None:
    assert presentation.card_text(metadata(duration=None), three_choices()) == "Sunset timelapse"


def test_missing_title_reads_untitled_video() -> None:
    lines = presentation.card_text(metadata(title=None), three_choices()).split("\n")
    assert lines[0] == "Untitled video"


def test_long_title_is_truncated_to_200_characters() -> None:
    title_line = presentation.card_text(metadata(title="x" * 250), three_choices()).split("\n")[0]
    assert len(title_line) <= 200
    assert title_line.startswith("x" * 190)


def test_title_of_exactly_200_characters_is_kept_whole() -> None:
    title_line = presentation.card_text(metadata(title="y" * 200), three_choices()).split("\n")[0]
    assert title_line == "y" * 200


@pytest.mark.parametrize(
    ("missing", "line"),
    [
        ({"audio": "not_offered"}, "Not available: Audio only."),
        ({"silent": "not_offered", "audio": "not_offered"}, "Not available: Video (no sound), Audio only."),
        ({"video": "too_large"}, "Too large to send: Video."),
        ({"video": "too_large", "audio": "not_offered"}, "Not available: Audio only. Too large to send: Video."),
    ],
    ids=["one-not-offered", "two-not-offered", "one-too-large", "not-offered-plus-too-large"],
)
def test_unavailable_line_exact_text(missing: dict[str, str], line: str) -> None:
    text = presentation.card_text(metadata(), three_choices(missing))
    assert text.split("\n") == ["Sunset timelapse", "2:05", line]


def test_unavailable_labels_follow_kind_order_not_mapping_order() -> None:
    missing = {"audio": "not_offered", "video": "not_offered", "silent": "not_offered"}
    text = presentation.card_text(metadata(), StubChoiceSet(missing=missing))
    assert text.split("\n")[-1] == "Not available: Video, Video (no sound), Audio only."


def test_no_unavailable_line_when_nothing_is_missing() -> None:
    text = presentation.card_text(metadata(), three_choices({}))
    assert "Not available" not in text
    assert "Too large" not in text


def test_status_line_comes_last() -> None:
    status = f"Video {EM} downloading{ELLIPSIS}"
    text = presentation.card_text(metadata(), three_choices({"audio": "not_offered"}), status=status)
    assert text.split("\n") == ["Sunset timelapse", "2:05", "Not available: Audio only.", status]


def test_status_line_directly_follows_duration_when_nothing_is_missing() -> None:
    status = f"Audio only {EM} sent."
    text = presentation.card_text(metadata(), three_choices(), status=status)
    assert text.split("\n") == ["Sunset timelapse", "2:05", status]


def test_card_fits_a_telegram_caption_in_the_worst_case() -> None:
    status = f"Video (no sound) {EM} could not confirm sending. Check this chat before sending the link again."
    missing = {"video": "too_large", "silent": "too_large", "audio": "not_offered"}
    text = presentation.card_text(metadata(title="z" * 5000, duration=359999), StubChoiceSet(missing=missing), status=status)
    assert len(text) <= 1024
    assert text.endswith(status)


@pytest.mark.parametrize(
    "missing",
    [{}, {"audio": "not_offered"}, {"video": "too_large", "silent": "not_offered"}],
)
def test_card_never_shows_source_or_technical_details(missing: dict[str, str]) -> None:
    text = presentation.card_text(metadata(), three_choices(missing), status=f"Video {EM} sending{ELLIPSIS}")
    for forbidden in FORBIDDEN:
        assert forbidden not in text
    assert "Some Creator" not in text
    assert "youtube" not in text.lower()
    assert "360p" not in text
    assert "1080" not in text


# --- status_text ----------------------------------------------------------------------


def test_status_downloading() -> None:
    assert presentation.status_text("Video", "downloading") == f"Video {EM} downloading{ELLIPSIS}"


def test_status_downloading_automatic() -> None:
    assert (
        presentation.status_text("Video", "downloading", automatic=True)
        == f"Video {EM} only version available, downloading{ELLIPSIS}"
    )


def test_status_picture_downloading() -> None:
    assert presentation.status_text("Picture", "downloading") == f"Picture {EM} downloading{ELLIPSIS}"


def test_status_sending() -> None:
    assert presentation.status_text("Audio only", "sending") == f"Audio only {EM} sending{ELLIPSIS}"


def test_status_completed() -> None:
    assert presentation.status_text("Video (no sound)", "completed") == f"Video (no sound) {EM} sent."


def test_status_failed_carries_stage_and_next_step() -> None:
    next_step = "The download stage timed out. Retry the link later."
    assert (
        presentation.status_text("Video", "download", next_step=next_step)
        == f"Video {EM} download failed. {next_step}"
    )


def test_status_upload_unconfirmed() -> None:
    assert (
        presentation.status_text("Audio only", "upload", unknown=True)
        == f"Audio only {EM} could not confirm sending. Check this chat before sending the link again."
    )

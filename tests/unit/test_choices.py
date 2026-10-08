"""Unit tests for the three-choice policy (contracts/choice-policy.md, research R1-R3)."""

from __future__ import annotations

import dataclasses
import random
from typing import Any

import pytest

from openmedia.models import FormatOption, MediaKind

LIMIT = 50_000_000
MB = 1_000_000
ALLOWED_MISSING = {"not_offered", "too_large"}
KIND_ORDER = ("video", "silent", "audio")


def load() -> Any:
    # Imported inside each test so every test fails on its own until the module exists.
    import openmedia.choices as module

    return module


def video(
    option_id: int,
    format_id: str,
    *,
    width: int | None = None,
    height: int | None = None,
    vcodec: str | None = "avc1.64001f",
    acodec: str | None = "mp4a.40.2",
    audio: bool = True,
    extension: str = "mp4",
    size: int | None = None,
    size_kind: str | None = None,
    bitrate: float | None = None,
    excluded: bool = False,
) -> FormatOption:
    if size_kind is None:
        size_kind = "unknown" if size is None else "exact"
    return FormatOption(
        option_id=option_id,
        adapter="fixture",
        source_format_id=format_id,
        media_type="video",
        extension=extension,
        mime_type=f"video/{extension}",
        width=width,
        height=height,
        bitrate=bitrate,
        includes_audio=audio,
        size_bytes=size,
        size_kind=size_kind,
        transport_ref={"vcodec": vcodec, "acodec": acodec if audio else "none"},
        availability="excluded" if excluded else "selectable",
        unavailable_reason="File exceeds the delivery limit" if excluded else None,
    )


def silent(option_id: int, format_id: str, **kwargs: Any) -> FormatOption:
    return video(option_id, format_id, audio=False, **kwargs)


def audio(
    option_id: int,
    format_id: str,
    *,
    acodec: str = "mp4a.40.2",
    extension: str = "m4a",
    bitrate: float | None = None,
    size: int | None = None,
    size_kind: str | None = None,
    excluded: bool = False,
) -> FormatOption:
    if size_kind is None:
        size_kind = "unknown" if size is None else "exact"
    return FormatOption(
        option_id=option_id,
        adapter="fixture",
        source_format_id=format_id,
        media_type="audio",
        extension=extension,
        mime_type=f"audio/{extension}",
        bitrate=bitrate,
        size_bytes=size,
        size_kind=size_kind,
        transport_ref={"vcodec": "none", "acodec": acodec},
        availability="excluded" if excluded else "selectable",
        unavailable_reason="File exceeds the delivery limit" if excluded else None,
    )


def image(option_id: int, format_id: str = "image") -> FormatOption:
    return FormatOption(
        option_id=option_id,
        adapter="fixture",
        source_format_id=format_id,
        media_type="image",
        extension="jpg",
        mime_type="image/jpeg",
        width=1080,
        height=1350,
        size_bytes=200_000,
        size_kind="exact",
        transport_ref={"url": "https://example.com/p.jpg"},
    )


def run(choices: Any, options: list[FormatOption], media_kind: MediaKind = MediaKind.VIDEO) -> Any:
    result = choices.choose(options, media_kind=media_kind, max_file_bytes=LIMIT)
    assert_guarantees(choices, options, result)
    return result


def by_kind(choices: Any, result: Any) -> dict[str, FormatOption]:
    return {str(choices.kind_of(option)): option for option in result.options}


def assert_guarantees(choices: Any, options: list[FormatOption], result: Any) -> None:
    kept = tuple(result.options)
    # Subset of input with only option_id changed.
    for option in kept:
        matches = [
            original
            for original in options
            if dataclasses.replace(original, option_id=option.option_id) == option
        ]
        assert matches, f"{option.source_format_id} is not an input option with only option_id changed"
        assert str(option.availability) == "selectable"
    # Ids 0..n-1.
    assert [option.option_id for option in kept] == list(range(len(kept)))
    # At most one per kind, in fixed kind order.
    kinds = [str(choices.kind_of(option)) for option in kept]
    assert len(kinds) == len(set(kinds))
    non_image = [kind for kind in kinds if kind != "image"]
    assert non_image == [kind for kind in KIND_ORDER if kind in non_image]
    # missing values and keys.
    for kind, reason in result.missing.items():
        assert str(kind) in KIND_ORDER
        assert str(kind) not in kinds
        assert reason in ALLOWED_MISSING
    # automatic iff exactly one option.
    assert result.automatic is (len(kept) == 1)


def youtube_like() -> list[FormatOption]:
    options: list[FormatOption] = []

    def add(factory: Any, *args: Any, **kwargs: Any) -> None:
        options.append(factory(len(options), *args, **kwargs))

    heights = {"160": 144, "133": 240, "134": 360, "135": 480, "136": 720, "137": 1080}
    for format_id, height in heights.items():
        add(silent, format_id, width=height * 16 // 9, height=height, vcodec="avc1.4d401f",
            size=height * 20_000, bitrate=height * 3.0)
    add(silent, "247", width=1280, height=720, vcodec="vp09.00.40.08", extension="webm", size=12 * MB)
    add(silent, "398", width=1280, height=720, vcodec="av01.0.05M.08", size=11 * MB)
    add(video, "18", width=640, height=360, vcodec="avc1.42001e", acodec="mp4a.40.2", size=9 * MB, bitrate=500.0)
    add(audio, "140", acodec="mp4a.40.2", extension="m4a", bitrate=129.5, size=3 * MB)
    add(audio, "251", acodec="opus", extension="webm", bitrate=135.8, size=3 * MB)
    add(video, "135+140", width=854, height=480, vcodec="avc1.4d401f", acodec="mp4a.40.2", size=13 * MB, size_kind="estimated", bitrate=1440.0)
    add(video, "136+140", width=1280, height=720, vcodec="avc1.4d401f", acodec="mp4a.40.2", size=17 * MB, size_kind="estimated", bitrate=2160.0)
    add(video, "137+140", width=1920, height=1080, vcodec="avc1.640028", acodec="mp4a.40.2", size=25 * MB, size_kind="estimated", bitrate=3240.0)
    add(video, "398+140", width=1280, height=720, vcodec="av01.0.05M.08", acodec="mp4a.40.2", size=14 * MB, size_kind="estimated", bitrate=2400.0)
    add(video, "247+251", width=1280, height=720, vcodec="vp09.00.40.08", acodec="opus", extension="webm", size=15 * MB, size_kind="estimated", bitrate=2600.0)
    return options


# --- Required test cases (contract table) -------------------------------------------------


def test_youtube_like_picks_720p_merge_720p_avc1_and_best_audio() -> None:
    choices = load()
    result = run(choices, youtube_like())
    kinds = by_kind(choices, result)
    assert list(kinds) == ["video", "silent", "audio"]
    assert kinds["video"].source_format_id == "136+140"
    assert kinds["silent"].source_format_id == "136"
    assert kinds["audio"].source_format_id == "251"
    assert [option.option_id for option in result.options] == [0, 1, 2]
    assert dict(result.missing) == {}
    assert result.automatic is False


def test_vertical_720x1280_is_tier_one() -> None:
    choices = load()
    options = [
        video(0, "v480", width=480, height=854, size=5 * MB),
        video(1, "v1080", width=1080, height=1920, size=20 * MB),
        video(2, "v720", width=720, height=1280, size=10 * MB),
    ]
    result = run(choices, options)
    assert by_kind(choices, result)["video"].source_format_id == "v720"


def test_only_height_known_uses_height_as_shorter_side() -> None:
    choices = load()
    options = [
        video(0, "h1080", height=1080, size=20 * MB),
        video(1, "h360", height=360, size=5 * MB),
    ]
    result = run(choices, options)
    assert by_kind(choices, result)["video"].source_format_id == "h360"


def test_only_width_known_uses_width_as_shorter_side() -> None:
    choices = load()
    options = [
        video(0, "w1080", width=1080, size=20 * MB),
        video(1, "w480", width=480, size=5 * MB),
    ]
    result = run(choices, options)
    assert by_kind(choices, result)["video"].source_format_id == "w480"


def test_linkedin_like_two_unknown_mp4s_pick_lower_option_id() -> None:
    choices = load()
    options = [
        video(0, "mp4-a", vcodec=None, acodec=None),
        video(1, "mp4-b", vcodec=None, acodec=None),
    ]
    result = run(choices, options)
    assert [option.source_format_id for option in result.options] == ["mp4-a"]
    assert result.automatic is True


def test_linkedin_like_lower_option_id_wins_regardless_of_input_order() -> None:
    choices = load()
    options = [
        video(1, "mp4-b", vcodec=None, acodec=None),
        video(0, "mp4-a", vcodec=None, acodec=None),
    ]
    result = run(choices, options)
    assert [option.source_format_id for option in result.options] == ["mp4-a"]
    assert result.options[0].option_id == 0


def test_known_h264_beats_unknown_codec_mp4_even_at_lower_resolution() -> None:
    choices = load()
    options = [
        video(0, "unknown-720", width=1280, height=720, vcodec=None, acodec=None, size=10 * MB),
        video(1, "h264-360", width=640, height=360, size=4 * MB),
    ]
    result = run(choices, options)
    assert by_kind(choices, result)["video"].source_format_id == "h264-360"


def test_unknown_codec_silent_mp4_is_last_resort() -> None:
    choices = load()
    options = [
        silent(0, "unknown-720", width=1280, height=720, vcodec=None, size=10 * MB),
        silent(1, "h264-240", width=426, height=240, size=2 * MB),
    ]
    result = run(choices, options)
    assert by_kind(choices, result)["silent"].source_format_id == "h264-240"


def test_only_1080_and_1440_picks_smallest_in_tier_two() -> None:
    choices = load()
    options = [
        video(0, "1440", width=2560, height=1440, size=40 * MB),
        video(1, "1080", width=1920, height=1080, size=30 * MB),
    ]
    result = run(choices, options)
    assert by_kind(choices, result)["video"].source_format_id == "1080"


def test_oversized_estimated_720p_merge_falls_back_to_480p() -> None:
    choices = load()
    options = [
        video(0, "136+140", width=1280, height=720, size=60 * MB, size_kind="estimated"),
        video(1, "135+140", width=854, height=480, size=30 * MB, size_kind="estimated"),
        video(2, "134+140", width=640, height=360, size=20 * MB, size_kind="estimated"),
    ]
    result = run(choices, options)
    assert by_kind(choices, result)["video"].source_format_id == "135+140"


def test_only_vp9_and_av1_video_offers_no_video_choices() -> None:
    choices = load()
    options = [
        silent(0, "247", width=1280, height=720, vcodec="vp09.00.40.08", extension="webm", size=10 * MB),
        silent(1, "398", width=1280, height=720, vcodec="av01.0.05M.08", size=10 * MB),
        video(2, "398+140", width=1280, height=720, vcodec="av01.0.05M.08", size=12 * MB, size_kind="estimated"),
        video(3, "247+251", width=1280, height=720, vcodec="vp09.00.40.08", acodec="opus",
              extension="webm", size=12 * MB, size_kind="estimated"),
        audio(4, "251", acodec="opus", extension="webm", bitrate=130.0, size=3 * MB),
    ]
    result = run(choices, options)
    kinds = by_kind(choices, result)
    assert list(kinds) == ["audio"]
    assert result.missing["video"] == "not_offered"
    assert result.missing["silent"] == "not_offered"
    assert "audio" not in result.missing


@pytest.mark.parametrize("excluded", [True, False], ids=["router-excluded", "selectable-oversized"])
def test_all_video_candidates_over_limit_are_too_large(excluded: bool) -> None:
    choices = load()
    options = [
        video(0, "136+140", width=1280, height=720, size=70 * MB, size_kind="estimated", excluded=excluded),
        video(1, "18", width=640, height=360, size=55 * MB, excluded=excluded),
        silent(2, "136", width=1280, height=720, size=60 * MB, excluded=excluded),
        audio(3, "140", bitrate=129.0, size=5 * MB),
    ]
    result = run(choices, options)
    kinds = by_kind(choices, result)
    assert list(kinds) == ["audio"]
    assert result.missing["video"] == "too_large"
    assert result.missing["silent"] == "too_large"


def test_linkedin_like_single_muxed_h264_aac_is_automatic() -> None:
    choices = load()
    options = [video(0, "progressive", width=1280, height=720, size=8 * MB)]
    result = run(choices, options)
    assert [str(choices.kind_of(option)) for option in result.options] == ["video"]
    assert result.automatic is True
    assert result.missing["silent"] == "not_offered"
    assert result.missing["audio"] == "not_offered"


def test_silent_source_offers_only_silent_automatically() -> None:
    choices = load()
    options = [
        silent(0, "a", width=640, height=360, size=3 * MB),
        silent(1, "b", width=1280, height=720, size=8 * MB),
    ]
    result = run(choices, options)
    assert [option.source_format_id for option in result.options] == ["b"]
    assert str(choices.kind_of(result.options[0])) == "silent"
    assert result.automatic is True
    assert result.missing["video"] == "not_offered"
    assert result.missing["audio"] == "not_offered"


def test_image_returns_single_image_automatically() -> None:
    choices = load()
    result = run(choices, [image(0)], media_kind=MediaKind.IMAGE)
    assert len(result.options) == 1
    assert str(choices.kind_of(result.options[0])) == "image"
    assert result.options[0].option_id == 0
    assert result.automatic is True
    assert all(str(kind) != "image" for kind in result.missing)


def test_image_with_no_selectable_option_returns_empty_set() -> None:
    choices = load()
    result = run(choices, [], media_kind=MediaKind.IMAGE)
    assert result.options == ()
    assert result.automatic is False


def test_unknown_sizes_only_are_used() -> None:
    choices = load()
    options = [
        video(0, "u360", width=640, height=360),
        video(1, "u720", width=1280, height=720),
    ]
    result = run(choices, options)
    assert by_kind(choices, result)["video"].source_format_id == "u720"


def test_known_size_candidates_preferred_over_unknown_size() -> None:
    choices = load()
    options = [
        video(0, "u720", width=1280, height=720),
        video(1, "k360", width=640, height=360, size=5 * MB),
    ]
    result = run(choices, options)
    assert by_kind(choices, result)["video"].source_format_id == "k360"


# --- Further R2/R3 rules --------------------------------------------------------------------


def test_unknown_dimensions_rank_below_known_dimensions_in_tier_one() -> None:
    choices = load()
    options = [
        video(0, "nodims", size=5 * MB),
        video(1, "240", width=426, height=240, size=2 * MB),
    ]
    result = run(choices, options)
    assert by_kind(choices, result)["video"].source_format_id == "240"


def test_unknown_dimensions_are_tier_one_so_they_beat_tier_two() -> None:
    choices = load()
    options = [
        video(0, "1080", width=1920, height=1080, size=20 * MB),
        video(1, "nodims", size=5 * MB),
    ]
    result = run(choices, options)
    assert by_kind(choices, result)["video"].source_format_id == "nodims"


def test_tie_prefers_higher_bitrate() -> None:
    choices = load()
    options = [
        video(0, "low", width=1280, height=720, size=10 * MB, bitrate=1000.0),
        video(1, "high", width=1280, height=720, size=10 * MB, bitrate=2000.0),
    ]
    result = run(choices, options)
    assert by_kind(choices, result)["video"].source_format_id == "high"


def test_tie_prefers_exact_size_over_estimated() -> None:
    choices = load()
    options = [
        video(0, "estimated", width=1280, height=720, size=10 * MB, size_kind="estimated", bitrate=1000.0),
        video(1, "exact", width=1280, height=720, size=10 * MB, size_kind="exact", bitrate=1000.0),
    ]
    result = run(choices, options)
    assert by_kind(choices, result)["video"].source_format_id == "exact"


def test_full_tie_prefers_lower_option_id() -> None:
    choices = load()
    options = [
        video(3, "later", width=1280, height=720, size=10 * MB, bitrate=1000.0),
        video(2, "earlier", width=1280, height=720, size=10 * MB, bitrate=1000.0),
    ]
    result = run(choices, options)
    assert by_kind(choices, result)["video"].source_format_id == "earlier"


def test_non_mp4_h264_is_not_phone_playable() -> None:
    choices = load()
    options = [video(0, "h264-webm", width=1280, height=720, extension="webm", size=10 * MB)]
    result = run(choices, options)
    assert result.options == ()
    assert result.missing["video"] == "not_offered"


def test_video_with_non_aac_audio_is_not_phone_playable() -> None:
    choices = load()
    options = [video(0, "h264-opus", width=1280, height=720, acodec="opus", size=10 * MB)]
    result = run(choices, options)
    assert result.options == ()
    assert result.missing["video"] == "not_offered"


def test_audio_picks_highest_bitrate_any_extension_that_fits() -> None:
    choices = load()
    options = [
        audio(0, "140", extension="m4a", bitrate=129.0, size=3 * MB),
        audio(1, "251", acodec="opus", extension="webm", bitrate=160.0, size=4 * MB),
        audio(2, "huge", extension="m4a", bitrate=320.0, size=60 * MB),
    ]
    result = run(choices, options)
    assert [option.source_format_id for option in result.options] == ["251"]
    assert result.automatic is True
    assert result.missing["video"] == "not_offered"
    assert result.missing["silent"] == "not_offered"


def test_audio_prefers_known_size_over_unknown_size() -> None:
    choices = load()
    options = [
        audio(0, "unknown", bitrate=320.0),
        audio(1, "known", bitrate=128.0, size=3 * MB),
    ]
    result = run(choices, options)
    assert by_kind(choices, result)["audio"].source_format_id == "known"


def test_audio_all_over_limit_is_too_large() -> None:
    choices = load()
    options = [
        video(0, "18", width=640, height=360, size=9 * MB),
        audio(1, "140", bitrate=129.0, size=60 * MB, excluded=True),
    ]
    result = run(choices, options)
    assert list(by_kind(choices, result)) == ["video"]
    assert result.missing["audio"] == "too_large"


def test_excluded_options_are_never_kept() -> None:
    choices = load()
    options = [
        video(0, "excluded-720", width=1280, height=720, size=10 * MB, excluded=True),
        video(1, "selectable-360", width=640, height=360, size=4 * MB),
    ]
    result = run(choices, options)
    assert by_kind(choices, result)["video"].source_format_id == "selectable-360"


# --- Guarantees -----------------------------------------------------------------------------


def test_kind_of_derives_kind_from_media_type_and_audio() -> None:
    choices = load()
    assert choices.kind_of(video(0, "v")) == choices.ChoiceKind.VIDEO
    assert choices.kind_of(silent(0, "s")) == choices.ChoiceKind.SILENT
    assert choices.kind_of(audio(0, "a")) == choices.ChoiceKind.AUDIO
    assert choices.kind_of(image(0)) == choices.ChoiceKind.IMAGE
    assert [kind.value for kind in choices.ChoiceKind] == ["video", "silent", "audio", "image"]


def test_choice_set_is_frozen() -> None:
    choices = load()
    result = run(choices, youtube_like())
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.automatic = True  # type: ignore[misc]


def test_empty_input_never_raises() -> None:
    choices = load()
    result = run(choices, [])
    assert result.options == ()
    assert result.automatic is False
    assert {str(kind): reason for kind, reason in result.missing.items()} == {
        "video": "not_offered",
        "silent": "not_offered",
        "audio": "not_offered",
    }


def test_all_excluded_input_never_raises() -> None:
    choices = load()
    options = [
        video(0, "v", width=1280, height=720, size=60 * MB, excluded=True),
        silent(1, "s", width=1280, height=720, size=55 * MB, excluded=True),
        audio(2, "a", bitrate=128.0, size=51 * MB, excluded=True),
    ]
    result = run(choices, options)
    assert result.options == ()
    assert result.automatic is False
    assert {str(kind): reason for kind, reason in result.missing.items()} == {
        "video": "too_large",
        "silent": "too_large",
        "audio": "too_large",
    }


def test_choose_is_deterministic_and_independent_of_input_order() -> None:
    choices = load()
    options = youtube_like()
    first = run(choices, options)
    second = run(choices, options)
    assert first == second
    shuffled = list(options)
    random.Random(7).shuffle(shuffled)
    third = run(choices, shuffled)
    assert [option.source_format_id for option in third.options] == [
        option.source_format_id for option in first.options
    ]


def test_input_is_not_mutated() -> None:
    choices = load()
    options = youtube_like()
    snapshot = list(options)
    run(choices, options)
    assert options == snapshot
    assert [option.option_id for option in options] == list(range(len(options)))


@pytest.mark.parametrize(("options", "expected"), [
    ([audio(7, "low", size=10, bitrate=128), audio(9, "high", size=20, bitrate=160)], "high"),
    ([audio(7, "known", size=10, bitrate=128), audio(9, "unknown", bitrate=256)], "known"),
    ([audio(7, "low", bitrate=128), audio(9, "high", bitrate=160)], "high"),
    ([audio(7, "estimated", size=10, size_kind="estimated", bitrate=128), audio(9, "exact", size=10, bitrate=128)], "exact"),
    ([audio(7, "first", size=10, bitrate=128), audio(9, "second", size=10, bitrate=128)], "first"),
])
def test_music_selects_one_ranked_native_audio(options, expected: str) -> None:
    choices = load().choose([video(1, "video", size=10), *options], media_kind="audio", max_file_bytes=LIMIT)
    assert choices.automatic
    assert not choices.missing
    assert [(o.option_id, o.source_format_id) for o in choices.options] == [(0, expected)]


@pytest.mark.parametrize(("options", "reason"), [
    ([], "not_offered"), ([video(0, "big-video", size=LIMIT+1, excluded=True)], "not_offered"),
    ([audio(0, "big-audio", size=LIMIT+1, excluded=True)], "too_large"),
    ([audio(0, "big-audio", size=LIMIT+1), audio(1, "unknown")], "too_large"),
])
def test_empty_music_choices_only_explain_audio(options, reason: str) -> None:
    choices = load().choose(options, media_kind="audio", max_file_bytes=LIMIT)
    assert not choices.automatic
    assert not choices.options
    assert dict(choices.missing) == {load().ChoiceKind.AUDIO: reason}

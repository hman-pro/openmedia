from __future__ import annotations


def test_projected_oversize_and_unknown_merges_are_not_selectable():
    from openmedia.sources.ytdlp import normalize_info
    info = {"extractor_key": "Youtube", "id": "abcDEF12345", "webpage_url": "https://youtu.be/abcDEF12345",
        "formats": [{"format_id": "v", "protocol": "https", "url": "https://cdn.invalid/v", "ext": "mp4", "vcodec": "avc1", "acodec": "none", "filesize_approx": 60_000_000},
                    {"format_id": "a", "protocol": "https", "url": "https://cdn.invalid/a", "ext": "m4a", "vcodec": "none", "acodec": "mp4a", "filesize": 1_000_000}]}
    result = normalize_info(info, max_file_bytes=50_000_000)
    assert all(o.availability == "excluded" for o in result.options if "+" in o.source_format_id)
    del info["formats"][0]["filesize_approx"]
    result = normalize_info(info, max_file_bytes=50_000_000)
    assert all(o.availability == "excluded" for o in result.options if "+" in o.source_format_id)

import json
from pathlib import Path

import pytest

from openmedia.models import Availability, MediaType, SizeKind
from openmedia.sources import ErrorCategory, SourceAdapterError
from openmedia.sources.ytdlp import YTDLP_OPTIONS, normalize_info


FIXTURES = Path(__file__).parents[1] / "fixtures" / "ytdlp"


def load(name: str) -> dict[str, object]:
    return json.loads((FIXTURES / name).read_text())


@pytest.mark.parametrize(
    ("name", "platform"),
    [
        ("youtube-video.json", "youtube"),
        ("linkedin-video.json", "linkedin"),
        ("instagram-video.json", "instagram"),
    ],
)
def test_normalizes_three_explicit_extractors_without_downloading(name: str, platform: str) -> None:
    result = normalize_info(load(name), max_file_bytes=50_000_000)
    assert result.metadata.platform == platform
    assert result.options
    assert all(option.source_format_id not in {"best", "bestvideo+bestaudio"} for option in result.options)
    assert YTDLP_OPTIONS["skip_download"] is True
    assert YTDLP_OPTIONS["extractor_args"] == {"youtube": {"player_client": ["default", "android"]}}
    assert YTDLP_OPTIONS["allowed_extractors"] == ["Youtube", "LinkedIn", "Instagram"]


def test_offers_native_audio_silent_video_muxed_and_compatible_merge() -> None:
    result = normalize_info(load("youtube-video.json"), max_file_bytes=50_000_000)
    by_id = {option.source_format_id: option for option in result.options}
    assert by_id["18"].includes_audio is True
    assert by_id["137"].includes_audio is False
    assert by_id["140"].media_type is MediaType.AUDIO
    assert by_id["137+140"].includes_audio is True
    assert by_id["137+140"].extension == "mp4"
    assert by_id["137+140"].size_bytes == 2500
    assert "hls" not in by_id


def test_rejects_incompatible_pairs_and_excludes_exact_oversize() -> None:
    info = load("youtube-video.json")
    formats = info["formats"]
    assert isinstance(formats, list)
    formats[1]["vcodec"] = "vp9"
    result = normalize_info(info, max_file_bytes=1200)
    by_id = {option.source_format_id: option for option in result.options}
    assert "137+140" not in by_id
    assert by_id["137"].availability is Availability.EXCLUDED
    assert by_id["137"].unavailable_reason


def test_rejects_playlist_and_live_wrappers() -> None:
    for change in ({"_type": "playlist", "entries": [{}]}, {"live_status": "is_live"}):
        info = load("youtube-video.json")
        info.update(change)
        with pytest.raises(SourceAdapterError) as caught:
            normalize_info(info, max_file_bytes=50_000_000)
        assert caught.value.category is ErrorCategory.UNSUPPORTED_COLLECTION


def test_estimated_and_unknown_sizes_remain_distinct() -> None:
    linked = normalize_info(load("linkedin-video.json"), max_file_bytes=50_000_000)
    insta = normalize_info(load("instagram-video.json"), max_file_bytes=50_000_000)
    assert linked.options[0].size_kind is SizeKind.ESTIMATED
    assert insta.options[0].size_kind is SizeKind.UNKNOWN


def test_unknown_codecs_are_present_not_absent() -> None:
    result = normalize_info(load("linkedin-video-progressive.json"), max_file_bytes=50_000_000)
    assert [option.source_format_id for option in result.options if option.availability is Availability.SELECTABLE] != []
    assert {option.source_format_id for option in result.options} == {"0", "1"}
    for option in result.options:
        assert option.media_type is MediaType.VIDEO
        assert option.includes_audio is True
        assert option.availability is Availability.SELECTABLE
        assert option.size_kind is SizeKind.UNKNOWN
        assert not option.transport_ref.get("vcodec")
        assert not option.transport_ref.get("acodec")
        assert option.extension == "mp4"
    # The two renditions stay distinguishable by their fields: native bitrate, not a label.
    assert len({option.bitrate for option in result.options}) == 2
    assert all(option.bitrate for option in result.options)


def test_unknown_codecs_never_pair_for_merging() -> None:
    info = {"extractor_key": "Youtube", "id": "abcDEF12345", "webpage_url": "https://youtu.be/abcDEF12345",
        "formats": [{"format_id": "v", "protocol": "https", "url": "https://cdn.invalid/v", "ext": "mp4", "vcodec": None, "acodec": "none", "filesize": 1_000},
                    {"format_id": "a", "protocol": "https", "url": "https://cdn.invalid/a", "ext": "m4a", "vcodec": "none", "acodec": None, "filesize": 1_000}]}
    result = normalize_info(info, max_file_bytes=50_000_000)
    assert {option.source_format_id for option in result.options} == {"v", "a"}


def _dubbed_info(languages: int) -> dict[str, object]:
    # Mirrors a live auto-dubbed YouTube response: every audio stream exists once per language,
    # and yt-dlp marks the original track with the highest language_preference (10 vs -1).
    videos = [{"format_id": f"v{i}", "protocol": "https", "url": f"https://cdn.invalid/v{i}", "ext": "mp4",
               "vcodec": "avc1.4d401f", "acodec": "none", "width": 640, "height": 360, "tbr": 500 + i, "filesize": 1_000}
              for i in range(3)]
    audios = [{"format_id": f"140-{n}", "protocol": "https", "url": f"https://cdn.invalid/a{n}", "ext": "m4a",
               "vcodec": "none", "acodec": "mp4a.40.2", "abr": 129 + n, "filesize": 1_000,
               "language": "en-US" if n == 0 else f"x{n}", "language_preference": 10 if n == 0 else -1}
              for n in range(languages)]
    return {"extractor_key": "Youtube", "id": "abcDEF12345", "webpage_url": "https://youtu.be/abcDEF12345",
            "formats": videos + audios}


def test_dubbed_audio_tracks_are_dropped_in_favor_of_the_original() -> None:
    result = normalize_info(_dubbed_info(languages=40), max_file_bytes=50_000_000)
    ids = {option.source_format_id for option in result.options}
    # The dubs carry a higher bitrate here, so a bitrate-only pick would choose one of them.
    assert {i for i in ids if "140-" in i} == {"140-0", "v0+140-0", "v1+140-0", "v2+140-0"}


def test_many_audio_languages_do_not_multiply_merge_pairs() -> None:
    # A live response with 100 dubbed audio streams produced 840 pairs, a 3 MB worker result
    # that overran the 2 MiB protocol line limit and failed inspection.
    few = normalize_info(_dubbed_info(languages=2), max_file_bytes=50_000_000)
    many = normalize_info(_dubbed_info(languages=100), max_file_bytes=50_000_000)
    assert len(many.options) == len(few.options)


def test_audio_without_language_preference_is_kept_unfiltered() -> None:
    info = _dubbed_info(languages=3)
    for item in info["formats"]:
        item.pop("language_preference", None)
    result = normalize_info(info, max_file_bytes=50_000_000)
    assert sum(1 for option in result.options if option.media_type is MediaType.AUDIO) == 3


def test_youtube_http_chunk_size_is_kept_for_ranged_download() -> None:
    info = _dubbed_info(languages=1)
    for item in info["formats"]:
        item["downloader_options"] = {"http_chunk_size": 10_485_760}
    result = normalize_info(info, max_file_bytes=50_000_000)
    by_id = {option.source_format_id: option for option in result.options}
    assert by_id["140-0"].transport_ref["range_bytes"] == 10_485_760
    assert by_id["v0+140-0"].transport_ref["video_range_bytes"] == 10_485_760
    assert by_id["v0+140-0"].transport_ref["audio_range_bytes"] == 10_485_760


def test_formats_without_chunk_size_download_whole() -> None:
    result = normalize_info(_dubbed_info(languages=1), max_file_bytes=50_000_000)
    by_id = {option.source_format_id: option for option in result.options}
    assert by_id["140-0"].transport_ref.get("range_bytes") is None
    assert by_id["v0+140-0"].transport_ref.get("video_range_bytes") is None

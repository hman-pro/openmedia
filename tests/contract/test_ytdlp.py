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


# --------------------------------------------------------------------------------------
# US2 (004): post addresses whose trailing code is not four word characters (research R7).
# The real yt-dlp extraction runs against a fake guarded transport; nothing reaches the network.
# --------------------------------------------------------------------------------------

import inspect as _inspect
import time
from types import SimpleNamespace
from unittest.mock import Mock
from urllib.parse import urlsplit

from openmedia.models import MediaMetadata
from openmedia.sources import InspectInput, SourceRouter, TransportResponse


LINKEDIN_FIXTURES = Path(__file__).parents[1] / "fixtures" / "linkedin"
HYPHEN_CODE_POST = "https://www.linkedin.com/posts/sample-author_sample-text-ugcPost-7508434034927017984-lwx-/"
HYPHEN_CODE_ID = "7508434034927017984"
PICTURE_POST_PAGE = (
    "<!doctype html><html><head><title>Sample post</title>"
    '<meta property="og:title" content="Sample post"></head>'
    "<body><main><img src=\"https://media.example.invalid/picture.jpg\"></main></body></html>"
)


class PageTransport:
    """Serves one HTML page for the post address and 404 for anything else, like MetadataHTTP expects."""

    def __init__(self, page: str) -> None:
        self.page = page.encode()
        self.on_request = self.on_response = None
        self.fetches: list[str] = []

    def fetch(self, url, **kwargs):
        self.fetches.append(url)
        if self.on_request:
            self.on_request()
        served = urlsplit(url)._replace(query="", fragment="").geturl() == HYPHEN_CODE_POST
        status = 200 if served else 404
        if self.on_response:
            self.on_response(status, {})
        return TransportResponse(url, status, {"content-type": "text/html; charset=utf-8"}, self.page if served else b"")

    def head(self, url, **kwargs):  # pragma: no cover - inspection never issues HEAD here
        raise AssertionError("inspection must not HEAD media")

    def download(self, url, destination, **kwargs):  # pragma: no cover
        raise AssertionError("inspection must not download media")


def _library_rate():
    return SimpleNamespace(acquire=Mock(), limited=Mock(), observe=Mock())


def _inspect_input(tmp_path: Path, url: str) -> InspectInput:
    return InspectInput(source_url=url, request_id="a" * 32, work_directory=tmp_path,
        deadline=time.monotonic() + 30, metadata_limit=65_536)


def test_linkedin_post_extractor_matches_hyphen_code_by_recognizer() -> None:
    from yt_dlp.extractor.linkedin import LinkedInIE

    from openmedia.sources.ytdlp import _linkedin_post_extractor

    extractor = _linkedin_post_extractor()
    assert issubclass(extractor, LinkedInIE)
    assert extractor.suitable(HYPHEN_CODE_POST) is True
    assert extractor._match_id(HYPHEN_CODE_POST) == HYPHEN_CODE_ID
    # The stock pattern still rejects the address; only our subclass widens the match.
    assert LinkedInIE.suitable(HYPHEN_CODE_POST) is False
    assert extractor.suitable("https://www.linkedin.com/in/someone/") is False
    assert extractor.suitable("https://www.youtube.com/watch?v=abcDEF12345") is False


def test_ytdlp_adapter_inspects_hyphen_code_video_post(tmp_path: Path) -> None:
    from openmedia.sources.ytdlp import YtDlpAdapter

    page = (LINKEDIN_FIXTURES / "linkedin-video-post-hyphen-code.html").read_text()
    transport = PageTransport(page)

    result = YtDlpAdapter().inspect(_inspect_input(tmp_path, HYPHEN_CODE_POST),
        transport=transport, rate_control=_library_rate())

    assert result.metadata.platform == "linkedin"
    assert result.metadata.media_id == HYPHEN_CODE_ID
    videos = [option for option in result.options if option.media_type is MediaType.VIDEO]
    assert len(videos) == 2
    assert {urlsplit(option.transport_ref["url"]).hostname for option in videos} == {"media.example.invalid"}
    assert all(urlsplit(url).hostname == "www.linkedin.com" for url in transport.fetches)


def test_linkedin_ie_still_reads_its_id_through_match_id() -> None:
    from yt_dlp.extractor.linkedin import LinkedInIE

    source = _inspect.getsource(LinkedInIE._real_extract)
    assert "self._match_id(url)" in source, (
        "LinkedInIE._real_extract no longer calls self._match_id(url); OpenMediaLinkedInPostIE "
        "relies on it. Re-check research R7 (specs/004-linkedin-share-links/research.md) before "
        "upgrading yt-dlp."
    )


class _StubImageAdapter:
    name = "linkedin_image"

    def __init__(self) -> None:
        self.requests: list[InspectInput] = []

    def inspect(self, request, *, transport, rate_control):
        from openmedia.models import FormatOption
        from openmedia.sources import InspectResult

        self.requests.append(request)
        metadata = MediaMetadata(platform="linkedin", canonical_url=request.source_url,
            media_id=HYPHEN_CODE_ID, media_kind="image")
        option = FormatOption(option_id=0, adapter="linkedin_image", source_format_id="image-0",
            media_type="image", extension="jpg", mime_type="image/jpeg",
            transport_ref={"url": "https://media.example.invalid/picture.jpg"})
        return InspectResult(metadata, (option,))

    def download(self, request, **kwargs):  # pragma: no cover
        raise AssertionError("download is not expected during inspect")


def test_hyphen_code_picture_post_is_unavailable_and_falls_back_to_image(tmp_path: Path) -> None:
    from openmedia.sources.ytdlp import YtDlpAdapter

    transport = PageTransport(PICTURE_POST_PAGE)
    with pytest.raises(SourceAdapterError) as caught:
        YtDlpAdapter().inspect(_inspect_input(tmp_path, HYPHEN_CODE_POST),
            transport=transport, rate_control=_library_rate())
    assert caught.value.category is ErrorCategory.UNAVAILABLE
    # yt-dlp really fetched the post page: the failure is "no video", not "unsupported URL".
    assert [urlsplit(url)._replace(query="").geturl() for url in transport.fetches] == [HYPHEN_CODE_POST]

    image = _StubImageAdapter()
    router = SourceRouter(ytdlp=YtDlpAdapter(), instagram=_StubImageAdapter(), linkedin=image)
    result = router.inspect(_inspect_input(tmp_path, HYPHEN_CODE_POST),
        transport=PageTransport(PICTURE_POST_PAGE), rate_control=_library_rate())
    assert [request.source_url for request in image.requests] == [HYPHEN_CODE_POST]
    assert result.options[0].adapter == "linkedin_image"


def music_route():
    from openmedia.sources import SourceRoute
    return SourceRoute("youtube", "fixtureYT01", "https://music.youtube.com/watch?v=fixtureYT01", "audio")


def test_music_normalization_keeps_trusted_identity_and_only_native_audio() -> None:
    from openmedia.models import MediaKind
    result = normalize_info(load("youtube-music.json"), max_file_bytes=600, source_route=music_route())
    assert result.metadata.media_kind is MediaKind.AUDIO
    assert result.metadata.canonical_url == music_route().canonical_url
    assert {o.source_format_id for o in result.options} == {"140", "251"}
    assert all(o.media_type is MediaType.AUDIO for o in result.options)
    assert next(o for o in result.options if o.source_format_id == "251").availability is Availability.EXCLUDED
    assert normalize_info(load("youtube-music.json"), max_file_bytes=50_000_000).metadata.media_kind == "video"


@pytest.mark.parametrize(("change", "category"), [
    ({"id": "wrongID1234"}, ErrorCategory.INVALID_SOURCE_RESPONSE),
    ({"extractor_key": "Instagram"}, ErrorCategory.INVALID_SOURCE_RESPONSE),
    ({"entries": [{}]}, ErrorCategory.UNSUPPORTED_COLLECTION),
    ({"live_status": "is_live"}, ErrorCategory.UNSUPPORTED_COLLECTION),
    ({"formats": []}, ErrorCategory.NO_NATIVE_AUDIO),
])
def test_music_checks_identity_and_finished_item_before_audio(change, category) -> None:
    info = load("youtube-music.json"); info.update(change)
    with pytest.raises(SourceAdapterError) as caught:
        normalize_info(info, max_file_bytes=50_000_000, source_route=music_route())
    assert caught.value.category is category


@pytest.mark.parametrize("context", ["", "&list=PLexample&index=2&radio=1&si=share&t=42"])
def test_music_adapter_passes_canonical_route_and_shared_youtube_rate_bucket(tmp_path, monkeypatch, context) -> None:
    from openmedia.sources import InspectInput
    from openmedia.sources.ytdlp import YtDlpAdapter
    import yt_dlp

    calls = []
    def extract(self, url, download):
        calls.append((url, download))
        return load("youtube-music.json")
    monkeypatch.setattr(yt_dlp.YoutubeDL, "extract_info", extract)
    class Rate:
        def acquire(self, platform, request_class, *, deadline):
            calls.append((platform, request_class, deadline))
    request = InspectInput(source_url=music_route().canonical_url + context,
        request_id="0123456789abcdef0123456789abcdef", work_directory=tmp_path, deadline=100)
    from types import SimpleNamespace
    result = YtDlpAdapter().inspect(request, transport=SimpleNamespace(), rate_control=Rate())
    assert calls == [("youtube", "metadata", 100), (music_route().canonical_url, False)]
    assert result.metadata.media_kind == "audio"
    assert all(o.media_type == "audio" for o in result.options)


@pytest.mark.parametrize(("change", "category"), [
    ({"formats": []}, ErrorCategory.NO_NATIVE_AUDIO),
    ({"formats": None}, ErrorCategory.NO_NATIVE_AUDIO),
    ({"formats": {"bad": "shape"}}, ErrorCategory.INVALID_SOURCE_RESPONSE),
    ({"formats": [None]}, ErrorCategory.INVALID_SOURCE_RESPONSE),
    ({"formats": ["malformed"]}, ErrorCategory.INVALID_SOURCE_RESPONSE),
    ({"formats": [None, {"vcodec": "none"}]}, ErrorCategory.INVALID_SOURCE_RESPONSE),
    ({"live_status": "is_upcoming"}, ErrorCategory.UNSUPPORTED_COLLECTION),
    ({"live_status": "post_live"}, ErrorCategory.UNSUPPORTED_COLLECTION),
    ({"id": "wrongID1234", "formats": []}, ErrorCategory.INVALID_SOURCE_RESPONSE),
    ({"extractor_key": "LinkedIn", "formats": []}, ErrorCategory.INVALID_SOURCE_RESPONSE),
])
def test_music_failure_meanings_survive_audio_intent(change, category) -> None:
    info = load("youtube-music.json"); info.update(change)
    with pytest.raises(SourceAdapterError) as caught:
        normalize_info(info, max_file_bytes=50_000_000, source_route=music_route())
    assert caught.value.category is category


def test_music_video_only_is_no_audio_and_fitting_video_does_not_hide_oversize_audio() -> None:
    from openmedia.choices import choose, ChoiceKind
    info = load("youtube-music.json")
    info["formats"] = [f for f in info["formats"] if f["vcodec"] != "none"]
    with pytest.raises(SourceAdapterError) as caught:
        normalize_info(info, max_file_bytes=50_000_000, source_route=music_route())
    assert caught.value.category is ErrorCategory.NO_NATIVE_AUDIO
    info = load("youtube-music.json")
    for item in info["formats"]:
        if item["vcodec"] == "none":
            item["filesize"] = 50_000_001
    result = normalize_info(info, max_file_bytes=50_000_000, source_route=music_route())
    assert all(o.media_type == "audio" and o.availability == "excluded" for o in result.options)
    assert dict(choose(result.options, media_kind="audio", max_file_bytes=50_000_000).missing) == {ChoiceKind.AUDIO: "too_large"}


@pytest.mark.parametrize("category", [ErrorCategory.UNAVAILABLE, ErrorCategory.RATE_LIMITED, ErrorCategory.TIMEOUT])
def test_music_adapter_does_not_relabel_source_errors(tmp_path, monkeypatch, category) -> None:
    import yt_dlp
    from types import SimpleNamespace
    from openmedia.sources import InspectInput
    from openmedia.sources.ytdlp import YtDlpAdapter
    def unavailable(*args, **kwargs):
        raise SourceAdapterError(category, stage="inspection")
    monkeypatch.setattr(yt_dlp.YoutubeDL, "extract_info", unavailable)
    with pytest.raises(SourceAdapterError) as caught:
        YtDlpAdapter().inspect(InspectInput(source_url=music_route().canonical_url,
            request_id="a" * 32, work_directory=tmp_path, deadline=100),
            transport=SimpleNamespace(), rate_control=SimpleNamespace(acquire=lambda *args, **kwargs: None))
    assert caught.value.category is category


@pytest.mark.parametrize("formats", [[], [{"protocol": "m3u8", "format_id": "x", "url": "https://cdn.invalid/audio", "vcodec": "none", "acodec": "aac", "ext": "m4a"}]])
def test_valid_music_without_supported_native_audio_remains_no_audio(formats):
    info = load("youtube-music.json")
    info["formats"] = formats
    with pytest.raises(SourceAdapterError) as caught:
        normalize_info(info, max_file_bytes=50_000_000, source_route=music_route())
    assert caught.value.category is ErrorCategory.NO_NATIVE_AUDIO


@pytest.mark.parametrize("row", [None, "malformed"])
def test_nonmusic_malformed_format_rows_keep_existing_filtering(row):
    info = load("youtube-video.json")
    expected = normalize_info(info, max_file_bytes=50_000_000)
    info["formats"].append(row)
    assert normalize_info(info, max_file_bytes=50_000_000) == expected

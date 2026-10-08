from __future__ import annotations

import pytest

from openmedia.bot import ONE_LINK_GUIDANCE, InputError, parse_link_message
from openmedia.sources import (
    ErrorCategory,
    SourceAdapterError,
    SourceRoute,
    normalize_supported_link,
    recognize_source_url,
    supported_urls_in_text,
)


def test_counts_only_supported_platform_links_with_surrounding_text() -> None:
    text = (
        "Try https://example.com/ignored then "
        "https://youtu.be/abcDEF12345, and https://instagram.com/p/DdExample1/."
    )
    assert supported_urls_in_text(text) == (
        "https://youtu.be/abcDEF12345",
        "https://instagram.com/p/DdExample1/",
    )


@pytest.mark.parametrize(
    ("url", "platform", "identity"),
    [
        ("https://youtu.be/abcDEF12345", "youtube", "abcDEF12345"),
        ("https://www.youtube.com/watch?v=abcDEF12345", "youtube", "abcDEF12345"),
        ("https://www.linkedin.com/posts/example_activity-7505650038253965312-x", "linkedin", "7505650038253965312"),
        ("https://www.instagram.com/p/DdExample1/", "instagram", "DdExample1"),
        ("https://www.instagram.com/alice/reel/DdExample2/", "instagram", "DdExample2"),
    ],
)
def test_recognizes_canonical_single_item_routes(url: str, platform: str, identity: str) -> None:
    route = recognize_source_url(url)
    assert route.platform == platform
    assert route.media_id == identity
    assert route.canonical_url.startswith("https://")


LI = "https://www.linkedin.com"


@pytest.mark.parametrize(
    ("url", "canonical", "urn_kind", "route_kind"),
    [
        # Real "Copy link to post" shape: the slug names the URN type; tracking query is dropped.
        (f"{LI}/posts/someone_words-ugcPost-7504928712690176000-AbCd?utm_source=share&rcm=x",
            f"{LI}/posts/someone_words-ugcPost-7504928712690176000-AbCd", "ugcPost", "post"),
        ("https://linkedin.com/posts/someone_words-activity-7275224371206504449-Wx9z/",
            f"{LI}/posts/someone_words-activity-7275224371206504449-Wx9z", "activity", "post"),
        (f"{LI}/posts/someone_words-share-7505650038253965312-Qq1_",
            f"{LI}/posts/someone_words-share-7505650038253965312-Qq1_", "share", "post"),
        # Like yt-dlp's greedy pattern, the identity is the last type/ID pair before the suffix.
        (f"{LI}/posts/x-ugcPost-12345678-activity-7505650038253965312-Wxyz",
            f"{LI}/posts/x-ugcPost-12345678-activity-7505650038253965312-Wxyz", "activity", "post"),
        (f"{LI}/feed/update/urn:li:activity:7275224371206504449/?utm_source=x",
            f"{LI}/feed/update/urn:li:activity:7275224371206504449", "activity", "post"),
        # The pinned yt-dlp LinkedInIE matches neither of these, so only the image path applies.
        (f"{LI}/feed/update/urn:li:ugcPost:7504928712690176000",
            f"{LI}/feed/update/urn:li:ugcPost:7504928712690176000", "ugcPost", "embed"),
        (f"{LI}/feed/update/urn%3Ali%3Ashare%3A7505650038253965312",
            f"{LI}/feed/update/urn:li:share:7505650038253965312", "share", "embed"),
    ],
)
def test_linkedin_routes_keep_the_urn_type_and_are_stable(url, canonical, urn_kind, route_kind) -> None:
    route = recognize_source_url(url)
    assert (route.canonical_url, route.urn_kind, route.route_kind) == (canonical, urn_kind, route_kind)
    assert route.media_id.isdigit() and route.media_id in canonical
    # Workers and refresh re-recognize the canonical URL; it must name the same object.
    assert recognize_source_url(route.canonical_url) == route


@pytest.mark.parametrize(
    "url",
    [
        f"{LI}/posts/",
        f"{LI}/posts/a/b-activity-7505650038253965312-AbCd",
        f"{LI}/feed/update/urn:li:group:7505650038253965312",
    ],
)
def test_linkedin_routes_without_a_single_post_identity_are_rejected(url) -> None:
    with pytest.raises(SourceAdapterError) as caught:
        recognize_source_url(url)
    assert caught.value.category is ErrorCategory.UNSUPPORTED_URL


HYPHEN_CODE = f"{LI}/posts/sample-author_sample-text-ugcPost-7508434034927017984-lwx-"


@pytest.mark.parametrize(
    ("url", "canonical", "urn_kind", "media_id"),
    [
        # Research R6: the trailing code may contain hyphens, including a trailing one.
        (f"{HYPHEN_CODE}/", HYPHEN_CODE, "ugcPost", "7508434034927017984"),
        (f"{HYPHEN_CODE}/?utm_source=x&rcm=y", HYPHEN_CODE, "ugcPost", "7508434034927017984"),
        # A digit-heavy prefix that contains a type word still takes the rightmost one.
        (f"{LI}/posts/share-fan-8346721bb_x-ugcPost-7508434034927017984-lwx-",
            f"{LI}/posts/share-fan-8346721bb_x-ugcPost-7508434034927017984-lwx-", "ugcPost", "7508434034927017984"),
        # A post with no text: the author slug meets the type word with "_", not "-".
        (f"{LI}/posts/sample-author_share-7508570327892013056-d5q8/",
            f"{LI}/posts/sample-author_share-7508570327892013056-d5q8", "share", "7508570327892013056"),
        # Telegram may pass a pasted non-Latin slug raw or percent-encoded.
        (f"{LI}/posts/sample-author_سلام-دنیا-share-7508424761698410497-2cX9",
            f"{LI}/posts/sample-author_سلام-دنیا-share-7508424761698410497-2cX9", "share", "7508424761698410497"),
        (f"{LI}/posts/sample-author_%D8%B3%D9%84%D8%A7%D9%85-share-7508424761698410497-2cX9",
            f"{LI}/posts/sample-author_%D8%B3%D9%84%D8%A7%D9%85-share-7508424761698410497-2cX9",
            "share", "7508424761698410497"),
    ],
)
def test_linkedin_post_slug_accepts_any_trailing_code(url, canonical, urn_kind, media_id) -> None:
    route = recognize_source_url(url)
    assert (route.canonical_url, route.urn_kind, route.media_id, route.route_kind) == (
        canonical, urn_kind, media_id, "post",
    )
    assert recognize_source_url(route.canonical_url) == route


def test_linkedin_post_identity_ignores_the_trailing_code() -> None:
    lwx = recognize_source_url(f"{HYPHEN_CODE}/")
    abcd = recognize_source_url(f"{LI}/posts/sample-author_sample-text-ugcPost-7508434034927017984-abcd/")
    assert (lwx.urn_kind, lwx.media_id) == (abcd.urn_kind, abcd.media_id)
    assert lwx.canonical_url != abcd.canonical_url


@pytest.mark.parametrize(
    "url",
    [
        f"{LI}/posts/sample-author_sample-text-ugcPost-7508434034927017984-{'a' * 33}",
        f"{LI}/posts/sample-author_sample-text-ugcPost-7508434034927017984-lw.x",
    ],
)
def test_linkedin_post_slug_rejects_a_long_or_dotted_code(url) -> None:
    with pytest.raises(SourceAdapterError) as caught:
        recognize_source_url(url)
    assert caught.value.category is ErrorCategory.UNSUPPORTED_URL


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/playlist?list=abc",
        "https://www.youtube.com/live/abcDEF12345",
    ],
)
def test_rejects_collection_and_live_routes(url: str) -> None:
    with pytest.raises(SourceAdapterError) as caught:
        recognize_source_url(url)
    assert caught.value.category is ErrorCategory.UNSUPPORTED_COLLECTION


SHORT = "https://lnkd.in/p/dMhfr6kG"


@pytest.mark.parametrize(
    "raw",
    [
        "https://lnkd.in/p/dMhfr6kG",
        "http://lnkd.in/p/dMhfr6kG",
        "lnkd.in/p/dMhfr6kG",
        "https://lnkd.in/p/dMhfr6kG?trk=x",
    ],
)
def test_linkedin_short_link_is_recognized_and_query_dropped(raw: str) -> None:
    # Bare and http forms reach recognition only through the same normalization the bot uses.
    link = normalize_supported_link(raw)
    assert link is not None
    assert recognize_source_url(link) == SourceRoute("linkedin", "dMhfr6kG", SHORT, "short_link", None)


@pytest.mark.parametrize("code", ["a", "A-z_09", "x" * 32])
def test_linkedin_short_code_alphabet_and_length(code: str) -> None:
    route = recognize_source_url(f"https://lnkd.in/p/{code}")
    assert (route.media_id, route.canonical_url, route.route_kind) == (
        code, f"https://lnkd.in/p/{code}", "short_link",
    )


@pytest.mark.parametrize(
    "url",
    [
        f"{SHORT}#frag",
        "https://lnkd.in/p/" + "x" * 33,
        "https://lnkd.in/p/",
        "https://lnkd.in/p/bad.code",
        "https://lnkd.in/dMhfr6kG",
        "https://lnkd.in/p/a/b",
        "https://www.lnkd.in/p/dMhfr6kG",
    ],
)
def test_linkedin_short_link_outside_the_p_route_is_rejected(url: str) -> None:
    with pytest.raises(SourceAdapterError) as caught:
        recognize_source_url(url)
    assert caught.value.category is ErrorCategory.UNSUPPORTED_URL


def test_short_link_counts_as_a_link_so_two_links_get_one_link_guidance() -> None:
    text = "see https://lnkd.in/p/dMhfr6kG and https://youtu.be/abcdefghijk"
    assert supported_urls_in_text(text) == (SHORT, "https://youtu.be/abcdefghijk")
    with pytest.raises(InputError) as caught:
        parse_link_message(text, chat_type="private")
    assert str(caught.value) == ONE_LINK_GUIDANCE


@pytest.mark.parametrize("raw", [
    "https://music.youtube.com/watch?v=abcDEF12345",
    "http://music.youtube.com/watch?v=abcDEF12345",
    "music.youtube.com/watch?v=abcDEF12345",
])
def test_plain_music_link_retains_audio_intent(raw: str) -> None:
    normalized = normalize_supported_link(raw)
    assert normalized is not None
    route = recognize_source_url(normalized)
    assert route == SourceRoute("youtube", "abcDEF12345",
        "https://music.youtube.com/watch?v=abcDEF12345", "audio")
    assert recognize_source_url(route.canonical_url) == route
    assert supported_urls_in_text(f"Track {raw}") == (normalized,)


@pytest.mark.parametrize("url", [
    "https://music.youtube.com/watch?v=", "https://music.youtube.com/watch?v=bad",
    "https://music.youtube.com/watch?v=abcDEF12345&v=abcDEF12345",
    "https://music.youtube.com/watch?v=abcDEF12345&v=",
    "https://music.youtube.com/watch?v=abcDEF12345#fragment",
    "https://user:password@music.youtube.com/watch?v=abcDEF12345",
    "https://music.youtube.com.evil.invalid/watch?v=abcDEF12345",
])
def test_plain_music_link_refuses_invalid_identity(url: str) -> None:
    with pytest.raises(SourceAdapterError) as caught:
        recognize_source_url(url)
    assert caught.value.category is ErrorCategory.UNSUPPORTED_URL


def test_music_counts_toward_one_link_limit_and_ordinary_youtube_stays_video() -> None:
    links = supported_urls_in_text("music.youtube.com/watch?v=abcDEF12345 https://youtu.be/abcDEF12345")
    assert len(links) == 2
    assert recognize_source_url(links[1]).route_kind == "video"


@pytest.mark.parametrize("context", ["list=PLexample", "list=PLexample&index=2&radio=1&si=share&t=42", "t=42", "si=share"])
def test_music_listening_context_names_one_complete_track(context: str) -> None:
    route = recognize_source_url(f"https://music.youtube.com/watch?v=abcDEF12345&{context}")
    assert route == SourceRoute("youtube", "abcDEF12345", "https://music.youtube.com/watch?v=abcDEF12345", "audio")


@pytest.mark.parametrize(("path", "category"), [
    ("/playlist?list=PLexample", ErrorCategory.MUSIC_COLLECTION),
    ("/playlist", ErrorCategory.MUSIC_COLLECTION),
    ("/playlist?v=abcDEF12345", ErrorCategory.MUSIC_COLLECTION),
    ("/watch?list=PLexample", ErrorCategory.MUSIC_COLLECTION),
    ("/browse/MPREb_album", ErrorCategory.MUSIC_COLLECTION),
    ("/browse/artist", ErrorCategory.UNSUPPORTED_URL),
    ("/search?q=track", ErrorCategory.UNSUPPORTED_URL),
    ("/artist/artist", ErrorCategory.UNSUPPORTED_URL),
    ("/", ErrorCategory.UNSUPPORTED_URL),
    ("/watch?v=&list=PLexample", ErrorCategory.UNSUPPORTED_URL),
    ("/watch?v=bad&list=PLexample", ErrorCategory.UNSUPPORTED_URL),
    ("/watch?v=abcDEF12345&v=abcDEF12345&list=PLexample", ErrorCategory.UNSUPPORTED_URL),
    ("/watch?v=abcDEF12345&v=otherID1234&list=PLexample", ErrorCategory.UNSUPPORTED_URL),
    ("/watch?v=&v=&list=PLexample", ErrorCategory.UNSUPPORTED_URL),
])
def test_music_collection_and_malformed_precedence(path: str, category: ErrorCategory) -> None:
    with pytest.raises(SourceAdapterError) as caught:
        recognize_source_url("https://music.youtube.com" + path)
    assert caught.value.category is category


def test_ordinary_youtube_list_remains_unsupported_collection() -> None:
    with pytest.raises(SourceAdapterError) as caught:
        recognize_source_url("https://www.youtube.com/watch?v=abcDEF12345&list=PLexample")
    assert caught.value.category is ErrorCategory.UNSUPPORTED_COLLECTION

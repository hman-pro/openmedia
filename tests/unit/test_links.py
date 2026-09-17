from __future__ import annotations

import pytest

from openmedia.sources import (
    ErrorCategory,
    SourceAdapterError,
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

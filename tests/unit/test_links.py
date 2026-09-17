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

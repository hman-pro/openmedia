from __future__ import annotations

from pathlib import Path

import pytest

from openmedia.sources import ErrorCategory, SourceAdapterError
from openmedia.sources.linkedin import parse_embed


FIXTURES = Path(__file__).parents[1] / "fixtures" / "linkedin"
IDENTITY = "7505650038253965312"
URL = f"https://www.linkedin.com/embed/feed/update/urn:li:share:{IDENTITY}"


def read(name: str) -> str:
    return (FIXTURES / name).read_text()


def test_selects_exactly_one_explicit_feed_attachment() -> None:
    result = parse_embed(read("linkedin-image-single.html"), requested_activity_id=IDENTITY, fetched_url=URL)
    assert result.metadata.media_id == IDENTITY
    assert result.metadata.title_or_caption is None
    assert result.metadata.creator is None
    assert result.options[0].transport_ref["url"] == "https://media.example.invalid/feed-attachment.jpg"


def test_rejects_multiple_explicit_attachments() -> None:
    with pytest.raises(SourceAdapterError) as caught:
        parse_embed(read("linkedin-image-multiple.html"), requested_activity_id=IDENTITY, fetched_url=URL)
    assert caught.value.category is ErrorCategory.UNSUPPORTED_COLLECTION


@pytest.mark.parametrize(
    ("html", "url"),
    [
        ("<html></html>", URL),
        (read("linkedin-image-unrelated.html"), URL),
        (read("linkedin-image-single.html"), URL.replace(IDENTITY, "7500000000000000000")),
    ],
)
def test_rejects_absent_unrelated_or_mismatched_identity(html: str, url: str) -> None:
    with pytest.raises(SourceAdapterError) as caught:
        parse_embed(html, requested_activity_id=IDENTITY, fetched_url=url)
    assert caught.value.category in {ErrorCategory.UNAVAILABLE, ErrorCategory.INVALID_SOURCE_RESPONSE}

from __future__ import annotations

import json
from pathlib import Path

import pytest

from openmedia.sources import ErrorCategory, SourceAdapterError
from openmedia.sources import InspectInput, TransportResponse
from openmedia.sources.instagram import InstagramImageAdapter, detect_image_format, normalize_post


FIXTURES = Path(__file__).parents[1] / "fixtures" / "instagram"


def load(name: str):
    return json.loads((FIXTURES / name).read_text())


def test_graph_image_produces_one_native_option_without_fetching_primary_bytes() -> None:
    post = load("instagram-image-single-post.json")
    result = normalize_post(post, content_type="image/jpeg", content_length=1234)
    assert result.metadata.media_id == "gbStjFIaB4"
    assert result.metadata.media_kind == "image"
    assert result.metadata.thumbnail_url != result.options[0].transport_ref["url"]
    assert result.options[0].extension == "jpg"
    assert result.options[0].size_bytes == 1234


def test_missing_optional_metadata_is_not_invented() -> None:
    post = load("instagram-image-single-post.json")
    post["caption"] = None
    post["owner_username"] = None
    result = normalize_post(post, content_type="image/webp", content_length=None)
    assert result.metadata.title_or_caption is None
    assert result.metadata.creator is None
    assert result.options[0].extension == "webp"
    assert result.options[0].size_bytes is None


def test_recorded_sidecars_are_rejected_before_first_image_can_be_selected() -> None:
    for post in load("instagram-image-sidecars.json"):
        with pytest.raises(SourceAdapterError) as caught:
            normalize_post(post, content_type="image/jpeg", content_length=100)
        assert caught.value.category is ErrorCategory.UNSUPPORTED_COLLECTION


@pytest.mark.parametrize(
    ("content_type", "body", "expected"),
    [
        ("image/jpeg", b"\xff\xd8\xff\xe0payload", ("jpg", "image/jpeg")),
        ("image/webp", b"RIFF\x04\x00\x00\x00WEBPpayload", ("webp", "image/webp")),
    ],
)
def test_download_format_requires_matching_header_and_signature(content_type, body, expected) -> None:
    assert detect_image_format(content_type, body) == expected


def test_mismatched_header_and_signature_is_rejected() -> None:
    with pytest.raises(SourceAdapterError) as caught:
        detect_image_format("image/jpeg", b"RIFF\x04\x00\x00\x00WEBPpayload")
    assert caught.value.category is ErrorCategory.INVALID_SOURCE_RESPONSE


def test_adapter_uses_parent_rate_control_and_headers_only_probe(tmp_path: Path) -> None:
    events: list[object] = []

    class Transport:
        def head(self, url, **kwargs):
            events.append(("head", url))
            return TransportResponse(url, 200, {"content-type": "image/jpeg", "content-length": "12"}, b"")

        def fetch(self, *args, **kwargs):
            raise AssertionError("inspection must not fetch primary image bytes")

        def download(self, *args, **kwargs):
            raise AssertionError("inspection must not download primary image bytes")

    class Rate:
        def acquire(self, platform, request_class, *, deadline):
            events.append(("rate", platform, request_class))
            return 0

        def limited(self, *args, **kwargs):
            events.append("limited")

    adapter = InstagramImageAdapter(post_loader=lambda _shortcode: load("instagram-image-single-post.json"))
    result = adapter.inspect(
        InspectInput(
            source_url="https://www.instagram.com/p/gbStjFIaB4/",
            request_id="0123456789abcdef0123456789abcdef",
            work_directory=tmp_path,
            deadline=100,
        ),
        transport=Transport(),
        rate_control=Rate(),
    )
    assert result.options[0].size_bytes == 12
    assert events[0] == ("rate", "instagram", "metadata")
    assert events[1][0] == "head"

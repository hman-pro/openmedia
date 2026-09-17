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
    assert result.options[0].transport_ref["url"] == "https://media.example.invalid/feed-attachment.jpg"


def test_available_creator_and_caption_come_from_the_post_markup_only() -> None:
    result = parse_embed(read("linkedin-image-single.html"), requested_activity_id=IDENTITY, fetched_url=URL)
    assert result.metadata.creator == "Sanitized Author"
    assert result.metadata.title_or_caption == "Sanitized caption line one\nline two with #hashtag"
    # Attachment alt text and the profile link's aria-label are never used as metadata.
    assert "attachment description" not in result.metadata.title_or_caption
    assert "View profile" not in result.metadata.creator


def test_unclosed_caption_paragraph_does_not_hide_the_attachment() -> None:
    html = read("linkedin-image-single.html").replace("#hashtag</a></p>", "#hashtag</a>")
    result = parse_embed(html, requested_activity_id=IDENTITY, fetched_url=URL)
    assert result.options[0].transport_ref["url"] == "https://media.example.invalid/feed-attachment.jpg"


def test_absent_creator_and_caption_stay_absent() -> None:
    html = read("linkedin-image-single.html")
    start = html.index('<div class="text-color-text ">')
    end = html.index("<img class=\"lazy-load")
    result = parse_embed(html[:start] + html[end:], requested_activity_id=IDENTITY, fetched_url=URL)
    assert result.metadata.creator is None
    assert result.metadata.title_or_caption is None


class ProbeTransport:
    """Serves the single-image embed, then answers the attachment probe with one status."""

    def __init__(self, status: int) -> None:
        self.status = status

    def fetch(self, url, *, limit, **kwargs):
        from openmedia.sources import TransportResponse
        return TransportResponse(url, 200, {"content-type": "text/html"}, read("linkedin-image-single.html").encode())

    def head(self, url, **kwargs):
        from openmedia.sources import TransportResponse
        # Deliberately plausible headers: a failed probe's type and length must not be trusted.
        return TransportResponse(url, self.status, {"content-type": "image/jpeg", "content-length": "100", "retry-after": "30"}, b"")


class ProbeRate:
    def __init__(self) -> None:
        self.limited_calls: list[float | None] = []

    def acquire(self, platform, request_class, *, deadline):
        return 0

    def limited(self, platform, request_class, *, retry_after):
        self.limited_calls.append(retry_after)


def inspect_with_probe(tmp_path, status: int, rate: ProbeRate | None = None):
    from openmedia.sources import InspectInput
    from openmedia.sources.linkedin import LinkedInImageAdapter
    request = InspectInput(source_url=f"https://www.linkedin.com/feed/update/urn:li:activity:{IDENTITY}",
        request_id="0123456789abcdef0123456789abcdef", work_directory=tmp_path, deadline=100)
    return LinkedInImageAdapter().inspect(request, transport=ProbeTransport(status), rate_control=rate or ProbeRate())


@pytest.mark.parametrize(
    ("status", "category"),
    [
        (403, ErrorCategory.UNAVAILABLE),
        (404, ErrorCategory.UNAVAILABLE),
        (410, ErrorCategory.UNAVAILABLE),
        (405, ErrorCategory.INVALID_SOURCE_RESPONSE),
        (500, ErrorCategory.INVALID_SOURCE_RESPONSE),
    ],
)
def test_attachment_probe_status_is_classified_before_headers(tmp_path, status, category) -> None:
    with pytest.raises(SourceAdapterError) as caught:
        inspect_with_probe(tmp_path, status)
    assert caught.value.category is category


def test_rate_limited_attachment_probe_reports_shared_cooldown(tmp_path) -> None:
    rate = ProbeRate()
    with pytest.raises(SourceAdapterError) as caught:
        inspect_with_probe(tmp_path, 429, rate)
    assert caught.value.category is ErrorCategory.RATE_LIMITED
    assert rate.limited_calls == [30.0]


def test_successful_attachment_probe_still_yields_the_image_choice(tmp_path) -> None:
    result = inspect_with_probe(tmp_path, 200)
    assert (result.options[0].extension, result.options[0].size_bytes) == ("jpg", 100)


class RecordingProbeTransport(ProbeTransport):
    def __init__(self) -> None:
        super().__init__(200)
        self.fetched: list[str] = []

    def fetch(self, url, *, limit, **kwargs):
        self.fetched.append(url)
        return super().fetch(url, limit=limit, **kwargs)


@pytest.mark.parametrize(
    ("source_url", "embed_urn"),
    [
        (f"https://www.linkedin.com/posts/someone_words-ugcPost-{IDENTITY}-AbCd", f"urn:li:ugcPost:{IDENTITY}"),
        (f"https://www.linkedin.com/feed/update/urn:li:activity:{IDENTITY}", f"urn:li:activity:{IDENTITY}"),
        (f"https://www.linkedin.com/feed/update/urn:li:share:{IDENTITY}", f"urn:li:share:{IDENTITY}"),
    ],
)
def test_image_adapter_requests_the_embed_under_the_posts_own_urn_type(tmp_path, source_url, embed_urn) -> None:
    from openmedia.sources import InspectInput, recognize_source_url
    from openmedia.sources.linkedin import LinkedInImageAdapter
    transport = RecordingProbeTransport()
    route = recognize_source_url(source_url)
    request = InspectInput(source_url=route.canonical_url, request_id="0123456789abcdef0123456789abcdef",
        work_directory=tmp_path, deadline=100)
    result = LinkedInImageAdapter().inspect(request, transport=transport, rate_control=ProbeRate())
    assert transport.fetched == [f"https://www.linkedin.com/embed/feed/update/{embed_urn}"]
    assert result.metadata.media_id == IDENTITY
    # Refresh re-inspects metadata.canonical_url, so it must still name the same URN type.
    assert result.metadata.canonical_url == route.canonical_url
    assert recognize_source_url(result.metadata.canonical_url) == route


def test_router_sends_extractor_unmatchable_linkedin_routes_straight_to_the_image_adapter(tmp_path) -> None:
    from openmedia.sources import InspectInput, SourceRouter
    from openmedia.sources.linkedin import LinkedInImageAdapter

    class MustNotRun:
        def inspect(self, request, **kwargs):
            raise AssertionError("yt-dlp cannot match feed/update ugcPost or share URLs")

    class NoVideo:
        calls = 0
        def inspect(self, request, **kwargs):
            NoVideo.calls += 1
            raise SourceAdapterError(ErrorCategory.NO_FORMATS, stage="inspection")

    def inspect(router, url):
        request = InspectInput(source_url=url, request_id="0123456789abcdef0123456789abcdef",
            work_directory=tmp_path, deadline=100)
        return router.inspect(request, transport=RecordingProbeTransport(), rate_control=ProbeRate())

    embed_only = SourceRouter(ytdlp=MustNotRun(), linkedin=LinkedInImageAdapter(), instagram=MustNotRun())
    assert inspect(embed_only, f"https://www.linkedin.com/feed/update/urn:li:ugcPost:{IDENTITY}").options
    video_first = SourceRouter(ytdlp=NoVideo(), linkedin=LinkedInImageAdapter(), instagram=MustNotRun())
    assert inspect(video_first, f"https://www.linkedin.com/posts/someone_words-ugcPost-{IDENTITY}-AbCd").options
    assert NoVideo.calls == 1


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

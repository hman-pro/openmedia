from __future__ import annotations

import time
from pathlib import Path

import pytest

from openmedia.choices import choose
from openmedia.models import MediaKind
from openmedia.network import GuardedHTTPTransport, validate_owned_file
from openmedia.sources import DownloadInput, InspectInput, SourceRouter, recognize_source_url


class LiveRateControl:
    """Production Instagram request spacing, plus a polite pause between Instagram cases."""

    REQUEST_SPACING = 1.0
    CASE_SPACING = 60.0

    def __init__(self) -> None:
        self.last_request: dict[str, float] = {}
        self.last_instagram_case: float | None = None

    def begin_case(self, platform: str) -> None:
        if platform != "instagram":
            return
        if self.last_instagram_case is not None:
            time.sleep(max(0.0, self.CASE_SPACING - (time.monotonic() - self.last_instagram_case)))
        self.last_instagram_case = time.monotonic()

    def acquire(self, platform: str, request_class: str, *, deadline: float) -> float:
        if platform != "instagram":
            return 0
        # Mirrors ParentRateController: one second per request class, refused past the deadline.
        now = time.monotonic()
        delay = max(0.0, self.REQUEST_SPACING - (now - self.last_request.get(request_class, -10.0)))
        if now + delay >= deadline:
            pytest.fail("Instagram spacing would exceed the current live-test deadline")
        if delay:
            time.sleep(delay)
        self.last_request[request_class] = now + delay
        return delay

    def limited(self, platform: str, request_class: str, *, retry_after: float | None) -> None:
        pytest.fail(f"{platform} rate limited the {request_class} live check ({retry_after=})")


@pytest.mark.live
def test_required_source_matrix(live_manifest: list[dict[str, object]], tmp_path: Path) -> None:
    expected_cases = {
        "youtube-video",
        "youtube-music",
        "youtube-music-context",
        "linkedin-video",
        "linkedin-image",
        "instagram-video",
        "instagram-image",
        # 004 SC-003: an app share link, and a post whose code ends in a hyphen.
        "linkedin-short-video",
        "linkedin-hyphen-code",
    }
    by_case = {str(case["case_id"]): case for case in live_manifest}
    assert expected_cases <= by_case.keys(), "live manifest must cover source categories, both LinkedIn link forms and plain/context music"
    router = SourceRouter()
    transport = GuardedHTTPTransport()
    rate = LiveRateControl()

    for index, case_id in enumerate(sorted(expected_cases)):
        case = by_case[case_id]
        url = str(case["url"])
        route = recognize_source_url(url)
        rate.begin_case(route.platform)
        work = tmp_path / f"case-{index}"
        work.mkdir()
        inspected = router.inspect(
            InspectInput(
                source_url=route.canonical_url,
                request_id=f"{index + 1:032x}",
                work_directory=work,
                deadline=time.monotonic() + 60,
            ),
            transport=transport,
            rate_control=rate,
        )
        assert inspected.metadata.media_id == str(case["expected_identity"])
        assert inspected.metadata.media_kind == str(case["expected_type"])
        selectable = [option for option in inspected.options if option.availability == "selectable"]
        assert selectable, f"{case_id} exposed no selectable native option"
        if case_id.startswith("youtube-music"):
            assert inspected.metadata.media_kind is MediaKind.AUDIO
            assert inspected.metadata.platform == "youtube"
            assert inspected.metadata.canonical_url == route.canonical_url
            assert route.canonical_url.startswith("https://music.youtube.com/watch?v=")
            choices = choose(inspected.options, media_kind=MediaKind.AUDIO, max_file_bytes=50_000_000)
            assert choices.automatic and len(choices.options) == 1 and not choices.missing
            option = choices.options[0]
            assert option.media_type == "audio" and "+" not in option.source_format_id
        else:
            option = min(selectable, key=lambda item: item.size_bytes if item.size_bytes is not None else 50_000_000)
        downloaded = router.download(
            DownloadInput(
                request_id=f"{index + 1:032x}",
                metadata=inspected.metadata,
                option=option,
                work_directory=work,
                deadline=time.monotonic() + 600,
                output_limit=50_000_000,
                workspace_limit=128 * 1024 * 1024,
            ),
            transport=transport,
            rate_control=rate,
        )
        assert downloaded.media_id == inspected.metadata.media_id
        assert downloaded.source_format_id == option.source_format_id
        assert downloaded.extension == option.extension
        assert downloaded.media_type == option.media_type
        actual = validate_owned_file(downloaded.path, work, max_bytes=50_000_000)
        assert actual == downloaded.actual_bytes
        print(f"{case_id}: identity={downloaded.media_id} format={downloaded.source_format_id} bytes={actual}")
        downloaded.path.unlink()


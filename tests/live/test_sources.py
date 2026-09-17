from __future__ import annotations

import time
from pathlib import Path

import pytest

from openmedia.network import GuardedHTTPTransport, validate_owned_file
from openmedia.sources import DownloadInput, InspectInput, SourceRouter, recognize_source_url


class LiveRateControl:
    """One process-owned Instagram interval shared across successive adapter calls."""

    def __init__(self) -> None:
        self.last_instagram_request = 0.0

    def acquire(self, platform: str, request_class: str, *, deadline: float) -> float:
        if platform != "instagram":
            return 0
        delay = max(0.0, 60.0 - (time.monotonic() - self.last_instagram_request))
        if time.monotonic() + delay >= deadline:
            pytest.fail("Instagram spacing would exceed the current live-test deadline")
        if delay:
            time.sleep(delay)
        self.last_instagram_request = time.monotonic()
        return delay

    def limited(self, platform: str, request_class: str, *, retry_after: float | None) -> None:
        pytest.fail(f"{platform} rate limited the {request_class} live check ({retry_after=})")


@pytest.mark.live
def test_required_source_matrix(live_manifest: list[dict[str, object]], tmp_path: Path) -> None:
    expected_cases = {
        "youtube-video",
        "linkedin-video",
        "linkedin-image",
        "instagram-video",
        "instagram-image",
    }
    by_case = {str(case["case_id"]): case for case in live_manifest}
    assert expected_cases <= by_case.keys(), "live manifest must cover all five FR-002 categories"
    router = SourceRouter()
    transport = GuardedHTTPTransport()
    rate = LiveRateControl()

    for index, case_id in enumerate(sorted(expected_cases)):
        case = by_case[case_id]
        url = str(case["url"])
        route = recognize_source_url(url)
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
        validate_owned_file(downloaded.path, work, max_bytes=50_000_000)
        downloaded.path.unlink()


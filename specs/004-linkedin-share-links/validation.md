# Validation: LinkedIn Share Links

## Baseline

- Date: 2026-09-23
- Branch: `004-linkedin-share-links` at `03ce9e9` (before any 004 code change)
- Commands: `uv sync --locked --group dev && uv run pytest`
- Result: green — 517 passed, 3 deselected (the `live` tests excluded by default), 0 failed

## US1

- Date: 2026-09-23
- Branch: `004-linkedin-share-links` on top of `c8671db`, phase 3 changes uncommitted
- Command: `uv run pytest`
- Result: green — 597 passed, 3 deselected (`live`), 0 failed

Quickstart §2 rows, walked through controlled tests (recording fake transport, no network):

| Row | Covered by | Observed |
|---|---|---|
| Short link → video post | `tests/contract/test_linkedin.py::test_short_link_redirect_resolves_to_the_post_without_tracking`, `tests/contract/test_adapter_transports.py::test_router_resolves_short_link_before_calling_ytdlp`, `tests/integration/test_download_flow.py::test_short_link_is_admitted_by_code_and_rebound_to_the_resolved_post` | One `HEAD` to `lnkd.in` with `follow_redirects=False` and no `Cookie`. yt-dlp receives the query-free post address. The request is rebound to the post's `media_id`/canonical URL and then publishes and claims as for the full address |
| Short link → picture post | `tests/contract/test_adapter_transports.py::test_router_short_link_falls_back_to_image_adapter_with_resolved_input` | yt-dlp `UNAVAILABLE` falls back to `linkedin_image` with the same resolved input. From there the flow is the full-address picture path |
| `404` | `test_linkedin.py::test_short_link_failure_outcomes`, `test_adapter_transports.py::test_router_short_link_resolution_failure_calls_no_adapter`, `test_download_flow.py::test_short_link_resolution_failure_ends_on_the_checking_message_without_a_keyboard` | `short_link_unresolved`, `detail == "not_found"`. The unresolved text is shown on the checking message, with no keyboard |
| `200` interstitial | `test_short_link_failure_outcomes`, `test_router_short_link_resolution_failure_calls_no_adapter` | `short_link_unresolved`, `no_redirect`. No adapter called |
| 301 to `lnkd.in/p/other` | same two tests | `short_link_unresolved`, `too_many_redirects`. The only URL requested is the original short link |
| 301 to `https://example.com/…` (also `http://www.linkedin.com/…`, `https://de.linkedin.com/…`) | same two tests; `test_download_flow.py::test_short_link_resolution_failure_ends_on_the_checking_message_without_a_keyboard` | `short_link_not_post`, `outside_linkedin`. The destination is never requested |
| 301 to `…/in/someone/` | same two tests | `short_link_not_post`, `not_a_post` |
| `429` | `test_network.py::test_head_without_following_reports_its_status_to_the_response_hook`, `test_adapter_transports.py::test_router_short_link_rate_limit_propagates_unchanged_and_calls_no_adapter` (both added in T016) | The no-follow `HEAD` reports its 429 to the transport response hook, which in the worker raises `RATE_LIMITED`. The router lets it propagate unchanged with no adapter called, so the existing rate-limited text applies |
| Short link + YouTube link | `tests/unit/test_links.py::test_short_link_counts_as_a_link_so_two_links_get_one_link_guidance` | Both links recognized; `parse_link_message` raises `InputError(ONE_LINK_GUIDANCE)`. The `refused` log entry is US3 (T024/T026) |

Notes:
- The `429` row had no controlled test before T016. Two tests were added rather than recording it unverified.
- The log fields in the quickstart (`resolution=…`, `refused` entries) are US3 scope and are not checked here.

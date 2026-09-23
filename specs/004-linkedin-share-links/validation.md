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

## US2

- Date: 2026-09-23
- Branch: `004-linkedin-share-links` on top of `081dcfb`, phase 4 changes uncommitted
- Command: `uv run pytest`
- Result: green — 601 passed, 3 deselected (`live`), 0 failed

Quickstart §2 rows, walked through controlled tests (real yt-dlp extraction against a fake
page transport, no network):

| Row | Covered by | Observed |
|---|---|---|
| Hyphen-code video post | `tests/unit/test_links.py::test_linkedin_post_slug_accepts_any_trailing_code`, `tests/contract/test_ytdlp.py::test_linkedin_post_extractor_matches_hyphen_code_by_recognizer`, `test_ytdlp.py::test_ytdlp_adapter_inspects_hyphen_code_video_post` | Recognized as `ugcPost` `7508434034927017984`. Stock `LinkedInIE.suitable` stays `False`; `OpenMediaLinkedInPostIE.suitable` is `True` and `_match_id` returns the recognizer's ID. `YtDlpAdapter.inspect` on the `linkedin-video-post-hyphen-code.html` fixture returns `platform == "linkedin"`, that `media_id`, and two video options from `media.example.invalid`. Only `www.linkedin.com` was fetched |
| Hyphen-code picture post | `test_ytdlp.py::test_hyphen_code_picture_post_is_unavailable_and_falls_back_to_image` | yt-dlp fetches the post page once and raises `UNAVAILABLE` (no video), not `UNSUPPORTED_URL`. `SourceRouter` then hands the same input to `linkedin_image` |
| Same post, two codes/queries | `test_links.py::test_linkedin_post_slug_accepts_any_trailing_code` (`…-lwx-/` and `…-lwx-/?utm_source=x&rcm=y`), `test_links.py::test_linkedin_post_identity_ignores_the_trailing_code` (`-lwx-` vs `-abcd`) | Same (`urn_kind`, `media_id`). Query is dropped from the canonical URL; a different trailing code keeps its own canonical URL |
| Raw Persian slug | `test_links.py::test_linkedin_post_slug_accepts_any_trailing_code` (raw and percent-encoded Persian slug) | Recognized as `share` `7508424761698410497`, canonical URL round-trips through the recognizer |

Upgrade pin: `test_ytdlp.py::test_linkedin_ie_still_reads_its_id_through_match_id` asserts
`LinkedInIE._real_extract` still calls `self._match_id(url)` (research R7).

Notes:
- `OpenMediaLinkedInPostIE` is added per `YoutubeDL` instance with `add_info_extractor`, after
  the default extractors, so addresses the stock `LinkedInIE` accepts are still handled by it.

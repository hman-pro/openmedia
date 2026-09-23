---

description: "Task list for 004 LinkedIn share links"
---

# Tasks: LinkedIn Share Links

**Input**: Design documents from `/specs/004-linkedin-share-links/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/linkedin-links.md,
contracts/telegram-bot.md, quickstart.md

**Tests**: Included. The constitution requires controlled validation of changed success and
failure paths, and 001–003 were built test first. Write each test task before its
implementation task, and confirm the test fails.

**Organization**: Grouped by user story. Commit at each phase boundary:
`feat(004): phase N <name>`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1, US2, US3 from spec.md
- The network is disabled in `tests/conftest.py`. Short-link tests use a local recording
  fake transport (`fetch`/`head`/`download` that append `(method, url, kwargs)` to a list)
  and never a real host. All fixture media URLs use `media.example.invalid`.
- The identifiers of the live posts from research R1/R5 (`7508434034927017984`,
  `7508424761698410497`) may be used as test IDs. Their descriptive slugs must be replaced
  with neutral text in fixtures (for example `sample-author_sample-text`), except for one
  Persian-text case built from the words `سلام دنیا`.

---

## Phase 1: Setup

**Purpose**: Confirm a green baseline before any change.

- [X] T001 Run `uv sync --locked --group dev && uv run pytest` on branch `004-linkedin-share-links`. Confirm it is green, then create `specs/004-linkedin-share-links/validation.md` with a "Baseline" section recording the date and pass count.

**Checkpoint**: Baseline recorded. No commit needed if nothing else changed (fold it into phase 2).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The no-follow `HEAD`, the two new error categories and texts, the resolution
outcome vocabulary, and its passage through the worker protocol. US1 and US3 both depend on
these.

**⚠️ CRITICAL**: No user story work begins until this phase is complete.

- [ ] T002 [P] Add failing tests to `tests/contract/test_network.py`, patching `openmedia.network._PinnedHTTPSConnection` as `test_real_transport_limits_metadata_client_redirects` does, with a connection whose `getresponse()` returns `status=301` and `Location: https://www.linkedin.com/posts/x-share-7508424761698410497-2cX9/`:
  - `GuardedHTTPTransport(...).head(url, follow_redirects=False)` returns a `TransportResponse` with `status == 301` and `headers["location"]` equal to that value.
  - Exactly one connection is opened, and `on_request` is called exactly once.
  - The default `head(url)` still follows the redirect (two connections).
  - `follow_redirects=False` still rejects a non-HTTPS or private-address short-link URL through `policy.resolve` (`UnsafeDestination`).
- [ ] T003 In `src/openmedia/network.py`, add the keyword `follow_redirects: bool = True` to `GuardedHTTPTransport.head` and `_open`. When it is `False`, `_open` returns `(connection, response, current_url)` after the first response, whatever its status, still running `policy.resolve` and both hooks. In `src/openmedia/sources/__init__.py`, add the same keyword to the `GuardedTransport.head` protocol. Pass T002.
- [ ] T004 [P] Add failing tests to `tests/contract/test_bot_errors.py`:
  - `failure_message(ErrorCategory.SHORT_LINK_UNRESOLVED, stage="checking") == "That LinkedIn link could not be opened. Send the post's full linkedin.com address."`
  - `failure_message(ErrorCategory.SHORT_LINK_NOT_POST, stage="checking") == "That LinkedIn link does not lead to a supported post. Send a public LinkedIn post link."`
  - Neither text contains `http`, `lnkd.in`, or `www.`.
  - The existing `test_every_adapter_error_has_sanitized_guidance` parametrization over `list(ErrorCategory)` covers both new values.
- [ ] T005 In `src/openmedia/sources/__init__.py`:
  - Add `ErrorCategory.SHORT_LINK_UNRESOLVED = "short_link_unresolved"` and `SHORT_LINK_NOT_POST = "short_link_not_post"`.
  - Add `RESOLUTION_FAILURES = frozenset({"not_found", "no_redirect", "too_many_redirects", "timed_out", "unreachable", "outside_linkedin", "not_a_post"})`, export it in `__all__`, and add a comment pointing to data-model "ResolutionOutcome".

  In `src/openmedia/bot.py` `failure_message`, return the two texts from T004. Pass T004.
- [ ] T006 [P] Add failing tests to `tests/integration/test_workers.py`, adding modes to `tests/fixtures/worker_stub.py`:
  - Mode `error_detail` prints `{"event":"error","category":"short_link_unresolved","stage":"inspection","detail":"not_found"}`. The supervisor raises `WorkerRemoteError` with `category == "short_link_unresolved"` and `detail == "not_found"`.
  - Mode `error_bad_detail` prints the same event with `"detail":"https://evil.example/"`. It raises `WorkerRemoteError` with `detail is None`.
  - An existing error event without `detail` still yields `detail is None`.
- [ ] T007 In `src/openmedia/workers.py`:
  - `WorkerRemoteError.__init__(self, category, stage=None, detail=None)` stores `detail`. The message text is unchanged, and `detail` does not appear in it.
  - `WorkerSupervisor` passes `event.get("detail")` only when it is a `str` in `RESOLUTION_FAILURES`, else `None`.
  - In `_child_main`'s `except` block, add `"detail": exc.detail` to the printed error event only when `getattr(exc, "detail", None) in RESOLUTION_FAILURES`.

  Pass T006.

**Checkpoint**: `uv run pytest` green. Commit `feat(004): phase 2 foundational`.

---

## Phase 3: User Story 1 - Send a LinkedIn post shared from the phone app (Priority: P1) 🎯 MVP

**Goal**: An `lnkd.in/p/<code>` link is resolved with one anonymous `HEAD` inside the inspect
worker and then handled exactly like the post's full address. Bad short links get one of two
plain explanations.

**Independent Test**: With a recording fake transport, a short link whose `HEAD` answers
`301` to a video post fixture address, or to a picture post embed, ends in the same card or
picture delivery as the full address. Every failure outcome gives its text, and no host
outside `lnkd.in`/`linkedin.com`/`www.linkedin.com`/`media.example.invalid` is requested
(quickstart §2, SC-004).

### Tests for User Story 1

- [ ] T008 [P] [US1] Add failing tests to `tests/unit/test_links.py`:
  - `recognize_source_url` returns `SourceRoute("linkedin", "dMhfr6kG", "https://lnkd.in/p/dMhfr6kG", "short_link", None)` for `https://lnkd.in/p/dMhfr6kG`, `http://lnkd.in/p/dMhfr6kG`, bare `lnkd.in/p/dMhfr6kG`, and `https://lnkd.in/p/dMhfr6kG?trk=x`. The query is dropped. A fragment is rejected (`UNSUPPORTED_URL`), as for every other route. For the bare and `http` forms, normalize via `normalize_supported_link` first.
  - Short codes allow `[A-Za-z0-9_-]{1,32}`. A 33-character code and `https://lnkd.in/p/` raise `UNSUPPORTED_URL`.
  - `https://lnkd.in/dMhfr6kG`, `https://lnkd.in/p/a/b`, and `https://www.lnkd.in/p/dMhfr6kG` raise `UNSUPPORTED_URL`.
  - `supported_urls_in_text("see https://lnkd.in/p/dMhfr6kG and https://youtu.be/abcdefghijk")` returns both links. `parse_link_message` on that text raises `InputError(ONE_LINK_GUIDANCE)`: the 001 FR-001 behavior change in contracts/telegram-bot.md.
- [ ] T009 [P] [US1] Add failing tests to `tests/contract/test_linkedin.py` for `resolve_short_link(url, *, transport, rate_control, deadline) -> str` in `src/openmedia/sources/linkedin.py`. Use a recording fake whose `head` returns a scripted `TransportResponse` (with `set_cookies=("JSESSIONID=x",)` on every response). Cover each row of data-model "ResolutionOutcome":
  - `301` to `https://www.linkedin.com/posts/sample-author_sample-text-ugcPost-7508434034927017984-lwx-/?utm_source=social_share_send&utm_medium=ios_app&rcm=ACoAAA&utm_campaign=copy_link` returns `https://www.linkedin.com/posts/sample-author_sample-text-ugcPost-7508434034927017984-lwx-/`. The returned value contains no `?`, `utm_`, or `rcm`.
  - `302`, `303`, `307`, and `308` behave the same. `https://linkedin.com/feed/update/urn:li:activity:7508434097229369345` resolves too.
  - `404` or `410` → `SHORT_LINK_UNRESOLVED`, `detail == "not_found"`.
  - `200` HTML, `500`, `403`, or a `301` without `location` → `SHORT_LINK_UNRESOLVED`, `"no_redirect"`.
  - Location `https://lnkd.in/p/other`, or the relative `/p/other` → `SHORT_LINK_UNRESOLVED`, `"too_many_redirects"`.
  - Location `https://example.com/`, `http://www.linkedin.com/posts/…`, `https://de.linkedin.com/posts/…`, `https://user@www.linkedin.com/posts/…`, or `https://www.linkedin.com:8443/posts/…` → `SHORT_LINK_NOT_POST`, `"outside_linkedin"`.
  - Location `https://www.linkedin.com/in/someone/` or `https://www.linkedin.com/jobs/view/123/` → `SHORT_LINK_NOT_POST`, `"not_a_post"`.
  - `head` raising `TimeoutError` while `deadline` is still in the future → `SHORT_LINK_UNRESOLVED`, `"timed_out"`. When `deadline` has already passed, the `TimeoutError` propagates unchanged.
  - `head` raising `ConnectionResetError` or `ConnectionRefusedError` → `SHORT_LINK_UNRESOLVED`, `"unreachable"`.
  - Every case makes exactly one transport call: a `head` to the short URL with `follow_redirects=False`, no `headers` containing `Cookie`, and no `fetch` or `download`.
  - `rate_control.acquire("linkedin", "metadata", deadline=deadline)` is called once before the `head`.
  - Every raised error has `stage == "inspection"`.
- [ ] T010 [P] [US1] Add failing tests to `tests/contract/test_adapter_transports.py` for `SourceRouter.inspect`, reusing that file's `Transport`/`RecordingTransport` doubles and stub adapters:
  - An `InspectInput` whose `source_url` is `https://lnkd.in/p/dAjqaykT`, with `head` answering `301` to `https://www.linkedin.com/posts/sample-author_sample-text-share-7508424761698410497-2cX9/?utm_source=x&rcm=y`, calls the stub yt-dlp adapter with `source_url == "https://www.linkedin.com/posts/sample-author_sample-text-share-7508424761698410497-2cX9/"`.
  - When the yt-dlp stub raises `UNAVAILABLE`, the stub `linkedin_image` adapter gets the same resolved input.
  - A resolution failure propagates with its category and `detail`, and no adapter is called.
  - SC-004: every URL the recording transport saw has a host in `{"lnkd.in", "www.linkedin.com", "linkedin.com", "media.example.invalid"}`.
- [ ] T011 [P] [US1] Add failing tests to `tests/integration/test_download_flow.py`, driving `MediaWorkflow` with injected callables:
  - (a) A request submitted with links `("https://lnkd.in/p/dAjqaykT",)` is admitted with `platform == "linkedin"`, `media_id == "dAjqaykT"`, and `source_url == "https://lnkd.in/p/dAjqaykT"`. The `checking` status runs before `inspect`. The inspect stub returns the normalized `tests/fixtures/ytdlp/linkedin-video-progressive.json` result, with `metadata.canonical_url` set to `https://www.linkedin.com/posts/sample-author_sample-text-share-7508424761698410497-2cX9/` and `media_id` set to `7508424761698410497`. The flow then publishes and claims exactly as for the full address. After inspection, `request.media_id == "7508424761698410497"` and `request.source_url` equals that canonical URL. The download result is validated against the rebound ID.
  - (b) The same request, with the inspect stub returning `canonical_url` `https://www.youtube.com/watch?v=abcdefghijk`, or a LinkedIn canonical URL whose ID differs from `metadata.media_id`, fails at stage `checking` with the existing media-identity `WorkflowError`.
  - (c) The inspect stub raising `WorkerRemoteError("short_link_not_post", "inspection", "outside_linkedin")` notifies the `short_link_not_post` text from contracts/telegram-bot.md on the status surface, with no keyboard.
  - (d) The same with `WorkerRemoteError("short_link_unresolved", "inspection", "not_found")` notifies the unresolved text.
  - (e) A full-address request keeps today's strict `media_id` equality check. Its identity is never rebound.

### Implementation for User Story 1

- [ ] T012 [US1] In `src/openmedia/sources/__init__.py`:
  - Add `"lnkd.in"` to `SUPPORTED_HOSTS` and `lnkd\.in` to `_BARE_SUPPORTED_HOST`.
  - In `recognize_source_url`, handle host `lnkd.in` before the other hosts. Exactly two path segments `["p", code]`, with `code` matching `^[A-Za-z0-9_-]{1,32}$`, give `SourceRoute("linkedin", code, f"https://lnkd.in/p/{code}", "short_link")`. Anything else raises `UNSUPPORTED_URL`.
  - Update the `supported_host` docstring to mention LinkedIn short links.

  Pass T008.
- [ ] T013 [US1] Implement `resolve_short_link(url, *, transport, rate_control, deadline) -> str` in `src/openmedia/sources/linkedin.py`, applying the rules of research R4 in order:
  1. Call `rate_control.acquire("linkedin", "metadata", deadline=deadline)`.
  2. Call `transport.head(url, follow_redirects=False, deadline=deadline)` with no `headers` argument.
  3. On `404`/`410` raise `not_found`. On a non-redirect status or a missing `location`, raise `no_redirect`.
  4. Resolve the destination with `urllib.parse.urljoin(url, location)`. If its host is `lnkd.in`, raise `too_many_redirects`.
  5. Scheme must be `https`, host exactly `linkedin.com` or `www.linkedin.com` (after `rstrip(".").lower()`), with no userinfo and a port of `None` or `443`. Otherwise raise `outside_linkedin`.
  6. Rebuild with `urlunsplit(("https", netloc, path, "", ""))`. Call `recognize_source_url` on it. Anything that raises, or whose `platform` is not `linkedin` or whose `route_kind` is not in `{"post", "embed"}`, raises `not_a_post`.
  7. Return the rebuilt URL.

  Error handling:
  - Wrap only the `head` call. First `except TimeoutError`: If `time.monotonic() < deadline`, raise `timed_out`. Otherwise re-raise, so the parent reports the ordinary inspection timeout (spec edge case).
  - Then `except ConnectionError`: raise `unreachable`. Keep the `TimeoutError` handler first so the deadline rule reads first.
  - Every failure is `SourceAdapterError(<SHORT_LINK_UNRESOLVED for not_found/no_redirect/too_many_redirects/timed_out/unreachable, SHORT_LINK_NOT_POST for outside_linkedin/not_a_post>, stage="inspection", detail=<outcome>)`.
  - Never read `set_cookies` and never log the destination.

  Pass T009.
- [ ] T014 [US1] In `SourceRouter._inspect` in `src/openmedia/sources/__init__.py`, when `route.route_kind == "short_link"`:
  - Call `resolve_short_link(request.source_url, transport=transport, rate_control=rate_control, deadline=request.deadline)` (import inside the function, as the adapters are imported).
  - Then `return self._inspect(dataclasses.replace(request, source_url=resolved), transport=transport, rate_control=rate_control)`.
  - Add a comment that a resolved route cannot be `short_link` again because its host is `linkedin.com`.

  Pass T010.
- [ ] T015 [US1] In `MediaWorkflow.submit` in `src/openmedia/coordinator.py`, replace the media-identity check with a helper `_bind_identity(request, result)`:
  - When `recognize_source_url(request.source_url).route_kind == "short_link"`: call `recognize_source_url(result.metadata.canonical_url)`, catching `SourceAdapterError` as a mismatch. Require `platform == "linkedin"`, `route_kind in {"post", "embed"}`, and `route.media_id == result.metadata.media_id`. Then set `request.source_url = route.canonical_url` and `request.media_id = route.media_id`.
  - Otherwise keep `result.metadata.media_id == request.media_id`.
  - Any mismatch raises `WorkflowError("inspection returned a different media identity")`.

  Pass T011.
- [ ] T016 [US1] Run `uv run pytest` until green. Walk the quickstart §2 rows "Short link → video post", "Short link → picture post", `404`, `200` interstitial, "301 to lnkd.in/p/other", "301 to https://example.com/…", "301 to …/in/someone/", `429`, and "Short link + YouTube link" through the controlled tests. Record them in `specs/004-linkedin-share-links/validation.md` under "US1".

**Checkpoint**: US1 works on its own for short links that resolve to addresses the stock
extractor already accepts, such as `dAjqaykT`. Commit
`feat(004): phase 3 us1 short links`.

---

## Phase 4: User Story 2 - Posts whose address ends in an unusual code (Priority: P2)

**Goal**: A post address is recognized by type and numeric ID whatever its trailing code
is, and video posts with hyphenated codes still reach yt-dlp.

**Independent Test**: Controlled tests with `…-ugcPost-7508434034927017984-lwx-/`: the
recognizer returns (`ugcPost`, ID), yt-dlp extracts a video from a sanitized page fixture
through `OpenMediaLinkedInPostIE`, and the picture path still receives it on `unavailable`
(quickstart §2 rows "Hyphen-code video post", "Same post, two codes/queries",
"Raw Persian slug").

### Tests for User Story 2

- [ ] T017 [P] [US2] Add failing rows to `tests/unit/test_links.py` for the research R6 slug rule (`LI = "https://www.linkedin.com"`):
  - `f"{LI}/posts/sample-author_sample-text-ugcPost-7508434034927017984-lwx-/"` gives `urn_kind == "ugcPost"`, `media_id == "7508434034927017984"`, `route_kind == "post"`, and a `canonical_url` that keeps `-lwx-` (with the trailing slash stripped, as today's canonical does).
  - The same address with `?utm_source=x&rcm=y` gives an equal (`urn_kind`, `media_id`) and the same `canonical_url`.
  - `…-ugcPost-7508434034927017984-abcd/` gives the same (`urn_kind`, `media_id`) but a different `canonical_url`.
  - A prefix containing digits and a type word, `f"{LI}/posts/share-fan-8346721bb_x-ugcPost-7508434034927017984-lwx-"`, takes the **rightmost** type word (`ugcPost`).
  - A raw Unicode slug `f"{LI}/posts/sample-author_سلام-دنیا-share-7508424761698410497-2cX9"` and its percent-encoded form are both recognized with `share`/`7508424761698410497`.
  - A code longer than 32 characters, or one containing `.`, raises `UNSUPPORTED_URL`.
  - Every existing row in `test_linkedin_routes_keep_the_urn_type_and_are_stable` and `test_linkedin_routes_without_a_single_post_identity_are_rejected` still passes unchanged, and `recognize_source_url(route.canonical_url) == route` holds for every new row.
- [ ] T018 [P] [US2] Create `tests/fixtures/linkedin/linkedin-video-post-hyphen-code.html`: a minimal sanitized page with `<title>Sample post</title>`, `<meta property="og:title" content="Sample post">`, and one `<video data-sources='[{"src":"https://media.example.invalid/li-720.mp4","type":"video/mp4","data-bitrate":"284460"},{"src":"https://media.example.invalid/li-360.mp4","type":"video/mp4","data-bitrate":"212348"}]'>`. Add a section to `tests/fixtures/linkedin/PROVENANCE.md`: its shape follows the live `…-ugcPost-7508434034927017984-lwx-/` page of 2026-09-23 (research R7). The content is synthetic, and no author, text, or media URL was copied.
- [ ] T019 [P] [US2] Add failing tests to `tests/contract/test_ytdlp.py`:
  - For the `-lwx-` address, `_linkedin_post_extractor().suitable(url)` is `True` and `_match_id(url) == "7508434034927017984"`. Stock `LinkedInIE.suitable` stays `False` for it. `suitable` is `False` for `https://www.linkedin.com/in/someone/` and for a YouTube URL.
  - `YtDlpAdapter().inspect` on that address runs against a fake transport that serves `linkedin-video-post-hyphen-code.html` for the page URL. Reuse the `MetadataHTTP` fake-transport pattern already used in `tests/contract/test_adapter_transports.py` for yt-dlp. It returns `metadata.platform == "linkedin"`, `metadata.media_id == "7508434034927017984"`, and two video options from `media.example.invalid`.
  - An upgrade pin: `inspect.getsource(LinkedInIE._real_extract)` contains `self._match_id(url)`. A failure message says to re-check research R7 before upgrading yt-dlp.
  - A picture post (a page with no `<video>`) makes the adapter raise `UNAVAILABLE`, so `SourceRouter` falls back to `linkedin_image` (assert through a router with a stub image adapter).

### Implementation for User Story 2

- [ ] T020 [US2] In `src/openmedia/sources/__init__.py`, replace `_LINKEDIN_POST_SLUG` with the research R6 rule:
  - Typed pattern: `^(?P<prefix>[^/?#\s]+)-(?P<type>activity|ugcPost|share)-(?P<id>\d{8,32})(?:-(?P<code>[A-Za-z0-9_-]{1,32}))?$`. The greedy prefix makes it the rightmost type word.
  - Untyped fallback: the current pattern with its code class widened to `[A-Za-z0-9_-]{1,32}` and its prefix class widened to `[^/?#\s]`. The type defaults to `activity`.
  - Keep `canonical_url = f"https://www.linkedin.com/posts/{segments[1]}"`.

  Pass T017.
- [ ] T021 [US2] In `src/openmedia/sources/ytdlp.py`:
  - Add `_linkedin_post_extractor()`, which imports `LinkedInIE` from `yt_dlp.extractor.linkedin` at call time, as `inspect` already imports `yt_dlp` lazily. It returns a cached subclass `OpenMediaLinkedInPostIE(LinkedInIE)` with:
    - `IE_NAME = "openmedia:linkedin:post"`
    - a coarse `_VALID_URL = r"https?://(?:www\.)?linkedin\.com/posts/[^/?#]+"`
    - `suitable(cls, url)`: `True` only when `recognize_source_url(url)` returns a `linkedin` route with `route_kind == "post"` and a path under `/posts/`. Catch `SourceAdapterError` as `False`.
    - `_match_id(cls, url)`: returns that route's `media_id`.

    The recognizer is thus the single source of truth for which addresses exist and what their ID is (research R6/R7). Add a docstring citing research R7: extraction is inherited, and only the address match widens.
  - In `YtDlpAdapter.inspect`, call `extractor.add_info_extractor(_linkedin_post_extractor()())` right after creating `yt_dlp.YoutubeDL(options)`.
  - Add `"openmedialinkedinpost": "linkedin"` to `_EXTRACTOR_PLATFORM`, placed **before** `"linkedin"`: the lookup uses `startswith`, and the key must not be shadowed.

  Pass T018 and T019.
- [ ] T022 [US2] Run `uv run pytest` until green. Record the quickstart §2 US2 rows in `specs/004-linkedin-share-links/validation.md` under "US2".

**Checkpoint**: US1 + US2 together cover both links from the 2026-09-23 run in controlled
tests. Commit `feat(004): phase 4 us2 hyphenated post codes`.

---

## Phase 5: User Story 3 - Refused links leave a diagnostic trace (Priority: P3)

**Goal**: Every message refused before a request starts writes one `refused` entry when the
diagnostic flag is on. A short-link request records its resolution outcome on the trace.
Nothing reaches the console.

**Independent Test**: With the diagnostic log on, a non-link message, an unsupported link, a
two-link message, and a group link each produce one `refused` entry with the right `reason`
and `links`. With it off, no file exists (quickstart §2 last rows, US3 scenarios 1–3).

### Tests for User Story 3

- [ ] T023 [P] [US3] Add failing tests to `tests/unit/test_diagnostics.py` for `JsonLineFormatter`:
  - A record with `links=["https://bit.ly/x", "https://lnkd.in/p/dMhfr6kG"]` and `resolved_url="https://www.linkedin.com/posts/x-share-7508424761698410497-2cX9"` keeps both values unredacted.
  - A URL in `reason`, `msg`, or `error` is still replaced by `<redacted-url>`.
  - A bot-token-shaped string inside `links` is still replaced by `<redacted-token>`.
- [ ] T024 [P] [US3] Add failing tests to `tests/integration/test_diagnostic_trace.py`, using the `trace` fixture and `BotHandlers(workflow).message` with updates shaped like `private_update` in `tests/contract/test_bot_errors.py`. Give them URL entities where needed, through a `parse_entities` stub.
  - Each case writes exactly one entry with `origin == "input"`, `stage == "refused"`, `chat_id`, `user_id`, the `reason`, and `links`:
    - `hello` → `no_link`, `[]`
    - `https://bit.ly/x` → `unsupported_link`, `["https://bit.ly/x"]`
    - a short link plus a YouTube link → `too_many_links`, both links
    - `https://lnkd.in/abc` → `unsupported_url`
    - `https://www.youtube.com/playlist?list=abc` → `unsupported_collection`
    - a group message holding `https://lnkd.in/p/dMhfr6kG` → `not_private`
  - No entry holds `hello` or any other message text. Six links store only the first 5. A 3,000-character link is cut to 2,048 characters.
  - A group message with no link writes nothing.
  - With the flag off (no `trace` fixture), the same messages create no file, and `capsys`/`caplog` for the console contain none of the links, chat IDs, or user IDs (FR-010).
  - A short-link request whose inspect stub raises `WorkerRemoteError("short_link_unresolved", "inspection", "not_found")` has an `inspection_finished` entry with `error_category == "short_link_unresolved"` and `resolution == "not_found"`.
  - A successful short-link request has `resolution == "resolved"` and `resolved_url` equal to the rebound query-free `request.source_url`. No entry anywhere contains `rcm=` or `utm_`.

### Implementation for User Story 3

- [ ] T025 [US3] In `src/openmedia/diagnostics.py`:
  - Extend `_KEEPS_URL` to `frozenset({"source_url", "links", "resolved_url"})`.
  - Add `reason`, `links`, `resolution`, and `resolved_url` to `_FIELD_ORDER` after `outcome`.
  - Update the comment above `_KEEPS_URL` to name the three fields.

  Pass T023.
- [ ] T026 [US3] In `src/openmedia/bot.py`:
  - Add `message_link_candidates(message) -> tuple[str, ...]` returning the raw `url` entity values and `text_link` URLs, or, when there are no such entities, the plain-text tokens that contain `://` or match `_BARE_SUPPORTED_HOST`. Make `message_links` call `supported_links(message_link_candidates(message))`.
  - Add `refusal_reason(chat_type, candidates, links, exc) -> str`, using the data-model "Refusal record" reason rules in their stated order.
  - In `BotHandlers.message`, call `diagnostics.event("refused", origin="input", reason=..., links=[link[:2048] for link in candidates[:5]], chat_id=chat.id, user_id=user.id)`, at the group-reply branch and in the `except` branch before `reply_text`.
  - Never pass message text.

  Pass the refusal cases of T024.
- [ ] T027 [US3] In `src/openmedia/coordinator.py`:
  - In `_record_failure`, add `resolution=detail` to the event when `detail := getattr(exc, "detail", None)` is in `RESOLUTION_FAILURES`.
  - In `submit`, when `_bind_identity` rebound a short-link request, add `resolution="resolved"` and `resolved_url=request.source_url` to the successful `inspection_finished` event.

  Pass the remaining cases of T024.
- [ ] T028 [US3] Run `uv run pytest` until green. Record US3 scenarios 1–3 in `specs/004-linkedin-share-links/validation.md` under "US3".

**Checkpoint**: All three stories pass independently. Commit
`feat(004): phase 5 us3 refusal diagnostics`.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T029 [P] Amend `specs/001-media-download/contracts/source-adapters.md` (LinkedIn recognized inputs, short-link resolution step, `head(follow_redirects=…)`, worker `error.detail`) and `specs/001-media-download/contracts/telegram-bot.md` (two new failure rows; `lnkd.in/p/` counts as a supported link). Mark each change "(amended by 004)" and link it to `specs/004-linkedin-share-links/contracts/`.
- [ ] T030 [P] Amend `specs/002-file-logging/contracts/diagnostic-log.md`: the "Flag on" guarantees now say links and identifiers appear on `received` and `refused` entries, and a query-free `resolved_url` may appear on `inspection_finished`. Amend `specs/002-file-logging/data-model.md`: the `origin` values gain `input`, and the entry fields gain `reason`, `links`, `resolution`, and `resolved_url`, with types and entries as in `specs/004-linkedin-share-links/data-model.md`. Mark each change "(amended by 004)".
- [ ] T031 [P] Update `README.md`'s supported-links description to say LinkedIn app share links (`lnkd.in/p/…`) are accepted. Add 004 rows to the "Where truth lives" table in `CLAUDE.md`: `specs/004-linkedin-share-links/tasks.md` (working on LinkedIn short links or post recognition) and `specs/004-linkedin-share-links/contracts/` (touching LinkedIn address recognition, short-link resolution, or refusal diagnostics).
- [ ] T032 [P] Add the two example cases from quickstart §3 (`linkedin-short-video`, `linkedin-hyphen-code`) to `tests/fixtures/live-sources.example.json` with `REPLACE_ME` placeholders. Confirm that `tests/live/test_sources.py` compares `expected_identity` with the inspected `metadata.media_id`, the resolved post ID, and not with the route's short code. Adjust that comparison if it does not.
- [ ] T033 Run the live checks in quickstart §3 and the manual Telegram run in §4, with `OPENMEDIA_DIAGNOSTIC_LOG=1`. Record in `specs/004-linkedin-share-links/validation.md` "Completion":
  - the SC-001 video and picture results
  - SC-002 timing differences from `inspection_finished.elapsed_seconds`
  - SC-003 results for `lnkd.in/p/dMhfr6kG` and `lnkd.in/p/dAjqaykT`
  - SC-005 refusal entries
  - `grep -c 'rcm=' logs/*.log == 0`
  - remaining limitations: non-`/p/` `lnkd.in` paths and other shorteners stay unsupported, login-only posts stay unavailable, and the R7 yt-dlp coupling needs re-checking on upgrade
- [ ] T034 Update `specs/003-streamlined-bot-ux/validation.md` "Remaining limitations": mark the LinkedIn short-link item resolved by 004, with a link to `specs/004-linkedin-share-links/validation.md`. Run `uv run pytest` and `uv run python -m openmedia --check-config` a final time.

---

## Dependencies & Execution Order

- **Phase 1** → **Phase 2** → US1 → US2 → US3 → Polish. Per CLAUDE.md, phases are strictly
  sequential, with one commit per phase.
- US1 depends on T003 (no-follow `HEAD`), T005 (categories and `RESOLUTION_FAILURES`), and
  T007 (worker `detail`).
- US2 is functionally independent of US1. It touches the same `recognize_source_url` in
  `src/openmedia/sources/__init__.py`, so it runs after US1 to avoid conflicting edits.
  SC-003's `dMhfr6kG` passes only once both are done.
- US3 needs T005/T007 (`RESOLUTION_FAILURES`, `detail`) and T015 (`_bind_identity`, for the
  `resolved_url` field).
- Within a phase, each test task comes before its implementation task. T020 must come before
  T021, whose `suitable` relies on the new slug rule. T012 must come before T014, which needs the
  `short_link` route.

## Parallel Opportunities

- Phase 2: the tests T002, T004, and T006 are separate files. T003, T005, and T007 touch
  `network.py`, `sources/__init__.py` + `bot.py`, and `workers.py`, so they can also run
  together. T003 and T005 both edit `sources/__init__.py` (protocol vs enum), so merge those
  two edits in sequence.
- US1 tests: T008, T009, T010, and T011 are separate files.
- US2 tests: T017, T018, and T019 are separate files.
- US3 tests: T023 and T024.
- Polish: T029, T030, T031, and T032.

```text
# US1 test batch
T008 tests/unit/test_links.py
T009 tests/contract/test_linkedin.py
T010 tests/contract/test_adapter_transports.py
T011 tests/integration/test_download_flow.py
```

## Implementation Strategy

- **MVP = Phases 1–3 (US1).** Phone users' short links work whenever the destination
  address matches today's slug rule (a four-character code, for example `dAjqaykT`), for
  both video and picture posts. A destination with a hyphenated code (`dMhfr6kG`) is
  refused as `not_a_post` until US2. Stop here, run quickstart §4 with `dAjqaykT`, and
  decide whether to continue.
- US2 closes the `-lwx-` gap, about half of the observed short links. US3 is diagnostics
  only and changes nothing users see.
- Rough effort with tests: Phase 2 ≈ 1.5 hours, US1 ≈ 3 hours, US2 ≈ 2 hours, US3 ≈ 2 hours,
  Polish ≈ 1 hour, plus the manual run.

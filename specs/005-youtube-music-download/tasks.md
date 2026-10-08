# Tasks: YouTube Music Downloads

**Input**: Design documents from `specs/005-youtube-music-download/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/music-links.md), and [quickstart.md](quickstart.md).

**Tests**: Included because the specification explicitly calls for controlled acceptance,
regression, byte-preservation, and failure validation. Write acceptance tests before their
corresponding behavior changes and confirm the new assertions fail for the intended reason.
Existing foundation tests must pass before starting a user-story phase.

**Organization**: Six sequential phases, following CLAUDE.md. Each story has its own
independent acceptance checkpoint. Implementation is scoped to one phase per invocation.

## Format: `[ID] [P?] [Story] Description`

`[P]` identifies independent work within a phase after its stated prerequisites; it does
not authorize overlapping phases or concurrent edits to the same file. Story labels map to
spec.md. All paths below are repository-relative. Mark tasks complete only after their
implementation and required checks pass; release checks stay open if unavailable.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the feature workspace and baseline without changing dependencies.

- [X] T001 Establish or reuse feature branch `005-youtube-music-download` following `CLAUDE.md`, preserve existing unrelated changes, confirm `.specify/feature.json` points to `specs/005-youtube-music-download`, and record the actual branch and starting commit in `specs/005-youtube-music-download/validation.md`.
- [X] T002 Run `uv sync --locked --group dev` and the baseline `uv run --locked pytest tests/unit tests/contract tests/integration` against `pyproject.toml` and `uv.lock`; record results and any pre-existing failures in `specs/005-youtube-music-download/validation.md`; retain exact dependency and runtime pins from research R1/R6.

**Checkpoint**: Feature workspace and baseline recorded; no source feature changes yet.

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared model and error vocabulary required by all stories.

- [X] T003 Add `MediaKind.AUDIO = "audio"` in `src/openmedia/models.py`; enforce the quoted data-model constraint "`media_count == 1`" for AUDIO alongside VIDEO/IMAGE, preserve "nonnegative optional duration" and "Missing values remain absent rather than fabricated," and cover valid/missing metadata, invalid duration, and multiple-item rejection in `tests/unit/test_models.py`.
- [X] T004 Add `music_collection` and `no_native_audio` to `ErrorCategory` in `src/openmedia/sources/__init__.py` with the quoted constraints "input stage" and "checking/inspection stage" respectively; verify error-envelope reconstruction accepts both and does not alter existing enum meanings in `tests/unit/test_source_contracts.py`.
- [X] T005 Verify AUDIO metadata and both new error categories survive the existing serialization in `src/openmedia/workers.py` using `tests/contract/test_adapter_transports.py` and `tests/integration/test_workers.py`; preserve the quoted constraints "Worker round trips must preserve AUDIO and the canonical music URL" and "Limits on serialized inspection output remain unchanged"; change serialization only if these tests expose a required compatibility fix.

**Checkpoint**: Model/error and worker compatibility checks pass. All user stories depend on this phase.

## Phase 3: User Story 1 — Download a shared track (Priority: P1, MVP)

**Goal**: One plain public track link produces one best eligible native audio file automatically.

**Independent Test**: Submit a plain music watch link through the fake Telegram flow with
multiple native audio versions. Assert one best-ranked document, unchanged bytes, zero taps,
no keyboard or video choices, and card progress ending in completion; repeat with missing metadata.

### Tests for User Story 1

- [X] T006 [P] [US1] Add plain-link recognition tests in `tests/unit/test_links.py` for canonical and bare/http-normalized music links, supported-host counting, idempotence, credential/lookalike rejection, and ordinary YouTube regressions; assert the data-model values `platform=youtube`, `route_kind=audio`, `urn_kind=None`, and "No context query, credentials, or fragment" on the canonical music URL.
- [X] T007 [P] [US1] Add sanitized mixed audio/video music inspection samples in `tests/fixtures/ytdlp/youtube-music.json`, document synthetic or capture provenance honestly in `tests/fixtures/ytdlp/PROVENANCE.md`, and add adapter assertions in `tests/contract/test_ytdlp.py` for native audio only, no merge pairs, trusted music canonical identity even when webpage_url is ordinary YouTube, and rejection of wrong identity/collection/live output before applying audio intent.
- [X] T008 [P] [US1] Add AUDIO choice tests in `tests/unit/test_choices.py` for multiple native formats, known-size preference, unknown-size fallback, bitrate ranking and deterministic ties; assert "`option_id=0`, `automatic=True`, and an empty missing map" for success and "`automatic=False` and only `ChoiceKind.AUDIO` mapped to `not_offered` or `too_large`" for empty results.
- [X] T009 [P] [US1] Add full plain-track acceptance tests in `tests/integration/test_youtube_music_flow.py` using injected clocks and fake Telegram delivery: card with/without artwork/title/duration, no selection keyboard, exactly one source-byte-identical document, accurate status, shared YouTube rate bucket, and no conversion, merge, or tag rewriting calls.

### Implementation for User Story 1

- [X] T010 [US1] Extend supported-host, bare-link normalization, and `recognize_source_url` in `src/openmedia/sources/__init__.py` for plain music `/watch` links; require the quoted constraint "One `v`, existing YouTube ID grammar" (`[A-Za-z0-9_-]{6,64}`), parse blank values explicitly, refuse repeated/blank/malformed IDs, and return a stable `https://music.youtube.com/watch?v=<id>` audio route without modifying ordinary YouTube handling (FR-001, FR-010; T006).
- [X] T011 [US1] Pass trusted recognized route context from `YtDlpAdapter.inspect` into `normalize_info` in `src/openmedia/sources/ytdlp.py`; enforce "Apply intent only after rejecting collections/live responses and checking extractor identity," bind AUDIO and the music canonical URL, emit only supported native audio-only options, retain size exclusions, omit video/merge generation, and classify an accessible no-audio result as `no_native_audio`; retain existing VIDEO defaults without music context (FR-003–FR-005, FR-010; T007).
- [X] T012 [US1] Add an AUDIO branch in `src/openmedia/choices.py` using existing `_pick_audio`, `_result`, and size/tie policy unchanged; ensure "`too_large` requires actual supported audio candidates blocked by the size policy, not merely an excluded video" and no missing-video entries appear in music ChoiceSets (FR-004; T008).
- [X] T013 [US1] Integrate AUDIO ChoiceSets with the existing atomic automatic-claim and card path in `src/openmedia/coordinator.py`, and thread music-aware status through `src/openmedia/presentation.py` as needed; use `Audio only — downloading…` for music without claiming only one upstream version, retain ordinary automatic-video wording, and reuse native document delivery without new request fields or states (FR-005–FR-006; T009).
- [X] T014 [US1] Run the plain-track unit/contract/integration tests from T006–T009 plus affected ordinary-video tests; record results, native-byte evidence, and US1 acceptance outcomes in `specs/005-youtube-music-download/validation.md`; do not count fixture success as live source evidence.

**Checkpoint**: Plain-track MVP works and can be demonstrated independently. Collection/context behavior is completed in US2 and the full failure matrix in US3.

## Phase 4: User Story 2 — Download only the shared track from listening context (Priority: P2)

**Goal**: Shared listening context identifies one whole track, while collection-only links are refused.

**Independent Test**: Send plain/context/offset variants of one track in separate requests;
each downloads only the same complete track. Submit album/playlist-only links and verify no
inspection/download. Ordinary YouTube links keep their existing video behavior.

### Tests for User Story 2

- [X] T015 [P] [US2] Extend `tests/unit/test_links.py` with music v+list/index/radio/si/t links, repeated identical/conflicting/blank v values, playlist-only/watch-list-only, `/browse/MPREb_…` album, other browse/search/artist/home paths, and ordinary YouTube list rejection; pin each outcome to `specs/005-youtube-music-download/contracts/music-links.md`.
- [X] T016 [P] [US2] Add context and expired-URL cases to `tests/integration/test_refresh.py` proving source parameters never reach extraction, music canonical URL and AUDIO survive refresh, only the same selected native format is refreshed under the original deadline, and a changed/missing format never falls back to video or another audio version.
- [X] T017 [P] [US2] Add collection-only message tests in `tests/contract/test_bot_errors.py` for `Only one track is supported. Send a YouTube Music track link.` with zero source work; retain ordinary collection and unsupported-page guidance and exactly-one-link refusals.

### Implementation for User Story 2

- [X] T018 [US2] Complete music-specific context stripping and collection classification before ordinary YouTube playlist rejection in `src/openmedia/sources/__init__.py`: valid watch v requests one complete item, repeated v is malformed before collection classification, `/playlist` and album `/browse/MPREb_…` are `music_collection`, other browse/search/artist/home pages are unsupported, and ordinary YouTube list links remain unchanged (FR-002, FR-007; T015).
- [X] T019 [US2] Map `music_collection` to the contract's single-track guidance in `src/openmedia/bot.py`, keep pre-admission diagnostic handling intact, and verify `SourceRouter.download` in `src/openmedia/sources/__init__.py` re-inspects the retained music canonical URL with exact-option matching; repair intent/identity loss only if exposed by T016 (FR-002, FR-007, FR-010; T016–T017).
- [X] T020 [US2] Extend `tests/integration/test_youtube_music_flow.py` with separately submitted plain/context/offset links, proving exactly one complete track per request, no playlist-member work, and ordinary YouTube choices unchanged; run T015–T017 and record US2 evidence in `specs/005-youtube-music-download/validation.md`.

**Checkpoint**: Shared listening context is bounded to one track and refresh preserves intent.

## Phase 5: User Story 3 — Understand why music cannot be delivered (Priority: P2)

**Goal**: Distinct actionable explanations for unsupported, inaccessible, unavailable-audio,
size, source, and delivery failures, with no unintended video or duplicate delivery.

**Independent Test**: Inject each failure from US3 and the edge-case matrix; verify correct
category, explanation/next step, no unintended file, and cleanup within existing limits.

### Tests for User Story 3

- [ ] T021 [P] [US3] Add music no-audio/oversize failure assertions in `tests/contract/test_ytdlp.py`: no formats, video-only, all audio over limit with fitting video, malformed response, wrong identity, live/upcoming/post-live, and source-unavailable; preserve excluded-audio diagnosis and do not relabel network/identity failures as missing audio.
- [ ] T022 [P] [US3] Add user-facing music failure tests in `tests/contract/test_bot_errors.py` covering `no_native_audio`, size, unavailable, rate limiting, timeouts, changed format, failed/uncertain send, and retry wording; absent-audio text must be `The source has no downloadable native audio-only option. Send another public track link.` and never suggest choosing video.
- [ ] T023 [P] [US3] Add music lifecycle failures in `tests/integration/test_failure_cleanup.py` with injected clocks: checking/download/send deadline, cancellation/shutdown, unknown-size output over cap, and storage exhaustion; assert 60s inspection/600s processing accounting, existing reap reserve and cleanup, no oversized upload, and no automatic resend of uncertain delivery.

### Implementation for User Story 3

- [ ] T024 [US3] Classify empty AUDIO ChoiceSets in `src/openmedia/coordinator.py` using only audio reasons: `too_large` maps to TOO_LARGE and `not_offered` to NO_NATIVE_AUDIO; retain existing nonmusic classification and preserve unavailable/rate-limit/timeout/format-change categories (FR-008–FR-009; T021).
- [ ] T025 [US3] Map `no_native_audio` to the music contract wording in `src/openmedia/bot.py`, preserve stage-specific size and source/send failure guidance, and ensure accepted music failures end the existing card with explanation and next step rather than exposing exceptions (FR-008; T022).
- [ ] T026 [US3] Add music busy, concurrent-user isolation, duplicate submission/callback, and restart cases in `tests/integration/test_request_isolation.py`; add diagnostic-on/off accepted-failure and pre-admission refusal coverage in `tests/integration/test_diagnostic_trace.py`, proving links/identifiers only appear in enabled diagnostics and tokens/cookies never appear (FR-009–FR-011).
- [ ] T027 [US3] Run T021–T023 and T026 plus the affected existing failure suites; fix any exposed music-path lifecycle/privacy regression in `src/openmedia/coordinator.py`, `src/openmedia/sources/ytdlp.py`, or `src/openmedia/bot.py` without widening deadlines/access rules; record US3 category, cleanup, duplicate-prevention, and diagnostic evidence in `specs/005-youtube-music-download/validation.md`.

**Checkpoint**: Full controlled music success and failure matrix passes; no video fallback.

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Align support documentation and obtain controlled, live, and deployment evidence.

- [ ] T028 [P] Update user help/start/input guidance in `src/openmedia/bot.py` and assertions in `tests/contract/test_bot_preview.py` to name YouTube Music single-track downloads without promising MP3, playlists, subscriptions, or inline playback; retain normal video/picture guidance.
- [ ] T029 [P] Update `README.md`, `CLAUDE.md`, `specs/001-media-download/contracts/source-adapters.md`, `specs/001-media-download/contracts/telegram-bot.md`, `specs/003-streamlined-bot-ux/contracts/choice-policy.md`, and `specs/003-streamlined-bot-ux/contracts/telegram-bot.md` to reference feature 005's source support, AUDIO policy, music card/status exception, error meanings, and scope while preserving all inherited architecture/security rules.
- [ ] T030 [P] Extend `tests/fixtures/live-sources.example.json` with `youtube-music` and `youtube-music-context` audio cases; update `tests/live/test_sources.py` to assert AUDIO/music canonical identity, apply the audio choice policy, and verify the selected native format; retain `@pytest.mark.live` and sanitized placeholders, and keep controlled tests offline.
- [ ] T031 Run `uv run --locked pytest tests/unit tests/contract tests/integration` and `uv build` after T028–T030; record commands, results, FR-001–FR-011 and SC-001–SC-005 coverage, and remaining release limitations in `specs/005-youtube-music-download/validation.md` following `specs/005-youtube-music-download/quickstart.md`.
- [ ] T032 Run the opt-in plain/context music checks via `uv run --locked pytest -m live tests/live/test_sources.py` with an operator-supplied public manifest outside version control; record pinned versions, date/region, per-case identity/format/byte counts and anonymous availability in `specs/005-youtube-music-download/validation.md`; leave this task open if no passing live samples are available.
- [ ] T033 Validate the private-chat plain/context/collection/ordinary-YouTube flow from `specs/005-youtube-music-download/quickstart.md` using `scripts/dev.sh` and authorized bot credentials; record card/progress, one native document, byte comparison where available, and refusal/regression evidence in `specs/005-youtube-music-download/validation.md`; leave open if credentials or manual evidence are unavailable.
- [ ] T034 Build `Dockerfile` with `docker build --tag openmedia:local .` and perform README's bounded-storage startup/health smoke check with runtime-injected credentials; record outcomes and any limitations in `specs/005-youtube-music-download/validation.md`, then review alignment with `.specify/memory/constitution.md`; leave deployment readiness unclaimed if build/startup or required live/manual checks remain incomplete.

**Checkpoint**: All controlled checks pass. Release readiness requires actual live, manual,
and container evidence; unavailable checks remain explicitly unchecked.

## Dependencies & Execution Order

```text
Phase 1 Setup (T001–T002)
  → Phase 2 Foundation (T003–T005)
    → Phase 3 US1 (T006–T014)
      → Phase 4 US2 (T015–T020)
        → Phase 5 US3 (T021–T027)
          → Phase 6 Polish (T028–T034)
```

- Setup: T001 precedes T002. Foundation: T003/T004 precede T005; finish all before US1.
- US1: T006–T009 are independent test-writing tasks once the foundation passes; they precede
  T010–T013. T010 precedes T011; T012 uses only the foundation but is executed after prior
  numbered tasks in a sequential run. T011/T012 precede T013; T014 validates the whole story.
- US2: T015–T017 can be written independently after US1. T018 precedes T019, and T020 verifies
  both route behavior and the already established delivery flow.
- US3: T021–T023 can be written independently after US2. T024 precedes T025; T026 adds the
  lifecycle/privacy matrix; T027 verifies all fixes and tests.
- Polish: T028–T030 are independent after US3; T031 follows all three. T032/T033/T034 then
  collect release evidence. Do not mark tasks complete merely because checks were skipped.
- US2 and US3 build on US1's usable downloader; they are independently verifiable increments,
  not alternative implementations. Do not overlap story phases because they edit common files.

## Parallel Execution Examples

**US1**: After Phase 2, T006 (`tests/unit/test_links.py`), T007 (music fixture and
`tests/contract/test_ytdlp.py`), T008 (`tests/unit/test_choices.py`), and T009
(`tests/integration/test_youtube_music_flow.py`) can be prepared in parallel.

**US2**: After US1, T015 (`tests/unit/test_links.py`), T016
(`tests/integration/test_refresh.py`), and T017 (`tests/contract/test_bot_errors.py`) have
separate files and no dependencies on one another.

**US3**: After US2, T021 (`tests/contract/test_ytdlp.py`), T022
(`tests/contract/test_bot_errors.py`), and T023 (`tests/integration/test_failure_cleanup.py`)
can be prepared in parallel.

**Polish**: T028, T029, and T030 can proceed together because their paths do not overlap.
These examples describe scheduling opportunities; no sub-agent delegation is required.

## Implementation Strategy

### MVP First

Complete Setup, Foundation, and US1, then validate a plain public track's automatic native
audio delivery. This is the smallest useful demo. US2 and US3 remain required for the full
specified feature; a plain-link demo is not a release support claim.

### Incremental Delivery

Complete one phase per implementation invocation as required by CLAUDE.md. Record evidence
in validation.md and mark tasks as each phase passes. Commit at phase boundaries using
`feat(005): phase N <description>` with only related changes. Add context handling in US2,
complete failure explanations and lifecycle checks in US3, then finish documentation and
release validation. Preserve dependency pins and existing unrelated changes throughout.

## Notes

- No database, queue, additional service, new downloader, source credentials, conversion,
  metadata rewriting, or source-client changes are part of these tasks.
- Controlled tests use sanitized fixtures, fake Telegram transport, and injected clocks.
- New tests must check observable behavior or failure boundaries, not mirror implementation.
- Plans and tasks do not establish live success; record real-source and deployment limits honestly.

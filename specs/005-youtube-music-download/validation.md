# Validation: YouTube Music Downloads

## Phase 1 — Setup

- Date: 2026-10-08.
- Actual branch: `005-youtube-music-download` (created from `main`).
- Starting commit: `31d2ceaa47c38b523ec5786bf0663c428746b2c5`.
- `.specify/feature.json` already points to `specs/005-youtube-music-download`.
- Requirements checklist: 16 checked, 0 unchecked; passed without edits.
- Existing unrelated changes preserved: untracked root `AGENTS.md` and modified tracked
  `.specify/scripts/python/__pycache__/common.cpython-314.pyc`. Existing feature design
  documents were untracked at the start and are retained with the feature.
- Verified Python and Docker ignore files cover secrets, media, virtual environments,
  build artifacts, and caches; no missing critical patterns required changes.
- `uv sync --locked --group dev`: PASS; resolved 29 packages, checked 25 packages.
  The sandbox initially denied access to uv's cache; the approved rerun succeeded.
- Dependency and runtime pins remain unchanged: Python `>=3.13,<3.14`,
  `python-telegram-bot==22.8`, `yt-dlp[default]==2026.8.19`, and
  `instaloader==4.15.3`; existing FFmpeg/ffprobe and Deno configuration retained.
- `uv run --locked pytest tests/unit tests/contract tests/integration`: PASS;
  648 passed, 20 warnings in 5.21s on Python 3.13.16 / pytest 9.1.1.
  No pre-existing test failures. Warnings are existing python-telegram-bot
  `retry_after` deprecations (18 delivery-error cases, 2 runtime cases).
  The sandbox initially denied uv cache access; the approved rerun succeeded.
- `pyproject.toml` and `uv.lock` have no changes after sync and validation.
- No `.specify/extensions.yml` exists; no pre/post implementation hooks registered.
- Phase 1 tasks T001–T002 complete; Phases 2–6 remain unchecked.

Phase 1 establishes the workspace and existing controlled baseline only. It does not
establish YouTube Music support or live, Telegram, or deployment readiness.


## Phase 2 — Foundational

- Date: 2026-10-08; branch: `005-youtube-music-download`.
- Requirements checklist remains 16 checked / 0 unchecked. Existing Python/Docker
  ignore patterns remain sufficient; dependency/runtime pins unchanged.
- T003: added AUDIO media kind and single-item validation. Tests cover absent and
  supplied metadata, zero/positive duration, negative duration, invalid counts,
  and blank title rejection.
- T004: added `music_collection` (input) and `no_native_audio` (inspection);
  reconstruction tests preserve category/stage and existing error meanings.
- Test-first check: 10 new model/error cases failed on absent enum values before
  implementation; all 24 model/error tests passed after implementation.
- T005: JSON inspection/download payload round trips preserve AUDIO, music canonical
  identity and native audio options. Subprocess protocol tests preserve both error
  categories and AUDIO metadata; an oversized music result is rejected under the
  existing bounded protocol. No changes to workers.py or serialization limits needed.
- During test development, corrected fixtures to respect existing audio-option and
  nonempty-inspection invariants and the protocol's `value` result key.
- `uv run --locked pytest tests/unit tests/contract tests/integration`: PASS;
  664 passed, 20 existing Telegram deprecation warnings in 4.76s.
- No extension hook configuration exists at pre/post checks.
- T003–T005 complete. Phase 3 and later remain unchecked; this foundation does not
  establish live music extraction, automatic delivery, or release readiness.


## Phase 3 — US1: Plain-track automatic delivery

- Date: 2026-10-08; branch: `005-youtube-music-download`.
- Checklist: requirements.md 16 checked / 0 unchecked. Foundation checkpoint:
  61 model/error/adapter-transport/worker tests passed before story implementation.
- T006/T010: exact music host and bare/http normalization produce stable youtube/audio
  routes; invalid/blank/repeated identifiers, fragments, credentials and lookalikes
  are refused. Supported-link counting includes music; ordinary YouTube stays video.
- T007/T011: synthetic mixed-format fixture and provenance added. Trusted route identity
  is checked before applying AUDIO; canonical music identity survives ordinary YouTube
  webpage metadata. Only supported native audio options remain, including size exclusions;
  no merge pairs. Empty native audio yields `no_native_audio`. Collection/live and wrong
  identity retain their existing categories. Adapter test confirms canonical extraction
  and the shared YouTube metadata rate bucket.
- T008/T012: audio choices reuse known-size preference, unknown-size fallback, bitrate,
  exact-size and option-ID ties. Successful output is automatic ID 0 with no missing map;
  empty output has only an audio reason, unaffected by excluded video.
- T009/T013: real coordinator atomic automatic claim, card rendering, native adapter
  download and document delivery pass for full and absent metadata. No new coordinator
  states or claim logic were necessary. Runtime preview receives media kind so the first
  status is `Audio only — downloading…`; automatic video wording remains covered by
  existing regression checks.
- Native-byte evidence: tests generate one second of synthetic sine-wave Opus/WebM
  source audio in private pytest directories (existing CC0 fixture convention). Scripted
  transport supplies those bytes to the real adapter; fake Telegram receives exactly the
  same bytes in one document. Merge is forbidden and download subprocess calls permit only
  ffprobe, so conversion/tag rewriting cannot satisfy the tests. No selection tap/keyboard;
  progress is checking → downloading → sending → completed, including missing metadata.
- Test-first checkpoint: 21 failures / 104 passes across the four affected suites before
  implementation, caused by absent music recognition, route context and audio-only policy.
- Regression found and fixed during implementation: canonical extraction initially changed
  LinkedIn trailing-slash requests; canonical extraction is now restricted to music routes.
  Corrected the scripted adapter test transport to support the existing HTTP hook binding.
- T014: `uv run --locked pytest tests/unit tests/contract tests/integration --tb=short`:
  PASS; 694 passed, 20 existing Telegram deprecation warnings in 5.05s.
- Dependency pins, worker protocol, deadlines and delivery limits unchanged. Python/Docker
  ignores remain sufficient. No extension configuration exists at pre/post checks.
- T006–T014 complete. This is controlled plain-track MVP evidence, not live source evidence.
  Collection/context acceptance, full music failure wording/lifecycle and release checks
  remain in Phases 4–6; release support is not claimed.


## Phase 4 — US2: Listening context and exact refresh

- Date: 2026-10-08; branch: `005-youtube-music-download`.
- Requirements checklist: 16 checked / 0 unchecked. Existing Python/Docker ignores
  remain sufficient; no extension configuration exists at pre/post checks.
- T015/T018: listening list/index/radio/si/t parameters are stripped from valid watch
  routes; repeated/blank/malformed v takes precedence over collection classification.
  Playlist, watch-list-only and MPREb_ album targets produce `music_collection`;
  artist/search/home/other browse targets remain unsupported. Ordinary YouTube list
  links retain `unsupported_collection`.
- T016: real router, yt-dlp inspection normalization, guarded transport download and
  media validation cover expired native audio URLs. Refresh uses the retained music
  canonical URL, preserves AUDIO and the original deadline, and downloads only format
  140. Generated AAC/M4A bytes remain identical. Missing/changed format cases (including
  remaining video and another audio version) stop with `format_unavailable` before a
  second media request. No router/refresh implementation repair was needed.
- T017/T019: exact refusal text is `Only one track is supported. Send a YouTube Music
  track link.` Handler tests assert zero inspection/download/delivery/status work for
  playlist-only, watch-list-only and album links. Existing pre-admission logging remains
  unchanged; privacy regressions are covered by the full controlled suite.
- Test-first checkpoint: 8 failed / 129 passed before implementation in link, bot-error
  and refresh suites. Failures were the missing collection category and refusal text;
  context stripping and exact refresh already passed.
- Adapter extraction assertions now cover a context input and prove only the canonical
  music URL reaches extraction, with the same YouTube metadata rate bucket.
- T020: plain/context/offset variants submitted separately pass with full and absent
  metadata, one unchanged complete native audio document per request, no keyboard/taps,
  no conversion or tag rewriting. An ordinary YouTube submission still exposes video,
  silent video and audio choices and waits for selection without downloading.
- Affected link/bot-error/adapter/refresh/music-flow checks: 171 passed in 1.71s before
  adding the explicit ordinary-YouTube flow regression.
- `uv run --locked pytest tests/unit tests/contract tests/integration --tb=short`:
  PASS; 726 passed, 20 existing Telegram deprecation warnings in 5.76s.
- T015–T020 complete. Dependency/runtime pins, deadlines, limits and worker protocol
  unchanged. Phases 5–6 remain open; no live source or release readiness claim.


## Phase 5 — US3: Music failures, isolation and privacy

- Date: 2026-10-08; branch: `005-youtube-music-download`.
- Requirements checklist remains 16 checked / 0 unchecked. All 61 foundation checks
  passed before story implementation. Existing Python/Docker ignores remain sufficient;
  no extension configuration exists at pre/post checks.
- T021: controlled adapter failures cover empty/absent audio, video-only source, all
  audio oversized despite fitting video, malformed format-list shape, wrong identity,
  live/upcoming/post-live and unavailable/rate-limited/timeout source errors. Retained
  excluded audio options explain size failures without offering or falling back to video.
- Test-first adapter/message checkpoint: 3 failed / 93 passed. The intended failures
  exposed malformed formats labeled as no audio, absent dedicated no-audio wording,
  and empty AUDIO choices labeled as generic no-formats. All three were corrected.
- T022/T025: `no_native_audio` now maps to the exact contract message asking for another
  public track link. Stage-specific size, source-busy/unavailable/timeout, changed format
  and failed-send guidance remains. Runtime notification tests edit existing checking
  text or track caption with explanation/next step; uncertain send retains check-chat
  guidance and never sends another status message when the edit succeeds.
- T023: injected-clock/failure tests cover inspection/download/send timeout, cancellation
  at all three stages, storage exhaustion, unknown-size overflow and failed/uncertain send.
  Assertions preserve 60-second inspection / 600-second processing accounting with the
  existing five-second reap reserve (55/595 active budgets), release capacity, remove
  partial files and prevent repeat delivery. Shutdown actually cancels an event-gated
  music download through ManagedApplication.stop and removes the owned partial file.
- Unknown-size limit evidence includes the real native adapter and guarded transport:
  a 101-byte scripted source under a 100-byte configured cap raises ResponseTooLarge
  and leaves no selected file. The workflow test separately injects the existing worker
  `too_large` envelope and proves zero uploads and cleanup. Hosted cap remains 50,000,000.
- T024: empty AUDIO choices classify using only the audio missing reason: too_large
  remains TOO_LARGE; absent audio becomes NO_NATIVE_AUDIO. Nonmusic classification
  remains unchanged. Malformed non-null format-list shapes retain INVALID_SOURCE_RESPONSE.
- T026: event-gated concurrent music requests for the same track use independent IDs
  and bytes. Same-user/global busy admission, active and terminal duplicate callbacks,
  wrong-user callbacks and restart invalidation cannot add downloads or deliveries.
  Diagnostic-on/off accepted failure and collection-refusal tests prove links/Telegram
  IDs occur only in enabled diagnostics; tokens and cookie detail appear in neither
  diagnostics nor console. No source access or credential rules were widened.
- Test fixtures corrected during development to read delivery outcomes from the request
  rather than bounded terminal tombstones, model overflow at the worker boundary, and
  use the caption status surface and established uncertain-send wording.
- Cleanup/isolation/diagnostic suites: 74 passed in 1.28s before final card/byte-cap checks.
- T027: `uv run --locked pytest tests/unit tests/contract tests/integration --tb=short`:
  PASS; 766 passed, 20 existing Telegram deprecation warnings in 5.50s.
- T021–T027 complete. Dependencies, worker serialization, deadlines, access rules and
  runtime limits unchanged. Phase 6 documentation/live/manual/container checks remain
  unchecked; controlled success does not establish live availability or release readiness.


## Phase 6 — Documentation and controlled release checks

- Date: 2026-10-08; branch: `005-youtube-music-download`.
- Requirements checklist: 16 checked / 0 unchecked. Python/Docker ignores verified;
  dependency/runtime pins unchanged. No extension configuration exists at pre/post checks.
- T028: start/help/input/profile guidance names YouTube Music single tracks with automatic
  delivery while preserving ordinary video/picture guidance, 50 MB and 15-minute limits.
  Profile lengths remain within Telegram limits; no MP3/playlist/subscription/inline promise.
- T029: README, CLAUDE.md and affected 001/003 contracts describe AUDIO ranking, music
  canonical identity/refresh, card-status exception and both music errors, preserving all
  architecture/security constraints. Plan/quickstart status now reflects implementation
  and outstanding external evidence rather than the earlier planning stage.
- T030: sanitized live manifest template includes youtube-music and youtube-music-context.
  Opt-in suite asserts AUDIO/music canonical identity, uses production audio choice ranking,
  and verifies exact native format, media type and byte count. Existing source cases and
  live marker remain; no controlled test contacts an external source.
- T031: `uv run --locked pytest tests/unit tests/contract tests/integration --tb=short`:
  PASS; 767 passed, 20 existing Telegram deprecation warnings in 5.84s.
- `uv build`: PASS; built `dist/openmedia-0.1.0.tar.gz` and
  `dist/openmedia-0.1.0-py3-none-any.whl`. Initial sandbox uv cache denial was resolved
  by approved escalation. Build artifacts remain ignored.

### Controlled requirement coverage

| Requirement | Evidence |
| --- | --- |
| FR-001 | Music host/route, normalization, one-link and malformed-ID tests in test_links.py |
| FR-002 | Context/offset grammar, extraction canonical URL and whole-track music flow |
| FR-003 | Existing guarded anonymous adapter path reused; pinned extractor options and transport regression checks |
| FR-004 | test_choices.py audio pool/ranking/size/tie checks and automatic claim acceptance |
| FR-005 | Generated native audio delivered byte-for-byte; probe-only download with merge/conversion/tag-writing forbidden |
| FR-006 | Artwork/metadata card, missing metadata, automatic progress and existing failure-surface checks |
| FR-007 | Collection classification and handler refusal with zero source work |
| FR-008 | No-audio/oversize/malformed/identity/source/deadline/format/send failure matrix |
| FR-009 | Injected deadline/reserve accounting, capacity/duplicates/shutdown/cleanup and guarded byte-cap checks |
| FR-010 | Exact music refresh plus ordinary YouTube/LinkedIn/Instagram controlled regression suite |
| FR-011 | Diagnostic-on/off accepted failures and pre-admission refusals, console/token/cookie privacy assertions |

SC-001/SC-002 are covered by automatic one-document/no-tap ranking and exact native-byte
acceptance; SC-003 by plain/context/offset and collection zero-work checks; SC-004 by the
failure/deadline/cleanup matrix; SC-005 by ordinary-source regressions. These are controlled
checks, not real-source availability or measured Telegram timing evidence.

### Open external release checks

- T032 OPEN: OPENMEDIA_LIVE_MANIFEST is unset; no operator-supplied public manifest was
  available. `uv run --locked pytest -m live tests/live/test_sources.py` collected one test
  and skipped it in 0.01s. No plain/context sample identity, format, byte count or anonymous
  availability can be reported. No regional live evidence was collected (development
  timezone Europe/Helsinki; source region unverified). Pinned yt-dlp is 2026.8.19;
  Python 3.13.16 / python-telegram-bot 22.8 / instaloader 4.15.3 remain unchanged.
- T033 OPEN: no operator private-chat acceptance or received-document byte comparison
  was supplied. scripts/dev.sh and a real Telegram session were not launched for manual
  acceptance; no credentials were read or logged. Controlled fake-transport evidence
  does not complete this task.
- T034 OPEN: `docker build --tag openmedia:local .` failed before building because the
  Docker daemon socket `/Users/homan/.docker/run/docker.sock` does not exist. Docker CLI
  is installed, but no daemon was available. Bounded-storage startup and health checks
  with runtime-injected credentials therefore could not run. Constitution review confirms
  no new service/dependency/state/access exception, but container deployment verification
  remains required before release.

T028–T031 are complete. T032–T034 remain unchecked; Phase 6 and release readiness are
incomplete until passing live/manual/container evidence is recorded. Unrelated root AGENTS.md
and the pre-existing tracked Python cache modification remain outside the feature commit.


## Phase 7 — Convergence implementation

- Date: 2026-10-08; branch: `005-youtube-music-download`.
- Requirements checklist: 16 checked / 0 unchecked, left unchanged. Python and Docker
  ignore files verified against the current setup; no missing critical patterns found.
  No `.specify/extensions.yml` exists at pre/post checks, so no hooks were dispatched.
- T035: three test-first malformed-row cases failed with NO_NATIVE_AUDIO before the
  fix. Music format lists containing any non-mapping row now raise
  INVALID_SOURCE_RESPONSE. Empty, video-only and unsupported-native results retain
  NO_NATIVE_AUDIO; nonmusic malformed-row filtering remains unchanged. Mixed malformed
  and mapping rows are rejected as malformed rather than silently filtered.
- T039: event-gated inspection, download and send callbacks never raise TimeoutError
  themselves. A controlled monotonic clock and scheduler drive real asyncio timeout
  cancellation without sleeps. Tests observe CancelledError inside stalled callbacks,
  failure categories/stages, owned-file cleanup, capacity release, and unknown/no-resend
  behavior for interrupted upload. Inspection status consumes seven seconds; processing
  status consumes thirteen and download consumes two hundred before stalled sending.
  The effective deadlines stay at created_at + 60 - 5 and claim_time + 600 - 5;
  sending does not receive a new processing budget. Failure notification's separate
  five-second guard is also accounted for.
- Mutation validation: temporarily removing the inspection guard failed all three new
  cases; removing the processing guard failed download/send cases; resetting the send
  deadline failed the send case. Production source restored after each validation;
  no coordinator repair was required.
- Affected suites: `uv run --locked pytest tests/contract/test_ytdlp.py
  tests/integration/test_failure_cleanup.py --tb=short`: PASS, 72 passed in 1.39s.
- Full controlled validation: `uv run --locked pytest tests/unit tests/contract
  tests/integration --tb=short`: PASS, 777 passed, 20 existing Telegram deprecation
  warnings in 5.99s. Commands used a writable temporary UV_CACHE_DIR.
- `uv build`: PASS; source distribution and wheel built, ignored under dist/.
- T036/T032 OPEN: OPENMEDIA_LIVE_MANIFEST is unset. The opt-in live command collected
  one test and skipped it in 0.01s; no anonymous availability, format/bytes or region
  evidence is claimed. Operator manifest path requested; no manifest supplied during
  this invocation. Pinned versions remain those recorded in Phase 6.
- T037/T033 OPEN: no authorized operator test chat or manual acceptance evidence
  supplied. scripts/dev.sh and Telegram delivery were not launched; no credentials read.
- T038/T034 OPEN: `docker build --tag openmedia:local .` failed before building because
  `/Users/homan/.docker/run/docker.sock` does not exist. Container startup/health checks
  cannot run without a daemon and authorized runtime credentials. Constitution alignment
  remains unchanged: native bytes, anonymous access, bounded memory, existing deadlines,
  and one container; release readiness remains unclaimed.
- T035 and T039 complete; T032–T034 and T036–T038 remain unchecked. No phase-boundary
  commit made while external validation remains incomplete. Existing convergence task
  additions, root AGENTS.md and tracked Python cache modification were preserved.


## Phone playback follow-up — T040

- User reported successful music download with WebM unplayable on their phone. Supplied
  diagnostic trace records confirmed delivery of 4,034,743 bytes in 5.47 seconds; it does
  not include source format/codec or the full external acceptance matrix.
- Root cause: bitrate-first audio selection chose WebM/Opus over available AAC/M4A.
  Music AUDIO selection now first ranks eligible native AAC in M4A/MP4, then falls back
  to all native audio if none is eligible. Size/bitrate/tie rules remain within each group;
  unknown-size preferred AAC remains subject to the guarded download byte cap. Ordinary
  YouTube video/audio selection is unchanged. No conversion or metadata rewriting added.
- Test-first compatibility checkpoint: 3 failed / 4 passed before the selection change.
  Tests cover M4A and MP4 AAC preference, unknown size, oversized/excluded AAC fallback,
  and refusal to infer compatibility from an extension with Opus or absent codec.
- Plain/context/offset full-flow tests now generate AAC/M4A source bytes and assert native
  format 140, .m4a extension, one automatic document and exact delivered byte equality.
  Real adapter download still permits ffprobe only and forbids merge/conversion/tag rewrite.
- Specification, plan, data model, research, choice/adapter contracts, quickstart, README
  and CLAUDE.md amended to reflect the user-requested compatibility preference.
- `uv run --locked pytest tests/unit tests/contract tests/integration --tb=short`:
  PASS, 784 passed, 20 existing warnings in 5.50s (writable temporary UV_CACHE_DIR).
- T040 complete. Restart the running bot to load this code before retrying the track.
  On-phone playback of the new M4A selection is not yet verified. Existing full external
  release checks stay open; the user report is positive delivery evidence only.


## User acceptance update — 2026-10-08

- User confirmed "awesome, working now" after the AAC/M4A preference change, then
  asked to finalize the specification. This records successful real-user download and
  phone playback for the tested track, superseding the earlier playback-unverified note.
- Phone OS, track/context URL, selected codec/format details and received-file hash were
  not supplied. No claim of separate iOS and Android device testing is made.
- Feature specification status updated from Draft to Implemented with external release
  validation pending. Controlled acceptance remains 784 passing tests. Implementation
  and the reported phone-playback issue are complete.
- T032/T036 remain open for the specified plain/context live-manifest evidence.
  T033/T037 remain open for the remaining manual acceptance matrix (context/collection/
  ordinary YouTube, card progress and byte comparison where available). T034/T038
  remain open for container build/startup/health verification. User playback confirmation
  is accepted as partial manual evidence, without marking unperformed checks complete.

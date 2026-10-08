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

# Tasks: Media Delivery Titles

**Input**: Design documents from `specs/006-media-delivery-titles/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contract](contracts/telegram-bot.md), [quickstart.md](quickstart.md).

**Tests**: Included for the specification's controlled acceptance set, Unicode boundary,
byte-preservation, isolation, refresh/retry, and inherited failure requirements. Add tests
before the corresponding behavior change and confirm new assertions fail for the intended
reason. Use existing fake transports and injected clocks, without live traffic or sleeps.

**Organization**: Five sequential phases. Follow CLAUDE.md: implement one phase per
invocation, update this progress record, and commit at each completed phase boundary.

## Format: `[ID] [P?] [Story] Description`

All paths are repository-relative. `[P]` means independent files within the same phase,
after explicitly stated prerequisites; phases do not overlap. Story labels match spec.md.
Keep unavailable release checks unchecked and record their limitations.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish an auditable baseline and dependency closure.

- [X] T001 Confirm or reuse branch `006-media-delivery-titles` and active `.specify/feature.json`, preserve unrelated changes, and create `specs/006-media-delivery-titles/validation.md` recording starting commit, environment, and baseline `uv run --locked pytest` results before dependency changes.
- [X] T002 Add exact runtime pin `regex==2026.8.31` in `pyproject.toml`, regenerate `uv.lock` without unrelated upgrades, run `uv sync --locked --group dev`, verify Python 3.13 import and grapheme matching, and record installation and third-party notice/license findings in `specs/006-media-delivery-titles/validation.md` per research section 3.

**Checkpoint**: Baseline and dependency installation recorded; no delivery behavior changed.

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared pure title contract; no adapter, worker, or request schema expansion.

- [X] T003 Define the pure helper interface and immutable label pair in `src/openmedia/media_titles.py`: accept `title: str | None` and a validated selected `extension: str`, return caption and filename, and define code-point limit 64, complete-filename UTF-8 byte limit 240, and fallback `Untitled media`; enforce the data-model constraint "Its values must not be added to diagnostic events or exception messages" without adding persistent state or logging.

**Checkpoint**: Helper API is importable and ready for story behavior. Both stories require this phase.

## Phase 3: User Story 1 - Identify delivered media (Priority: P1, MVP)

**Goal**: The correct source title accompanies every delivered media type as caption and filename.

**Independent Test**: Deliver titled short safe-text samples through each supported source
and video/silent-video/audio/music/picture path. Assert correct caption, selected extension,
existing delivery method and hints, unchanged bytes, zero extra taps/messages, and no cross-request titles.

### Tests for User Story 1

- [ ] T004 [P] [US1] Add short safe-title helper assertions in `tests/unit/test_media_titles.py` for caption and filename, identical titles with different extensions, and source text already containing a suffix; quote and verify the data-model filename constraint "Safe stem plus dot and selected extension; extension outside stem budget; at most 240 UTF-8 bytes for the complete filename, including any ellipsis; upload label only".
- [ ] T005 [P] [US1] Extend `tests/integration/test_download_flow.py` with controlled YouTube, LinkedIn, Instagram, silent-video, audio, and picture cases asserting actual final media-call caption/filename, explicit `parse_mode=None`, no caption entities, preserved hints/methods/bytes, and unchanged preview-card policy.
- [ ] T006 [P] [US1] Extend `tests/integration/test_youtube_music_flow.py` to assert source track title on the single automatically sent document and its filename, native extension/bytes, zero selection taps, and no audio-player mode switch or embedded-tag changes.
- [ ] T007 [P] [US1] Extend `tests/integration/test_request_isolation.py` with concurrent differently titled requests and same-title requests; assert request-local labels and no local path collision or naming-based state sharing.

### Implementation for User Story 1

- [ ] T008 [US1] Implement ordinary titled-item label derivation in `src/openmedia/media_titles.py` from the source title and selected extension, returning the immutable pair without touching local media paths or file contents; keep complex normalization/shortening behavior for T014–T015.
- [ ] T009 [US1] Integrate `src/openmedia/delivery.py` with request.metadata.title_or_caption, tolerating absent metadata; derive labels after current identity/file validation and once before the retry loop, pass caption/filename and explicit `parse_mode=None` to both send methods, omit caption entities, and preserve streaming hints, opened file bytes, and all failure handling.
- [ ] T010 [US1] Run T004–T007 controlled acceptance and existing delivery-error checks, fix failures in `src/openmedia/media_titles.py` or `src/openmedia/delivery.py`, and record outcomes in `specs/006-media-delivery-titles/validation.md` before the phase commit.

**Checkpoint**: US1 is independently demonstrable with titled safe-text fixtures. This is
the MVP scope; release still requires US2's title hardening and final gates.

## Phase 4: User Story 2 - Receive media with imperfect title metadata (Priority: P2)

**Goal**: Missing, unsafe, long, and Unicode titles produce valid, bounded labels without blocking media.

**Independent Test**: Exercise missing/blank/control-only input, unsafe and reserved filenames,
63/64/65-code-point boundaries, complete filename byte boundaries 239/240/241, CJK and combined emoji. Assert literal captions, independent
caption/stem budgets, intact extensions, stable refresh/retry labels, and existing failure send counts.

### Tests for User Story 2

- [ ] T011 [P] [US2] Extend `tests/unit/test_media_titles.py` for None/blank/control-only/invisible-only fallback, whitespace-before-control cleanup, literal markup/Unicode, unsafe-character runs, traversal-like names, leading/trailing dots/spaces, reserved device basenames, unusable stems, and filename sanitization before shortening; verify "One line, whitespace collapsed, non-display controls removed, Unicode text preserved; neutral fallback when display-empty".
- [ ] T012 [P] [US2] Extend `tests/contract/test_delivery_errors.py` with missing metadata and imperfect-title uploads through both send methods, stable labels across definite RetryAfter retries, no resend on ambiguous outcomes, and unchanged blocked/timeout/invalid-output results; use injected clocks and verify upload bytes and send counts.
- [ ] T013 [P] [US2] Extend `tests/integration/test_refresh.py` with original-title and original-title-missing requests where refreshed metadata differs; prove final delivery retains the original title or fallback, media identity and exact selected format, and no additional title-only inspection or worker schema fields.

### Implementation for User Story 2

- [ ] T014 [US2] Implement full normalization, display-empty fallback, and independent safe-stem derivation in `src/openmedia/media_titles.py` per research section 4: whitespace normalization before controls, preserve ZWJ/ZWNJ and variation selectors, remove other non-display controls, replace unsafe runs with `_`, trim outer spaces/dots, protect reserved basenames, and fall back for unusable stems; never infer an extension from source text.
- [ ] T015 [US2] Add boundary tests and implement grapheme-safe shortening in `tests/unit/test_media_titles.py` and `src/openmedia/media_titles.py` using regex iterator `\X` with no NFC/NFKC rewriting; enforce "At most 64 code points; truncated only at grapheme boundaries, terminal ellipsis included in budget" and "Derived independently from full normalized title; unsafe runs replaced, reserved names protected, at most 64 code points"; cover 63/64/65 ASCII points, CJK, accents, flags, modifiers, ZWJ emoji, a first cluster exceeding 63 points, final stem trim, and extension exclusion from the code-point limit; also enforce "at most 240 UTF-8 bytes for the complete filename, including any ellipsis", reserving dot/extension bytes and three ellipsis bytes before whole-grapheme prefix selection; test complete filename lengths 239/240/241 bytes, 64 four-byte characters, and a cluster exceeding the remaining byte budget.
- [ ] T016 [US2] Run T011–T015 plus US1 regressions, confirm fallback and label stability without expanding `src/openmedia/models.py`, `src/openmedia/workers.py`, or `src/openmedia/sources/__init__.py`, fix only exposed title/delivery defects, and record results in `specs/006-media-delivery-titles/validation.md`.

**Checkpoint**: Both stories pass independently against their acceptance fixtures; no Unicode
cluster is split, no delivered caption or filename stem exceeds 64 code points, and
no complete filename exceeds 240 UTF-8 bytes including ellipsis, dot, and extension.

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Complete privacy, compatibility, packaging, and release evidence.

- [ ] T017 [P] Add or extend diagnostic regression assertions in `tests/integration/test_diagnostic_trace.py` so title labels do not introduce console output or new diagnostic payload fields, then record a review of `src/openmedia/media_titles.py` and `src/openmedia/delivery.py` for new state, storage, source requests, or credential-bearing errors in `specs/006-media-delivery-titles/validation.md`.
- [ ] T018 [P] Add feature-006 delivery cross-references to `specs/001-media-download/contracts/telegram-bot.md`, `specs/003-streamlined-bot-ux/contracts/telegram-bot.md`, and `specs/005-youtube-music-download/contracts/telegram-bot.md`; align `specs/006-media-delivery-titles/quickstart.md` with implemented paths/commands and keep existing preview title rules explicit.
- [ ] T019 Execute focused and full controlled suites, `uv build`, Docker build/import and configured startup checks from `specs/006-media-delivery-titles/quickstart.md`; confirm locked dependency installation and required third-party notices in built artifacts, record exact results in `specs/006-media-delivery-titles/validation.md`, and leave this gate open if required checks are unavailable.
- [ ] T020 Record real Telegram caption/saved-filename/client checks only if explicitly authorized, using the optional procedure in `specs/006-media-delivery-titles/quickstart.md`; otherwise document them as unverified in `specs/006-media-delivery-titles/validation.md`, reconcile every FR/SC with evidence, and update `specs/006-media-delivery-titles/spec.md` status without claiming unperformed checks passed.

**Checkpoint**: Controlled acceptance and release evidence are distinguished. No live Telegram
messages are sent merely because this task list exists; explicit authorization is required.

## Dependencies & Execution Order

```text
Setup T001 → T002
  → Foundational T003
  → US1 tests T004–T007 → T008 → T009 → T010
  → US2 tests T011–T013 → T014 → T015 → T016
  → Polish T017 + T018 → T019 → T020
```

US1 requires the shared foundation. US2 reuses US1's delivery integration and expands the
same helper, so story implementation is sequential to avoid concurrent edits. Each story
has a separate acceptance checkpoint. T015's new boundary assertions must fail before its
shortening implementation; T011–T013 must expose intended missing behavior first.

### Parallel Opportunities

Within US1, T004–T007 edit different test files and can run together after T003.
Within US2, T011–T013 edit different test files and can run together after T010.
T017 and T018 can run together after T016; reconcile validation.md evidence sequentially.
Do not run dependent source changes or phase commits in parallel.

## Parallel Example: User Story 1

```text
T004: helper happy-path tests in tests/unit/test_media_titles.py
T005: general media acceptance in tests/integration/test_download_flow.py
T006: music acceptance in tests/integration/test_youtube_music_flow.py
T007: concurrent request isolation in tests/integration/test_request_isolation.py
```

## Parallel Example: User Story 2

```text
T011: metadata and filename edge cases in tests/unit/test_media_titles.py
T012: send/retry/error contract in tests/contract/test_delivery_errors.py
T013: source refresh title stability in tests/integration/test_refresh.py
```

## Implementation Strategy

Complete Setup and Foundational first, then US1 for a working short-title MVP. Validate
its independent acceptance before adding US2 normalization and 64-character Unicode rules.
Complete Polish before declaring the feature release-ready. Follow the repository's one-phase
implementation and commit rhythm; do not mark tests, container checks, or manual checks passed
without evidence. No migrations, new services, callback formats, or worker schemas are needed.

## Requirement Traceability

| Requirements | Tasks |
|---|---|
| FR-001–002; SC-001 | T004–T010 |
| FR-003–005; SC-002 | T011–T012, T014–T016 |
| FR-006; SC-004 | T007, T009, T012–T013, T016 |
| FR-007–008; SC-003, SC-005 | T005–T006, T009–T010, T012–T013, T016, T019 |
| FR-009 | T017 |
| Dependency/container and documentation gates | T001–T002, T018–T020 |

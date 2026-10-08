# Implementation Plan: YouTube Music Downloads

**Branch**: `main` (actual checkout; setup reports feature key `005-youtube-music-download`) | **Date**: 2026-10-08 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-youtube-music-download/spec.md`

## Summary

Accept public single-track YouTube Music watch links and automatically deliver the best
eligible native audio file. Reuse the existing YouTube adapter and audio policy. Preserve
music-host canonical identity through inspection and refresh; add an audio media kind so
selection considers audio alone and the current automatic-claim path sends it without taps.
Do not change ordinary YouTube video routing or introduce new services or dependencies.

## Technical Context

**Language/Version**: Python 3.13 (`>=3.13,<3.14`).

**Primary Dependencies**: Existing `python-telegram-bot==22.8`,
`yt-dlp[default]==2026.8.19`, and `instaloader==4.15.3`; existing FFmpeg/ffprobe and bundled
Deno/EJS remain. No dependency or lockfile changes planned. License review is in research.md.

**Storage**: Existing bounded in-memory request registry and owned temporary job directories;
no database, queue, or persistent media. Optional diagnostic log follows feature 002.

**Testing**: pytest and pytest-asyncio, controlled fixtures, fake Telegram transport, injected
clocks; separate opt-in live checks. Unit, contract, integration, and regression coverage.

**Target Platform**: Existing single Linux container and local Python development environment.

**Project Type**: Telegram polling bot with isolated source-worker processes.

**Performance Goals**: One link submission, zero selection taps, one audio file; inspection
finishes within 60s and download/send within 600s at supported capacity. No live success rate
claim based solely on fixture validation.

**Constraints**: Anonymous access, unchanged native bytes, at most 50,000,000 output bytes,
no conversion or audio extraction from combined video. Existing configurable lower output
cap applies. Defaults: two shared workers, 100 pending requests, 134,217,728 bytes per job;
900s cleanup and selection-expiry policies, five-second reaping reserve remain unchanged.

**Scale/Scope**: One finished public item per music watch link. Album/playlist-only URLs,
search, accounts, live content, conversion, metadata rewriting, and shorteners excluded.

## Constitution Check

*GATE: Evaluated before research and re-evaluated after design.*

| Gate | Before research | After design | Evidence |
| --- | --- | --- | --- |
| I: downloading purpose and explicit scope | Pass | Pass | Public YouTube Music single-item native audio only |
| II: Telegram workflow and failures | Pass | Pass | Card, automatic file delivery, distinct actionable refusals |
| III: Python and simplest architecture | Pass | Pass | Existing adapter and worker lifecycle; no extra service |
| IV: reuse and dependency review | Pass | Pass | Pinned yt-dlp reused; research records license and alternatives |
| V: container deployment | Pass | Pass | Same runtime; build/startup smoke test required before release |
| Access, limits, storage, security | Pass | Pass | Existing anonymous guarded transport and bounded cleanup retained |
| Specification and validation gates | Pass | Pass | Spec reviewed; controlled and opt-in live matrix defined |

No constitutional exceptions required. Design is ready for tasks; deployment readiness still
requires implementation checks and recorded live results.

## Project Structure

### Documentation (this feature)

```text
specs/005-youtube-music-download/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/requirements.md
└── contracts/
    ├── music-links.md
    ├── source-adapters.md
    └── telegram-bot.md
```

`tasks.md` is produced by the next `$speckit-tasks` phase.

### Source Code (repository root)

```text
src/openmedia/
├── models.py                 # audio metadata kind and single-item validation
├── choices.py                # audio-only policy branch
├── coordinator.py            # audio-specific empty-choice failure classification
├── bot.py                    # music refusal text and input guidance
├── presentation.py           # accurate automatic music status
└── sources/
    ├── __init__.py           # music host and route recognition
    └── ytdlp.py              # trusted music context, audio-only normalization

tests/
├── unit/                    # links, models, choices, presentation
├── contract/                # adapter, worker transport, card/errors
├── integration/             # auto-send, refresh, cleanup, isolation
├── fixtures/ytdlp/          # sanitized music responses and provenance
└── live/                   # opt-in source matrix
```

**Structure Decision**: Extend existing modules. Worker dataclass serialization, guarded
HTTP, download verification, and document delivery are reused; test their compatibility
rather than introduce duplicate transport or music-downloader modules. Update README,
CLAUDE.md, and affected 001/003 contracts when implementation adds this supported workflow.

## Phase 0: Research Decisions

Resolved: URL recognition and collection boundary, native audio support, persistence of
music intent through refresh, deterministic ranking, message semantics, dependency reuse,
and validation boundaries. See [research.md](research.md). No unresolved design questions.

## Phase 1: Design and Validation

Use [data-model.md](data-model.md) and the three contracts below. Work proceeds in order:
link/model foundations; adapter and choice policy; automatic Telegram flow and errors;
regression and live/runtime validation. Implementation tasks are generated separately.

| Requirements | Design boundary | Validation |
| --- | --- | --- |
| FR-001–FR-002, FR-007 | music-links contract | parser/context/refusal matrix |
| FR-003–FR-005 | source-adapters contract | native formats, ranking, bytes |
| FR-006, FR-008 | Telegram contract | card, progress, refusal and failures |
| FR-009–FR-011 | inherited runtime/privacy and all contracts | deadlines, duplicates, refresh, cleanup, regression |

## Complexity Tracking

No constitution violations or additional architectural complexity requiring an exception.

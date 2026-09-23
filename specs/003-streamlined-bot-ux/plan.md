# Implementation Plan: Streamlined Bot UX

**Branch**: `003-streamlined-bot-ux` | **Date**: 2026-09-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-streamlined-bot-ux/spec.md`

## Summary

Replace the long numbered, paginated format list with one card (thumbnail, title, duration)
and up to three plainly labeled buttons: `Video`, `Video (no sound)`, `Audio only`. A new pure
choice policy picks at most one native version per kind from what the adapters already
return: phone-playable MP4/H.264 up to 720p on the shorter side for video, and the
highest-bitrate audio in any format. Nothing is converted. Pictures, and videos with a single
possible choice, are sent without a tap. Progress lives on one message edited in place.
Videos are sent with `sendVideo` so they play inline; audio and pictures stay documents.

## Technical Context

**Language/Version**: Python 3.13 (unchanged)

**Primary Dependencies**: python-telegram-bot 22.8, yt-dlp 2026.8.19, FFmpeg/ffprobe
(unchanged; no new dependency)

**Storage**: None. In-memory registry only (unchanged)

**Testing**: pytest; controlled tests with fixtures and the fake Telegram transport; one new
opt-in `live` test for inline video bytes

**Target Platform**: Linux container (unchanged)

**Project Type**: Single-process Telegram bot service

**Performance Goals**: No change to deadlines (60 s inspect, 900 s selection, 600 s
processing). At most 5 message edits per request (card, keyboard removal, downloading, sending, sent)

**Constraints**: No re-encoding or stream splitting; 50,000,000-byte delivery cap; callback
data carries an integer `option_id`; links and identifiers only via `openmedia.diagnostic`;
Telegram captions ≤ 1,024 characters

**Scale/Scope**: 3 sources (YouTube, Instagram, LinkedIn), 2 media kinds (video, image), 3
video choices. About 8 source modules touched, 1 new module

All Technical Context unknowns are resolved in [research.md](research.md):
phone-playable definition (R1), selection order (R2, R3), policy placement (R4), callback
shape (R5), card/status mechanics (R6), inline delivery and its live gate (R7), automatic claim
(R8), wording (R9), diagnostics (R10).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle / constraint | Status | Evidence |
|---|---|---|
| I. Social media downloading; spec names platforms, media types, journeys | Pass | Spec Assumptions and Stories 1–3 |
| II. Telegram is the UI; invalid/unsupported/failure/limit behavior defined; download logic separate from handlers | Pass | contracts/telegram-bot.md; policy is a pure module (R4); adapters change only in two narrow places |
| III. Python by default; simplest arrangement | Pass | No new service or language |
| IV. Reuse open source | Pass | Same yt-dlp/FFmpeg/PTB; no custom extraction |
| V. Container deployment | Pass | No image or runtime change; startup check still run |
| Output formats and delivery behavior stated | Pass | contracts/telegram-bot.md "Delivery method" |
| Limits and what users see when exceeded | Pass | `too_large` choice handling, R2 size filter |
| Timeouts, concurrency, cleanup | Pass | Unchanged; automatic claim keeps reservations (R8) |
| No credentials in logs | Pass | New diagnostic fields are fixed vocabularies (R10) |
| No DB/queue/service | Pass | None added |
| Project rule: deliver source-encoded streams, never re-encode | Pass | Policy only selects; merge stays `-c copy`; no splitting (clarification Q2) |
| Project rule: deliver unchanged | **Conditional** | `sendVideo` byte preservation is undocumented; live gate in quickstart §4 before US1 merges (R7) |

Post-design re-check: still passing. The one conditional item has a defined test and a
defined fallback, so it is a release gate, not a violation.

## Project Structure

### Documentation (this feature)

```text
specs/003-streamlined-bot-ux/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── telegram-bot.md
│   └── choice-policy.md
├── checklists/requirements.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
src/openmedia/
├── choices.py        # NEW: pure ChoiceSet policy (contracts/choice-policy.md)
├── presentation.py   # choice labels, card text, status text; drop numbered labels/sizes
├── bot.py            # card render/send, keyboard of labels, drop p: callbacks, help text
├── coordinator.py    # publish_and_claim; automatic path in submit; status surface tracking
├── models.py         # DownloadRequest.status_message_id / status_is_caption / status_prefix
├── delivery.py       # sendVideo for video kinds, sendDocument for audio/picture
├── sources/__init__.py, sources/ytdlp.py  # shared codec_family; unknown-codec probe
├── __main__.py       # runtime callbacks: edit-in-place status, card publish, failure edit
└── diagnostics.py    # no API change; new fields passed through event()

tests/
├── unit/test_choices.py                 # NEW
├── unit/test_option_labels.py           # rewrite for choice labels
├── contract/test_bot_preview.py         # rewrite: card, ≤3 buttons, no pagination
├── contract/test_bot_callbacks.py       # drop p: cases, add label confirmation
├── contract/test_delivery_errors.py     # sendVideo paths
├── integration/test_download_flow.py    # automatic image + single-choice flows, 2-message SC-004
└── live/test_inline_video.py            # NEW, live marker, R7 gate
```

**Structure Decision**: Keep the single-package layout from 001. The only new module is
`choices.py`, placed beside `presentation.py` because both are pure and Telegram-independent.
Source adapters change only in two narrow places: `codec_family` moves to
`src/openmedia/sources/__init__.py` (shared by the merge step and the policy), and
`src/openmedia/sources/ytdlp.py` gains a post-download H.264/AAC probe for MP4 video whose
codecs were unknown at inspection (research R1).

## Delivery order (for /speckit-tasks)

1. Foundational: `choices.py` + unit tests; model fields; `publish_and_claim`.
2. US1 (P1): card, labeled buttons, `sendVideo`, and the R7 live gate.
3. US2 (P2): automatic picture delivery (reuses `publish_and_claim`).
4. US3 (P3): edit-in-place status and failure text, 2-message check.
5. Polish: 001/002 amendments, help text, validation record.

## Second-order effects

- Existing 001 contract tests for pagination, numbered labels, and size text will fail by
  design. They are rewritten, not deleted silently. Each rewrite cites the 003 requirement.
- `ytdlp.normalize_info` imports `presentation.sort_options`, so it stays. The label helpers
  (`option_label`, `format_size`, `selected_label`) go; their callers are `bot.py`,
  `__main__.py`, `tests/unit/test_option_labels.py`, and `tests/contract/test_ytdlp.py`.
- The 001 help text promises "native choices before downloading anything", which is no longer
  true for pictures. It is updated.
- iOS users choosing `Audio only` on YouTube will often get an Opus `.webm` file (accepted in
  spec, clarification on audio).

## Complexity Tracking

No constitution violations to justify.

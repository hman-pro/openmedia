# Data Model: Streamlined Bot UX

Still ephemeral and in memory. This file lists only what changes relative to
`specs/001-media-download/data-model.md`; everything not named here is unchanged.

## ChoiceKind (new, derived)

A fixed vocabulary, derived from a `FormatOption` rather than stored on it.

| Kind | Derived from | Button / status label | Delivered with |
|---|---|---|---|
| `video` | `media_type=video`, `includes_audio=true` | `Video` | inline video |
| `silent` | `media_type=video`, `includes_audio=false` | `Video (no sound)` | inline video |
| `audio` | `media_type=audio` | `Audio only` | file |
| `image` | `media_type=image` | `Picture` (status only, never a button) | file |

Order is fixed: `video`, `silent`, `audio`. Diagnostic `choices` values use the kind names.

## ChoiceSet (new, transient)

The output of the pure policy in `choices.py` (research R2–R4). It is computed once per
inspection and not kept after the request is published.

| Field | Meaning and validation |
|---|---|
| options | 0–3 `FormatOption` records, at most one per kind, in kind order, rebound to `option_id` 0..n-1; each `availability=selectable`. For images, exactly the one image option |
| missing | For each absent kind among `video`, `silent`, `audio` (never `image`): `not_offered` (no candidate from the source) or `too_large` (candidates exist but none fits the delivery limit) |
| automatic | True when `options` has exactly one entry (FR-002a, pictures) |

Rules:

- `video` and `silent` candidates must be phone-playable (research R1): extension `mp4`, video
  codec family H.264, audio codec family AAC when `includes_audio`. An `mp4` with unknown
  codecs (`transport_ref` `vcodec`/`acodec` absent) is a last-resort candidate, used only when
  no known-codec candidate of that kind exists; the worker verifies H.264/AAC after download.
- Shorter side: `min(width, height)` when both are known, the one known dimension when only
  one is, unknown when neither is (research R2).
- `audio` accepts any adapter-accepted audio extension; highest bitrate wins (R3).
- No option is created, split, or re-encoded by the policy; it only selects among adapter
  options. A merged `<video>+<audio>` option is a valid `video` candidate.
- Empty `options` for a video → inspection ends with the existing `too_large` or `no_formats`
  failure meaning, chosen from `missing`.

## FormatOption (unchanged shape)

No new fields. `option_id` values are rebound by the policy. A request's `options` now holds
only the ChoiceSet options, so `claim_selection` can never select a non-kept option.

## DownloadRequest (changed)

| Field | Change |
|---|---|
| options | Now the ≤3 ChoiceSet options (was: every native option) |
| preview_message_id | For video: the card's message ID. For automatic requests: the status message ID. Callbacks still must match it |
| status_message_id | **New.** The message whose text or caption carries progress. Starts as the "Checking link…" message; becomes the card's ID once published. Positive integer or null |
| status_is_caption | **New.** True when the status surface is a photo caption (`editMessageCaption`), false for a text message (`editMessageText`) |
| status_prefix | **New.** Card text kept above the status line (title and duration) so each edit re-renders the full caption. Not logged |

## State transitions (changed)

```text
checking ──publish_preview──▶ awaiting_selection ──claim_selection──▶ downloading ─▶ sending ─▶ completed
    │                                                                      ▲
    └────────────── publish_and_claim (automatic: 1 option) ───────────────┘
```

- `publish_and_claim` (new registry operation, research R8) runs under the same lock and
  checks as `publish_preview` (still the active request, still `checking`, reservation held).
  It sets `metadata`, `options`, `preview_message_id`, `selected_option_id = 0`, and
  `processing_deadline = now + 600 s`, sets `state = downloading`, and **keeps** the work and
  Instagram reservations instead of releasing them. There is no `preview_expires_at`.
- If `publish_and_claim` does not return `ACCEPTED` (request replaced, no longer active, or
  no longer `checking`), the workflow raises `WorkflowError`; the request fails at stage
  `checking`, and the status surface (by then the card) shows the failure text instead of
  "downloading…" (analysis U4).
- All other transitions, expiry, replacement, and terminal records are unchanged.

## DeliveryResult (unchanged)

`confirmed` still requires a positive Telegram `message_id` and the actual byte count; the
Telegram message type (`video`, `animation`, `document`) is not part of the result.

## Diagnostic Log Entry (amends 002 data model)

| Key | Type | Present | Notes |
|---|---|---|---|
| `choices` | array of string | `inspection_finished` | Kept kinds, e.g. `["video","audio"]`; empty when none |
| `automatic` | boolean | `selection` | True when no tap was needed |

`options` on `inspection_finished` keeps its meaning: the number of native options the source
offered before the policy ran.

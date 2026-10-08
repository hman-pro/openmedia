# Data Model: YouTube Music Downloads

## SourceRoute (existing entity)

| Field | Music value | Validation |
| --- | --- | --- |
| platform | `youtube` | Shared extractor identity and rate-control bucket |
| media_id | Track ID | One `v`, existing YouTube ID grammar |
| canonical_url | `https://music.youtube.com/watch?v=<id>` | No context query, credentials, or fragment |
| route_kind | `audio` | Only music watch links receive this value |
| urn_kind | `None` | LinkedIn-only field unchanged |

Canonical recognition is idempotent. Music collection-only addresses produce a
`music_collection` refusal rather than a partial route. No new persistent entity is needed.

## MediaMetadata (existing entity extended)

Add `MediaKind.AUDIO = "audio"`. Include AUDIO with VIDEO and IMAGE in the single-item
`media_count == 1` invariant. Audio permits nonnegative optional duration and the existing
optional thumbnail, creator, and title fields. Missing values remain absent rather than
fabricated. AUDIO describes requested audio presentation even when YouTube calls the item a video.

For a trusted music route, metadata.platform remains youtube, media_id must match the input,
canonical_url remains the music URL, media_kind is AUDIO, and media_count is 1. Apply intent
only after rejecting collections/live responses and checking extractor identity. Do not
trust source-reported webpage host to infer music intent. Existing normalization callers
without music context keep VIDEO defaults and their current behavior.

## FormatOption and InspectResult (existing entities)

Music inspection contains only source-provided audio-only options. Fields and immutable
transport references are unchanged; retain availability and size exclusion data so an empty
selection can distinguish no audio from too-large audio. No synthetic merge format IDs,
combined video, or image options. Never modify the bytes to embed track metadata.

`InspectResult` continues to carry metadata, bounded options, and an optional local thumbnail.
Worker round trips must preserve AUDIO and the canonical music URL. Limits on serialized
inspection output remain unchanged.

## ChoiceSet (existing entity, new branch)

For AUDIO, first use `_pick_audio` on native AAC options in M4A/MP4 containers. If that
group has no eligible choice, use `_pick_audio` on all native audio options. A success returns one option with
`option_id=0`, `automatic=True`, and an empty missing map. Empty results have
`automatic=False` and only `ChoiceKind.AUDIO` mapped to `not_offered` or `too_large`.
`too_large` requires actual supported audio candidates blocked by the size policy, not merely
an excluded video. If none exists, use `not_offered`. Preserve known-size preference and
quality/tie rules documented in research R4 within each group, including unknown-size
fallback behavior. An unknown-size preferred AAC option can outrank known-size WebM;
download byte limits still apply.

## DownloadRequest and lifecycle (existing)

No new request field or database. The request's canonical music source URL and bound AUDIO
metadata retain intent; refresh uses the same canonical music URL. Request identity remains
random and per request, so two users sharing the same track do not share request state.

Successful flow: CHECKING → DOWNLOADING → SENDING → COMPLETED. `publish_and_claim` binds
metadata, one option, and card atomically; there is no user-visible AWAITING_SELECTION state
for music. Existing failure, replacement, timeout, shutdown, and cleanup paths still apply.
Uncertain Telegram delivery is never automatically resent. Inspection scratch cleanup must
not remove the downloaded media before upload, following the existing ownership lifecycle.

## ErrorCategory (existing enum extended)

- `music_collection`: recognized music album/playlist target without one track; input stage.
- `no_native_audio`: accessible finished music item has no supported downloadable native
  audio-only option; checking/inspection stage.

Propagate these values through the existing worker error envelope and diagnostic enum mapping.
Do not collapse `unavailable`, `too_large`, `rate_limited`, `timeout`, or identity/format changes
into missing audio. Generic no-formats normalization for nonmusic callers remains unchanged.

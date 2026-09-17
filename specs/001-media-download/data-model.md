# Data Model: Media Download Workflow

This model is ephemeral. Python data classes and in-memory maps are sufficient; no schema
migration or database is required. `spec.md` defines behavior; the contracts define boundaries.

## DownloadRequest

| Field | Meaning and validation |
|---|---|
| request_id | Random 128-bit identity, encoded as 32 hex characters; never reused |
| user_id, chat_id | Telegram integer identities; private chat required; do not infer ownership from username |
| source_url, platform, media_id | Validated canonical public source; recognized route and stable source item identity |
| state | checking, awaiting_selection, downloading, sending, completed, failed, expired, replaced |
| metadata | Optional MediaMetadata, populated by successful inspection |
| options | Ordered FormatOption records bound to this request; immutable after preview |
| selected_option_id | Null until one valid callback atomically claims the request |
| created_at, preview_expires_at, processing_deadline | Monotonic deadlines internally; UTC timestamps only for diagnostics |
| preview_message_id | Message owning the format keyboard; callbacks must match |
| work_directory, worker_pid | Internal handles only; no caller-supplied paths; absent while idle |
| delivery_result | Optional DeliveryResult |

Indexes: `requests_by_id` and `active_request_by_user`. Per-user locks protect both and are
removed when no state or task references them. Capacity admission and state changes must be
atomic relative to concurrent messages/callbacks. Old workers may publish results only if
the request ID and expected state still match; they cannot overwrite a replacement preview.

Validate the shape and recognized source route of a new URL before invalidating a pending
request. If the new URL is valid but inspection later fails, the replaced preview remains
invalid: the user must submit a fresh link. If capacity is full, preserve the current preview.

## MediaMetadata

`platform`, `canonical_url`, and `media_id` identify the item. Optional `title_or_caption`,
`creator`, `duration_seconds`, and `thumbnail_url` carry available descriptive information.
Duration is nonnegative and absent for images. Escape user-visible strings; truncate preview
text without changing the source identity. Never infer a creator or title from missing data.

`media_count` and `media_kind` identify single video/image versus a collection or live item.
An upstream playlist wrapper is acceptable only if proven to represent one post with one
media item; it must not hide a rejected playlist/carousel by selecting its first child.

## FormatOption

| Field | Meaning and validation |
|---|---|
| option_id | Stable integer within one request; mapped on the server, never accepted as a raw extractor expression |
| adapter, source_format_id | Selected extractor and exact upstream identifier or immutable image identity |
| media_type | video, audio, image |
| extension, mime_type | Supported native file format; detected/validated rather than trusting a filename |
| width, height, bitrate | Optional quality descriptors; positive when supplied |
| includes_audio | True/false for video; absent when not applicable |
| size_bytes, size_kind | Nonnegative byte count or null; exact, estimated, or unknown |
| transport_ref | Private upstream URL/headers or extractor reference; never emitted in callback data or logs |
| availability | selectable or excluded, with a user-facing reason |

A selectable option must be producible without conversion or re-encoding. Combined audiovisual
source files are eligible; standalone video is labeled silent. A merged option records both
component format IDs in `source_format_id` as `<video>+<audio>`, sets `includes_audio` to
true, labels the component-size sum as estimated (muxing changes container overhead), and
is labeled combined. Combined choices require a known/projected sum within the cap; unknown
or oversized sums are excluded. Exact sizes above the cap are excluded for individual
outputs. Individual outputs with uncertain size may be attempted with a byte limit and a
warning that size is unconfirmed. Each final file must match its
selected media identity, type, format, and quality. Never choose a different option on retry.

## DeliveryResult

`status` is confirmed, failed, or unknown. A confirmed result contains the returned Telegram
`message_id` and actual byte count. Failed/unknown results record a sanitized error category,
failed stage, and next-step text. `notification_sent` is a boolean. Timeout after upload may
mean delivery is unknown; it does not prove that no file arrived. In that case the request
ends in `failed` with an unknown result and asks the user to check the chat before retrying.

## State transitions

| Current state | Event | Next state and action |
|---|---|---|
| None | Valid link and capacity available | checking; reserve user and work slot |
| checking | One supported item with usable options | awaiting_selection; publish preview with any worker thumbnail, remove inspection directory, start 900s expiry, release work slot |
| checking | Invalid source, no usable option, error, deadline | failed; explain, release and clean |
| awaiting_selection | Owner selects current option, work capacity available | downloading; claim option once, start 600s deadline |
| awaiting_selection | No capacity for selection | unchanged; explain busy, preserve original expiry |
| awaiting_selection | Valid new link and inspection capacity available | replaced; invalidate old choices, create a new checking request |
| awaiting_selection | Expiry reached | expired; invalidate choices |
| downloading | Valid selected file ready | sending; retain the work slot and original deadline |
| sending | Successful Telegram response | completed; retain message identity, release and clean |
| downloading or sending | Error, deadline, shutdown | failed; kill/reap as needed, release and clean |
| Any terminal state | Old callback | No work; report terminal state or request a fresh link |
| Any state | Process restart | Request state discarded; old callbacks ask for resubmission |

For checking/downloading/sending, a new link returns busy without creating another request.
The source slot is released after inspection, but the user remains active while choosing.
No background retry changes terminal states back to active. Notification failure cannot
prevent finalization. A failed preview send ends the request rather than leaving invisible
pending options.

## Capacity and retention

Two active work slots span inspection or download-through-send; 100 awaiting-selection
requests maximum. Reserve a pending-preview place at inspection admission so inspection
cannot succeed with nowhere to publish its result. One Instagram work slot and parent-owned
rate counters/cooldowns coordinate all Instagram workers; other platforms can use the other
slot. Reject capacity overflow with busy, not a queued job.

After finalization, remove source URLs, metadata, options, and paths. Retain only request ID,
owner/chat, state, terminal time, and confirmed message ID for 900 seconds, at most 1,000
records; evict oldest terminal records first. Missing/evicted IDs always mean resubmit, never
reconstruct a download. Locks and rate counters are likewise TTL-bounded. Temporary files
are deleted immediately where possible and within FR-015's 900s ceiling by the 60s sweeper.
Global output paths cannot point outside the request-owned directory or traverse symlinks.

# Research: Streamlined Bot UX

Each decision resolves an open point from `plan.md` Technical Context. Code references are
to the tree at `cb50757`.

## R1. What counts as "phone-playable"

- **Decision**: An MP4 file whose video stream is H.264 (`avc1…`) and whose audio stream,
  if any, is AAC (`mp4a…`). Nothing else qualifies for "Video" or "Video (no sound)".
- **Rationale**: H.264/AAC in MP4 is the only combination the default players of every
  current iOS and Android phone decode in hardware, and it is what Telegram's own clients
  treat as a streamable video. YouTube serves H.264 at every height up to 1080p (e.g. 136 =
  720p, 18 = 360p muxed), Instagram's DASH renditions are H.264/AAC, and LinkedIn's
  progressive files are H.264/AAC, so the rule keeps a choice available on all three sources.
- **Alternatives rejected**: AV1 in MP4 (no hardware decode before iPhone 15 Pro and
  many Android devices; software playback stutters). VP9/Opus in WebM (not playable by the
  iOS default player). HEVC (not served by the three sources).
- **Unknown codecs (analysis C1)**: yt-dlp sometimes reports no codec for a progressive MP4
  (LinkedIn: `vcodec`/`acodec` absent). Such an MP4 is a **last-resort** candidate: it is
  considered only when no candidate of that kind has known codecs, and it ranks below every
  known-codec candidate. After download, the worker probes the file with ffprobe and rejects
  it unless the video stream is H.264 and, when `includes_audio`, the audio stream is AAC
  (`FORMAT_UNAVAILABLE`, stage `download`). The phone-playable promise is checked on the real
  file instead of on missing metadata. Rejected alternative: treating unknown codecs as not
  phone-playable, which leaves LinkedIn video posts with no deliverable choice.

## R2. Picking the one "Video" / "Video (no sound)" version

- **Decision**: Among selectable, phone-playable candidates of the right kind:
  1. Size filter: keep candidates whose known size (exact or estimated) is at most the
     delivery limit. Only if no candidate has a known size, consider unknown-size candidates.
  2. Resolution tier by the **shorter side**: `min(width, height)` when both are known; the
     one known dimension when only one is (yt-dlp often reports only `height`); unknown when
     neither is. Tier 1 is ≤ 720; tier 2 is > 720. A candidate with unknown dimensions
     belongs to tier 1 and ranks below every candidate with known dimensions.
  3. In tier 1 take the largest shorter side; if tier 1 is empty, take the **smallest**
     shorter side in tier 2.
  4. Ties: known codecs before unknown codecs (R1), higher bitrate, then exact size before
     estimated, then lower `option_id`.
- **Rationale**: Implements FR-004/FR-006 and clarification Q1/720p exactly. The size filter
  comes first so a long video falls back from 720p to 480p/360p instead of losing its button.
  Unknown sizes stay a last resort because the download-time cap (`validate_owned_file`,
  merge `RLIMIT_FSIZE`) still enforces the limit and returns the existing too-large message.
- **Alternatives rejected**: Picking by height (clarified away); preferring muxed files over
  merges (would pin YouTube to 360p format 18).

## R3. Picking the "Audio only" version

- **Decision**: The selectable audio-only candidate with the highest bitrate whose known size
  fits; unknown-size candidates only when none has a known size. Any extension the adapter
  already accepts (`m4a`, `webm`, `opus`). Delivered as a document.
- **Rationale**: Clarification Q "Audio only" → B (highest quality, any format). On YouTube
  this is usually Opus 251 (`.webm`); iOS users may need another app to play it. Accepted in
  the spec edge cases.
- **Language**: Candidates are already limited to the original-language track by the adapter
  (001 research, merge pairs, "amended by 003"), so the highest bitrate is never a dub. Found
  in T038 on an auto-dubbed video with 100 audio streams.

## R4. Where the three-choice policy runs

- **Decision**: A new pure module `src/openmedia/choices.py`, called in the parent process
  after `decode_inspect_result` and before the card is published. The worker protocol,
  `SourceRouter.inspect` size exclusion, and URL-refresh (`_same_option`) are unchanged:
  adapters still return every native option; the parent keeps at most three. The only
  adapter changes are the shared `codec_family` helper and the post-download probe for
  unknown-codec MP4 video (R1).
- **Rationale**: Keeps UX policy out of platform adapters (constitution II/IV isolation),
  needs no worker-protocol change, and is testable with plain `FormatOption` fixtures.
  Refresh on expired URLs matches on format identity, not `option_id`, so rebinding ids is safe.
- **Alternatives rejected**: Filtering in `normalize_info` (couples UX to yt-dlp, skips the
  image adapters, and would change the adapter contract).

## R5. Callback data

- **Decision**: Keep `s:<32-hex-request-id>:<option_id>`. The ≤3 kept options are rebound to
  `option_id` 0, 1, 2 in the fixed order Video, Video (no sound), Audio only (skipping absent
  ones). Remove the `p:` page callback; the parser rejects it as malformed.
- **Rationale**: Integer `option_id` mapped server-side is a project constraint (CLAUDE.md).
  Pagination has no purpose with ≤3 buttons. In-flight previews do not survive a restart
  anyway (state is in memory), so no compatibility window is needed.

## R6. One progress surface: the card

- **Decision**:
  - Send "Checking link…" as today and record its message ID on the request.
  - **Thumbnail available**: `sendPhoto` with the card as caption and the keyboard attached,
    then `deleteMessage` the checking message (best effort). Status edits use
    `editMessageCaption`.
  - **No thumbnail, or the photo upload fails**: `editMessageText` turns the checking message
    into the card, keyboard included. Status edits use `editMessageText`.
  - `BadRequest("message is not modified")` is ignored. Any other edit failure (message
    deleted by the user, too old) falls back to one new plain message carrying the same text.
  - Caption budget: Telegram caps captions at 1,024 characters; the title is truncated to 200
    characters, which leaves room for the duration, one "unavailable" line, and status text.
- **Rationale**: Telegram cannot convert a text message into a photo message (`editMessageMedia`
  only works on messages that already have media), so "replace" means send-then-delete when a
  thumbnail exists and edit-in-place otherwise. Edits happen only at stage transitions
  (≤ 5 per request, including keyboard removal), far below Telegram's per-chat limits.
- **Alternatives rejected**: A separate status message (clarified away, Q3 → A); keeping the
  checking message and adding a card (3 messages, fails SC-004).

## R7. Inline video delivery

- **Decision**: "Video" and "Video (no sound)" are sent with `sendVideo`
  (`supports_streaming=True`, plus `width`, `height`, `duration` when known). "Audio only" and
  pictures keep `sendDocument`. A confirmed `Message` is success whether Telegram returns it
  as `video`, `animation`, or `document`.
- **Rationale**: Bot API: "Telegram clients support MPEG4 videos (other formats may be sent as
  Document)"; bots may upload up to 50 MB with either method. R1 guarantees MPEG-4/H.264, so
  every video choice is eligible for inline playback.
- **Open risk, checked live before release** (quickstart §4): the Bot API does not promise
  that the stored bytes equal the uploaded bytes. A live test sends a small (<20 MB, the
  bot `getFile` download limit) H.264 video with `sendVideo`, downloads it with `getFile`, and
  compares SHA-256. A second check sends a silent MP4, because clients may show silent MP4s
  as looping animations. **Gate**: if the hash differs, stop and revise FR-009 (fall back to
  `sendDocument` for video) before merging User Story 1.
- **Alternatives rejected**: `sendDocument` for all (clarified away, Q3 → A).

## R8. Sending without a tap (pictures and single-choice videos)

- **Decision**: A new atomic registry operation `publish_and_claim` moves a request from
  `checking` straight to `downloading`, keeping the work and Instagram reservations it
  already holds from admission, setting `selected_option_id` and `processing_deadline`. The
  workflow calls it instead of `publish_preview` when the choice set has exactly one entry
  (always true for pictures). Download then runs as a separate supervised task, exactly as a
  tapped selection does.
- **Rationale**: `publish_preview` releases capacity and `claim_selection` re-acquires it; a
  busy result in between would leave an automatic request with no button to retry.
  Holding the reservation removes that window and the need for a new busy message.
- **Alternatives rejected**: Calling `publish_preview` then `claim_selection` from the
  workflow (race described above); showing a single button anyway (clarified away, Q4 → B).

## R9. Status and failure wording

- **Decision**: Fixed English strings in `presentation.py`:
  - `Checking link…`
  - `<Label> — downloading…`, `<Label> — sending…`, `<Label> — sent.`
  - Automatic single choice: `<Label> — only version available, downloading…`
  - Pictures: label `Picture`.
  - Failure: `<Label> — <stage> failed. <next step>` using the existing `failure_message`
    next steps; unknown upload: `<Label> — could not confirm sending. Check this chat before
    sending the link again.`
  - Unavailable line on the card (analysis A5): one line built from `missing`: `Not available: <labels>.` for `not_offered` kinds and `Too large to send: <labels>.` for `too_large` kinds, labels in kind order joined by `, `; when both apply, the two sentences share the line (e.g. `Not available: Audio only. Too large to send: Video.`); no line when nothing is missing.
- **Rationale**: FR-011 plain English, no codec/container names. Existing failure categories
  and next steps are reused so 001 failure meanings stay intact (FR-012).

## R10. Diagnostics

- **Decision**: No new event names. Add two fields through the existing `diagnostics.event`
  allowlist: `choices` (list drawn from `video`, `silent`, `audio`) on `inspection_finished`,
  and `automatic` (bool) on `selection`. Recorded as an amendment to the 002 data model.
- **Rationale**: Operators can see why a user got one button or none without logging URLs or
  identifiers; both values are fixed vocabularies.

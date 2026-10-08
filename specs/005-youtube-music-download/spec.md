# Feature Specification: YouTube Music Downloads

**Feature Branch**: Not created by this invocation (no branch hook configured)

**Created**: 2026-10-08

**Status**: Draft

**Input**: User description: "Let's support the youtube music (download music by a shared link)"

**Extends**: Feature 001 source support to public single-item YouTube Music links. For
these links, the audio-only automatic workflow below takes precedence over feature 003's
video choices. Ordinary YouTube links retain their existing video workflow. All other
access, resource, delivery, privacy, and failure rules from features 001–004 remain in force.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Download a shared track (Priority: P1)

A user copies a track link from YouTube Music and sends it to the bot in a private chat.
The bot shows the track card and progress, then automatically sends one audio file.

**Why this priority**: Sharing a link should be enough to obtain the music without choosing
between video formats or opening another application.

**Independent Test**: Submit a public track link with controlled source responses and verify
that one native audio file arrives without a selection tap.

**Acceptance Scenarios**:

1. **Given** a public track with downloadable native audio within the delivery limit,
   **When** the user sends its YouTube Music link, **Then** the bot shows checking progress,
   a card with available artwork, title, and duration, and sends exactly one audio file
   automatically, with no video or format-selection buttons.
2. **Given** several native audio versions, **When** the link is processed, **Then** the
   highest-quality version within the delivery limit is sent using feature 003's existing
   audio ranking; equal-ranked versions follow its existing deterministic tie-breaks.
3. **Given** missing artwork or duration, **When** the track is available, **Then** the
   existing card fallback is used and audio delivery still succeeds.
4. **Given** a completed download, **When** the audio is sent, **Then** it arrives as a file
   in its source format with unchanged bytes, and the card reports completion.

---

### User Story 2 - Download only the shared track from listening context (Priority: P2)

A user shares a track while listening to an album or playlist. The bot downloads only the
track identified in the link, regardless of playlist or sharing parameters.

**Why this priority**: Listening context must not accidentally turn a single-link request
into a bulk download.

**Independent Test**: Submit links to the same track with and without playlist and sharing
parameters; each request produces only that track's audio.

**Acceptance Scenarios**:

1. **Given** a track link containing a track identifier and playlist context, **When** it is
   submitted, **Then** exactly the identified track is downloaded; no other track is inspected
   or downloaded as a playlist member.
2. **Given** links differing only in sharing parameters, playlist context, or playback offset,
   **When** each is submitted separately, **Then** each refers to the same complete track.
3. **Given** an album or playlist link with no individual track identifier, **When** it is
   submitted, **Then** the bot explains that only a single track is supported and asks for
   a track link, without downloading any item.
4. **Given** an ordinary YouTube video link to the same item, **When** it is submitted,
   **Then** the existing video-choice workflow remains available.

---

### User Story 3 - Understand why music cannot be delivered (Priority: P2)

A user receives a clear explanation and a next step when a music link cannot produce an
eligible audio file.

**Why this priority**: Users need to distinguish unsupported links, inaccessible content,
missing native audio, and delivery failures.

**Independent Test**: Submit controlled examples of each refusal and failure category and
verify that each ends with a plain explanation and no unintended media delivery.

**Acceptance Scenarios**:

1. **Given** removed, private, login-required, or otherwise anonymously inaccessible content,
   **When** the link is processed, **Then** the bot explains that the content cannot be opened
   anonymously and suggests another public link without asserting an unverified cause.
2. **Given** an item with video but no downloadable native audio-only version, **When** the
   link is processed, **Then** the bot explains that audio-only download is unavailable;
   it does not send video or create an audio version.
3. **Given** all native audio versions exceed the delivery limit, **When** the link is
   processed, **Then** the bot explains the size limit and suggests another track.
4. **Given** a download or delivery failure, **When** the operation ends, **Then** the card
   identifies the failed stage and gives the existing retry guidance without internal errors.

### Edge Cases

- A malformed or missing track identifier receives unsupported-link guidance.
- Playlist-only, album-only, artist, search, and home-page links do not trigger downloads.
- A track identifier accompanied by playlist, radio, sharing, or offset parameters still
  requests one complete item; conflicting repeated track identifiers are refused.
- A music video shared on YouTube Music is treated as one audio request when native audio
  is available; live or unfinished items retain the existing unsupported-content refusal.
- A source offers several audio formats: preserve the selected source format, including
  formats that Telegram may display only as downloadable files.
- Known oversized versions are excluded before selection; an unknown-size version that
  exceeds the limit during download is stopped and receives the existing size explanation.
- Rate limiting, inspection timeout, changed source availability, and send timeout retain
  their existing explanations and cleanup behavior.
- Two supported links in one message are refused under the existing one-link rule.
- Requests submitted while busy, repeated submissions, expired requests, and restarts follow
  existing request-state rules; a music request never produces duplicate deliveries.
- Lookalike domains and unsupported redirects do not gain access through music-link recognition.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The bot MUST recognize HTTPS single-item links on `music.youtube.com` with
  path `/watch` and one valid `v` track identifier, including links with sharing parameters,
  as supported YouTube Music requests under the existing exactly-one-supported-link rule.
- **FR-002**: A recognized music link MUST request only the complete item identified by `v`.
  Playlist, radio, tracking, and playback-offset parameters MUST NOT expand or truncate it.
  Missing, malformed, or conflicting track identifiers MUST be refused without downloading.
- **FR-003**: Music requests MUST use anonymous access only. They MUST NOT require source
  accounts, subscriptions, supplied cookies, or stored source credentials.
- **FR-004**: The bot MUST automatically select one highest-quality native audio-only version
  that fits the existing delivery limit, using feature 003's audio ranking and tie-breaks.
  It MUST NOT offer video, silent video, or a format picker for music requests.
- **FR-005**: Audio MUST be delivered as a file in its original source format with unchanged
  bytes. The bot MUST NOT convert formats, re-encode, split audio from a combined video file,
  or rewrite embedded tags or artwork. No particular format such as MP3 is guaranteed.
- **FR-006**: The user MUST see the existing checking message, then a single card with
  available artwork, title, duration, and stage progress. Existing missing-metadata fallbacks
  MUST apply, and the card MUST end with completion or a plain failure explanation.
- **FR-007**: Album or playlist links without a single track identifier MUST receive
  single-track-only guidance. Other unsupported YouTube Music pages MUST receive
  unsupported-link guidance. Neither case MUST download a collection or arbitrary item.
- **FR-008**: Inaccessible content, absent native audio, size-limit failures, rate limits,
  source changes, inspection/download/send failures, and live content MUST retain the existing
  distinct failure meanings and actionable next steps. Music failures MUST NOT fall back to video.
- **FR-009**: Music requests MUST observe the existing delivery cap (50,000,000 bytes),
  inspection deadline (60 seconds), download-and-send deadline (600 seconds), bounded request
  state, concurrency, duplicate prevention, and temporary-media cleanup rules from feature 001.
- **FR-010**: Ordinary YouTube links MUST retain feature 003's existing video choices;
  LinkedIn and Instagram workflows MUST retain their existing behavior. Music intent MUST
  remain associated with the request even if the source item is also available on YouTube.
- **FR-011**: Existing diagnostic privacy rules MUST apply to music requests and refusals:
  source links and Telegram identifiers appear only in the enabled diagnostic log, credentials
  never appear in logs or user errors, and source credentials are never retained.

### Key Entities

- **Music link**: A shared YouTube Music address identifying one track, with optional
  listening or sharing context that does not alter the requested item.
- **Music request**: A user's single-item audio download intent, associated with the source
  item and the existing request lifecycle, distinct from an ordinary YouTube video request.
- **Native audio version**: A source-provided audio-only file with format, quality, available
  size information, and eligibility under the existing delivery limit.
- **Track card**: Available artwork, title, duration, and the current outcome or progress of
  the music request, using the existing presentation conventions.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every eligible single-track case in the controlled acceptance set delivers
  exactly one audio file after one link submission and zero selection taps.
- **SC-002**: For every delivered acceptance sample, the file matches the selected source
  audio byte-for-byte and is the highest-ranked eligible version under the existing policy.
- **SC-003**: Every acceptance link with playlist or sharing context delivers only the
  identified track; every collection-only link delivers zero files and requests a track link.
- **SC-004**: Every failure case above gives an explanation and next step, with inspection
  resolving within 60 seconds and download-and-send resolving within 600 seconds.
- **SC-005**: All existing ordinary YouTube, LinkedIn, and Instagram acceptance scenarios
  retain their expected media choices and delivery behavior.

## Assumptions

- Initial scope is public, finished, individual YouTube Music items that expose native
  downloadable audio anonymously. Availability can differ by item or region.
- The supported shared-link shape is `https://music.youtube.com/watch?v=<track-id>` with
  optional context parameters. Other share-link shapes or URL shorteners are outside this
  initial scope unless separately specified.
- Album and playlist downloading, search, recommendations, subscription-only content,
  format conversion, and embedded metadata editing are outside this feature.
- Music delivery follows the existing audio-as-file convention; inline Telegram music
  playback is not a requirement for every native format.
- The feature depends on the existing source inspection, native audio ranking, card,
  delivery, and cleanup behavior defined in features 001 and 003. Planning must confirm
  anonymous source availability separately; this specification does not claim live verification.

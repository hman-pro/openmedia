# Feature Specification: Media Download Workflow

**Feature Branch**: `main` (existing branch; no branch-creation hook configured)

**Created**: 2026-09-15

**Status**: Draft

**Input**: User description: "User puts a media link into the bot. The server checks it and
provides available metadata. The user selects the desired format. The server downloads
the media and sends it to the user."

## Clarifications

### Session 2026-09-15

- Q: Who should be allowed to use the OpenMedia bot? → A: Anyone who messages the bot;
  no allowlist or separate registration is required.
- Q: Should the bot offer source formats or standardize downloads to MP4 video and MP3
  audio? → A: Offer available source formats and quality choices with no format
  conversion; images retain their original format.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Choose and Receive Media (Priority: P1)

Any Telegram user can send a social media link to the OpenMedia Telegram Bot without
prior approval or separate registration. The user reviews the available
information and formats, chooses one, and receives the resulting file in the same chat.
This lets the user obtain the intended media without leaving Telegram.

**Why this priority**: This complete journey delivers the feature's core value.

**Independent Test**: Submit a supported public link, inspect the metadata and options,
select a format, and verify that the matching media arrives in the requesting chat.
Repeat for every in-scope platform and media combination.

**Acceptance Scenarios**:

1. **Given** a supported public media link and no active request, **When** the user sends
   it, **Then** the bot acknowledges the request and displays available metadata and
   selectable formats before downloading the requested media file.
2. **Given** metadata is available, **When** the preview appears, **Then** it identifies
   the source platform and link and includes the title or caption, creator, duration,
   and thumbnail when each is available and applicable.
3. **Given** a preview with multiple formats, **When** the user chooses one, **Then** the
   bot confirms the choice, downloads that format, and sends the matching file to the
   same user in the same chat, indicating completion only after delivery succeeds.
4. **Given** only one format is available, **When** the preview appears, **Then** the user
   must still select that option before downloading begins.
5. **Given** some descriptive metadata is missing, **When** a downloadable option exists,
   **Then** the bot still presents the available information and allows selection without
   inventing missing values.
6. **Given** a video, audio, or image choice, **When** options are displayed, **Then** each
   identifies the media type and file format, with quality and size information where
   known; estimated sizes are labeled as estimates.
7. **Given** a source offers only particular file formats and quality choices, **When**
   the preview appears, **Then** only supported choices available from that source are
   offered, with no generated MP4 or MP3 alternatives; the delivered file preserves the
   selected format. Where the source serves video and audio as separate streams, a
   video-with-sound choice may combine exactly one of each by stream copy, without
   re-encoding, and is labeled as combined. Audio-only choices appear only when available
   without conversion.

---

### User Story 2 - Understand an Unsuccessful Request (Priority: P2)

A user whose link cannot be processed or whose chosen file cannot be delivered receives
an understandable reason and a next step, rather than waiting without an outcome.

**Why this priority**: Source availability and delivery limits can prevent otherwise
valid requests; users need to know whether to change the link or try another option.

**Independent Test**: Submit invalid, inaccessible, and oversized examples or cause a
processing failure, then verify that each produces the specified explanation and
allows a subsequent valid request.

**Acceptance Scenarios**:

1. **Given** text without exactly one supported media link, **When** it is submitted,
   **Then** the bot explains that one supported link is required; it does not silently
   choose among multiple links or start a download.
2. **Given** a link to unsupported, removed, private, or login-required content, **When**
   it is checked, **Then** the bot explains the known reason or says the content could
   not be accessed when the reason is unknown, and asks for another public link.
3. **Given** content with no usable format, **When** inspection completes, **Then** the
   bot explains that no downloadable option is available and offers no selection.
4. **Given** an option known to exceed delivery limits, **When** options are displayed,
   **Then** that option cannot start a download and its limitation is explained; usable
   alternatives remain selectable, or the bot explains that none can be delivered.
5. **Given** a selection that becomes unavailable or exceeds limits during processing,
   **When** the problem is detected, **Then** the bot reports failure without substituting
   a different format and advises resubmitting the link to review current options.
6. **Given** metadata lookup, downloading, or sending fails or times out, **When** the
   request ends, **Then** the bot identifies the failed stage and a retry step without
   exposing internal credentials. If Telegram is unreachable, the request still ends
   as failed and cleanup proceeds; immediate user notification is not guaranteed.

---

### User Story 3 - Keep Requests and Selections Unambiguous (Priority: P2)

A user receives clear feedback when submitting another link or pressing an old option,
and each selected file stays associated with the request and person who selected it.

**Why this priority**: Repeated actions and stale choices must not cause duplicate work
or send a file to the wrong person.

**Independent Test**: Exercise repeated selections, a second link, expired choices, and
requests from two different users; verify the response and destination for each.

**Acceptance Scenarios**:

1. **Given** a request is being checked, downloaded, or sent, **When** the same user sends
   another link, **Then** the bot reports the active request and asks them to wait; it
   neither replaces that request nor silently queues the new link.
2. **Given** a request is awaiting format selection, **When** the user submits a new valid
   link, **Then** the bot replaces the pending request and invalidates its old choices.
3. **Given** a selection has already been accepted, **When** it is pressed again,
   **Then** the bot reports the current or completed state without starting another
   download or intentionally sending another copy.
4. **Given** a selection has expired, been replaced, or become unavailable after a service
   restart, **When** it is pressed, **Then** the bot asks the user to resubmit the link.
5. **Given** requests from different users, **When** they make selections, **Then** each
   selection applies only to its originating user and request and each result goes only
   to its originating chat.
6. **Given** the service has reached its processing capacity, **When** another request is
   submitted, **Then** the bot reports that it is busy and asks the user to retry later.

---

### Edge Cases

- A first-time user has no prior relationship with the bot: accept their private-chat
  request without registration or approval, subject to the same capacity limits as
  other users.
- A supported link redirects to unsupported or inaccessible content: explain that the
  resolved content cannot be processed and present no download choices.
- A post contains several media items, or a link identifies a playlist or live broadcast:
  explain that this workflow accepts a single finished media item.
- File size is unknown until downloading: label size as unknown, allow selection, and
  stop with a limit explanation if processing reveals the file cannot be delivered.
- A video option has no audio: label it as silent; do not imply that it includes sound.
- An image has no quality variants: offer its available original file format for selection.
- A video contains sound but the source offers no downloadable audio-only option: keep
  the available video choices and explain that audio-only download is unavailable; do
  not create an audio format through conversion.
- A user blocks the bot during delivery: do not claim successful delivery; end processing
  and clean up temporary media even when an error notification cannot be sent.
- Temporary storage is exhausted: terminate the affected request with a retry explanation
  and release its temporary files; do not leave the request indefinitely active.
- The bot receives a link in a group: direct the user to a private chat without processing
  or publishing a media preview in the group.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The bot MUST accept a private-chat message containing exactly one link to a
  supported platform; surrounding text and links to other sites are ignored. It MUST reject
  messages with no such link or more than one, with guidance, and direct group users to a
  private chat (Story 2.1; group edge case).
- **FR-002**: The workflow MUST support public single-item YouTube videos, LinkedIn video
  and image posts, and Instagram video and image posts. It MUST offer audio-only choices
  when the source provides a supported downloadable audio-only option requiring no
  format conversion. Unsupported access modes and
  multi-item content MUST receive an explanation (Story 1; Story 2.2; content edge cases).
- **FR-003**: The bot MUST acknowledge accepted links, check accessibility, and present
  available metadata before asking for selection (Story 1.1–1.2).
- **FR-004**: Metadata MUST identify the source platform and link and include available
  title or caption, creator, applicable duration, and thumbnail. Missing optional fields
  MUST NOT prevent a download with usable options (Story 1.2, 1.5).
- **FR-005**: Each selectable option MUST identify its media type, file format, available
  quality, known or estimated size, and whether video includes audio. Unknown values MUST
  be labeled or omitted without fabrication (Story 1.6; size and silent-video edge cases).
- **FR-006**: Offered video and audio formats and quality choices MUST be available from
  the source and supported by the service without format conversion. The service MUST
  preserve the selected source format and MUST NOT generate additional formats or quality
  variants through conversion. Combining one source video stream and one source audio
  stream into a single file by stream copy is not conversion: both streams MUST keep their
  source encoding, and the choice MUST be labeled as combined. Images MUST retain their available original format
  (Story 1.3, 1.6–1.7; image and audio-only edge cases).
- **FR-007**: The service MUST wait for an explicit selection before downloading the
  requested media file, including when only one choice exists. Metadata and thumbnail
  retrieval are allowed during inspection (Story 1.1, 1.4).
- **FR-008**: A valid selection MUST start processing of the selected output and provide
  user-visible downloading and sending states. The service MUST NOT silently change the
  chosen media type, format, or quality (Story 1.3; Story 2.5).
- **FR-009**: The service MUST send the result directly in the originating Telegram chat,
  using a media attachment or a downloadable file attachment that preserves the selected
  output. It MUST mark the request complete only after successful delivery (Story 1.3).
- **FR-010**: Known unusable options MUST be excluded from selection with an explanation.
  Unknown sizes MAY be attempted, but detected resource or delivery-limit violations MUST
  terminate the request with a next step (Story 2.3–2.5; resource edge cases).
- **FR-011**: Each failed request MUST leave its active state, identify the failed stage
  and a next step when the bot can communicate, and hide credentials and internal error
  details. Notification failure MUST NOT prevent request termination or cleanup
  (Story 2; blocking edge case).
- **FR-012**: Choices and results MUST be bound to their originating user, chat, and
  request. Repeated, expired, replaced, or unavailable selections MUST NOT start duplicate
  processing (Story 3.3–3.5).
- **FR-013**: Each user MUST have at most one active request. A new valid link MUST replace
  a request awaiting selection; during checking, downloading, or sending it MUST receive
  a busy response. Global capacity exhaustion MUST receive a retry-later response rather
  than silently queuing work (Story 3.1–3.2, 3.6).
- **FR-014**: An unselected preview MUST expire after 15 minutes. Metadata lookup MUST end
  within 60 seconds, and downloading plus sending MUST end within 10 minutes of selection,
  with a timeout explanation if unfinished (Story 2.6; Story 3.4).
- **FR-015**: Temporary media MUST be removed within 15 minutes of success or failure.
  Following an interruption, leftover media MUST be removed within 15 minutes of service
  recovery. Cleanup MUST NOT depend on successful user notification (resource and
  blocking edge cases).
- **FR-016**: The bot MUST accept requests from any Telegram user in a private chat without
  an allowlist, invitation, administrator approval, or separate registration. First-time
  and returning users MUST follow the same workflow and capacity rules (Story 1;
  first-time-user edge case).

### Key Entities *(include if feature involves data)*

- **Download Request**: The submitted source link, originating user and chat, available
  metadata and choices, selected choice, expiry, and current outcome. Its user-visible
  states are checking, awaiting selection, downloading, sending, completed, failed,
  expired, or replaced.
- **Media Metadata**: Available descriptive information about the source item, including
  its platform, link, title or caption, creator, duration, and thumbnail.
- **Format Option**: One selectable source-format output for a request, identified by media type, file
  format, quality, audio inclusion where applicable, size certainty, and deliverability.
- **Delivery Result**: Whether the selected media reached the originating chat, or the
  failed stage, reason, next step, and whether a failure notice could be delivered.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every in-scope platform and media combination passes an end-to-end acceptance
  example: submit a link, see metadata, choose an option, and receive the matching file
  in the correct chat with its selected source format preserved. Video examples exercise
  an audio-only choice when one is available from the source and verify the explanation
  when none is available. No acceptance example requires format conversion.
- **SC-002**: In at least 95% of a 20-request acceptance run within processing capacity,
  users see acknowledgment within 2 seconds and metadata with choices within 30 seconds,
  excluding only samples affected by externally logged source or messaging-service errors
  under the exclusion rule fixed in the validation guide; excluded samples are replaced.
- **SC-003**: In at least 95% of 20 eligible download attempts within capacity, users receive
  their selected file within 2 minutes when files are at most 20 MB and fit delivery limits,
  excluding only samples affected by externally logged source or messaging-service errors
  under the exclusion rule fixed in the validation guide; excluded samples are replaced.
  Larger eligible files follow the 10-minute processing deadline.
- **SC-004**: Every defined invalid-input, unavailable-content, limit, and timeout scenario
  ends with the specified reason and next step when communication is available; none
  remains indefinitely active or reports a failed delivery as successful.
- **SC-005**: Repeated-selection and two-user acceptance scenarios produce zero duplicate
  downloads from repeated selections and zero deliveries to the wrong user or chat.
- **SC-006**: The happy path requires only one link submission and one format selection,
  with no additional account login or mandatory commands, for both first-time and
  returning users without prior approval.
- **SC-007**: All expiry, busy-state, and temporary-media cleanup checks meet FR-013–FR-015,
  including failure and recovery scenarios.

## Assumptions

- Bot access is public to anyone who messages it. Public bot access does not expand
  supported source access modes: source media must still meet the restrictions below.
- Initial scope is private Telegram chats and publicly accessible content requiring no
  source login, supplied credentials, subscription, or account-specific access. The
  supported combinations in FR-002 are intended acceptance scope, not a claim that every
  URL on those platforms is accessible.
- Single-item videos and images are included. Audio-only choices are included when the
  source provides a supported downloadable audio-only option without conversion;
  standalone audio-post URLs are outside this initial workflow.
- Playlists, multi-item posts and carousels, live broadcasts, bulk downloading, format
  conversions, cancellation controls, and saved download history are outside this feature.
- Formats and quality choices are limited to the source item's available options that
  the service can deliver without conversion. No standardized MP4 or MP3 output is
  promised when that format is absent from the source. Images retain their original format.
- Separate source video and audio streams may be combined into one file by FFmpeg stream
  copy, without re-encoding. A combined choice is offered only when the pair is
  container-compatible and its projected size fits the delivery limit, so the highest
  qualities may still appear only as silent video or audio-only choices. Re-encoding,
  scaling, bitrate changes, and format conversion remain out of scope.
- Delivery is a direct Telegram attachment. External download hosting, file splitting,
  and automatic changes to quality to fit limits are outside scope.
- The 15-minute selection expiry, 60-second inspection deadline, 10-minute processing
  deadline, and 15-minute cleanup window are initial product defaults. Changes to these
  acceptance values must be reflected in this specification.
- The processing capacity and storage budget are deployment constraints to be quantified
  during planning; exceeding them must produce the behavior specified above.
- Source accessibility, extraction support, and Telegram delivery availability and limits
  are external dependencies. Planning must verify support and applicable limits before
  implementation; inability to meet FR-002 requires an explicit scope revision.
- Timing targets are initial acceptance targets for available external services. Validation
  must record the media examples, sizes, service conditions, and request concurrency used.
- A restart may invalidate pending selections; users can resubmit their links. Automatic
  resumption of interrupted downloads is outside scope. An interrupted request must
  never be reported as completed without delivery confirmation; interacting with an
  invalidated selection prompts resubmission under Story 3.4.

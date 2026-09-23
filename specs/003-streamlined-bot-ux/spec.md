# Feature Specification: Streamlined Bot UX

**Feature Branch**: `003-streamlined-bot-ux`

**Created**: 2026-09-23

**Status**: Draft

**Input**: User description: "Let's improve bot UX, currently we emit a lot of information and that is not user friendly. Keep: thumbnail of the media (title and duration included) and a log of what we are doing now. Eliminate: massive information about formats. Adjust: give the user only 3 choices for video — mobile-friendly video (audio included), mobile-friendly video (silent), just the audio of that video — applying to all video downloads. For pictures, no format selection; just send the picture in original quality. Put the formats in the selection buttons instead of numbers."

**Supersedes**: the preview, option-listing, pagination, and image-selection behavior of
`specs/001-media-download` (Story 1 presentation, FR-004, FR-005, FR-007 for images and
single-choice videos, and the
"Preview and selection" section of `contracts/telegram-bot.md`). Source support, access
modes, limits, deadlines, busy/expiry rules, and failure meanings from 001 remain in force.

## Clarifications

### Session 2026-09-23

- Q: What does "mobile-friendly" mean, and may the bot convert media? → A: The best
  phone-playable version the source already provides, up to 720p, within the delivery
  limit; never converted. (Fallback when nothing is at or below 720p: see the 720p cap
  answer below.)
- Q: When a source has only one combined file, how are "Video (no sound)" and "Audio only"
  offered? → A: They are not; the bot never splits a combined file. Those buttons are hidden.
- Q: How does a delivered video arrive? → A: Videos play inline in the chat; audio and
  pictures arrive as files with original bytes.
- Q: How is the 720p cap measured, and what if nothing is at or below it? → A: On the
  shorter side of the picture; if no phone-playable version is ≤720p, use the smallest
  phone-playable version above 720p that fits the delivery limit.
- Q: Which audio does "Audio only" send when the source offers several? → A: The
  highest-quality audio the source provides, whatever its format, within the delivery limit.
- Q: Does progress appear on the preview card or in its own message? → A: On the card. The
  initial "Checking link…" message is replaced by the card, whose caption then carries the
  progress; the chat ends with the card and the delivered file.
- Q: With only one available video choice, wait for a tap or send at once? → A: Send at
  once; the card shows no buttons and states it is sending the only available version.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Pick a video in one tap from three plain choices (Priority: P1)

A user sends a public video link. The bot shows a single preview card: the thumbnail with
the title and duration beneath it, and up to three buttons labeled in plain words —
"Video", "Video (no sound)", "Audio only". No format table, codec names, bitrates, or
numbered option list appears. The user taps one button and receives that file.

**Why this priority**: This is the main flow of the bot and the source of the current
information overload. Delivering it alone fixes the complaint for every video source.

**Independent Test**: Send a YouTube, Instagram, and LinkedIn video link to the bot with a
fake transport; verify the preview contains only thumbnail, title, duration, and at most
three plainly labeled buttons, and that each button delivers the matching file.

**Acceptance Scenarios**:

1. **Given** a public video with separate picture and sound available, **When** the user
   sends its link, **Then** the bot shows one preview with the thumbnail, title, duration,
   and exactly three buttons: "Video", "Video (no sound)", "Audio only".
2. **Given** the preview is shown, **When** the user taps "Video", **Then** the bot
   delivers one phone-playable video file with sound.
3. **Given** the preview is shown, **When** the user taps "Video (no sound)", **Then** the
   bot delivers one phone-playable video file without an audio track.
4. **Given** the preview is shown, **When** the user taps "Audio only", **Then** the bot
   delivers one audio file of that video's sound.
5. **Given** any of the three choices cannot be produced for this video, **When** the
   preview is shown, **Then** that button is absent and one short line says which choice
   is unavailable, without technical detail.
6. **Given** exactly one of the three choices can be produced, **When** the preview card
   appears, **Then** it shows no buttons, states that the only available version is being
   sent, and delivery starts without a tap.
7. **Given** none of the three choices can be produced, **When** the source is checked,
   **Then** no buttons are shown and the message explains that this video cannot be
   delivered and suggests sending another link.

---

### User Story 2 - Receive a picture immediately, without choosing (Priority: P2)

A user sends a link to a public image post. The bot does not ask the user to choose
anything. It shows its progress and then sends the picture at its original quality.

**Why this priority**: Images have one meaningful output, so a selection step is pure
friction. It is independent of the video flow.

**Independent Test**: Send an Instagram and a LinkedIn image link with a fake transport;
verify no buttons are shown and the delivered file is byte-identical to the source image.

**Acceptance Scenarios**:

1. **Given** a public single-image post, **When** the user sends its link, **Then** the
   bot delivers the picture without showing any selection buttons.
2. **Given** the picture is delivered, **When** the user saves it, **Then** it has the same
   pixel dimensions and bytes as the source original (no compression or resizing).
3. **Given** the original picture exceeds the delivery limit, **When** the user sends the
   link, **Then** the bot explains the picture is too large to deliver.

---

### User Story 3 - See what the bot is doing in one live status line (Priority: P3)

From link to delivery, the user sees one short, plain status that updates in place —
for example "Checking link…", "Downloading…", "Sending…" — instead of a sequence of
separate messages.

**Why this priority**: It keeps the chat clean and reassures the user during long
downloads, but the core flow works without it.

**Independent Test**: Run a video and an image request with a fake transport; verify the
chat never holds more than one bot status or preview message for the request at a time,
that its text changes through the stages, and that it ends showing the outcome.

**Acceptance Scenarios**:

1. **Given** a link is accepted, **When** the bot works on it, **Then** one status line
   progresses through checking, downloading, and sending, each shown in plain words.
2. **Given** a request fails at any stage, **When** the failure occurs, **Then** the same
   status line states the failed stage and one next step for the user.
3. **Given** a video request, **When** the preview card appears, **Then** it replaces the
   "Checking link…" message rather than appearing beside it.
4. **Given** a video preview card, **When** the user taps a choice, **Then** the buttons are
   removed and the card's caption keeps the title and duration and adds the chosen label and
   stage (e.g., "Audio only — downloading…"), updating in place until delivery.

---

### Edge Cases

- A video has no separate sound track and only a single file with sound (common on
  LinkedIn): "Video" is offered from that file when it qualifies; "Video (no sound)" and
  "Audio only" are absent, and the preview says so in one line.
- The source has no sound at all: "Video" and "Audio only" are absent; "Video (no sound)"
  is offered and the preview says the video has no sound.
- Every phone-playable version exceeds the delivery limit: that choice is absent and the
  preview says it is too large; other choices remain.
- A vertical video (e.g., 720×1280) counts as 720p, because the cap is measured on the
  shorter side.
- The source's only phone-playable versions are above 720p (e.g., 1080p only): the smallest
  of them that fits the delivery limit is used; if none fits, the choice is absent.
- The thumbnail cannot be fetched: the preview shows title and duration as text only.
- Title is missing: the preview shows a neutral label (e.g., "Untitled video") and the
  duration; the duration is omitted when unknown.
- A very long title: it is shortened so the preview stays within one message.
- A user taps a button on an expired or replaced preview: the existing 001 rule applies
  (send the link again).
- The highest-quality audio is in a format some phones' default players cannot open: it is
  still sent, as a file (FR-005a, FR-009).
- A LinkedIn video with only a combined file: usually only "Video" is available, so it is
  sent without a tap (FR-002a).
- A multi-image post: out of scope, as in 001 (only one finished media item is supported).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: For a video link, the preview MUST show only the thumbnail, the title, and the
  duration, plus the single unavailable line required by FR-007 and the status line required
  by FR-010. Platform name, creator, canonical link, format lists, codecs, bitrates,
  resolutions, and file-size tables MUST NOT appear.
- **FR-002**: For a video link, the bot MUST offer at most three choices: "Video" (with
  sound), "Video (no sound)", and "Audio only". No other video or audio choice is offered,
  and there is no pagination.
- **FR-002a**: When exactly one video choice is available, the bot MUST start delivering it
  without waiting for a tap, show no buttons, and name the choice on the card (e.g.,
  "Video — only version available, downloading…"). With two or three choices, an explicit
  tap remains required.
- **FR-003**: Choice buttons MUST carry the plain label of the choice, never a number or a
  technical format description.
- **FR-004**: "Video" and "Video (no sound)" MUST each be a mobile-friendly version: the
  best version the source already provides in a format that plays in the default player of
  current iOS and Android phones, whose shorter side is at most 720 pixels, and within the
  delivery limit. When no phone-playable version is at or below 720 pixels, the bot MUST
  use the smallest phone-playable version above 720 pixels that fits the delivery limit.
  The bot MUST NOT convert, re-encode, or resize media to make it mobile-friendly; "Video"
  may join the source's own picture and sound without altering either. When no
  phone-playable version fits the delivery limit, the choice is omitted per FR-007.
- **FR-005**: "Audio only" and "Video (no sound)" MUST be offered only when the source
  itself provides a separate sound-only or picture-only version. The bot MUST NOT split a
  combined file to create them; when absent, they are omitted per FR-007.
- **FR-005a**: "Audio only" MUST deliver the highest-quality audio version the source
  provides that fits the delivery limit, regardless of format. The phone-playable rule of
  FR-004 does not apply to audio.
- **FR-006**: The bot MUST select, for each choice, the single best source version that
  meets FR-004 (video choices) or FR-005a ("Audio only"). The user never chooses quality.
- **FR-007**: A choice that cannot be produced within the delivery limit MUST be omitted,
  with one plain line naming the missing choice and why (unavailable or too large).
- **FR-008**: For an image link, the bot MUST deliver the original picture without any
  selection step, byte-for-byte, with no compression or resizing.
- **FR-009**: Delivered "Video" and "Video (no sound)" files MUST play inline in the chat.
  "Audio only" and pictures MUST arrive as files that keep their original bytes.
- **FR-010**: Each request MUST show its progress in a single message updated in place
  through checking, downloading, and sending, ending in the outcome or failure reason. For
  a video, the "Checking link…" message MUST be replaced by the preview card, and from then
  on the card's caption carries the status. For an image, the "Checking link…" message
  carries the status until the picture is delivered.
- **FR-011**: All user-visible text MUST be plain English, free of internal identifiers,
  codec or container names, and error internals.
- **FR-012**: Limits, deadlines, one-active-request, expiry, busy, and cleanup behavior from
  `specs/001-media-download` MUST continue to apply unchanged.

### Key Entities

- **Video choice**: one of three fixed kinds (with sound, no sound, audio only); has a
  plain label, availability, and a reason when unavailable. Replaces the numbered,
  paginated option list for video.
- **Preview card**: thumbnail (optional), title, duration, and the available video
  choices.
- **Status line**: the in-place progress text for one request; first its own "Checking
  link…" message, then (for video) part of the preview card's caption, holding the current
  stage and, after a tap, the chosen label.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A video preview shows no more than 3 buttons and no more than 3 lines of text
  besides the title.
- **SC-002**: A user gets a video, silent video, or audio file with exactly 1 tap after
  sending the link when two or three choices are offered, and with 0 taps when only one is,
  in 100% of requests.
- **SC-003**: A user gets a picture with 0 taps after sending an image link.
- **SC-004**: Each successful request leaves exactly 2 bot messages in the chat: for video,
  the preview card and the delivered file; for images, the status message and the picture.
- **SC-005**: 100% of delivered "Video" and "Video (no sound)" files play in the default
  player on current iOS and Android phones without extra apps.
- **SC-006**: Delivered pictures are byte-identical to the source original in 100% of
  controlled tests.

## Assumptions

- Supported sources, access modes, and content types are those of 001: public single-item
  videos from YouTube, Instagram, LinkedIn, and public single-image posts from Instagram and
  LinkedIn.
- "Log of what we are doing" means a user-facing progress status in the chat, not the
  operator's diagnostic log file from 002, which is unchanged.
- The 50 MB delivery limit and all fixed deadlines from 001 remain.
- English remains the only message language.
- Inline-playable delivery of a video is assumed to leave the file's bytes unchanged; this
  must be confirmed during planning, and if it does not hold, the plan must report it before
  FR-009 is implemented.
- Button labels are "Video", "Video (no sound)", "Audio only"; wording may be polished in
  planning without changing their meaning.

# Feature Specification: Media Delivery Titles

**Feature Branch**: `006-media-delivery-titles`

**Created**: 2026-10-18

**Status**: Implemented; controlled acceptance verified; external release gates pending

**Input**: User description: "I'd like to have a title of downloaded media on the sending media (as title) to the Telegram."

**Extends**: Features 001–005 with titles attached to delivered media. Existing support,
anonymous access, native formats, byte preservation, limits, privacy, and failures apply.

## Clarifications

### Session 2026-10-18

- Q: Where should the downloaded media’s title appear in Telegram? → A: Both the media message caption and filename.
- Q: Should delivery titles have a short length limit? → A: Yes; use 64 characters for both the caption and filename stem, excluding the extension. Shortened titles end with `…` within that limit.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Identify delivered media (Priority: P1)

A user receives media with its source title on the media message and in its filename,
so the item remains recognizable when saved or forwarded.

**Why this priority**: The title needs to accompany the delivered item independently
of the earlier card or original link.

**Independent Test**: Deliver a controlled item with a known title and inspect its
message caption and filename.

**Acceptance Scenarios**:

1. **Given** a supported video titled `Summer walk`, **When** it is sent, **Then**
   its caption is `Summer walk` and its filename is `Summer walk` plus the selected
   format's extension.
2. **Given** a titled audio-only choice or YouTube Music track, **When** it is sent,
   **Then** its document caption and filename identify the track using that title.
3. **Given** a supported titled picture, **When** it is automatically sent, **Then**
   its document carries the title as its caption and filename stem.
4. **Given** overlapping requests for different items, **When** they finish,
   **Then** each delivery carries only its own title.

---

### User Story 2 - Receive media with imperfect title metadata (Priority: P2)

A user still receives media when the source title is missing, long, or contains
characters unsuitable for display or filenames.

**Why this priority**: Optional metadata must not prevent a valid download.

**Independent Test**: Deliver items with missing, blank, Unicode, long, and unsafe
titles; inspect captions, filenames, and delivery outcomes.

**Acceptance Scenarios**:

1. **Given** a missing or blank title, **When** delivery completes, **Then** the
   caption is `Untitled media` and the filename uses that stem and the original extension.
2. **Given** Unicode, emoji, and markup-like punctuation, **When** sent, **Then**
   the caption preserves visible characters literally without interpreting formatting.
3. **Given** line breaks, controls, or path separators in a title, **When** sent,
   **Then** its caption is readable on one line and its filename is a single safe name.
4. **Given** a normalized title longer than 64 characters, **When** sent, **Then**
   the caption and safe filename stem each contain at most 64 characters, including
   a final `…` indicating truncation; the filename extension is retained separately.
5. **Given** no usable filename characters after normalization, **When** sent,
   **Then** the filename uses the fallback while the caption retains usable display text.

### Edge Cases

- Surrounding whitespace is trimmed; internal whitespace becomes single spaces;
  non-display controls are removed. Display-empty titles use the fallback.
- Path separators, leading dots, and traversal-like text cannot become local paths.
- A title resembling a filename does not change the selected format's final extension.
- Captions of exactly 64 characters remain unshortened. Longer titles retain their
  beginning and end with `…` within the 64-character budget. Filename stems may also
  be shortened when the complete filename would exceed 240 UTF-8 bytes. Count Unicode code points,
  not bytes; avoid cutting a combined visible character or emoji sequence, even if
  doing so leaves fewer than 64 code points. Apply the limit after normalization
  and, for filenames, after sanitization. Existing preview-card title limits are unchanged.
- Source refresh retains an original usable title; newly available metadata may
  replace a missing title. Permitted retries retain consistent naming.
- Unsupported links, inaccessible content, size limits, timeouts, and delivery
  failures keep their existing outcomes. Ambiguous sends are not retried.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Every successful currently supported YouTube, YouTube Music, LinkedIn,
  and Instagram delivery MUST attach the available source title as a plain-text
  caption on the delivered media message itself.
- **FR-002**: Videos, silent videos, audio documents, and picture documents MUST
  use a filename derived from the same title, with the selected format's extension.
  Showing the title only on an earlier card MUST NOT satisfy this requirement.
- **FR-003**: Missing, blank, or display-empty titles MUST use `Untitled media`;
  absent metadata MUST NOT prevent delivery or require another user action.
- **FR-004**: Captions MUST preserve visible Unicode and punctuation literally,
  normalize whitespace, and remove non-display controls. The normalized caption
  MUST contain at most 64 Unicode code points; longer titles MUST retain their
  beginning and end with `…`, included in the limit, without splitting a combined
  visible character or emoji sequence.
- **FR-005**: Filenames MUST replace path separators and incompatible characters
  with safe separators, trim leading/trailing spaces and dots, and shorten the stem
  to at most 64 Unicode code points, including a final `…` when shortened, without
  splitting a combined visible character or emoji sequence. The dot and selected
  extension MUST be retained outside that limit. Unusable stems MUST use `Untitled media`.
  The complete filename MUST additionally fit within 240 UTF-8 bytes, including
  the dot, extension, and any truncation ellipsis. Shorten the stem at whole visible
  character boundaries to satisfy both limits; the caption has no filename byte limit.
  Names MUST NOT contain local paths.
- **FR-006**: Each title MUST remain associated with its own request through selection,
  download, refresh, and permitted send retries. Retain the original usable title;
  refreshed metadata MAY supply one if originally unavailable.
- **FR-007**: Title presentation MUST preserve current delivery types, selected
  formats, media bytes, and embedded metadata. It MUST NOT rewrite tags or change
  audio delivery into another playback mode.
- **FR-008**: Existing cards, selection, automatic delivery, anonymous access,
  limits, deadlines, cleanup, failure guidance, and duplicate prevention MUST remain
  in force, with zero additional user actions.
- **FR-009**: Titles MUST NOT introduce new console logging, credential exposure,
  or persistent request storage. Existing diagnostic privacy rules apply.

### Key Entities

- **Source title**: Optional human-readable item name associated with a request,
  independently of its chosen media version.
- **Delivery title**: Normalized source title or fallback accompanying the sent item.
- **Delivery filename**: Safe title-derived name retaining the selected extension;
  changing this label does not change file contents.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All titled acceptance cases show the correct item's title on the
  delivered message and in the filename, across supported sources and delivery types.
- **SC-002**: All missing, blank, long, Unicode, and unsafe-character acceptance
  cases deliver with readable captions and safe filename stems of at most 64 Unicode
  code points each, correct truncation indicators, and intact extensions. Boundary
  cases MUST include normalized titles of 63, 64, and 65 code points and combined emoji,
  plus complete UTF-8 filenames of 239, 240, and 241 bytes before shortening.
  Every resulting complete filename MUST fit within 240 UTF-8 bytes.
- **SC-003**: All acceptance deliveries preserve selected media bytes and require
  zero additional user actions compared with the existing workflow.
- **SC-004**: Overlapping requests, refreshes, and permitted retries produce zero
  title mix-ups or duplicate deliveries in the controlled acceptance set.
- **SC-005**: Existing unsupported-link, inaccessible-content, size-limit, and
  delivery-failure acceptance cases retain their expected outcomes.

## Assumptions

- The confirmed title presentation is both a visible media message caption and a
  meaningful filename so saved and forwarded items are recognizable. Embedded tags
  and new music-player presentation are outside scope.
- Scope covers anonymous single-item media already supported by features 001–005;
  no new platforms, collections, access modes, or output formats are introduced.
- Existing source metadata supplies titles; titles are not generated, translated,
  or inferred from media contents or source links.
- Existing inspection and request handling supply the title association. The delivery
  title limit is 64 Unicode code points; complete filenames additionally have a
  240-byte UTF-8 limit for saving compatibility, including their selected extension.
- Runtime title labels are implemented. Controlled acceptance and remaining container,
  configured startup/health, and real Telegram client checks are recorded separately in
  [validation.md](validation.md#t020--requirements-reconciliation-and-external-acceptance-2026-10-19-local).
  Pending external checks do not relax any requirement below.

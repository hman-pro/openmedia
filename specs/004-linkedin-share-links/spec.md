# Feature Specification: LinkedIn Share Links

**Feature Branch**: `004-linkedin-share-links`

**Created**: 2026-09-23

**Status**: Draft

**Input**: User description: "LinkedIn links shared from the LinkedIn app must work. Today every link copied with the app's \"Share → Copy link\" is a short link on lnkd.in (for example https://lnkd.in/p/dMhfr6kG), and the bot rejects it as unsupported before any request starts, so LinkedIn effectively does not work for phone users. Each short link answers with a single HTTP 301 to a normal https://www.linkedin.com/posts/<slug>-<type>-<19-digit id>-<code>/ address with tracking query parameters (utm_source, utm_medium, utm_campaign, rcm). The bot should accept lnkd.in/p/ short links, follow that one redirect safely (anonymous, no cookies kept, at most one hop, destination must be linkedin.com, within the existing inspect deadline), and then treat the result exactly like a pasted linkedin.com post link, dropping tracking parameters. Second, some resolved post slugs end in a hyphenated code such as \"-lwx-\" (…-ugcPost-7508434034927017984-lwx-/); both our slug pattern and yt-dlp's LinkedInIE pattern (posts/[^/?#]+-(\d+)-\w{4}/?) reject it, so such posts must still be recognized, by their type and numeric id, and reach the video or picture path. Third, a link that is turned away before a request starts currently leaves no trace in the diagnostic log; a rejected link should be recorded there (diagnostic log only, never the console) so failures like this can be diagnosed. Out of scope: LinkedIn content that needs a login, other LinkedIn short-link paths than /p/, other URL shorteners. Evidence: T038 manual run on 2026-09-23, recorded in specs/003-streamlined-bot-ux/validation.md \"Remaining limitations\"."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Send a LinkedIn post shared from the phone app (Priority: P1)

A user taps "Share → Copy link" on a public LinkedIn post in the LinkedIn phone app and pastes
the copied short link into a private chat with the bot. The bot handles it exactly as it
would handle the post's full `linkedin.com` address: it shows the usual card, or sends the
media without a tap when there is only one version, as feature 003 defines.

**Why this priority**: The app's share button is how phone users get a LinkedIn link, and it
only ever produces a short link. Today every such link is refused, so LinkedIn does not work
at all for phone users. This story alone makes LinkedIn usable.

**Independent Test**: Paste an app-shared `lnkd.in/p/…` link of a public LinkedIn video post
and of a public picture post; each is delivered as if the full address had been pasted.

**Acceptance Scenarios**:

1. **Given** a public LinkedIn video post, **When** the user sends its app-shared short link,
   **Then** the bot shows `Checking link…` and continues exactly as for the post's full
   address, ending with the video delivered.
2. **Given** a public LinkedIn picture post, **When** the user sends its app-shared short
   link, **Then** the picture is delivered without a choice, as for the full address.
3. **Given** a short link whose destination is not a LinkedIn post (for example a LinkedIn
   profile, a job, or another website), **When** the user sends it, **Then** the bot explains
   that the link does not lead to a supported post and offers no choices.
4. **Given** a short link that no longer exists or does not redirect, **When** the user sends
   it, **Then** the bot explains that the link could not be opened and suggests sending the
   post's full address.

---

### User Story 2 - Posts whose address ends in an unusual code (Priority: P2)

Some LinkedIn post addresses end in a short code that contains a hyphen (for example
`…-ugcPost-7508434034927017984-lwx-/`). Whether the user pastes such an address or it comes
out of a short link, the bot recognizes the post by its type and number and handles it like
any other LinkedIn post.

**Why this priority**: One of the two app-shared links in the manual run resolved to such an
address. Without this story, about half of short links would still fail after Story 1.

**Independent Test**: Send a full post address ending in a hyphenated code, for a public
video post and a public picture post; both are delivered.

**Acceptance Scenarios**:

1. **Given** a public LinkedIn video post whose address ends in a hyphenated code, **When**
   the user sends that address, **Then** the video is delivered as for any LinkedIn video
   post.
2. **Given** the same kind of address for a picture post, **When** the user sends it,
   **Then** the picture is delivered.
3. **Given** two addresses of the same post that differ only in the trailing code or the
   tracking parameters, **When** each is sent, **Then** both are recognized as the same post.

---

### User Story 3 - Refused links leave a diagnostic trace (Priority: P3)

When the operator has the diagnostic log turned on and a user's message is refused before a
request starts (no supported link, more than one link, a link form the bot does not accept),
the refusal is written to the diagnostic log with the reason, so the operator can see why a
link failed without reproducing it by hand.

**Why this priority**: The LinkedIn failure left no trace in either log and had to be
reproduced manually. This does not change what users see, so it ranks below the two stories
that make links work.

**Independent Test**: With the diagnostic log on, send a message with an unsupported link and
a message with two links; each produces one refusal entry with its reason. With the log off,
nothing is written.

**Acceptance Scenarios**:

1. **Given** the diagnostic log is on, **When** a user sends a link the bot refuses, **Then**
   one entry records the refused link, the reason, and the chat, and the console shows none
   of them.
2. **Given** the diagnostic log is off, **When** a link is refused, **Then** nothing about it
   is written anywhere.
3. **Given** a short link that fails to resolve, **When** it is refused, **Then** the entry
   also records why resolution failed (for example not found, a destination outside LinkedIn,
   too many redirects, or timed out).

---

### Edge Cases

- A short link redirects more than once: refuse it with the "could not be opened" explanation;
  never follow a second hop.
- A short link redirects to a non-LinkedIn site, to `http://`, or to a LinkedIn host other than
  `linkedin.com` or `www.linkedin.com`: refuse it as not leading to a supported post; the
  destination is never contacted.
- A short link answers with a page instead of a redirect (for example an interstitial "you are
  leaving LinkedIn" page): refuse it with the "could not be opened" explanation.
- The short-link service is slow: resolution counts against the existing 60-second inspection
  deadline, and a timeout ends like any other inspection timeout.
- The short-link service rate-limits the bot: the user sees the same message as for any other
  rate-limited source.
- A message contains a short link and another supported link: this is two supported links and
  is refused with the existing "exactly one link" guidance (a behavior change: today the short
  link is ignored as a link to another site).
- The resolved post needs a login or is private: handled exactly as the same post pasted in full
  (existing unavailable-content explanation).
- The resolved address has no recognizable post type and number: refuse it as not leading to a
  supported post.
- The resolved address contains non-Latin text in its descriptive part (for example Persian
  words): recognized normally; only the type and number identify the post.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The bot MUST accept a link on `lnkd.in` whose path is `/p/<code>` as a supported
  LinkedIn link, counted like any other supported link for the "exactly one link" rule of
  feature 001 FR-001.
- **FR-002**: The bot MUST resolve such a link by making one anonymous request to it and
  reading its redirect destination. It MUST follow at most one redirect, MUST NOT send or keep
  cookies, and MUST NOT download the destination page as part of resolving.
- **FR-003**: Resolution MUST accept a destination only if it is `https://` on `linkedin.com`
  or `www.linkedin.com`; any other destination MUST be refused without being contacted.
- **FR-004**: A resolved destination MUST then be recognized exactly as if the user had pasted
  it, including every existing rule for LinkedIn post addresses; tracking parameters MUST NOT
  influence recognition or appear in the address used afterwards.
- **FR-005**: Resolution MUST happen within the existing inspection deadline (60 seconds) and
  after the user has seen `Checking link…`; it MUST use the same destination safety checks as
  every other source request.
- **FR-006**: A LinkedIn post address MUST be recognized by its post type (`activity`,
  `ugcPost`, or `share`, or none for older addresses) and its numeric identifier, whatever the
  trailing code after the number looks like, including codes that contain hyphens.
- **FR-007**: A post recognized under FR-006 MUST reach the same video or picture handling as a
  post whose address already matches today's rules; a video post whose original address the
  video downloader does not accept MUST still be offered through an address form it does
  accept for that post type.
- **FR-008**: Each refusal of a short link MUST give the user one of two plain explanations:
  the link could not be opened (not found, no redirect, too many redirects, timed out), or the
  link does not lead to a supported post (destination outside LinkedIn or not a post). Neither
  explanation may reveal the destination address.
- **FR-009**: When the diagnostic log is on, every message refused before a request starts
  MUST produce one diagnostic entry with the refused link or links, the refusal reason, and
  the chat and user identifiers; for a short link it MUST also record the resolution outcome.
  The message's other text MUST NOT be recorded.
- **FR-010**: Refusal entries MUST be written only to the diagnostic log, never to the
  console, and nothing MUST be written when the diagnostic log is off.

### Key Entities

- **Short link**: A LinkedIn share link on `lnkd.in/p/…`. Has one resolution outcome: resolved
  (to a LinkedIn post address), not found, no redirect, too many redirects, outside LinkedIn,
  or timed out.
- **LinkedIn post reference**: What the bot extracts from a post address: the post type and
  numeric identifier. Two addresses with the same reference are the same post.
- **Refusal record**: A diagnostic entry for a message refused before a request starts: the
  refused link or links, the reason, the chat and user identifiers, and, for a short link,
  the resolution outcome.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: App-shared links to public LinkedIn video and picture posts are delivered as
  often as the same posts' full addresses: in the manual check, every sampled short link whose
  full address works also works when sent as a short link.
- **SC-002**: A short link adds at most 3 seconds to the time before the user sees the card or
  the delivered picture, compared with its full address.
- **SC-003**: Both links from the 2026-09-23 manual run (`lnkd.in/p/dMhfr6kG` and
  `lnkd.in/p/dAjqaykT`) are delivered, or, if a post has since been removed, refused with an
  explanation rather than as an unsupported link.
- **SC-004**: No short link ever causes a request to a host outside LinkedIn's short-link and
  post hosts, verified by the controlled tests covering every edge case above.
- **SC-005**: With the diagnostic log on, an operator can find the reason for any refused link
  from the log alone, without reproducing it.

## Assumptions

- LinkedIn's `lnkd.in/p/` links answer an anonymous request with a single permanent redirect to
  the post's `linkedin.com/posts/…` address, as observed for both sampled links on 2026-09-23.
  If LinkedIn changes this, Story 1 degrades to the "could not be opened" explanation rather
  than to a wrong download.
- Resolving a short link is one extra anonymous request to LinkedIn and needs no new service,
  stored state, or credential, so it stays within the constitution's single-service, anonymous
  access model.
- Posts behind a login stay out of scope, as in feature 001; a short link does not change what
  content is reachable.
- Other LinkedIn short-link paths (anything on `lnkd.in` not under `/p/`) and other URL
  shorteners stay unsupported and keep today's "Send one supported public media link."
  guidance.
- The diagnostic log's existing rules (feature 002) apply unchanged: it is off by default,
  and it is the only place links and Telegram identifiers may be written.
- Whether hyphenated trailing codes (Story 2) occur only on `ugcPost` addresses is not known;
  the requirement covers every post type.

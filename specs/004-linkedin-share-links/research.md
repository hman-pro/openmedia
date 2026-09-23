# Research: LinkedIn Share Links

Each decision resolves an open point from `plan.md` Technical Context. Code references are
to the tree at `0903589`. Live evidence was gathered anonymously on 2026-09-23 with `curl`
and the pinned yt-dlp 2026.8.19; no cookies were sent.

## R1. How `lnkd.in/p/` links behave

- **Decision**: Treat a short link as a single anonymous `HEAD` whose only useful output is
  the `Location` header of a redirect response.
- **Evidence**:

  | Request | Answer |
  |---|---|
  | `HEAD`/`GET https://lnkd.in/p/dMhfr6kG` | `301`, `Location: https://www.linkedin.com/posts/abbas-goleh-…-ugcPost-7508434034927017984-lwx-/?utm_source=social_share_send&utm_medium=ios_app&rcm=…&utm_campaign=copy_link`, `content-length: 0` |
  | `HEAD https://lnkd.in/p/dAjqaykT` | `301`, `Location: https://www.linkedin.com/posts/amirhosein-mirzabeigi_…-share-7508424761698410497-2cX9/?utm_…` |
  | `GET https://lnkd.in/p/zzzzzzzz` | `404`, `text/html` |
  | `GET https://lnkd.in/dMhfr6kG` (no `/p/`) | `301` to the same post; out of scope per spec, stays unsupported |
  | Every `301` | Also sets `JSESSIONID`, `lang`, `lidc` cookies |

- **Consequences**: `HEAD` is enough, so resolution never reads a body (FR-002). The
  cookies are ignored: `GuardedHTTPTransport` has no jar, and `MetadataHTTP` keeps
  cookies only for Instagram hosts. The `rcm` parameter identifies the sharing member, so
  the query is dropped before the address is used or logged (FR-004, R8).
- **Alternatives rejected**: `GET` without following (reads a body we never use).

## R2. Where resolution runs

- **Decision**: Inside the inspect worker, as the first step of `SourceRouter.inspect`
  when the route is a short link. The worker resolves, validates, recognizes the destination,
  and continues with the normal LinkedIn path in the same process.
- **Rationale**: The parent does no source network I/O today. Every source request goes
  through `GuardedHTTPTransport` and `guard_public_sockets` in a single-use subprocess, with
  the parent's rate controller consulted through the worker protocol. Running inside
  inspection also puts resolution after `Checking link…` and inside the 60 s deadline
  (FR-005) with no new timing code. The cost is one `HEAD` of about 0.2–0.5 s, well within the
  3 s allowed by SC-002.
- **Alternatives rejected**:
  - Resolve in the bot handler before admission: blocking HTTP on the event loop, a second
    network path outside the worker guard, and the user would not see `Checking link…`
    first (FR-005).
  - A separate `resolve` worker operation before admission: a second subprocess spawn and
    import (about 1 s), a new protocol operation, and the same guard duplicated.

## R3. Making exactly one request without following the redirect

- **Decision**: Add `follow_redirects: bool = True` to `GuardedHTTPTransport.head` (and the
  `GuardedTransport` protocol). With `False`, `_open` returns the first response as is,
  redirect or not, after the usual `policy.resolve` destination check and the
  `on_request`/`on_response` hooks.
- **Rationale**: The public-address check, TLS pinning, 30 s per-connection cap, deadline,
  rate acquisition, and 429 handling all stay in one place. `lnkd.in` gets the same
  destination safety checks as every other source (FR-005).
- **Alternatives rejected**: `PublicEndpointPolicy(max_redirects=0)` raises
  `UnsafeDestination` on a redirect and loses the `Location`. A dedicated `http.client` call
  would duplicate the guard.

## R4. Validating the destination and naming the outcome

- **Decision**: `resolve_short_link` in `sources/linkedin.py` returns one of the outcomes in
  [data-model.md](data-model.md) "ResolutionOutcome". Rules, applied in order, without
  contacting the destination:
  1. Status `429` → the existing `rate_limited` (raised by the transport hook).
  2. Status `404` or `410` → `not_found`.
  3. Status not in `301/302/303/307/308`, or no `Location` → `no_redirect`. An interstitial
     page (`200`) lands here.
  4. `Location` joined against the short link. Host `lnkd.in` again → `too_many_redirects`,
     because following it would be a second hop.
  5. Scheme not `https`, host not exactly `linkedin.com`/`www.linkedin.com`, userinfo, or a
     port other than 443 → `outside_linkedin`.
  6. Query and fragment dropped. `recognize_source_url` fails, or the route is not a
     LinkedIn post or feed update → `not_a_post`.
  7. Otherwise `resolved`, with the query-free address.

  A connection or read timeout on the `HEAD` itself → `timed_out`. The overall 60 s
  deadline expiring is handled by the parent as any other inspection timeout (spec edge
  case) and does not carry an outcome.
- **User meaning** (FR-008): `not_found`, `no_redirect`, `too_many_redirects`, `timed_out`
  → new category `short_link_unresolved`. `outside_linkedin`, `not_a_post` → new category
  `short_link_not_post`. Two categories keep the texts distinct from 001's generic
  `unavailable` and `unsupported_url`, which suggest other actions.
- **Carrying the outcome to the parent**: `SourceAdapterError(category, stage="inspection",
  detail=<outcome>)`. The worker's `error` event gains an optional `detail`, forwarded only
  if it is one of the six failure outcome names. `WorkerRemoteError` gains `detail`. Any
  other value is dropped, so no free text crosses the protocol.

## R5. Request identity before and after resolution

- **Decision**: A short-link request is admitted with `source_url = https://lnkd.in/p/<code>`,
  `platform = "linkedin"`, `media_id = <code>`. After inspection, the coordinator
  re-recognizes `result.metadata.canonical_url`. It must be a LinkedIn post route whose
  `media_id` equals `result.metadata.media_id`. The coordinator then rebinds
  `request.source_url` and `request.media_id` before choices are published. Any mismatch is
  the existing `WorkflowError` ("different media identity").
- **Rationale**: Admission and the per-user and LinkedIn capacity rules need a platform before
  any network I/O. The post ID is not known until the worker resolves the link. Re-checking
  in the parent keeps worker output untrusted, as the current media-ID check does. After the
  rebind, the download-result check (`delivery.py:86`), metadata refresh
  (`SourceRouter.download` re-inspects `metadata.canonical_url`), and diagnostics all see
  the resolved post, so nothing downstream knows a short link was involved.
- **Canonical address keeps the trailing code**: live test, same ugcPost:

  | Address | Result |
  |---|---|
  | `…/posts/<original slug>-ugcPost-7508434034927017984-lwx-/` | `200`, one `<video data-sources>` |
  | `…/posts/<original slug>-ugcPost-7508434034927017984-abcd/` | `404` |
  | `…/posts/x-ugcPost-7508434034927017984-abcd/` | `404` |
  | `…/feed/update/urn:li:ugcPost:7508434034927017984/` | `200`, same page |

  The code is part of the address LinkedIn serves, so it cannot be normalized away. Two
  addresses are the same post when their (post type, numeric ID) match (US2 scenario 3). Their
  canonical URLs may still differ.

## R6. Recognizing post addresses (FR-006)

- **Decision**: Replace `_LINKEDIN_POST_SLUG` with two rules on the `posts/<slug>` segment:
  1. **Typed**: the rightmost `-(activity|ugcPost|share)-(\d{8,32})` followed by nothing or
     by `-<code>`, where `<code>` is 1–32 of `[A-Za-z0-9_-]` (hyphens allowed, trailing
     hyphen allowed). The descriptive prefix may hold any characters except `/ ? #` and
     whitespace, including raw non-Latin text.
  2. **Untyped** (older addresses): unchanged from today, except the code may contain
     hyphens. The type defaults to `activity`.
  The route keeps `urn_kind` and `media_id` as identity, and `canonical_url` as
  `https://www.linkedin.com/posts/<slug>` with the slug as given (R5).
- **Rationale**: Taking the rightmost type word makes a digit-heavy prefix harmless, for
  example `abbas-goleh-⭐-8346721bb_…`. Allowing raw Unicode covers pasted addresses that
  Telegram did not percent-encode (spec edge case). The adapters' identity checks (yt-dlp
  `id`, embed URN) still reject a mis-parse instead of downloading the wrong post.
- **Alternatives rejected**: Matching on the first type word (fails on prefixes that
  contain `share`), and ignoring everything after the ID (would accept `…-7508…/extra/path`).

## R7. Getting a hyphen-code video post to yt-dlp (FR-007)

- **Decision**: Register a subclass of yt-dlp's own `LinkedInIE` with a wider URL pattern
  (`OpenMediaLinkedInPostIE`, in `sources/ytdlp.py`) on each `YoutubeDL` instance with
  `add_info_extractor`. Its `_VALID_URL` is built from the same pattern as R6, so the
  recognizer and the extractor cannot drift apart. Extraction is inherited unchanged. Add
  `"openmedialinkedinpost": "linkedin"` to `_EXTRACTOR_PLATFORM`.
- **Evidence**: The stock pattern `posts/[^/?#]+-(?P<id>\d+)-\w{4}/?(?:[?#]|$)` rejects
  `…-lwx-/`. With the subclass registered under `allowed_extractors`, the live `-lwx-`
  post returned `id=7508434034927017984`, `extractor_key=OpenMediaLinkedInPost`, two MP4
  formats, and `webpage_url` equal to the input. The stock extractor remains first in
  order, so addresses it already accepts are unaffected.
- **Rationale**: yt-dlp still does all the extraction (constitution IV); only the address
  match is widened. It fetches the original address, the only posts form LinkedIn serves
  (R5).
- **Alternatives rejected**:
  - Rewriting the code to four characters: LinkedIn answers `404` (R5).
  - `feed/update/urn:li:ugcPost:<id>`: serves the page, but stock yt-dlp matches feed
    updates for `activity` only, so a subclass would be needed anyway, and the canonical
    address would change.
  - Reading the activity ID from the guest embed's `<link rel="canonical">` and handing yt-dlp
    `feed/update/urn:li:activity:<id>`: an extra request, and the media ID changes so the
    identity check would need an exception.
  - Parsing `<video data-sources>` ourselves: custom extraction when an open-source
    extractor already does it.
- **Upgrade risk**: The subclass relies on `LinkedInIE._real_extract` calling
  `self._match_id`. A controlled test pins that contract. The live test covers the real
  page. Both fail loudly on a yt-dlp upgrade that changes it.

## R8. Refusal records and resolution outcomes in the diagnostic log (FR-009, FR-010)

- **Decision**:
  - One `refused` entry from `BotHandlers.message`, at the single place a message is turned
    away before admission, including a group message that carries a link.
    Fields: `origin="input"`, `reason`, `links`, `chat_id`, `user_id`. No `request_id`
    exists yet, and the message text is never recorded.
  - `links` are the raw URL and text-link entities from the message (or plain-text
    candidates), **not** just the supported ones. The `lnkd.in` failure was invisible
    precisely because unsupported links were filtered out before anything could see them.
    Bounded to the first 5 links, 2,048 characters each.
  - Short-link outcomes: the request's `inspection_finished` entry gains `resolution`
    (the outcome name) on failure. On success it gains `resolution="resolved"` and
    `resolved_url`, the query-free address after resolution. The `received` entry already
    holds the short link, chat, and user, so request ID joins them (SC-005).
  - `diagnostics._KEEPS_URL` gains `links` and `resolved_url`. Every other field keeps full
    URL redaction.
- **Rationale**: Uses the existing `event()` path, which does nothing when the flag is off,
  so FR-010 holds by construction. Resolution failures happen after admission, so they
  belong on the request trace, not in a pre-request refusal.
- **Contract impact**: Feature 002 says links and identifiers appear only on `received`
  entries, and lists four origins. Both are amended (see
  [contracts/telegram-bot.md](contracts/telegram-bot.md) "Amendments").
- **Alternatives rejected**: Logging only supported links (misses the very case that
  motivated US3). Logging the resolved address with its query (writes the sharer's `rcm`
  identifier to disk).

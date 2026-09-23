# Implementation Plan: LinkedIn Share Links

**Branch**: `004-linkedin-share-links` | **Date**: 2026-09-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-linkedin-share-links/spec.md`

## Summary

The bot will accept `lnkd.in/p/<code>` links, the only form the LinkedIn phone app's share
button produces. The inspect worker resolves each one with a single anonymous `HEAD` that
does not follow redirects. It checks that the `Location` is an `https://` LinkedIn post,
drops tracking parameters, and continues exactly as if the full address had been pasted. The
parent then re-validates the resolved identity and rebinds the request to it.

Post addresses are recognized by post type and numeric ID, whatever the trailing code looks
like. yt-dlp reaches hyphen-code video posts through a subclass of its own `LinkedInIE` with
a wider URL pattern.

Messages refused before a request starts get one `refused` diagnostic entry. A failed
short-link resolution records its outcome on the request trace.

## Technical Context

**Language/Version**: Python 3.13 (unchanged)

**Primary Dependencies**: python-telegram-bot 22.8, yt-dlp 2026.8.19 (unchanged, no new
dependency; one subclass of the bundled `LinkedInIE`)

**Storage**: None. The resolved address lives on the in-memory request only

**Testing**: pytest with controlled fixtures and a recording fake transport. Two new opt-in
`live` manifest cases (short link, hyphen code)

**Target Platform**: Linux container (unchanged)

**Project Type**: Single-process Telegram bot service with single-use source workers

**Performance Goals**: A short link adds at most 3 s before the card (SC-002). One `HEAD`
measured at about 0.2–0.5 s

**Constraints**: Anonymous, no cookies kept. At most one redirect read, never followed.
Destination limited to `linkedin.com`/`www.linkedin.com`. Inside the fixed 60 s inspection
deadline. Links and identifiers only through `openmedia.diagnostic`

**Scale/Scope**: 1 platform (LinkedIn), 2 media kinds (video, picture). About 9 source
modules touched, no new module

All Technical Context unknowns are resolved in [research.md](research.md): live short-link
behavior (R1), where resolution runs (R2), the no-follow request (R3), outcome vocabulary
(R4), identity handoff (R5), slug rule (R6), yt-dlp for hyphen codes (R7), diagnostics (R8).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-checked after Phase 1 design.*

| Principle / constraint | Status | Evidence |
|---|---|---|
| I. Social media downloading; spec names platforms, media types, journeys | Pass | Spec Stories 1–3: LinkedIn video and picture posts, phone share journey |
| II. Telegram is the UI; invalid/unsupported/failure behavior defined; download logic separate | Pass | contracts/telegram-bot.md adds two failure texts. Resolution lives in `sources/linkedin.py`, not in handlers |
| III. Python by default; simplest arrangement | Pass | No new service or process type. Resolution reuses the inspect worker (R2) |
| IV. Reuse open source; isolate platform code | Pass | yt-dlp still extracts. Only its URL match is widened, in `sources/ytdlp.py` (R7). Rejected alternative: a custom `<video>` parser |
| V. Container deployment | Pass | No image or runtime change. Startup check still run |
| Access modes stated; private content out of scope | Pass | Spec Assumptions: anonymous only, login posts out of scope |
| Limits and what users see | Pass | Unchanged 50 MB cap. `rate_limited`/`timeout` meanings reused for `lnkd.in` |
| Timeouts, concurrency, cleanup | Pass | Resolution inside the 60 s inspect deadline and the existing LinkedIn rate token. No new temporary files |
| No credentials in logs | Pass | `rcm` tracker dropped before use or logging (R1, R8). Refusal fields are fixed vocabularies plus links |
| No DB/queue/service | Pass | None added |
| Project rule: anonymous access, cookies not persisted | Pass | Transport has no jar. `lnkd.in` cookies are discarded (R1) |
| Project rule: links and identifiers only via `openmedia.diagnostic` | Pass | `refused` uses `diagnostics.event`. Amends 002's "only on `received`" wording (contracts/telegram-bot.md) |
| Project rule: callback data carries only `option_id` | Pass | Unchanged. The short link never enters callback data |

Post-design re-check: still passing. The two contract amendments (001 link counting, 002
log fields) are recorded in the contracts and scheduled in Polish.

## Project Structure

### Documentation (this feature)

```text
specs/004-linkedin-share-links/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── linkedin-links.md
│   └── telegram-bot.md
├── checklists/requirements.md
└── tasks.md             # created by /speckit-tasks
```

### Source Code (repository root)

```text
src/openmedia/
├── sources/__init__.py   # lnkd.in host + short_link route; R6 slug rule; 2 ErrorCategory values;
│                         #   GuardedTransport.head(follow_redirects); router resolves short links first
├── sources/linkedin.py   # resolve_short_link(): one HEAD, outcome classification (R4)
├── sources/ytdlp.py      # OpenMediaLinkedInPostIE registered per YoutubeDL; extractor→platform map
├── network.py            # GuardedHTTPTransport.head/_open: follow_redirects=False
├── workers.py            # error event `detail` (allowlisted outcomes); WorkerRemoteError.detail
├── coordinator.py        # short-link identity rebind after inspection; `resolution` on trace
├── bot.py                # refusal reason + raw link candidates; `refused` event; 2 failure texts
└── diagnostics.py        # _KEEPS_URL += links, resolved_url

tests/
├── unit/test_links.py                      # short-link routes, R6 slugs incl. -lwx- and Persian
├── contract/test_linkedin.py               # every ResolutionOutcome; no Cookie; no second request
├── contract/test_network.py                # head(follow_redirects=False) returns 3xx untouched
├── contract/test_ytdlp.py                  # subclass suitability, id, LinkedInIE._match_id pin
├── contract/test_bot_errors.py             # two new texts; short link + other link → one-link text
├── unit/test_diagnostics.py                # links/resolved_url not redacted; other URLs still are
├── integration/test_diagnostic_trace.py    # refused entries; resolution on inspection_finished
├── integration/test_download_flow.py       # short link → card / picture end to end, identity rebind
└── fixtures/linkedin/                      # trimmed hyphen-code post page with <video>, PROVENANCE
```

**Structure Decision**: Keep the single-package layout. There is no new module: short-link
resolution is LinkedIn-specific, so it lives beside the LinkedIn embed parser in
`sources/linkedin.py`. The yt-dlp subclass lives in `sources/ytdlp.py`, the one file that
already knows yt-dlp internals. The router in `sources/__init__.py` stays the only place
that decides adapter order.

## Delivery order (for /speckit-tasks)

1. **Foundational**: `head(follow_redirects=False)` in transport and protocol; the two
   `ErrorCategory` values and texts; worker `detail` pass-through. These are shared by US1
   and US3.
2. **US1 (P1)**: `lnkd.in` host and `short_link` route; `resolve_short_link`; router step;
   coordinator identity rebind; short-link plus other-link counting.
3. **US2 (P2)**: R6 slug rule; `OpenMediaLinkedInPostIE`; hyphen-code fixture. US2 is
   independent of US1, but SC-003's `dMhfr6kG` needs both.
4. **US3 (P3)**: `refused` entry with reason and raw links; `resolution`/`resolved_url` on
   the trace; `_KEEPS_URL`.
5. **Polish**: 001/002 amendments; README supported-links line; quickstart §3–4 live and
   manual run; `validation.md`; update 003 `validation.md` "Remaining limitations" to point
   here.

## Second-order effects

- **Group chats**: a group message holding only an `lnkd.in` link now gets the private-chat
  pointer. Before, it was ignored as a link to another site. This follows from FR-001 and is
  intended.
- **Fake transports**: every test double implementing `head` (`test_adapter_transports.py`,
  `test_instagram.py`, `test_metadata_clients.py`, `test_linkedin.py`) must accept the new
  keyword, even where it is unused.
- **Rate budget**: a short link spends one extra LinkedIn `metadata` token. Under heavy
  LinkedIn use, short links hit the parent's cooldown slightly sooner than full addresses.
- **Canonical URLs are not normalized**: two shares of one post keep different
  `canonical_url` values, because the trailing code is load-bearing (R5). Anything that
  compares posts must compare (`urn_kind`, `media_id`), never the URL.
- **yt-dlp upgrade coupling**: the subclass depends on `LinkedInIE._real_extract` calling
  `_match_id`. A controlled test pins this, so a breaking upgrade fails CI instead of
  silently dropping hyphen-code videos to the picture path.
- **Diagnostic privacy surface grows**: raw links from refused messages, including
  non-supported sites, are now written to disk when the flag is on. They stay behind the
  same dev-only flag, retention, and `0600` file mode as `received`.
- **Existing tests**: none reference `lnkd.in` today, so no test flips from ignored to
  supported. `test_links.py` slug cases gain hyphen-code rows. Current rows stay valid,
  because R6 accepts a superset of today's slugs.

## Complexity Tracking

No constitution violations to justify.

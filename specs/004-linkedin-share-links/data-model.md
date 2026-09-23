# Data Model: LinkedIn Share Links

All entities are in-memory values. Nothing is stored beyond one request, and there is no new
persistent state (constitution, "State lives in memory").

## SourceRoute (changed)

`src/openmedia/sources/__init__.py`. One new `route_kind` value. Existing fields unchanged.

| Field | Short link | Resolved LinkedIn post |
|---|---|---|
| `platform` | `linkedin` | `linkedin` |
| `media_id` | the short code, `[A-Za-z0-9_-]{1,32}` | numeric post ID, 8–32 digits |
| `canonical_url` | `https://lnkd.in/p/<code>` (query dropped; a fragment is rejected as for every route) | `https://www.linkedin.com/posts/<slug as given>` (query dropped, trailing code kept, research R5) |
| `route_kind` | **`short_link`** (new) | `post` (unchanged) |
| `urn_kind` | `None` | `activity`, `ugcPost`, or `share` |

Validation:

- `lnkd.in` is a supported host for normalization and counting (FR-001), so a short link
  counts toward the "exactly one link" rule.
- Only the path `/p/<code>`, with exactly two segments, is a short-link route. Any other
  `lnkd.in` path raises `unsupported_url`, which keeps today's
  `Send one supported public media link.` text.
- `www.lnkd.in` and other hosts are not added.

## LinkedIn post reference (identity rule, changed)

The identity of a LinkedIn post is the pair (`urn_kind`, `media_id`), taken from a post
address by the rules in research R6. Two addresses with equal pairs are the same post, even
when their slug text, trailing code, or query differ. `canonical_url` is the address to
fetch, not the identity.

## ResolutionOutcome (new)

A fixed vocabulary, used as `SourceAdapterError.detail`, on the worker `error` event, and in
diagnostics as `resolution`.

| Outcome | Condition (research R4) | Error category | User meaning |
|---|---|---|---|
| `resolved` | Valid LinkedIn post destination | none | continue as the resolved post |
| `not_found` | `404` or `410` | `short_link_unresolved` | could not be opened |
| `no_redirect` | not a redirect status, or no `Location` | `short_link_unresolved` | could not be opened |
| `too_many_redirects` | `Location` is on `lnkd.in` again | `short_link_unresolved` | could not be opened |
| `timed_out` | the `HEAD` connection or read timed out | `short_link_unresolved` | could not be opened |
| `unreachable` | the `HEAD` connection was refused or reset | `short_link_unresolved` | could not be opened |
| `outside_linkedin` | not `https`, not `linkedin.com`/`www.linkedin.com`, userinfo, or non-443 port | `short_link_not_post` | not a supported post |
| `not_a_post` | LinkedIn host, but not a recognizable post or feed update | `short_link_not_post` | not a supported post |

`429` stays the existing `rate_limited`. A destination-safety failure on `lnkd.in` itself
stays the existing `unsafe_destination`. The overall 60 s inspection deadline stays the
existing `timeout`. None of these three carries an outcome.

## ErrorCategory (changed)

`src/openmedia/sources/__init__.py`. Two new values, `short_link_unresolved` and
`short_link_not_post`. Their user texts are in [contracts/telegram-bot.md](contracts/telegram-bot.md).

## WorkerRemoteError (changed)

`src/openmedia/workers.py`. Gains `detail: str | None`. It is set only when the worker's
`error` event carries a `detail` that is one of the seven failure outcome names above.
Otherwise it is `None`.

## DownloadRequest (behavior change, no new field)

`src/openmedia/models.py`. For a short-link request, `source_url` and `media_id` start as the
short link and its code. They are rebound once, by the coordinator, to the resolved
`canonical_url` and post ID, after the parent re-validates the worker's metadata (research R5).
State transitions are unchanged: `checking` → `awaiting_selection` / `downloading` → ….

## Refusal record (new diagnostic entry)

Written through `diagnostics.event` only, when the diagnostic flag is on.

| Field | Type | Notes |
|---|---|---|
| `origin` | string | `input` (new origin value) |
| `stage` | string | `refused` |
| `reason` | string | `not_private`, `no_link`, `unsupported_link`, `too_many_links`, `unsupported_url`, `unsupported_collection` |
| `links` | list of strings | Raw link candidates from the message, at most 5, each at most 2,048 characters. Empty for `no_link`. Not URL-redacted |
| `chat_id`, `user_id` | integers | Telegram identifiers |

The message text, names, and usernames are never recorded.

Reason rules, in order: group chat with at least one link → `not_private`. No link
candidates at all → `no_link`. Candidates but no supported link → `unsupported_link`. More
than one supported link → `too_many_links`. The one supported link fails recognition →
`unsupported_url` or `unsupported_collection` (the error category).

## Request trace additions

| Entry | New field | When |
|---|---|---|
| `inspection_finished` (failed) | `resolution` | Short-link request whose worker error carried an outcome |
| `inspection_finished` (ok) | `resolution="resolved"`, `resolved_url` | Short-link request, after the rebind. `resolved_url` is query-free |

`resolved_url` and `links` join `source_url` as the only fields the formatter does not
URL-redact.

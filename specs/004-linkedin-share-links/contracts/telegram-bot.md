# Telegram Bot Contract (004)

This file only adds to `specs/001-media-download/contracts/telegram-bot.md` and
`specs/003-streamlined-bot-ux/contracts/telegram-bot.md`. Both stay in force.

## Accepting a short link

- An `lnkd.in/p/<code>` link is a supported link. It counts toward "exactly one link" like
  any other supported link.
- A message with a short link plus another supported link gets the existing
  `Send exactly one supported public YouTube, LinkedIn, or Instagram link.` reply. This is a
  behavior change: before 004 the short link was ignored as a link to another site.
- An accepted short link follows the 003 progress surface unchanged. `Checking link…` is sent
  first, and resolution happens while it is shown. From then on the user sees exactly what the
  resolved post's full address would produce: a card, automatic video, or a picture.

## New failure meanings

Shown on the request's status surface (the `Checking link…` message), in the same way 003
shows any checking-stage failure. No keyboard. The destination address never appears.

| Category | Text |
|---|---|
| `short_link_unresolved` | `That LinkedIn link could not be opened. Send the post's full linkedin.com address.` |
| `short_link_not_post` | `That LinkedIn link does not lead to a supported post. Send a public LinkedIn post link.` |

Unchanged meanings that a short link can also reach:

| Situation | Category | Text source |
|---|---|---|
| `lnkd.in` rate-limits the bot | `rate_limited` | 001 table |
| The 60 s inspection deadline expires during or after resolution | `timeout` | 001 table |
| The resolved post needs a login or is private | `unavailable` | 001 table |
| An `lnkd.in` path other than `/p/` | `unsupported_url` | 001 table (`Send one supported public media link.`) |

## Refused messages in the diagnostic log

With `OPENMEDIA_DIAGNOSTIC_LOG=1`, every message refused before a request starts writes one
`refused` entry (data-model "Refusal record"). With the flag off, nothing is written. The
console never shows these entries or their links. Example:

```json
{"ts":"2026-09-23T10:12:03.511Z","level":"INFO","origin":"input","stage":"refused","chat_id":123456789,"user_id":123456789,"reason":"too_many_links","links":["https://lnkd.in/p/dMhfr6kG","https://youtu.be/abcdefghijk"]}
```

A short-link request that fails resolution is not a refusal, because it was already
admitted. Its `inspection_finished` entry carries `resolution`, for example
`"error_category":"short_link_unresolved","resolution":"not_found"`.

## Amendments

Applied during implementation, each marked "(amended by 004)":

1. 001 `contracts/telegram-bot.md`, conflict/failure meaning table: add the two rows above.
   Note that `lnkd.in/p/` links count as supported links.
2. 002 `contracts/diagnostic-log.md`, "Flag on" guarantees: links and Telegram identifiers
   appear on `received` **and `refused`** entries. A query-free `resolved_url` may appear on
   `inspection_finished`. Still no token, signed media URL, names, or usernames.
3. 002 `data-model.md`, `origin` values: add `input`. Entry fields: add `reason`, `links`,
   `resolution`, `resolved_url`.

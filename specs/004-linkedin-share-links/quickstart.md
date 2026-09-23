# Quickstart: Validate LinkedIn Share Links

## 1. Controlled tests

```bash
uv sync --locked --group dev
uv run pytest tests/unit/test_links.py              # short-link + slug recognition (R6)
uv run pytest tests/contract/test_linkedin.py       # resolution outcomes (R4), no second hop
uv run pytest tests/contract/test_network.py        # head(follow_redirects=False)
uv run pytest tests/contract/test_ytdlp.py          # OpenMediaLinkedInPostIE (R7)
uv run pytest tests/contract/test_bot_errors.py tests/integration/test_diagnostic_trace.py
uv run pytest                                       # full suite, network disabled
```

Expected: all pass with the network disabled by `tests/conftest.py`. Short-link tests use a
fake transport that records every URL requested. SC-004 is asserted on that record: no host
outside `lnkd.in`, `linkedin.com`, `www.linkedin.com`, and the fixture's media host.

## 2. Scenario checks (fake transport, controlled fixtures)

| Scenario | Input | Expect |
|---|---|---|
| Short link → video post | `HEAD` 301 to a fixture posts URL with `utm_*`/`rcm` query | One `HEAD` to `lnkd.in`, no `Cookie` header. yt-dlp receives the query-free address. The card is the same as for the full address |
| Short link → picture post | 301 to a picture post | `Picture — downloading…` → `sent.`, as for the full address |
| Hyphen-code video post | `…-ugcPost-7508434034927017984-lwx-/` pasted | Recognized as `ugcPost` `7508434034927017984`. yt-dlp is reached through `OpenMediaLinkedInPostIE` |
| Same post, two codes/queries | `…-lwx-/` vs `…-lwx-/?utm_source=x` | Same (`urn_kind`, `media_id`) |
| Raw Persian slug | Unencoded Unicode slug | Recognized |
| `404` | short link | `short_link_unresolved` text. `resolution=not_found` in the log |
| `200` interstitial | short link | `short_link_unresolved`, `no_redirect` |
| 301 to `lnkd.in/p/other` | short link | `short_link_unresolved`, `too_many_redirects`. The second URL is never requested |
| 301 to `https://example.com/`, `http://www.linkedin.com/…`, `https://de.linkedin.com/…` | short link | `short_link_not_post`, `outside_linkedin`. Destination never requested |
| 301 to `https://www.linkedin.com/in/someone/` | short link | `short_link_not_post`, `not_a_post` |
| Connection reset on the `HEAD` | short link | `short_link_unresolved`, `unreachable` |
| `429` | short link | Existing rate-limited text |
| Short link + YouTube link | one message | `Send exactly one supported …` and a `refused` entry, `too_many_links`, both links |
| `lnkd.in/abc` (no `/p/`) | one message | `Send one supported public media link.` and a `refused` entry, `unsupported_url` |
| `bit.ly/x` only | one message | Existing one-link guidance and a `refused` entry, `unsupported_link`, `links=["https://bit.ly/x"]` |
| Any refusal, flag off | — | No file created. Console unchanged |
| Any refusal, flag on | — | Console holds no link, chat ID, or user ID |

## 3. Live checks (opt-in)

Add cases to your machine-local manifest (see `tests/fixtures/live-sources.example.json`),
never to the repository:

```json
{"case_id": "linkedin-short-video", "platform": "linkedin", "media_type": "video",
 "url": "https://lnkd.in/p/REPLACE_ME", "expected_identity": "REPLACE_ME", "expected_type": "video"},
{"case_id": "linkedin-hyphen-code", "platform": "linkedin", "media_type": "video",
 "url": "https://www.linkedin.com/posts/REPLACE_ME-lwx-/", "expected_identity": "REPLACE_ME", "expected_type": "video"}
```

```bash
OPENMEDIA_LIVE_MANIFEST=~/openmedia-live.json uv run pytest -m live tests/live/test_sources.py
```

A skip is not a pass. Record results and dates in `validation.md`.

## 4. Manual run against Telegram (SC-001, SC-002, SC-003)

```bash
uv run python -m openmedia --check-config
OPENMEDIA_DIAGNOSTIC_LOG=1 OPENMEDIA_DIAGNOSTIC_LOG_DIR=$PWD/logs uv run python -m openmedia
```

From the LinkedIn phone app, use "Share → Copy link" and paste the link into a private chat
with the bot:

1. `https://lnkd.in/p/dMhfr6kG` (ugcPost, `-lwx-` code) and `https://lnkd.in/p/dAjqaykT`
   (share). Each is delivered, or, if the post has since been removed, refused with an
   explanation. Neither may get `Send one supported public media link.` (SC-003).
2. For one video and one picture post, send the short link and then the full address. Time
   from sending to card or picture must differ by at most 3 s (SC-002). Take the
   `inspection_finished.elapsed_seconds` values from `logs/openmedia-*.log`.
3. Send a non-link message and a two-link message. `logs/` gets one `refused` entry each, and
   the terminal shows none of the links (SC-005, FR-010).
4. Check `logs/` for `rcm=`. It must not appear anywhere (research R1, R8).

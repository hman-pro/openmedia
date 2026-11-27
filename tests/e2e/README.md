# End-to-end suite

Drives a running bot the way a user does: a dedicated Telegram **test account** sends links
over the Telegram user API (Telethon), taps card buttons and checks what arrives — message
type, caption, filename, bytes. It complements the controlled suite (fake transport) and
the live suite (sources only); it is the only check that exercises Telegram itself.

Opt-in and excluded by default (`-m 'not live and not e2e'`).

## One-time setup

Use a dedicated test account, never a personal one: its login session grants full access to
that account.

1. Create an API app at <https://my.telegram.org> ("API development tools"), any name,
   platform Desktop. Any account may log in through it.
2. Store the values in the OS keyring (account `openmedia-e2e`). macOS prompts without echo:

   ```bash
   security add-generic-password -a openmedia-e2e -s openmedia-e2e-tg-api-id -w
   security add-generic-password -a openmedia-e2e -s openmedia-e2e-tg-api-hash -w
   security add-generic-password -a openmedia-e2e -s openmedia-e2e-dev-bot-username -w   # dev bot, no @
   security add-generic-password -a openmedia-e2e -s openmedia-e2e-bot-username -w       # production bot (optional)
   ```

   On Linux use `secret-tool store --label=… service <name>` with the same service names.
   Environment variables named after the service (`OPENMEDIA_E2E_TG_API_ID`, …) override
   the keyring for one run.
3. Log the test account in once; the session goes to the keyring as
   `openmedia-e2e-tg-session`:

   ```bash
   uv run --group e2e python -m tests.e2e.login
   ```

4. In the test account, open the dev bot and press **Start**.
5. Add the e2e case IDs below to your private live manifest (`OPENMEDIA_LIVE_MANIFEST`,
   outside version control).

## Running

```bash
scripts/dev.sh                     # terminal 1: the dev bot (only one poller per token)
export OPENMEDIA_LIVE_MANIFEST=…   # terminal 2
uv run --group e2e pytest -m e2e   # about 13 minutes
OPENMEDIA_E2E_SLOW=1 uv run --group e2e pytest -m e2e -k expiry   # adds the 15-minute expiry case
OPENMEDIA_E2E_TARGET=prod uv run --group e2e pytest -m e2e        # the deployed bot instead
```

Start `scripts/dev.sh` first: its exact `uv sync --group dev` removes the e2e group from
the project environment, and `uv run --group e2e` adds it back without disturbing the bot.

A missing credential, manifest case or unresponsive bot skips with the reason. Each test
waits for its outcome before the next starts, so the bot sees one request at a time;
Instagram cases are spaced 60 s apart.

## Manifest case IDs

The live-suite IDs under `"cases"` (`youtube-video`, `youtube-music`,
`youtube-music-context`, `linkedin-video`, `linkedin-short-video`, `linkedin-hyphen-code`,
`linkedin-image`, `instagram-video`, `instagram-image`) plus these under a separate
`"e2e_cases"` list, which the live source suite does not iterate (an all-over-limit case
would fail it). Entries need only `case_id` and `url`:

| Case ID | Needs |
|---|---|
| `youtube-title-slash` | A short YouTube video whose title contains `/` (stem under 60 characters) |
| `youtube-title-emoji` | A short YouTube video whose title contains emoji |
| `youtube-all-over-limit` | A YouTube video whose every choice exceeds 50 MB (for example a 10-hour recording) |

`youtube-music-context` must carry a `list=` parameter; the collection-refusal case is built
from it.

## Known outcomes

- `test_instant_tap_is_accepted` is an expected failure while the publish/tap race exists
  (008 follow-up item 7); it passes once fixed.
- `test_instagram_picture_is_delivered_or_refused_as_login_only` is an expected failure while
  Instagram refuses anonymous picture access from the test network.
- Telegram's Bot API rewrites long and emoji filenames on upload (006 SC-002 note), so the
  emoji-title test checks the caption literally and only the filename's extension.

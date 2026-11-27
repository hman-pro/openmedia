# Resume feature 008 — updated 2026-11-27

Do not cancel running workflows. Check their actual status before acting on one.
Never move or delete tags, overwrite a published image version, replace immutable
assets, or remove required sources. `validation.md` holds the full evidence for every
step below; this file is only the resume point.

## Where things stand

- **T059–T065 done.** T063 (2026-11-23) installed preview.5 on the operator's Ubuntu
  26.04 amd64 host and migrated the old root-Compose bot. T064 run 2 (2026-11-26)
  passed every update, rollback, failure, shutdown and migration case between
  preview.6 and preview.7. T065 (2026-11-26/27) passed every maintenance case on the
  production host by operator choice.
- **Production:** preview.7 running and selected on the host.
- **T066–T068 done (2026-11-27).** Feature 008 is complete as a preview. T067 reconciled
  `README.md`, `deploy/README.md`, the preview.7 release notes (update paragraph) and the
  validation register. Stable promotion still needs I001-SOURCES and hosts beyond Ubuntu
  26.04 amd64.

## Next steps

1. Next release candidate (preview.8): items 4, 5 and 7 below, test-first, then the release
   lessons under "Release state". Run `tests/e2e` against the dev bot before tagging and
   against production after the update; the instant-tap test flips to a pass once the
   race is fixed.
2. Merge PR #1 (`008-public-docker-deployment` → `main`, open, 41 commits ahead as of 2026-11-27) when ready.
3. Host cleanup now that T065 is done: the recovery pin `openmedia-recovery:52520a82…`,
   `openmedia:local`, `~/openmedia/.env`, and the closed LUKS2 vault
   `/var/lib/openmedia-backup/vault.luks` (holds a copy of the current token;
   passphrase in the Mac Keychain as `openmedia-backup-luks`). Also the T066 S1
   diagnostics directory `/opt/openmedia/diagnostics` (real links and Telegram IDs), unless
   already deleted after the S1 timing read.
4. Release follow-up: add a bounded retry to `download_url`
   (`scripts/release/collect_sources.py`) in the next release candidate.
5. Release follow-up: `codec_family()` (`src/openmedia/sources/__init__.py`) misses the
   RFC 6381 form `vp09.*`, so an Instagram DASH VP9 download is refused with `source codec
   changed` (T066 S0). Fix test-first in the next release candidate; also check
   `hev1`/`hvc1` and `vp08`. Pre-existing since `f4708eb`; deferred by the operator.
6. Done 2026-11-27 13:13: the plain Instaloader request still got 401 three hours later,
   so the Instagram image is source-blocked (T066 S2).
7. Product findings from the T066 automated client (pre-existing, next release candidate):
   - Publish/tap race: a tap that arrives between the card being sent and the request
     moving to awaiting-selection is answered "stale" (`coordinator.py`: `_publish_preview`
     then the selection record; `CHECKING` → `STALE`). Seen 3 of 5 times with instant taps.
   - Duplicate failure sentence: a checking-stage `internal` failure reads "The checking
     stage failed. The checking stage failed. Retry the link later." (`__main__.py`
     `notify_failure` prefix plus `bot.py` `failure_message` fallback; same shape for
     `timeout` and `storage_exhausted`).
   - Telegram rewrites upload filenames on the hosted Bot API: stems over 60 characters get
     `_` for spaces and lose punctuation; emoji and Arabic punctuation become spaces; a
     trailing `…` is dropped (probed with the test bot). 006 allows a 240-byte stem, so long
     titles arrive underscored. Decided 2026-11-27: recorded as a Telegram limitation
     (006 SC-002 amended); capping the stem at 60 code points stays an option.
8. T068: the T066 client is now the opt-in suite `tests/e2e/` (README there), driven by a
   dedicated test account against the dev bot by default. First run 2026-11-27 against the
   dev bot: 18 passed, 2 expected failures (publish/tap race reproduced; Instagram picture
   source-blocked), expiry case opt-in. Keychain account `openmedia-e2e`: `-tg-api-id`,
   `-tg-api-hash`, `-tg-session` (test account), `-dev-bot-username`, `-bot-username`
   (production). The second personal account used in T066 S2–S4 was logged out. The private
   manifest is `~/.config/openmedia/live-sources.json` (e2e-only cases under `e2e_cases`).
   Start `scripts/dev.sh` before the suite: its exact `uv sync` removes the e2e group,
   and `uv run --group e2e` adds it back.

## Release state

| Version | Commit | State |
|---|---|---|
| preview.1 | `17c7d6d` | Immutable sources; empty image draft; stale-attempt receipt rejected |
| preview.2 | `4f693c5` | Images pushed, sources retained; INCOMPLETE draft (regctl template) |
| preview.3 | `083ea8f` | Signed; evidence verify failed on exclusive gh flags; INCOMPLETE draft |
| preview.4 | `b4d087d` | Rejected before publication: unreviewed SRT revision; tags kept |
| preview.5 | `c84a168` | **Accepted**, run 44149181265; index `sha256:2262f99c…6b81` |
| preview.6 | `d938409` | **Accepted**, run 45238239957; index `sha256:1a500b06…700f` |
| preview.7 | `80c72fa` | **Accepted**, run 45687934499; index `sha256:8c27c75f…8cc6`; T064 run 2 and T065 passed; in production |

Release lessons that cost a version before:

- **Inventory a no-cache image before tagging.** `docker build --no-cache --pull`, then
  resolve every component against `release/source-policy.json`. Cached APT layers hide
  new Debian security revisions; SRT (preview.4) and librsvg (preview.7 pre-tag) each
  needed a reviewed exact policy entry.
- **Push the branch and wait for CI before tagging.** Branch CI builds both native
  architectures and runs `collect_sources collect` on both inventories, so it proves
  amd64 resolution before a version is spent.
- **Source downloads have no retry.** `download_url` (`scripts/release/collect_sources.py`)
  makes one attempt; the 2026-11-25 branch push run failed `sources` on a
  `RemoteDisconnected` while the PR run of the same commit passed. Adding a bounded
  retry is a release-code change and needs its own candidate.
- Actions artifacts last one day. Already-published materials can force a new version.

## Server

- SSH alias `openmedia`. Ubuntu 26.04.1 amd64, rootful Docker Engine 29.10.0,
  Compose v5.8.0, sudo-rs. **Sudo is operator-only**: hand privileged steps to the
  operator; never ask for a password.
- Deployment: root-owned `/opt/openmedia` (`compose.yaml`, `deploy.env` 0600 holding the
  selected digest, `secrets/` with the token file). preview.7 running and selected
  as of 2026-11-27 (restored from backup in T065).
- `/opt/openmedia/migration` was deleted after T065's restore. The pinned old image
  `openmedia-recovery:52520a82…` is still present (cleanup item above).
- Acceptance staging: `~/openmedia-008-acceptance` (runner, guide blocks, release
  assets, logs). Run 1's runner is kept as `t064.run1.sh`.
- Guide functions: never call `start_checked` (or other guide functions) inside
  `&&`, `||`, `if` or `!`. Bash disables errexit there, the running guard is skipped,
  and Compose force-recreates a healthy bot (`deploy/README.md`, before the function
  definitions).
- The operator runs the real Telegram requests. Bot username, source URLs and Telegram
  IDs stay in private notes outside Git, never in validation or release notes.
- After any interrupt test, run `docker ps` before leaving: on 2026-11-25 an
  interrupted start without a recovery start left the bot down for 13.5 h unnoticed.
- The server's default editor is vim (`EDITOR`/`VISUAL`/`SUDO_EDITOR` in `~/.bashrc`).
  A runner that tees its output must run the editor on `/dev/tty`: an editor screen
  echoes pasted secrets into the log (T065 session R, token revoked).
- Read runner logs through a token-redacting filter, and scan them before printing.

## Suggested first prompt

"Continue feature 008 from `specs/008-public-docker-deployment/follow-up.md` for preview.8 (follow-up items 4, 5 and 7)."

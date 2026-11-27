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
- **T066–T067 open.**

## Next steps

1. Run T066 (inherited media matrix), then T067 (claims reconciliation).
2. T067 must note that the published preview.7 `deploy/README.md` predates two guide
   fixes: the OP-EXIT command (`4ef5dcc`; the old one kills PID 1, a no-op under
   `init: true`) and the rotation empty-replacement guard (block 21 now ends before
   `stop_selected` when the edited file is empty; `tests/contract/test_deploy_guide_rotation.py`).
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
6. Repeat the Instagram image check once, with plain Instaloader and a single request, a
   few hours after 2026-11-27 10:10. This rules out our own requests as the cause of the 401.

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

"Continue feature 008 from `specs/008-public-docker-deployment/follow-up.md` with T066."

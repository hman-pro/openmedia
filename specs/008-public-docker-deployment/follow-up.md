# Resume feature 008 — updated 2026-11-28

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

1. Next release candidate (preview.8), branch `008-preview-8`: items 4, 5 and 7 are fixed
   test-first (2026-11-28, `7bb97de` code, `a0d2adb` CI filter); 7c stays a recorded
   Telegram limitation. Remaining before tagging: the release lessons under "Release
   state" (no-cache inventory against `release/source-policy.json`, branch CI green) and
   `tests/e2e` against the dev bot (`scripts/dev.sh` from this branch); the instant-tap
   test now fails, not xfails, on a stale answer. Then merge to `main`, tag, and run
   `tests/e2e` against production after the update.
2. Done 2026-11-27: PR #1 merged to `main` by fast-forward.
3. Host cleanup now that T065 is done: the recovery pin `openmedia-recovery:52520a82…`,
   `openmedia:local`, `~/openmedia/.env`, and the closed LUKS2 vault
   `/var/lib/openmedia-backup/vault.luks` (holds a copy of the current token;
   passphrase in the Mac Keychain as `openmedia-backup-luks`). Also the T066 S1
   diagnostics directory `/opt/openmedia/diagnostics` (real links and Telegram IDs), unless
   already deleted after the S1 timing read.
4. Done 2026-11-28: `download_url` retries 3 times (5 s, 15 s) on transient errors only;
   HTTP 4xx, an insecure redirect and a checksum mismatch still fail at once.
5. Done 2026-11-28: `codec_family()` maps `vp09.*`→vp9, `vp08.*`→vp8 and
   `hev1`/`hvc1`/`h265`→hevc (T066 S0 Instagram DASH VP9 refusal). Recheck I001-SOURCES
   with the live suite after preview.8 is deployed.
6. Done 2026-11-27 13:13: the plain Instaloader request still got 401 three hours later,
   so the Instagram image is source-blocked (T066 S2).
7. Product findings from the T066 automated client. Done 2026-11-28 except the Telegram
   limitation (7c): the race waits up to 5 s for the card record (003 callbacks contract),
   the stage is named once (003 stage text), the notes use `publish.OPEN_GATES`, and CI
   decides the sources job in `scripts/release/ci_changes.py` (`changes` job):
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
   - Stale accepted release notes: `scripts/release/publish.py` (`accepted-notes.txt`)
     hard-codes "Deployment acceptance and inherited source/live readiness gates remain
     open"; since 008 deployment acceptance passed, preview.8 would publish a wrong
     sentence. Make the text name only the gates still open.
   - CI time: the `sources` job (`.github/workflows/ci.yml`) takes about 20 minutes on every
     push, docs-only ones included. Run it only when release inputs change (`Dockerfile`,
     `uv.lock`, `pyproject.toml`, `release/`, `scripts/release/`, the workflows) and always
     on `workflow_call` and tags. Do it per job, not with a workflow-level `paths:` filter,
     which would also skip `controlled` and `native`. Use a `git diff` step, not a new
     third-party action, and check that `publish.py`'s `ci.yml` assertions still pass.
     Accepted gap: a new Debian security revision with no repository change shows up only
     at the pre-tag no-cache inventory (release lessons below).
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

"Continue feature 008 from `specs/008-public-docker-deployment/follow-up.md`: release preview.8 from branch `008-preview-8` (next step 1)."

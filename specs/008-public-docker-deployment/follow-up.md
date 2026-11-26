# Resume feature 008 — updated 2026-11-25

Do not cancel running workflows. Check their actual status before acting on one.
Never move or delete tags, overwrite a published image version, replace immutable
assets, or remove required sources. `validation.md` holds the full evidence for every
step below; this file is only the resume point.

## Where things stand

- **T059–T061, T063 done.** T063 (2026-11-23) installed preview.5 on the operator's
  Ubuntu 26.04 amd64 host from the guide, migrated the old root-Compose bot and
  delivered real media.
- **T062 open** until the T064 update/rollback between an accepted pair passes.
  preview.5 and preview.6 each passed their complete pipelines.
- **T064 open.** Run 1 (2026-11-24) passed N1, N2, N3, U1, SD, RB, MP, IC-a, IR and MR,
  and found two defects:
  1. **Console token leak** (IC-b): a Telegram-rejected token reached stderr through
     Python's default traceback printer. Fixed in `1f00ea4`; needs preview.7 on the host.
  2. **Interrupted start left a container** (IS): reproduced with one real Ctrl-C on
     2026-11-25, which cleaned up correctly. Run 1's failure was the runner's double
     signal, not the guide.
- **preview.7** is the candidate carrying the fix (see the release table).
- **T065–T067 open.** T065 needs a decision on the isolated acceptance host.

## Next steps

1. Verify preview.7 independently on the host (account-free, as for preview.6) and
   record its release in `validation.md`. The run passed every job on 2026-11-25.
   (For a future release: a network drop before any image push writes no images;
   rerun **all jobs** on the same tag, never failed-jobs-only.)
2. Stage preview.7 on the host: public assets as `cand-assets/`, checkout and extracted
   guide blocks at the preview.7 commit, `checkout.rev`, and `cand.image`,
   `cand.version`, `cand.revision` (`base.*` already names preview.6).
3. The operator runs `~/openmedia-008-acceptance/t064.sh` (cases N1 N2 N3 UP U1 SD ST RB
   MP IC TO IS IR MRPE, about 30–40 min with prompts). New since run 1: UP (update-path
   preflight failure with the old bot running), ST (stale-callback tap after restart),
   TO (timed-out start by dropping Telegram traffic in `DOCKER-USER`), IS as an operator
   Ctrl-C prompt, MRPE (persistence failure through a duplicate `OPENMEDIA_IMAGE` line).
4. Record run 2 in `validation.md`, update the register rows, mark T062/T064 `[X]` only
   if every case passes.
5. Then T065, T066, T067 in order.

## Release state

| Version | Commit | State |
|---|---|---|
| preview.1 | `17c7d6d` | Immutable sources; empty image draft; stale-attempt receipt rejected |
| preview.2 | `4f693c5` | Images pushed, sources retained; INCOMPLETE draft (regctl template) |
| preview.3 | `083ea8f` | Signed; evidence verify failed on exclusive gh flags; INCOMPLETE draft |
| preview.4 | `b4d087d` | Rejected before publication: unreviewed SRT revision; tags kept |
| preview.5 | `c84a168` | **Accepted**, run 44149181265; index `sha256:2262f99c…6b81` |
| preview.6 | `d938409` | **Accepted**, run 45238239957; index `sha256:1a500b06…700f` |
| preview.7 | `80c72fa` | **Published**, run 45687934499; index `sha256:8c27c75f…8cc6`; T064 run 2 candidate |

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
  selected digest, `secrets/` with the token file). preview.6 running and selected
  as of 2026-11-25.
- Keep for T064 reruns: `/opt/openmedia/migration` (old compose/env) and the pinned
  old image `openmedia-recovery:52520a82…`.
- Acceptance staging: `~/openmedia-008-acceptance` (runner, guide blocks, release
  assets, logs). Run 1's runner is kept as `t064.run1.sh`.
- Guide functions: never call `start_checked` (or other guide functions) inside
  `&&`, `||`, `if` or `!`. Bash disables errexit there, the running guard is skipped,
  and Compose force-recreates a healthy bot (`deploy/README.md`, before the function
  definitions).
- The operator runs the real Telegram requests. Bot username, source URLs and Telegram
  IDs stay in private notes outside Git, never in validation or release notes.
- After T065: retire the old root-Compose project's credential copy, once its return
  path is no longer needed.

## Suggested first prompt

"Continue feature 008 from `specs/008-public-docker-deployment/follow-up.md`. Check the
preview.7 release run, then stage preview.7 for T064 run 2."

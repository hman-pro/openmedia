# Resume feature 008 — updated 2026-11-17

The operator requested continuing tomorrow in a new session and explicitly requested
**not stopping running pipelines**. Do not cancel existing jobs. Check their actual
status before doing anything with a workflow. No preview.4 workflow has been started.

## Start here

- Workspace: `/Users/homan/source/openmedia`.
- Branch: `008-public-docker-deployment`; preserve `007-local-server-deploy`.
- Read `CLAUDE.md`, this file, `tasks.md` and the latest `validation.md` entries.
- Continue **Phase 7, T062**. T059–T061 are historically complete; T062–T067 remain
  unchecked. Rerun affected final-candidate gates after changing release code.
- Use `speckit-implement` scoped to this phase. Requirements checklist is 16/16 checked;
  no extension hooks were configured. Do not mark live gates passed from fixtures.
- Use `git -c core.fsmonitor=false` for Git inspection/mutations; the fsmonitor IPC
  intermittently fails. Network/uv cache commands often need sandbox escalation.

## Current release state

| Version | Commit | State |
|---|---|---|
| preview.1 | 17c7d6df5dc9f86a8f5ebaad46b542e21d3d1ea2 | Immutable sources published; empty image draft; promotion rejected a stale-attempt controlled receipt; temporary CI artifacts expired |
| preview.2 | 4f693c5a1fb0d675524c1752f2424552fc57944e | Both images/index pushed, immutable sources retained; empty INCOMPLETE draft; regctl digest-template failure |
| preview.3 | 083ea8fc3d1df7963383a5c011696c2ad31143a2 | All pre-push checks and promotion passed; both signatures created; evidence verification failed on mutually exclusive CLI flags; empty INCOMPLETE draft |

Never move/delete tags, overwrite published image versions, replace immutable assets,
or remove required sources. These incomplete versions are not accepted releases.

Release run [42084150441](https://github.com/hman-pro/openmedia/actions/runs/42084150441)
is completed/failure. All jobs except `evidence` passed, including native amd64/arm64,
full sources, public source retrieval and no-rebuild promotion. Both signing actions
inside `evidence` succeeded. Draft ID **435600508**, zero assets, title INCOMPLETE.

At the last check, supplemental CI **42083680165** was still running; leave it alone.
Supplemental CI **42083688507** succeeded. Inspect live state; do not rely on stale notes.

## Verifier fix applied — 2026-11-17

The correction below is now applied with a failing-before/passing-after regression
test. Targeted release suites: 135 passed; full controlled suite: 1167 passed,
3 live deselected. Build, release pin audit and diff checks pass. Preview.4 is the
next unused version; its complete pipeline and public acceptance remain required.
See the latest validation entry before resuming.

### Original failure and recovery requirements

`scripts/release/validate_release.py::verify` builds a gh 2.103.3 command containing
both `--cert-identity` and `--signer-workflow`. The actual CLI rejects this combination:

```text
if any flags in the group [cert-identity cert-identity-regex signer-repo signer-workflow]
are set none of the others can be; [cert-identity signer-workflow] were all set
```

Use **only the exact `--cert-identity` selector**, retaining all other repository,
source-ref/digest, issuer, hosted-builder, local-bundle and additional certificate checks.
The exact SAN includes repository, `.github/workflows/release.yml` and version tag;
the existing parsed-certificate checks independently enforce that same workflow identity.
The wrong-workflow negative proof in `publish.py` uses only `--signer-workflow` and is
already a valid CLI combination; do not weaken its rejection check.

Before editing, extend the controlled `signed_boundary` verifier in
`tests/contract/test_release_policy.py` to reproduce gh's mutually exclusive selector
behavior, and observe the existing positive verification fail. Then fix the command,
run the targeted and full controlled suites, build, audit pins and check the diff.
Update `research.md`'s earlier description of CLI selectors if needed.

This correction has already been proved manually with the **actual preview.3 bundles**:
both index and manifest cryptographically verify without auth using the exact SAN
selector alone, and `check_verified_attestations` passes all extra checks. The CLI
output is retained privately under `preview3-public/*.verification.json`.
No trust-policy relaxation or version upgrade is needed.

Because the tagged workflow code still contains the invalid argv, rerunning its failed
evidence job cannot fix it. Commit the correction and use a **new unused preview tag
pair**, expected preview.4, through the complete gated workflow. Do not patch/move an
old tag or manually claim a failed workflow accepted. Verify version availability first.

The prior committed fixes are:

- 4f693c5: retry guidance and stale source/run/attempt receipt coverage.
- 083ea8f: regctl `manifest head` default digest output (the `{{.Digest}}` template
  fails for OCI indexes), and paginated authenticated draft lookup after tag-API 404.
- Last full controlled run: **1167 passed, 3 live deselected**, 32 existing PTB warnings.
  Last targeted release-policy run: **65 passed**. Build/pin audit/diff checks passed.

## Actual preview.3 identities and evidence

- Index: `sha256:96a142370770804af0b515283597bc119c2a5041732e113412cd564d8901ee1a`.
- amd64 child: `sha256:079700a675219af4c27d47a6f38f7b2d4eb90b508bba3fb3ed4546370751c0f2`.
- arm64 child: `sha256:e704484dc38195f967f35d02f9f1bf9357ca77db9bab517148c7e7ba6a0641a7`.
- Release manifest SHA256: `117a77faea0c5b9cb401b151ad03592033533e8c420a0bff6366a548607d21ca`.
- Source manifest SHA256: `43a2d33f9ab0429681554ba415e8e91003697be143f1dc2623c2893976590f4f`.
- Both platform config/archive identities are in `validation.md`.
- GH attestation IDs: **64182594** index; **64182617** manifest. Bundles can be
  recovered through `repos/hman-pro/openmedia/attestations/sha256:DIGEST` (take
  `.attestations[0].bundle`), even after temporary Actions artifacts expire.
- GHCR package is **Public**, verified in signed-in owner UI and through empty-config
  anonymous retrieval; no visibility change was made by the agent.
- Independent full anonymous source download/validation passed. Independent anonymous
  exports of both full image platforms passed, matching native config/labels. No image
  was started by these checks. These facts do not close F008-PUBLIC while final public
  assets/workflow acceptance are incomplete.

Local scratch root: `/tmp/openmedia-008-phase7` (not guaranteed to survive cleanup).
Important directories:

- `preview3-{controlled,amd64,arm64,sources,public-source-receipt,final-evidence}`.
- `preview3-public-sources`: complete anonymous source bytes.
- `preview3-public`: real manifest/index/children/SBOMs, source hardlinks, both real
  Sigstore bundles, successful gh verification JSON and both anonymous image exports.
- `preview2-*`: failed attempt records, immutable-source downloads and an unsigned
  local reconstruction which passed actual-material assembly/bundle validation.
- `mac-tools/regctl`: official 0.11.7 darwin-arm64, independently checksum-verified;
  SHA256 `8ac077a1eeb834d3053714e86ccbd838d0da46567df8cd7c2695d1a19135bf60`.
- `fetch_records.py`: selective remote ZIP metadata retrieval; now supports root and
  `final/` JSON/text records, without downloading large archives.
- `fetch_public.py`: anonymous complete final release verification helper.
- `verify_public_images.py`, `prefinal_public_images.py`: anonymous image-byte checks.

Actions artifacts have **one-day retention**. Re-fetch public permanent assets and
attestation API records if scratch or artifacts are gone. Never reuse stale native
artifacts as another source/run/attempt. A full retry before any publication requires
**all jobs**, not failed-jobs-only; already-published materials/image content can require
a new version. Public evidence failures must retain incomplete state and sources.

## Server state and operator agreements

- `ssh openmedia-server` works again (the user restored network access).
- Ubuntu **26.04.1 amd64**; rootful Docker **29.9.3**, Compose **5.7.0**, containerd.io
  **2.4.2**, installed from official Docker repository **by the operator** this session.
- Initially hit a file conflict with Ubuntu `docker-compose-v2`; operator removed it
  with `sudo dpkg --remove docker-compose-v2`, then completed official installation
  using `apt-get --fix-broken install ...`. `dpkg --audit` is clear. All required
  Compose wait/run flags and rootful AppArmor/seccomp/cgroupns checks pass.
- Existing `openmedia-openmedia-1` still runs **openmedia:local** and is healthy after
  the daemon/package restart. Do not mistake that for new-release acceptance.
- `/opt/openmedia` was absent at last inspection; no new protected deployment/token
  files were provisioned and no new polling service was started by the agent.
- SSH user has Docker access but **no noninteractive sudo**. The operator explicitly
  chose to perform privileged steps manually; do not request a password or assume sudo.
- Current bot credential remains only on host in the old protected configuration.
  Do not print/transfer it into evidence/CI or accidentally start a second poller.
- Staged reviewed files/tools under `/home/homan/openmedia-008-phase7-083ea8f`.
  Linux pinned gh 2.103.3/regctl 0.11.7 are in `tools/`; helpers start no poller.
  Re-stage changed verifier code from a reviewed new commit before using it.
- The repository guide has a later documentation-only Compose collision/recovery
  improvement, shell-syntax checked (32 guide / 6 quickstart blocks). It is not yet
  copied over the server's staged 083ea8f guide. Runtime/tagged inputs are unchanged.

## Private live-test inputs and manual testing

The operator said the manifest needed creating and will perform Telegram tests personally.
The bot reference is saved **outside Git** in the private operator notes; do not put
the username, source URLs or Telegram IDs into public validation/release notes.

- Server manifest: `/home/homan/openmedia-008-phase7-083ea8f/private/live-sources.json`
  (0600, parent 0700). Nine cases; original feature-004 short links both resolved via
  one anonymous HEAD/301, including the actual hyphen-code URL. Selected YouTube video,
  music and context inputs; Instagram video/image candidates need type/availability
  confirmation. All outcomes remain unexecuted.
- Local copy: `/tmp/openmedia-008-phase7/private-live-sources.json`.
- Private worksheet: `/tmp/openmedia-008-phase7/private-manual-tests.md`.
- Private operator notes: same local scratch root, `private-operator-notes.md`, and
  server `private/operator-notes.md`.
- No diagnostic storage/mount was present on the existing bot, and no previous live
  manifest was found. Do not claim diagnostic/live gates passed from preparation.
- User has been told to wait for an explicit verified-deployment-ready signal before
  using the worksheet. No test messages were sent by the agent.

After T062, continue T063 protected configuration/preflight, one polling owner and
representative real delivery; T064 update/rollback/migration/shutdown; T065 isolated-host
maintenance/rotation/reboot/removal; T066 full inherited matrix assessment; T067 final
claims/evidence reconciliation. T062 additionally requires a separately gated compatible
baseline/candidate pair if no usable previous accepted published image exists. Current
preview.1–3 incomplete versions do not silently become accepted baselines. Coordinate
disruptive host/manual steps and token rotation with the operator.

## Suggested first prompt tomorrow

“Continue feature 008 from `specs/008-public-docker-deployment/follow-up.md`.
Preserve running CI and immutable releases; start with the known gh verifier flag fix.”

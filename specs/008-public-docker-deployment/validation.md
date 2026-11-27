# Validation: Public Docker Deployment

Created 2026-10-28. This register starts with no feature-008 acceptance claims. A checked
implementation task is not a passed acceptance gate. Releases remain previews until all
required container and live/manual stable-readiness gates pass.

## Record format

Every execution appends a record; retain earlier attempts and link superseding evidence.
For a matrix gate, record each case/platform/host separately; a partial run does not pass
the aggregate. The register below initializes every unexecuted gate as `pending`.

| Field | Required value |
|---|---|
| gate_id / requirement_ids | Release/check identity and related acceptance requirements; use the gate IDs below and exact requirement IDs |
| class | Controlled, native container, public distribution, or deployment-network/manual |
| release / platform | Exact source revision, tag/package version, image/config ID and registry digest when available, architecture; distinguish these identities |
| environment | Host OS, Engine/Compose/tool versions, network context without secrets |
| result | `pending`, `pass`, `fail`, or `blocked` with a concrete reason |
| gate_scope | Feature 008 acceptance or inherited stable-readiness obligation |
| failure_class | Deployment regression, evidenced pre-existing source limitation, unclassified, or none |
| evidence / limitations | Sanitized commands/results, timing, observed constraints, next action; links to retained evidence |

For initial pending rows: release/platform and environment are `not yet selected/recorded`,
failure_class is `none`, and evidence/limitations is the required execution described in
the row. These defaults do not imply execution or successful classification.

Passing a substitute does not transition a live/manual gate to pass.
Public evidence uses sanitized case IDs, never source URLs, Telegram identifiers, tokens,
credential hashes or raw host environment. Private manifests and permitted diagnostics
stay outside Git and release assets. No host credentials, live manifests, or media enter assets.

## Completion and stable readiness

Feature completion requires every F008 gate below to pass, representative real Telegram
media delivery, and execution and assessment of every inherited I001–I006 case. Only
an evidenced pre-existing source limitation may remain an open inherited obligation at
feature completion. It still blocks stable readiness and that capability's public claims.
Deployment regressions and unclassified failures block feature completion. Unexecuted
inherited checks cannot be excused as source limitations.

Stable readiness additionally requires all inherited obligations to pass; no open
container/live/manual gate is closed by reclassification. Preserve preview status and
consistent README/deployment/release claims while any required stable gate remains open.

A known-source classification must cite an earlier validation record (exact section,
date, versions, source-case identity and observed outcome) or an independent comparison
establishing the failure without deployment changes on a comparable network. Record
baseline and candidate identities and conditions. The older documents below are evidence
indexes, not automatic classifications; stale or mismatched evidence is insufficient.
A failure without that evidence is `unclassified`. Platform/process failures are not
source limitations. No classification changes a failed result to `pass`.

## Feature 008 acceptance register

All rows have gate_scope **Feature 008 acceptance**.

T034's US1 candidate milestone passed on `52f4dc8` (record below). Aggregate
final-candidate, promotion and public-distribution gates still require T059–T062;
their pending rows are not a claim that the completed US1 checks were unexecuted.

| gate_id | requirement_ids | class | Required execution / evidence and limitations | result |
|---|---|---|---|---|
| F008-SETUP | FR-003, FR-009, FR-019 | Controlled | Official pin provenance/checksums; validation register; Git/Docker secret exclusions; execution record below | pass |
| F008-CONFIG | FR-008–FR-010, FR-018; SC-004 | Controlled | Presence conflicts including empty keys, file/path/type/size/ASCII/newline/grammar errors, bounded nonblocking reads, direct compatibility, redacted chains/repr/logs/workers and CLI no-poll behavior | pass |
| F008-REGRESSION | FR-014, FR-017–FR-021; SC-006, SC-008 | Controlled | Full locked controlled suite; native byte/stream-copy, source categories, titles, state/deadlines/limits, worker/child/upload cleanup, failure/refusal/retry and privacy regressions | pass |
| F008-NATIVE-AMD64 | FR-007, FR-018; SC-004 | Native container | Native linux/amd64 build/import config identity; restricted offline smoke, tools/EJS, local stream-copy, bounded writable tmpfs, read-only root, UID/capabilities/init, secret permissions/negative cases, no runtime executable acquisition | pass |
| F008-NATIVE-ARM64 | FR-007, FR-018; SC-004 | Native container | Same checks independently on native linux/arm64; retain runner/image/tool versions and exact checked image ID | pass |
| F008-COMPOSE | FR-005, FR-007–FR-011, FR-016, FR-018 | Controlled | Effective published Compose with fixture settings; fixed project and digest; explicit allowed environment, read-only secret, limits/logging, no ports/build/socket; retained local-build Compose path | pass |
| F008-RELEASE-POLICY | FR-001–FR-004, FR-020; SC-002 | Controlled | Identity/manifest/source collectors and tamper/failure cases; both imported identities before either push; zero writes on pre-push failure; correct incomplete distribution behavior after push/finalization; immutable pins/least privilege/tag authority/preview | pass |
| F008-SOURCES | FR-002, FR-004; SC-002 | Public distribution | Both actual-image component closures, Debian Built-Using/system+application Python/unmanaged/embedded coverage and notices; exact source hashes/build materials; anonymous source-only release retrieval before first push; retain sources on later failure | pass |
| F008-PUBLIC | FR-001, FR-003–FR-004, FR-020; SC-001–SC-002 | Public distribution | Actual preview: anonymous both-platform pull, exact child/index/config joins, local signed raw-index/manifest bundles with trusted numeric repo/workflow/source identity, negative proof, all final public assets redownloaded/hash verified; no rebuild promotion; immutable-release staging | pass |
| F008-INSTALL | FR-005–FR-010, FR-018–FR-019; SC-003–SC-004 | Deployment-network/manual | Clean supported host guide walkthrough, secret ownership as UID 10001, local preflight vs remote token validity, exact digest polling/fresh health and representative native media delivery | pass (operator host Ubuntu 26.04 amd64, 2026-11-23); other host combinations pending in the supported-host matrix |
| F008-UPDATE | FR-011–FR-015, FR-019; SC-003, SC-005–SC-006 | Deployment-network/manual | Failed pull/preflight leaves old poller uninterrupted; successful update; timeout/failure/interruption stops candidate; finite 180s health wait; protected selection persistence; explicit current-settings rollback incl unavailable/incompatible failure; migration/recovery of local image ID; one poller | pass (operator host Ubuntu 26.04 amd64, preview.6 ↔ preview.7, T064 run 2 2026-11-26); other host combinations pending |
| F008-SHUTDOWN | FR-014, FR-019, FR-021; SC-006 | Deployment-network/manual | Real active-work shutdown <=20s, child termination/reaping and scratch/upload cleanup, no duplicate uncertain/canceled sends; fresh request after recovery | pass (operator host Ubuntu 26.04 amd64, preview.6 ↔ preview.7, T064 run 2 2026-11-26); other host combinations pending |
| F008-OPERATIONS | FR-015–FR-017, FR-019; SC-003, SC-007 | Deployment-network/manual | Token rotation/recreated file mount, console privacy/status/resources, optional 002 diagnostics, unexpected process exit, reboot and intentional stop, upstream outage/recovery with no health restart loop/additional poller, backup/restore/removal | pass (operator host Ubuntu 26.04 amd64, preview.7, T065 2026-11-26/27); other host combinations pending |
| F008-ASSESSMENT | FR-019–FR-021; SC-008 | Deployment-network/manual | Execute/assess full inherited matrix, classify every failure from evidence, reconcile actual release/README/deployment capability claims; distinguish feature completion from stable readiness | pass (T066 assessment 2026-11-27; T067 reconciliation 2026-11-27) |

F008-INSTALL/UPDATE/SHUTDOWN/OPERATIONS records identify the actual tested Ubuntu
24.04 or 26.04 LTS and amd64 or arm64 combination. Untested combinations stay pending
as separate support-verification entries; one host does not verify all four combinations.

## Inherited 001–006 stable-readiness register

All rows have gate_scope **Inherited stable-readiness obligation**. Rerun against the
feature-008 selected release; earlier passing evidence remains historical evidence only.
Source/media matrix cases are individual anonymous YouTube video, LinkedIn video/image,
Instagram video/image, and the additional YouTube Music cases below. Preserve negative
outcomes as failure/refusal evidence, never as successful media support.

| gate_id | requirement_ids / original gate | class | Required execution / earlier evidence index | result |
|---|---|---|---|---|
| I001-CONTROLLED | 001 FR/SC controlled acceptance; 008 FR-021 | Controlled | Full media/adapter/delivery/lifecycle regression suite; [001 validation](../001-media-download/validation.md) | pass |
| I001-SOURCES | 001 FR-002, SC-001; T026/T074 | Deployment-network/manual | Full five-category inspect/download native formats, actual bytes, anonymous access and limitations; earlier 001 validation including 2026-09-21/22 attempts | fail (T066 S0 2026-11-27: live-suite Instagram video hits the pre-existing `vp09` codec-family defect, but the bot's card picks H.264 and delivered the reel 4/4 in S2; Instagram image anonymous 401 persisted 3 h with a plain Instaloader baseline, source-blocked) |
| I001-RUNTIME | 001 SC-007; T053/T075 | Native container | Constrained container build/start/config plus real dedicated-bot polling, fresh health, active-work shutdown/child cleanup; [001 runtime evidence](../001-media-download/validation.md) | pass (preview.7 on Ubuntu 26.04 amd64, T066 S0 2026-11-27) |
| I001-TELEGRAM | 001 SC-001, SC-005–SC-006; T054/T076 | Deployment-network/manual | Deployment-network five categories and two independent accounts; originating-chat isolation, repeated/forged/stale selections, available audio-only/absent-audio, native received output | pass (T066 S1–S4 2026-11-27; B on A's card and forged callback not executable live) |
| I001-TIMING | 001 SC-002–SC-003; T055/T080 | Deployment-network/manual | 20 eligible inspections: >=19 acknowledgments <=2s and previews <=30s; 20 eligible <=20MB deliveries: >=19 <=2min; <=2 global/<=1 Instagram concurrency; document exclusions/replacements | pass (T066 S2 2026-11-27, automated client) |
| I002-DIAGNOSTICS | 002 FR/SC; quickstart local/container checks | Deployment-network/manual | Enabled real trace/refusal, console/token privacy; disabled leaves no files; retention/rotation and mounted persistence across restart; [002 quickstart](../002-file-logging/quickstart.md) | pass (T066 S1 2026-11-27) |
| I003-UX | 003 SC-001–SC-005; manual matrix | Deployment-network/manual | One preview/status surface, first-page choices, audio/combined/image/video behavior, inline video including silent video on actual clients, native delivery/refusal; [003 validation](../003-streamlined-bot-ux/validation.md) | pass (T066 S3 2026-11-27; iPhone playback checked by the operator) |
| I004-SHORT-LINKS | 004 FR-010, SC-001–SC-005 | Deployment-network/manual | Anonymous lnkd.in short/full equivalence, video/image delivery, redirect/refusal diagnostics and console privacy; [004 validation](../004-linkedin-share-links/validation.md) | pass (T066 S1 2026-11-27) |
| I005-LIVE | 005 SC-001–SC-005; T032/T036 | Deployment-network/manual | Plain/context/offset track identity, whole native audio, selected format/bytes, collection refusal and ordinary YouTube regression; [005 validation](../005-youtube-music-download/validation.md) | pass (T066 S0 + S4 2026-11-27) |
| I005-TELEGRAM | 005 US1–US3; T033/T037 | Deployment-network/manual | One automatic native audio document/no selection, card/progress/completion, whole-track context behavior, collection refusal and ordinary YouTube; actual received-byte comparison where available | pass (T066 S4 2026-11-27, automated client, native bytes equal) |
| I005-CONTAINER | 005 T034/T038 | Native container | Configured restricted startup/health with runtime credentials; prior missing-daemon result is not source evidence | pass (preview.7 on Ubuntu 26.04 amd64, T066 S0 2026-11-27) |
| I006-CONTAINER | 006 T019 | Native container | Locked distribution/build/import, version/notices, configured startup and live health; [006 validation](../006-media-delivery-titles/validation.md#external-acceptance-and-release-gaps) | pass (preview.7 on Ubuntu 26.04 amd64, T066 S0 2026-11-27) |
| I006-TITLES | 006 FR-001–FR-009, SC-001–SC-005; manual quickstart | Deployment-network/manual | Caption, saved/forwarded filenames, long/Unicode titles, client versions/rendering/playback, native received bytes including YouTube Music; controlled upload labels do not close this gate | pass with a Telegram limitation (T066 S3 2026-11-27: Bot API rewrites long and emoji filenames; captions pass) |

## Execution records

### F008-SETUP — 2026-10-28

- gate_id / requirement_ids: F008-SETUP; FR-003, FR-009, FR-019 (setup scope only).
- class: Controlled.
- release / platform: working branch `008-public-docker-deployment`, baseline source
  `ba133f557afec6fe4596fa59da14eb5f8a3a6798`; Phase 1 uncommitted changes; native linux/arm64 Docker context probe;
  no published version or digest selected.
- environment: macOS 27.0.1 arm64; Docker Engine 29.9.2 linux/arm64, Compose 5.6.1,
  gh 2.103.3; official upstream HTTPS/API and authenticated Debian APT metadata only.
  Synthetic nonsecret fixtures; no source URLs, Telegram requests or live credential use.
- result: pass — validation schema/register, official pin lookup/download hashes and
  Git/Docker exclusion checks completed.
- gate_scope: Feature 008 acceptance.
- failure_class: none.
- evidence / limitations: `gh api repos/OWNER/REPO/releases/tags/TAG` and peeled Git tag
  refs resolved versions and full commits in [the pin ledger](research.md#implementation-pin-ledger--phase-1-2026-10-28).
  All six required Linux assets were streamed from official release URLs through
  `hashlib.sha256` and matched release asset digests; Syft/gh checksum files also matched.
  `git check-ignore -q --no-index PATH` excluded 13 synthetic host/secret/state/media paths
  and retained six nonsecret example/policy/fixture paths. A temporary build context with
  the actual `.dockerignore` and those 13 synthetic artifacts used `COPY . /ignore-check/`
  and a build-time assertion: only `retained.txt` and its Dockerfile were copied.
  Probe image ID `sha256:8f5bb8619bcec672043c836e5601312bf3f05a34bcdd5d91fc3dff9dbc3841e3`;
  the temporary context was deleted. `git diff --check` passed. No application/runtime
  behavior changed, so no new behavior tests were added. This probe does not pass native
  runtime, polling, source acquisition, upstream signature, public release or host gates.

Append subsequent actual records using all fields above; cite aggregate and individual
case IDs. Record baseline failures separately from candidate results and never claim a
build alone is live startup.

### Orchestrator baseline and Phase 1 review — 2026-10-28

- gate_id / requirement_ids: F008-SETUP; FR-003, FR-009, FR-019.
- class: Controlled. gate_scope: Feature 008 acceptance. failure_class: none.
- release / platform: baseline source `ba133f5`, feature branch `008-public-docker-deployment`; macOS arm64 host, Linux arm64 Docker Engine 29.9.2 / Compose 5.6.1.
- result: pass for parent Phase 1 review: checked T001–T003, representative Git secret exclusions/nonsecret retained paths, six checksum pins and seven full action SHAs; `git diff --check` passed. Agent executed actual Docker context exclusion checks and official asset hashes as recorded above.
- evidence / limitations: baseline `uv run --locked pytest`: 943 passed, 1 failed, 3 deselected; existing exited-leader cleanup test gets macOS `PermissionError` signaling the process group, reproduced independently before application edits. Linux arm64 baseline cleanup suite: 27 passed. Wider ephemeral Linux dev-container baseline: 940 passed, 4 failed, 3 deselected; four rotation fixtures use `-display_rotation`, unavailable in pinned FFmpeg 5.1.9. These are pre-feature platform/test issues, not source limitations or feature acceptance passes. Foundation/lifecycle phases will investigate them.
- baseline native build: `docker build --platform linux/arm64 --tag openmedia:008-baseline .` passed with retained pins; config ID `sha256:c593cdff6463dd5249f431098f2d4c86c2c674e08feed00320d079bcdf949072`, Python 3.13.15, Deno 2.9.6, FFmpeg 5.1.9 GPL enabled/nonfree absent. This baseline build is not final restricted smoke/public/server acceptance. Dev test dependencies were installed only in disposable container layers.
- infrastructure: canonical repository numeric ID `1380348601`; maintainer made repository public during this session. SSH acceptance target reports Ubuntu 26.04.1 amd64, Engine 29.1.3, Compose 2.40.3. Existing local-build polling service is healthy; no service change or token read occurred during inspection.

### Phase 2 foundation — controlled configuration and Compose (2026-10-28)

- gate_id / requirement_ids: F008-CONFIG, F008-COMPOSE; FR-005, FR-007–FR-011,
  FR-016, FR-018; SC-004.
- class: Controlled. gate_scope: Feature 008 acceptance. failure_class: none.
- release / platform: `008-public-docker-deployment`, Phase 2 working tree based on
  Phase 1 commit `b2e9e1f`; installed package version unchanged; macOS arm64 and
  disposable Linux arm64 test container. No published version/digest selected.
- environment: macOS 27.0.1 arm64; Docker Engine 29.9.2 Linux arm64 / Compose 5.6.1;
  controlled pytest fixtures prohibit external connections. Fake credentials only.
- result: pass for Phase 2 configuration/privacy/CLI and effective Compose checks.
- evidence / limitations: tests were added before the loader: the first targeted run
  produced **39 failed, 67 passed**, including file parsing, conflict detection, loaded
  credential logging and worker privacy failures. Additional surrogate-path and nested
  worker-key rejection cases were also observed failing before their fixes. Final
  `uv run --locked pytest tests/unit/test_config.py tests/unit/test_config_diagnostics.py
  tests/unit/test_diagnostics.py tests/integration/test_workers.py
  tests/integration/test_runtime.py tests/integration/test_diagnostic_trace.py
  tests/integration/test_merge.py -q`: **240 passed**, two existing PTB warnings, 3.02s.
  Parent independently ran its targeted subset: **193 passed**, two warnings, 2.87s.
  The final FIFO test adds an assertion of O_NONBLOCK before opening the real FIFO to
  prevent a regression hanging CI; config suite rerun: **57 passed**, 0.05s.
  Errors/tracebacks, repr, enabled diagnostics, console, actual inspect/download payloads,
  minimal environment and case-insensitive nested credential-key refusal are covered.
  Descriptor closure on success/fstat/read failure and the 4,097-byte total read budget
  are asserted; FIFO/device rejection never uses blocking opens.
- Compose evidence: rendered `docker compose --project-name openmedia --env-file
  TEMP_FIXTURE/deploy.env --file deploy/compose.yaml config --format json` with a fake
  canonical SHA256 image and default `/opt/openmedia/secrets/telegram_bot_token`. Parsed
  the rendered model and asserted fixed project/service, UID/GID, explicit allowed env,
  all resource/security/log restrictions, secret source and target, no build/ports/media
  volumes or unfiltered env_file. Extra fake `TELEGRAM_BOT_TOKEN` and unrelated keys in
  the interpolation file did not enter container environment. No token value rendered.
  Root local-build `compose.yaml` retained. Compose interpolation itself does not enforce
  digest grammar; the later operator/release validator must enforce that boundary.

### Phase 2 foundation — native Linux arm64 build and restricted smoke (2026-10-28)

- gate_id / requirement_ids: F008-NATIVE-ARM64 (foundation build/smoke subset),
  F008-REGRESSION (Linux controlled subset); FR-007, FR-018–FR-021; SC-004.
- class: Native container and Controlled. gate_scope: Feature 008 acceptance.
  failure_class: none for the executed checks.
- release / platform: Phase 2 working tree based on `b2e9e1f`; `openmedia:008-foundation`,
  native `linux/arm64`; development labels `version=008-foundation`, `revision=b2e9e1f`.
  Docker local index/image ID
  `sha256:f0556ed5396cc27752a5f8037268cf6fe11d9749ee742cf0834f221d4c47cb48`;
  platform manifest `sha256:eeeb05f0be561621fec31e4f13caa02d525454a54c2449811180c45200120f78`;
  OCI config `sha256:ed5f5f876da99a86542dcf8b04f52c51c7909c238fa6fdb10a3c7eb5afe2522a`.
  These are distinct local build identities, not published release identities.
- environment: macOS 27.0.1 arm64 with native Linux arm64 Docker Engine 29.9.2;
  Compose 5.6.1. Python 3.13.15, Deno 2.9.6 aarch64, FFmpeg/ffprobe 5.1.9-0+deb12u1;
  all Dockerfile base/tool/runtime pins retained.
- result: pass for actual native build, restricted offline smoke and full Linux suite.
- evidence / limitations: `docker build --platform linux/arm64 --tag
  openmedia:008-foundation --build-arg OPENMEDIA_VERSION=008-foundation --build-arg
  OPENMEDIA_REVISION=b2e9e1f .` passed; `scripts/smoke-container.sh
  openmedia:008-foundation` passed twice after fixture corrections. Every checked CLI
  and probe container uses network none, UID/GID 10001, init, read-only root, all caps
  dropped, no-new-privileges, 2 CPUs/2 GiB/512 MiB noexec/nosuid tmpfs, 30s stop timeout,
  unless-stopped restart and 10 MiB × 3 json-file logging. Docker inspect assertions
  confirm effective restrictions and read-only sanitized mounts. CLI checks valid fake
  file token (0), absent token (2), missing/unreadable/malformed file (2), and both keys
  with empty direct value (2), with safe fixed output. The probe checks installed EJS,
  executes bundled Deno, Python and media tools, compares original and merged encoded
  packet SHA256 lists for both streams, exercises writable bounded scratch, root/secret
  write denial, UID-10001 PermissionError on mode-000 fake secret and injected heartbeat
  freshness/staleness. It never polls, sleeps for readiness, or contacts Telegram/sources.
  Initial chmod-000 host-bind fixture was exposed as missing by Docker Desktop and was
  replaced by root-owned Linux-volume fixture; no permission-denial claim uses ENOENT.
  Script exit traps remove all its containers, fixture volume and temporary host files.
- Controlled regression: a separate disposable container copied only project/test files
  to `/tmp/project`, set `UV_NO_DEV=0 UV_OFFLINE=0 UV_CACHE_DIR=/tmp/uv-cache`, ran
  `uv sync --locked --group dev`, then `uv run --locked pytest -q`: **992 passed,
  3 deselected, 32 warnings in 9.73s**. Dev dependencies are absent from the published
  runtime layer. The initial disposable attempt inherited UV_NO_DEV=1 and could not
  spawn pytest; the corrected explicit dev setting produced the successful run above.
  The four rotation cases pass using pinned FFmpeg's metadata interface; the research
  record explains the fixture-only compatibility adjustment. macOS's pre-existing
  process-group cleanup defect remains assigned to the lifecycle phase; it is not a
  source limitation and the aggregate regression gate remains pending.
- Remaining gates: same-run native CI builds, archive export/import and config identity
  joins, final release images, public retrieval, and real health/polling/server/media
  acceptance remain required. This local build/smoke does not close those gates.

### Phase 2 foundation — parent native Linux amd64 build and restricted smoke (2026-10-28)

- gate_id / requirement_ids: F008-NATIVE-AMD64 (foundation build/smoke subset);
  FR-007, FR-018; SC-004.
- class: Native container. gate_scope: Feature 008 acceptance. failure_class: none.
- release / platform: same Phase 2 working tree; local image `openmedia:008-foundation`,
  native `linux/amd64`. OCI config
  `sha256:748d712b946a89f046b2cf131661a978d41963cd1194aa01505178ce3091af20`;
  platform manifest `sha256:723dbfba91510ed0c37f3c425059e13b2b84b190bfe74ec14cb6a015895c645f`;
  Docker local index/image ID
  `sha256:01a0c43050ad58b162a53cf9bf7ce0ca530c6cd7e36128b7b35dd8207b313066`.
- environment: Ubuntu 26.04.1 x86_64, Docker Engine 29.1.3, Compose 2.40.3; parent
  orchestrator executed through the SSH Docker context, with no running service changes.
- result: pass for actual native amd64 build and the finalized restricted offline smoke.
- evidence / limitations: parent ran `docker --host ssh://openmedia-server build
  --platform linux/amd64 --tag openmedia:008-foundation .`, then copied only the sanitized
  smoke script/probe into a disposable `/tmp` tree and ran
  `scripts/smoke-container.sh openmedia:008-foundation` on the native host. It reported
  the same effective restriction, permission denial, CLI, bundled tool, packet-copy and
  synthetic-health successes as arm64; temporary smoke resources were cleaned. Local
  transient logs: `/tmp/openmedia-008-amd64-foundation-build.log` and
  `/tmp/openmedia-008-amd64-foundation-smoke.log`. The existing polling service remained
  healthy and untouched. This is neither CI/promotion evidence nor final-release or
  real-polling acceptance. Both native architectures are available and tested for this
  foundation; later native CI and final exact release-image checks remain mandatory.

### Phase 3 US1 implementation checkpoint — controlled release boundaries (2026-10-29)

- gate_id / requirement_ids: F008-RELEASE-CONTROLLED, F008-REGRESSION (controlled subset);
  FR-001–FR-004, FR-018–FR-021; SC-001, SC-002, SC-008.
- class: Controlled. gate_scope: Feature 008 acceptance. failure_class: none for executed checks.
- release / platform: working tree based on `e3b27763208ee31d3e9d83a90aa0505a99bbeb75`,
  feature `008-public-docker-deployment`; no release tag, registry image or public acceptance.
- environment: macOS 27.0.1 arm64; locked Python 3.13.15 application/test environment.
- result: pass for the implemented controlled release interfaces. T013–T015 first failed
  with three expected missing-module collection errors before implementation. The final
  three release suites pass **104 tests**: identities, pure final assembly of an existing
  matching version, archive/config/child/index distinction, actual inner source/notice/
  recipe hashes, unsafe archives/link chains, stale inventory/source/SBOM joins, exact
  sdists, atomic interrupted/checksum/oversize acquisition, DSC source version/reference
  checks, unknown executable coverage outside /usr/local, complete certificate baseline
  and individual identity mutations, local-bundle auth independence, both real promotion
  command imports before either push, arm64 import mismatch, no rebuild, workflow privilege/
  action-pin rejection, and actual signing/image/public-evidence failure boundaries.
  Failures before publication produce zero image writes; later failures preserve sources
  and immutable artifacts and never claim acceptance. Certificate/signature command
  doubles are controlled boundary evidence, never a real own-release signature proof.
- evidence / limitations: `uv run --locked pytest -q tests/unit/test_release_manifest.py
  tests/integration/test_release_tools.py tests/contract/test_release_policy.py`: 104 passed.
  Full controlled suite before the last three isolated stage-boundary additions passed
  **1093, 3 deselected, 32 warnings in 6.36s**; those added cases subsequently pass in the
  104-test suite. `python3 -m py_compile scripts/release/*.py`, Ruby standard-library YAML
  parsing for both workflows, `publish.py audit-pins`, and `git diff --check` pass.
  The read-only CI workflow exports one-day native/controlled/source artifacts; only
  the separate protected-tag workflow grants publication permissions. Audits check the
  reviewed full action SHAs, exact tool checksums, all three runtime image digests,
  effective CI read-only declarations and forbidden privileged PR triggers.
- Superseding inherited baseline: the earlier macOS child-cleanup failure was caused by
  local Python 3.13.5. The parent synchronized the existing lock to the planned Python
  3.13.15, with unchanged dependencies, and observed the formerly failing child test pass,
  cleanup suite 27/27 pass, and original full baseline 992 pass/3 deselected/32 warnings.
  No lifecycle workaround or test weakening was needed. Parent logs include
  `/tmp/openmedia-008-python31315-full.log` and `/tmp/openmedia-008-phase3-full-tests.log`.
- Host verifier compatibility: parent independently executed the standalone verifier's
  parsing/hashing on actual isolated Python 3.11.18 without application dependencies;
  pass, log `/tmp/openmedia-008-verifier-python311.log`. Actual gh 2.103.3 local-bundle
  verification of its upstream original signed demo fixture also passed without auth;
  see the exact field/provenance record in research.md. OpenMedia's raw-index/image-subject
  signature and negative proof remains pending T062.

### Phase 3 actual native inventory/source acquisition — partial, not T034 completion

- gate_id / requirement_ids: F008-NATIVE-AMD64, F008-NATIVE-ARM64 (intermediate artifact
  audit subsets), F008-SOURCE-COVERAGE (partial acquisition); FR-004, FR-007, FR-018;
  SC-002, SC-004. class: Native container. gate_scope: Feature 008 acceptance.
  failure_class: none for the executed subsets; full source/native CI gates pending.
- release / platform: native working-tree audit images based on the above commit plus
  explicit cache-cleanup changes, with local version `v0.1.0-preview.audit`. Parent amd64
  config/Docker ID `sha256:31e11f42208d88e07452e693b91f6d8170977fa0892ddbe3685df9315eedfc15`.
  Native arm64 OCI config
  `sha256:b75f8c8b701425874897db31750c56a457015cc61e26b82bfb34250969016354`;
  Docker local image/manifest ID
  `sha256:907657c196c75266eaf2c5c92f9106ae76b678d7990feef0cde8abf7dfcaa6ee`.
  Even with build provenance disabled, these identities differ on this image store;
  the archive-derived config digest is authoritative for config joins.
  These intermediate images precede the subsequently added runtime notice COPY input;
  they are not final candidate images and do not substitute for the required CI rebuilds.
- environment: native amd64 Ubuntu 26.04.1 / Engine 29.1.3 / Compose 2.40.3 through
  authorized Docker access; native arm64 macOS Docker VM / Engine 29.9.2 / Compose 5.6.1.
  The parent kept the existing server polling project untouched. Python 3.13.15,
  uv/uvx 0.12.15, Deno 2.9.6, FFmpeg/ffprobe 5.1.9 retained.
- result: pass for actual cache-cleanup builds, both restricted offline smokes and whole-
  filesystem inventory audits. Actual inventories contain 317 arm64 / 321 amd64 components,
  including separate pip 26.2.1 and five unmanaged groups after exact base-helper naming.
  Both actual inventories resolve to reviewed source identities and exact unmanaged
  byte sets. The initial amd64 record's `unknown:/usr/sbin/policy-rc.d` was explicitly
  normalized only by its already recorded exact bytes; the latest collector names it
  directly. No path or unknown component is skipped. Native FFmpeg configuration has
  `--enable-gpl` and no `--enable-nonfree` on both architectures.
- evidence / limitations: actual parent source audit build/smoke logs are
  `/tmp/openmedia-008-amd64-source-audit-build-direct.log` and
  `/tmp/openmedia-008-amd64-source-audit-smoke.log`; actual full inventory/notices are in
  `/tmp/openmedia-008-inventory-amd64-final`. Local arm64 smoke/inventory logs are
  `/tmp/008-phase3-smoke.log`, `/tmp/008-runtime-arm64-final`; no polling or external source
  media request occurred. The Docker source-context audit excluded ten synthetic private/
  staging paths while retaining only the explicit notice exception; parent log
  `/tmp/openmedia-008-context-audit.log`.
- The pinned native arm64 build-only collector assembled successfully. A real APT-
  authenticated bzip2 source acquisition and standard dpkg-source unpackability check
  passed for source `1.0.8-5`, independent of binary `1.0.8-5+b1`. Receipt/materials are
  at `/tmp/008-debian-bzip2-source`. It retains `.dsc`, original and Debian archives,
  authenticated source stanza/index signatures, checksums, acquisition URLs and collector
  dpkg inventory. Direct tools: apt 2.6.1, dpkg/dpkg-dev 1.21.23, gpgv
  2.2.40-1.1+deb12u2, debian-archive-keyring 2023.3+deb12u2, tar
  1.34+dfsg-1.2+deb12u1, xz-utils 5.4.1-1+deb12u2, bzip2 1.0.8-5+b1,
  patch 2.7.6-7. Sources are never built/executed during validation.
- The reviewed source policy has 1,879 exact component entries, including a complete
  locked Rust source superset, explicit CPython/ICU/TypeScript/standard-library and pip
  vendoring edges. All 1,553 distinct crate archives were actually downloaded and matched
  their Cargo.lock hashes. The runtime notice bundle contains 18,175 deduplicated original
  notice/attribution entries; deterministic gzip SHA256
  `6db348e47b894d5d93618c453aefe021c3e20d94b1e49b2384cb4720829587fb`.
  It supplements installed Debian/Python notices; its presence/hash is a native inventory
  gate and its full provenance is tracked. Authors/template placeholders are never treated
  as original copyright notices; explicit MIT-only absence findings remain in notice-review.
- **Pending**: T034 must execute the committed candidate's actual native CI/archive jobs
  and entire source/notice collection after the runtime notice input change. The policy,
  one real Debian source, or the preceding intermediate images do not close that gate.
  Any unavailable exact source/notice remains blocking. Own signed bundles, anonymous
  registry/material/evidence access, immutable tag/settings bootstrap and public acceptance
  remain T060–T062; no tag, release or image was published during this phase.

### Phase 3 orchestrator code review before committed CI

- gate_id / requirement_ids: F008-RELEASE-POLICY, F008-REGRESSION (controlled subsets); FR-001–FR-004, FR-018, FR-020–FR-021; SC-002, SC-008.
- class: Controlled. gate_scope: Feature 008 acceptance. failure_class: none.
- release / platform: Phase 3 working tree on `008-public-docker-deployment`; macOS arm64, Python 3.13.15. No published candidate.
- result: pass — parent full run before final subject-name assertion: 1096 passed, 3 deselected, 32 warnings in 6.46s. After that narrow hardening, parent independently reran all 105 release cases successfully; frozen-tree agent full run passed 1097, 3 deselected, 32 warnings in 6.42s. `uv build` passed, with the existing nonfatal uv/backend-range warning; no dependency or lock changes.
- evidence / limitations: parent verified both workflow YAML files with Ruby, `audit-pins`, shell examples, diff whitespace, notice compressed/uncompressed hashes against provenance, and actual Docker build-context exclusion of ten synthetic private/staging paths while retaining only the notice exception. Standalone verifier parsing/hashing passed on Python 3.11.18. Logs: `/tmp/openmedia-008-phase3-final-full.log`, `/tmp/008-phase3-final-full.log`, `/tmp/openmedia-008-phase3-build.log`, `/tmp/openmedia-008-context-audit.log`. T034 remains unchecked until the committed candidate executes both native CI/archive jobs and complete source collection. Intermediate native image checks do not close that gate.
- authorized acceptance boundary: maintainer confirmed use of available Docker access and explicitly left root-only installation/ownership/reboot acceptance pending. An authorized test chat is held privately for later delivery checks; no ID or credential is included in tracked/public evidence. Existing server service remains healthy and unchanged.

### US1 T034 committed CI validation — 2026-10-30–31

- gate_id / requirement_ids: F008-REGRESSION, F008-NATIVE-AMD64,
  F008-NATIVE-ARM64, F008-SOURCE-COVERAGE; FR-002, FR-004, FR-007, FR-018;
  SC-002, SC-004. class: Controlled and native container/source acquisition.
  gate_scope: Feature 008 acceptance. No polling, publication or host operations.
- Original candidate `cbc74cc9ca3399fb3f709bf3f5fe21768c6686d1`:
  [push run 40851016043](https://github.com/hman-pro/openmedia/actions/runs/40851016043)
  passed both native jobs but failed controlled tests (1 failed, 1096 passed,
  3 deselected). Root bypassed chmod in the diagnostic outage test. Commit
  `07885b4111b0819a41707172d4302f8104e90cf8` injects `PermissionError` at the
  filesystem boundary, retaining outage/retry/recovery assertions; local diagnostics:
  33 passed. No application change was required.
- [PR run 41102961896](https://github.com/hman-pro/openmedia/actions/runs/41102961896)
  passed controlled and both native jobs, then failed source policy resolution:
  `libslang2` incorporated `unicode-data=15.0.0-1` without a reviewed source entry.
  This is a deployment tooling defect, not a source-network limitation or waived gate.
  The PR artifact identifies merge revision `e80b9e7f4235059947e064b910192fbcf8321ffa`;
  it is not evidence for the subsequent corrected candidate.
- Commit `46a6fe3d5e891f606144e06d7f1767ce624219ea` adds the exact Debian source
  entry and retains original notices from authenticated incorporated source archives.
  Controlled policy-edge and notice-retention regression checks added; release-tool
  suites: 107 passed. [Candidate push run 41104236736](https://github.com/hman-pro/openmedia/actions/runs/41104236736)
  passed controlled and both native jobs, then failed recording the first Debian source
  receipt: APT selected an equivalent HTTP binary mirror from the base configuration,
  so the required HTTPS acquisition URL was absent. Reproduced with real `adduser=3.134`
  acquisition in the native arm64 collector. Source operations now use only the explicit
  signed HTTPS source configuration (`Dir::Etc::sourcelist`/`sourceparts`). The same real
  acquisition passes and records both HTTPS material URLs; local evidence:
  `/tmp/openmedia-008-t034/apt-https-repro/receipt.json`. Injected receipt regression plus
  release-tool suites: 108 passed. The next committed CI rerun must still complete all
  materials, notices, packaging and validation. T034 remains unchecked.
- Candidate `d4d7d4b7a64f42278724c00268b8d32f26a037b8`,
  [push run 41105041723](https://github.com/hman-pro/openmedia/actions/runs/41105041723):
  controlled and both native jobs passed; source collection reached `dpkg=1.21.23`
  and rejected its three original FIFO test fixtures as unsupported types. Actual
  signed-APT acquisition and isolated network-free dpkg-source unpacking pass after
  allowing zero-length FIFO metadata without host extraction. Devices, FIFO data and
  descendant traversal remain rejected; release-tool suites: 112 passed. This is a
  corrected validator compatibility issue, not a waived archive/source gate.
- Candidate `a076cca9b83b77b30f1c08dcd0414e6a0eee463a`,
  [push run 41106267477](https://github.com/hman-pro/openmedia/actions/runs/41106267477):
  controlled and both native jobs passed; source collection rejected the NORM source's
  archive-root symlink. Local source acquisition reproduced this and its equivalent
  repeated directory header, then reached systemd's literal hex-escape filenames.
  Corrections preserve original archive bytes and retain traversal/device/conflicting
  member rejection. Controlled release-tool suites: 117 passed. The local acquisition
  diagnostic uses earlier inventories/notices and is not candidate acceptance evidence.
- The resumed local diagnostic now uses matching inventories/notices downloaded from
  run 41105041723, and individually rehashes cached upstream materials before reuse.
  It passed acquisition/notices for every component and reached source packaging.
  It also exposed libmpdec's incorrect notice pattern, corrected to the original source
  headers in the exact CPython archive. This working-tree diagnostic is not evidence
  for a later committed candidate; a complete fresh CI run remains required.
- Candidate `e6677271921c3f7301c3994c5a81166fff87739b`,
  [push run 41117313115](https://github.com/hman-pro/openmedia/actions/runs/41117313115):
  1109 controlled tests passed (3 live tests deselected, 32 existing warnings); both
  native jobs passed. CI source collection failed on the first Python package notice:
  artifact upload omitted hidden `notices/app/.venv/` files. The local diagnostic had
  retained those files from its earlier inputs, explaining its full 1899-component
  pass; it never substituted for committed CI acceptance. Native output upload now
  explicitly preserves hidden files, with inventory notice validation before network
  acquisition. This fix requires a fresh complete CI run; no missing notice is waived.

### US1 T034 candidate evidence — 2026-10-31

- gate_id / requirement_ids: F008-REGRESSION, F008-NATIVE-AMD64,
  F008-NATIVE-ARM64, F008-SOURCE-COVERAGE; FR-002, FR-004, FR-007, FR-018;
  SC-002, SC-004. class: Controlled, native container and source acquisition.
  gate_scope: Feature 008 acceptance. failure_class: none for completed checks.
- Candidate: `52f4dc8cecf23e781df827a2305cf15f4a5030ce`, image label
  `development`, installed package 0.1.0; [push run 41229989620, attempt 1](https://github.com/hman-pro/openmedia/actions/runs/41229989620).
  **Result: pass.** All four jobs completed successfully: controlled, native amd64,
  native arm64 and sources. The controlled suite reports **1110 passed, 3 live tests
  deselected, 32 existing warnings**. Source collection, bundle validation and material
  upload passed. T034 is complete; US1 has no remaining implementation tasks.
- Environment: native GitHub-hosted Ubuntu 24.04 runners; amd64 image revision
  `20261026.354.1`, arm64 `20261026.166.1`. Both report Engine 28.0.4, Compose
  2.38.2, checksum-pinned Buildx 0.38.1 and Syft 1.55.0. Runtime tools remain
  Python 3.13.15, uv/uvx 0.12.15, Deno 2.9.6 (V8 15.0.245.2, TypeScript 6.0.3),
  FFmpeg/ffprobe 5.1.9-0+deb12u1. No runtime pins changed.

| Identity | linux/amd64 | linux/arm64 |
|---|---|---|
| Checked config/Docker ID | `sha256:e2f606d92ed0dd7bd319173af6d2743e3a702fc0070330f9805804c1c52c68de` | `sha256:79fc13659c36d37bdc7280b73f326eed7405df4ae3670278221aa3758ec7fbf3` |
| Docker archive SHA256 | `3b0a503ceee24ed64020033c968bcee24e606103c85f59a1995a81a7aa42cd0f` | `299ce46b89740713e260d6d87d0d3d34ac3e768d435c0f7bcc1148feeb06aef0` |
| Inventory SHA256 | `641650044fb4f209a809c3a3defa4ac4292d5693f72d214ce45dbeb5da5b36a1` | `7b11bd0ea4088da11137dc30f6ea8835b77cf1cf308e1834a3ade62c386887dc` |
| SPDX SBOM SHA256 | `19076db08866f8db513abc773e7938fb909d033bb9fce93b48f1f145e8ca1984` | `9b653c4e254477cf700ebb8fe09dc5af17998d4bd4a6f6e79f6297f075bec774` |
| Actual image components | 321 | 317 |

- Both native reports pass effective production restrictions and offline smoke:
  tools/EJS, local native packets/stream copy, bounded storage, permissions, synthetic
  health and negative secret cases. These tests use fake secrets and no real polling.
- Independently downloaded `native-amd64`/`native-arm64` artifacts to
  `/tmp/openmedia-008-t034/52f4dc8/`; rehashed both archives, parsed their archived
  configs and matched the native records. Validated every declared installed notice,
  including hidden `.venv` paths, after transfer. Archive, config, SBOM and inventory
  identities remain distinct; no registry child/index digest is invented.
- Complete source result: **1899 components**, all `coverage=complete`, with both
  final native inventories/config identities joined to this exact commit. Source job
  duration 19m 4s; total workflow 20m 20s. Both source/notice bundle validation and
  the explicit `validate_release.py sources --directory materials` check passed.
  The run retains five artifacts: controlled, both native archives, source diagnostics
  and matching sources (1.87 GB). CI artifact retention is one day; this is validation
  evidence, not the durable public source distribution required before image push.
- Downloaded `source-diagnostics` to
  `/tmp/openmedia-008-t034/52f4dc8-source-diagnostics/`, validated its manifest schema,
  complete component coverage and exact equality with both downloaded image inventories.
  Manifest SHA256: `cd908355a1ad29290c137dddb1d8e357f16c636fb59a98002c6ab964b04cf7a2`.
  Passing progress record: `stage=source-bundle-validation`, `coverage=complete`,
  `result=pass`, `components=1899`. Controlled log:
  `/tmp/openmedia-008-t034/52f4dc8-controlled.log`.

| CI source material | Bytes | SHA256 |
|---|---|---|
| `sources-001.tar.gz` | 1064431804 | `2f4df42155a8de696774cc13aa2cc70d2027e33dde07dd1ca0eec8381d07c547` |
| `sources-002.tar.gz` | 918726676 | `199af34c91677f6577c759a026f527b9263dad3df3188bd598c6e61f190c4c0a` |
| `notices.tar.gz` | 16245613 | `b499f8bf2f2bd2b04ed3fd9872d1375ddcea0f05ae8fac605af321bce01f5d1a` |

- Public source availability, source/version tag authority, signed provenance and
  anonymous image/evidence retrieval remain T060–T062. Final integrated candidate
  checks after the later stories remain T059. This record does not claim a release,
  real-host installation, polling or media-delivery acceptance. No source tag, version
  tag, registry image or release was published. Later artifact-input changes invalidate
  affected checks; release publication must rerun against its own exact candidate.


## Phase 4 — secure installation implementation checkpoint (2026-10-31)

- gate_id / requirement_ids: F008-CONFIG, F008-REGRESSION,
  F008-NATIVE-ARM64; FR-005–FR-010, FR-018, FR-021; SC-003–SC-004.
  class: Controlled and native container. gate_scope: Feature 008 acceptance.
  result: **pass for this implementation checkpoint (T036–T042)**.
  failure_class: none. This does **not** pass F008-INSTALL or T063.
- Source: Phase 4 working tree based on
  `7a9c1bb03261b168271df71d9f2f23a2264d9620`, subsequently committed at the
  Phase 4 boundary. Changes are CLI integration tests, the nonsecret settings
  example, installation guidance and evidence. No application, Dockerfile, Compose
  or dependency changes were needed. Exact runtime pins remain unchanged.
- Pre-implementation artifact review: prerequisites resolved the existing feature;
  requirements checklist 16/16 checked, unchanged. Read-only spec/plan/tasks review
  found no blocking inconsistency, constitutional issue or unmapped task. The task
  coverage register maps all 21 FR and 8 SC identifiers (29/29) to the 67 tasks.
  Phase 4 remains sequential T036–T042; actual installation acceptance is T063.
  `.specify/extensions.yml` is absent; no analysis/implementation hooks are registered.

### Controlled CLI and local development evidence

Command:

```sh
uv run --locked pytest tests/unit/test_config.py tests/integration/test_runtime.py tests/integration/test_workers.py tests/unit/test_diagnostics.py tests/integration/test_diagnostic_trace.py -q
```

**234 passed**, 2 existing PTB deprecation warnings. Runtime suite alone:
**75 passed**. New CLI cases use actual injected environment parsing, fake file secrets,
injected permission failures and clocks, and fixture application startup with no network.
They cover local check-config 0/2; healthcheck 0/1/2; missing, malformed, conflicting and
unreadable secrets before logging/polling; intact foreign workspaces; no preflight
heartbeat; no healthcheck diagnostic storage; direct-input compatibility; and file-loaded
token redaction with diagnostics off/on. Existing unit tests retain suppressed formatted
exception-chain coverage and exact loader boundaries. Tests were added before deciding
whether runtime changes were needed: first execution exposed test-fixture errors (log
extension and a diagnostic directory nested inside scratch); correcting those fixtures
made the existing runtime pass. No runtime defect or failing behavior was concealed.

Unchanged root `compose.yaml` was copied into an isolated fixture directory and rendered
with a fake direct-token `.env`: only the direct token source is mapped. The current
native image passed `python -m openmedia --check-config` with that direct input under
`--network none`, read-only root, dropped capabilities and private bounded tmpfs.
An isolated copy of `scripts/dev.sh --check-config` also passed both its preflight and
final CLI invocation using an exported fake direct token and a nonsecret `.env`.
Only uv dependency synchronization/dispatch was stubbed; the actual installed Python
CLI and bundled local tool checks ran. No keyring credential or user `.env` was read,
no poller started, and neither output exposed the fake token. `bash -n scripts/dev.sh`
passed. The local-build example remains unchanged; the guide explains removing both
token keys from dev.sh's nonsecret `.env` for its keyring/direct-token workflow.

### Native and effective Compose evidence

Environment: macOS host with Docker Desktop native Linux/aarch64 VM, Engine **29.9.2**,
Compose **5.6.1**. This is native arm64 container evidence, not Ubuntu host acceptance.

```sh
docker build --tag openmedia:008-phase4 .
bash scripts/smoke-container.sh openmedia:008-phase4
```

Both **passed**. Local Docker image-store identity:
`sha256:3a99b2ed0257267c840f297647b4967ea1b224d03aab7c12d72b52dbcd76a75e`;
build config identity:
`sha256:085754a5df6cb7fba326286deb906c509866d703c3b00524dc38f3592d43ad71`;
local child manifest:
`sha256:0b702bd0c00a6cc0725c832fb88ed5f49e35932958ccedfe0ec1cc1293860d4a`.
These are local build identities, **not a published GHCR production digest**.
Python 3.13.15, Deno 2.9.6 and FFmpeg/ffprobe 5.1.9-0+deb12u1 passed; bundled EJS,
stream-copy/native packets, effective identity/restrictions, writable bounded storage,
negative secret access, all fake-token CLI error cases and synthetic health passed.
The smoke starts no real poller and uses `--network none`.

Additional actual Compose checks rendered `deploy/compose.yaml` with the new example,
a synthetic 64-hex digest and a fake secret path. Effective settings contain only the
file path, no token value/direct-token key/service env_file or shared work volume.
An isolated local-only copy of that effective config selected `openmedia:008-phase4`
and `network_mode: none`; its real `run --rm --no-deps -T --pull never openmedia
python -m openmedia --check-config` passed as UID/GID 10001. Two separate one-offs
confirmed a marker created in the first tmpfs is absent in the second. No production
project was touched. Temporary containers/network/files were removed.
Separately, a Linux-volume fake secret created as **root:10001 mode 0640** was read
successfully by UID/GID 10001 with a read-only mount, no network/capabilities and the
read-only root. The temporary volume was removed. Host directory traversal/ownership
on real Ubuntu remains T063; Docker Desktop sharing is not substituted for it.
Diagnostic defaults remain off; no writable diagnostic volume was added.

### Guide consistency and failure-path review

The guide now provides signed official Docker Ubuntu APT setup, supported-host checks,
installed tool version/flag recording, protected absolute files, group membership review,
exact digest-shape checks after independent signature verification, clean command-scoped
overrides, isolated preflight, stop-before-start ownership review and first activation.
The startup block refuses an already running project service. A failed 180-second health
wait or signal explicitly stops the candidate; terminal-loss cleanup is adjacent.
All discovery operations propagate errors before permitting activation.

`bash -n` passed for **11** operator-guide and **15** quickstart shell blocks. A disposable
command-boundary harness executed the actual guide wrapper/preflight/startup blocks:
success, failed pull, failed preflight, failed container discovery, failed startup,
SIGTERM during startup and malformed image selection all produced expected outcomes.
Failures before startup executed no `up`; startup failure/SIGTERM executed stop cleanup.
This is controlled shell evidence, not an actual unhealthy/restarted Telegram service.
Temporary harnesses/checks were in `/tmp/openmedia-008-phase4/`, outside release assets.
`git diff --check` passed. Existing ignore files already exclude host secrets/state,
Python artifacts and editor files while retaining the new nonsecret example; no change
was necessary. Quickstart section 5 now follows the exact executable installation guide;
section 6 is explicitly later-phase work.

Official documentation consulted 2026-10-31:
[Ubuntu signed APT installation](https://docs.docker.com/engine/install/ubuntu/),
[Compose run flags](https://docs.docker.com/reference/cli/docker/compose/run/),
[Compose up/wait flags](https://docs.docker.com/reference/cli/docker/compose/up/).

### Supported-host and external acceptance matrix

| Target host | Architecture | Clean-host Docker/permissions/preflight | Real token polling/health/delivery (T063) |
|---|---|---|---|
| Ubuntu 24.04 LTS | amd64 | pending | pending |
| Ubuntu 24.04 LTS | arm64 | pending | pending |
| Ubuntu 26.04 LTS | amd64 | pass (2026-11-23, T063 record) | pass (2026-11-23, T063 record) |
| Ubuntu 26.04 LTS | arm64 | pending | pending |

Each row has gate_id F008-INSTALL; requirement_ids FR-005–FR-010, FR-018–FR-019,
SC-003–SC-004; class deployment-network/manual; gate_scope Feature 008 acceptance;
failure_class none; release/environment not yet selected. Required next action: execute
the guide on the operator's actual combination with T062's exact verified public digest,
protected real credential, installed version/capability evidence, successful polling,
fresh health and representative native Telegram delivery. Other combinations remain
pending. No public image was published or real credential used during Phase 4.

T040's local arm64 evidence does not rerun native amd64: the earlier T034 record retains
both native architectures at its exact candidate. Final integrated candidate gates T059
must rerun both after all story work. T062/T063 remain pending, as do Phase 5–7 tasks
and inherited acceptance gates. This is the code-ready US2 checkpoint only.

## Phase 5 — deliberate update and recovery implementation checkpoint (2026-10-31)

- gate_id / requirement_ids: F008-REGRESSION (targeted lifecycle/configuration subset),
  F008-UPDATE and F008-SHUTDOWN (controlled substitutes only); FR-011–FR-015,
  FR-018–FR-019, FR-021; SC-003, SC-005–SC-006.
- class: Controlled. gate_scope: Feature 008 acceptance.
  result: **pass for implementation tasks T043–T050**; the aggregate real-host
  F008-UPDATE/F008-SHUTDOWN gates and T064 remain **pending**.
  failure_class: none.
- release / platform: Phase 5 working tree based on
  `e643411` (Phase 4), committed at this phase boundary; macOS arm64,
  Python 3.13.15. No runtime, dependency, Dockerfile or Compose-definition change.
  No public version/index selected, image rebuilt, production project touched,
  real credential used, or real poller started.
- environment: Existing locked uv development environment; Bash shell syntax and
  command-boundary checks with disposable state under `/tmp/openmedia-008-phase5/`.
  Actual Docker Compose 5.6.1 rendered a sanitized old-project recovery override;
  a stopped identity fixture was also created/inspected/removed; no service started. No external source/Telegram network used in tests.
- Prerequisites: existing feature branch reused; requirements checklist 16/16 checked,
  unchanged. Git/Docker ignores retain all critical Python/secret/state exclusions;
  no new ignore entry necessary. `.specify/extensions.yml` absent at pre/post checks;
  no implementation hooks registered.

### Lifecycle and file-token regressions (T043, T049)

```sh
uv run --locked pytest tests/integration/test_runtime.py tests/integration/test_failure_cleanup.py tests/integration/test_workers.py tests/unit/test_config.py tests/unit/test_diagnostics.py tests/integration/test_diagnostic_trace.py -q
```

**263 passed**, 2 existing PTB deprecation warnings, **16.48 seconds** total suite
runtime. This total is controlled test execution time, not measured real-host downtime.
The real child-group shutdown case now runs with both direct and file-loaded settings
through `build_application`: actual leader/descendant reaping, closed admission, owned
work cancellation, scratch/heartbeat cleanup and maintenance completion remain inside
the test's 20-second bound. The music shutdown case now uses the built runtime with a
fake file credential, for both active download and upload. Actual `deliver_media` opens
the file; injected Telegram transport stalls on an event. Runtime shutdown cancels it,
closes the file, releases capacity, rejects late admission and stale selection replay,
records uncertain delivery, and never issues a second upload. No external connections
or new sleep-based readiness checks were added. The deployment grace remains 30 seconds.

Tests were extended before deciding whether runtime changes were needed. The first run
reported two test-fixture errors (wrong registry attribute and missing `self` on the
injected bot method); both were corrected. Failure-cleanup alone then passed **28 tests**,
followed by the integrated 263-test pass above. Existing runtime behavior satisfied the
new assertions; no application implementation fix was justified. Controlled shutdown
bounds do not establish real SIGTERM, Docker stop timing, or real Telegram cancellation.

### Runbook commands, persistence, and failure exits (T044–T049)

`deploy/README.md` provides a nonsecret operator record, digest-scoped commands in a
clean environment, shared explicit stop/health/persistence helpers, complete update and
rollback sequences, old-project discovery/config preservation/local-image pinning,
migration and the return path. Quickstart section 6 references these exact procedures
with expected states for each acceptance scenario. Credentials/settings are current
through rollback; only the image selection is atomically replaced after health.

`bash -n` passed for **20 guide shell blocks** and **7 quickstart shell blocks**.
A disposable harness (`python3 /tmp/openmedia-008-phase5/check_runbook.py`) extracted
and executed actual guide blocks with injected sudo/Docker/verifier boundaries and
stateful synthetic container identities. **31 scenarios passed**:

- Update: healthy; failed verify, pull, preflight, discovery, stop and unconfirmed stop;
  failed startup, unhealthy candidate, SIGTERM during startup, and persistence error.
- Rollback: healthy; locally missing plus unavailable remote image; incompatible
  preflight; failed startup; SIGTERM; persistence error.
- Migration: healthy; failed verify/pull/preflight/old stop; failed new startup;
  SIGTERM; persistence error. Old poller is stopped before new activation.
- Old-project return: healthy; missing preserved image; failed preflight/startup;
  SIGTERM. Candidate is stopped before recovery and failed old startup is cleaned up.
- Discovery/preservation: actual old identity retained and pinned; protected config-copy
  and override commands dispatched before migration.

Assertions checked nonzero failure exits, no `up` after failed prerequisites, candidate
stop after startup/health/signal failure, no overlapping old/new pollers, unchanged
selection on persistence failure, and healthy selected identity on success. Shell
signal handling was actually exercised; unhealthy/timeout return statuses were injected,
not an actual 180-second host health wait. Syntax checks alone are not these assertions.

The actual embedded persistence Python was separately executed on a disposable nonsecret
env file: only the image line changed, other settings/comment stayed intact, mode was
0600, and missing/duplicate image lines failed without altering the original file.
The production root ownership syscall alone was omitted in this nonroot fixture;
root:root enforcement and real host filesystem failure handling remain manual evidence.
Atomic replacement uses a same-directory temporary file and `os.replace`, after flushing
and fsync of file contents. No credential is read or hashed by this helper.

Actual `docker compose ... --file <root-fixture> --file <recovery-override> config --images`
selected exactly the synthetic preserved local recovery tag. Root Compose and all runtime
restrictions remain unchanged; recovery explicitly uses `--no-build --pull never`.
A separate stopped `--network none --entrypoint /bin/true` fixture from the existing
`openmedia:008-phase4` image confirmed container `.Image` equals the local image-store
identity `sha256:3a99b2ed0257267c840f297647b4967ea1b224d03aab7c12d72b52dbcd76a75e`;
`.Config.Image` retained the tag and `.State.Running` was false. The fixture was removed
without being started. This identity is not a published GHCR digest or necessarily the
OCI config object's hash. These checks do not prove local image availability on a server.
`git diff --check` passed.

Official references checked 2026-10-31:
[Compose up and bounded wait](https://docs.docker.com/reference/cli/docker/compose/up/),
[one-off nonpolling run](https://docs.docker.com/reference/cli/docker/compose/run/),
[ordered Compose image overrides](https://docs.docker.com/compose/how-tos/multiple-compose-files/merge/).

### Transition review and remaining real-host cases (T050 / T064)

Reviewed against `contracts/operations.md` and `data-model.md`:

| Contract transition | Concrete implemented mapping and controlled evidence | T064 still required |
|---|---|---|
| running(previous) → downloaded → validated | Complete update block verifies then pulls/config-checks/nonpolling preflights before stop; injected failures leave old bot and env intact | Real failed pull/file-token preflight with old poller uninterrupted |
| validated → previous_recorded → previous_stopped | Inspect actual `.Config.Image`, `.Image`, container ID and UTC; reject local-only reference; stop helper and original-container check must succeed | Real identity/stop timing, active-work cancellation, child/scratch/upload cleanup |
| previous_stopped → candidate_starting → candidate_healthy | `start_checked` refuses a running service; no-build/no-pull recreate/wait 180; inspect running/health/reference | Actual healthy and never-healthy candidates, deadline/downtime measurement, single polling ownership |
| candidate_healthy → selection_persisted | Atomic image-only env replacement, then effective env selection/running health agreement; error exits before success message | Root ownership/mode, actual host persistence failure and correction |
| startup failure/timeout/interruption → candidate_stopped → rollback_available | EXIT/INT/TERM cleanup stops/confirms; adjacent terminal-loss cleanup; unconfirmed absence blocks recovery | Actual startup/timeout/interruption and cleanup, including terminal loss |
| rollback_available → previous_validated → starting → healthy | Explicit previous record digest; candidate stop first; retained local image or pull; current settings/token validation; same checked startup and post-health persistence | Compatible recovery, unavailable/incompatible previous image, failed/interrupted rollback and real delivery |
| rollback failure → stopped, explicit recovery error | Preflight aborts before up; failed health/signal stops attempted previous service; persistence failure stays incomplete | Real failed recovery and operator correction; no revived token/settings |
| migration / return | Actual old project/files protected, local content ID pinned; new nonpolling preflight; old stop/confirm; new checked startup. Return stops new first and validates/starts pinned local old content with cleanup | Actual root-Compose migration/return, retained image availability, current credential compatibility, no overlap |

All real-host rows remain **pending** for the selected Ubuntu 24.04/26.04 LTS and
amd64/arm64 acceptance combination. Record observed UTC/timing/outcomes and exact verified
public source/index identity in T064; other host combinations stay pending. Do not count
this checkpoint as passing T062 publication, T063 installation, T064 update/shutdown,
or later maintenance/media acceptance. Final integrated/native checks and inherited
stable-readiness obligations remain required. No new support or stable-release claim.

## Phase 6 maintenance and media case register (T056)

These are required future execution cases, **not executed acceptance results**. Follow
the [maintenance runbook](../../deploy/README.md#maintenance) and
[quickstart walkthrough](quickstart.md#7-maintenance-walkthrough-t065).
Every row started `pending`; T065 results are in the
[T065 record](#t065-maintenance-acceptance--2026-11-2627). Release/platform and environment are `not yet selected/recorded`;
failure_class is `none` until an observed outcome is assessed. Each execution must append
the full record format above: exact version/source/index/container/image identities,
OS/architecture, Engine/Compose, UTC and observed timing, nonsecret network context,
result/reason, evidence, limitations and next action. Record each tested host combination
separately; no result here expands the supported-host evidence matrix.

| Case | Gate / requirements | Required observation | Result |
|---|---|---|---|
| OP-INSPECT | F008-OPERATIONS; FR-016–FR-017, FR-019; SC-003 | Selected health/restart/time fields, bounded console logs and one-shot resource stats; no token/link/Telegram ID disclosure, no poller from inspection, memory includes tmpfs | pass (Ubuntu 26.04 amd64, T065 2026-11-26/27) |
| OP-DIAGNOSTICS-OFF | F008-OPERATIONS; FR-017, FR-021; SC-003 | Default-off mode creates no diagnostic files, including local validation | pass (Ubuntu 26.04 amd64, T065 2026-11-26/27) |
| OP-DIAGNOSTICS-ON | F008-OPERATIONS; FR-017, FR-021; SC-003 | Explicit protected writable mount, UID 10001 access, directory 0700/files 0600, private real trace/refusal, no console disclosure, 14 UTC-day files/50MB retention, persistence across recreation; healthcheck writes no logs | pass (Ubuntu 26.04 amd64, T065 2026-11-26/27) |
| OP-ROTATE | F008-OPERATIONS; FR-008–FR-010, FR-015, FR-017; SC-003–SC-004 | Protected replacement, confirmed stop, atomic rename, local validation, forced mount recreation, real replacement authentication/health and one poller; transient/editor copies cleaned under host policy | pass (Ubuntu 26.04 amd64, T065 2026-11-26/27) |
| OP-ROTATE-FAIL | F008-OPERATIONS; FR-009, FR-015, FR-017; SC-003–SC-004 | Local invalid input and remotely rejected credential leave attempts stopped; corrected current input recovers; no revoked-token restoration or restart-only mount renewal | pass (Ubuntu 26.04 amd64, T065 2026-11-26/27) |
| OP-EXIT | F008-OPERATIONS; FR-016, FR-019; SC-007 | In-container unexpected exit after restart-monitoring threshold, automatic same-container recovery/increased restart count without up/start, health <=180s and delivery; no second poller | pass (Ubuntu 26.04 amd64, T065 2026-11-26/27) |
| OP-REBOOT | F008-OPERATIONS; FR-016, FR-019; SC-007 | Running selected digest automatically recovers after isolated-host reboot, healthy <=180s after Engine availability, real delivery and one poller; record boot IDs/timing | pass (Ubuntu 26.04 amd64, T065 2026-11-26/27) |
| OP-STOP | F008-OPERATIONS; FR-016, FR-019; SC-007 | Intentional stop persists across reboot; retained stopped container/no polling observed >=180s after Engine availability, followed by explicit healthy restart | pass (Ubuntu 26.04 amd64, T065 2026-11-26/27) |
| OP-OUTAGE | F008-OPERATIONS; FR-016, FR-019; SC-007 | Isolated network loss exceeds freshness/retry windows; unhealthy with unchanged container/StartedAt/restart count, reconnect recovers healthy polling <=180s and delivery; no restart agent/additional poller | pass (Ubuntu 26.04 amd64, T065 2026-11-26/27) |
| OP-BACKUP | F008-OPERATIONS; FR-017, FR-019; SC-003 | Operator verifies encrypted storage/access controls; consistent config/current credential/verified selection record, protected recoverability, no media/request/diagnostic backup | pass (Ubuntu 26.04 amd64, T065 2026-11-26/27) |
| OP-REMOVE | F008-OPERATIONS; FR-017, FR-019; SC-003 | Only fixed project removed; explicit retained config/secret/diagnostic/migration/record/backup/image inventory and retention decisions; unrelated services unchanged | pass (Ubuntu 26.04 amd64, T065 2026-11-26/27) |
| OP-RESTORE | F008-OPERATIONS; FR-015, FR-017, FR-019; SC-003 | Other pollers stopped; reviewed config, current credential and ownership/modes, verified digest and isolated preflight, real health/delivery; no request resumption | pass (Ubuntu 26.04 amd64, T065 2026-11-26/27) |

All OP cases have gate_scope **Feature 008 acceptance**, class
**Deployment-network/manual**, and belong to T065. F008-SHUTDOWN/T064 remains a separate
real active-work <=20-second exit/child/upload/scratch/no-duplicate acceptance gate; a
forced exit or successful maintenance restart does not pass it.

T066 retains **every inherited gate** in the earlier register: I001-CONTROLLED,
I001-SOURCES, I001-RUNTIME, I001-TELEGRAM, I001-TIMING, I002-DIAGNOSTICS, I003-UX,
I004-SHORT-LINKS, I005-LIVE, I005-TELEGRAM, I005-CONTAINER, I006-CONTAINER and I006-TITLES.
Keep inherited results separate even when one observation supports an OP case too.
Use the [section 8 matrix](quickstart.md#8-representative-delivery-and-inherited-matrix-t066)
for the five original source categories, music, two accounts, timing, short links,
client UX, native bytes and caption/saved/forwarded filename checks. Representative real
delivery is additionally required for feature-008 acceptance (F008-INSTALL/ASSESSMENT).
No inherited gate is transitioned by this documentation update.

For each failed case choose `deployment regression`, `evidenced pre-existing source
limitation`, or `unclassified`, citing precise earlier validation or an independent
comparable baseline before claiming a source limitation. A missing token/host/reboot
capability is not a source limitation; record `blocked` with the actual missing
prerequisite if an execution attempt establishes it. Otherwise keep unexecuted cases
`pending`. Publish only sanitized case IDs/outcomes; private manifests/diagnostics stay
outside Git and release assets. Do not record credential contents or hashes.

Feature completion requires every feature-008 gate to pass, representative real delivery
and an executed/assessed inherited matrix. Only evidenced pre-existing source limitations
may remain open inherited stable-readiness blockers on a completed preview feature;
missing execution/evidence, deployment regressions and unclassified failures still block
completion. Reclassification never passes a failed gate. Stable promotion and capability
claims still require the corresponding inherited gates to pass.

## Phase 6 — operations documentation checkpoint (2026-11-01)

- Tasks: T051–T058. Branch `008-public-docker-deployment`, parent revision
  `60cef5468e5aaf8a62f05c86b37b14feaa2976e0`, documentation-only working changes.
  No version/public digest selected and no runtime/container/workflow code changed.
- gate_id / requirement_ids: F008-OPERATIONS/F008-ASSESSMENT documentation readiness;
  FR-015–FR-021; SC-003, SC-007–SC-008. Class: Controlled. Scope: Feature 008 acceptance,
  documentation checkpoint only. Result: **pass for the executed checks below**;
  failure_class: none. Aggregate external gates remain pending.
- Environment: local macOS workspace, Bash syntax validation, Python through the locked
  uv environment; Docker Compose 5.6.1 used only for offline configuration rendering.
  No polling, credential mutation, host reboot, network disconnection, live source access,
  publication, or operator service modification performed.

### Executed verification (T058)

- Parsed all **43** Bash/sh blocks across `deploy/README.md`, `quickstart.md` and root
  `README.md` with `bash -n`, plus 3 existing blocks in this validation record
  (**46 total**); compiled embedded Python heredocs. All passed. Checked relative
  Markdown file targets and heading anchors across all four documents. Reviewed paths
  and CLI names manually
  against Compose, token configuration and operations contracts. Corrected stale
  quickstart inventory inputs to `inventory-amd64.json` / `inventory-arm64.json`, matching
  the collector output; removed obsolete descriptions of already implemented tests.
- Executed the actual rotation block plus the existing `start_checked` function with
  temporary synthetic files and controlled sudo/Docker/editor boundaries. All four
  scenarios passed: success orders stop → replace → preflight → start → confirmation;
  failed stop prevents replacement/start; failed local preflight leaves stopped with
  no start; failed health invokes explicit stop cleanup. Temporary input cleanup passed
  in every scenario. Harness: `/tmp/openmedia-phase6-check.py` (local scratch evidence).
  This checks command ordering and shell failure exits, not real root permissions,
  mount renewal, Telegram authentication or host recovery.
- Rendered the documented optional diagnostic bind mount merged into a temporary copy
  of production Compose with synthetic digest/token and diagnostic flag enabled.
  `docker compose ... config --format json` passed: writable log mount at
  `/var/log/openmedia`, `create_host_path: false`, UID/GID 10001 and read-only root
  retained. No container was started; actual log permissions/retention/persistence remain
  OP-DIAGNOSTICS-ON/I002-DIAGNOSTICS.
- `uv run --locked pytest tests/unit/test_config.py tests/unit/test_config_diagnostics.py
  tests/unit/test_diagnostics.py tests/integration/test_diagnostic_trace.py
  tests/integration/test_runtime.py -q`: **236 passed**, 2 existing PTB deprecation
  warnings. These existing tests cover configuration privacy, diagnostics and local
  heartbeat/lifecycle/child cleanup; no duplicate documentation-snapshot tests added.
- Ignore verification: existing Git/Docker exclusions already cover host secrets,
  deployment state/evidence, diagnostics/logs, live manifests, Python build/cache and
  private staging outputs. No missing critical pattern found; neither ignore file changed.
  No Node/ESLint/Prettier/Terraform/Helm setup requiring additional ignore files found.
- Privacy/contract review: inspection prints selected state only; logs are bounded;
  diagnostics stay default-off/private with explicit mount and retention; rotation never
  prints/hashes credentials and recreates mounts; encrypted backup excludes media/request
  state; restore uses current credentials; removal is project-scoped with retained-file
  inventory. No autoheal/process manager, new runtime dependency or storage introduced.
- Public claims reconciled with existing evidence: 001 historical feasibility and
  Telegram results remain historical, 005's 2026-10-08 tested-track phone playback is
  partial manual evidence, and 006 client title/filename/byte checks remain open.
  No new live capability or tested Ubuntu/architecture combination claimed.
- `git diff --check` passed. `.specify/extensions.yml` is absent; no before/after
  implementation hooks are registered.

Official Docker references checked for this runbook:
[restart policy and monitoring threshold](https://docs.docker.com/engine/containers/start-containers-automatically/),
[container signals](https://docs.docker.com/reference/cli/docker/container/kill/),
[project removal defaults](https://docs.docker.com/reference/cli/docker/compose/down/).

**US4 implementation checkpoint:** operations instructions and readiness reporting are
ready for external execution. **T065–T066 remain pending**, as do all T059–T067 tasks.
No real rotation, recovery/reboot/outage, backup/restore/removal, polling or delivery
acceptance is claimed. Final-candidate controlled/native/public checks remain Phase 7;
earlier CI images do not establish final-candidate acceptance. Other host combinations
remain pending, and no inherited stable-readiness gate changed status.

### Phase 7 final-candidate checks — 2026-11-02 (T059 complete)

- gate_id / requirement_ids: F008-REGRESSION, F008-NATIVE-AMD64,
  F008-NATIVE-ARM64, F008-RELEASE-POLICY, F008-SOURCES; FR-001–FR-004,
  FR-007–FR-010, FR-014, FR-017–FR-021; SC-002, SC-004, SC-006, SC-008.
- class / gate_scope: Controlled and native container / Feature 008 acceptance;
  matching-source acquisition here is a prepublication check, not public availability.
- release / platform: reviewed candidate
  `17c7d6df5dc9f86a8f5ebaad46b542e21d3d1ea2`, package 0.1.0;
  development-labeled linux/amd64 and linux/arm64 images, not published images.
- environment: local macOS 27.0.1 arm64, Python 3.13.15, uv 0.13.6;
  native hosted Ubuntu 24.04 runners, Docker 28.0.4, Compose 2.38.2,
  checksum-pinned Buildx 0.38.1 and Syft 1.55.0. Runtime Python 3.13.15,
  uv 0.12.15, Deno 2.9.6 and FFmpeg/ffprobe 5.1.9-0+deb12u1 unchanged.
- result / failure_class: **pass / none** for T059. Controlled, both native jobs,
  full matching-source validation and material upload completed successfully.

The final audit found an authority bug before publication: RepositoryRole ID 4 is
Write, not Maintain. New tests first reproduced acceptance of Write, rejection of
Maintain ID 2, and the collaborator API's legacy `permission=write` for Maintain.
The committed correction accepts Maintain/Admin (IDs 2/5), uses effective `role_name`
when supplied, and rejects Write in both initial authority and pre-push authorization.
Nine new controlled cases cover these decisions. See the Phase 7 research entry.

`uv run --locked pytest -q`: **1159 passed, 3 live tests deselected**, 32 existing
PTB deprecation warnings. `uv build` produced the sdist and wheel; local uv 0.13.6
warns that the existing build backend range targets uv-build 0.12. No pin changed.
`python3 scripts/release/publish.py audit-pins` and `git diff --check` passed.
The checklist gate remains read-only: requirements.md **16/16 checked**.
Read-only artifact consistency review found task coverage for all 21 FRs and 8 SCs
across 67 tasks, with no Phase 7 ordering or constitution conflict. Ignore files
already cover the detected Python/Docker setup and protected deployment/staging paths.

Authoritative exact-revision evidence is the **push** workflow
[41495762383, attempt 2](https://github.com/hman-pro/openmedia/actions/runs/41495762383/attempts/2).
Its controlled record explicitly identifies this full candidate SHA and attempt 2.
Native jobs independently completed restricted/no-network smoke, full-image inventory,
SPDX generation, archive/config identity validation and artifact upload:

| Platform | Native runner image revision | OCI config ID | Docker archive SHA256 |
|---|---|---|---|
| linux/amd64 | 20261026.354.1 | `sha256:6c325d7c8e301bc207a090e8d9142786b33258e365aca20b0f36e3543cc4d5a6` | `16fa228c26333e59508f7db29923b017d140a217b153866d8dfb64ebeec69734` |
| linux/arm64 | 20261026.166.1 | `sha256:5381aa9bbe49bc38b7f5f245c531b7260e792c0241b36d727b90449ff3544965` | `9ac62c5d94a4adc7ea61a8c865c30c44e0049c956ebf6f491191e1a6a698d62c` |

Inventories contain **321 amd64 / 317 arm64 components**, with neither pytest nor
pytest-asyncio installed. Retrieved native records pass prepromotion validation;
both inventories identify the candidate SHA and match their recorded hashes.
Architecture SPDX SHA256 values are respectively
`bc881f1d96d286622cd80bf31840a2bcfc649b42045ddd14134dfc5b56ca0027` and
`a4ba83b0cffea2561aacc03994ee12c8924f52d6cd9a993443b05293ddfdcd67`.
These match the downloaded SPDX files. Archive hashes above were computed/checked
by the native jobs; local metadata retrieval alone is not an independent archive import.
Evidence is staged privately at `/tmp/openmedia-008-phase7/exact-{controlled,amd64,arm64}`.

The earlier selected run 41495769136 is a **pull_request** run. Its controlled record
uses synthetic merge SHA `747bdcf3f1b159ec197f84c1dc6f3dbce4f60ed8`; it is supplemental
PR evidence only, even though the run API reports candidate head SHA 17c7d6d.
After detecting this, reran the push workflow rather than promoting merge-SHA images.
Cancelled/superseded attempts and earlier phase images do not establish T059 acceptance.

Acceptance-host discovery is read-only: `ssh openmedia-server` reaches Ubuntu
26.04.1 LTS amd64 after the operator corrected network settings. Existing Docker
29.1.3 and Compose 2.40.3 come from Ubuntu packages, not the guide's official Docker
repository. The Docker-group SSH user can inspect containers but has no noninteractive
sudo; the operator will perform privileged steps. `/opt/openmedia` does not exist.
An existing healthy root-Compose project `openmedia` runs `openmedia:local`, content ID
`sha256:52520a82eb6b8259990f4e36c2111bcf388c9b7a84fb9bf5a565344519ce081b`,
with no restart since 2026-10-19. Its protected environment is retained on the host;
no token contents were read into evidence or transferred to CI. No deployment file,
service or host package changed. Clean-host installation, migration/recovery and
all other actual server/media cases remain unexecuted; host discovery does not pass them.

The authoritative push attempt completed successfully at **18:30:39 UTC**. Its source
job ran **18m 58s** (18:11:41–18:30:39 UTC), including full acquisition, safe archive
checks, notice/recipe coverage, explicit source-bundle validation and upload.
Downloaded diagnostics independently validate **1899 components, all complete**;
both embedded inventories exactly equal the separately retrieved final native inventories.
Progress receipt: `stage=source-bundle-validation`, `coverage=complete`, `result=pass`.
Source-manifest SHA256:
`ae0e915da7ac0be91d14193ed8f2b87f77b00f353021b4fbe4ec974875840a02`.

| Exact-candidate source material | Bytes | SHA256 |
|---|---|---|
| sources-001.tar.gz | 1064438028 | `c2fb4219d29383a8a89b55d0447a8356a4631bd2f38b103e76ef0afb24ddfba3` |
| sources-002.tar.gz | 918728135 | `a820f68eb6e591275f355324606e417d56d0c26f56f0629af55c99614f214195` |
| notices.tar.gz | 16245613 | `b499f8bf2f2bd2b04ed3fd9872d1375ddcea0f05ae8fac605af321bce01f5d1a` |

The matching-sources CI artifact is 2,009,003,934 bytes, artifact ID 13169260406,
SHA256 `22564bcbac7749b19b5d57767656208aab7297587a1ac676378a686210340533`.
CI rehashed/inspected the complete inner source and notice bundles. Local independent
inspection here covers the manifest/schema/coverage/inventory joins, not a second
download of every material byte. This is temporary CI evidence with one-day retention;
F008-SOURCES public distribution and signed-release acceptance still require T062.
The supplemental PR workflow also completed successfully, but is not the release identity.

### T060 repository authority and first-package bootstrap — 2026-11-02

- gate_id / requirement_ids: F008-RELEASE-POLICY, F008-PUBLIC; FR-001–FR-003,
  FR-020; SC-001–SC-002. class: Public distribution configuration.
  gate_scope: Feature 008 acceptance. result / failure_class: **pass / none**
  for T060 configuration; this is not public image acceptance.
- Canonical repository lookup: numeric ID **1380348601**, public, current actor
  has admin/maintain/push. Before this invocation, the only ruleset was a disabled
  branch rule; release immutability was disabled. Existing branch rules were retained.
- Created active tag-creation ruleset
  [26388931](https://github.com/hman-pro/openmedia/rules/26388931), matching
  `refs/tags/v*` and `refs/tags/sources-v*`, with creation restricted and only
  RepositoryRole **2 (Maintain)** / **5 (Admin)** allowed `always` bypass.
  API readback confirms `current_user_can_bypass=always` for the current administrator.
- Created separate active mutation ruleset
  [26388932](https://github.com/hman-pro/openmedia/rules/26388932), matching the
  same refs, prohibiting update and deletion with **no bypass actors**.
  API readback confirms `current_user_can_bypass=never`, including the administrator.
- `PUT repos/hman-pro/openmedia/immutable-releases` succeeded; independent GET
  returned `enabled=true`, `enforced_by_owner=false`. Future releases are immutable
  at publication. Existing tags/releases were not changed.
- Actions are enabled, allowed actions currently `all`; workflow token defaults
  are `read`, with pull-request approval disabled. Checked CI logs expose only
  contents/metadata read. Reviewed full action pins provide the code-level allowlist.
  Release job grants are explicit: authority contents/package read, source staging
  contents write, promotion contents/package write, evidence contents/OIDC/attestation
  write with storage-record creation disabled. Actual registry/OIDC execution is T062;
  no claim that declared permissions alone prove successful publication.
- Capability limitation: package enumeration returns **403: read:packages scope
  required** for this local CLI credential. The earlier direct package lookup's 404
  therefore did not prove absence. The owner separately checked and confirmed on
  2026-11-02 that the OpenMedia package **does not exist yet**.
- The existing [maintainer distribution runbook](../../deploy/README.md#maintainer-release-procedure)
  documents first creation: publish complete source assets, promote checked images,
  have the owner set the newly created canonical package public, require anonymous
  both-platform retrieval before finalizing, and rerun only a failed evidence job
  against unchanged promoted images after fixing visibility. Never rerun successful
  promotion or move immutable tags. This bootstrap remains required in T062.
  The bot credential remains on the acceptance host; no GitHub CI bot-token variable
  is required or provisioned.

### T061 final-candidate distribution audit — 2026-11-02

- gate_id / requirement_ids: F008-RELEASE-POLICY, F008-SOURCES, F008-COMPOSE;
  FR-001–FR-010, FR-018–FR-021; SC-002, SC-004, SC-008.
  class: Controlled/material review; gate_scope: Feature 008 acceptance.
  release / platform: candidate 17c7d6d and the exact native/source records above.
  result / failure_class: **pass / none** for T061 audit, not public/live acceptance.
- Reviewed Dockerfile, published Compose, both workflow files, source/verification
  policies, build-tool installer, promotion/verifier boundaries and produced native
  inventories/SPDX/source manifest. Runtime/base/collector images retain exact digests;
  FFmpeg retains its exact Debian version; external actions use reviewed 40-hex commits,
  and downloaded tools use exact versions and SHA256 values. No runtime pin changed.
- CI remains read-only, without `pull_request_target` or bot credentials. Privileged
  release jobs are serialized with cancellation disabled and require the canonical
  repository, protected matching tags and preview syntax. Both imports/config IDs,
  controlled/native results, full coverage and anonymous matching sources precede any
  image push; provenance/anonymous image checks gate finalization, and public evidence
  redownload gates acceptance. No application image rebuild occurs in promotion.
- The observed authority-role defect was corrected and retested before tagging.
  Independent policy pins numeric repository identity, workflow, issuer and hosted
  builder; account-free verification uses established roots and stripped auth with
  raw index/manifest subjects. Real own-release signatures remain T062, not supplied
  by controlled certificate fixtures or this review.
- Native jobs inventory the whole static filesystem and retain original notices,
  including hidden application `.venv` paths. Complete 1899-component source closure
  covers Debian/Built-Using, both Python environments and unmanaged/embedded materials.
  CI validated original acquisition hashes, safe archives, original/declared notices,
  exact source/recipe files and logical bundle hashes; locally checked manifest joins
  and coverage agree with both exact native records. This is matching-source evidence,
  not a binary reproducibility claim or public source availability.
- Explicit Docker COPY inputs and Git-archive source allowlist exclude host deployment
  configuration, live manifests, media and private staging. Git/Docker exclusions
  remain in force; produced inventories have no development test tooling or runtime
  token configuration. CI receives only fake smoke secrets, never the real bot token.
  Upstream source archives/notices are retained unchanged under their reviewed hashes.
- Published Compose retains UID/GID 10001, read-only root/secret, init, dropped caps,
  no-new-privileges, bounded resources/logs and tmpfs; it has no application ports,
  Docker socket, media volume or build directive. Diagnostics stay default-off.
- Preview-only version checks, prerelease labels and pending external gate references
  remain enabled. T062–T067 and actual supported-host/media combinations remain open;
  no stable, publicly accepted or live deployment claim is made by this audit.

### T062 preview attempt and host migration preparation — 2026-11-02

Created annotated `sources-v0.1.0-preview.1` and `v0.1.0-preview.1`, both resolving
to reviewed candidate `17c7d6df5dc9f86a8f5ebaad46b542e21d3d1ea2`. The actual pushes
used the administrator's permitted creation bypass; no update/deletion bypass was
used or granted. [Release run 41501886450](https://github.com/hman-pro/openmedia/actions/runs/41501886450)
passed authority with actual contents/package **read** permissions, matching tag-pair
and effective ruleset checks, pin audit and unused image-version authorization.
The tag run also passed its repeated controlled suite and both native jobs.
Source collection/publication, promotion and signed/public acceptance remain pending
at this record's creation. T062 stays unchecked; tags are not acceptance evidence.

Staged public verifier/deployment files from the exact reviewed Git commit under the
operator's user-owned `openmedia-008-phase7-17c7d6d` directory. The pinned installer
downloaded and checksum-verified Linux amd64 gh 2.103.3 and regctl 0.11.7 there.
No real credentials entered this staging directory, local evidence or CI. No sudo,
application start/stop, host package installation or production configuration occurred.

Preparing the actual host exposed an operator-guide gap: its existing root Compose
project is already `openmedia`, while the migration guide rejected that name.
Updated the guide to support this ordinary default: after nonpolling preflight,
same-project discovery must identify exactly the recorded old container; stop and
confirm it before forced activation. Retain old files and pinned content for recovery.
Recovery under shared labels is explicitly described as running the old local image,
rather than incorrectly calling the whole project stopped. Unrecognized container
identity aborts before stopping or starting a poller.

The disposable same-project harness first reproduced the healthy migration failure
against the former guide. After correction, **32 same-project scenarios** passed,
including rejection of a foreign running container with old service undisturbed.
The existing **31 distinct-project scenarios** also passed. Both harnesses exercise
healthy/update/preflight/stop/startup/signal/persistence failures, rollback, migration
and old-image return. Syntax checks passed for 31 guide and 6 quickstart shell blocks;
actual protected-file persistence payload checks passed. Scratch harnesses live under
`/tmp/openmedia-008-phase7/` and `/tmp/openmedia-008-phase5/`. They are controlled
command-boundary checks, not real polling/migration acceptance.

This is a deployment-guide-only correction: `deploy/README.md` is excluded from the
runtime Docker context and is not an image COPY input. The already tagged image/workflow
inputs are unchanged; no tag or distributed artifact is moved to include later evidence
or guide corrections. Operators use the separately reviewed updated guide with the
exact verified image. Actual T063–T066 host/media gates remain open.

### Operator-requested stop / resume point — 2026-11-02, 19:00 UTC

The operator explicitly requested stopping and continuing later. Requested normal
cancellation of release run **41501886450** during `checks / sources`; because the
run did not promptly stop, also submitted GitHub's force-cancel request (accepted).
Final API readback confirmed **status=completed, conclusion=cancelled**, with
`checks / sources` cancelled and no publication jobs created.
At the stop request, authority, controlled and both native jobs had passed; source
publication, promotion and evidence jobs had not started. No registry image or public
release had been published. Preserve both preview/source tags at commit 17c7d6d;
do not move or delete them.

**Resume at T062.** T059–T061 are complete; T062–T067 remain unchecked. If candidate
image/workflow inputs remain unchanged, rerun the complete cancelled tag workflow,
including all checks, for the same unpublished version; its authority must recheck
unused-version status. Do not reuse expired/partial CI artifacts or count the cancelled
source job as passed. If image/workflow content changes, use a newly checked commit and
new immutable tag pair. First-package public visibility still requires the owner's
action, and a separately gated baseline/candidate pair is needed for rollback acceptance.

The existing server bot, host packages and protected credential/configuration remain
unchanged. The operator chose to perform privileged server steps manually; noninteractive
sudo remains unavailable. Staged public verifier tools and anonymous acceptance helper
are under `/home/homan/openmedia-008-phase7-17c7d6d`; no real token is staged there.
The authority fix is committed/pushed as **17c7d6d**. Migration-guide, task-marker and
validation edits are preserved **uncommitted** in the feature branch working tree.

### T062 resumed: partial rerun rejected before image writes — 2026-11-05

Live GitHub readback supersedes the cancelled-run resume snapshot above. Run
[41501886450, attempt 2](https://github.com/hman-pro/openmedia/actions/runs/41501886450/attempts/2)
completed with failure on November 2. Only the cancelled source job and its downstream
jobs reran: controlled/native/authority execution timestamps still match attempt 1
(18:34–18:36 UTC), while source collection restarted at 19:01:41 UTC. Promotion's
current-attempt controlled-receipt guard therefore rejects the reused receipt.
The promotion log ends before Docker archive imports, publication-stage receipt creation
or any image push. This is an enforced pre-push identity gate, not a runtime failure.

Source staging succeeded: `sources-v0.1.0-preview.1` was published at
19:23:25 UTC, is immutable, and retains both inventories, source manifest, two source
parts and notices. The image release `v0.1.0-preview.1` remains an empty, unpublished
draft. All temporary run artifacts have expired (artifact listing is empty).
Retain both tags, the source release and the draft. No preview.1 acceptance is claimed.

Recovery uses a new preview.2 tag pair and a complete pipeline, rather than attempting
to replace immutable materials with rebuilt inventories. The maintainer guide now
explains whole-run retries before promotion and new-version recovery after artifact
expiry with already-published sources. Added three controlled promotion cases for stale
attempt/run/source receipts; each rejects before any image push. No production code,
runtime dependency, image input pin or workflow changed.

Validation: release-policy suite **60 passed**; full locked suite **1162 passed,
3 live tests deselected**, 32 existing PTB deprecation warnings. Pin audit and
`git diff --check` pass. Requirements checklist remains **16/16** checked. Read-only
artifact review retains the existing 21-FR/8-SC coverage across 67 tasks and sequential
Phase 7 gates; no specification/plan/constitution change is needed for this retry.
T062–T067 remain unchecked pending actual acceptance. The earlier migration/evidence
changes were committed as 958d855 before this session; the worktree was initially clean.

### Preview.2 full release gates — 2026-11-05

- gate_id / requirement_ids: F008-REGRESSION, F008-NATIVE-AMD64,
  F008-NATIVE-ARM64, F008-RELEASE-POLICY, F008-SOURCES, F008-PUBLIC;
  FR-001–FR-004, FR-007, FR-018–FR-021; SC-001–SC-002, SC-004, SC-008.
  class: Controlled/native container/public distribution.
  gate_scope: Feature 008 acceptance.
- release / platform: annotated `sources-v0.1.0-preview.2` and
  `v0.1.0-preview.2`, both at `4f693c5a1fb0d675524c1752f2424552fc57944e`.
  Both tag pushes used the permitted administrator creation bypass; no mutation
  or deletion rule was bypassed. Release
  [42074124949](https://github.com/hman-pro/openmedia/actions/runs/42074124949).
- environment: native Ubuntu 24.04 hosted runners, image revisions
  `20261101.360.1` amd64 / `20261101.172.1` arm64; Docker 28.0.4,
  Compose 2.38.2, Python 3.13.15, Deno 2.9.6, FFmpeg/ffprobe
  5.1.9-0+deb12u1, retained reviewed Buildx/Syft pins. CI uses fake secrets only.
- result / failure_class: controlled, authority and both native checks **pass / none**;
  source/public acceptance remains **pending** during attempt 2. Attempt 1
  **failed** during the first component's authenticated APT index refresh, before
  source publication or any image writes. Two independent branch/PR source jobs
  also failed at that boundary. The preserved diagnostic identifies
  `debian:adduser@3.134`, stage `acquisition-and-notices`, coverage `missing`;
  its truncated traceback does not establish the underlying APT cause.
  Do not classify this as a media-source limitation or bypass authentication.
- evidence / limitations: public Debian current and selected historical InRelease
  endpoints independently returned HTTP 200 from the local network. Started a
  **whole-run** retry, not failed-jobs-only, while no preview.2 source assets or
  images had been published. Attempt 2 again passed authority, the controlled suite
  and both restricted offline native checks. Its downloaded controlled receipt
  explicitly matches run `42074124949`, attempt `2`, and the tagged full commit.
  Separately retrieved platform records pass schema/source/version validation;
  actual inventory/SPDX file hashes match their records. These metadata checks
  do not independently import the Docker archives or prove public access.

| Attempt 2 platform | OCI config ID | Docker archive SHA256 |
|---|---|---|
| linux/amd64 | `sha256:8e7ddb825c6295e7d139037ed83cd5272703a6d57e490a8bda3749884997c288` | `12e032bddf85aefe7c593a324bb87f81a84b9902db1d674781459bb90c283a2a` |
| linux/arm64 | `sha256:52116dcba88f83d10937b3249353d04c1b3241f645d98819e790c09ca40b96c7` | `841f5c0e4e3fe0d70d22bbe383460759df7006e6e8eaf5df6dc3a6e9ca17d3ca` |

Private staging: `/tmp/openmedia-008-phase7/preview2-attempt2-{controlled,amd64,arm64}`;
the superseded first-attempt records use separate `preview2-*` directories.
First-attempt source diagnostics remain under `preview2-sources`.

Actual server acceptance is blocked on connectivity: both sandboxed and approved
direct SSH attempts to the configured `openmedia-server` address timed out before
authentication. Requested restored connectivity or an updated SSH address. No host
configuration, package, credential or polling service changed. Local Docker is also
unavailable (daemon socket absent). T063–T066 remain unexecuted; existing successful
CI offline probes do not pass those gates. The operator's prior preference to perform
privileged server steps manually remains in force.

Attempt 2 source collection completed successfully at **17:54:10 UTC**, after
**23m 17s**. Its coverage receipt reports `source-bundle-validation`, `complete`,
`pass`, **1899 components**. The source manifest validates independently and its
two embedded inventories exactly equal the downloaded native inventories.
Source-manifest SHA256:
`8139316b9da03c4fd6fec1c8efe2334c6936d50117d949a5d30de6b20dc79580`.

The completed [sources-v0.1.0-preview.2 release](https://github.com/hman-pro/openmedia/releases/tag/sources-v0.1.0-preview.2)
was published immutable at **17:58:27 UTC**. The source-release job passed its
anonymous downloads before promotion began. Independent local Python HTTPS downloads
used no GitHub token or authenticated client; every public source/notice/inventory
asset matched the exact expected size/hash. `validate_sources` then inspected the
downloaded source bundles and verified their full source/notice/build-material joins.
This establishes **F008-SOURCES pass**, while image/signature acceptance remains open.

| Public matching material | Bytes | SHA256 |
|---|---|---|
| sources-001.tar.gz | 1064436573 | `137c762a98347dbee7e052d9fa3e224b76d66d2f3e2f38b94391ee7dc988b1e6` |
| sources-002.tar.gz | 918727883 | `5c665660520b40d755c4f6e0171402c70644d0fc5c25115df333983003577e04` |
| notices.tar.gz | 16245613 | `b499f8bf2f2bd2b04ed3fd9872d1375ddcea0f05ae8fac605af321bce01f5d1a` |

Full independent public material bytes are retained outside Git at
`/tmp/openmedia-008-phase7/preview2-public-sources`. For independent registry
retrieval on this Mac without Docker, downloaded official regctl **0.11.7**
`regctl-darwin-arm64`, SHA256
`8ac077a1eeb834d3053714e86ccbd838d0da46567df8cd7c2695d1a19135bf60`.
The official GitHub release API supplied this digest; actual downloaded bytes match.
It reports source revision `36abda84830dae07db00bf9e5cec95d97b78222a`.
This adds only a temporary host acceptance tool, with no repository/runtime pin change.

### Preview.2 post-push failure and corrected release boundaries — 2026-11-05

Run 42074124949 attempt 2 completed **failure** at 18:07:01 UTC. Authority,
controlled, both native jobs, source collection and immutable public-source staging
passed. Promotion validated/imported both checked archives before image writes,
pushed both children, and wrote the exact OCI version index; evidence/signing was skipped.
The preserved `publication-stage.json` says `images_published`. The final release
remains draft **435539850**, explicitly titled **INCOMPLETE preview**, with no assets.
No image/source/tag was moved, overwritten or deleted.

| Published incomplete object | SHA256 digest |
|---|---|
| OCI index | `71b89d6132ee04de9c55c44d718862bc71242f40b67e73e9cf0baa93573cae2b` |
| linux/amd64 child | `529e3ccd09de3de9ca53127fd70d6b445cb168b9be7606a97abd9a2cefb54207` |
| linux/arm64 child | `44d357b590ba584753cf4ecba6c6130b3676b3bae04d2b9e7a8cbb1f30628e74` |

Both child config digests match the exact attempt-2 native records above. The raw
index is OCI format and maps precisely these two platforms. Independently reproduced
the post-push error with actual pinned regctl 0.11.7: `manifest head --format
'{{.Digest}}'` fails because the OCI-index template has no `Digest` field. Its default
output is the correct digest and matches SHA256 of the retained raw index. Promotion
now uses that default output. This is a **deployment/release regression**, corrected
in the next candidate; the incomplete preview.2 is not accepted or selected for startup.

Also verified a latent finalization issue against GitHub: the tag lookup endpoint
returns HTTP 404 for this authenticated maintainer's unpublished draft, while the
authenticated release listing and ID lookup return it. `get_release` now falls back
to the paginated authenticated listing only after 404, finds the exact tag, rejects
ambiguous drafts, and retains fail-closed behavior for permission/network errors.
It never creates or replaces an existing populated release.

Controlled reproduction before fixes: **5 failed, 60 passed** in release-policy tests.
After fixes: **65 release-policy tests passed**, full locked suite **1167 passed,
3 live tests deselected**, 32 existing PTB warnings. Real-service checks using the
fixed helper found draft ID 435539850 and anonymously retrieved the correct index digest.
No runtime/source-access behavior, image input pin or workflow permission changed.
The changed publisher requires a new candidate/tag pair and complete release checks.

The signed-in owner browser visibly reports the newly created canonical GHCR package
as **Public**, with preview.2 and both auxiliary architecture versions. Independent
regctl access used an empty HOME, Docker/regctl configurations and no inherited
credentials; index retrieval succeeds. No visibility setting was changed by this
session. Package visibility/bootstrap is established, while full signed-release
acceptance is still open.

After the operator restored connectivity, SSH discovery succeeded: Ubuntu 26.04.1
amd64, Docker 29.1.3, Compose 2.40.3+ds1-0ubuntu1, existing `openmedia:local` container
healthy with two weeks' uptime. `/opt/openmedia` is absent and noninteractive sudo
remains unavailable. No production file/service/credential changed. The earlier SSH
blocker is resolved; manual privileged provisioning and actual acceptance remain pending.

### Preview.3 corrected candidate and server staging — 2026-11-05

Committed the two release-boundary fixes and their failing-before/passing-after
checks as **083ea8fc3d1df7963383a5c011696c2ad31143a2**, then pushed the feature
branch and new annotated `sources-v0.1.0-preview.3` / `v0.1.0-preview.3` tag pair.
Both use the same reviewed commit and permitted maintainer creation bypass. Preserved
all preview.1/preview.2 tags, incomplete drafts, image identities and immutable sources.
[Release run 42084150441](https://github.com/hman-pro/openmedia/actions/runs/42084150441),
attempt 1, passes authority, controlled tests and both native restricted builds/smokes;
source/public gates remain pending while its source job runs. Local `uv build`, pin audit
and diff checks passed after the fixes; uv 0.13.7 reports the existing uv-build range warning.

Downloaded controlled receipt matches the exact tagged commit, run ID and attempt 1.
Downloaded native metadata passes platform/source/version validation and actual inventory/
SPDX hash checks. Same native runner image revisions and tool versions as preview.2.

| Preview.3 platform | OCI config ID | Docker archive SHA256 |
|---|---|---|
| linux/amd64 | `sha256:f7127ac9572b2103fb81212dfca07567e967951d11c09e58904480a62fcd0847` | `26ce6d8b4bd0217263fa70e7d4fffb2fbd485203c076221b164a6b132a2e69cc` |
| linux/arm64 | `sha256:f32b4973100c9cdebf9363753b96c0f4fd7cb92c9721e83bfbe4c2ca197838f4` | `994d43d7a8301fa72eed377ed404ee3d93386f7326b6b9f978a4de8417a8f602` |

As a separate real-material compatibility check, reconstructed an **unsigned, local-only**
preview.2 manifest from its actual retained index/children, checked native records and
independently downloaded source bytes. Pure manifest assembly and full `validate_bundle`
passed. This exercises the post-digest assembly path not reached by the failed workflow;
it is not signed evidence, does not change any release, and does not accept preview.2.
Scratch path: `/tmp/openmedia-008-phase7/preview2-offline-assembly`.

Staged exact reviewed public verifier/deployment files and nonpolling anonymous helpers
under `/home/homan/openmedia-008-phase7-083ea8f`. Pinned Linux amd64 gh 2.103.3 and
regctl 0.11.7 installed there with checksum verification; no host package/root
configuration or service changed. Host package discovery confirms `docker.io`
29.1.3-0ubuntu4.1 and `docker-compose-v2` 2.40.3+ds1-0ubuntu1, rootful default
security (AppArmor/seccomp/cgroupns), and no group 10001. No live manifest was found
under the existing checkout. Asked the operator to perform the documented privileged
official-Docker setup; verified the staged README path and supplied its exact location.
Actual sudo provisioning, real polling/delivery, baseline/rollback and maintenance cases
remain unexecuted. No earlier live gate or T062–T067 task is marked complete.

The operator ran the privileged official-Docker installation. APT replaced the
Ubuntu Engine/containerd/runc packages but initially stopped because the still-installed
Ubuntu `docker-compose-v2` package owned the same Compose plugin path. Supplied the
targeted removal/recovery commands; the operator completed them. Independent SSH
readback confirms **Docker Engine/CLI 29.9.3**, **Compose 5.7.0**, containerd.io
2.4.2-3~ubuntu.26.04~resolute, installed official docker-ce/CLI/Compose packages,
removed docker-compose-v2, and an empty `dpkg --audit`. The existing local-build bot
restarted during the package migration and is healthy again. This is observed host
package recovery, not feature-008 release installation or unexpected-exit acceptance.

All required Compose up/run flags pass capability checks (`--wait`, `--wait-timeout`,
`--force-recreate`, `--no-build`, `--pull`, `--rm`, `--no-deps`, `--no-tty`).
Docker remains rootful with default AppArmor/seccomp/cgroupns security. The guide now
names the Compose-package collision and gives the exact targeted recovery command.
All **32 guide / 6 quickstart** shell blocks pass `bash -n`. This guide-only update
does not change the tagged runtime/workflow inputs or move preview.3's tags.

### Preview.3 signed evidence failure / operator-requested handoff — 2026-11-05

Preview.3 source collection, immutable source publication and **promotion all passed**.
The completed immutable source release was published at **18:54:09 UTC** with all
six assets. Independent credential-free downloads matched every expected size/hash;
full `validate_sources` inspected the actual source/notices/build-material contents
and passed. Source-manifest SHA256:
`43a2d33f9ab0429681554ba415e8e91003697be143f1dc2623c2893976590f4f`.
The successful source receipt binds the exact tagged commit and matching inventories.

| Published preview.3 object | SHA256 digest |
|---|---|
| OCI index | `96a142370770804af0b515283597bc119c2a5041732e113412cd564d8901ee1a` |
| linux/amd64 child | `079700a675219af4c27d47a6f38f7b2d4eb90b508bba3fb3ed4546370751c0f2` |
| linux/arm64 child | `e704484dc38195f967f35d02f9f1bf9357ca77db9bab517148c7e7ba6a0641a7` |
| release manifest | `117a77faea0c5b9cb401b151ad03592033533e8c420a0bff6366a548607d21ca` |

Independent anonymous regctl exports retrieved all image bytes for both platforms,
with empty HOME/Docker/regctl configuration and no inherited credentials. Exported
config IDs match the exact native records; architecture/OS/version/revision labels
match preview.3. Export sizes: amd64 **309216768**, arm64 **291030528** bytes.
These exports are different tar objects from CI's Docker-save archives; their sizes
are not archive-hash equality claims. No image was executed by this local check.

Both `actions/attest` steps succeeded, uploaded their signatures to Rekor and GitHub,
and signed the actual index and release manifest. Attestation records **64182594**
(index) and **64182617** (manifest) remain obtainable through GitHub's attestation API.
The evidence job failed during `finalize` at **19:11:06 UTC**, before final asset
upload/publication. Draft **435600508** remains empty and explicitly **INCOMPLETE**.
All images, source assets and tags remain intact; F008-PUBLIC/T062 do not pass.

Reproduced the failure with real gh **2.103.3**: the verifier supplies both
`--cert-identity` and `--signer-workflow`, but those selectors are mutually exclusive.
The CLI exits before checking either signature. Its own help documents using one
selector. Independently reran the actual two bundles with **only the exact
`--cert-identity` selector**, retaining `--repo`, source ref/digest, issuer,
GitHub-hosted-runner restriction, established roots, local bundles and stripped auth.
Both cryptographic verifications **pass**, and the existing additional numeric-repo,
repository-URI, source/ref, workflow-SAN, issuer, runner and subject checks **pass**.
The required correction is known but **not yet applied** to `validate_release.py`.
Last full controlled result remains **1167 passed / 3 live deselected** for 083ea8f.

The operator requested saving follow-up for a new session tomorrow, explicitly without
stopping running pipelines. At handoff, release run **42084150441** has already completed
failure, supplemental CI **42083688507** completed success, and supplemental CI
**42083680165** remains in progress. **No cancellation was requested or issued.**
No preview.4 tag or new release workflow was started. See [follow-up.md](follow-up.md)
for the exact pending fix, immutable-release recovery, evidence paths and next actions.

At the operator's request, created a private nine-case source manifest on the server
(mode 0600, parent 0700) using original feature-004 LinkedIn examples, selected public
YouTube/music inputs and unverified Instagram candidates. Both original LinkedIn HEAD
requests returned the expected one-hop targets, including the real hyphen-code URL.
No media/Telegram acceptance execution occurred. The operator will perform Telegram
tests manually; bot reference and source URLs remain in private staging, outside Git.
Private manifest: `/home/homan/openmedia-008-phase7-083ea8f/private/live-sources.json`;
local worksheet: `/tmp/openmedia-008-phase7/private-manual-tests.md`.


### Preview.4 verifier correction — 2026-11-17

Resumed Phase 7/T062 on `008-public-docker-deployment`. Confirmed release run
42084150441 remains completed/failure with only `evidence` failing; all earlier
checks, source publication and promotion succeeded. No existing run was cancelled
and no immutable tag, image or source asset was changed.

Extended the controlled signed verifier boundary to reject GitHub CLI 2.103.3's
mutually exclusive certificate selectors. Before the production fix, the release-policy
suite reproduced the defect: **1 failed, 64 passed**. Removed `--signer-workflow`
from the positive verifier command, retaining the exact `--cert-identity` SAN with
repository/workflow/version, repository selector, source ref/revision, issuer,
hosted-builder restriction, local bundles and parsed-certificate/subject checks.
The separate wrong-workflow negative proof still uses its valid workflow selector.
Updated research guidance to match this command.

Validation: **135 passed** across release-policy, release-manifest and release-tool
tests; full controlled suite **1167 passed, 3 live deselected**, 32 existing PTB
warnings. The initial sandboxed full suite had one real child-process shutdown
failure (1166 passed); the complete unsandboxed suite above passed. `uv build`
produced the source distribution and wheel; it warned that the host uv 0.13.9 is
outside the build-system's 0.12 range. Runtime/build pins were unchanged, and
`publish.audit_pins()` passed. `git diff --check` passed. Requirements checklist
remains 16/16 checked; no extension hooks are configured.

The next preview tag pair is unused and no release workflow is active. A new full
preview.4 pipeline is required; rerunning preview.3's evidence job would use the old
invalid command. T062 and public acceptance remain open until the new workflow and
anonymous verification actually pass. Server/manual T063–T067 remain unexecuted.


### Preview.4 pre-push source-policy rejection — 2026-11-17

Committed verifier fix `b4d087d8e9c8eb254f5435e68de488f25f77b809`, pushed
the feature branch and created the new matching `sources-v0.1.0-preview.4` /
`v0.1.0-preview.4` tags at that commit. The tag-pair availability API returned no
existing refs; an anonymous GHCR manifest HEAD returned 404 for preview.4.
The authenticated package API lacked read:packages scope; no token scope changed.

[Release run 44148163691](https://github.com/hman-pro/openmedia/actions/runs/44148163691)
completed failure: authority, controlled and both native build/smoke/inventory jobs
passed. Source collection rejected `debian:libsrt1.5-gnutls@1.5.1-1+deb12u2`
at policy resolution, before source publication or any image push. Source-release,
promotion and evidence jobs were skipped. The corrected signature command was not
reached; do not claim public acceptance from this run. Tags remain preserved.

Retrieved source-diagnostics artifact 14358450532 to
`/tmp/openmedia-008-preview4-diagnostics`. Both complete inventories show only
one previously unreviewed component/version, the SRT security revision released
November 10. Reviewed exact Debian source/patch/copyright changes and documented
the compatibility adjustment in plan.md and research.md. Added only that exact
additional binary/source policy identity, retaining the earlier reviewed revision
and fail-closed checks. Both actual inventories now resolve against the policy
(**321 amd64 / 317 arm64 components**); targeted release suites **135 passed**.
`git diff --check` passed. This is controlled policy resolution, not complete source
acquisition. A fresh preview.5 candidate must repeat the complete gated workflow.
T062 and server/live acceptance remain open.


### Preview.5 accepted public distribution — 2026-11-17

- gate_id / requirement_ids: F008-PUBLIC, F008-SOURCES, F008-NATIVE-AMD64,
  F008-NATIVE-ARM64, F008-REGRESSION, F008-RELEASE-POLICY; FR-001–FR-004,
  FR-007, FR-018–FR-020; SC-001–SC-002, SC-004.
- class: Controlled, native container and public distribution.
  gate_scope: Feature 008 acceptance. result / failure_class: **pass / none**
  for these gates. Server/live gates remain pending.
- release / source: `v0.1.0-preview.5`, matching `sources-v0.1.0-preview.5`,
  commit `c84a16802505cb9074995fbdcdf40e65363eecfa`.
- environment: native hosted Ubuntu 24.04 amd64/arm64 runners; reviewed pinned
  tools and production-restricted smoke checks. Runner image revisions and exact
  tool versions are preserved in the signed release manifest's platform records.
  Additional independent verification ran on the local macOS arm64 host with
  checksum-verified gh 2.103.3 and empty authentication/configuration.

[Release run 44149181265](https://github.com/hman-pro/openmedia/actions/runs/44149181265)
completed **success** at **19:29:23 UTC**. Every job passed: authority, controlled,
both native builds/smokes/inventories, complete source collection, source publication,
no-rebuild promotion and signed evidence/public acceptance. The source collector
reported **1899 component records, all coverage complete**, with 321 amd64 and
317 arm64 installed inventory components. Source-only release **449074148** is
public and immutable; its anonymous full-material retrieval passed before image
promotion. Final image release **449075641** is public, immutable and a prerelease:
[v0.1.0-preview.5](https://github.com/hman-pro/openmedia/releases/tag/v0.1.0-preview.5).

The evidence job verified the real raw-index and manifest bundles with the corrected
exact certificate selector, executed tampering/identity rejection proofs and anonymous
both-platform pulls, uploaded all final evidence before immutable finalization, then
redownloaded every public material/evidence asset and verified signatures, identities
and hashes again. The successful workflow closes the formerly failing evidence stage.

Accepted index / selected deployment image:

```text
ghcr.io/hman-pro/openmedia@sha256:2262f99c6580a2b2c4d60911febb5bb4180b4330329ae39878f5115e7d4b6b81
```

Release manifest SHA256:
`2c173a1ce350a0c14d6f533ae1639baddcd80a79298b122355ceabe1cb468359`.
Source manifest SHA256:
`f0bb5b777321d07c68e825a7f8c40d7e66828a83666e7ec8ba89a26c5e2539e7`.

| Platform | Child digest | Checked/imported config ID | Docker archive SHA256 |
|---|---|---|---|
| `linux/amd64` | `sha256:f026602740c27e85683634262ade1d20a547ec7764dfaae10a0833d3e944ace7` | `sha256:644e44bc218146f23943a316c925210a2a2c0acfb1d78d00f254379fa2a8bb21` | `21359be4e6e3c109e8bef4279fa5ddd4a5953728deedb19b71c09dad5580c734` |
| `linux/arm64` | `sha256:8c28e583d763bc5855ca1c053def3cd5a4912c2a2b4ab74d7098a96059fe35c6` | `sha256:7e6b3c16fbf50717e8e2495f8f0310c97f3b5d6ae1c43b76778f0b3b6d287e52` | `a50d0980e5b41738c9482372263b85c7e8c6be36607cdee6239e25bf0dc5c379` |

Independent local verification downloaded the four public signed-evidence files
without credentials into `/tmp/openmedia-008-preview5/public`. The official macOS
arm64 gh 2.103.3 archive SHA256
`d700207eae9ae98fe2b89535c2c087c07823d4628c56364695a5a07ef311c062`
matched both GitHub's release digest and its checksum file. For **both index and
manifest**, actual gh verification and `check_verified_attestations` passed the
repository/workflow/tag/revision/issuer/hosted-builder/subject checks; modifying the
bytes or selecting a wrong workflow caused rejection. The raw-index hash also
matched the published selected digest. Temporary verification JSON and the helper
are retained under that scratch root; permanent originals remain public release assets.
This independent check covers signatures and identities; the successful pipeline
provides complete source/material download and both-image acceptance evidence.

README, deployment guide, quickstart and handoff now reflect accepted public
distribution. **T062 remains open for its separately gated compatible baseline/candidate
pair**: preview.5 can serve as the accepted baseline, but no additional candidate
release was started. T063–T067 and all server/live obligations remain open. No server
configuration, credential, poller or running service was changed in this session.
Preview.1–3 remain incomplete, preview.4 remains unpublished, and all old tags,
images and required source releases were preserved. No CI run was cancelled.

### T063 clean-server installation and real delivery — 2026-11-23

- gate_id / requirement_ids: F008-INSTALL (and the root-Compose migration case of
  F008-UPDATE, recorded here as partial T064 evidence only); FR-005–FR-010,
  FR-011–FR-013, FR-018–FR-019; SC-003–SC-004.
- class: Deployment-network/manual. gate_scope: Feature 008 acceptance.
  result / failure_class: **pass / none** for F008-INSTALL on this host combination.
- release / platform: `v0.1.0-preview.5`, source commit
  `c84a16802505cb9074995fbdcdf40e65363eecfa`, selected index
  `ghcr.io/hman-pro/openmedia@sha256:2262f99c6580a2b2c4d60911febb5bb4180b4330329ae39878f5115e7d4b6b81`,
  linux/amd64 child `sha256:f026602740c27e85683634262ade1d20a547ec7764dfaae10a0833d3e944ace7`.
  Running container `9554be020b6385a978983cce05a13ade1c370a4dfa92c499a97d495a08e98657`,
  `.Config.Image` = `.Image` = the selected index digest.
- environment: operator-owned host, Ubuntu 26.04.1 LTS, amd64 (x86_64), rootful
  Docker Engine client/server 29.10.0 (official Docker APT repository, installed earlier
  by the operator), containerd 2.4.2, runc 1.5.3, Compose v5.8.0. Security options:
  apparmor, seccomp builtin, cgroupns; no rootless/userns. Outbound residential
  network; no inbound ports. Runbook inputs came from reviewed checkout
  `43cdc37e7910a6d2b486b3b5b48072aac11f96f4` staged on the host.

**Method.** Every shell block ran verbatim from that checkout's `deploy/README.md`,
extracted mechanically into separate files and executed by a logging runner the
operator started interactively (sudo is operator-only on this host). Two
operator inputs replaced the guide's interactive steps: the `sudoedit` calls were
satisfied non-interactively (image line set to the verified digest; the existing
credential piped from the old protected root-Compose `.env` into the new secret
file, never in arguments, history or output), and the old-project placeholders were
set to the inspected project `openmedia`, `/home/homan/openmedia/compose.yaml` and
its `.env`. Docker was already installed, so only the capability portion of the
installation block ran.

**Account-free verification (on the deployment host).** Pinned gh 2.103.3 was
installed through `install_tools.py` (archive checksum verified). With empty
GitHub/Docker configuration and no auth variables, all public preview.5 materials
(1.9 GB) were downloaded anonymously and `validate_release.py verify` passed against
the real local bundles; SHA256SUMS matched. Negative proofs all exited 1: one-byte
modification of `release-index.json`, `release-manifest.json` and `sbom-amd64.spdx.json`
(each in a disposable same-filesystem copy), a wrong index digest, and a wrong
source commit. The migration block repeated the positive verification before stop.

**Results (UTC).**

| Step | Outcome |
|---|---|
| Capability (18:15:46) | Version checks and every required `up`/`run` flag present; exit 0 |
| Provision (18:15:46) | `/opt/openmedia` root:root 0750; `compose.yaml` 0640; `deploy.env` root:root 0600 with defaults identical to the old deployment's nonsecret settings; `secrets/` root 0700; secret `root:10001` 0640, shape valid; no group 10001 and no user with primary GID 10001 |
| Pull + isolated preflight (18:16:02) | Selected env image equals candidate; anonymous pull; `--check-config` as UID 10001 with the mounted real secret: `configuration valid (token=<redacted> …)`; no poller |
| First-activation guard (18:16:03) | Refused with exit 1 because the old root-Compose service was running in project `openmedia`; old bot verified still running |
| Migration preservation (18:16:04) | Old container `6bafc9a8da21…`, content `sha256:52520a82eb6b8259990f4e36c2111bcf388c9b7a84fb9bf5a565344519ce081b` pinned as `openmedia-recovery:52520a82…`; old compose/env copied to root-only `/opt/openmedia/migration`; recovery override renders the pin |
| Verify + pull + preflight before stop (to 18:18:46) | Pass; old bot served throughout |
| Old stop | Signal 18:18:47.07, clean exit 18:18:50.30 (3.2 s, within 30 s grace) |
| Candidate start / health | Started 18:18:50.75; **healthy 18:19:02.27** (real Telegram poll with real credential); outage ≈15.2 s |
| Persistence | `persist_selected` + `confirm_selection` passed; selected env, running image and health agree |
| One poller | Only `openmedia-openmedia-1` in project; no `409 Conflict`/poll errors in console and no OpenMedia process on the maintainer workstation; both test requests reached this container |

**Representative real delivery (operator, private chat).** Two confirmed deliveries
received and opened by the operator; console `delivery` events:

| Case | UTC | Outcome | Bytes | Total / after selection |
|---|---|---|---|---|
| T063-LI-1 LinkedIn short link | 18:20:12 | confirmed | 4,500,310 | 6.21 s / 3.79 s |
| T063-YT-1 YouTube video | 18:22:28 | confirmed | 15,432,171 | 9.19 s / 4.39 s |

Console privacy: a scan of the complete container log found 0 URLs, 0 source host
names, 0 Telegram-ID-like or token-shaped strings. Post-delivery: healthy, restart
count 0, 45.8 MiB of 2 GiB, 3 PIDs. Diagnostics off; no diagnostic files.

**Limitations / next action.** Only Ubuntu 26.04 amd64 is accepted; the other three
supported combinations remain pending. The two deliveries are representative cases,
not the inherited I001–I006 matrix (T066). The migration case passed its forward
path only; the return path, update, rollback, failure and shutdown cases remain T064.
The previous local image and migration files are retained for that return path.

### T062 preview.6 candidate release — 2026-11-23

- gate_id / requirement_ids: F008-PUBLIC, F008-SOURCES, F008-NATIVE-AMD64,
  F008-NATIVE-ARM64, F008-RELEASE-POLICY (candidate of the baseline/candidate pair);
  FR-001–FR-004, FR-020; SC-001–SC-002.
- class: Controlled, native container and public distribution. gate_scope: Feature 008
  acceptance. result / failure_class: **pass / none** for the candidate release.
- release / source: `v0.1.0-preview.6` and matching `sources-v0.1.0-preview.6`, both
  annotated tags at commit `d938409fab897b6b0d42555fb769fb70b2911d7f` (T063 record on top
  of the preview.5 code; no runtime or release-tool change). Tag creation went through
  the maintainer ruleset bypass; no other actor can create these refs.

**Pre-tag checks (maintainer workstation, macOS arm64, Docker 29.9.3).** Controlled suite
**1167 passed, 3 live deselected** at `43cdc37` (the candidate adds only validation
records); `uv build`, `publish.audit_pins()` and `git diff --check` passed. To avoid a
repeat of preview.4's pre-push rejection, a native arm64 build of the candidate was
inventoried and every one of its **317 components resolved** against
`release/source-policy.json` (0 unreviewed). amd64-only components were left to the
pipeline's own gate. The tag pair was confirmed unused (no refs, no releases, anonymous
GHCR manifest 404) before creation.

[Release run 45238239957](https://github.com/hman-pro/openmedia/actions/runs/45238239957)
completed **success** (18:25:34–19:14:28 UTC): authority, controlled, native amd64 and
arm64, sources, source-release, promote and evidence all passed. Source-only release
**455845510** and image release **455847579** are published, immutable; the image
release is a prerelease.

| Identity | Value |
|---|---|
| Index | `ghcr.io/hman-pro/openmedia@sha256:1a500b068166d0f0ad80e73bb6b8a559fb75f476e20fba2c7cbd861c2a52700f` |
| linux/amd64 child / config | `sha256:84fd2ddf3ff045c25bb6170d3a779111406b841f3fa0e71b6c77a8e7eeeff0c7` / `sha256:c000c702410fa407385b5f867f026a627b63cedbc9686434169d18ff5489cfef` |
| linux/arm64 child / config | `sha256:c3e5e74041883ce18642b97dfec9d486aad07457c124fa0bd0b5eb2ddf6835e1` / `sha256:4aa114d4cc56f12e8c0eea0ea58789d6927fe319ae46d78fa712504df7b44c74` |
| Release manifest SHA256 | `03fa9388288642ff452b0737edd410533fe49ebe9e891e2c007429f7d84bf1dc` |
| Source manifest SHA256 | `cf477ae15109b12e5f9084a8411dab6582e47e03080d64d3efc31dff8fe42530` (1899 component records) |

**Independent verification on the deployment host** (Ubuntu 26.04 amd64, checksum-pinned
gh 2.103.3, empty GitHub/Docker configuration, no auth variables) against reviewed
checkout `d938409`: every public material and evidence asset downloaded anonymously
(files whose hashes exactly matched preview.5's were hard-linked rather than
re-downloaded), `validate_release.py verify` passed on the real local bundles and
SHA256SUMS matched.

**Pair status.** preview.5 (accepted 2026-11-17) is the baseline and preview.6 the
candidate; each passed its own complete gated pipeline. Earlier boundary evidence is
unchanged: preview.4's pre-push rejection wrote zero images; preview.2/3 post-push
failures kept their drafts INCOMPLETE with sources retained. T062 is completed by this
record together with the T064 update/rollback between the pair, which shows they are
compatible on the real host.

### T064 run 1 — real-host update, rollback, failure and shutdown — 2026-11-24

- gate_id / requirement_ids: F008-UPDATE, F008-SHUTDOWN (and the return path of the T063
  root-Compose migration); FR-011–FR-015, FR-019, FR-021; SC-003, SC-005–SC-006.
- class: Deployment-network/manual. gate_scope: Feature 008 acceptance.
- result / failure_class: **F008-UPDATE fail** (run 1) — one deployment regression
  (console token leak) and one unclassified failure (interrupted start left a container
  running). **F008-SHUTDOWN pending** — the executed cases passed, stale-callback reuse
  was not exercised. Register rows stay pending; T064 stays open.
- release / platform: baseline `v0.1.0-preview.5` index
  `ghcr.io/hman-pro/openmedia@sha256:2262f99c6580a2b2c4d60911febb5bb4180b4330329ae39878f5115e7d4b6b81`;
  candidate `v0.1.0-preview.6` index
  `ghcr.io/hman-pro/openmedia@sha256:1a500b068166d0f0ad80e73bb6b8a559fb75f476e20fba2c7cbd861c2a52700f`
  (source `d938409fab897b6b0d42555fb769fb70b2911d7f`); old root-Compose content
  `sha256:52520a82eb6b8259990f4e36c2111bcf388c9b7a84fb9bf5a565344519ce081b` pinned as
  `openmedia-recovery:52520a82…`. linux/amd64.
- environment: the T063 host (Ubuntu 26.04.1 LTS amd64, Docker Engine 29.10.0, Compose
  v5.8.0), residential outbound network, no inbound ports. Runbook inputs from a staged
  copy of `d938409`; its `deploy/README.md` is byte-identical to the current tree
  (SHA256 `9e13ddeb…73ba2b`).

**Method.** One interactive runner (`t064.sh`, operator-started because sudo is
operator-only) sourced the guide's extracted shell blocks verbatim: 03/08 (functions),
09 (update), 11 (rollback), 13/15/16 (old-project migration and return). Each case logged
Docker container events, the running/selected identity and the console delivery events.
The operator performed the real Telegram requests in a private chat. Fake credentials for
the incompatible-previous cases lived in separate secret files; the real token file was
never modified. Log retained on the host outside Git:
`~/openmedia-008-acceptance/logs/t064-20261124T182619Z.log` (18:26:19–18:53:56 UTC).

**Results (UTC).** Outage = old container `kill` event to new `health_status: healthy`.

| Case | Contract transition | Outcome | Evidence |
|---|---|---|---|
| N1 failed verification | Update refused before stop | **pass** | Block 09 with preview.6 digest under preview.5 identity: `Release check failed`, exit 1; same container running; selection unchanged |
| N2 non-digest selection | Refused before any Docker call | **pass** | `dc` with a tag reference: exit 2, `Select a verified digest-qualified OpenMedia image first`; same container running |
| N3 unavailable digest | Failed pull leaves old running | **pass** | Config + pull of a nonexistent digest: `not found`, exit 1; same container running; selection unchanged |
| U1 update 5 → 6 | Verify, pull, preflight, stop old, start, persist | **pass** | Exit 0; preflight `configuration valid (token=<redacted> …)` before stop; kill 18:31:20.390 → healthy 18:31:32.641, outage **12.25 s**; selected = running = preview.6 |
| SD active-work shutdown | Stop ≤20 s, no children, no repeated uncertain send | **pass** (stale callback not exercised) | Stop issued at app stage `sending`; kill 18:34:00.472 → exit 0 at 18:34:03.621 (**3.15 s**, wall 3.4 s); console ends `openmedia: stopped (reason=signal)`; host scan for yt-dlp/ffmpeg/ffprobe/deno: none; interrupted file arrived: **none** |
| RB rollback 6 → 5 | Explicit rollback with current settings/credential | **pass** | Block 11 exit 0; kill 18:38:48.550 → healthy 18:39:02.131, outage **13.58 s**; selected = running = preview.5 |
| MP missing previous | Fails clearly, nothing running | **pass** | Block 11 to an unpublished digest: `No such image` then pull `not found`, exit 1; nothing running; selection still preview.5. Explicit recovery start of preview.5: exit 0, confirmed |
| IC-a malformed credential | Local preflight prevents start | **pass** | `configuration error: TELEGRAM_BOT_TOKEN_FILE: invalid token shape`, exit 2; nothing running |
| IC-b Telegram-rejected credential | Failed start stopped explicitly | **stop: pass; privacy: fail** | Preflight passes, Telegram rejects at startup, `start_checked` stops the unhealthy container and exits 1 after 3 s; nothing running; selection unchanged. **Console printed the full fake token** (scan count 1) — see defect 1 |
| IS interrupted start | Interrupted start stopped explicitly | **fail** | TERM to `start_checked` and its descendants ~2 s after container start: exit 143 as expected, but a preview.6 container was left running (`health=starting`, started 18:40:41.382) — see defect 2 |
| IR migration return | Return to the pinned old local image | **pass** | Blocks 13/16 exit 0; healthy 18:40:57.682 on `openmedia-recovery:52520a82…`. Starting state was the leftover IS preview.6 container, not preview.5; the block's stop removed it |
| MR remigration old → 6 | Old local project to selected preview.6 | **pass** | Block 15 exit 0; kill 18:46:44.127 → healthy 18:46:56.431, outage **12.30 s**; selection persisted |

**Real deliveries after each transition** (console `delivery` events, all `confirmed`):

| Case ID | After | Platform | Bytes | Total / after selection |
|---|---|---|---|---|
| T064-U1-YT | U1 (preview.6) | YouTube | 19,753,883 | 9.82 s / 4.97 s |
| T064-SD-YT | SD restart (preview.6) | YouTube | 20,484,732 | 12.05 s / 6.99 s |
| T064-RB-YT | RB (preview.5) | YouTube | 4,290,348 | 8.02 s / 3.99 s |
| T064-IR-YT | IR (old image) | YouTube | 12,128,982 | 55.42 s / 3.84 s (operator delay before selection) |
| T064-MR-LI | MR (preview.6) | LinkedIn | 12,421,583 | 6.94 s / 3.49 s |

**Defect 1 — console token leak (deployment regression, blocks completion).** When
Telegram rejects the token at startup, `run_with_diagnostics` re-raises the exception
(`src/openmedia/__main__.py:565`, bare `raise`). Python's default excepthook then prints
the chained traceback to stderr, bypassing the redacting console handler. PTB's own
`InvalidToken` message embeds the token, so the console shows it unredacted. The logged
copy from PTB's retry loop is correctly `<redacted>`. Only the fake test token was
exposed. preview.5 and preview.6 carry the same code. Fix needs a code change and a new
release (preview.7), then a rerun of the update/rollback pair and IC-b.

**Defect 2 — interrupted start left a container (unclassified).** After TERM, Compose
began `Gracefully Stopping`; events show stop/die 18:40:41.060, destroy 41.363, then a
new start 41.500. The guide's next `start_checked` refused to start preview.5 because a
container was running (exit 1), so no second poller ran. Cause unproven: the runner
sent TERM to every descendant (sudo and Compose) at once, which is harsher than an
operator's single Ctrl-C to the foreground process group. Next action: reproduce with a
real interactive Ctrl-C before changing the guide's traps.

**Not executed in run 1.** Update-path preflight failure with the old bot still running
(IC-a used the rollback block, which stops first by design); timed-out start (180 s
health wait); persistence failure (duplicate `OPENMEDIA_IMAGE` line); stale-callback tap
after restart (the interrupted YouTube card was automatic, with no buttons); explicit
scratch/upload leakage inspection after SD (scratch is container tmpfs, removed on
recreate, but not separately inspected).

**End state.** preview.6 running and selected (container `abcffc39f6be`, healthy); old
migration files and the recovery pin retained for later reruns.

### T064 interrupted-start reproduction (IS) — 2026-11-25

- gate_id / requirement_ids: F008-UPDATE (interrupted start); FR-012–FR-013, FR-019; SC-005.
- class: Deployment-network/manual. gate_scope: Feature 008 acceptance.
- result / failure_class: **pass / none** for the guide's interrupted-start cleanup.
  Run 1's IS failure is reclassified as a test-runner artifact; its record is kept
  unchanged. F008-UPDATE stays failed until the preview.7 rerun (defect 1).
- release / platform: `v0.1.0-preview.6` index
  `ghcr.io/hman-pro/openmedia@sha256:1a500b068166d0f0ad80e73bb6b8a559fb75f476e20fba2c7cbd861c2a52700f`,
  linux/amd64. Guide functions (blocks 03, 08) from the staged `d938409` checkout.
- environment: the T063/T064 host (Ubuntu 26.04.1 LTS amd64, Docker Engine 29.10.0,
  Compose v5.8.0, sudo-rs 0.2.13), operator interactive SSH shell.

**Method.** The operator sourced blocks 03 and 08 in an interactive shell and ran
`stop_selected "$P6"; start_checked "$P6"; echo "exit=$?"`, pressing Ctrl-C once,
about 1 s after the new container started. This is the operator action the guide's traps
are designed for, unlike run 1's runner, which sent TERM to `start_checked` and to all of
its descendants (sudo and Compose) at once.

**Result (UTC).** Console: `^CGracefully Stopping...`, container stopped, then the
EXIT trap's `stop_selected` ran (`[+] stop … Stopped`), **`exit=130`**. Docker events:

| UTC | Event |
|---|---|
| 17:45:46.204 → 17:45:49.426 | kill, stop, die (`stop_selected` of the running bot) |
| 17:45:49.720 → 17:45:49.882 | create, destroy, rename, start (`up --force-recreate`) |
| 17:45:50.826 → 17:45:50.983 | kill, stop, die (interrupt cleanup) |
| 17:45:50.983 → 17:47:05.520 | **no container event** — nothing left running |
| 17:47:05.520 → 17:47:17.200 | create, destroy, rename, start, healthy (operator recovery, standalone `start_checked`) |

Two earlier attempts (17:42:52 and 17:45:23) reached `healthy` before the interrupt
landed and are not counted. Service outage for the counted attempt: 17:45:46.2 → 17:47:17.2
(91 s, operator-paced).

**Run 1 comparison.** Run 1's events continued after the interrupt stop with destroy
(18:40:41.363) and a new start (18:40:41.500), leaving a container. A single Ctrl-C ends
at `die`. The double delivery (direct TERM plus sudo's relay) made Compose take its
second-signal force path. Next action: in the preview.7 rerun, IS becomes an operator
prompt with a real Ctrl-C instead of a scripted descendant kill.

**Errexit restriction observed.** During recovery the operator twice ran
`start_checked "$P6" && confirm_selection "$P6" && …` (shortly after 17:43:08, and at 17:48:54). Both times
Compose force-recreated the running, healthy bot (create before kill) instead of the
guard refusing. This is the documented behavior: Bash disables errexit inside a function
called from an `&&` list, which skips every `test` in `start_checked`. The guide already
forbids this form (`deploy/README.md`, before the function definitions). The standalone
form refused correctly in run 1 (IS recovery exit 1). One container ran throughout; end
state is preview.6 healthy and selected.

**Correction — 2026-11-26.** The end state above held only until 17:50:39. The operator
session then ran the interrupted-start sequence a fourth time (`stop` at 17:50:39,
`up --force-recreate` at 17:50:40, interrupt cleanup `stop` at 17:50:41, container exit
143) without a recovery start afterwards. The guide again behaved as designed (nothing
left running), but the bot was **down from 17:50:41 until 2026-11-26 07:23 UTC**
(about 13.5 h), unnoticed until preview.7 staging found no running container. Recovered
with a standalone `start_checked` and `confirm_selection` (exit 0): preview.6 healthy and
selected. The T064 runner now refuses to start unless the base image is running healthy,
and its "same container running" check no longer treats "nothing before and after" as
a match. Unattended host monitoring remains an open operations follow-up.

### Preview.7 pre-tag checks and librsvg policy review — 2026-11-25

- gate_id / requirement_ids: F008-RELEASE-POLICY, F008-SOURCES (pre-tag, controlled);
  FR-002, FR-004; SC-002.
- class: Controlled. gate_scope: Feature 008 acceptance. result / failure_class:
  **pre-tag checks pass after one reviewed policy addition / none**. This is not a
  release run; preview.7 publication gates remain pending.
- release / platform: candidate source = this branch after the T064 token-redaction fix
  `1f00ea4`; native linux/arm64 image built locally without cache
  (`docker build --no-cache --pull`), image `sha256:7156998b…`, inventoried config
  `sha256:d2842f275b0d177aacfb9efbe382cebd8e8fe50cc660de70bb1a7dc6b68706f7`.
- environment: maintainer workstation, macOS arm64, Docker 29.9.3.

**Checks.** Controlled suite **1168 passed, 3 live deselected**; `uv build`,
`publish.audit_pins()` and `git diff --check d938409..HEAD` passed; no
`*-v0.1.0-preview.7` tags exist. A first arm64 build reused cached APT layers and was
discarded, because cached layers would report package versions from an earlier build,
not the ones CI installs. The no-cache inventory resolved **316 of 317** components;
the sole unresolved entry was `debian:librsvg2-2@2.54.7+dfsg-1~deb12u2`, a Debian LTS
security revision published the same day (DLA-4936-1, CVE-2026-96889). After the
packaging review in research.md and the exact policy addition (retaining `~deb12u1`),
the same inventory resolves **317 of 317**; `tests/integration/test_release_tools.py`
**32 passed** and the full controlled suite still **1168 passed**.

**Limitations / next action.** Only arm64 was inventoried; amd64 resolution is first
proved by the release pipeline's native job. Tag the preview.7 pair only after this
record and the fix are pushed; a newer Debian revision before tagging would need the
same review.

### T062 preview.7 candidate release — 2026-11-25

- gate_id / requirement_ids: F008-PUBLIC, F008-SOURCES, F008-NATIVE-AMD64,
  F008-NATIVE-ARM64, F008-RELEASE-POLICY (candidate of the preview.6/preview.7 pair);
  FR-001–FR-004, FR-020; SC-001–SC-002.
- class: Controlled, native container and public distribution. gate_scope: Feature 008
  acceptance. result / failure_class: **pass / none** for the candidate release.
- release / source: `v0.1.0-preview.7` and matching `sources-v0.1.0-preview.7`, both
  annotated tags at commit `80c72fa21a05746c8b622886b53ca5fa3ae56c05` (token-redaction fix
  `1f00ea4` plus the reviewed librsvg policy entry).

**Before tagging.** The branch was pushed first. Branch CI built both native
architectures and collected sources from both inventories: PR run
[45684760327](https://github.com/hman-pro/openmedia/actions/runs/45684760327) passed every
job, which first proved amd64 resolution (no further policy entry needed). The push run
[45684744235](https://github.com/hman-pro/openmedia/actions/runs/45684744235) of the same
commit failed `sources` on a `RemoteDisconnected` while downloading the last component
(`unmanaged:deno@2.9.6`); `download_url` makes a single attempt, so one dropped
connection fails the job. A bounded retry is a release-code change and is left as a
follow-up.

[Release run 45687934499](https://github.com/hman-pro/openmedia/actions/runs/45687934499)
completed **success** (19:43:05–20:29:37 UTC, attempt 1): authority, controlled, native
amd64 and arm64, sources, source-release, promote and evidence all passed. Source-only
release **458596790** and image prerelease **458598906** are published and immutable.

| Identity | Value |
|---|---|
| Index | `ghcr.io/hman-pro/openmedia@sha256:8c27c75f1808ca97de8aeb0b0ab726d0b008f918ec43b1a1c979247f0b578cc6` |
| linux/amd64 child / config | `sha256:b9a8141074dbe71e8a0cc1f6dd0d4914425b9b18256308d860848a4411f2c835` / `sha256:ea06b8358c4ddbfb78ff3bd5d3230f95ee93aa0c34a60de565c1d2f391bfa31d` |
| linux/arm64 child / config | `sha256:31fbe11c7790eb1c63e1e695fb782d6bd4f4ea91a1b4cfd0cbf94b23d9bcbfaa` / `sha256:cac9890d46e5d725f16117f459eadf4d5fcadeedf825a1b03bad2c97871ade03` |
| Release manifest SHA256 | `6ffb085a3022a5e22099e2a35d11383219e5f241702746c6f93631ed0e20a4d7` |
| Source manifest SHA256 | `0f20de869297a6f1535b3d44afbaaba05e17691ca5d04b86ab968d43c3fc4ca6` (1899 component records) |

The CI-built arm64 config (`cac9890d…`) differs from the workstation pre-tag build
(`d2842f27…`), as expected for separate builds; only the CI archive is promoted.

**Independent verification on the deployment host** (2026-11-26, Ubuntu 26.04 amd64,
checksum-pinned gh 2.103.3, empty GitHub/Docker configuration, no auth variables)
against a `git archive` of `80c72fa`: every public material and evidence asset
downloaded anonymously (`notices.tar.gz` hard-linked from preview.6 after an exact
hash match), `validate_release.py verify` passed on the real local bundles and
SHA256SUMS matched. The staged `deploy/README.md` is byte-identical to preview.6's
(SHA256 `9e13ddeb…73ba2b`), so the extracted guide blocks are unchanged.

### T064 run 2 — real-host update, rollback, failure and shutdown — 2026-11-26

- gate_id / requirement_ids: F008-UPDATE, F008-SHUTDOWN (and the return path of the T063
  root-Compose migration); FR-011–FR-015, FR-019, FR-021; SC-003, SC-005–SC-006.
- class: Deployment-network/manual. gate_scope: Feature 008 acceptance.
- result / failure_class: **F008-UPDATE pass / none**; **F008-SHUTDOWN pass / none**
  on Ubuntu 26.04 amd64. Run 1's defect 1 is fixed (IC-b) and its defect 2 was a runner
  artifact (IS, 2026-11-25 reproduction and below).
- release / platform: baseline `v0.1.0-preview.6` index
  `ghcr.io/hman-pro/openmedia@sha256:1a500b068166d0f0ad80e73bb6b8a559fb75f476e20fba2c7cbd861c2a52700f`;
  candidate `v0.1.0-preview.7` index
  `ghcr.io/hman-pro/openmedia@sha256:8c27c75f1808ca97de8aeb0b0ab726d0b008f918ec43b1a1c979247f0b578cc6`
  (source `80c72fa`); old root-Compose content pinned as `openmedia-recovery:52520a82…`.
  linux/amd64.
- environment: the T063 host (Ubuntu 26.04.1 LTS amd64, Docker Engine 29.10.0, Compose
  v5.8.0, sudo-rs), residential outbound network, no inbound ports.

**Method.** As run 1, with a revised runner: guide blocks 03/08/09/10/11/13/15/16
sourced verbatim from the staged `80c72fa` checkout; Docker events, running/selected
identity and console delivery events logged per case; real Telegram requests by the
operator in a private chat; fake credentials only in separate secret files, the real
token file never modified. New cases: UP, ST, TO, MRPE. The runner refuses to start
unless the base runs healthy and selected, and its "same container running" check
treats "nothing running" as a mismatch. Log retained on the host outside Git:
`~/openmedia-008-acceptance/logs/t064-20261126T075845Z.log` (07:58:45–08:36:56 UTC).

**Results (UTC).** Outage = old container `kill` event to new `health_status: healthy`.

| Case | Contract transition | Outcome | Evidence |
|---|---|---|---|
| N1 failed verification | Update refused before stop | **pass** | Block 09 with the preview.7 digest under preview.6 identity: exit 1; same container running; selection unchanged |
| N2 non-digest selection | Refused before any Docker call | **pass** | `dc` with a tag reference: exit 2; same container running |
| N3 unavailable digest | Failed pull leaves old running | **pass** | exit 1; same container running; selection unchanged |
| UP update-path preflight failure | Preflight failure leaves old running | **pass** | Block 09 with a malformed credential setting: verify passed, preflight `invalid token shape`, exit 2; preview.6 container unchanged; selection unchanged; real setting restored |
| U1 update 6 → 7 | Verify, pull, preflight, stop old, start, persist | **pass** | Exit 0; kill 08:06:13.230 → healthy 08:06:25.525, outage **12.30 s**; selected = running = preview.7 |
| SD active-work shutdown | Stop ≤20 s, no children, no repeated uncertain send | **pass** | Stop at app stage `downloading`; kill 08:09:18.254 → exit 0 at 08:09:21.648 (**3.39 s**, wall 3.64 s); console ends `openmedia: stopped (reason=signal)`; host scan for yt-dlp/ffmpeg/ffprobe/deno: none; interrupted file arrived: **none** |
| ST stale callback | Card from before a restart does not deliver | **pass** | Card with choices left untapped across a stop/start (healthy 08:11:58.462, confirm 0); the tap showed "This choice is stale. Submit the link again for current choices"; files arrived: **none** |
| RB rollback 7 → 6 | Explicit rollback with current settings/credential | **pass** | Block 11 exit 0; kill 08:12:53.464 → healthy 08:13:06.974, outage **13.51 s**; selected = running = preview.6 |
| MP missing previous | Fails clearly, nothing running | **pass** | Block 11 to an unpublished digest: `No such image`, pull `not found`, exit 1; nothing running; selection still preview.6. Explicit recovery: exit 0, confirm 0 |
| IC-a malformed credential | Local preflight prevents start | **pass** | `invalid token shape`, exit 2; nothing running |
| IC-b Telegram-rejected credential | Failed start stopped; console redacted | **pass** | Preflight passed, Telegram rejected at startup, `start_checked` stopped the unhealthy container, exit 1 after 3 s; nothing running. Console: ``telegram.error.InvalidToken: The token `<redacted>` was rejected by the server.``; fake-token scan **0**, redacted mentions 2 |
| TO timed-out start | Finite health wait, candidate stopped | **pass** | Container start 08:14:20.743; Telegram dropped both ways for containers (`DOCKER-USER`, 149.154.160.0/20) at 08:14:25.801; `application not healthy after 3m0s`, kill 08:17:20.839, stop 08:17:25.991; `start_checked` exit 1 after 186 s; nothing running; rules removed; recovery exit 0, confirm 0 |
| IS interrupted start | Interrupted start stopped explicitly | **pass** (second attempt) | Runner attempt inconclusive (healthy 08:17:54.681 before any interrupt; runner stopped it, recovery confirm 0). Operator shell, blocks 03/08, `stop_selected`/`start_checked` with preview.7 and one Ctrl-C: start 08:40:26.199, kill 08:40:26.994, die 08:40:27.136, **exit=130**; no container event until the recovery start 08:40:46.750, healthy 08:40:58.412 |
| IR migration return | Return to the pinned old local image | **pass** | Blocks 13/16 exit 0; kill 08:18:11.734 → healthy 08:18:28.478 (**16.74 s**) on `openmedia-recovery:52520a82…` |
| MRPE remigration with persistence error | Old → candidate; failed persistence is reported, bot keeps serving | **pass** | Two `OPENMEDIA_IMAGE` lines in the protected settings; block 15 verified, pulled, preflighted, kill 08:30:39.240 → healthy 08:30:51.466 (**12.23 s**), then `Expected exactly one OPENMEDIA_IMAGE setting; selection not persisted`, exit 1, candidate healthy. Guide recovery (correct settings, `persist_selected`, `confirm_selection`): 0 / 0 |

**Real deliveries after each transition** (console `delivery` events, all `confirmed`):

| Case ID | After | Platform | Bytes | Total / after selection |
|---|---|---|---|---|
| T064R2-U1-YT | U1 (preview.7) | YouTube | 14,669,495 | 8.96 s / 4.08 s |
| T064R2-SD-YT | SD restart (preview.7) | YouTube | 19,644,478 | 11.67 s / 4.91 s |
| T064R2-RB-YT | RB (preview.6) | YouTube | 9,947,200 | 10.56 s / 4.44 s |
| T064R2-IR-YT | IR (old image) | YouTube | 2,872,018 | 7.40 s / 3.59 s |
| T064R2-MR-LI | MRPE recovery (preview.7) | LinkedIn | 4,326,429 | 6.13 s / 3.53 s |

**Scratch and upload cleanup.** Scratch exists only in the container's `/tmp` tmpfs
(`deploy/compose.yaml`: `read_only: true`, `tmpfs: /tmp … size=536870912`; the only
host mount is the read-only secret). Docker discards a tmpfs when its container stops,
and SD's restart destroyed the stopped container (destroy 08:09:22.124). No host path
can hold scratch or partial uploads; the stopped container's tmpfs was not inspected
separately.

**One poller.** At most one `openmedia-openmedia-1` container ran at any time in the
event log; no `409 Conflict` appeared in any console excerpt.

**End state.** preview.7 running and selected (container `392f8b22020d`, healthy since
08:40:58); a separate `confirm_selection` with the preview.7 digest after the IS
recovery returned 0 (selected = running). Migration files and the recovery pin are
retained until T065.

### T065 maintenance acceptance — 2026-11-26/27

- gate_id / requirement_ids: F008-OPERATIONS (cases OP-INSPECT … OP-RESTORE);
  FR-008–FR-010, FR-015–FR-017, FR-019, FR-021; SC-003–SC-004, SC-007.
- class: Deployment-network/manual. gate_scope: Feature 008 acceptance.
- result / failure_class: **F008-OPERATIONS pass / none** on Ubuntu 26.04 amd64. Every
  OP case passed; the runner faults below are acceptance-harness defects, not
  deployment regressions. One guide finding (empty rotation input) was fixed after
  the run.
- release / platform: `v0.1.0-preview.7` index
  `ghcr.io/hman-pro/openmedia@sha256:8c27c75f1808ca97de8aeb0b0ab726d0b008f918ec43b1a1c979247f0b578cc6`
  (source `80c72fa`), selected and running throughout. Guide blocks were extracted from
  `4ef5dcc`, whose `deploy/README.md` differs from `80c72fa` only in the OP-EXIT
  command (block 25). linux/amd64.
- environment: the T063/T064 host (Ubuntu 26.04.1 LTS amd64, Docker Engine 29.10.0,
  Compose v5.8.0, sudo-rs), residential outbound network, no inbound ports.

**Host choice.** T065 ran on the production host by operator choice (plan.md, "Phase 7
maintenance acceptance host adjustment"): the bot's outages are tolerable, and each
case keeps its isolation as plan.md describes (OP-OUTAGE disconnects only the bot
container from its Compose network; OP-REMOVE inventories unrelated services before
and after).

**Method.** A runner (`~/openmedia-008-acceptance/t065.sh`, outside Git) sourced guide
blocks 03/08 and each case's block verbatim, logged Docker events, running/selected
identity and console delivery events, and scanned every captured output for
token-shaped strings, URLs and identifier keys. Sessions: A (2026-11-26
10:02:36–10:14:31), A2 (10:25:39 and 10:36:03), R (13:54:53 and 13:59:32), B1/B2/B3
(14:13:45–14:19:10), C (2026-11-27 07:45:50–07:49:02 UTC). Real Telegram requests were
sent by the operator in a private chat; token replacements came from BotFather
`/revoke`. Logs retained on the host outside Git (`logs/t065-*.log`).

| Case | Outcome | Evidence |
|---|---|---|
| OP-INSPECT | **pass** | Blocks 17/18: privacy scan of all inspection output token-shaped 0, URLs 0, identifier keys 0; same single container afterwards, 0 containers created; `mem_limit` 2,147,483,648 with the 512 MiB `/tmp` tmpfs counted inside it |
| OP-DIAGNOSTICS-OFF | **pass** | Setting `0`; local validation `diagnostic_log=off`, exit 0; host diagnostics directory absent; 0 entries under in-container `/var/log/openmedia`; only mount is the read-only secret |
| OP-DIAGNOSTICS-ON | **pass** (limits below) | Block 19 exit 0; validation `diagnostic_log=on (/var/log/openmedia)`; directory `10001:10001 700`, today's file `10001:10001 600`; real delivery traced, 1 refusal entry, 0 token-shaped strings in the file; console scan 0/0/0 while on; 70 s idle (two healthcheck intervals) left the file at 12,212 bytes; file kept across recreation (12,870 bytes); after disable the only mount is the secret. Retention with 16 seeded day files of 4,000,000 bytes each: today plus the 12 newest seeds kept (2026-11-14…11-25); seeds 14–16 days old removed by age (11-10…11-12) and the 13-day seed (11-13) by size, since 13 × 4,000,000 bytes exceeds 50,000,000 |
| OP-EXIT | **pass** | Block 25 (`os.kill(-1, SIGKILL)` inside the container, about 100 s after start): die 10:10:44.477 → start 10:10:44.684, same container, restarts 0 → 1, healthy after 13 s with no `up`/`start`; 1 project container |
| OP-OUTAGE | **pass** (A2) | Block 28 disconnected only the bot container at 10:25:40; `health_status: unhealthy` 10:28:16.753; runner reconnected at 10:28:36 (176 s); healthy again 42 s later; same container, StartedAt and restart count unchanged |
| OP-ROTATE | **pass** (R, second run) | Block 21 with a new BotFather token via `sudoedit`: exit 0; kill 14:00:13.746 → healthy 14:00:32.831 (**19.1 s**); new container, local validation `token=<redacted>`; 0 temporary token files left; secret `root:10001 640`; log and console token scans 0; no editor swap or temporary copies under `~`, `/tmp`, `/var/tmp`; `~/.viminfo` and shell history token scans 0 |
| OP-ROTATE-FAIL | **pass** | Malformed input: `invalid token shape`, exit 2, service stopped (kill 10:14:26.322). Telegram-rejected input from the stopped state: preflight passed, startup rejected, exit 1, stopped; fake-token console scan 0, 2 `<redacted>` mentions. Empty input (A2 operator error): `TELEGRAM_BOT_TOKEN_FILE: empty content`, exit 2, stopped, 0 temporary files. Corrected current input from the stopped state (block 21 without its initial confirmation): health passed twice (10:21:06 and 12:25:19) and real deliveries followed each |
| OP-REBOOT | **pass** | Boot ID changed; Engine active 14:14:08; same container `5ae554f8…` started 14:14:07.790, first passing probe ended 14:14:25.356 (**17 s** after Engine availability); restarts 0, no `up`/`start`; 1 running project container |
| OP-STOP | **pass** | Block 27 stopped the bot (14:15:27) with the container retained, then rebooted; boot ID changed; Engine active 14:15:49; no running project container at any 5 s poll through 188 s after Engine availability; retained container still `Exited (0)`; deliberate `start_checked` + `confirm_selection` exit 0, healthy within 13 s |
| OP-BACKUP | **pass** | Mount `/mnt/openmedia-encrypted-backup` on `/dev/mapper/openmedia-backup`: LUKS2, `aes-xts-plain64`, 512-bit key, file-backed loop device, mount root `root:root 700`; block 22 exit 0; backup directory `700 root:root` holding `compose.yaml`, `deploy.env`, `telegram_bot_token` and the runner's version/digest/revision record, each `600 root:root` (operator listing); no media, diagnostics or request files. The vault was closed afterwards |
| OP-REMOVE | **pass** | Block 24 exit 0: removed the project container and `openmedia_default` network only; running-service and non-project container inventories identical before and after; retained inventory `compose.yaml`, `deploy.env`, `migration/`, `secrets/` and all images (preview.5/.6/.7, recovery pin, local builds) |
| OP-RESTORE | **pass** | `/opt/openmedia` moved aside to start from an empty destination; 0 project containers; operator confirmed no other poller; block 23 exit 0 from the backup, block 04 pull and preflight exit 0, block 05 exit 0, `confirm=0`; modes: directory `root:0 750`, `compose.yaml` 640, `deploy.env` 600, `secrets/` 700, token `root:10001 640`; kill 07:46:25.836 → healthy 07:47:06.531 (40.7 s). A card left untapped before removal showed "stale" after restore: no request resumed |

**Real deliveries after each transition** (console `delivery` events, all `confirmed`):

| Case ID | After | Platform | Bytes | Total / after selection |
|---|---|---|---|---|
| T065-DIAG-YT | Diagnostics on | YouTube | 22,847,091 | 11.50 s / 6.31 s |
| T065-EXIT-YT | OP-EXIT recovery | YouTube | 4,191,972 | 6.13 s / 3.53 s |
| T065-OUT-YT | OP-OUTAGE recovery (A2) | YouTube | 3,423,844 | 8.42 s / 3.67 s |
| T065-RFIX-LI | Corrected input, 12:25 | LinkedIn | 18,914,866 | 15.10 s / 11.88 s |
| T065-ROT1-YT | First R rotation (token later revoked) | YouTube | 1,770,015 | 7.77 s / 3.72 s |
| T065-ROT2-YT | OP-ROTATE (R, second run) | YouTube | 3,905,936 | 7.41 s / 3.77 s |
| T065-RB-YT | OP-REBOOT | YouTube | 27,118,621 | 14.65 s / 5.93 s |
| T065-STOP-YT | OP-STOP restart | YouTube | 11,417,888 | 8.36 s / 3.88 s |
| T065-REST-YT | OP-RESTORE | YouTube | 36,845,469 | 22.83 s / 13.31 s |

**One poller.** At most one `openmedia-openmedia-1` container ran at any time in the
event logs; the operator stopped `scripts/dev.sh` before OP-RESTORE.

**Guide fix found by T065.** The original OP-EXIT command killed PID 1 from inside the
container. With `init: true`, PID 1 is the init, and the kernel ignores SIGKILL sent to
a namespace's init from inside it, so the command did nothing. `4ef5dcc` kills every
other process instead (`os.kill(-1, SIGKILL)`). The published preview.7 `deploy/README.md`
still carries the old command; T067 reconciles it.

**Guide finding (fixed after T065).** Block 21 moved the edited replacement over the live
token file before local validation. An unchanged or empty edit (sudoedit exits 0)
therefore stopped a healthy bot and emptied the token file, and validation then refused
to start. The failure is safe and reported (exit 2, stopped, no temporary files), and a
healthy bot should not be stopped by it. The block now ends before `stop_selected` when
the replacement is empty (`sudo test -s`), pinned by
`tests/contract/test_deploy_guide_rotation.py`, which runs the block against stub host
commands.

**Runner faults and their outages.** All were acceptance-harness defects, fixed and
followed by valid reruns:

1. Session A: nano could not start under the host's unknown `xterm-ghostty` terminal type,
   so the real OP-ROTATE `sudoedit` exited 1 before any stop. The runner continued into
   the scripted OP-ROTATE-FAIL cases, which replaced the real token file. The bot was
   down 10:14:26–10:21:06 until the operator installed a newly revoked token. Fixed:
   terminal-type fallback, halt after a failed rotation.
2. Session A OP-OUTAGE was invalid: its Enter was consumed 21 s after the disconnect,
   before health went unhealthy. Fixed: the runner presses Enter 15 s after unhealthy;
   rerun in A2.
3. Session A diagnostics and session C backup checks globbed inside 0700 directories
   without privilege, so byte totals, line counts and backup modes went unrecorded. The
   retention outcome is from the privileged file inventory; the backup modes are from
   the operator's privileged listing. Fixed for diagnostics (privileged `find`).
4. A2 OP-ROTATE: the whole BotFather message was pasted into nano and the edit left
   unsaved, giving the empty-input refusal above. The bot was down 10:35:42–12:25:19
   until the corrected input was installed. The editor became vim (`SUDO_EDITOR`).
5. Session R, first run: the runner tee'd the terminal into its log, so the vim screen
   carried the pasted token into the log. The token reached the log file, the operator's
   terminal and the coding assistant's session transcript (sent to its model API). It was redacted from the
   log and revoked by the second R rotation at 14:00:13. Fixed: the editor runs on
   `/dev/tty`, outside the logged stream; the second run's log scan is 0.
6. Session B2 passed `@epoch` to `docker events --since`, which Docker rejects, so the
   17 s reboot timing was read from the container's health probe log. Fixed.

**Limitations.**
- Both retention rules fired: age (14+ days) and size (the 13-day seed could only go by
  the 50,000,000-byte limit). The runner's byte totals failed (unprivileged), so the held
  total (12 × 4,000,000 bytes plus today's file) is inferred from the seed size and the
  surviving file list, not measured. Retention runs when a new day's file is opened, so a process running across midnight
  applies it at that point.
- One host combination (Ubuntu 26.04 amd64). Other combinations stay pending.
- The backup is a file-backed LUKS2 container on the same disk. It proves the guide
  procedure, not off-host recoverability.

**End state.** preview.7 running and selected (container `562e6b22fccd`, healthy since
07:47:06 on 2026-11-27, restarts 0). The old root-Compose `migration/` directory,
including its revoked credential, was deleted with the moved-aside pre-removal copy
after the successful restore. The diagnostics directory was removed before session C.
Still on the host: the recovery pin `openmedia-recovery:52520a82…`,
`openmedia:local`, `~/openmedia/.env`, and the closed encrypted vault holding a copy of
the current token.

### T066 S0 — container gates and live source suite — 2026-11-27

- gate_id / requirement_ids: I001-RUNTIME, I005-CONTAINER, I006-CONTAINER, I001-SOURCES,
  I005-LIVE (inherited stable-readiness obligations).
- class: Native container (running deployment) and Deployment-network/manual.
  gate_scope: Inherited stable-readiness obligation.
- release / platform: `v0.1.0-preview.7` index
  `ghcr.io/hman-pro/openmedia@sha256:8c27c75f1808ca97de8aeb0b0ab726d0b008f918ec43b1a1c979247f0b578cc6`
  (labels `org.opencontainers.image.version=v0.1.0-preview.7`, revision `80c72fa`),
  linux/amd64. The live suite ran from a checkout of `a9a0f9d`, whose `src/`,
  `pyproject.toml` and `uv.lock` are identical to `80c72fa`.
- environment: production host (Ubuntu 26.04.1 amd64, Engine 29.10.0, Compose v5.8.0)
  for the container checks. The live suite ran on the operator's Mac on the same LAN,
  with the same public egress address as the host (compared by hash). The host has no
  `uv`. Instaloader 4.15.3.

**Container checks (running container `562e6b22fccd`, healthy since 07:47:06, restarts 0).**
User 10001:10001; read-only root (`touch /probe` refused); `init: true`; capabilities
effective and bounding sets 0, `cap_drop: ALL`, `no-new-privileges`, not privileged; no
published ports; 2 CPUs (`NanoCpus` 2,000,000,000), memory 2 GiB, `/tmp` tmpfs 512 MiB
`noexec,nosuid`; json-file logs 3 × 10 MB; restart `unless-stopped`; only mount the
read-only token file. In the image: package `openmedia 0.1.0`; `import regex,
openmedia.media_titles` succeeds (regex 2026.8.31); `/app/LICENSE`,
`/app/THIRD_PARTY_NOTICES.md` (3 regex mentions) and the regex `LICENSE.txt` present.
Healthcheck `python -m openmedia --healthcheck` every 30 s; last probe exit 0.
Observations: memory+swap limit 4 GiB (2 GiB swap allowed beyond the memory limit); no
PID limit (not required).

| Gate | Result | Evidence |
|---|---|---|
| I001-RUNTIME | **pass** | The constraints above on the selected digest; real polling with fresh health (healthcheck enforces heartbeat/poll freshness); active-work shutdown on this same digest from T064 run 2 SD (stop at `downloading`, exit in 3.39 s, no yt-dlp/ffmpeg/ffprobe/deno processes, no interrupted file) |
| I005-CONTAINER | **pass** | Configured restricted startup with the runtime file credential and live health on the selected digest (above; T065 restore start 07:46:55 → healthy 07:47:06) |
| I006-CONTAINER | **pass** | Locked image from the release pipeline (T062); version label/package, regex import and licence/notices in the image; configured startup and live health |

**Live source suite.** `tests/live/test_sources.py` with the private nine-case manifest
(outside Git). The test stops at its first failing case, and it reached Instagram image
first, so each case was rerun with the same calls in a per-case script (scratch, outside
Git), one case per call with Instagram spacing of 60 s.

| Case ID | Outcome | Evidence |
|---|---|---|
| T066-SRC-YT-VIDEO | **pass** | Identity matches; 137 options, 79 selectable; smallest native choice format `139-drc` m4a, 3,871,021 bytes |
| T066-SRC-YTM-PLAIN | **pass** | Kind audio, canonical `music.youtube.com` watch address, automatic single choice format `140` m4a, 3,344,267 bytes |
| T066-SRC-YTM-CONTEXT | **pass** | Same track identity, same automatic `140`, 3,344,267 bytes |
| T066-SRC-LI-VIDEO | **pass** | Identity matches; format `1` mp4, 4,843,445 bytes |
| T066-SRC-LI-SHORT | **pass** | lnkd.in app link resolves to the same post; same format and bytes |
| T066-SRC-LI-HYPHEN | **pass** | Hyphen-code address; same post, format and bytes |
| T066-SRC-LI-IMAGE | **pass** | Identity matches; native jpg, 147,246 bytes |
| T066-SRC-IG-VIDEO | **fail — pre-existing product defect** | Inspection passed (six video options: three DASH VP9, three without codec). The download of the DASH option `vcodec=vp09.00.40.08…` produced a VP9 1080×1080 file (ffprobe `vp9`), then failed `format_unavailable` with `source codec changed`. Cause: `codec_family()` (`src/openmedia/sources/__init__.py`) maps `vp9*` but not the RFC 6381 form `vp09.*`, so a correct file is refused. Present since `f4708eb` (feature 003); not a deployment regression. YouTube labels VP9 as `vp9` (28 selectable VP9 options classified correctly, card offered H.264), so only `vp09.*` sources are affected. Whether the Instagram card offers the VP9 option, and so whether users reach the defect, is checked by the S2/S3 Instagram deliveries |
| T066-SRC-IG-IMAGE | **fail — source-blocked (provisional)** | Inspection failed `unavailable`: Instagram GraphQL `401 … "Please wait a few minutes before you try again."` at 09:59 and again at 10:09 UTC after a cool-down. Independent baseline: unwrapped Instaloader 4.15.3 `Post.from_shortcode` from the same egress at about 10:25 returned the same 401. Provisional because the suite's own requests may have triggered the throttle; repeat the baseline later before final classification |

Gate results from S0: **I001-SOURCES fail** (Instagram video: pre-existing product
defect; Instagram image: anonymous access refused by the source, provisional). **I005-LIVE
partial**: plain and context music identity, whole native audio and format/bytes pass;
offset, collection refusal and the ordinary-YouTube regression run in S4.

Follow-ups: fix `codec_family()` for `vp09.*` (and check `hev1`/`hvc1`, `vp08`) with a
failing test first. The fix needs a new preview release to reach the deployment.
Decision (operator, 2026-11-27): defer the fix to the next release candidate; S1–S4 run
on preview.7, and the S2/S3 Instagram deliveries decide whether users reach the defect.
`test_sources.py` should report each case separately instead of stopping at the first
failure.

### T066 S1 — diagnostics and LinkedIn short links — 2026-11-27

Runner `t066.sh S1` (sha256 `d20a3a06…b8bd`) on the production host, preview.7 digest
`8c27c75f…8cc6`, iPhone account A, 11:59–12:11 UTC. The runner log was scanned before
reading (0 token-shaped strings, 0 URLs, 0 bot usernames). Diagnostics were enabled with
guide block 19 (scripted edits, configuration check, stop/start, selection confirmed);
directory `10001:10001 0700`, file `0600`. Per-request timings come from the diagnostics
file through a reader that prints only platform, times and outcome.

| # | Case | Inspection | Card | Delivered | Bytes | Outcome |
|---|---|---|---|---|---|---|
| 1 | T066-I002-1 ordinary YouTube | 4.22 s | 4.60 s | 17.14 s | 47,817,430 | confirmed |
| 2 | T066-I002-2 unavailable YouTube | 1.08 s | — | — | — | failed `unavailable`, ERROR `failed_stage=checking` |
| 3 | T066-I004-1 first original lnkd.in | 3.15 s | 3.46 s | 9.78 s | 9,303,269 | confirmed |
| 4 | T066-I004-2 second original lnkd.in | 3.24 s | 3.50 s | 6.98 s | 8,829,701 | confirmed |
| 5 | T066-I004-3 video, full address | 2.58 s | 2.90 s | 6.22 s | 6,379,045 | confirmed |
| 6 | T066-I004-4 same video, short link | 2.52 s | 2.68 s | 5.25 s | 6,379,045 | confirmed |
| 7 | T066-I004-5 picture, full address | 3.07 s | — | 5.25 s | 64,434 | confirmed (no card) |
| 8 | T066-I004-6 same picture, app short link | 3.60 s | — | 6.58 s | 64,434 | confirmed (no card) |
| — | T066-I002-3 non-link text | — | — | — | — | refused `no_link` |
| — | T066-I004-7 two links in one message | — | — | — | — | refused `too_many_links` |

Times are seconds from request creation. Delivery times for cards include the operator's
selection, so card equivalence uses the card time.

Diagnostics file after the sends (counts only): 206 entries; 8 received, 8 terminal, 7
deliveries, 2 refusals; 1 ERROR, with `failed_stage`; 0 token-shaped strings; 0 `rcm=`
and 0 `utm_`; 6 `resolved_url` entries, none with a query string. Console since
enablement: 0 token-shaped strings, 0 URLs, 0 identifier or link keys. `failed_stage`
values are the 003 user-facing stage names (`checking`, `downloading`, `sending`); the
`inspection` value in the 002 contract example predates that rename.

Restart on the mounted volume (stop/start): the file kept every entry and gained
`startup`, `shutdown(signal)`, `startup` in that order. Disabled (block 19 reverted,
recreated): startup reports `diagnostic_log=off`, the only mount is the token file, an
ordinary YouTube delivery (21,089,494 bytes, confirmed) left the diagnostics inventory
unchanged, and `/var/log/openmedia` in the container is empty. Retention by age and size
on the mounted directory passed in T065 (see the T065 record).

| Gate | Result | Evidence |
|---|---|---|
| I002-DIAGNOSTICS | **pass** | Real success trace (#1) and failure trace (#2, ERROR with `failed_stage`); refusal reasons logged; 0 tokens in file and console; console carries no links or identifiers; persistence across restart; disabled writes nothing; retention from T065 |
| I004-SHORT-LINKS | **pass** | Both original 004 short links delivered (SC-003); short/full video: card 2.68 s vs 2.90 s, identical bytes; short/full picture: delivered 6.58 s vs 5.25 s (+1.33 s, limit 3 s), identical bytes (SC-001, SC-002); no tracking parameters or query strings in resolved addresses; refusal reasons in the log alone (SC-005); console privacy |

The diagnostics directory holds real links and Telegram identifiers; the operator kept it
past the runner's retention prompt to read the timings above. It is listed for deletion in
follow-up.md.

### T066 automated client — account B through the Telegram user API — 2026-11-27

From S2 on, a scripted Telegram client drives the production bot as the second account
(B) instead of the operator's iPhone: it sends the link, reads the card, taps a button,
waits for the outcome and downloads the received file (sha256 and byte count). It uses the
official Telegram user API (Telethon 1.46.0, run in a throwaway `uv` environment, not a
project dependency) from the Mac on the host's network. The API credentials and the login
session live in the macOS Keychain; the session is revocable from Telegram's device list.
Links come from the private manifests and are never printed; server timing comes from the
container console, which carries no links or identifiers. Taps wait 0.8 s after the card
appears (human-like) unless a case says otherwise.

Limits of the scripted client: it reads message types and attributes (inline video or
document, streaming flag, filename, caption) but does not watch a phone screen, so
playback rendering is attribute-verified, not visually observed; and with one scripted
account, cross-account checks (B acting on A's card) are not executed.

### T066 S2 — I001-TIMING — 2026-11-27

24 sequential rounds 12:42–13:10 UTC (at most one active request; Instagram rounds at least
60 s apart), then one Instagram picture round outside the timing set. Mix: YouTube
(choices: audio only, video without sound), YouTube Music plain/context, LinkedIn video
(full, short, hyphen code), LinkedIn picture, Instagram reel. No 429, 5xx or connection
failures, so no exclusions.

| Measure | Result | Required |
|---|---|---|
| Acknowledgment ≤ 2 s | 23 of 24 (max 3.38 s, one Instagram round) | ≥ 19 of 20 |
| Card ≤ 30 s | 22 of 22 cards (max 8.47 s); 2 pictures delivered without a card | ≥ 19 of 20 |
| Deliveries ≤ 20 MB confirmed ≤ 120 s after selection | 20 of 20 (max 6.75 s) | ≥ 19 of 20 |
| Console privacy | 0 token-shaped strings, 0 URLs, 0 identifier/link keys | 0 |

Every repeat of a case delivered identical bytes (same sha256): Instagram reel 1,846,690;
LinkedIn video 4,843,445 through the full address, the short link and the hyphen-code
address; LinkedIn picture 147,246; YouTube Music 3,344,267 plain and with context; YouTube
audio only 10,271,496; YouTube video without sound 28,207,144.

Three YouTube rounds (R01, R11, R19) produced no delivery: the harness tapped within
milliseconds of the card appearing and the bot answered "This choice is stale". Cause
(code): the card is published before the request moves to awaiting-selection
(`coordinator.py` `_publish_preview`, then the selection record), and a tap in that gap
finds the request still `CHECKING` and is answered `STALE`. A `STALE` answer does not end
the request, so a later tap should succeed; S3's instant-tap round did not hit the race, so
that recovery was not observed. Real users react far slower than the gap (about one Bot
API round trip); the harness now waits 0.8 s before a tap. The three rounds count as inspections
(acknowledgment and card within limits) and not as delivery samples.

Instagram reel: the card offered one automatic choice, "Video (no sound)", and said "Not
available: Video, Audio only." Inspection shows why: the reel has no audio stream anywhere
(three DASH VP9 video-only and three progressive video-only formats, no audio format), and
the delivered file is one H.264 720×720 stream. The automatic choice is the H.264 format,
not a VP9 one, so users of this reel do not reach the `vp09` defect from S0.

Instagram picture (extra round, 13:10): refused with "That content can't be opened without
logging in…"; the source answered 4xx. A plain Instaloader 4.15.3 request at 13:13 got the
same 401 "Please wait a few minutes", three hours after the S0 attempt.

| Gate | Result | Evidence |
|---|---|---|
| I001-TIMING | **pass** | Above; sequential rounds (≤ 1 active request, Instagram never overlapping); 0 exclusions; the three stale-tap rounds documented |

### T066 S4 — YouTube Music through Telegram — 2026-11-27

13:13–13:16 UTC, account B. No card buttons in any music case; each showed `Audio only —
downloading…`, `— sending…`, `— sent.` and delivered one `audio/mp4` document (`.m4a`).

| Case | Outcome | Bytes | sha256 |
|---|---|---|---|
| T066-I005-1 plain track | one document, no picker | 3,344,267 | `b4fa6194…c5e6` |
| T066-I005-2 same track with `list`/`si`/`index`/`t` | one document, no picker | 3,344,267 | `b4fa6194…c5e6` |
| T066-I005-3 same track with `t=45` | one document, no picker | 3,344,267 | `b4fa6194…c5e6` |
| T066-I005-4 collection-only (playlist page) | "Only one track is supported. Send a YouTube Music track link." No file | — | — |
| T066-I005-5 ordinary YouTube video | card with Video, Video (no sound), Audio only | — | — |
| Native comparison | format 140 fetched by the deployed image's yt-dlp (`docker run --read-only --user 10001:10001`) | 3,344,267 | `b4fa6194…c5e6` |

The received documents are byte-identical to the native format 140, so context and offset
neither change the track nor cut it. Console: per-request selection to delivery 3.0–3.2 s;
0 token-shaped strings, 0 URLs, 0 identifier/link keys.

| Gate | Result | Evidence |
|---|---|---|
| I005-TELEGRAM | **pass** | One automatic native audio document with no selection; progress and completion on the card; context and offset whole track (identical bytes); collection refusal; ordinary YouTube keeps video choices; received bytes equal the native format |
| I005-LIVE | **pass** | S0 plain/context identity and native format/bytes, plus S4 offset, collection refusal and ordinary-YouTube regression |

### T066 S3 — Telegram behaviour, UX and titles — 2026-11-27

13:17–13:42 UTC, account B through the automated client (S1 covered account A on the
iPhone). Every delivery arrived in the chat that sent the link.

| Case | Observation |
|---|---|
| T066-S3-1 instant tap (0 s) | Card, tap accepted, audio delivered (race not hit this time) |
| T066-S3-2 double tap | One delivery (10,271,496 bytes); second tap answered "That request is already processing. Please wait; no duplicate download was started." |
| T066-S3-3 combined video | First attempt failed at checking with console `external_causes=["connection_failure"]` (excludable, external). Retry: "Video" delivered inline (`sendVideo`, streaming flag set), 32,262,889 bytes, ffprobe H.264 + AAC; bytes re-downloaded from Telegram identical |
| T066-S3-4 title with `/` | Caption `AC/DC - Thunderstruck (Official Video)`; filename `AC_DC - Thunderstruck (Official Video).m4a` |
| T066-S3-5 title with emoji | Caption keeps both emoji; filename arrives as `atlantic ocean  View.mp4` (see filename finding) |
| T066-S3-6 every choice over 50 MB (10-hour video) | "The checking stage failed. None of the available choices fits the current delivery limit, so nothing can be sent. Send another public link." No file |
| T066-S3-7 forward a delivered file | Filename and sha256 unchanged after forwarding |
| T066-S3-8 forwarded card | Telegram strips the buttons from the forwarded copy, so it cannot be tapped; the original card still worked afterwards (one delivery) |
| T066-S3-9 group | Link sent in a new group with the bot, then with an @-mention: no reply and no file (privacy mode: the bot does not receive the message); group deleted |
| T066-S3-10 tap after 920 s | "Those choices expired. Submit the link again." No file |

From S2 (same client): cards show at most three buttons; LinkedIn video and pictures need
no tap; pictures arrive as documents (`image/jpeg`); video without sound arrives as an
inline video (`sendVideo`, not an animation); audio arrives as an `audio/mp4` document; a
successful request leaves two bot messages (the card, edited in place, and the file); an
absent audio track is explained on the card ("Not available: Video, Audio only."). Captions
equal the 006 caption rule (64 code points with `…` for long titles; Persian, `/` and emoji
kept literally).

Filename finding (Telegram-side): the hosted Bot API rewrites upload filenames. A probe
with the test bot (not production) sent fixed names and read the stored name back from the
API: stems up to 60 characters arrive unchanged (ASCII `-`, `,`, `(`, `_` kept); longer
stems get `_` for spaces, lose punctuation and are cut near 60 characters; emoji and
Arabic punctuation become spaces; a trailing `…` is dropped. The bot sends names that meet
006 FR-005 (stem up to 64 code points with `…`), so long titles arrive as
`Big_Buck_Bunny_60fps_4K_Official_Blender_Foundation_Short_Film.m4a` and emoji titles lose
the emoji.

Message wording finding: a checking-stage `internal` failure reads "The checking stage
failed. The checking stage failed. Retry the link later." (prefix in `notify_failure` plus
the `failure_message` fallback); pre-existing.

| Gate | Result | Evidence |
|---|---|---|
| I001-TELEGRAM | **pass** | Two accounts (A on iPhone in S1, B in S2–S4); five categories delivered except Instagram picture (source-blocked, I001-SOURCES); originating-chat delivery; double tap → one delivery; stale tap refused; audio-only delivered; absent audio explained; received bytes equal native output (S4) and stable across repeats (S2). Limits: B acting on A's card has no client path (forwarding strips the buttons), and a forged callback stays controlled-only |
| I003-UX | **pass** | Message shape, button count, tap counts and send methods verified from message attributes; the operator played the combined and silent videos on the iPhone (account B): both inline, the silent one not looping |
| I006-TITLES | **pass with a Telegram limitation** | Captions pass FR-004; the bot sends FR-005 filenames; forwarded filename unchanged; `/` → `_` passes. The hosted Bot API rewrites stems over 60 characters (`…` dropped, spaces → `_`) and replaces emoji with spaces; recorded as a Telegram limitation by operator decision (2026-11-27), with 006 SC-002 amended to measure the filename the bot sends. Missing-title fallback not reached live (controlled tests only) |

### T066 completion — 2026-11-27

Every required matrix case has an executed outcome or an evidenced source-blocked outcome
(S0–S4), real delivery passes in all five categories except the source-blocked Instagram
picture, and no deployment regression or unclassified failure remains. Open or limited
inherited gates, each classified: **I001-SOURCES fail** (pre-existing `vp09` codec-family
defect in the live suite, not reached through the bot's card; Instagram picture
source-blocked), **I001-TELEGRAM** limits (no client path for acting on another account's
card; forged callbacks controlled-only), **I006-TITLES** Telegram filename limitation.
Pre-existing product findings (publish/tap race, repeated failure sentence) are queued for
the next release candidate (follow-up item 7).

Cross-references were added to the earlier records: 001, 002, 003, 004, 005 and 006
`validation.md`, each under "Deployment acceptance through feature 008 T066 — 2026-11-27".
The earlier features' task boxes are unchanged. T066 is marked complete; T067 reconciles
public claims next.

### T067 claims reconciliation — 2026-11-27

Public claims checked against the register and T059–T066 outcomes, reported by evidence kind:

| Kind | Requirements | Outcome | Evidence |
|---|---|---|---|
| Controlled | FR-003, FR-008–FR-010, FR-014, FR-017–FR-021; SC-004, SC-006, SC-008 | pass | F008-SETUP, F008-CONFIG, F008-REGRESSION, F008-COMPOSE, F008-RELEASE-POLICY |
| Native container | FR-007, FR-018; SC-004 | pass on amd64 and arm64 | F008-NATIVE-AMD64, F008-NATIVE-ARM64 (T059) |
| Public distribution | FR-001–FR-004, FR-020; SC-001–SC-002 | pass (preview.5, .6, .7 accepted; preview.1–.4 kept as incomplete or rejected) | F008-SOURCES, F008-PUBLIC (T061–T062) |
| Deployment host | FR-005–FR-017, FR-019; SC-003, SC-005–SC-007 | pass on Ubuntu 26.04 amd64; 24.04 and arm64 hosts have no host acceptance | F008-INSTALL, F008-UPDATE, F008-SHUTDOWN, F008-OPERATIONS (T063–T065) |
| Live and Telegram | FR-019–FR-021; SC-008 | assessment complete; inherited I001-SOURCES fails (classified), other inherited gates pass, two with recorded limits | F008-ASSESSMENT, T066 S0–S4 and completion |

Reconciled documents:

- `README.md`: the source table reports the T066 outcomes; the Instagram single-image
  capability is withheld (source-blocked anonymously); Project status separates
  controlled, native/public, deployment and live results, names preview.7, keeps the
  project a **preview** and lists the open stable-release gates (I001-SOURCES; hosts
  other than Ubuntu 26.04 amd64) and the known limitations (Telegram filename rewriting,
  publish/tap race).
- `deploy/README.md`: preview.7 and its accepted index digest replace preview.5; T063 is
  recorded as passed on Ubuntu 26.04 amd64 with other hosts pending; operators are told
  to follow the repository guide, because the preview.7 source release predates the
  OP-EXIT command fix (`4ef5dcc`) and the empty-input rotation guard.
- preview.7 release notes (edited 2026-11-27, after `c945e72` was pushed): the original
  paragraph is kept and an "Update 2026-11-27" paragraph appended. It records server
  acceptance on Ubuntu 26.04 amd64, names the open stable gates (I001-SOURCES; Ubuntu 24.04
  and arm64 hosts) and points operators to the guide at `c945e72` instead of the copy in
  the release's sources. Tag, pre-release flag and all 9 assets checked unchanged before
  and after the edit.
- Immutable tags, images and source releases were not changed.

Feature 008 is complete as a preview. Stable promotion still needs I001-SOURCES to pass
(the `vp09.*` codec fix in the next release candidate and Instagram single-image access)
and host acceptance beyond Ubuntu 26.04 amd64.

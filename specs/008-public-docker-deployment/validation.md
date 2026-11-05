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
| F008-SOURCES | FR-002, FR-004; SC-002 | Public distribution | Both actual-image component closures, Debian Built-Using/system+application Python/unmanaged/embedded coverage and notices; exact source hashes/build materials; anonymous source-only release retrieval before first push; retain sources on later failure | pending |
| F008-PUBLIC | FR-001, FR-003–FR-004, FR-020; SC-001–SC-002 | Public distribution | Actual preview: anonymous both-platform pull, exact child/index/config joins, local signed raw-index/manifest bundles with trusted numeric repo/workflow/source identity, negative proof, all final public assets redownloaded/hash verified; no rebuild promotion; immutable-release staging | pending |
| F008-INSTALL | FR-005–FR-010, FR-018–FR-019; SC-003–SC-004 | Deployment-network/manual | Clean supported host guide walkthrough, secret ownership as UID 10001, local preflight vs remote token validity, exact digest polling/fresh health and representative native media delivery | pending |
| F008-UPDATE | FR-011–FR-015, FR-019; SC-003, SC-005–SC-006 | Deployment-network/manual | Failed pull/preflight leaves old poller uninterrupted; successful update; timeout/failure/interruption stops candidate; finite 180s health wait; protected selection persistence; explicit current-settings rollback incl unavailable/incompatible failure; migration/recovery of local image ID; one poller | pending |
| F008-SHUTDOWN | FR-014, FR-019, FR-021; SC-006 | Deployment-network/manual | Real active-work shutdown <=20s, child termination/reaping and scratch/upload cleanup, no duplicate uncertain/canceled sends; fresh request after recovery | pending |
| F008-OPERATIONS | FR-015–FR-017, FR-019; SC-003, SC-007 | Deployment-network/manual | Token rotation/recreated file mount, console privacy/status/resources, optional 002 diagnostics, unexpected process exit, reboot and intentional stop, upstream outage/recovery with no health restart loop/additional poller, backup/restore/removal | pending |
| F008-ASSESSMENT | FR-019–FR-021; SC-008 | Deployment-network/manual | Execute/assess full inherited matrix, classify every failure from evidence, reconcile actual release/README/deployment capability claims; distinguish feature completion from stable readiness | pending |

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
| I001-SOURCES | 001 FR-002, SC-001; T026/T074 | Deployment-network/manual | Full five-category inspect/download native formats, actual bytes, anonymous access and limitations; earlier 001 validation including 2026-09-21/22 attempts | pending |
| I001-RUNTIME | 001 SC-007; T053/T075 | Native container | Constrained container build/start/config plus real dedicated-bot polling, fresh health, active-work shutdown/child cleanup; [001 runtime evidence](../001-media-download/validation.md) | pending |
| I001-TELEGRAM | 001 SC-001, SC-005–SC-006; T054/T076 | Deployment-network/manual | Deployment-network five categories and two independent accounts; originating-chat isolation, repeated/forged/stale selections, available audio-only/absent-audio, native received output | pending |
| I001-TIMING | 001 SC-002–SC-003; T055/T080 | Deployment-network/manual | 20 eligible inspections: >=19 acknowledgments <=2s and previews <=30s; 20 eligible <=20MB deliveries: >=19 <=2min; <=2 global/<=1 Instagram concurrency; document exclusions/replacements | pending |
| I002-DIAGNOSTICS | 002 FR/SC; quickstart local/container checks | Deployment-network/manual | Enabled real trace/refusal, console/token privacy; disabled leaves no files; retention/rotation and mounted persistence across restart; [002 quickstart](../002-file-logging/quickstart.md) | pending |
| I003-UX | 003 SC-001–SC-005; manual matrix | Deployment-network/manual | One preview/status surface, first-page choices, audio/combined/image/video behavior, inline video including silent video on actual clients, native delivery/refusal; [003 validation](../003-streamlined-bot-ux/validation.md) | pending |
| I004-SHORT-LINKS | 004 FR-010, SC-001–SC-005 | Deployment-network/manual | Anonymous lnkd.in short/full equivalence, video/image delivery, redirect/refusal diagnostics and console privacy; [004 validation](../004-linkedin-share-links/validation.md) | pending |
| I005-LIVE | 005 SC-001–SC-005; T032/T036 | Deployment-network/manual | Plain/context/offset track identity, whole native audio, selected format/bytes, collection refusal and ordinary YouTube regression; [005 validation](../005-youtube-music-download/validation.md) | pending |
| I005-TELEGRAM | 005 US1–US3; T033/T037 | Deployment-network/manual | One automatic native audio document/no selection, card/progress/completion, whole-track context behavior, collection refusal and ordinary YouTube; actual received-byte comparison where available | pending |
| I005-CONTAINER | 005 T034/T038 | Native container | Configured restricted startup/health with runtime credentials; prior missing-daemon result is not source evidence | pending |
| I006-CONTAINER | 006 T019 | Native container | Locked distribution/build/import, version/notices, configured startup and live health; [006 validation](../006-media-delivery-titles/validation.md#external-acceptance-and-release-gaps) | pending |
| I006-TITLES | 006 FR-001–FR-009, SC-001–SC-005; manual quickstart | Deployment-network/manual | Caption, saved/forwarded filenames, long/Unicode titles, client versions/rendering/playback, native received bytes including YouTube Music; controlled upload labels do not close this gate | pending |

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
| Ubuntu 26.04 LTS | amd64 | pending | pending |
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
Every row starts `pending`: no accepted public digest/isolated real-host maintenance run
has been recorded. Release/platform and environment are `not yet selected/recorded`;
failure_class is `none` until an observed outcome is assessed. Each execution must append
the full record format above: exact version/source/index/container/image identities,
OS/architecture, Engine/Compose, UTC and observed timing, nonsecret network context,
result/reason, evidence, limitations and next action. Record each tested host combination
separately; no result here expands the supported-host evidence matrix.

| Case | Gate / requirements | Required observation | Result |
|---|---|---|---|
| OP-INSPECT | F008-OPERATIONS; FR-016–FR-017, FR-019; SC-003 | Selected health/restart/time fields, bounded console logs and one-shot resource stats; no token/link/Telegram ID disclosure, no poller from inspection, memory includes tmpfs | pending |
| OP-DIAGNOSTICS-OFF | F008-OPERATIONS; FR-017, FR-021; SC-003 | Default-off mode creates no diagnostic files, including local validation | pending |
| OP-DIAGNOSTICS-ON | F008-OPERATIONS; FR-017, FR-021; SC-003 | Explicit protected writable mount, UID 10001 access, directory 0700/files 0600, private real trace/refusal, no console disclosure, 14 UTC-day files/50MB retention, persistence across recreation; healthcheck writes no logs | pending |
| OP-ROTATE | F008-OPERATIONS; FR-008–FR-010, FR-015, FR-017; SC-003–SC-004 | Protected replacement, confirmed stop, atomic rename, local validation, forced mount recreation, real replacement authentication/health and one poller; transient/editor copies cleaned under host policy | pending |
| OP-ROTATE-FAIL | F008-OPERATIONS; FR-009, FR-015, FR-017; SC-003–SC-004 | Local invalid input and remotely rejected credential leave attempts stopped; corrected current input recovers; no revoked-token restoration or restart-only mount renewal | pending |
| OP-EXIT | F008-OPERATIONS; FR-016, FR-019; SC-007 | In-container unexpected exit after restart-monitoring threshold, automatic same-container recovery/increased restart count without up/start, health <=180s and delivery; no second poller | pending |
| OP-REBOOT | F008-OPERATIONS; FR-016, FR-019; SC-007 | Running selected digest automatically recovers after isolated-host reboot, healthy <=180s after Engine availability, real delivery and one poller; record boot IDs/timing | pending |
| OP-STOP | F008-OPERATIONS; FR-016, FR-019; SC-007 | Intentional stop persists across reboot; retained stopped container/no polling observed >=180s after Engine availability, followed by explicit healthy restart | pending |
| OP-OUTAGE | F008-OPERATIONS; FR-016, FR-019; SC-007 | Isolated network loss exceeds freshness/retry windows; unhealthy with unchanged container/StartedAt/restart count, reconnect recovers healthy polling <=180s and delivery; no restart agent/additional poller | pending |
| OP-BACKUP | F008-OPERATIONS; FR-017, FR-019; SC-003 | Operator verifies encrypted storage/access controls; consistent config/current credential/verified selection record, protected recoverability, no media/request/diagnostic backup | pending |
| OP-REMOVE | F008-OPERATIONS; FR-017, FR-019; SC-003 | Only fixed project removed; explicit retained config/secret/diagnostic/migration/record/backup/image inventory and retention decisions; unrelated services unchanged | pending |
| OP-RESTORE | F008-OPERATIONS; FR-015, FR-017, FR-019; SC-003 | Other pollers stopped; reviewed config, current credential and ownership/modes, verified digest and isolated preflight, real health/delivery; no request resumption | pending |

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

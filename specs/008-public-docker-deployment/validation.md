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

| gate_id | requirement_ids | class | Required execution / evidence and limitations | result |
|---|---|---|---|---|
| F008-SETUP | FR-003, FR-009, FR-019 | Controlled | Official pin provenance/checksums; validation register; Git/Docker secret exclusions; execution record below | pass |
| F008-CONFIG | FR-008–FR-010, FR-018; SC-004 | Controlled | Presence conflicts including empty keys, file/path/type/size/ASCII/newline/grammar errors, bounded nonblocking reads, direct compatibility, redacted chains/repr/logs/workers and CLI no-poll behavior | pending |
| F008-REGRESSION | FR-014, FR-017–FR-021; SC-006, SC-008 | Controlled | Full locked controlled suite; native byte/stream-copy, source categories, titles, state/deadlines/limits, worker/child/upload cleanup, failure/refusal/retry and privacy regressions | pending |
| F008-NATIVE-AMD64 | FR-007, FR-018; SC-004 | Native container | Native linux/amd64 build/import config identity; restricted offline smoke, tools/EJS, local stream-copy, bounded writable tmpfs, read-only root, UID/capabilities/init, secret permissions/negative cases, no runtime executable acquisition | pending |
| F008-NATIVE-ARM64 | FR-007, FR-018; SC-004 | Native container | Same checks independently on native linux/arm64; retain runner/image/tool versions and exact checked image ID | pending |
| F008-COMPOSE | FR-005, FR-007–FR-011, FR-016, FR-018 | Controlled | Effective published Compose with fixture settings; fixed project and digest; explicit allowed environment, read-only secret, limits/logging, no ports/build/socket; retained local-build Compose path | pending |
| F008-RELEASE-POLICY | FR-001–FR-004, FR-020; SC-002 | Controlled | Identity/manifest/source collectors and tamper/failure cases; both imported identities before either push; zero writes on pre-push failure; correct incomplete distribution behavior after push/finalization; immutable pins/least privilege/tag authority/preview | pending |
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
| I001-CONTROLLED | 001 FR/SC controlled acceptance; 008 FR-021 | Controlled | Full media/adapter/delivery/lifecycle regression suite; [001 validation](../001-media-download/validation.md) | pending |
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

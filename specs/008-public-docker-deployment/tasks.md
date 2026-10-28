---
description: "Implementation tasks for public Docker releases and single-server deployment"
---

# Tasks: Public Docker Deployment

**Input**: Design documents from `specs/008-public-docker-deployment/`.

**Prerequisites**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md),
[data-model.md](data-model.md), [configuration contract](contracts/configuration.md),
[release contract](contracts/release.md), [operations contract](contracts/operations.md),
and [quickstart.md](quickstart.md). Retain [proposal.md](proposal.md) unchanged.

**Tests**: Required by FR-018–FR-019 and the constitution. Include controlled configuration,
release-policy and failure-path checks, native restricted-container checks, and separate
public-distribution and real-server acceptance. Write new behavior/contract tests before
implementation and observe the expected failure. Do not add tests that merely mirror
documentation or YAML text. Existing media/lifecycle tests remain regression evidence.

**Organization**: Setup → shared foundation → US1 (P1) → US2 (P1) → US3 (P2) → US4 (P2)
→ cross-cutting validation. User-story phases deliver independently testable behavior;
actual publication/server acceptance is collected in the final phase so code development
does not depend on prematurely publishing a partial feature. Those final gates remain
required for acceptance and are mapped to each story below.

## Format: `[ID] [P?] [Story] Description`

All tasks start unchecked. `[P]` permits concurrent work only for the explicitly named
groups after their prerequisites pass; it does not authorize spawning agents. Story tasks
carry `[US1]`–`[US4]`; shared and final tasks have no story label. Exact repository-relative
paths identify outputs. Quoted entity constraints come from `data-model.md` and remain
binding. A report entry is not a substitute for executing the check it records.

## Path Conventions

Application: `src/openmedia/`; controlled tests: `tests/unit/`, `tests/contract/`,
`tests/integration/`; sanitized release/probe fixtures: `tests/fixtures/release/` and
`tests/fixtures/deployment/`; native Docker checks: `scripts/smoke-container.sh`;
release tooling: `scripts/release/`; workflows: `.github/workflows/`; public deployment:
`deploy/`; release policies: `release/`; evidence: `specs/008-public-docker-deployment/validation.md`.

Use the existing `008-public-docker-deployment` branch and feature pointer. Preserve
the separate `007-local-server-deploy` branch. No new runtime dependency, service,
request database, source authentication, transcoding, or automatic updater is included.
Any newly necessary pinned dependency must update its applicable lock/policy together;
do not silently upgrade the runtime while doing deployment work.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish evidence conventions, reviewed tool pins, and secret exclusions
without changing the application's architecture.

- [X] T001 Create `specs/008-public-docker-deployment/validation.md` with the FR/SC and inherited 001–006 gate register; validation-record fields must preserve gate_id/requirement_ids "Release/check identity and related acceptance requirements", class "Controlled, native container, public distribution, or deployment-network/manual", release/platform "Exact source, image identity, and architecture", environment "Host OS, Engine/Compose/tool versions, network context without secrets", result "`pending`, `pass`, `fail`, or `blocked` with a concrete reason", gate_scope "Feature 008 acceptance or inherited stable-readiness obligation", failure_class "Deployment regression, evidenced pre-existing source limitation, unclassified, or none", and evidence/limitations "Sanitized commands/results, timing, observed constraints, next action"; define feature-completion versus stable-readiness gate sets, require earlier validation/baseline evidence for known-source classifications, and initialize unexecuted gates pending and preserve "Passing a substitute does not transition a live/manual gate to pass."
- [X] T002 [P] Resolve the selected build-only tools/actions against their official releases and append actual checksums, full action commit SHAs, license/provenance links, and pinned collector-tool/container versions to `specs/008-public-docker-deployment/research.md`; retain Syft 1.55.0, regctl 0.11.7, GitHub CLI 2.103.3, actions/attest 4.2.2 and current runtime pins unless incompatibility is explicitly resolved in the plan; do not invent hashes or add runtime packages.
- [X] T003 [P] Extend `.gitignore` and `.dockerignore` to exclude host `deploy/deploy.env`, deployment secret directories, local update/evidence state, source-collection output and credential-bearing artifacts while retaining nonsecret examples and sanitized fixtures; preserve existing `.env`, diagnostic-log and media exclusions, including "No host credentials, live manifests, or media enter assets."

**Checkpoint**: The evidence register and pin ledger exist, and new deployment paths
cannot accidentally enter Git or the application image with host credentials.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Supply the token interface, published Compose surface, and restricted
smoke tooling shared by every story. Complete this phase before Phase 3.

### Required configuration and boundary tests

- [X] T004 [P] Extend `tests/unit/test_config.py` for both token keys present (including empty values, before any read), neither key, legacy direct-token compatibility, valid file tokens with zero/one terminal LF/CRLF, absolute/NUL-free paths, missing/unreadable/nonregular files, bounded nonblocking reads, 4,096/4,097-byte boundaries, ASCII/BOM/blank/multiline/control/whitespace failures, and `[0-9]+:[A-Za-z0-9_-]+` file grammar; inject unreadability rather than trusting root chmod behavior and assert safe error strings and suppressed formatted exception chains.
- [X] T005 [P] Extend `tests/integration/test_workers.py` and `tests/unit/test_diagnostics.py` with sentinel file-loaded credentials to prove neither token input nor loaded value reaches worker payloads/minimal environment, settings repr, console or enabled diagnostics; retain fake transports and injected clocks and observe failures before changing configuration code.

### Shared implementation

- [X] T006 Implement the private file-token loader in `src/openmedia/config.py` and integrate it with `Settings.from_env(mapping)` to pass T004–T005: preserve "Presence of both source keys is invalid even if empty." and "Store the loaded value only in the existing private settings field."; open read-only/nonblocking, fstat the descriptor, read at most 4,097 bytes, always close, apply the contract's ASCII/newline/grammar rules, retain legacy direct validation, and emit fixed redacted `ConfigError` categories with no path/content/raw exception interpolation or retained printable source field.
- [X] T007 Amend `specs/001-media-download/contracts/runtime.md` and `.env.example` to reference feature 008's mutually exclusive token sources and local validation meanings; preserve every other setting, fixed deadline, source-worker boundary, diagnostic contract and existing direct-token development path.
- [X] T008 Add `deploy/compose.yaml` for a published image with no build directive, ports, Docker socket or media volume; preserve deployment fields project "Fixed production Compose project `openmedia`", image "`ghcr.io/hman-pro/openmedia@sha256:` followed by 64 hexadecimal digits", env_file/compose_file "Explicit `/opt/openmedia/deploy.env` and `/opt/openmedia/compose.yaml`", token_file "Host secret path; nonsecret reference, mounted read-only at `/run/secrets/telegram_bot_token`", runtime_settings "Explicit permitted nonsecret settings under existing validation rules", limits/logging "Production restrictions and bounded console logs", and diagnostic_storage "Absent by default; explicitly provisioned per feature 002 when enabled"; explicitly map nonsecret interpolation settings, mount the file secret read-only, and retain UID/GID 10001, init, read-only root, all capabilities dropped, no-new-privileges, unless-stopped, 2 CPUs/2 GiB/512 MiB tmpfs, 30-second grace and 10 MiB × 3 console logs.
- [X] T009 Add a sanitized nonpolling probe and fixture provenance in `tests/fixtures/deployment/probe.py` and `tests/fixtures/deployment/README.md`, reusing licensed tiny media from `tests/fixtures/media/` to check bundled Python/EJS/Deno/FFmpeg/ffprobe, unchanged local stream-copy output, writable bounded scratch storage, synthetic local heartbeat checks and negative secret access as UID 10001; the probe contains no bot credential, external connection or sleep-based readiness claim.
- [X] T010 Implement `scripts/smoke-container.sh IMAGE` using T009 under the actual production restrictions and `--network none`; exercise valid/missing/unreadable/malformed/conflicting fake token inputs through the CLI, inspect effective identity/mounts/capabilities/resource limits and read-only root, mount only sanitized probes read-only, and trap exit/failure/interruption to remove its own containers and temporary fixtures; keep pytest/dev tooling out of the runtime layer and distinguish synthetic health from real polling.
- [X] T011 Preserve exact base/tool/FFmpeg pins and retained license files in `Dockerfile`, adding only release metadata/notice support needed for source/version/revision labels; preserve UID/GID, bundled EJS, no executable downloads at startup, 120-second health grace and existing health command; leave root `compose.yaml` available for local builds and record any necessary compatibility adjustment in `specs/008-public-docker-deployment/research.md` rather than silently replacing pins.
- [X] T012 Run the targeted configuration, worker, diagnostic and runtime suites plus an available native-platform build and T010 smoke check, render the published Compose definition with nonsecret fixture settings, and record commands/results/image IDs and missing platform evidence in `specs/008-public-docker-deployment/validation.md`; require the executed checks to pass, retain the other architecture as a required US1/CI gate, and report unavailable build infrastructure explicitly rather than claiming smoke acceptance.

**Checkpoint**: The shared loader and offline container validation work. The other
native architecture remains mandatory in Phase 3; no registry image has been published.

---

## Phase 3: User Story 1 - Obtain an identifiable public release (Priority: P1)

**Goal**: Maintainers can distribute the exact checked amd64/arm64 images with matching
source, inventories, immutable identities, and verifiable signed evidence.

**Independent Test**: Exercise the full pipeline with a maintainer-created preview
tag, retrieve both platforms and all source/evidence assets without credentials, verify
the real bundles and selected digest, and reject failed checks/tampered identities.
Controlled and native pipeline evidence is recorded here; T062 is the actual public
end-to-end gate and is required before declaring this story publicly accepted.

### Required contract and failure tests

- [ ] T013 [P] [US1] Add `tests/unit/test_release_manifest.py` and sanitized records under `tests/fixtures/release/records/` for release/platform/source identities, exact platform set, immutable version rejection, hash/config-ID distinctions, incomplete coverage, canonical asset URLs and noncyclic manifest hashes; distinguish duplicate-version rejection by publisher pre-push authorization from successful final assembly/local verification of an existing version with matching identities, and reject mismatched published identities; include stale inventory, source-version mismatch, artifact swaps, wrong platforms and malformed/missing fields from `data-model.md`.
- [ ] T014 [P] [US1] Add acquisition/collector failure tests in `tests/integration/test_release_tools.py` and sanitized Debian/Python/tool metadata under `tests/fixtures/release/sources/`; inject Docker/APT/download boundaries to cover source-versus-binary version differences, `Built-Using`, both Python environments, lockfile sdist hashes, embedded/unmanaged components, absent notices, unsafe archives, interrupted acquisition and checksum failures without real network access.
- [ ] T015 [P] [US1] Add `tests/contract/test_release_policy.py` with controlled workflow/CLI boundary fixtures under `tests/fixtures/release/policy/` covering wrong tag/repository/source/signing identity, missing matching source tag, missing architecture or failed gate before any push, arm64 import mismatch before amd64 push, no rebuild on promotion, immutable-release staging, local-bundle auth independence, tampered index/manifest/SBOM, untrusted roots and stage-specific failure handling: every pre-push failure causes zero image writes, signing/image-access failure after push leaves the final release draft and distribution incomplete, and evidence-download failure after finalization prevents acceptance while retaining immutable artifacts and sources; test observable decisions through the release helpers/command boundaries rather than YAML substring snapshots.

### Release entities, acquisition, and verification

- [ ] T016 [P] [US1] Create reviewed `release/source-policy.json` from actual pinned tool/base origins, listing exact unmanaged/system/embedded source revisions, acquisition hashes, license/notice paths, build recipes and incorporated source edges; distinguish CPython/uv/uvx/Deno, all installed Debian components and any unlocked system Python distributions, and make unknown components fail coverage instead of assuming the root notices table or application Git archive is complete.
- [ ] T017 [P] [US1] Create `release/verification-policy.json` with the canonical numeric GitHub repository ID resolved from the authoritative repository, expected repository/workflow/issuer/hosted-builder constraints and allowed public asset origins; pin the trusted identity independently of downloaded release assets, use established verifier roots, and record the lookup and tool-output compatibility evidence in `specs/008-public-docker-deployment/research.md`.
- [ ] T018 [US1] Implement published-release record validation and final manifest assembly in `scripts/release/validate_release.py`: version "Exact maintainer-created `vMAJOR.MINOR.PATCH[-prerelease]` tag; validate syntax and its expected release identity", package_version "Installed OpenMedia package version; recorded independently of preview tag suffix", source_revision "Full Git commit at the release tag", source_repository/repository_id "Canonical project URL and numeric GitHub repository identity", workflow/workflow_run "Trusted release workflow path, run ID and attempt", source_release_tag/source_release_url "Completed sources-only release `sources-VERSION` at the same commit; material assets can live there", index_digest "SHA256 of exact OCI index bytes; selected production identity", platforms "Exactly `linux/amd64` and `linux/arm64`; each linked to its child image", artifacts "Named assets, SHA256, size, media type, and public location", and preview/gates "Preview status and references to feature-acceptance and inherited stable-readiness gates"; preserve "A version is immutable once published." and pass the related T013 cases; do not query version nonexistence in shared parsing/final assembly or operator verification, which must accept matching already-published versions.
- [ ] T019 [US1] Implement the `promotion --record FILE --image IMAGE` boundary and platform record checks in `scripts/release/validate_release.py`: platform "One required platform, built and tested natively", runner "Hosted runner label, architecture, runner-image revision", image_config_id "Docker image ID before archive export and after import; must match", archive_hash "SHA256 of same-run Docker archive transferred between jobs", base_digests/tool_versions "Effective build inputs from pinned Dockerfile and build tooling", smoke_result "Successful restricted/no-network smoke result for this exact image ID", platform_digest "Registry child manifest digest after promotion; joins index descriptor", sbom "Architecture-specific SPDX JSON asset and hash", and component_inventory "Actual Debian/Python/unmanaged inventory used for source coverage"; validate imports before publication without treating archive hashes as manifest digests.
- [ ] T020 [US1] Implement `inventory --image IMAGE --platform PLATFORM --output DIRECTORY` in `scripts/release/collect_sources.py` using actual Debian metadata, both application and system Python environments and unmanaged binaries; record source-component fields component_id/kind "Stable inventory identity; Debian, application Python, system Python, or unmanaged/embedded tool", name/version/architectures "Exact installed identity and platforms containing it", license/notice_paths "Reviewed license classification and installed/archived notice locations", source_identity "Debian source package/version, lockfile sdist, or explicit policy revision", source_files "Archive paths, acquisition URLs, checksums, size, and source-format relationships", build_materials "Required packaging, patches, base/tool build recipes and instructions", incorporated_sources "Debian `Built-Using` and reviewed vendored/static source relationships", and coverage "`complete` or `missing`; missing blocks publication".
- [ ] T021 [US1] Implement exact Debian source collection in `scripts/release/collect_sources.py` using reviewed pinned collector tooling, authenticated source metadata and historical snapshots when needed; retain `.dsc` plus every referenced upstream/patch archive for all installed package/source identities and `Built-Using` edges, preserve installed copyright/common-license files, safely validate unpackability without executing upstream build code, and pass the relevant T014 fixtures.
- [ ] T022 [US1] Implement installed Python sdist, system-package and unmanaged/embedded tool collection in `scripts/release/collect_sources.py` from `uv.lock` and `release/source-policy.json`, including required base/tool recipes and notices; preserve "Deduplicate identical source materials across platform builds." and "Every installed component must map to a reviewed entry even if no source obligation applies."; emit `source-manifest.json`, notice archives and size-bounded logical source parts with verified acquisition/output hashes, without implying bit-for-bit binary reproducibility.
- [ ] T023 [US1] Implement `sources --directory DIRECTORY` and `bundle --directory DIRECTORY` in `scripts/release/validate_release.py` to fail closed on incomplete actual-image coverage, stale version/platform joins, missing notices/sources, unsafe archive members, wrong hashes, unsupported asset origins or manifest cycles; bind source-manifest and per-platform SPDX hashes to the final manifest, emit finalized `SHA256SUMS`, and pass T013–T014 without importing application/runtime-only dependencies.
- [ ] T024 [US1] Implement `verify --directory DIRECTORY --image IMAGE_AT_DIGEST --version TAG --source-revision COMMIT --policy FILE` in `scripts/release/validate_release.py` with Python 3.11+ compatibility and pinned gh local-bundle invocation; enforce image-reference shape, real index/manifest signatures, repository numeric ID/workflow/issuer/source/hosted-builder policy and every material hash, use established roots, sanitize inherited auth, and reject all T015 identity/tampering cases without invoking the authenticated OCI verifier path or accepting a Docker-save tar as the image subject.

### CI and tag publication

- [ ] T025 [US1] Add `.github/workflows/ci.yml` with read-only PR validation and reusable tag-validation jobs: run the locked controlled suite, build/load natively on `ubuntu-24.04` and `ubuntu-24.04-arm`, execute T010, generate pinned Syft SPDX inventories and T020 inventories, and export both tested Docker archives plus hashes/config IDs/smoke records as distinct same-run artifacts; use the T002 action/tool pins, capture hosted-runner versions, never pass a real bot credential or publish from PR/ordinary branch execution, and preserve the reused caller's workflow/source context.
- [ ] T026 [US1] Add the authority and prerequisite portion of `.github/workflows/release.yml`: validate the canonical repository, maintainer-created preview/version tag and matching `sources-VERSION` commit, reject an existing exact image version only in publisher authorization before the first push (never in read/verify paths), serialize with cancellation disabled, reuse/rerun T025 checks and collect/validate both source inventories; enforce "Both platform records and the controlled suite must pass before any image push." with explicit needs/failure conditions and default `contents: read` permissions; enumerate authority/pins, controlled/native build/smoke/inventory/source coverage, public source retrieval and both archive-import identities as the complete pre-push gate set, with checks requiring pushed images or finalized assets assigned to later stages.
- [ ] T027 [US1] Implement source-release staging in `.github/workflows/release.yml`: attach all source/notice materials to the sources-only draft, publish that completed release and prove anonymous material download before any registry push; keep the final image release draft, allow reuse of a prior source release only when every relevant material/inventory hash matches, and fail rather than append/replace assets in an immutable published release.
- [ ] T028 [US1] Implement tested-image promotion/index assembly in `.github/workflows/release.yml`: import both same-run archives with distinct local references, verify both archive hashes/config IDs through T019 before pushing either, grant package-write only to the release publisher, push without rebuilding using unique run/attempt/architecture auxiliary references, assemble the exact version index, and cross-check both child config identities/platform descriptors and record resulting child/index digests.
- [ ] T029 [US1] Implement signed evidence generation in `.github/workflows/release.yml`: obtain exact raw index bytes with pinned regctl `raw-body`, assert their SHA256 matches the index digest, generate signed image provenance and a separate release-manifest attestation with full-SHA-pinned actions/attest and `create-storage-record: false`, and attach index, bundles, both SPDX files, final manifest and checksums to the image-release draft; grant OIDC/attestation or contents-write only to the release jobs needing them and preserve noncyclic hashes and sources-only URLs.
- [ ] T030 [US1] Implement post-push verification, release finalization and release acceptance in `.github/workflows/release.yml`: prove actual raw-index/image-subject local-bundle verification and its negative cases with empty GitHub/Docker configurations, pull both platform digests anonymously, keep the fully populated final release draft until those finalization checks pass, then publish it and require successful redownload/verification of public evidence before acceptance; report any partial/postpublication failure as incomplete in notes/workflow results without mutating locked assets or moving version tags, and require preview status while inherited external gates are open.
- [ ] T031 [US1] Document maintainer tag-pair creation, immutable source/image release ordering, minimal permissions, image/source retention and initial public-package setup in the release section of `deploy/README.md`; include the reviewed repository identity, pinned verifier installation, trusted-policy retrieval and positive/negative account-free verification commands, and clarify that publication never deploys or updates a server.
- [ ] T032 [US1] Reconcile `THIRD_PARTY_NOTICES.md` with the actual inventoried runtime closure, required source/build materials and public sources-only asset locations; preserve installed notice obligations and record the exact FFmpeg build's GPL-enabled/nonfree-disabled check, including base/system Python and embedded-tool coverage rather than only top-level application dependencies.
- [ ] T033 [US1] Run T013–T015 and source/promotion/bundle/verification controlled checks against the integrated release tooling, correct failures in `scripts/release/collect_sources.py`, `scripts/release/validate_release.py` and policies, and record outcomes/actual pin provenance in `specs/008-public-docker-deployment/validation.md`; treat the real signed-bundle proof as still pending until T062 executes it.
- [ ] T034 [US1] Run both native CI build/smoke/inventory/archive jobs and source-material collection for the candidate, record actual architecture/tool/image/source results in `specs/008-public-docker-deployment/validation.md`, and require these pre-push checks to pass before any registry image push; a missing native runner, source archive or notice remains a blocking gate, not an emulated or silently skipped pass.
- [ ] T035 [US1] Exercise read-only PR behavior and failure-before-push boundaries using the workflow/tool fixtures from T015, review effective workflow permissions and full action/tool pins, and record US1's code-ready versus public-acceptance state in `specs/008-public-docker-deployment/validation.md`; keep public distribution/real-signature gates assigned to T062 and mark no unperformed gate passed.

**Checkpoint**: US1's checked-artifact pipeline and operator verifier are implemented.
This is an implementation checkpoint. Public preview publication follows US2–US4 code
and T059–T062 in order; a local build or fixture signature does not establish public
distribution or real provenance verification.

---

## Phase 4: User Story 2 - Start the bot securely on a server (Priority: P1)

**Goal**: An operator can install the published digest without a local application build,
provide a readable runtime token securely, preflight offline, and start one healthy bot.

**Independent Test**: On a clean supported host, follow only the guide using a verified
release and an operator-owned token; confirm health and a representative delivery, and
reject invalid secrets before polling. T063 supplies this actual external walkthrough.

### Required CLI tests and implementation

- [ ] T036 [US2] Extend `tests/integration/test_runtime.py` with file-input CLI cases proving `--check-config` returns 0/2 locally, invalid file settings fail before polling/log setup with safe stdout/stderr/tracebacks, preflight preserves another process's workspaces, and `--healthcheck` returns 0/1/2 without network/poller/diagnostic-file creation; cover valid direct-input compatibility and loaded-token redaction with diagnostic logging both off and on, using fixture runtimes and injected clocks.
- [ ] T037 [US2] Add `deploy/deploy.env.example` with only digest-qualified `OPENMEDIA_IMAGE`, nonsecret `OPENMEDIA_TOKEN_FILE` and explicit permitted runtime settings; document the exact image digest grammar and verification prerequisite instead of treating Compose required-variable syntax as digest validation, explain shell override precedence, and prevent wholesale host env import or a mapped direct-token setting in `deploy/compose.yaml`.
- [ ] T038 [US2] Extend the installation section of `deploy/README.md` for rootful Docker from the official Ubuntu 24.04/26.04 APT repository, amd64/arm64, recorded Engine/Compose versions and required flag capability checks; use protected `/opt/openmedia` files, a root-owned 0700 secret directory and `root:10001` 0640 secret, check GID membership, explain ignored Compose file-secret ownership attributes and lack of encrypted host storage, and keep tmpfs within the 2 GiB memory explanation.
- [ ] T039 [US2] Add first-start and offline preflight instructions to `deploy/README.md` using explicit project/absolute file paths, verified digest selection, command-scoped overrides and isolated one-off tmpfs; require each pull/config/preflight block to succeed before continuing, start no poller for validation, enforce stop-before-start ownership checks, use the 180-second health wait and explicit failed/interrupted-start cleanup, and distinguish local credential shape from real Telegram acceptance.
- [ ] T040 [US2] Verify the installed CLI/deployment contract against the T036 suite and T010 native container smoke checks, including UID 10001 actual secret readability, absent token values from effective Compose/container settings and no unintended workdir sharing; fix integration defects in `src/openmedia/config.py`, `src/openmedia/__main__.py` or `deploy/compose.yaml` only as necessary, and record the observed results in `specs/008-public-docker-deployment/validation.md`.
- [ ] T041 [US2] Validate the preserved root `compose.yaml`, `.env.example` and `scripts/dev.sh` direct-token local workflow after the new file-token interface, including a local configuration check without networking; record compatibility in `specs/008-public-docker-deployment/validation.md` and correct documentation/settings defaults without mapping both token sources into the same process.
- [ ] T042 [US2] Reconcile the setup/preflight/activation examples in `specs/008-public-docker-deployment/quickstart.md` with the implemented `deploy/README.md` and exact CLI flags/paths; record the supported-host matrix and the remaining real-token installation/health/delivery gate T063 in `specs/008-public-docker-deployment/validation.md`, leaving untested OS/architecture combinations explicitly pending.

**Checkpoint**: The secure installation surface is complete and locally verified.
Public release and real-host startup/delivery evidence remain T062–T063, not implied passes.

---

## Phase 5: User Story 3 - Update deliberately and recover a previous release (Priority: P2)

**Goal**: An operator can preflight without downtime, update with one poller and bounded
health wait, explicitly recover the previous digest, and migrate from local Compose.

**Independent Test**: Exercise healthy and failed candidates, an unavailable/incompatible
previous digest, interrupted startup, and migration from the old project. Confirm no
overlap, old service unaffected by failed preflight, cleanup and healthy explicit rollback.
The real-server update/migration gate is T064.

### Required lifecycle validation and operator interfaces

- [ ] T043 [US3] Extend the existing active-work shutdown cases in `tests/integration/test_runtime.py` and `tests/integration/test_failure_cleanup.py` to exercise file-token settings through the runtime boundary without changing the lifecycle design; prove admission closes, owned tasks/uploads are canceled, real child groups are reaped, heartbeat/scratch cleanup occurs, stale callbacks remain invalid and uncertain sends are not automatically repeated within the inherited 20-second application/30-second deployment budgets.
- [ ] T044 [US3] Add the nonsecret operator update-record template to `deploy/README.md` with previous/candidate references, actual container/image IDs, UTC/settings identity, preflight/deadline/health/stop/rollback outcomes; preserve "Do not hash/log credential contents as an identity mechanism." and "At most one polling container per token across projects."; map the exact update transitions from `data-model.md` without adding application persistence or an updater service.
- [ ] T045 [US3] Implement the manual update runbook in `deploy/README.md`: verify/pull/preflight with command-scoped candidate override while selected env/current bot stay unchanged, record the actual running `.Config.Image` and content ID, stop and confirm before startup, wait at most 180 seconds, explicitly stop failed/timed-out/interrupted candidates, then atomically persist only the healthy image setting and report persistence failure as an incomplete update; make every pasteable sequence abort when a prerequisite fails.
- [ ] T046 [US3] Add explicit rollback instructions to `deploy/README.md` selecting the recorded previous digest with current settings and credentials, ensuring candidate stop before preflight/start, checking health and persisting the restored selection only on success; include unavailable/incompatible previous images, failed rollback cleanup and retention of the previous image until update acceptance, with no automatic settings/token resurrection.
- [ ] T047 [US3] Add root-Compose migration and return-path instructions to `deploy/README.md`: identify the actual old project, preserve its protected configuration and local image content ID, preflight the new service without polling, stop/confirm the old poller before activation, and recover the old project from its pinned local content if needed; never invent a registry digest for a local-only image or change/merge the `007-local-server-deploy` branch.
- [ ] T048 [US3] Update failure walkthroughs in `specs/008-public-docker-deployment/quickstart.md` with concrete accepted/failed startup, interruption, persistence-error, missing/incompatible rollback and migration scenarios; reference the exact implemented commands and expected states, require candidate stop before any recovery attempt, and document canceled active work/users resubmitting without promised resumption or automatic duplicate sends.
- [ ] T049 [US3] Run the integrated lifecycle/cleanup/worker tests, configuration-file path regressions and syntax validation of the runbook shell examples after T043–T048; correct failures in the owning runtime module only if evidence requires a fix, and record measured/controlled results separately from unperformed real-host timing in `specs/008-public-docker-deployment/validation.md`.
- [ ] T050 [US3] Review the update/rollback/migration state transitions and all failure exits against `contracts/operations.md` and `data-model.md`, record their concrete validation mapping and T064's still-pending real-host cases in `specs/008-public-docker-deployment/validation.md`, and leave no guide path that can start a candidate after failed stop/preflight or declare success after an unhealthy/persistence-failed transition.

**Checkpoint**: US3 has a complete operator workflow and inherited lifecycle regressions.
Actual downtime, process cleanup and rollback/migration acceptance require T064.

---

## Phase 6: User Story 4 - Operate the service and assess readiness (Priority: P2)

**Goal**: Operators can inspect, rotate, recover, restore and remove the service while
maintainers publish support/readiness claims that match recorded evidence.

**Independent Test**: Follow each maintenance procedure on the acceptance host; test
process exit/reboot, intentional stop, upstream outage, rotation/recreation, restore and
project-scoped removal. Review logs/status and the release evidence for privacy and honest
pending gates. T065–T066 provide actual external operations/media evidence.

### Required validation references and operations documentation

Reuse T005/T036/T043 and existing local heartbeat/lifecycle tests; the maintenance
changes below are a runbook, not a new process manager requiring duplicate unit tests.

- [ ] T051 [US4] Add health/log/resource inspection commands to `deploy/README.md` using `compose ps`, bounded logs, selected health fields and one-shot stats, explaining the local heartbeat/poll freshness model and avoiding token-bearing environment dumps or public diagnostic content; retain default-off diagnostics and document its explicit protected optional mount, retention and privacy contract when enabled.
- [ ] T052 [US4] Add credential rotation and failed-rotation recovery to `deploy/README.md`: prepare protected replacement input, stop, atomically replace, locally validate and force-recreate to renew the single-file mount, confirm real authentication/health, and clean temporary secret copies under host storage practices; never rely on restart alone or software rollback restoring an obsolete/revoked token.
- [ ] T053 [US4] Add secure configuration/credential backup and restore instructions to `deploy/README.md`, preserving current valid credentials, host ownership/modes and a verified selected digest while excluding request/media persistence; explain encrypted backup/access controls, optional diagnostic privacy and the lack of request resumption after restore.
- [ ] T054 [US4] Add project-scoped removal instructions to `deploy/README.md`, identifying retained host config/secrets, optional diagnostic storage and local images for explicit operator decisions; avoid host-wide prune or unrelated-service deletion and document safe restoration prerequisites if the operator retains configuration.
- [ ] T055 [US4] Document unexpected-exit/reboot recovery, intentional-stop behavior and upstream-outage handling in `deploy/README.md`, retaining `unless-stopped`, no health-only restart agent, no second process manager and no extra poller; provide separate runnable acceptance steps and expected outcomes for those three cases.
- [ ] T056 [US4] Expand the maintenance/real-network case register in `specs/008-public-docker-deployment/validation.md` and matching walkthrough in `specs/008-public-docker-deployment/quickstart.md` for T051–T055, keeping separate feature-acceptance/inherited-stable-readiness scopes and deployment-regression/evidenced-pre-existing-source/unclassified failure classifications alongside pending/pass/fail/blocked reasons, exact release/OS/architecture/Engine/Compose context and sanitized evidence distinct from controlled substitutes; carry forward existing source-category, two-account, timing, music and title/manual gates without marking them passed; state that feature completion requires successful feature-008 checks and representative real delivery plus an executed/assessed inherited matrix, while only evidenced pre-existing source limitations may remain inherited blockers on a completed preview feature.
- [ ] T057 [US4] Reconcile `README.md` deployment entry points, supported-source claims and preview/release status with `deploy/README.md` and the existing 001/005/006 validation records; replace stale assertions only with recorded evidence, link the published-image/local-build choices and source/verification guidance, and retain explicit limitations for any category or host combination lacking live proof.
- [ ] T058 [US4] Walk through the completed operator guide and `specs/008-public-docker-deployment/quickstart.md` for path/flag/settings consistency and shell syntax, check console/diagnostic privacy instructions against their contracts, and record the code-ready US4 checkpoint plus still-open T065–T066 gates in `specs/008-public-docker-deployment/validation.md` without claiming a real reboot/rotation/delivery was performed.

**Checkpoint**: Maintenance and readiness reporting are implemented. External operations,
media support and final status reconciliation remain the final phase's acceptance work.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validate the integrated candidate, publish only checked artifacts, exercise
the actual deployment, and reconcile public claims with evidence. External tasks require
the maintainer's release access and operator's acceptance environment/token. If a
feature-008 acceptance check is unavailable or fails, record the reason and leave its task
unchecked. T066 is an execution/assessment task: evidenced pre-existing source limitations
may remain open inherited gates after the matrix assessment completes. Deployment
regressions, unclassified failures, and missing execution/evidence still block completion.

- [ ] T059 Run `uv run --locked pytest`, `uv build`, both native restricted build/smoke jobs, SBOM/inventory/source validation and integrated release-policy checks for the final candidate revision after all story changes; record exact tested artifacts/results in `specs/008-public-docker-deployment/validation.md`, fixing failures in their owning paths and rerunning affected checks before publication rather than relying on an earlier revision's images.
- [ ] T060 Configure or verify canonical repository tag rules for maintainer-only `sources-VERSION`/version tag creation and immutability and required Actions/attestation/package privileges; verify public GHCR visibility if the package already exists, otherwise document the owner-controlled visibility bootstrap to perform at first package creation in T062; record actual settings/effective-permission evidence and capability limitations in `specs/008-public-docker-deployment/validation.md` and the bootstrap sequence in `deploy/README.md`, without treating a tag-prefix condition or public source repository as proof of authorization/public package access.
- [ ] T061 Audit `Dockerfile`, `deploy/compose.yaml`, `.github/workflows/ci.yml`, `.github/workflows/release.yml`, `release/source-policy.json`, `release/verification-policy.json` and produced release materials for actual full SHA/checksum/digest pins, effective least privilege, retained notices, complete matching sources, safe host configuration and no token/live-manifest/media leakage; record the review in `specs/008-public-docker-deployment/validation.md` and keep preview/version gating while any inherited external acceptance gate remains open.
- [ ] T062 Execute US1 public acceptance on the reviewed committed candidate: create the authorized matching sources/preview tag pair, rerun the complete pre-push gate set, publish completed source assets before images, promote both checked archives without rebuild and finalize the evidence-filled draft with immutable-release behavior enabled; perform the owner-controlled public-visibility bootstrap at first package creation before anonymous acceptance, prove credential-free both-platform pulls/material downloads and real raw-index/manifest local-bundle verification plus tampering/identity rejection, and confirm every pre-push gate failure causes zero image pushes, signing/image-access failure after push keeps the final release draft and distribution incomplete, and public-evidence failure after finalization prevents acceptance without overwriting versions/assets or withdrawing required source materials; if no compatible previous published image exists, publish a separately gated known-good baseline preview as well for T064, and record every source/child/index identity, workflow result and incomplete publication in `specs/008-public-docker-deployment/validation.md`.
- [ ] T063 Execute US2's clean-server guide on the operator's actual supported Ubuntu/architecture combination using T062's exact verified digest and protected real token; prove permissions, offline preflight, one successful polling owner, health and representative real Telegram delivery, and record OS/architecture/tool/network context and redacted results in `specs/008-public-docker-deployment/validation.md`; retain other untested combinations as pending and do not count a well-formed fake token as real startup acceptance.
- [ ] T064 Execute US3 real-host acceptance using current settings/credentials: failed pull/config leaves the old bot running; healthy update stops old before new and persists the right digest; failed/timed-out/interrupted starts stop explicitly; recorded previous digest rollback and old-project migration/recovery work; missing/incompatible previous images fail clearly; active-work shutdown exits within 20 seconds with no surviving children, scratch leakage, stale callback reuse or repeated uncertain delivery; record timings/identities and operator outcomes in `specs/008-public-docker-deployment/validation.md`.
- [ ] T065 Execute US4 maintenance acceptance on the isolated acceptance host: inspect safe health/log/resources, force-recreate after protected token-file rotation and confirm real use, verify unexpected-exit recovery, reboot recovery and intentional stop across reboot, observe upstream-outage degradation without health-triggered restart loops, and follow secure backup/restore/project-only removal with explicit retained-file inventory; record each observed result/limitation in `specs/008-public-docker-deployment/validation.md` and leave unsuccessful cases open.
- [ ] T066 Execute and assess representative real media and the inherited source/two-account/timing/music/title matrix from the deployment network using private manifests and permitted diagnostics, including existing anonymous YouTube video, YouTube Music audio, LinkedIn video/image and Instagram video/image journeys with native bytes/formats/titles and clear refusal/failure outcomes; record sanitized case IDs, actual evidence and blocked categories in `specs/008-public-docker-deployment/validation.md` and applicable earlier feature validation records, classify failures using earlier validation or an independent baseline and leave inherited source/live gates open when they fail rather than expanding access modes or counting substitutes; complete this assessment task only when every required matrix case has an executed outcome or evidenced pre-existing source-blocked outcome, representative real delivery passes, and no deployment regression or unclassified failure remains. A recorded known limitation does not pass its inherited gate, but does not keep this completed assessment task open; missing execution/evidence still does.
- [ ] T067 Reconcile `README.md`, `deploy/README.md`, release notes/evidence and `specs/008-public-docker-deployment/validation.md` with the FR/SC coverage below and actual T059–T066 outcomes; report controlled/native/public/live results separately, label partial publications incomplete and releases preview while any required gate is open, preserve immutable assets/tags, and finish the feature only after T059–T065 feature-008 acceptance passes and T066 execution/assessment is complete with no deployment regressions or unclassified failures. Evidenced pre-existing source limitations may remain open inherited stable-readiness gates on the completed preview feature, with corresponding capability claims withheld; do not require their remediation to complete deployment work or mark those gates passed.

**Checkpoint**: Feature-008 public distribution and deployment acceptance pass, and
the inherited matrix is executed/assessed. No documentation edit, skipped check or controlled
substitute closes an external gate. Keep unavailable/failing feature-acceptance tasks open;
T066 can complete with evidenced pre-existing source limitations still recorded as failed/blocked
inherited gates. Those gates continue blocking stable readiness and unsupported claims.

---

## Dependencies & Execution Order

### Phase Dependencies

Follow `CLAUDE.md`: implement one phase per invocation and commit at the phase boundary
using `feat(008): phase N ...`; preserve uncommitted user work. Phase progression is:

```text
Setup (T001–T003)
  -> Foundation (T004–T012)
  -> US1 release implementation (T013–T035)
  -> US2 secure installation (T036–T042)
  -> US3 updates / rollback / migration (T043–T050)
  -> US4 maintenance / readiness (T051–T058)
  -> Integrated/public/server gates (T059–T067)
```

Within a phase, only explicitly independent tasks can overlap. Cross-story code work
is sequential in this repository; the examples below describe potential concurrent
file work without requiring agents or overriding that agreement.

### Task Dependencies Within Phases

- Setup: T001–T003 have independent outputs; T002/T003 may overlap after starting T001.
- Foundation: T004/T005 can run together; T006 follows both; T007 follows T006.
  T008 follows T007, T009 follows T008, T010 follows T009, T011 follows T010,
  and T012 integrates all preceding foundation work.
- US1 tests: T013/T014/T015 can run together, with disjoint fixture subdirectories.
  Then T016/T017 can run together. T018 follows T013/T017; T019 follows T018;
  T020 follows T014/T016/T019; T021 → T022 follow T020;
  T023 follows T018–T022; T024 follows T015/T017/T023.
- US1 workflow: T025 follows T002/T010–T024; T026 → T027 → T028 → T029 → T030
  build on it. T031 → T032 → T033 → T034 → T035 close that phase. The actual
  workflow verifies both imports before either push and all shared gates before any push.
- US2: T036 → T037 → T038 → T039 → T040 → T041 → T042. The foundational token
  and image surfaces are reused; docs evolve in one file, so they are not parallel tasks.
- US3: T043 → T044 → T045 → T046 → T047 → T048 → T049 → T050.
  Operator update records are notes, not a new persisted application state machine.
- US4: T051 → T052 → T053 → T054 → T055 → T056 → T057 → T058.
- Final: T059 → T060 → T061 → T062 → T063 → T064 → T065 → T066 → T067.
  No actual publication occurs until the final committed candidate passes all required
  pre-push checks. Source availability and both import identities precede every image
  push; post-push signing/image checks precede finalization; public evidence checks after
  finalization precede accepted-public-release claims. T064 requires a recoverable previous image
  and old local installation; T065 uses a dedicated acceptance host for disruptive cases.

### User Story Dependencies and Independence

| Story | Shared inputs / earlier stories | Independent acceptance |
|---|---|---|
| US1 | Foundation; existing runtime | Credential-free exact releases and verified evidence; failure before push; T062 |
| US2 | Foundation + US1 published artifact | Clean-host installation, safe credential failures, real health/delivery; T063 |
| US3 | US2 running service + recoverable previous/local image | Healthy/failed update, bounded cleanup, explicit rollback/migration; T064 |
| US4 | US2 running service; US3 supplies recovery instructions | Inspect, rotate, recover/reboot, restore/remove, honest readiness; T065–T066 |

Each acceptance scenario can be exercised independently once its stated running/artifact
fixture exists; a public deployment story cannot claim independence from having an image
to deploy. Controlled test doubles do not remove its actual external acceptance gate.

### Parallel Opportunities

Marked tasks: T002/T003, T004/T005, T013/T014/T015, and T016/T017.
These groups touch distinct output files and require no result from another unfinished
member. Later source/validator/workflow edits and `deploy/README.md` sections share
files and remain sequential. Evidence writers to `validation.md` are always serialized.

## Parallel Example: User Story 1

After Foundation, T013 (manifest tests in `tests/unit/test_release_manifest.py`), T014
(collector tests in `tests/integration/test_release_tools.py`) and T015 (policy tests in
`tests/contract/test_release_policy.py`) can run concurrently with their distinct fixture
subdirectories. After those tests exist, T016 (`release/source-policy.json`) and T017
(`release/verification-policy.json` plus research evidence) can overlap. Import/push and
draft/publication operations remain ordered.

## Parallel Example: User Story 2

No concurrent implementation pair is safe in this phase as written: guide sections share
`deploy/README.md`, and integration checks depend on the completed settings/runbook.
The shared Foundation provides the already independent T004 configuration and T005
worker/diagnostic checks. During T040, native amd64 and arm64 smoke executions may run
as separate CI matrix jobs; aggregate their evidence serially.

## Parallel Example: User Story 3

T044–T047 all edit `deploy/README.md` and are sequential. Within T043, the independent
runtime and failure-cleanup test cases may be executed in separate processes using
isolated temporary directories; write their report once. Run update/rollback/migration
scenarios serially on a given token/host so they cannot create overlapping pollers.

## Parallel Example: User Story 4

Run maintenance steps serially on one host/token, especially rotation, reboot, restore
and removal. Read-only guide/requirements review can accompany a running CI matrix,
but it is not a separate `[P]` mutation task. External read-only source checks on separate
test environments may overlap only when existing source-rate rules are respected;
acceptance evidence is still consolidated by one writer.

---

## Requirement Coverage

| Requirements / outcomes | Primary tasks | Required actual acceptance |
|---|---|---|
| FR-001–FR-003, SC-001–SC-002 | T002, T013, T015, T017–T019, T024–T031 | T034, T059–T062 |
| FR-004, SC-002 | T003, T014, T016, T020–T023, T027, T032 | T034, T061–T062 |
| FR-005–FR-007, SC-003 | T008–T011, T037–T042 | T059, T063 |
| FR-008–FR-010, SC-004 | T004–T008, T010, T036–T040 | T012, T059, T063 |
| FR-011–FR-013, SC-005 | T039, T044–T046, T048–T050 | T064 |
| FR-014, SC-006 | T043, T045, T048–T049 | T064 |
| FR-015, SC-005 | T039, T044–T048, T052 | T064–T065 |
| FR-016, SC-007 | T008, T036, T051, T055 | T065 |
| FR-017, SC-003 | T031, T038–T039, T044–T047, T051–T055 | T063–T065 |
| FR-018 | T004–T006, T009–T012, T025, T034, T036, T040–T041 | T059 |
| FR-019–FR-020, SC-008 | T001, T026, T030, T035, T042, T050, T056–T058 | T062–T067 |
| FR-021, SC-008 | T007, T009–T012, T036, T041, T043, T049, T057 | T059, T063–T066 |

## Implementation Strategy

### MVP Scope and First Implementation Checkpoint

Complete Setup, Foundation and US1 for the first implementation checkpoint: both-architecture
build/release tooling, source materials and signed-evidence verification code. It is not a
publishable US1-only MVP under the sequential phase workflow. The first public preview
includes US2–US4 code and requires T059–T062 afterward; real-host feature acceptance then
requires T063–T065 and T066 matrix assessment. Do not jump to final-phase tasks after US1
or bypass either architecture, matching source or provenance gates. Stable promotion still
requires the inherited readiness gates to pass independently of preview feature completion.

### Incremental Delivery

1. Foundation establishes safe runtime secrets and executable offline container checks.
2. US1 adds the traceable distribution implementation and its controlled/native checks;
   actual public acceptance is T062 after all story code.
3. US2 makes that distribution installable on the actual target server.
4. US3 adds manual safe updates and explicit recovery, preserving cancellation semantics.
5. US4 supplies maintenance and evidence-aligned readiness; the final phase proves all
   integrated claims against the exact release and acceptance environment.

### Phase and Evidence Discipline

Run `$speckit-implement` for one phase at a time as `CLAUDE.md` requires. Mark a task
complete only after its stated work and checks are done. Record missing access, runners,
source archives, host or token as concrete pending/blocked evidence; do not mark real
acceptance tasks complete because a guide, fixture, or report exists. T066 can complete
only after actual execution/assessment; evidenced pre-existing limitations remain open
inherited gates and block stable readiness, while regressions/unclassified failures block
this feature. Keep immutable
release assets intact and retain sources even for incomplete/superseded publications.
Use `$speckit-analyze` before implementation to check artifact consistency.
Changes to image inputs or workflows after candidate verification invalidate the affected
checks: rerun those gates and use a new version if content was already published. Never
reuse an earlier revision's acceptance evidence for a changed artifact.

# Implementation Plan: Public Docker Deployment

**Branch**: `008-public-docker-deployment` | **Date**: 2026-10-28 | **Spec**: [spec.md](spec.md)

**Input**: `specs/008-public-docker-deployment/spec.md`; original [proposal.md](proposal.md).

## Summary

Publish checked, traceable multi-architecture images to public GHCR and provide a
digest-selected Compose deployment for one bare-metal server. Extend the existing
configuration loader for a file-backed runtime token. Preserve the current container
restrictions, one-poller lifecycle, Telegram behavior, and local-build workflow.

Build and smoke-test each architecture natively, transfer those tested images to the
release job without rebuilding, publish matching source/notices in a completed
sources-only release, then publish images and finalize the image release from a draft
with all signed evidence attached. Operators use documented manual preflight, stop/start,
180-second health wait, and explicit rollback. No deployment daemon or new runtime
service is introduced. Releases remain previews while external acceptance gates are open.
Image pushes follow the complete pre-push gate set. Signing/local verification and
anonymous image access then gate release finalization; public evidence download and
verification gate acceptance. A later failure leaves an incomplete distribution with
matching source retained, rather than a claim that no image was pushed.

## Technical Context

**Language/Version**: Python 3.13 application and CI source collection; standalone
standard-library release verification supports host Python 3.11+;
shell validation/operations commands; GitHub Actions YAML and Compose YAML.

**Primary Dependencies**: Existing python-telegram-bot==22.8, yt-dlp[default]==2026.8.19,
instaloader==4.15.3, regex==2026.8.31, and locked transitive packages. Existing image
pins: Python 3.13.15, uv 0.12.15, Deno 2.9.6, Debian FFmpeg 7:5.1.9-0+deb12u1;
retain exact Dockerfile digests. Build-only Syft 1.55.0, regctl 0.11.7, GitHub CLI
2.103.3, actions/attest 4.2.2; exact download checksums/full action SHAs are resolved,
reviewed, and committed during implementation. No new runtime dependency.

**Storage**: Bounded in-memory requests and 512 MiB `/tmp` tmpfs. Operator-owned
configuration and credentials on the host; optional diagnostic storage follows 002.
Public release assets contain inventories, notices, matching source, manifests, and
provenance. CI archives are temporary artifacts, never request/media persistence.

**Testing**: Existing pytest/pytest-asyncio controlled suite; token-loader unit and CLI
integration cases; native Docker smoke scripts with fake secrets and no network;
source/manifest and promotion checks; public anonymous retrieval and provenance checks.
Separate real-host/network polling, lifecycle, reboot, rollback, and media acceptance.

**Target Platform**: Rootful standard Docker Engine and Compose on Ubuntu 24.04/26.04
LTS, `linux/amd64` and `linux/arm64`. CI native `ubuntu-24.04`/`ubuntu-24.04-arm` runners.
Require actual installed Compose support for documented wait/run flags and record versions.
Rootless/user-namespace-remapped deployments are outside initial instructions.

**Project Type**: Existing Telegram polling bot with at most two source workers;
container distribution and server operations, not a new application interface.

**Performance Goals**: At most one poller per token; failed preflight interrupts no
running service. Candidate health deadline 180 seconds after start. Existing application
shutdown within 20 seconds, worker escalation after 5 seconds, deployment stop grace
30 seconds; no new media performance target.

**Constraints**: UID/GID 10001, read-only root, init, all capabilities dropped,
no-new-privileges, 2 CPUs, 2 GiB RAM including 512 MiB tmpfs, console logs 10 MiB × 3,
no application ports. Runtime secrets only; no source credentials or token-bearing
worker environment. Preserve 50,000,000-byte delivery cap, 128 MiB workspace,
60-second inspection, 600-second processing, and 900-second selection/cleanup contracts.

**Scale/Scope**: One server and polling container per token, manual updates with brief
downtime. Existing anonymous individual YouTube video, YouTube Music audio, LinkedIn
video/image, and Instagram video/image journeys, subject to recorded live limitations.
Native formats/bytes, stream-copy-only merges, current cards/titles, failure messages,
and cleanup remain unchanged. No bulk media, authenticated source access, or new platform.

## Constitution Check

Pre-research gates: PASS based on the accepted spec and existing architecture.
Post-design gates: PASS after the research, entities, contracts, and validation guide below.

| Principle / gate | Design evidence and implementation gate |
|---|---|
| I. Downloader purpose and explicit scope | Distribution operates existing source/media journeys; FR-021 and the validation matrix bound support claims |
| II. Telegram interface and separation | Only configuration loading changes application behavior; no adapter, card, or delivery redesign |
| III. Python and simplest architecture | Standard-library loader/collectors, one existing polling service, no database/queue/updater daemon |
| IV. Reuse, licenses, versions | Reuse existing media tools and Docker/GitHub tooling; build-only selections and redistribution coverage recorded in research |
| V. Container and runtime credentials | Native build/startup checks under production restrictions, runtime file secret, offline local preflight, documented storage |
| Native bytes, deadlines, capacity, cleanup | Inherited contracts stay authoritative; lifecycle/merge/cleanup regression checks and real-host shutdown acceptance required |
| Privacy and diagnostics | Early fixed configuration errors; existing repr/log redaction and minimal worker environment; optional diagnostics retain 002 contract |
| Controlled versus external evidence | PR/tag gates use substitutes; release record separately tracks network/host acceptance and inherited live gates; preview until complete |
| Workflow order and honest completion | This invocation stops after design; tasks and implementation follow; no build/deployment pass is claimed here |

No constitutional exceptions. Release hosting and ephemeral CI tools are distribution
infrastructure, not additional runtime services. Actual container/live checks remain
implementation and release gates rather than prerequisites to writing this plan.

## Project Structure

### Documentation (this feature)

```text
specs/008-public-docker-deployment/
├── proposal.md                     # unchanged original input
├── spec.md                         # existing approved requirements
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── configuration.md
│   ├── release.md
│   └── operations.md
└── checklists/requirements.md       # existing specification-quality review
```

`tasks.md` is generated next by speckit-tasks. `validation.md` is created during
implementation to record actual checks and open external gates.

### Source Code (repository root)

Planned files and affected existing surfaces, not files created by this invocation:

```text
.github/workflows/
├── ci.yml                          # read-only PR controlled/native checks
└── release.yml                     # tag checks, artifact promotion, evidence
deploy/
├── compose.yaml                    # published image, no build directive
├── deploy.env.example              # nonsecret image/settings interpolation
└── README.md                       # supported-host installation and operations
release/
├── source-policy.json              # unmanaged/base/embedded source coverage
└── verification-policy.json        # reviewed canonical repository/workflow identity
scripts/
├── smoke-container.sh              # restricted, network-free image checks
└── release/
    ├── collect_sources.py          # actual-image inventory and source assets
    └── validate_release.py         # inventory coverage, hashes, promotion identity
src/openmedia/config.py             # private token-file loader, existing Settings
tests/
├── unit/test_config.py             # token-file and backward compatibility
├── unit/test_release_manifest.py   # incomplete/tampered inventory rejection
├── integration/test_runtime.py     # CLI safety and inherited lifecycle regression
└── integration/test_release_tools.py # collector/promotion failure paths with fixtures
Dockerfile                         # retain pins; release metadata/notices as needed
compose.yaml                       # existing local build remains available
.env.example                       # document mutually exclusive token sources
.gitignore                         # exclude deployment secrets/state artifacts
.dockerignore                      # exclude new host config/release artifacts
README.md                          # entry point and evidence-aligned status
THIRD_PARTY_NOTICES.md              # actual closure/source-distribution instructions
specs/001-media-download/contracts/runtime.md # amend token interface by reference
```

**Structure Decision**: Keep the new runtime behavior inside configuration loading;
release/source tooling and Docker smoke validation stay outside the installed package.
Use manual documented Compose operations rather than a persistent updater. Production
deployment is separate from root Compose so existing local users retain their workflow.

## Phase 0: Research Outcome

[research.md](research.md) resolves native build promotion, package access, workflow
authority, source coverage, signed provenance and anonymous verification, token parsing,
host permissions, health timeout, and explicit recovery. No unresolved design questions.
The raw-index detached-bundle verification method has a mandatory implementation proof;
failure blocks the public verification gate and requires a corrected design, not a waiver.
This proof occurs after image push and before release finalization; it must not be
described as a pre-push check. Exact-version nonexistence is checked only in publisher
authorization before pushing. Shared record parsing and final assembly accept an existing
version whose expected identities match; operator verification additionally authenticates
its signatures. Final assembly does not depend on the signature it will produce afterward.

## Phase 1: Design Outcome

- [data-model.md](data-model.md) defines release/configuration/update/validation records,
  identities and transitions. These are file/CI concepts, not new application persistence.
- [Configuration contract](contracts/configuration.md) defines both token sources,
  bounded regular-file parsing, safe errors, Compose environment, and host ownership.
- [Release contract](contracts/release.md) defines prepublication gates, tested-image
  promotion, version identity, signed manifests, inventory/source assets, and public checks.
- [Operations contract](contracts/operations.md) defines installation, manual update,
  failure cleanup, rollback, migration, rotation, recovery, backup, and removal.
- [quickstart.md](quickstart.md) provides runnable future implementation validation.
  Commands that depend on planned files are explicitly identified as such.

### Delivery sequence for task generation

1. Extend configuration and its failure/redaction tests; amend the runtime token contract.
2. Add published-image Compose, host guide, isolated preflight, and native smoke tooling.
3. Add source inventory/policy/collection and fail-closed release validation, then CI checks.
4. Add privileged tag publication promoting checked artifacts, signed evidence, and
   anonymous access/verification checks. Configure tag rules and public package visibility.
5. Exercise server operations and representative real media; reconcile README and record
   unresolved inherited gates. Keep preview status until those gates actually close.

### Validation and requirement coverage

| Scope | Evidence required | Requirements |
|---|---|---|
| Public versions, trust, source assets | Same-run artifact identities; signed index/manifest; negative verifier cases; anonymous both-platform pulls and asset downloads | FR-001–FR-004 |
| Install and restrictions | Clean-host guide walkthrough; effective Compose config; both native image smoke reports; retain local-build path | FR-005–FR-007 |
| Runtime secrets | Unit cases for presence conflicts and bounded file parsing; CLI errors/tracebacks/logs/repr contain no secret; UID 10001 mount checks; workers receive neither input | FR-008–FR-010 |
| Preflight and update | Failed pull/config leaves old bot running; candidate has isolated tmpfs; old stopped before new; timeout/interruption explicitly stops candidate; previous digest recorded | FR-011–FR-012 |
| Recovery and migration | Current settings/token rollback; unavailable/incompatible previous image fails clearly; old project stopped first | FR-013–FR-015 |
| Operations | Local health only; outage has no restart loop; unexpected-exit/reboot recovery and intentional-stop cases; rotation recreates mount; backup/restore/removal walkthrough | FR-016–FR-017 |
| Controlled and live gates | Native builds/tools/storage/secrets; separate polling, child cleanup, active-work shutdown, failed update and real delivery records | FR-018–FR-019 |
| Honest status and media regression | Preview enforced; README agrees with evidence; inherited controlled/live matrix remains required | FR-020–FR-021 |

Native smoke runs use fake token files, `--network none`, actual production restrictions,
and commands overriding polling. Probe bundled Python/Deno/EJS/FFmpeg/ffprobe, a tiny
local stream-copy merge, read-only root, writable bounded tmpfs, UID/capabilities and
secret readability. Controlled runtime tests already cover heartbeat and real child-group
cleanup; preserve them and extend CLI/file-secret paths. No real token is placed in CI.
Smoke success is not proof of Telegram polling or media availability on a deployment host.

Record each OS/architecture combination separately. Both architectures require native
build/smoke evidence; the initial host acceptance can use the operator's actual target
combination, with other host combinations explicitly pending. Do not claim all four
OS/architecture combinations live-verified based on one server run. Preserve existing
source-category, two-account, timing, music, and title/manual gates from features 001–006.

Feature-008 completion requires passing controlled, native, public-release and actual
server installation/operations checks, representative real media delivery, and execution
and assessment of the inherited matrix. The gate register records `gate_scope` and
`failure_class`; earlier evidence or an independent baseline must establish any claimed
pre-existing source limitation. Such limitations may remain inherited stable-readiness
blockers after deployment work completes as a preview. Deployment regressions and
unclassified failures still block this feature. No gate is marked passed by reclassification.

The US1 phase is an implementation checkpoint, not an independently publishable MVP
under this repository's sequential phase workflow. The first public preview follows
US2–US4 implementation and the final integrated release gates; real deployment acceptance
then completes the feature. Stable promotion remains a separate all-readiness-gates decision.

## Complexity Tracking

No violations. Additional build-only inventory/signing tools satisfy explicit release
trust and redistribution requirements. No new runtime dependency or service is justified
or introduced. The source collector and detached-index verifier add bounded CI work;
their completeness and negative-path checks are publication gates.

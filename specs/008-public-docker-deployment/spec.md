# Feature Specification: Public Docker Deployment

**Feature Branch**: `008-public-docker-deployment`

**Created**: 2026-10-28

**Status**: Draft

**Input**: [Original agreed deployment proposal](proposal.md), retained unchanged.

**Extends**: Features 001–006 with public release distribution and single-server
self-hosting. Existing Telegram journeys, source access rules, native media delivery,
diagnostic privacy, and bounded runtime behavior remain in force. This specification
defines deployment requirements; it does not claim that deployment has been verified.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Obtain an identifiable public release (Priority: P1)

A self-hosting operator obtains a published release without a registry account,
identifies exactly which release will run, and checks its origin and included components.
A maintainer checks artifacts before image publication and completes the later
verification stages before advertising an accepted release.

**Why this priority**: Public self-hosting requires an accessible, traceable release
that operators can select and keep fixed until they choose to update.

**Independent Test**: From a clean registry client with no credentials, retrieve an
exact release for each supported architecture, inspect its release evidence, and follow
the origin-verification instructions. Exercise a failing release check separately.

**Acceptance Scenarios**:

1. **Given** a published release, **When** an operator retrieves it anonymously for
   either supported architecture, **Then** retrieval succeeds and the exact version,
   immutable digest, and source revision are identifiable.
2. **Given** a pull request or ordinary branch update, **When** checks run, **Then**
   controlled tests and container smoke checks run without publishing a release.
3. **Given** a maintainer-created version tag, **When** any required pre-push check
   fails, **Then** no image is pushed; when those checks pass, the checked images may
   be pushed and their exact version and digests recorded for subsequent verification.
4. **Given** a release and its signed build provenance, **When** the operator follows
   the verification instructions, **Then** the expected project, source revision, and
   release identity verify; evidence for another artifact or publisher is rejected.
5. **Given** a release, **When** its distribution materials are inspected, **Then**
   its software inventory, third-party notices, and matching source materials required
   by repository redistribution policy are available.
6. **Given** an outstanding container or live acceptance gate, **When** the release
   and deployment documentation are read, **Then** the release is identified as a
   preview and the unresolved gate is stated without implying verified support.
7. **Given** release automation configuration, **When** a maintainer reviews its
   dependencies and permissions, **Then** dependencies have immutable references
   and only release publication jobs have publishing permissions.
8. **Given** images already pushed, **When** signing, verification, or public-access
   checks fail, **Then** the release is identified as incomplete, is not advertised as
   accepted, retains its required source materials, and has no published version or
   immutable evidence silently replaced.

---

### User Story 2 - Start the bot securely on a server (Priority: P1)

An operator follows the installation guide on a supported bare-metal server, supplies
their own bot token, validates settings, and starts one bot using a published release.
The operator does not need to build the application or install its bundled tools.

**Why this priority**: A downloadable release is useful only if an operator can start
it with readable credentials, bounded resources, and the existing protections intact.

**Independent Test**: Follow the guide on a clean supported host using a published
release and an operator-owned token. Check configuration before starting, then confirm
polling, health, and a representative Telegram delivery. Exercise invalid secrets in
controlled checks without contacting Telegram.

**Acceptance Scenarios**:

1. **Given** a supported host with outbound connectivity, **When** the operator follows
   the documented installation and startup steps, **Then** one healthy bot runs from
   the selected digest without a local application build or published application ports.
2. **Given** a valid token file readable by the application identity, **When** the
   deployment validates and starts, **Then** it uses that runtime secret without
   embedding the token in the image, tracked configuration, or logs.
3. **Given** a missing, unreadable, empty, or malformed token file, or both token
   inputs supplied, **When** configuration is checked or startup is attempted,
   **Then** it fails before polling with a redacted explanation of the configuration
   problem. No token value or file contents appear in errors or representations.
4. **Given** only the existing direct token setting, **When** an existing installation
   validates and starts, **Then** that setting remains supported.
5. **Given** host ownership that prevents the application from reading the secret,
   **When** the operator follows the permissions guidance, **Then** the application
   can read the file without granting unrelated host users access to its contents.
6. **Given** production restrictions, **When** runtime checks and a controlled job
   run on either supported architecture, **Then** required bundled tools work,
   temporary storage is writable and bounded, the restrictions remain active,
   and startup downloads no executable components.
7. **Given** existing supported media and refusal/failure examples, **When** they
   are exercised through the deployed bot, **Then** successful deliveries retain
   native formats, bytes, titles, and delivery types, while invalid links, unsupported
   content, unavailable sources, limits, and download/send failures retain their
   existing explanations and next steps. Live limitations are recorded separately.

---

### User Story 3 - Update deliberately and recover a previous release (Priority: P2)

An operator chooses when to update, validates the candidate before interrupting service,
and can restore the previous release if the candidate does not become healthy.

**Why this priority**: Operators need predictable downtime and an explicit recovery
path without overlapping consumers of the same bot token.

**Independent Test**: Start from a known healthy deployment and follow the update
procedure once with a healthy candidate and once with a candidate that fails startup
or never becomes healthy. Repeat using the existing local-build installation as the
migration source.

**Acceptance Scenarios**:

1. **Given** a healthy running deployment, **When** a candidate cannot be downloaded
   or fails local configuration validation, **Then** the current bot keeps running
   and candidate validation starts no poller.
2. **Given** a candidate that passes preflight, **When** the operator updates,
   **Then** the current digest is recorded, the old bot stops before the candidate
   polls, and success is reported only after the candidate becomes healthy within
   the documented finite timeout.
3. **Given** active work during an update, **When** the bot stops, **Then** admission
   stops, active work and child processes are canceled and cleaned up under the
   existing shutdown contract, and users must resubmit after startup. Work is not resumed
   or automatically sent again.
4. **Given** candidate startup failure or expiry of the health timeout, **When**
   the update fails, **Then** the candidate is stopped and the operator receives
   explicit rollback steps selecting the recorded previous digest with current
   configuration and credentials.
5. **Given** the previous release is available and compatible with current settings,
   **When** the operator follows rollback steps, **Then** exactly one healthy bot
   runs the previous release without resurrecting canceled requests.
6. **Given** the current local-build Compose installation, **When** the operator
   migrates, **Then** its poller is stopped before the published-release deployment
   starts, and the guide provides a path back to the previous installation.

---

### User Story 4 - Operate the service and assess readiness (Priority: P2)

An operator inspects health, logs, and resource use; rotates credentials; recovers after
a process failure or reboot; and removes or restores the deployment using documented steps.
Maintainers distinguish controlled validation from evidence on the deployment network.

**Why this priority**: Routine maintenance and honest readiness reporting are needed
to keep a public deployment usable beyond its first startup.

**Independent Test**: On a running deployment, follow each maintenance procedure and
record the observed outcome. Simulate a process exit, an upstream outage, a host reboot,
and an intentional stop; review the resulting release validation record.

**Acceptance Scenarios**:

1. **Given** a running bot, **When** the operator inspects status, console logs, and
   resource use, **Then** the documented procedures expose health and usage without
   revealing credentials, submitted links, or Telegram identifiers in the console.
2. **Given** a temporary upstream outage, **When** health degrades, **Then** status
   reflects it without starting another poller or restarting solely because of
   unhealthy status. Polling can recover when connectivity returns.
3. **Given** an unexpected process exit or host reboot, **When** recovery occurs,
   **Then** the configured deployment starts again; an intentionally stopped service
   remains stopped until the operator starts it.
4. **Given** a replacement token, **When** the operator follows rotation steps,
   **Then** the replacement is used after restart and the previous token is not
   retained in release artifacts, logs, or tracked configuration.
5. **Given** backed-up configuration and securely stored credentials, **When** the
   operator follows restore or removal instructions, **Then** restoration requires
   no request or media backup, and removal explains which configuration and secret
   files remain for explicit operator retention or deletion.
6. **Given** controlled checks and separate deployment-network checks, **When**
   maintainers review release readiness, **Then** each gate has a recorded pass,
   failure, or pending result with its environment and limitations; public guidance
   agrees with that evidence.
7. **Given** all feature-008 acceptance checks pass and the inherited acceptance
   matrix has been executed and assessed, **When** only evidenced pre-existing source
   limitations remain, **Then** deployment work can be complete as a preview while
   those inherited stable-readiness gates remain open. An unexplained failure or a
   regression introduced by deployment changes still blocks feature completion.

### Edge Cases

- Registry credentials are absent, access is denied because package visibility is
  wrong, an architecture is missing, or the selected digest is unavailable: retrieval
  fails clearly; preflight does not interrupt the existing bot.
- A version tag resolves to different content later: the deployment continues to use
  its selected digest until the operator explicitly changes it.
- Secret files are directories, missing, unreadable, empty, or malformed; both inputs
  are present even if one is empty: configuration is rejected without secret disclosure.
- A token file is locally well formed but rejected by Telegram: local preflight does
  not claim remote validity; startup fails safely without reporting readiness.
- Host secret permissions differ from the operator's own access: readability is
  checked for the application identity, and host storage is not described as encrypted.
- Candidate preflight passes but real startup or polling fails: the health timeout
  remains bounded, the candidate stops, and rollback is an explicit operator action.
- A previous digest is unavailable or incompatible with current settings: rollback
  reports failure rather than claiming restoration or silently changing credentials.
- Another installation already uses the token: instructions require stopping that
  poller first; the procedure must never deliberately overlap pollers.
- Temporary storage is exhausted, a worker ignores termination, or an upload outcome
  is uncertain during shutdown: existing limits, forced child cleanup, and no automatic
  duplicate-send rules apply. Restart discards previews and active requests.
- Diagnostic logging is enabled: its existing separate storage, access, retention,
  and privacy contract applies; default deployment keeps it disabled.
- Upstream restrictions block a source on the deployment network: record the limitation
  and keep the relevant release gate open; a passing controlled substitute is not live evidence.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Operators MUST be able to retrieve `ghcr.io/hman-pro/openmedia` publicly
  without authentication for both `linux/amd64` and `linux/arm64`. Releases MUST have
  exact version tags, recorded immutable digests, and source revision metadata.
- **FR-002**: Pull requests MUST run controlled tests and container smoke checks.
  Image pushes MUST occur only for maintainer-created version tags after required
  pre-push checks rerun successfully: controlled tests, both native architecture
  builds/smoke checks, inventories and source/notice coverage, release authority/pins,
  public source-material availability, and identity checks for both tested architecture artifacts.
  Failure of any pre-push check MUST prevent every image push for that attempt.
- **FR-003**: Each release MUST include a software bill of materials, signed build
  provenance, and instructions verifying the expected publisher, source, and artifact
  identity. Mismatched evidence MUST fail verification. Release automation dependencies
  MUST be pinned immutably, and publishing permissions MUST be restricted to release jobs.
  Signed evidence, local verification, and anonymous image retrieval MUST pass before
  release finalization; public evidence downloads and their verification MUST pass
  before release acceptance. Later failures MUST mark the release incomplete rather
  than imply that already pushed images were never distributed.
- **FR-004**: Distribution MUST preserve third-party notices and provide matching
  source materials required by the repository's [redistribution policy](../../THIRD_PARTY_NOTICES.md).
  Required source materials MUST be publicly available before the first image push
  and retained for distributed images even when later release checks fail.
- **FR-005**: A standalone published-image deployment definition at `deploy/compose.yaml`
  and installation guide MUST allow startup without building the application locally.
  Production examples MUST select an immutable digest. The existing local-build
  workflow MUST remain available.
- **FR-006**: The guide MUST cover standard Docker Engine with the Compose plugin
  on Ubuntu 24.04 and 26.04 LTS using Docker's official package repository, including
  prerequisites, outbound access, startup, configuration, and storage requirements.
- **FR-007**: Deployment MUST retain application UID/GID 10001, a read-only root
  filesystem, dropped capabilities, prevention of privilege escalation, child-process
  reaping, bounded console logs, and no published application ports. Initial limits
  MUST remain 2 CPUs, 2 GiB RAM, 512 MiB temporary filesystem, and 30-second stop grace.
  Guidance MUST explain that temporary filesystem usage consumes the memory budget.
- **FR-008**: The application MUST accept a runtime token through
  `TELEGRAM_BOT_TOKEN_FILE` while preserving `TELEGRAM_BOT_TOKEN` compatibility.
  Supplying both settings MUST be rejected, including when one is empty. The published
  deployment MUST supply the file as a read-only Compose secret.
- **FR-009**: Missing, unreadable, empty, or malformed token files MUST cause a
  nonzero configuration/startup result before polling, with a redacted actionable
  error. Token values and file contents MUST be absent from logs, errors, and object
  representations, and tokens MUST NOT reach source workers or distribution artifacts.
- **FR-010**: Secret instructions MUST specify host ownership and permissions that
  allow UID 10001 to read the token while excluding unrelated host users, and explain
  that file-backed secrets preserve host ownership and do not encrypt host storage.
- **FR-011**: Operators MUST be able to download and locally validate a candidate
  without polling or stopping the running bot. Failed download or validation MUST
  leave the current service running. Local validation MUST NOT imply remote token validity.
- **FR-012**: Updates MUST be operator initiated. The update procedure MUST record
  the current digest, stop the current bot before candidate polling starts, and wait
  for candidate health using a documented finite timeout. A failed or timed-out
  candidate MUST be stopped, and explicit rollback instructions MUST be provided.
- **FR-013**: Rollback MUST select the recorded previous digest using current
  settings and credentials. The procedure MUST validate those settings and confirm
  health before declaring success; unavailability or incompatibility MUST be reported.
- **FR-014**: Stop and update behavior MUST retain the existing runtime contract:
  cease admission, cancel active work, terminate and reap child processes, close uploads,
  and clean scratch files, with application exit within 20 seconds and 30 seconds of
  deployment stop grace. Restart MUST discard request state and stale callbacks;
  guidance MUST tell users to resubmit and MUST NOT promise resumed or repeated sends.
- **FR-015**: Migration instructions MUST stop the existing local-build poller
  before activation and provide recovery steps. Installation, migration, update,
  rollback, and credential rotation procedures MUST maintain at most one poller per token.
- **FR-016**: Deployment MUST retain `restart: unless-stopped` recovery behavior.
  Health inspection MUST start no poller. Unhealthy status alone MUST NOT trigger
  restart loops during upstream outages; intentional stops MUST be respected.
- **FR-017**: Operator documentation MUST cover token rotation, logs, health,
  resource usage, updates, rollback, secure configuration/credential backup and restore,
  and removal. Media and request state MUST remain ephemeral and need no backup.
  Console privacy and opt-in diagnostic logging MUST retain their existing contract.
- **FR-018**: Controlled validation MUST cover token-file loading, conflicting
  inputs, redacted errors and representations, and backward-compatible direct tokens.
  Both architectures MUST pass build and smoke checks under production restrictions,
  including bundled-tool availability, writable bounded temporary storage, and secret
  readability by the application identity. Startup MUST need no executable downloads.
- **FR-019**: Separate deployment-network validation MUST record real polling and
  health, active-work shutdown, child cleanup, reboot recovery, failed updates,
  rollback, and representative media delivery. Records MUST identify release, host
  architecture, environment, result, and remaining limitations. Existing live/manual
  acceptance gates MUST remain open until supported by their required evidence.
  Gate records MUST distinguish feature-008 acceptance from inherited stable-readiness
  obligations, and classify failures as deployment regressions, evidenced pre-existing
  source limitations, or unclassified. All feature-008 checks and representative real
  delivery MUST pass, and the inherited matrix MUST be executed and assessed, before
  this feature is complete; unclassified failures and deployment regressions block it.
- **FR-020**: Releases MUST remain marked as previews until outstanding container
  and live acceptance gates pass. README and deployment claims MUST be reconciled
  with recorded evidence; controlled checks MUST NOT substitute for live acceptance.
  Evidenced pre-existing source limitations MAY remain open after feature-008 completion
  but MUST continue to block stable readiness and unsupported capability claims.
- **FR-021**: Deployment MUST preserve the existing Telegram journeys for public,
  anonymous single-item YouTube video, YouTube Music audio, LinkedIn video/image, and
  Instagram video/image, subject to their recorded support limitations. Native output
  formats and bytes, stream-copy-only merges, title/caption behavior, delivery limits,
  deadlines, and bounded state MUST remain unchanged. Invalid or unsupported links,
  inaccessible content, size limits, and download/send failures MUST retain their
  existing clear explanations and next steps.

For these requirements, **image publication** begins with the first registry image push.
**Release finalization** makes the complete listing for the images and their evidence
public after its signing, local-verification and anonymous-image checks pass. **Release acceptance**
additionally requires successful public evidence retrieval/verification; an accepted
preview can still have explicitly recorded inherited stable-readiness limitations.
Incomplete artifacts are never advertised as accepted releases.

### Key Entities

- **Published release**: A versioned distribution with supported architectures,
  immutable digest, source revision, component inventory, provenance, notices, and
  required matching source materials.
- **Deployment configuration**: Operator-owned settings identifying the selected
  release, runtime limits, secret reference, and optional diagnostic storage.
- **Runtime credential**: An operator-supplied bot token obtained from exactly one
  supported input, readable by the application and excluded from public artifacts.
- **Update record**: The previous and candidate release identities, preflight result,
  startup/health outcome, and information needed for explicit rollback.
- **Validation record**: Evidence tied to a release and environment, distinguishing
  controlled checks, deployment-network checks, feature-008 acceptance and inherited
  stable-readiness gates, with an evidence-backed classification for failures.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: An operator with no registry account retrieves the exact selected
  release for every supported architecture, with zero local application builds.
- **SC-002**: Every accepted release has verifiable source and publisher identity,
  a component inventory, notices, and required source materials. Every failed pre-push
  case produces zero image pushes; every later signing, verification, or public-access
  failure prevents acceptance and leaves the release explicitly incomplete.
- **SC-003**: An operator following only the guide completes installation, token
  rotation, health/log/resource inspection, backup/restore, update, rollback, migration,
  and removal without undocumented steps in the acceptance walkthrough.
- **SC-004**: All missing, unreadable, empty, malformed, and conflicting credential
  cases fail before polling, with zero token disclosures across captured output and
  representations. Every valid single-input case passes local credential validation.
- **SC-005**: Every update and migration acceptance run has at most one active poller
  per token. Failed preflight causes zero service interruption; failed startup is
  reported within the documented timeout and leaves the candidate stopped. A rollback
  to an available compatible previous release restores healthy service.
- **SC-006**: Active-work shutdown acceptance runs exit within 20 seconds, leave
  zero child processes running, and automatically repeat zero uncertain or canceled
  deliveries. Users can submit fresh requests after recovery.
- **SC-007**: Process-failure and reboot acceptance cases recover service, intentional
  stops remain stopped, and the upstream-outage case causes zero health-triggered
  restarts or additional pollers.
- **SC-008**: Every supported source/media journey retains its controlled acceptance
  outcome. Every publicly claimed deployment-network media capability has a recorded
  successful real delivery; all unresolved gates and observed source limitations
  appear consistently in release status and public guidance. Feature completion has
  zero deployment regressions or unclassified failures, passing feature-008 checks
  and representative real delivery, and an executed/assessed inherited matrix;
  evidenced pre-existing source limitations may remain recorded stable-readiness blockers.

## Assumptions

- Operators administer their own single server and token, can install system packages,
  and provide outbound access to the registry, Telegram, and supported media sources.
  Host administration and recovery remain operator responsibilities.
- Confirmed delivery constraints from the proposal are GitHub Actions publication to
  public GHCR, standard Docker Engine and Compose, file-based secrets, manual updates,
  and brief downtime. Workflow actions use full commit SHA pins. Planning will define
  the workflow layout, commands, health-wait timeout, verification procedure, and
  validation matrix without reopening those confirmed choices.
- A single polling application remains the deployment unit. Managed hosting, automatic
  updates, multiple replicas, zero-downtime handover, orchestration services, new inbound
  interfaces, databases, and durable request/media storage are outside scope.
- Existing [runtime](../001-media-download/contracts/runtime.md),
  [diagnostic logging](../002-file-logging/contracts/diagnostic-log.md), and features
  003–006 presentation/delivery contracts remain dependencies. Optional diagnostic
  storage is the existing exception to otherwise ephemeral application storage.
- Source access remains anonymous and limited to existing supported individual media.
  Native video, audio, and image formats are preserved; no new platform, format,
  private access, supplied source credentials, playlist, bulk download, or transcoding
  support is introduced. Source availability varies by item and deployment network.
- Maintainers can configure public package visibility and release permissions. Actual
  publication and server acceptance require registry access and an operator-provided
  deployment environment and token; this specification creates neither credentials
  nor evidence that those gates have passed.
- The separate `007-local-server-deploy` SSH-tooling branch is outside this feature.
  Its work is preserved; this specification uses only `008-public-docker-deployment`.

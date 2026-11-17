# Server Operations Contract

This is the design for the operator-facing `deploy/README.md`. Commands and scenarios
in [quickstart.md](../quickstart.md) validate its future implementation. All service
operations are deliberate operator actions; no remote deployment or update daemon exists.

## Installation and selection

- Support standard rootful Docker Engine and Compose on Ubuntu 24.04/26.04 LTS,
  amd64/arm64, installed from Docker's official repository. Record OS, architecture,
  Engine/Compose versions and support for required wait/run flags. Explain outbound
  access and avoid adding inbound application ports or another process manager.
- Install the reviewed Compose definition and nonsecret settings under `/opt/openmedia`.
  Use `-p openmedia`, explicit `-f /opt/openmedia/compose.yaml`, and
  `--env-file /opt/openmedia/deploy.env` for every operation. Do not rely on working
  directory, implicit project naming, or a lingering exported image variable.
- Select a verified immutable image digest. The host environment file contains
  `OPENMEDIA_IMAGE`, `OPENMEDIA_TOKEN_FILE`, and allowed nonsecret settings only.
  Production examples have no floating tag fallback. Validate image-reference shape
  before a pull or activation; Compose's required-variable syntax alone does not
  validate a digest. Document a literal digest replacement and the verifier path.
- Provision the secret using protected input/editor, never a literal token in a
  command, shell history, repository, or process argument. Apply the ownership and
  mode from [configuration.md](configuration.md) and verify as the application identity.
- Pull, locally validate, and start one service with a 180-second health deadline.
  Local preflight starts no poller and cannot prove Telegram credential validity.
  Start only after checking that no other installation uses the token.

## Candidate preflight

Choose the candidate by a command-scoped `OPENMEDIA_IMAGE` override. Leave selected
`deploy.env` unchanged until activation succeeds. Use Compose `pull openmedia`, followed
by `run --rm --no-deps -T --pull never openmedia python -m openmedia --check-config`.
The one-off inherits secrets, identity and restrictions, but has its own tmpfs and
overridden nonpolling command. It must not mount the running bot's scratch directory.

Failure to pull, verify, or validate leaves the old service and selected configuration
unchanged. Report the failure and stop the procedure. Never use `up` as validation.

## Update state machine and failure behavior

1. Verify release identity/evidence and complete candidate preflight.
2. Inspect the actual existing container, record its `.Config.Image`, `.Image` content
   ID, container ID, and nonsecret settings identity. For the published workflow the
   image reference must already be digest-qualified; do not trust a stale env file.
3. Stop the current service with a 30-second timeout and confirm its container is
   no longer running. Keep the previous image locally for rollback. Stop failure
   aborts activation; do not start a second poller.
4. Start the candidate using `up --no-build --pull never --force-recreate --wait
   --wait-timeout 180 openmedia`. Health succeeds only through the existing parent
   heartbeat and successful polling history, not through a second network health probe.
5. On a nonzero result, timeout, interruption, or unexpected startup exit, explicitly
   stop the candidate and confirm it is stopped. A failed Compose wait does not
   guarantee that cleanup. Give explicit rollback instructions and preserve evidence.
6. After successful health, atomically persist only the selected image setting in
   `deploy.env`, preserving current other settings and protected ownership/mode.
   Verify persisted selection equals the running digest. Persistence failure is a
   reported incomplete update, even if the candidate is healthy.

Document the cleanup command next to the start command so an interrupted terminal
session has an explicit recovery step. On uncertain interruption, inspect and stop the
candidate before any recovery startup. Updates are not concurrency-safe against another
operator: require a single operator/change session, and document checking other projects.

Existing shutdown cancels active work, reaps child groups, closes uploads and removes
scratch files within the 20-second application budget. Users resubmit afterward.
No request/selection resurrection or automatic uncertain upload retry is introduced.

## Explicit rollback

Use the recorded previous digest with the current environment/settings and current
credential file. Ensure the candidate is stopped, pull if necessary, rerun local
validation, then start/recreate with the same 180-second health wait. Confirm the running
image and persist the previous selection after health succeeds. Never restore old token
contents or old settings automatically. If validation or health fails, stop that failed
attempt too and report rollback failure; do not claim restoration.

An unavailable or incompatible previous image is an explicit recovery limitation.
Do not prune the previous release until the operator has accepted the update. No automatic
rollback occurs merely because a healthy bot later becomes unhealthy during an outage.

## Migration from root Compose

Identify the actual old project/container and its root Compose/env files. Retain their
protected configuration and local image content ID. A locally built image may lack a
registry digest; preserve/tag that local content ID for recovery and do not fabricate
a GHCR digest. Preflight the new deployment without polling; stop the old project's
service and confirm it stopped before starting project `openmedia`.

If activation fails, stop the new candidate and use the preserved old project/configuration
and pinned local image for recovery with current credentials/settings where compatible.
Verify health before declaring recovery. Do not start both projects. The existing
`007-local-server-deploy` SSH-tooling branch is neither changed nor merged by this work.

## Credential rotation

Prepare the replacement token in a protected temporary host file with correct ownership
and permissions. Stop the polling service, replace the host secret, rerun local validation,
and **force-recreate** the service even if the image/settings did not change. Confirm health.
Atomic replacement can leave an existing bind mount pointing to the previous file;
`restart` alone is insufficient. Remove temporary credentials securely according to
host storage/backup practices; do not print old or new token values.

Rotation is not complete until the replacement is accepted by Telegram and normal polling
is healthy. If it fails, keep the failed service stopped and correct the current credential.
A software rollback still uses that current credential; it does not revive a revoked token.

## Health, logs, and resource inspection

Document `compose ps`, container health inspection, bounded `compose logs`, and
`docker stats --no-stream`. Avoid full environment dumps, debug HTTP logs, or rendering
an enabled diagnostic file into public console evidence. Console output must retain
the existing no-links/no-identifiers/no-token policy. Diagnostic logging remains off
unless the operator explicitly provisions its protected storage/retention contract.

`--healthcheck` is local and starts no poller. An upstream outage can make status unhealthy
without exiting. Retain `restart: unless-stopped` for unexpected exits and host reboot,
and do not attach an autoheal agent. An intentionally stopped service remains stopped
across daemon/host restarts. Validate those behaviors as separate cases.

Explain that the 512 MiB tmpfs consumes the 2 GiB container memory limit and is temporary,
and that changing limits requires respecting existing workspace and delivery constraints.

## Backup, restore, and removal

Back up reviewed Compose/nonsecret configuration and credentials using host access controls
and encrypted backup storage chosen by the operator. Treat any backup containing a token
as a credential. Request state and media are ephemeral; do not add them to backups.
Optional diagnostic files have their existing privacy/retention obligations and are
not needed for service restoration.

Restore configuration and current valid credentials with correct permissions, select
the intended verified digest, preflight, then start and confirm health. Restoring a
deployment never resumes old requests. Removal stops and removes only the identified
Compose project; document the configuration, secret, optional log storage, and image
files that remain for explicit retention/deletion. Avoid broad host-wide prune commands.

## Acceptance evidence

Record actual source/image identity, architecture, OS and tool versions, network context,
sanitized outcome, observed shutdown/health timing, and unresolved gates. Real acceptance
must exercise polling/health, active-work shutdown and child cleanup, unexpected exit,
host reboot and intentional stop, failed preflight/startup, explicit rollback, migration,
rotation, backup/restore/removal, and representative Telegram media delivery.

Do not infer real polling, source availability, two-account isolation, native media
delivery, or reboot recovery from controlled substitutes. Each claimed OS/architecture
combination needs its own evidence; mark other combinations pending. Reconcile README,
operator guidance, and preview release status with inherited feature validation records.
Mark server installation, update/recovery, maintenance, and representative actual delivery
as feature-008 acceptance gates requiring success. Execute and assess the inherited media
matrix separately. An evidenced pre-existing source limitation can remain an open inherited
stable-readiness gate after this deployment feature completes as a preview; unclassified
failures and deployment regressions must be resolved before feature completion. Record the
baseline/earlier evidence for each classification and do not relabel failed gates as passed.

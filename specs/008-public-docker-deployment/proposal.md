# Public Docker deployment on a bare-metal server

**Recorded**: 2026-10-28

**Branch**: `008-public-docker-deployment`

**Status**: Agreed deployment proposal; input for `$speckit-specify`, not a generated specification or Spec Kit implementation plan.

## Summary

Use **GitHub Actions → public GHCR images → Docker Compose on the server**, with operator-controlled updates.

This fits OpenMedia's existing architecture: one polling container, bounded temporary storage, and outbound network access. Docker supports Compose for single-server production deployments. [Docker guidance](https://docs.docker.com/compose/how-tos/production/).

The existing Dockerfile and Compose restrictions provide a strong starting point. The main gaps are image publication, file-based secrets, operational documentation, and deployment validation.

## Release distribution

- Publish `ghcr.io/hman-pro/openmedia` for `linux/amd64` and `linux/arm64`. Make package visibility public and verify anonymous pulls. [GHCR documentation](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry).
- Run controlled tests and container smoke checks on pull requests. Publish only from maintainer-created version tags; rerun checks before publication.
- Publish exact version tags and record the image digest. Production examples select a digest rather than a floating tag.
- Include source revision metadata, an SBOM, and signed build provenance with verification instructions. Pin workflow actions to full commit SHAs and grant publishing permissions only to release jobs. [GitHub publishing guidance](https://docs.github.com/en/actions/tutorials/publish-packages/publish-docker-images).
- Preserve third-party notices and package matching source materials required by the repository's redistribution policy.
- Keep releases marked as previews until the outstanding container and live acceptance gates pass.

## Server configuration and interfaces

- Add a standalone `deploy/compose.yaml` that pulls a published image. Keep the existing local-build workflow available.
- Document standard Docker Engine and the Compose plugin on Ubuntu 24.04/26.04 LTS, installed through Docker's official package repository. [Installation guidance](https://docs.docker.com/engine/install/ubuntu/).
- Retain UID/GID 10001, read-only root filesystem, dropped capabilities, `no-new-privileges`, init, bounded console logs, and no published application ports.
- Retain initial container limits: 2 CPUs, 2 GiB RAM, 512 MiB temporary filesystem, and 30-second stop grace. Explain that temporary filesystem usage consumes the memory budget.
- Add `TELEGRAM_BOT_TOKEN_FILE`, using a read-only Compose secret. Preserve `TELEGRAM_BOT_TOKEN` compatibility; reject configurations supplying both. Missing, unreadable, empty, or malformed token files produce redacted errors.
- Document host ownership and permissions explicitly: file-backed Compose secrets preserve host ownership, so UID 10001 must be able to read the token. Compose secrets do not provide encrypted host storage. [Secret handling](https://docs.docker.com/compose/how-tos/use-secrets/).

## Operations

- Document installation, token rotation, logs, health inspection, resource usage, updates, rollback, and removal.
- Update sequence: download the candidate, validate configuration without polling, record the current digest, stop the old container, then start the candidate and wait for health with a bounded timeout.
- Maintain one poller per token. Updates retain the accepted behavior: active work is canceled and users resubmit afterward.
- On failed candidate startup, stop it and provide explicit rollback to the previous digest using current settings and credentials.
- Keep `restart: unless-stopped` for process recovery and reboot behavior. An unhealthy status alone must not trigger restart loops during upstream outages. [Restart-policy guidance](https://docs.docker.com/engine/containers/start-containers-automatically/).
- Back up deployment configuration and credentials securely; media and request state remain ephemeral.
- Document migration from the current Compose installation, including stopping its poller before activation.

## Validation and defaults

- Test token-file loading, conflicting configuration, safe errors, and token redaction.
- Build and smoke-test both architectures under production restrictions; verify bundled tools, writable temporary storage, and secret permissions.
- Separately verify real polling, health, active-work shutdown, child cleanup, reboot recovery, failed updates, rollback, and representative media delivery on the deployment network.
- Reconcile stale README deployment statements with recorded evidence.
- Use a separate public-release feature branch for this work; preserve the existing `007-local-server-deploy` SSH-tooling branch.

Confirmed defaults: public self-hosting first, manual updates, standard Docker Engine, file-based secrets, and brief update downtime. The investigation did not run builds or deploy the service.

## Spec Kit handoff

Use the proposal above as the feature description. Preserve the confirmed choices when separating user requirements into the specification and technical design into the later implementation plan. Follow the repository constitution and existing runtime, diagnostic, and media-delivery contracts.

Reuse this branch and explicitly select this feature directory so specification generation does not allocate a second feature:

```text
$speckit-specify Use specs/008-public-docker-deployment/proposal.md as the feature description. GIT_BRANCH_NAME=008-public-docker-deployment SPECIFY_FEATURE_DIRECTORY=specs/008-public-docker-deployment. Reuse the existing branch and retain proposal.md as the original input.
```

Saving this proposal does not generate `spec.md`, `plan.md`, a quality checklist, or tasks, and does not change `.specify/feature.json`.

# Research: Public Docker Deployment

**Date**: 2026-10-28
**Input**: [spec.md](spec.md), [proposal.md](proposal.md), existing runtime and notices.
**Result**: Design questions resolved. Findings below select the implementation approach;
they are not evidence of completed builds, publication, or server acceptance.

## 1. Reuse the existing runtime and separate public deployment

**Decision**: Keep Python 3.13, the existing pinned runtime dependencies and Dockerfile,
and the root local-build Compose workflow. Add `deploy/compose.yaml`, a nonsecret
`deploy/deploy.env.example`, and an operator guide. No new application service or runtime
dependency. Existing yt-dlp/Instaloader adapters and FFmpeg remain the media tools;
this feature needs no new extraction or processing implementation.

**Rationale**: The application already has local configuration validation, polling-only
startup, health snapshots, bounded worker shutdown, and a production-restricted local
Compose definition. The missing work is distribution and an operator interface.

**Alternatives considered**: Kubernetes, a second process manager, a managed host, and
automatic update agents add services or change the confirmed manual single-server model.

## 2. Native checks before publishing the tested artifacts

**Decision**: PR and tag workflows run the controlled suite and native image smoke jobs
on `ubuntu-24.04` and `ubuntu-24.04-arm`. Each native job builds and loads one image,
checks it, inventories it, and exports that tested image through `docker save`. Record
archive hash and image/config ID. The release job loads those same-run archives,
verifies their identity, pushes without rebuilding, records child manifest digests,
then assembles the multi-platform index. No registry publication precedes the shared
controlled, both architecture smoke, SBOM, and source-material gates.

**Rationale**: Native execution establishes tool/permission behavior on each target.
Archive promotion avoids testing one build and shipping a second build. Docker archive
transport can lose BuildKit attestations, so produce inventories separately and sign
the final published identity explicitly.

**Alternatives considered**: QEMU is useful for optional diagnostics but is not primary
architecture acceptance. A rebuild in the publishing job gives weaker tested-artifact
identity. Pushing intermediate registry images before tests violates the required gate.

Sources: [GitHub runner labels](https://docs.github.com/en/actions/reference/runners/github-hosted-runners),
[Docker image transfer between jobs](https://docs.docker.com/build/ci/github-actions/share-image-jobs/),
[index assembly](https://docs.docker.com/reference/cli/docker/buildx/imagetools/create/).

## 3. Version identity, permissions, and public access

**Decision**: Use separate `ci.yml` and `release.yml` workflows with shared checked-in
validation scripts. PR jobs are read-only and execute no privileged `pull_request_target`
code. Release triggers accept validated SemVer-style `v` tags only in the canonical
repository. Repository rules restrict version-tag creation/update/deletion to maintainers;
serialize release publication with cancellation disabled. Fail if the exact version image
already exists. Use exact version tags and immutable production digests; no floating
production alias. Record source revision and OCI source/version/revision labels.

Default permissions are `contents: read`. Only release publication jobs receive
`packages: write`, `id-token: write`, and `attestations: write` as needed; only the release
assets job receives `contents: write`. Pin actions to verified full commit SHAs and
tool downloads to exact release/checksum pairs. Record hosted-runner image versions.
Set `create-storage-record: false` for attestations to avoid unused metadata-write grants.

Configure package visibility explicitly as public and verify anonymous pulls with empty
Docker configuration. Public repository visibility does not establish public GHCR access.

**Alternatives considered**: Branch pushes, a tag prefix alone as proof of maintainer
authority, mutable version tags, broad workflow permissions, and authenticated-only pull
tests do not meet the specification.

Sources: [GHCR access and metadata](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry),
[package visibility](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility),
[tag rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets),
[workflow security](https://docs.github.com/en/actions/reference/security/secure-use).

## 4. SBOM and signed provenance with account-free verification

**Decision**: Use Syft 1.55.0 to emit SPDX JSON for each tested image/archive. Use
`actions/attest` 4.2.2, resolved to its full commit SHA during implementation, for signed
provenance over the final image index digest. Publish its detached Sigstore bundle and
the exact raw OCI index as `release-index.json`. Use regctl 0.11.7
`manifest get IMAGE@DIGEST --format raw-body` to preserve the original bytes and verify
that their SHA256 equals the published digest. Also attest `release-manifest.json`,
which binds architecture digests, image/config IDs, SBOMs, and source-asset hashes.

Operators use checksum-verified GitHub CLI 2.103.3 local-file verification with `--bundle`,
`--repo`, `--signer-workflow`, `--source-ref`, `--source-digest`, and
`--deny-self-hosted-runners`. Check the numeric repository identity from the certificate
against the canonical repository ID recorded in the reviewed verification guide. Obtain
trusted roots through the verifier's established trust path, not arbitrary release assets.
Local bundle verification bypasses the CLI's authentication requirement. Verify the raw
index file, compare its hash to the selected image digest, and pull that digest anonymously.

**Rationale**: The default `gh attestation verify oci://...` path requires registry login.
The raw-index method is a design inference from content-addressed OCI identity and
documented local-file verification: implementation must prove it against the actual
image-subject bundle using empty GitHub and Docker configurations. Do not compare a
`docker save` archive hash with the index digest; they describe different bytes.

**Alternatives considered**: Unsigned BuildKit metadata is not signed provenance.
Cosign is a viable alternative but adds a second signing/verifier stack; detached
GitHub bundles meet this feature's needs. Verification requiring a registry account
is unsuitable as the default public self-hosting path.

Sources: [Syft capabilities](https://github.com/anchore/syft),
[Syft 1.55.0](https://github.com/anchore/syft/releases/tag/v1.55.0),
[attest interface](https://raw.githubusercontent.com/actions/attest/v4.2.2/action.yml),
[raw manifest bytes](https://regclient.org/how-to/manifest-get-format/),
[regctl 0.11.7](https://github.com/regclient/regclient/releases/tag/v0.11.7),
[CLI 2.103.3 verifier implementation](https://raw.githubusercontent.com/cli/cli/v2.103.3/pkg/cmd/attestation/verify/verify.go),
[GitHub offline verification and repository identity](https://docs.github.com/en/actions/how-tos/secure-your-work/use-artifact-attestations/verify-attestations-offline).

## 5. Matching source and notices are release assets

**Decision**: Add a CI-only Python standard-library collector and reviewed
`release/source-policy.json`. Inventory the entire final image for each architecture:
Debian packages, application and system Python distributions, and unmanaged CPython,
uv/uvx, and Deno binaries. Map exact components to licenses, notice paths, source
identities, acquisition hashes, and build instructions. Archive exact Debian `.dsc`
and referenced source/patch files, including `Built-Using` edges; archive installed
application dependency sdists from lockfile URLs/hashes. Explicit policy entries cover
unlocked system packages and unmanaged tools, embedded components, and base-image recipes.
Deduplicate common source across architectures and split large bundles into logical parts.

Preserve installed license texts and collect a notice archive. Require sources to be
present, hash verified, safely unpackable, and mapped to the actual tested components
before image publication. Publish a completed sources-only public release at tag
`sources-VERSION` (for example `sources-v0.1.0-preview.1`) before publishing images.
Keep the final `VERSION` release draft until its image identities, manifests and bundles
are attached; then publish it. This supports GitHub immutable releases, which lock
assets on publication. Both tags identify the same source commit; sources-only tags
do not trigger image publication. Keep
source assets available for as long as their images are distributed. Missing coverage
fails publication rather than becoming a warning.

**Rationale**: The existing notices table and the application's repository archive do
not cover the whole binary image. The base interpreter, system packages, shared libraries,
wheel-vendored code, and static tool components require inventory. Source-version fields
must come from package metadata, not string guesses from binary package versions.
This operational policy follows the repository's existing redistribution requirement.

**Alternatives considered**: Upstream links alone can disappear; an FFmpeg-only archive
misses dependencies; all of `uv.lock` includes packages not shipped while missing the
base image. Exact source coverage does not imply bit-for-bit binary reproducibility.

Sources: [repository policy](../../THIRD_PARTY_NOTICES.md),
[Debian source structure](https://www.debian.org/doc/debian-policy/ch-source.html),
[Debian Built-Using](https://www.debian.org/doc/debian-policy/ch-relationships.html#additional-source-packages-used-to-build-the-binary-built-using),
[Debian snapshots](https://snapshot.debian.org/),
[Python sdists](https://packaging.python.org/en/latest/specifications/source-distribution-format/),
[wheel notices](https://packaging.python.org/en/latest/specifications/binary-distribution-format/),
[Python image recipe](https://github.com/docker-library/python/blob/master/3.13/bookworm/Dockerfile),
[uv licensing](https://github.com/astral-sh/uv/blob/main/docs/reference/policies/license.md),
[Deno composition](https://github.com/denoland/deno).

Staging source: [GitHub release immutability](https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository).

## 6. File-secret loading preserves the direct-token interface

**Decision**: Extend `Settings.from_env` with a small private loader. Detect conflicting
inputs by key presence before reading either input; empty values still conflict.
Retain the current direct-token validation. New file input requires an absolute path
to a readable regular file, bounded to 4,096 bytes, decoded as ASCII. Accept one optional
terminal LF or CRLF; otherwise require one `digits:ASCII-letters-digits-underscore-hyphen`
token, with nonempty sides and no fixed token length. Reject blank content, BOM,
whitespace, extra lines, NUL, directories, special files, and oversized files.

Open without blocking on special files, check the opened descriptor is regular, read
at most 4,097 bytes, and close deterministically. Convert read/parse failures to fixed
`ConfigError` categories with suppressed exception chaining; never interpolate the path
or contents. Store only the loaded token in the existing `repr=False` settings field.
Do not retain a new printable secret-source field or forward either input to workers.

**Rationale**: Configuration is parsed before logging is configured. Safe errors must
be safe at their source, including tracebacks, rather than relying on later redaction.
The healthcheck also loads settings and must remain local. The new file grammar provides
useful malformed-file validation without retroactively tightening the direct-token input.
Local validation does not authenticate the token against Telegram.

**Alternatives considered**: Silent environment precedence, unbounded text reads,
catch-all errors containing exception/path text, stricter legacy-token validation,
and polling during preflight change compatibility or leak secrets.

Evidence: `src/openmedia/config.py`, `src/openmedia/__main__.py`,
`src/openmedia/diagnostics.py`, `src/openmedia/workers.py`, and existing configuration/
runtime tests. No new parser dependency is required.

## 7. Host setup, secrets, and production restrictions

**Decision**: Document rootful Docker Engine and Compose from Docker's official APT
repository on Ubuntu 24.04/26.04 LTS, amd64/arm64. Require the installed Compose CLI to
support `up --wait --wait-timeout` and the documented run/pull flags; record versions.
Do not invent an unverified minimum version. Keep deployment under `/opt/openmedia`,
use explicit project/file/env paths, and keep token values out of Compose interpolation.
Store the host secret as `root:10001`, mode `0640`, under a protected root-owned directory.
The single-file mount is read-only; file-secret `uid/gid/mode` settings are ignored by
Compose and are not a substitute for host ownership.

Retain the root Compose protections, init, 2 CPU/2 GiB limits, 512 MiB `/tmp` tmpfs,
30-second stop grace, and 10 MiB × 3 bounded console logs. tmpfs consumes the memory
budget. No application ports or Docker socket enter the container. Optional diagnostics
retain their existing explicitly provisioned storage contract.

**Alternatives considered**: Rootless Docker, user-namespace remapping, and non-Linux
production hosts require different ownership validation and are outside initial guidance.
File-backed secrets are not encrypted host storage.

Sources: [Ubuntu installation](https://docs.docker.com/engine/install/ubuntu/),
[Compose secrets](https://docs.docker.com/compose/how-tos/use-secrets/),
[file-secret ownership caveat](https://docs.docker.com/reference/compose-file/services/#secrets),
[tmpfs](https://docs.docker.com/engine/storage/tmpfs/).

## 8. Deliberate update, bounded health wait, and recovery

**Decision**: Use documented Compose commands rather than introduce an updater service.
Pass candidate `OPENMEDIA_IMAGE` per command, leaving `deploy.env` unchanged during
preflight. Pull and `run --rm --no-deps -T --pull never ... --check-config` use the
candidate with isolated tmpfs and no poller. Record the actual old container's immutable
image reference and ID, stop it, confirm it stopped, then force-recreate the candidate
with `up --wait --wait-timeout 180 --pull never --no-build`. Explicitly stop failed,
timed-out, or interrupted candidates; the health wait does not guarantee cleanup.
Persist the selected digest only after health succeeds. Rollback is an explicit repeat
of preflight and startup for the previous digest, using current settings and credentials.

Migration first stops the old Compose project, even if it has a different project name.
Keep its configuration and local image ID for recovery. Credential rotation stops the
bot, replaces the protected file, validates, and force-recreates it: a simple restart
can retain the old backing file after atomic host replacement. This rotation choice is
an inference from bind-mount behavior and is validated during server acceptance.

Keep `unless-stopped`; unhealthy status alone does not trigger restarts. Reboot/process
recovery and intentional stops are separate acceptance cases. Active requests are canceled
under the existing 20-second application shutdown budget; users resubmit after recovery.

**Alternatives considered**: Automatic rollback, parallel pollers, health-triggered
restart agents, and a host process manager would change accepted operational behavior.

Sources: [Compose interpolation precedence](https://docs.docker.com/compose/how-tos/environment-variables/variable-interpolation/),
[one-off run](https://docs.docker.com/reference/cli/docker/compose/run/),
[health wait](https://docs.docker.com/reference/cli/docker/compose/up/),
[stop](https://docs.docker.com/reference/cli/docker/compose/stop/),
[bind mounts](https://docs.docker.com/engine/storage/bind-mounts/),
[restart policy](https://docs.docker.com/engine/containers/start-containers-automatically/).

## Dependency accountability

Runtime versions/licenses remain those in `pyproject.toml`, `uv.lock`, Dockerfile, and
`THIRD_PARTY_NOTICES.md`. New build-only selections are Syft 1.55.0 (Apache-2.0),
regctl 0.11.7 (Apache-2.0), GitHub CLI 2.103.3 (MIT), and actions/attest 4.2.2 (MIT).
Resolve release checksums and full action SHAs from their official releases at implementation,
review them, and commit the actual pins; this plan intentionally invents no hashes.
Use Python standard-library manifest tooling and pinned Debian APT/dpkg tooling in CI.
These are not application dependencies and are excluded from the runtime image.

## Cross-artifact review resolutions

Image publication starts at the first registry image push and requires the full pre-push
gate set. Signing/local verification and anonymous image access occur afterward and gate
release finalization; public evidence retrieval/verification gates acceptance. Later failure
leaves incomplete distributed artifacts with source materials retained. Duplicate image
version rejection belongs only to publisher pre-push authorization, not shared parsing,
final assembly or operator verification of a matching published release.

US1 is an implementation checkpoint. The first public preview follows all story code and
the final integrated release gates under the existing sequential phase workflow. Feature
completion requires its own deployment acceptance plus an executed/assessed inherited
matrix. Evidenced pre-existing source limitations can remain open stable-readiness blockers
on a completed preview feature; deployment regressions and unclassified failures cannot.

## Implementation pin ledger — Phase 1, 2026-10-28

All requested versions exist in the official upstream repositories. Resolved release
metadata and peeled tag refs using `gh api repos/OWNER/REPO/releases/tags/TAG` and
`gh api repos/OWNER/REPO/git/ref/tags/TAG` (dereference annotated tags through
`git/tags/SHA`). Downloaded and independently SHA256-hashed all six Linux assets below;
each matched the official GitHub release asset digest. Syft and gh also matched their
published checksum files. These are build/operator tools only, never runtime packages.
Commit pins below identify source revisions; SHA256 values identify downloaded bytes.
Do not substitute floating action tags or upstream installer scripts in the workflows.

| Tool / provenance | Source commit | License at source commit |
|---|---|---|
| [Syft 1.55.0](https://github.com/anchore/syft/releases/tag/v1.55.0) | `f15c3343e29dfb20cf6d82c820e7090b49808c96` | [Apache-2.0](https://github.com/anchore/syft/blob/f15c3343e29dfb20cf6d82c820e7090b49808c96/LICENSE) |
| [regctl 0.11.7](https://github.com/regclient/regclient/releases/tag/v0.11.7) | `36abda84830dae07db00bf9e5cec95d97b78222a` | [Apache-2.0](https://github.com/regclient/regclient/blob/36abda84830dae07db00bf9e5cec95d97b78222a/LICENSE) |
| [GitHub CLI 2.103.3](https://github.com/cli/cli/releases/tag/v2.103.3) | `63837fb778d6a39f02be0ce76ff89f2bc8d74bdc` | [MIT](https://github.com/cli/cli/blob/63837fb778d6a39f02be0ce76ff89f2bc8d74bdc/LICENSE) |

Asset URLs use the release's `/releases/download/TAG/FILENAME` path on the same official
repository. Check the committed checksum before extraction/execution, including on arm64.

| Exact filename | SHA256 |
|---|---|
| `syft_1.55.0_linux_amd64.tar.gz` | `bb65249542db5fedeeb4d3f9b018b75e7264dbfbbb10486f044581a92f90490d` |
| `syft_1.55.0_linux_arm64.tar.gz` | `929bd163db2d7cd2255d3bcb8967208079813d7b46b0c952f7b794d8e2c7d304` |
| `regctl-linux-amd64` | `3737fbbdd791e04e7a831640b681f3397a376498e80e2ad9b1b2d27296f239bc` |
| `regctl-linux-arm64` | `9f349bab5c407ac04f3dabf99c7c7a6b0f9e9723c23f2775380e804d02c6dbb9` |
| `gh_2.103.3_linux_amd64.tar.gz` | `4c806978ffce1cec70853302a56d70ac6da4f19bae7adca4e1a8ab00633dd91d` |
| `gh_2.103.3_linux_arm64.tar.gz` | `ee32df2323c8847f5fac6cb6b4b69ca75828e9329a8f22f677021f7b3306ce63` |

The downloaded [Syft checksums](https://github.com/anchore/syft/releases/download/v1.55.0/syft_1.55.0_checksums.txt)
have SHA256 `aba5ac8ee870bb93fd3b2058471ffe7e57492ba673b5e0bcbfca92006c2f4dc7`;
the [gh checksums](https://github.com/cli/cli/releases/download/v2.103.3/gh_2.103.3_checksums.txt)
have SHA256 `f756e7859d90dbb5e85aae5194206c37da220bec9bac23d3d659078a8e766fdc`.
Upstream publishes [Syft's Sigstore checksum bundle](https://github.com/anchore/syft/releases/download/v1.55.0/syft_1.55.0_checksums.txt.sigstore.json)
and regctl per-binary `.sigstore.json`, `.sig` and `.pem` assets in its official release.
Phase 1 verifies download hashes and source origin; it does not claim these upstream
signature bundles have been cryptographically verified or prove our future release bundles.

### Full action commit pins

Resolved from each official release tag; license files were checked through GitHub's
license API. Use these exact commits with the listed version as a comment. The same
repository's `blob/COMMIT/LICENSE` provides version-specific license provenance.
Only include actions actually needed by the final workflow; any additional action needs
an equivalent reviewed ledger entry before use. Default permissions remain read-only.

| Official action / release | Full commit pin | License |
|---|---|---|
| [actions/attest v4.2.2](https://github.com/actions/attest/releases/tag/v4.2.2) | `1e69f48acb82d1966a394da916b4c1698aa569d6` | [MIT](https://github.com/actions/attest/blob/1e69f48acb82d1966a394da916b4c1698aa569d6/LICENSE) |
| [actions/checkout v7.0.1](https://github.com/actions/checkout/releases/tag/v7.0.1) | `3d3c42e5aac5ba805825da76410c181273ba90b1` | [MIT](https://github.com/actions/checkout/blob/3d3c42e5aac5ba805825da76410c181273ba90b1/LICENSE) |
| [actions/setup-python v7.1.0](https://github.com/actions/setup-python/releases/tag/v7.1.0) | `6d4fd22b20465ccc0f7354476588e8df7c9ca0e0` | [MIT](https://github.com/actions/setup-python/blob/6d4fd22b20465ccc0f7354476588e8df7c9ca0e0/LICENSE) |
| [actions/upload-artifact v7.0.2](https://github.com/actions/upload-artifact/releases/tag/v7.0.2) | `cf430e030ddbb5b0abf93d22962f4752f3646cd9` | [MIT](https://github.com/actions/upload-artifact/blob/cf430e030ddbb5b0abf93d22962f4752f3646cd9/LICENSE) |
| [actions/download-artifact v8.0.2](https://github.com/actions/download-artifact/releases/tag/v8.0.2) | `9000827ccba6bdab643e8b6fd33ac0654aef8333` | [MIT](https://github.com/actions/download-artifact/blob/9000827ccba6bdab643e8b6fd33ac0654aef8333/LICENSE) |
| [docker/setup-buildx-action v4.4.1](https://github.com/docker/setup-buildx-action/releases/tag/v4.4.1) | `f87e5991a6d7451dcb8d9637bfbc97413f497069` | [Apache-2.0](https://github.com/docker/setup-buildx-action/blob/f87e5991a6d7451dcb8d9637bfbc97413f497069/LICENSE) |
| [docker/login-action v4.7.0](https://github.com/docker/login-action/releases/tag/v4.7.0) | `81c6f93d4bc991e510b342a00b419b3bb4efc5c6` | [Apache-2.0](https://github.com/docker/login-action/blob/81c6f93d4bc991e510b342a00b419b3bb4efc5c6/LICENSE) |

Action source pins do not pin software they install. Explicitly supply the existing
application Python/uv versions and a pinned Buildx version if using setup actions;
record hosted runner/Engine/Compose versions per execution. Do not rely on a runner's
preinstalled gh, Syft or regctl as a release-verification dependency.

### Source-collector environment

Use the existing official multi-platform
`python:3.13.15-slim-bookworm@sha256:ed86c82274b3c69b52fb5820f358f0bd7df0b603332063cb5c6e32bd220c3e6e`
as the build-only collector base. Python standard-library tooling handles manifests,
HTTP and safe archive inspection; Debian APT authenticates source indexes using its
archive keyring. No arbitrary unsigned source index or `trusted=yes` override is allowed.
This reuses the reviewed [official Python image build provenance](https://github.com/docker-library/python)
and [Debian source archive](https://sources.debian.org/); it does not alter the runtime.

A native arm64 ephemeral container of that digest reported the following installed or
APT-authenticated candidate versions on 2026-10-28. Pin these exact direct collector
packages when constructing the separate collector; retain its complete dpkg inventory
and installed copyright/common-license files as build evidence. Additional dependencies
must be acquired through signed Debian metadata and recorded, never silently substituted.
Collector assembly and actual-image source coverage are later Phase 3 gates.

| Collector input | Version | Origin / license provenance |
|---|---|---|
| Python | 3.13.15 | Pinned base; PSF and bundled component notices in official CPython source |
| apt | 2.6.1 | Installed base, Debian `apt` source; GPL-2.0-or-later and component copyright |
| dpkg / dpkg-dev (`dpkg-source`) | 1.21.23 | dpkg installed; dpkg-dev exact candidate from bookworm/main; GPL-2.0-or-later and component copyright |
| gpgv | 2.2.40-1.1+deb12u2 | Installed base, Debian `gnupg2` source; GPL-3.0-or-later and component copyright |
| debian-archive-keyring | 2023.3+deb12u2 | Installed base; Debian authenticated archive roots and package copyright |
| tar | 1.34+dfsg-1.2+deb12u1 | Installed base; Debian `tar` source; GPL-3.0-or-later and component copyright |
| xz-utils | 5.4.1-1+deb12u2 | Exact candidate from bookworm-security/main; public-domain/LGPL/GPL component copyright |
| bzip2 | 1.0.8-5+b1 | Exact binary candidate from bookworm/main; source 1.0.8-5; bzip2 license |
| patch | 2.7.6-7 | Exact candidate from bookworm/main; GPL-3.0-or-later and component copyright |

Retain `.dsc` checksums and every referenced archive. Source-version identity can differ
from a binary's `+b1` rebuild suffix; never generate source URLs by assuming equality.
For historical package versions use authenticated Debian snapshots and pin the selected
snapshot/input hashes in the collection record. Package-specific component notices,
not this summary table, determine complete redistribution coverage.

Runtime Python/uv/Deno image digests, FFmpeg, application pins and `uv.lock` remain
unchanged. Upstream tool signatures, raw-index local-bundle compatibility, both native
collector environments and complete source closure still require their later executed gates.

If the optional setup-buildx action is used, set `version: v0.38.1` rather than its
floating default. [Official Buildx v0.38.1 release](https://github.com/docker/buildx/releases/tag/v0.38.1)
provides `buildx-v0.38.1.linux-amd64` with SHA256
`e25d5cd675092bb5d1d03632fdc46cdf3fede7b514dc5f023a105e00d3ce5ad4` and
`buildx-v0.38.1.linux-arm64` with SHA256
`3b83b3731916ba433feccaaa689fe5bcdc81c641d92c8e6c2ea865dfa141c97a`.
These hashes were read from the official release API; unlike the six required tool
assets above, these optional binaries have not been downloaded/executed in Phase 1.
Buildx uses Apache-2.0; retain its versioned source/license provenance if selected.

Authenticated APT package SHA256 pins resolved for the collector's **arm64** additions:

| Package / exact binary version | SHA256 from signed APT index |
|---|---|
| dpkg-dev 1.21.23 (Architecture: all) | `43547075395dbe9290e6a5f34e9ba93aa5dcf7dfc5698c3d30cc3c85e5f7e3de` |
| xz-utils 5.4.1-1+deb12u2 | `79b5b77de62315e3fa415aa80bd6fa68ea584e4f122d9dc4542172d85b067d68` |
| bzip2 1.0.8-5+b1 | `7624d678ce308bc301f2932fb5c60392de09c569b9be4f2ae2dfe9a59cd73868` |
| patch 2.7.6-7 | `11e5e56f3cb4b306c9589bb37f9c701bf23bb37c410bac12e6a50d6461e71bd6` |

Resolve architecture-specific binary hashes from authenticated metadata for amd64 during
collector assembly; arm64 binary hashes must not be reused for amd64. The source
identities and required exact versions above are shared. These are input pins, not a
claim that collector assembly/source acquisition has already passed.

## Foundation compatibility observations — Phase 2 (2026-10-28)

No base, Python package, tool, FFmpeg version or retained license file changed. The
four inherited rotation fixtures used `-display_rotation`, which pinned FFmpeg 5.1.9
does not provide. Fixture generation now selects that option when advertised by
`ffmpeg -h full`; otherwise it stream-copies with `-metadata:s:v:0 rotate=ANGLE`, the
5.1 display-matrix interface. All 0/90/-90/180 dimension assertions remain. Both the
newer macOS FFmpeg and retained Linux FFmpeg pass the four cases. This changes only
synthetic test creation, without changing application media processing or relaxing
assertions. The full Linux arm64 suite passes (992 tests).

Docker Desktop's host-file sharing exposed a chmod-000 bind fixture as missing rather
than returning permission denial. Smoke now initializes a root-owned mode-000 fake
secret inside its own disposable Docker volume, mounts it read-only, and requires
`PermissionError` from the actual UID/GID 10001 probe. Its CLI invocation separately
requires exit 2 and the fixed unreadable-file category. The helper has no network or
capabilities; all test resources are removed by the shell exit/interruption trap. This
volume is test-fixture storage, never production request/media storage.

With Docker Engine 29.9.2's containerd image store, a default BuildKit build produces
an OCI index containing its platform manifest and a build attestation. In this case
`docker image inspect .Id` is the local index identity, **not** the OCI config digest.
The build export reports each distinctly (see Phase 2 validation). Smoke reports
“Docker image ID” without mislabeling it a config hash. Release promotion must preserve
and independently join archive/image/platform/config identities; it cannot infer a
config identity from `.Id` on this store. Default development labels do not claim a
published version. Release workflows must supply exact version/full revision build args.

## Phase 3 implementation decisions and executed compatibility evidence

The canonical repository was independently queried with `gh api repos/hman-pro/openmedia`
on 2026-10-29: `id=1380348601`, `full_name=hman-pro/openmedia`, public canonical URL.
Both the reviewed verification policy and standalone verifier pin this identity
independently of downloaded release assets.

GitHub CLI 2.103.3's actual local-bundle JSON was exercised without authentication using
the pinned CLI repository's original `github_provenance_demo-0.0.12-py3-none-any.whl`
and matching real signed `.jsonl` fixture, from source commit
`63837fb778d6a39f02be0ce76ff89f2bc8d74bdc`. `gh attestation verify FILE --bundle BUNDLE
--repo actions/attest-demo --format json`, with an empty GH_CONFIG_DIR and no GH_TOKEN/
GITHUB_TOKEN, passed using established roots. Its authenticated fields are
`verificationResult.signature.certificate.sourceRepositoryIdentifier`,
`sourceRepositoryURI`, `sourceRepositoryDigest`, `sourceRepositoryRef`,
`subjectAlternativeName`, `issuer`, and `runnerEnvironment`; subject digests are in
`verificationResult.statement.subject`. These exact field names drive policy checks.
This is CLI-output/established-root compatibility evidence, not OpenMedia's own signed
raw-index proof. That proof and negative tests remain T062. No supplied root is trusted.

The final image's whole-filesystem inventory uses root in a disposable read-only,
network-none helper with all capabilities dropped except DAC_READ_SEARCH. This narrowly
permits reading root-only and UID-10001 mode-0700 directories without silently skipping
them. Production identity/restrictions remain unchanged and are separately smoke-tested.
DPKG file ownership is joined through merged-/usr aliases, registered maintainer scripts
are included, Python RECORD ownership is joined for both environments, and every remaining
ELF or executable script must map to an explicit reviewed, architecture-specific checksum.
Traversal errors are fatal. This found the otherwise untracked base `policy-rc.d` script;
its exact installed SHA256 is
`21a8dca0d6a52cbac52cb7a86178d973616ffb42ea08747e6ff311659ab095e1`.
The retained debuerreotype source's policy-rc.d heredoc was extracted and matched those
exact bytes; its recorded source revision denotes matching source, not an invented claim
about the original base-image builder revision.

Whole-image inspection also found unused uv build caches under /root. The maintainer
approved `uv cache clean` in the same Dockerfile RUN as uv sync, so unused cached wheels
never enter a layer. No Python/package/tool/base/FFmpeg pin or runtime behavior changed.
Exact original package notices remain, and the image now additionally includes deterministic
`RUNTIME_NOTICES.txt.gz`, with original unmanaged/embedded license texts, source attribution
lines and material provenance. The Docker source archive/build inputs include every COPY
input. The notice file is the sole release-directory runtime build-context exception.

The checked source policy records 1,553 distinct Cargo registry archives verified against
the exact uv/Deno Cargo.lock checksums. The uv source revision is
`d35f1f2703b4a9cefbfa7fc21164e3ca4fcab933`; Deno is
`e518fbd66dda5debcbdefc0beb0b3756b37b64fa`; CPython is
`4061bc4c35f7c26f25264666d4ba083b93d2f6f9`. The exact Python image's OCI annotation
identifies official recipe commit `688a0b86bb44289df16a363e9f41d90514c1a5f9`.
V8 crate 150.4.0 includes V8, Chromium build and ICU source rather than empty gitlinks;
its ICU header identifies 77.1. Deno's ICU-data wrapper is separately identified and
linked to those source/license materials. Native CPython reports embedded Expat 2.8.2
and libmpdec 2.5.1, distinct from Debian shared-library versions; HACL source and pip's
18 vendored components have explicit corresponding-source/notice edges as well.
Rust 1.98.1/1.95.0 source archives match their official published checksums, and TypeScript
6.0.3 source is separately retained. This is matching-source coverage, not a binary
reproducibility promise. Full acquisition of every declared material is still a native
CI gate, not established by policy construction or this paragraph.

Some exact crate archives omit a separate license file; unavailable recorded git commits
were not treated as retrieved. The reviewed narrow fallback preserves every original
source/header and Cargo authors/license declaration, supplies checksum-pinned full
standard text for an explicitly permitted license branch, and records the absence.
SPDX text revision `617f1a78824394ada7525017d98c6fb215aad09b` is pinned in policy.
Prefer Apache-2.0 in an allowed OR expression, retain LLVM exception text for WITH,
and retain complete source for the selected MPL branch. Unsupported expressions or
missing required original notices block coverage. Original source copyright notices
are not replaced with author-derived statements or SPDX template placeholders. The
MIT-only original-notice audit is retained in `release/notice-review.json`, including
explicit cases where no copyright line was found. See
[SPDX guidance](https://spdx.dev/learn/handling-license-info/) and
[Apache section 4](https://www.apache.org/licenses/LICENSE-2.0.html).

Collector direct package pins and runtime pins are unchanged. The actual arm64 collector
image built successfully, and APT-authenticated bzip2 source `1.0.8-5` (binary may be
`1.0.8-5+b1`) was acquired with `.dsc`, original and Debian patch archives and signed-index
receipt. Frozen signed snapshots at base-era `20260831T000000Z` and review-era
`20261028T000000Z` supplement current signed metadata; only historical expiry checks are
disabled, never signature verification. Exact source metadata, acquisition URI, hashes
and collector dpkg inventory are retained. Full both-platform source closure is T034.

Index media compatibility is explicit: Buildx 0.38.1's reviewed
[`util/imagetools/create.go`](https://github.com/docker/buildx/blob/v0.38.1/util/imagetools/create.go)
chooses a Docker manifest list when all children have Docker media types. Newer OCI
stores normally supply OCI children, and promotion uses `docker buildx imagetools create`
there. For a classic store yielding two Docker children, the already pinned regctl
0.11.7 `index create --media-type application/vnd.oci.image.index.v1+json --ref ...`
creates the required OCI index instead. This decision precedes the first exact-version
write; it never rewrites a published version or rebuilds either checked child. Child
config/digest checks and the exact two-platform raw-index verification are unchanged.
The regctl flag/default was checked against its pinned official source
`36abda84830dae07db00bf9e5cec95d97b78222a/cmd/regctl/index.go`.

# Data Model: Public Docker Deployment

These entities describe release artifacts and operator records. They do not add a
database, durable request queue, or persistent media state to the application.

## Published release

| Field | Meaning / validation |
|---|---|
| version | Exact maintainer-created `vMAJOR.MINOR.PATCH[-prerelease]` tag; validate syntax and its expected release identity |
| package_version | Installed OpenMedia package version; recorded independently of preview tag suffix |
| source_revision | Full Git commit at the release tag |
| source_repository / repository_id | Canonical project URL and numeric GitHub repository identity |
| workflow / workflow_run | Trusted release workflow path, run ID and attempt |
| source_release_tag / source_release_url | Completed sources-only release `sources-VERSION` at the same commit; material assets can live there |
| index_digest | SHA256 of exact OCI index bytes; selected production identity |
| platforms | Exactly `linux/amd64` and `linux/arm64`; each linked to its child image |
| artifacts | Named assets, SHA256, size, media type, and public location |
| preview / gates | Preview status and references to feature-acceptance and inherited stable-readiness gates |

Version metadata and OCI labels must identify the same tag/revision. Do not conflate a
Docker archive hash, image/config ID, platform manifest digest, and multi-platform index
digest. Each identifies a different object. A version is immutable once published.
The publisher's pre-push authorization rejects an existing exact image version.
That nonexistence check does not belong to shared record parsing, final manifest assembly,
or operator verification. Record parsing and final assembly accept an already published
version whose expected tag, source revision and digest match; operator verification also
authenticates its signed evidence. Assembly does not require its own not-yet-created
signature. These paths reject identity mismatches and never overwrite an existing version.
Reading/verifying a release is not republishing it.

## Platform build

| Field | Meaning / validation |
|---|---|
| platform | One required platform, built and tested natively |
| runner | Hosted runner label, architecture, runner-image revision |
| image_config_id | Docker image ID before archive export and after import; must match |
| archive_hash | SHA256 of same-run Docker archive transferred between jobs |
| base_digests / tool_versions | Effective build inputs from pinned Dockerfile and build tooling |
| smoke_result | Successful restricted/no-network smoke result for this exact image ID |
| platform_digest | Registry child manifest digest after promotion; joins index descriptor |
| sbom | Architecture-specific SPDX JSON asset and hash |
| component_inventory | Actual Debian/Python/unmanaged inventory used for source coverage |

No publishing job rebuilds the application image. Both platform records and the controlled
suite must pass before any image push. Registry manifest digest is recorded after push;
archive promotion is validated through archive hash and preserved image/config identity.

## Source component and material

| Field | Meaning / validation |
|---|---|
| component_id / kind | Stable inventory identity; Debian, application Python, system Python, or unmanaged/embedded tool |
| name / version / architectures | Exact installed identity and platforms containing it |
| license / notice_paths | Reviewed license classification and installed/archived notice locations |
| source_identity | Debian source package/version, lockfile sdist, or explicit policy revision |
| source_files | Archive paths, acquisition URLs, checksums, size, and source-format relationships |
| build_materials | Required packaging, patches, base/tool build recipes and instructions |
| incorporated_sources | Debian `Built-Using` and reviewed vendored/static source relationships |
| coverage | `complete` or `missing`; missing blocks publication |

Deduplicate identical source materials across platform builds. Every installed component
must map to a reviewed entry even if no source obligation applies. Preserve source/license
materials required by repository policy; do not infer a whole binary's license solely
from a top-level package label. Sources describe the distributed build, not necessarily
a binary-reproducibility promise. No host credentials, live manifests, or media enter assets.

## Deployment configuration and runtime credential

| Field | Meaning / validation |
|---|---|
| project | Fixed production Compose project `openmedia` |
| image | `ghcr.io/hman-pro/openmedia@sha256:` followed by 64 hexadecimal digits |
| env_file / compose_file | Explicit `/opt/openmedia/deploy.env` and `/opt/openmedia/compose.yaml` |
| token_file | Host secret path; nonsecret reference, mounted read-only at `/run/secrets/telegram_bot_token` |
| runtime_settings | Explicit permitted nonsecret settings under existing validation rules |
| limits / logging | Production restrictions and bounded console logs |
| diagnostic_storage | Absent by default; explicitly provisioned per feature 002 when enabled |

The host `deploy.env` contains no token value and is not imported wholesale as container
environment. A temporary candidate image is supplied per Compose invocation; shell
interpolation precedence must not silently select a different image. Persist the selected
digest only after healthy activation, with a protected atomic update of the image setting
that preserves current nonsecret settings.

The runtime credential has one source (`environment` or `file`) and one loaded token.
Presence of both source keys is invalid even if empty. Store the loaded value only in the
existing private settings field. The file source reference need not survive parsing or
appear in settings representations. See [configuration contract](contracts/configuration.md).

## Update record

Operator-owned, nonsecret notes record previous and candidate image references, actual
container/image IDs, UTC time, settings identity, preflight result, startup deadline,
health result, stop confirmation, and rollback outcome. Do not hash/log credential contents
as an identity mechanism. Records are not an application-side state store.

```text
running(previous)
  -> candidate_downloaded -> candidate_validated -> previous_recorded
  -> previous_stopped -> candidate_starting -> candidate_healthy -> selection_persisted

download/validation failure -> running(previous), selected configuration unchanged
startup failure/timeout/interruption -> candidate_stopped -> rollback_available
rollback_available -> previous_validated -> previous_starting -> previous_healthy
rollback failure -> stopped, explicit recovery error
```

At most one polling container per token across projects. Preflight is a nonpolling one-off
container with isolated scratch storage. Failed/interrupted startup is not complete until
the candidate is confirmed stopped. Persistence failure after health is reported explicitly;
do not claim the running and selected image references agree until corrected.

Migration adds an old-project identifier and local image/config ID for recovery. A local
image may have no registry digest; preserve its content ID and configuration rather than
invent a digest-qualified GHCR reference.

## Validation record

| Field | Meaning / validation |
|---|---|
| gate_id / requirement_ids | Release/check identity and related acceptance requirements |
| class | Controlled, native container, public distribution, or deployment-network/manual |
| release / platform | Exact source, image identity, and architecture |
| environment | Host OS, Engine/Compose/tool versions, network context without secrets |
| result | `pending`, `pass`, `fail`, or `blocked` with a concrete reason |
| gate_scope | Feature 008 acceptance or inherited stable-readiness obligation |
| failure_class | Deployment regression, evidenced pre-existing source limitation, unclassified, or none |
| evidence / limitations | Sanitized commands/results, timing, observed constraints, next action |

Source URLs and Telegram identifiers stay in private manifests or permitted diagnostic
storage. Public reports use sanitized case IDs. Passing a substitute does not transition
a live/manual gate to pass. Releases remain preview while any required inherited container
or live acceptance gate is not passed; source availability failures remain visible.
Known-source classifications require an earlier validation record or a comparison that
establishes the limitation independently of the deployment change. Unsupported assumptions
remain unclassified. All feature-008 controlled/native/public/server checks and representative
real delivery must pass; the inherited matrix must be executed and assessed. Only evidenced
pre-existing source limitations may remain open at feature completion. They still block
stable readiness and the corresponding capability claims; a regression or unclassified
failure blocks feature completion itself.

Release progression is `build_checks_passed -> sources_available -> pre_push_checked -> images_published
-> evidence_verified -> release_finalized -> accepted_preview`. Before `images_published`,
any failed pre-push check prevents all image writes. Signing/local verification and
anonymous image checks follow image publication and precede release finalization;
public evidence download/verification follows finalization and precedes acceptance.
Failure after the first push leaves an incomplete distribution, with source materials
retained and no accepted-release claim. Stable readiness additionally requires all
inherited readiness gates to pass. Published version/digest identities are never rewritten
to repair a failed release.

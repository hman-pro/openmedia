# Public Release Contract

## Authority and workflow boundary

Image name is `ghcr.io/hman-pro/openmedia`; required platforms are `linux/amd64` and
`linux/arm64`. `ci.yml` runs controlled/native container validation on PRs, without
publishing privileges or real bot credentials. `release.yml` reruns the pre-push checks
and performs finalization/acceptance checks for maintainer-created version tags in the
canonical repository. Do not execute untrusted
PR code through `pull_request_target` with privileged credentials.

Validate full SemVer-style `vMAJOR.MINOR.PATCH[-prerelease]` tag syntax, source revision,
canonical repository identity, and maintainer tag rules. Restrict tag creation, mutation,
and deletion using repository rulesets; a prefix test is insufficient authority.
Serialize publication with cancellation disabled. Before the first image push, reject
an existing exact image version; never overwrite it or replace its evidence. Shared
record parsing and final manifest assembly accept an existing version whose expected
tag/source/digest match; operator verification additionally authenticates its signatures.
Assembly does not require the manifest's own future signature. None of these read/assembly
paths runs the publisher's nonexistence check. A maintainer creates the source-only
`sources-VERSION`
tag at the same commit before creating the version tag; validate both under the configured
tag rules. Source-only tags do not trigger image publication. While external gates remain open, require preview
version/status and GitHub prerelease labeling; no final deployable claim is made.

Default token permission is `contents: read`. Release jobs receive only the publishing,
OIDC, attestation, or release-assets permissions their step needs. Disable unused
attestation storage-record creation. All actions use reviewed full SHA pins with version
comments; tools/images use exact release/checksum or digest pins. Actual pins are resolved
and recorded at implementation, not guessed in planning. Record hosted runner versions.

## Stage boundaries and required checks

| Boundary | Required checks / failure outcome |
|---|---|
| Before image publication (the first registry image push) | Authority/tag pair and unused image version; immutable pins/least privilege; controlled suite; both native builds/smokes and inventories; complete source/notices with public retrieval; both archive hashes/imported config identities. Any failure means zero image pushes for the attempt. |
| Before release finalization (publishing the evidence-filled GitHub release draft) | Published child/index identity joins, signed provenance/manifest, real raw-index local-bundle proof and negative cases, anonymous both-platform image retrieval. Failure leaves an incomplete distribution and keeps the final release draft. |
| Before release acceptance | Redownload all public final evidence/materials and verify signatures, identity and hashes with no account. Failure leaves a finalized but incomplete release; it is not advertised as accepted. |

Checks requiring registry objects or public final release assets are not pre-push checks.
All pushed images retain required public source materials even if a later stage fails.
An accepted preview is a successfully distributed release, not a stable-readiness claim.

## Build, check, and promotion sequence

1. Run the locked controlled pytest suite with its normal network prohibition.
2. Native amd64 and arm64 jobs build/load single-platform images with version/source
   OCI labels, using the pinned Dockerfile. Record Docker image/config IDs.
3. Run `scripts/smoke-container.sh IMAGE` against each exact image with fake file
   secrets, no networking, and production restrictions. Probe tools, EJS, local
   stream-copy merge, temp storage, UID/capabilities, read-only root and secret access.
   Negative secret/permissions cases must fail with safe errors. Never start real polling.
4. Generate per-platform Syft SPDX inventories. Export tested Docker image archives
   and hashes through same-run Actions artifacts, along with inventories and smoke results.
5. Collect/validate matching source and notices for the actual installed closure on
   both architectures. Any missing component, hash, required source, or notice blocks
   publication. Controlled suite and both native jobs must all succeed first.
6. Attach all source/notice assets to a sources-only draft at `sources-VERSION` and
   the same source commit, then publish that completed sources-only release. Verify
   anonymous material retrieval before pushing images. Keep the final `VERSION`
   image release draft. This ordering supports immutable releases: no asset is added
   to a release after its publication. A previous sources-only release may be reused
   only if all current material/inventory hashes agree; otherwise use a new version.
7. Import both same-run archives with distinct local image references; compare both
   archive hashes and image/config IDs to the checked records before pushing either
   platform. Confirm the full pre-push gate set is successful; only then push these
   images without rebuilding. Use unique
   run/attempt/architecture auxiliary references; they are not production selectors.
8. Record resulting child manifest digests; assemble exactly the two required platforms
   into the exact version index with `docker buildx imagetools create`. Check the
   index platform mapping and each child's config identity against the tested records.
9. Record index digest and exact raw bytes, create the final release manifest, and
   generate signed provenance over the index plus an attestation over the release manifest.
10. Attach all final evidence to the image-release draft. Check both-platform anonymous
    pulls and account-free local-bundle verification, including negative cases, then
    finalize by publishing the completed image release.
11. Redownload the public final assets/materials anonymously and verify their signatures,
    identities and hashes. Acceptance requires these checks and the successful workflow
    result; failure after any push is incomplete, not repaired by replacing immutable
    assets. No preview is advertised as accepted before the acceptance stage passes.

Failures after a registry write can leave partial artifacts. Mark the release incomplete
in release notes and the workflow result without mutating locked assets,
do not advertise it as accepted, and keep its source assets available. Do not repair a
published version by moving its tag; use a new version when content must change.
No publication workflow remotely deploys or updates an operator's server.

## Required public artifacts

| Asset | Contents / identity |
|---|---|
| Exact version image | Index and both children, source/version/revision metadata, retained runtime notices |
| `release-index.json` | Unmodified OCI index bytes; SHA256 equals selected index digest |
| `provenance.sigstore.json` | GitHub signed build provenance whose subject is the image index digest/name |
| `release-manifest.json` | Schema version, version/revision/repository ID/workflow run, index/child/config identities, platforms, package version, source-release location, all material hashes/public URLs, preview/gate status with feature-acceptance versus inherited stable-readiness scope |
| `release-manifest.sigstore.json` | Detached attestation over the exact release-manifest bytes |
| `sbom-amd64.spdx.json`, `sbom-arm64.spdx.json` | Inventory of each tested/distributed image; associated with child and index identities in release manifest |
| `source-manifest.json` | Actual component-to-source/notice/build-material mapping with acquisition checksums and architecture coverage; hosted in the completed sources-only release |
| `sources-*.tar.*`, `notices.tar.*` | Required corresponding materials and license texts in the sources-only release; logical parts when large |
| `SHA256SUMS` | Asset hashes for transfer integrity; signature trust comes from the signed manifest, not this file alone |
| Verification guide | Trusted project/repository ID/workflow identity, pinned verifier versions, runnable positive/negative checks |

Avoid cyclic hash definitions: the release manifest hashes material assets, not itself,
its own attestation, or `SHA256SUMS`. Checksums can list the finalized manifest and bundles.
Bind `source-manifest.json` and architecture SBOM hashes into the signed release manifest.
Material public URLs must use the canonical project's final or `sources-VERSION` release;
the sources-only release is not an accepted runnable image release. Its complete assets
remain available if final image publication later fails.
Use `application/vnd.in-toto+json`/Sigstore bundle formats as produced by the selected
GitHub tooling; do not invent a custom signature protocol.

## Source collection and validation interfaces

CI-only `collect_sources.py` uses Python 3.13 standard-library metadata, hashing,
TOML, and archive support plus pinned external Docker/APT/dpkg tooling:

```text
inventory --image IMAGE --platform PLATFORM --output DIRECTORY
collect --inventory FILE [--inventory FILE ...] --policy release/source-policy.json
        --lock uv.lock --output DIRECTORY
```

Inventory all Debian binary/source identities and `Built-Using`, both Python environments,
and copied unmanaged binaries. Query exact Debian source identity using metadata, including
source versions differing from binary versions. Retain `.dsc` and every referenced source/
patch archive, exact installed dependency sdists, required tool/base recipes, embedded
notices, and source/build materials required by repository policy. Record verified
acquisition and output hashes; validate safe unpacking without executing upstream code.

`validate_release.py` exposes:

```text
sources --directory DIRECTORY
promotion --record FILE --image IMAGE
bundle --directory DIRECTORY
verify --directory DIRECTORY --image IMAGE_AT_DIGEST --version TAG
       --source-revision COMMIT --policy release/verification-policy.json
```

Nonzero exit on missing/mismatched material or identity; bounded safe diagnostics.
`verify` supports host Python 3.11+, invokes the pinned `gh` verifier, enforces trusted
repository/workflow/certificate identity and digest/asset policy, and emits a nonsecret
summary. The reviewed policy records the canonical numeric repository ID resolved from
GitHub, trusted workflow path, and expected issuer/hosted-builder constraints. Unit tests
exercise missing sources, unsafe archives, stale inventories, artifact swaps, unsupported
platforms, mismatched source/versions, and wrong signing identities using controlled fixtures.
Include the stage distinction: duplicate image versions fail publisher pre-push authorization,
while final manifest assembly and account-free verification accept matching existing versions.
No read/verify command repurposes the publisher's availability/nonexistence query.

## Anonymous verification and public access

Use regctl's `--format raw-body` to retain exact index bytes; do not pretty-print JSON
before hashing. With local bundles, the verifier authenticates `release-index.json`
and `release-manifest.json`, checks signer workflow, source tag/full commit, trusted
repository ID, and hosted-builder identity, then compares the index hash to the selected
digest and checks all material hashes. Negative cases include modified index/manifest,
wrong digest, different source tag/revision/workflow/repository, and substituted SBOM.

Use established verifier trust roots. A release's own supplied root is not a trust anchor.
The raw-index/image-subject local verification method must pass an integration proof with
the real selected tools and signed bundle before release finalization. A Docker-save
tar is not the attestation subject and must not be used as a substitute.

Run pull/verification checks with empty Docker and GitHub configurations and no inherited
authentication variables. Public GHCR pulls and public asset downloads require no account.
Do not use `gh attestation verify oci://...` as the default path because that path requires
registry authentication. No check prints an operator credential or uses a real bot token.

## Evidence and availability

The release manifest links native check records and sanitized external validation status.
Release acceptance is the linked workflow's result, including downloads after finalization;
the immutable manifest does not claim those future downloads have passed.
An available preview still has open live gates; controlled checks do not close them.
Source assets remain publicly available for distributed images, including incomplete or
superseded versions. Existing feature 001/005/006 live/manual/container gates are inherited.
README, public release notes, and `deploy/README.md` must agree with recorded evidence.
Feature-008 completion additionally requires passing its own controlled/native/public/server
checks and representative real delivery, plus execution/assessment of the inherited matrix.
Only evidenced pre-existing source limitations may remain open; they continue blocking
stable readiness and unsupported capability claims. A deployment regression or unclassified
failure blocks feature completion. Completing the matrix assessment does not mark an
inherited failed/blocked gate passed.

# Public release distribution

The public-image pipeline is being implemented. Public preview distribution, real signed
index proof, and server acceptance remain pending in
[feature 008 validation](../specs/008-public-docker-deployment/validation.md). A local
build, a controlled certificate fixture, or a successful offline smoke is not public
release acceptance. The existing root Compose file remains the local-build entry point.

## Maintainer release procedure

Release from the canonical public repository `hman-pro/openmedia`, numeric GitHub
repository ID **1380348601**. Tag creation must be restricted to maintainers, and tag
updates/deletion restricted, through active repository rulesets. Enable immutable
releases in repository settings before staging sources. The workflow validates the
actual effective rules and later requires the published sources release's `immutable`
flag; a tag prefix or public repository alone is insufficient authority.

Complete all story implementation and the final candidate gates before creating a
public preview (T059–T062). On the reviewed, committed candidate, choose a new exact
version. Existing image versions are never overwritten. For example:

```bash
set -euo pipefail
version=v0.1.0-preview.1
revision=$(git rev-parse HEAD)
git tag --annotate "sources-$version" "$revision" --message "Matching sources for $version"
git push origin "refs/tags/sources-$version"
git tag --annotate "$version" "$revision" --message "$version preview"
git push origin "refs/tags/$version"
```

Both tags must point to the same full commit. Source tags do not trigger image pushes.
The release workflow serializes publication without cancellation, reruns controlled
checks and both **native** architectures, and checks complete inventories, matching
sources/notices, pins, source availability, and both imported archive/config identities
before the first image push. Publishing jobs do not rebuild application images.

The completed `sources-VERSION` release is published first with all its assets. Its
public assets must download anonymously and match every recorded hash. The image release
remains a draft. Only matching existing immutable source assets may be reused; nothing
is appended to a published release. The final release contains the exact OCI index,
raw child manifests, per-platform SPDX inventories, signed provenance, signed release
manifest, and checksums. Sources/notices remain in the sources-only release. The manifest
hashes material assets, and excludes itself, its own attestation, and `SHA256SUMS` to
avoid cycles. Transfer checksums alone are not signature verification.

Native job artifacts are temporary (one-day retention). They contain checked Docker
archives, actual inventories, retained notices and smoke records; these are distinct
from the indefinitely retained public source materials. Archive SHA256, OCI config ID,
child manifest digest and index digest identify different objects. On Docker's containerd
image store `docker inspect .Id` can identify an index; promotion reads actual config bytes
from Docker archives instead. Default build provenance is disabled, and the final exact
index is signed after promotion.

The workflow starts with `contents: read`; ordinary PR/branch checks have no publishing
permissions or bot token. Authority uses package read access. Source staging uses
contents write; promotion uses package write and contents write to record incomplete
publication; signing uses contents write, OIDC and attestations write. All external
actions use reviewed full commits, and downloaded tools use reviewed exact checksums.
No workflow deploys or updates an operator's server.

At the first package creation, the owner must open the canonical
[OpenMedia package settings](https://github.com/hman-pro/openmedia/pkgs/container/openmedia)
and set GHCR visibility to **public**. Repository visibility does not set package
visibility. If anonymous pulls fail, distribution remains incomplete and the final
release stays draft. After the owner corrects visibility, rerun only the failed evidence
job against the already promoted matching images; do not rerun successful publication
or move version tags. T060 records the actual owner-controlled bootstrap/settings proof.

A pre-push failure writes no images. Failure after any attempted image push may leave
partial distributed artifacts: preserve their source materials and label the release
**INCOMPLETE**. Signing/image access failure keeps the final release draft. Failed
public evidence downloads after finalization keep the immutable release and sources,
but prevent acceptance. Never repair a distributed version by changing its content.
Use a new version when content must change. Preserve partial promotion-state artifacts
and the failing Actions run for diagnosis.

## Account-free verification

Use host Python 3.11+ and GitHub CLI **2.103.3**. Obtain the verifier and
[verification policy](../release/verification-policy.json) from a separately reviewed
canonical repository commit, rather than trusting a policy supplied by downloaded
release assets. The verifier independently pins repository ID 1380348601, the canonical
repository URL, `.github/workflows/release.yml`, GitHub's OIDC issuer and GitHub-hosted
builders. It uses the CLI's established verifier roots. Release-supplied roots are rejected.

On a supported native Linux host, install the checksum-pinned CLI using the reviewed
repository helper (it also supports pinned Syft, regctl and Buildx for maintainers):

```bash
set -euo pipefail
python3 scripts/release/install_tools.py --output "$PWD/release-tools" gh
export PATH="$PWD/release-tools:$PATH"
gh --version
```

Choose the release tag, full expected source commit and index digest independently.
Download `release-manifest.json`, both `.sigstore.json` bundles, `release-index.json`,
`manifest-amd64.json`, `manifest-arm64.json`, both `sbom-*.spdx.json`, `SHA256SUMS`, and
every material asset listed in the manifest from the canonical version or matching
`sources-VERSION` release into one directory. These HTTPS assets and image pulls require
no GitHub or registry account. The source parts contain the exact material, installed
notice and recipe files declared in `source-manifest.json`; verification checks their
inner hashes and paths as well as the outer archive hashes.

```bash
set -euo pipefail
# Replace these with the reviewed release selection; never paste a credential here.
version=v0.1.0-preview.1
revision=REVIEWED_FULL_40_HEX_COMMIT
image=ghcr.io/hman-pro/openmedia@sha256:REVIEWED_64_HEX_INDEX_DIGEST
python3 scripts/release/validate_release.py verify --directory release-assets \
  --image "$image" --version "$version" --source-revision "$revision" \
  --policy release/verification-policy.json
```

The helper invokes `gh attestation verify` on the **exact raw index bytes** and exact
release-manifest bytes using local bundles and empty GitHub/Docker configurations,
with inherited authentication variables removed. It enforces signed repository numeric
ID, source ref/commit, workflow/issuer and hosted builder, then verifies the selected
index, child/config joins and all source/SBOM/material hashes. It does not use the
registry-authenticated `gh attestation verify oci://...` path or a Docker-save tar as
a substitute subject.

Require a nonzero exit for tampering and wrong selections before relying on verification:

```bash
set -euo pipefail
cp release-assets/release-index.json release-index.original
trap 'cp release-index.original release-assets/release-index.json; rm -f release-index.original' EXIT
printf ' ' >> release-assets/release-index.json
if python3 scripts/release/validate_release.py verify --directory release-assets \
  --image "$image" --version "$version" --source-revision "$revision" \
  --policy release/verification-policy.json; then
  echo 'ERROR: modified index unexpectedly verified' >&2
  exit 1
fi
cp release-index.original release-assets/release-index.json
```

Repeat in a disposable directory for a modified manifest or SBOM, and a wrong expected
version/commit/digest. The publication workflow also exercises the real local bundles
with an incorrect signer workflow before finalization. The actual own-release signed
raw-index proof is a mandatory public acceptance gate, not established by the controlled
certificate fixtures.

A successful public distribution workflow accepts a **preview**, with external
server/media and inherited stable-readiness gates reported separately. The immutable
manifest references pending gates; the completed Actions run records the later public
download result. A sources-only release is a redistribution artifact, not a runnable
accepted image release.

Included runtime notice texts can also be read without polling:

```bash
set -euo pipefail
docker run --rm --network none --read-only --cap-drop ALL \
  --security-opt no-new-privileges --entrypoint gzip "$image" \
  -dc /usr/local/share/doc/openmedia/RUNTIME_NOTICES.txt.gz
```

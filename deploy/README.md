# Public release distribution

The public-image pipeline is being implemented. Public preview distribution, real signed
index proof, and server acceptance remain pending in
[feature 008 validation](../specs/008-public-docker-deployment/validation.md). A local
build, a controlled certificate fixture, or a successful offline smoke is not public
release acceptance. The existing root Compose file remains the local-build entry point.

## Install on a single server

Use Bash on **Ubuntu 24.04 or 26.04 LTS, amd64 or arm64**, with standard rootful
Docker Engine. Rootless Docker and user-namespace remapping require a separate design.
These are supported targets; actual host acceptance for each combination is tracked in
[validation](../specs/008-public-docker-deployment/validation.md), with T063 still pending.
Use one operator/change session. The bot needs outbound HTTPS to Telegram and the media
sources, DNS, and HTTPS to GHCR/GitHub for release acquisition; it opens no inbound ports.
Do not add a second process manager or another polling service.

### Install Docker and check capabilities

On a clean supported host, follow Docker's [official Ubuntu APT instructions](https://docs.docker.com/engine/install/ubuntu/).
Review conflicting distribution packages there before using an existing Docker host;
do not remove packages used by unrelated services. This clean-host block uses Docker's
signed stable APT repository and stops at the first failure:

```bash
(
set -euo pipefail
. /etc/os-release
test "$ID" = ubuntu
case "$VERSION_ID" in 24.04|26.04) ;; *) exit 1 ;; esac
arch=$(dpkg --print-architecture)
case "$arch" in amd64|arm64) ;; *) exit 1 ;; esac
sudo apt-get update
sudo apt-get install -y ca-certificates curl
sudo install -d -m 0755 /etc/apt/keyrings
sudo curl --fail --silent --show-error --location \
  https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
sudo chmod a+r /etc/apt/keyrings/docker.asc
printf '%s\n' 'Types: deb' 'URIs: https://download.docker.com/linux/ubuntu' \
  "Suites: ${UBUNTU_CODENAME:-$VERSION_CODENAME}" 'Components: stable' \
  "Architectures: $arch" 'Signed-By: /etc/apt/keyrings/docker.asc' |
  sudo tee /etc/apt/sources.list.d/docker.sources >/dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo docker version
sudo docker compose version
up_help=$(sudo docker compose up --help)
run_help=$(sudo docker compose run --help)
for flag in --wait --wait-timeout --force-recreate --no-build --pull; do
  grep -F -- "$flag" <<< "$up_help" >/dev/null
done
for flag in --rm --no-deps --no-tty --pull; do
  grep -F -- "$flag" <<< "$run_help" >/dev/null
done
sudo docker info --format '{{json .SecurityOptions}}'
)
```

Record OS/architecture, client/server Engine and Compose versions and flag results in
your sanitized acceptance notes. Check the security options for unexpected rootless or
userns operation and stop if present. This guide requires the flags above, rather than
assuming an installed version supports them. The [run](https://docs.docker.com/reference/cli/docker/compose/run/)
and [up](https://docs.docker.com/reference/cli/docker/compose/up/) references define their behavior.

### Provision protected configuration and credential

From a separately reviewed checkout, verify the selected release with the
[account-free verification procedure](#account-free-verification) before selecting its
literal index digest. No public release is accepted yet; do not invent a digest to
bypass that prerequisite. Install the reviewed files, then replace the image placeholder
in `deploy.env` with that exact verified digest:

```bash
(
set -euo pipefail
sudo install -d --mode=0750 --owner=root --group=root /opt/openmedia
sudo install --mode=0640 --owner=root --group=root deploy/compose.yaml /opt/openmedia/compose.yaml
sudo install --mode=0600 --owner=root --group=root deploy/deploy.env.example /opt/openmedia/deploy.env
sudoedit /opt/openmedia/deploy.env
sudo install -d --mode=0700 --owner=root --group=root /opt/openmedia/secrets
sudoedit /opt/openmedia/secrets/telegram_bot_token
sudo chown root:10001 /opt/openmedia/secrets/telegram_bot_token
sudo chmod 0640 /opt/openmedia/secrets/telegram_bot_token
sudo stat -c '%U:%g %a %n' /opt/openmedia/secrets /opt/openmedia/secrets/telegram_bot_token
getent group 10001 || test "$?" -eq 2
getent passwd | awk -F: '$4 == 10001 {print $1 ": primary GID 10001"}'
)
```

Review both the group's supplementary members and users with primary GID 10001. Resolve
any unrelated membership before proceeding. Use a protected editor/input, never a token
literal in shell history, process arguments, `deploy.env`, the repository or evidence.
The secret contains ASCII `[0-9]+:[A-Za-z0-9_-]+` and optionally one final LF/CRLF.
Parent directory mode 0700 protects host traversal; the privileged daemon mounts the
file, and container UID/GID 10001 reads its `root:10001` mode 0640 inode. Compose's
file-backed secret `uid`, `gid`, `mode` fields do not change host inode permissions.
These secrets do not encrypt host storage; protect host access and credential backups.

Keep `OPENMEDIA_TOKEN_FILE` absolute. Only the listed nonsecret settings are mapped;
`deploy.env` is interpolation input, not a wholesale service `env_file`.
Never add a direct `TELEGRAM_BOT_TOKEN` mapping to this Compose service. The existing
root `compose.yaml` and `.env.example` remain available for direct-token local builds.
`scripts/dev.sh` continues to obtain its direct token from the keyring/exported environment;
remove both token keys from its nonsecret `.env` when using that workflow.

The container retains UID/GID 10001, init, read-only root, all capabilities dropped,
no-new-privileges, 2 CPUs, 2 GiB memory, 30-second stop grace and console rotation
10 MiB × 3. Its separate 512 MiB `/tmp` tmpfs consumes the same 2 GiB memory budget;
media and request state disappear on recreation. No persistent media/work volume exists.
Diagnostics default off. Enabling them requires explicitly provisioning a protected
writable log mount outside the work directory under the
[feature 002 contract](../specs/002-file-logging/contracts/diagnostic-log.md);
merely changing the flag fails local validation on the read-only root. Diagnostic files
contain submitted links and Telegram identifiers; keep them private with bounded retention.

### Select, pull and preflight without polling

Use a fresh Bash session. Set `CANDIDATE_IMAGE` to the same **verified literal index
digest** entered in `/opt/openmedia/deploy.env`, then define the function below. A normal
exported shell variable overrides Compose env-file interpolation. This wrapper clears
inherited environment settings and supplies only a command-scoped image selection;
no lingering image, token-path, limits or diagnostic override can affect these commands.
Compose's `${OPENMEDIA_IMAGE:?…}` tests presence only; this function enforces the shape.
It does not establish signature trust. The env file remains the selected configuration.

```bash
CANDIDATE_IMAGE=ghcr.io/hman-pro/openmedia@sha256:REPLACE_WITH_VERIFIED_64_HEX_INDEX_DIGEST
dc() {
  local image_ref="$1"
  shift
  if [[ ! "$image_ref" =~ ^ghcr\.io/hman-pro/openmedia@sha256:[0-9a-fA-F]{64}$ ]]; then
    echo 'Select a verified digest-qualified OpenMedia image first' >&2
    return 2
  fi
  sudo env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin OPENMEDIA_IMAGE="$image_ref" \
    docker compose --project-name openmedia --env-file /opt/openmedia/deploy.env \
    --file /opt/openmedia/compose.yaml "$@"
}
```

Require this entire block to return zero before activation. It validates the selected
file without an override too, pulls only the verified candidate, and runs the bundled
CLI as UID/GID 10001 with the actual mounted secret:

```bash
(
set -euo pipefail
[[ "$CANDIDATE_IMAGE" =~ ^ghcr\.io/hman-pro/openmedia@sha256:[0-9a-fA-F]{64}$ ]]
selected=$(sudo env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin docker compose \
  --project-name openmedia --env-file /opt/openmedia/deploy.env \
  --file /opt/openmedia/compose.yaml config --images)
test "$selected" = "$CANDIDATE_IMAGE"
dc "$CANDIDATE_IMAGE" config --quiet
dc "$CANDIDATE_IMAGE" pull openmedia
dc "$CANDIDATE_IMAGE" run --rm --no-deps -T --pull never \
  openmedia python -m openmedia --check-config
)
```

`run` overrides the polling command; it uses its own bounded tmpfs and no shared work
mount. The CLI checks only local settings, tools and writable scratch/optional logs.
The pull requires registry connectivity; the subsequent preflight performs no network
requests or polling. A missing/unreadable/malformed credential returns 2 with redacted
output. A failed verification/pull/config/preflight aborts activation and leaves any
existing bot untouched. A shape-valid token is not proof of Telegram authentication.
Do not use `up` for validation. Do not publish full environment or diagnostic dumps.

### First activation and failed-start cleanup

Only continue after verification and the complete preflight block succeed. Check all
other projects, hosts and development sessions using this bot, and stop their poller
before activation. Inventory local containers with `sudo docker ps` and project labels
without printing their environments. The operator must establish token ownership across
hosts; container discovery cannot prove that a remote poller is absent. This first-install
block refuses an existing running `openmedia` service; update/migration procedures are
separate Phase 5 work. At most one polling container per token is permitted.

```bash
(
set -euo pipefail
running=$(dc "$CANDIDATE_IMAGE" ps --status running -q openmedia)
test -z "$running"
cleanup_candidate() {
  dc "$CANDIDATE_IMAGE" stop --timeout 30 openmedia || return 1
  local running
  running=$(dc "$CANDIDATE_IMAGE" ps --status running -q openmedia) || return 1
  test -z "$running"
}
# Even a failed wait may leave a running container. Cleanup on errors and signals.
trap 'status=$?; trap - EXIT; if ! cleanup_candidate; then echo "Cleanup failed: inspect and stop candidate before recovery" >&2; fi; exit "$status"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
dc "$CANDIDATE_IMAGE" up --no-build --pull never --force-recreate \
  --wait --wait-timeout 180 openmedia
container=$(dc "$CANDIDATE_IMAGE" ps -q openmedia)
test -n "$container"
test "$(sudo docker inspect --format '{{.State.Health.Status}}' "$container")" = healthy
test "$(sudo docker inspect --format '{{.Config.Image}}' "$container")" = "$CANDIDATE_IMAGE"
trap - EXIT INT TERM
printf '%s\n' 'Startup health passed; record identity and perform real delivery acceptance.'
)
```

Keep this recovery block beside startup. After terminal loss or uncertain interruption,
run it and require success before attempting another startup or recovery:

```bash
(
set -euo pipefail
dc "$CANDIDATE_IMAGE" stop --timeout 30 openmedia
running=$(dc "$CANDIDATE_IMAGE" ps --status running -q openmedia)
test -z "$running"
dc "$CANDIDATE_IMAGE" ps -a openmedia
)
```

Health wait is bounded at 180 seconds. It reads the existing local heartbeat and successful
poll history; `--healthcheck` never creates a second poller (0 healthy, 1 unhealthy,
2 invalid settings). Health degradation alone triggers no restart agent. Successful
preflight is not real-token acceptance. Record actual OS/architecture, Engine/Compose,
verified source/index identity, health outcome and representative real Telegram delivery
for **T063** before claiming installation acceptance. Other host combinations remain pending.

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

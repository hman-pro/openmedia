# Quickstart Validation: Public Docker Deployment

This guide is for validating the future implementation. Planned deployment, workflow,
and release-helper files do not exist merely because this planning document exists.
Do not record the examples below as passed until they are executed against a concrete
release. Record sanitized results in this feature's future `validation.md`.

## 1. Controlled configuration and regression checks

From the repository root, with Python 3.13, uv, FFmpeg/ffprobe, and Deno available:

```sh
uv sync --locked --group dev
uv run --locked pytest tests/unit/test_config.py tests/integration/test_runtime.py
uv run --locked pytest tests/unit/test_release_manifest.py tests/integration/test_release_tools.py
uv run --locked pytest
```

Expected: valid direct and file inputs work; both-present inputs fail even when empty;
missing/unreadable/directory/special/oversized/blank/malformed/non-ASCII/multiline files
fail without blocking or leaking content. Accept a token with zero or one terminal LF/CRLF.
Verify exact boundary sizes and malformed path handling. Check token absence in str/repr,
CLI stdout/stderr, formatted traceback, console and enabled diagnostics. Prove local
preflight/health paths never build a poller or contact Telegram, and workers receive
neither token input. Existing media/merge/isolation/shutdown tests remain green.

The second command group names new tests to implement. Controlled fixtures substitute
for network acquisitions, GitHub, Docker command results, and clocks as appropriate;
actual native container execution belongs to the next section.

## 2. Native restricted-container checks

Use a native Linux host/runner of the target architecture with Docker. Run this once
for amd64 and once for arm64; the shown platform value is for an amd64 runner.

```sh
PLATFORM=linux/amd64
docker build --platform "$PLATFORM" --tag openmedia:validation .
scripts/smoke-container.sh openmedia:validation
uv run --locked python scripts/release/collect_sources.py inventory \
  --image openmedia:validation --platform "$PLATFORM" --output "dist/inventory-${PLATFORM#linux/}"
```

Expected: fake file secret readable by UID/GID 10001, no real polling, no network,
read-only root, dropped capabilities, init, bounded/writable tmpfs, and declared resource
limits. Python, bundled EJS, Deno, FFmpeg and ffprobe work; a controlled local merge
preserves streams. File-secret error cases have redacted nonzero results. Collect effective
image IDs, tool versions and restrictions. Retain the existing root Compose local-build
path and confirm it still renders/builds using its documented secret configuration.

The script must use ephemeral fixtures and cleanup containers/files on failure. Runtime
images contain no pytest/development tooling; mount only sanitized probe fixtures when
needed. Container checks do not count as a real Telegram startup or source delivery.

## 3. Source assets and release-policy checks

After collecting both native inventories using the paths emitted by the inventory command:

```sh
uv run --locked python scripts/release/collect_sources.py collect \
  --inventory dist/inventory-amd64/inventory.json \
  --inventory dist/inventory-arm64/inventory.json \
  --policy release/source-policy.json --lock uv.lock --output dist/release
uv run --locked python scripts/release/validate_release.py sources --directory dist/release
```

Use inventories copied from the respective native jobs into those two directories.
Expected: all installed Debian/application-Python/system-Python/unmanaged components map
to reviewed sources/notices. Debian source archives and `Built-Using` edges, locked sdists,
base/tool recipes and embedded notices are present and hash verified. Missing material,
unsafe archives, or a mismatched version causes a nonzero validation result.

Run a PR in the canonical repository: controlled/native gates run, no release image is
pushed, no bot credential is present, and no publishing permission is granted. A deliberate
failed native check or missing-source fixture prevents every image push in the tag path too.
Repository settings must establish maintainer-only version tags and public package access.

The first publication is a separate maintainer action after implementation review: create
the `sources-VERSION` tag and then its preview `VERSION` tag at the same reviewed commit,
under the configured maintainer-only rules. Confirm both native archives are imported
and checked before either image is pushed, without rebuilding. The workflow publishes a
completed sources-only release before images, keeps the image release draft until all
evidence is attached, and marks partial failures incomplete. Test with release immutability
enabled so no step depends on adding assets after publication.
Verify each boundary separately: failed pre-push checks produce zero image pushes;
signing/local-verification or anonymous-image failures after a push leave the final
release draft and distribution incomplete; failures redownloading final public evidence
after release finalization prevent acceptance. All distributed images retain source assets.

## 4. Public access and signature verification

Use a clean shell with no GitHub token, registry login, or inherited authentication config.
Install checksum-verified GitHub CLI 2.103.3 through its official release; the supplied
validator supports Python 3.11+. Use the reviewed checkout/policy as the trust input.
Choose an actual published preview tag and its independently expected full source commit.

```sh
VERSION=v0.1.0-preview.1
SOURCE_COMMIT=$(git rev-parse "$VERSION^{commit}")
mkdir -p /tmp/openmedia-release
curl --fail --location --output /tmp/openmedia-release/release-manifest.json \
  "https://github.com/hman-pro/openmedia/releases/download/$VERSION/release-manifest.json"
curl --fail --location --output /tmp/openmedia-release/release-manifest.sigstore.json \
  "https://github.com/hman-pro/openmedia/releases/download/$VERSION/release-manifest.sigstore.json"
curl --fail --location --output /tmp/openmedia-release/release-index.json \
  "https://github.com/hman-pro/openmedia/releases/download/$VERSION/release-index.json"
curl --fail --location --output /tmp/openmedia-release/provenance.sigstore.json \
  "https://github.com/hman-pro/openmedia/releases/download/$VERSION/provenance.sigstore.json"
```

Download the SBOMs, source manifest, notices, source parts, and other material assets
using their public URLs in the release manifest. Source assets live in the separate
`sources-VERSION` release. Verify with
the implemented policy checker; the following selects the claimed digest, then authenticates
and cross-checks it before any deployment use:

```sh
CANDIDATE_IMAGE=$(python3 -c 'import json; p=json.load(open("/tmp/openmedia-release/release-manifest.json")); print("ghcr.io/hman-pro/openmedia@" + p["index_digest"])')
EMPTY_GH_CONFIG=$(mktemp -d /tmp/openmedia-gh.XXXXXX)
env -u GH_TOKEN -u GITHUB_TOKEN -u GH_ENTERPRISE_TOKEN -u GITHUB_ENTERPRISE_TOKEN \
  GH_CONFIG_DIR="$EMPTY_GH_CONFIG" python3 scripts/release/validate_release.py verify \
  --directory /tmp/openmedia-release --image "$CANDIDATE_IMAGE" \
  --version "$VERSION" --source-revision "$SOURCE_COMMIT" \
  --policy release/verification-policy.json
```

Expected: local-bundle verification succeeds without an account; index SHA256 equals the
selected digest; signer/workflow/source/repository numeric ID and signed asset hashes match.
This deliberately verifies an existing image version. Confirm that only the publisher's
pre-push path rejects duplicate versions; local record/manifest validation and verification
accept a matching existing release and reject its altered identities without registry writes.
Exercise modified index/manifest, swapped SBOM, different source tag/commit/workflow/repository,
and wrong digest cases: each fails before acceptance. Test the actual image-subject bundle
against the raw index bytes, not a Docker-save tar. No arbitrary bundled root is trusted.

On native test machines, pull both supported platform variants using fresh empty Docker
configuration (the example empty directory must contain no credentials):

```sh
EMPTY_DOCKER_CONFIG=$(mktemp -d /tmp/openmedia-docker.XXXXXX)
sudo docker --config "$EMPTY_DOCKER_CONFIG" pull --platform linux/amd64 "$CANDIDATE_IMAGE"
sudo docker --config "$EMPTY_DOCKER_CONFIG" pull --platform linux/arm64 "$CANDIDATE_IMAGE"
```

Retrieval of both architectures can run on one client; execution still needs each native
runner. Do not count a logged-in pull as anonymous access. Public package visibility and
public source/evidence download success are explicit recorded gates.

## 5. Real-server setup and preflight

Use an operator-owned Ubuntu 24.04/26.04 LTS server with standard rootful Docker Engine
and Compose installed from the [official repository](https://docs.docker.com/engine/install/ubuntu/).
Record OS, architecture and these capability checks:

```sh
sudo docker version
sudo docker compose version
sudo docker compose up --help
sudo docker compose run --help
```

Install the reviewed files, edit the nonsecret image/settings selection, and enter the
token through the protected editor (no literal token appears in these commands):

```sh
sudo install -d --mode=0750 --owner=root --group=root /opt/openmedia
sudo install --mode=0640 --owner=root --group=root deploy/compose.yaml /opt/openmedia/compose.yaml
sudo install --mode=0600 --owner=root --group=root deploy/deploy.env.example /opt/openmedia/deploy.env
sudoedit /opt/openmedia/deploy.env
sudo install -d --mode=0700 --owner=root --group=root /opt/openmedia/secrets
sudoedit /opt/openmedia/secrets/telegram_bot_token
sudo chown root:10001 /opt/openmedia/secrets/telegram_bot_token
sudo chmod 0640 /opt/openmedia/secrets/telegram_bot_token
```

Confirm there are no unrelated host users in GID 10001. Set no literal token in env files. See
[configuration.md](contracts/configuration.md) for exact values/restrictions.

For repeatable validation, define this shell convenience function; its first argument
selects the image for that command only:

```sh
dc() {
  image_ref="$1"
  shift
  sudo env OPENMEDIA_IMAGE="$image_ref" docker compose -p openmedia \
    --env-file /opt/openmedia/deploy.env -f /opt/openmedia/compose.yaml "$@"
}
dc "$CANDIDATE_IMAGE" config --quiet
dc "$CANDIDATE_IMAGE" pull openmedia
dc "$CANDIDATE_IMAGE" run --rm --no-deps -T --pull never \
  openmedia python -m openmedia --check-config
```

Expected: no poller starts, UID 10001 reads the mounted token, only local validation
runs, and a running previous bot remains unaffected. A failed pull or malformed/unreadable
secret must stop the procedure without interrupting the old deployment. Use isolated
acceptance fixtures for failures rather than corrupt a production credential.

## 6. Activation, update failure, and rollback

On first installation, confirm no other poller uses the token. For an existing published
deployment, record the actual container and previous immutable image before stopping it:

```sh
CURRENT_CONTAINER=$(dc "$CANDIDATE_IMAGE" ps -q openmedia)
PREVIOUS_IMAGE=$(sudo docker inspect --format '{{.Config.Image}}' "$CURRENT_CONTAINER")
sudo docker inspect --format '{{.Id}} {{.Image}} {{.State.Running}}' "$CURRENT_CONTAINER"
```

The record/stop commands apply only when a previous container exists. Require this
stop-and-confirm block to return zero before proceeding; otherwise abort activation:

```sh
dc "$CANDIDATE_IMAGE" stop --timeout 30 openmedia &&
  test "$(sudo docker inspect --format '{{.State.Running}}' "$CURRENT_CONTAINER")" = false
```

After confirmed stop (or a first installation with no other poller), start the candidate.
The failure branch explicitly cleans up and returns failure:

```sh
if dc "$CANDIDATE_IMAGE" up --no-build --pull never --force-recreate \
    --wait --wait-timeout 180 openmedia; then
  printf '%s\n' 'Candidate is healthy; persist its selection next.'
else
  dc "$CANDIDATE_IMAGE" stop --timeout 30 openmedia
  dc "$CANDIDATE_IMAGE" ps -a openmedia
  false
fi
```

On interruption or uncertain terminal state, execute cleanup and confirm no candidate
is running before considering recovery:

```sh
dc "$CANDIDATE_IMAGE" stop --timeout 30 openmedia
dc "$CANDIDATE_IMAGE" ps -a openmedia
```

Expected: an unhealthy candidate is stopped; Compose wait failure alone is not cleanup.
To explicitly roll back to a recorded available compatible previous digest with current
settings/token:

```sh
dc "$PREVIOUS_IMAGE" pull openmedia
```

Proceed only if the pull succeeds. Then require successful preflight before running
the separate rollback startup block:

```sh
dc "$PREVIOUS_IMAGE" run --rm --no-deps -T --pull never \
  openmedia python -m openmedia --check-config
```

```sh
if dc "$PREVIOUS_IMAGE" up --no-build --pull never --force-recreate \
    --wait --wait-timeout 180 openmedia; then
  printf '%s\n' 'Previous release is healthy; persist its selection next.'
else
  dc "$PREVIOUS_IMAGE" stop --timeout 30 openmedia
  dc "$PREVIOUS_IMAGE" ps -a openmedia
  false
fi
```

Failed rollback startup needs the same explicit stop cleanup. After healthy activation
or rollback, update only `OPENMEDIA_IMAGE` to the healthy selected digest in a protected
copy, inspect the nonsecret diff, then replace the env file atomically on the same filesystem:

```sh
sudo install --mode=0600 --owner=root --group=root /opt/openmedia/deploy.env /opt/openmedia/deploy.env.next
sudoedit /opt/openmedia/deploy.env.next
sudo diff -u /opt/openmedia/deploy.env /opt/openmedia/deploy.env.next
sudo mv /opt/openmedia/deploy.env.next /opt/openmedia/deploy.env
```

A one-line image-selection diff is expected (`diff` returns 1 for that expected change).
Confirm persisted selection and running `.Config.Image` agree. Report persistence failure
as an incomplete operation. These examples assume the single-operator change session
defined in the operations contract.

Repeat with a candidate failing startup and a candidate never reaching health: failure
is bounded, no pollers overlap, and explicit rollback restores healthy service. Exercise
missing/incompatible previous images too. Migration starts from the root Compose project:
preserve its local image ID/configuration and stop that actual project before activation;
use its preserved image for recovery, as [operations.md](contracts/operations.md) specifies.

## 7. Operations and real media acceptance

```sh
dc "$CANDIDATE_IMAGE" ps
dc "$CANDIDATE_IMAGE" logs --tail 100 openmedia
ACTIVE_CONTAINER=$(dc "$CANDIDATE_IMAGE" ps -q openmedia)
sudo docker inspect --format '{{json .State.Health}}' "$ACTIVE_CONTAINER"
sudo docker stats --no-stream "$ACTIVE_CONTAINER"
```

Use the actually selected image in these commands after rollback. Verify normal polling
and a representative real delivery before declaring healthy service usable. Exercise:

1. A real active download/upload stopped by SIGTERM: application exits within 20 seconds,
   no child group survives, scratch data is cleaned, users resubmit, and no uncertain
   delivery is automatically repeated.
2. Unexpected process exit and host reboot recover service; intentionally stopped service
   stays stopped across reboot. Perform reboot testing on the acceptance host.
3. Temporary upstream outage becomes unhealthy without a health-triggered restart loop;
   polling recovers without a second poller.
4. Token rotation stops, atomically replaces the protected host file, validates and
   **force-recreates** the container; replacement credentials actually authenticate.
5. Secure config/credential backup, restore without request/media data, and project-scoped
   removal match the guide; remaining secret/config/log files are explicitly identified.
6. Existing YouTube, YouTube Music, LinkedIn video/image, Instagram video/image journeys
   retain native output, titles and refusal/failure behavior. Keep blocked categories open;
   include existing two-account, timing, music and title/manual acceptance obligations.

Real checks require the operator's token and deployment network and are separate from
controlled/native smoke results. Record actual OS/architecture coverage, source availability,
sanitized results, and remaining gates. README/release guidance must agree with the record.
Feature-008 completion requires passing its own controlled/native/public/server checks and
representative real delivery, and execution/assessment of the inherited matrix. Classify
every observed failure using earlier validation or an independent baseline; only evidenced
pre-existing source limitations may remain as open inherited gates. Unclassified failures
and deployment regressions block completion. Recording such a limitation is not a gate pass.
The feature may complete as a preview, but every release remains a preview until inherited
container and live stable-readiness gates have actually passed.

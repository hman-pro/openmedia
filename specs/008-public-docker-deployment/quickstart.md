# Quickstart Validation: Public Docker Deployment

Deployment and release tooling through Phase 4 are implemented. Execute the checks
below against a concrete candidate; record actual results in [validation.md](validation.md).
Public distribution and real-server acceptance remain pending. Update/rollback and
maintenance sections below still describe later-phase validation work.

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

Follow the executable [single-server installation guide](../../deploy/README.md#install-on-a-single-server)
on an operator-owned Ubuntu 24.04/26.04 LTS amd64/arm64 host. Use Bash and standard
rootful Docker from Docker's official signed APT repository, with no userns remapping.
The guide is authoritative for the exact shell blocks; do not substitute implicit
Compose discovery or a host-wide environment import.

1. Execute **Install Docker and check capabilities**. Record OS, architecture, Engine
   client/server, Compose versions, rootful security options and required `up`/`run`
   flags. Missing capabilities abort setup.
2. Complete **Account-free verification** with a separately trusted checkout/policy,
   expected version/source revision and literal index digest. Public-release T062
   remains required; offline fixtures cannot supply this trust proof.
3. Execute **Provision protected configuration and credential** from the reviewed
   checkout. The files are `/opt/openmedia/compose.yaml`, `/opt/openmedia/deploy.env`
   and `/opt/openmedia/secrets/telegram_bot_token`. Check root-owned 0700 parent,
   `root:10001` 0640 secret and unrelated primary/supplementary GID 10001 users.
   Enter credentials through the protected editor; never include them in evidence.
4. In the same Bash session, define `CANDIDATE_IMAGE` and `dc()` from **Select, pull
   and preflight without polling**. The wrapper validates exact digest shape and uses
   `sudo env -i` with only PATH and command-scoped image selection. Other settings
   come only from the explicit env file. Verify its selected image matches, then run
   `config --quiet`, `pull openmedia`, and
   `run --rm --no-deps -T --pull never openmedia python -m openmedia --check-config`.
   Require the whole block to succeed. It starts no poller, uses a separate tmpfs and
   leaves the current bot/workspaces untouched. Pull requires networking; the CLI
   preflight does not make network requests. Actual UID 10001 secret readability is
   exercised. Shape validation does not prove Telegram accepts the token.
5. Establish that no other project/host/development process polls this token. Execute
   **First activation and failed-start cleanup**, using
   `up --no-build --pull never --force-recreate --wait --wait-timeout 180 openmedia`.
   The first-install block refuses a currently running service. Error/signal traps
   stop failed candidates; the adjacent manual cleanup block handles terminal loss
   and confirms the candidate stopped before recovery. Existing service updates and
   migration use the update/rollback/migration runbook in section 6.
6. Record actual healthy polling and representative real Telegram delivery as **T063**.
   Local `--check-config` returns 0/2; `--healthcheck` returns 0/1/2 and only reads local
   freshness state. Neither creates a second poller. Successful offline checks do not
   pass T063. Other host combinations remain pending in the supported-host matrix.

For negative acceptance, use isolated fake secrets, never corrupt a production token:
missing/unreadable/malformed files must fail preflight with exit 2, no token/path leakage,
no polling and no interruption of a running bot. Record the actual failure separately
from a successful startup. Optional diagnostics require protected mounted storage under
feature 002; default diagnostics remain off. Tmpfs is 512 MiB within the 2 GiB limit.

## 6. Update failure, rollback, and migration validation

Use the executable [phase 5 runbook](../../deploy/README.md#update-rollback-and-migration).
Define its `dc`, `stop_selected`, `start_checked`, `persist_selected` and
`confirm_selection` functions in one Bash session. Use one operator/change session;
confirm token ownership across projects/hosts. Preserve the nonsecret operator record,
actual previous `.Config.Image`, `.Image` content ID and container ID before downtime.
Record UTC outcomes and settings revision without hashing or logging credentials.

Execute the complete **Update a published deployment** block with a verified candidate,
expected version/commit and downloaded evidence. Do not execute fragments after a failed
prerequisite. Exercise the following on the T064 acceptance host with protected records:

| Scenario | Commands / expected state |
|---|---|
| Accepted update | Complete update block: verify, pull, nonpolling `run --rm --no-deps -T --pull never ... --check-config`; inspect actual previous identity; stop/confirm; `start_checked` with 180-second wait; atomically persist and confirm. Only the healthy digest is selected. Verify actual delivery before acceptance. |
| Failed verification/pull/preflight | Complete block exits before stop/up; previous container remains running and selected env unchanged. Use isolated fake secrets for negative token cases. |
| Failed stop or discovery | Exit before candidate startup; inspect actual state. Do not infer absence from a failed Docker command. |
| Failed startup or health deadline | `start_checked` returns nonzero and explicitly stops/confirms candidate. Old bot is stopped, old selection retained; recovery is an explicit operator action. |
| SIGINT/SIGTERM / terminal loss | Signal traps attempt stop/confirmation. Execute the adjacent cleanup block after terminal loss or uncertain cleanup; no recovery until candidate absence is confirmed. SIGKILL/host loss cannot execute traps. |
| Persistence error | Healthy candidate may continue running while selection is stale; operation is incomplete. Record both identities, correct protected settings and rerun persistence/confirmation, or explicitly roll back. Never claim successful selection from health alone. |
| Explicit rollback | Set previous digest from record, run complete rollback block: stop candidate, use retained image or pull if missing, validate current settings/credential, start/wait, persist only after health, confirm and verify delivery. |
| Missing previous image | Remove only a disposable test image/fixture, then simulate unavailable pull; block exits with both pollers stopped. Retain production previous images until acceptance. |
| Incompatible previous image | Local preflight failure prevents up; authentication or health failure invokes failed-start cleanup. Report rollback failure; correct current config/credential or choose a compatible verified release. |
| Failed rollback / interrupted rollback | `start_checked` cleans failed attempt. After terminal loss execute `stop_selected "$PREVIOUS_IMAGE"` and confirm absence before retry. Persistence error remains incomplete. |
| Root-Compose migration | Execute discovery/preservation and migration blocks with actual old project/files. Protect config copies, preserve local content ID/tag, verify/preflight new service while old runs, then stop/confirm old before activation. No invented GHCR digest. |
| Migration return path | Execute complete old-project recovery block: stop/confirm new candidate, inspect retained local content ID, nonpolling preflight with current settings/credentials, no-build/no-pull startup and health. Failed recovery stops the old attempt too. Keep the recovery override for old-project operations. |

During active inspection/download/upload shutdown, measure actual application exit and
child-group cleanup against 20 seconds / 30-second deployment grace. Confirm heartbeat
and scratch removal, no overlapping pollers, invalid stale callbacks and canceled uploads.
Users resubmit after restart; no request or selection resumes, and uncertain sends are
never automatically retried. A controlled lifecycle test is not real-host timing evidence.

Record each scenario separately under **T064 / F008-UPDATE** with source/index identity,
host/tool versions, observed timing, stop/health/persistence results and limitations.
Controlled shell stubs do not pass real-host rollback, polling or migration acceptance.

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

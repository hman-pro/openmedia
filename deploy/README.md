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
covered below. At most one polling container per token is permitted.

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

## Update, rollback, and migration

Use one operator/change session. Establish that no other host, development process or
Compose project polls this token. **At most one polling container per token across
projects.** Keep the previous image locally until real delivery acceptance; do not prune
it during recovery. Shutdown cancels active requests/uploads, reaps source child groups
and removes scratch/heartbeat state within the inherited 20-second application budget
and 30-second deployment grace. Users resubmit after restart; selections do not resume,
and an uncertain send is never automatically repeated. Check the chat before resubmitting.

### Operator record and shared commands

Keep a protected, nonsecret change record outside the repository. Copy actual inspected
values and UTC outcomes into this template; use a reviewed configuration revision or
nonsecret settings diff as identity. **Do not hash/log credential contents as an identity
mechanism.** Never record tokens, full container environments or diagnostic contents.

```text
UTC / operator / host OS / architecture / Engine / Compose:
settings identity (nonsecret config revision/diff; current credential, no value/hash):
previous reference / actual container ID / .Image content ID:
candidate version / source commit / verified index reference:
candidate actual container ID / .Image content ID:
verify / pull / isolated preflight result and UTC:
previous stop result / confirmed stopped UTC:
startup UTC / 180-second health deadline / health outcome UTC:
failed-start or interruption cleanup / confirmed stopped UTC:
healthy image persistence / running-selected agreement:
rollback availability / preflight / stop / startup / health / persistence outcomes:
migration old project / absolute compose+env paths / preserved local image ID+tag:
real delivery acceptance / canceled-work observation / limitations / next action:
```

In Bash, define `dc()` from [Select, pull and preflight without polling](#select-pull-and-preflight-without-polling).
It validates digest shape and supplies the fixed project/files in a clean environment.
Define these additional functions in the same session. Each function propagates errors;
call them only as standalone commands under `set -e`, as the complete blocks below do.
Do not wrap a whole procedure in `if`, `!`, `&&` or `||`, which can disable Bash errexit
inside functions. `stop_selected` confirms project-wide absence of a running service.

```bash
stop_selected() {
  local ref=$1 running
  dc "$ref" stop --timeout 30 openmedia || return 1
  running=$(dc "$ref" ps --status running -q openmedia) || return 1
  test -z "$running" || return 1
}
start_checked() (
  set -euo pipefail
  local_ref=$1
  running=$(dc "$local_ref" ps --status running -q openmedia)
  test -z "$running"
  trap 'status=$?; trap - EXIT; if ! stop_selected "$local_ref"; then echo "Cleanup unconfirmed: stop and inspect before recovery" >&2; fi; exit "$status"' EXIT
  trap 'exit 130' INT
  trap 'exit 143' TERM
  dc "$local_ref" up --no-build --pull never --force-recreate \
    --wait --wait-timeout 180 openmedia
  container=$(dc "$local_ref" ps -q openmedia)
  test -n "$container"
  test "$(sudo docker inspect --format '{{.State.Running}}' "$container")" = true
  test "$(sudo docker inspect --format '{{.State.Health.Status}}' "$container")" = healthy
  test "$(sudo docker inspect --format '{{.Config.Image}}' "$container")" = "$local_ref"
  sudo docker inspect --format '{{.Id}} {{.Config.Image}} {{.Image}}' "$container"
  trap - EXIT INT TERM
)
persist_selected() {
  sudo python3 - "$1" <<'PY'
import os
from pathlib import Path
import re
import sys
import tempfile
image = sys.argv[1]
if not re.fullmatch(r"ghcr\.io/hman-pro/openmedia@sha256:[0-9a-fA-F]{64}", image):
    raise SystemExit("Invalid image selection")
path = Path('/opt/openmedia/deploy.env')
lines = path.read_text().splitlines(keepends=True)
indices = [i for i, line in enumerate(lines) if line.startswith('OPENMEDIA_IMAGE=')]
if len(indices) != 1:
    raise SystemExit("Expected exactly one OPENMEDIA_IMAGE setting; selection not persisted")
lines[indices[0]] = 'OPENMEDIA_IMAGE=' + image + '\n'
fd, name = tempfile.mkstemp(prefix='.deploy.env.', dir=path.parent)
try:
    with os.fdopen(fd, 'w') as output:
        os.fchmod(output.fileno(), 0o600)
        os.fchown(output.fileno(), 0, 0)
        output.writelines(lines)
        output.flush()
        os.fsync(output.fileno())
    os.replace(name, path)
finally:
    if os.path.exists(name):
        os.unlink(name)
PY
}
confirm_selection() {
  local ref=$1 selected container
  selected=$(sudo env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin docker compose \
    --project-name openmedia --env-file /opt/openmedia/deploy.env \
    --file /opt/openmedia/compose.yaml config --images) || return 1
  test "$selected" = "$ref" || return 1
  container=$(dc "$ref" ps -q openmedia) || return 1
  test -n "$container" || return 1
  test "$(sudo docker inspect --format '{{.Config.Image}}' "$container")" = "$ref" || return 1
  test "$(sudo docker inspect --format '{{.State.Health.Status}}' "$container")" = healthy || return 1
}
```

Persistence atomically replaces only the image line on the same filesystem, preserving
all other current settings and enforcing root:root 0600. A duplicate/missing image line
aborts. A persistence or final confirmation failure is an **incomplete operation**, even
if the new bot is healthy. Inspect running/selected identities, correct the protected
settings and rerun `persist_selected` and `confirm_selection` with the actually healthy
reference, or explicitly roll back. Never report success merely because `up` succeeded.

### Update a published deployment

Choose `CANDIDATE_IMAGE`, `version`, `revision` and downloaded `release-assets` as in
[Account-free verification](#account-free-verification). Use independently reviewed
identity/evidence and the current trusted verifier/policy. Replace placeholders before
running; digest validation rejects them. The complete block below aborts on any failed
prerequisite. Candidate override never edits selected settings during pull/preflight.
Record the printed previous identity before proceeding past its stop (retain this output
privately). The actual running reference must be a published digest; local images use
the migration path instead. Do not alter settings or credentials concurrently.

```bash
(
set -euo pipefail
python3 scripts/release/validate_release.py verify --directory release-assets \
  --image "$CANDIDATE_IMAGE" --version "$version" --source-revision "$revision" \
  --policy release/verification-policy.json
dc "$CANDIDATE_IMAGE" config --quiet
dc "$CANDIDATE_IMAGE" pull openmedia
dc "$CANDIDATE_IMAGE" run --rm --no-deps -T --pull never \
  openmedia python -m openmedia --check-config
current=$(dc "$CANDIDATE_IMAGE" ps --status running -q openmedia)
test -n "$current"
previous=$(sudo docker inspect --format '{{.Config.Image}}' "$current")
[[ "$previous" =~ ^ghcr\.io/hman-pro/openmedia@sha256:[0-9a-fA-F]{64}$ ]]
test "$(sudo docker inspect --format '{{.State.Running}}' "$current")" = true
sudo docker image inspect "$previous" --format '{{.Id}}'
date -u +%FT%TZ
sudo docker inspect --format 'previous: {{.Id}} {{.Config.Image}} {{.Image}}' "$current"
stop_selected "$previous"
test "$(sudo docker inspect --format '{{.State.Running}}' "$current")" = false
start_checked "$CANDIDATE_IMAGE"
# From here, a persistence failure leaves a healthy but incompletely selected candidate.
persist_selected "$CANDIDATE_IMAGE"
confirm_selection "$CANDIDATE_IMAGE"
printf '%s\n' 'Healthy selection persisted; perform real delivery acceptance and complete record.'
)
```

State progression is `running(previous) -> candidate_downloaded -> candidate_validated
-> previous_recorded -> previous_stopped -> candidate_starting -> candidate_healthy
-> selection_persisted`. Verify/pull/preflight failure leaves the old bot and selection
unchanged. Stop failure prevents startup. Failed/timed-out/interrupted startup goes to
`candidate_stopped -> rollback_available` only after cleanup is confirmed. No automatic
rollback occurs; a later upstream outage also does not cause automatic rollback/restart.

Keep this cleanup block next to startup. After terminal loss, uncertain interruption or
failed cleanup, run it successfully before **any** recovery startup; examine the service
list and record the stop result. If Docker is unavailable, recovery is blocked until
absence of the candidate can be established. SIGKILL/host loss cannot run shell traps.

```bash
(
set -euo pipefail
stop_selected "$CANDIDATE_IMAGE"
dc "$CANDIDATE_IMAGE" ps -a openmedia
)
```

### Explicit rollback

Set `PREVIOUS_IMAGE` to the literal reference from the protected update record, never
from a potentially stale env file. Use its previously verified evidence. Rollback uses
**current settings and current credentials**; it does not resurrect old settings or a
revoked token. Confirm candidate stop before validation or startup. Inspect local image
availability first, pulling only if absent. If missing remotely, incompatible with current
settings/token, or unable to reach health, abort and leave the failed attempt stopped.
Repair current configuration or select another verified compatible release deliberately.

```bash
(
set -euo pipefail
[[ "$PREVIOUS_IMAGE" =~ ^ghcr\.io/hman-pro/openmedia@sha256:[0-9a-fA-F]{64}$ ]]
stop_selected "$CANDIDATE_IMAGE"
if ! sudo docker image inspect "$PREVIOUS_IMAGE" --format '{{.Id}}'; then
  dc "$PREVIOUS_IMAGE" pull openmedia
fi
dc "$PREVIOUS_IMAGE" config --quiet
dc "$PREVIOUS_IMAGE" run --rm --no-deps -T --pull never \
  openmedia python -m openmedia --check-config
start_checked "$PREVIOUS_IMAGE"
persist_selected "$PREVIOUS_IMAGE"
confirm_selection "$PREVIOUS_IMAGE"
printf '%s\n' 'Previous release healthy and selected; record real delivery recovery.'
)
```

Recovery transitions are `rollback_available -> previous_validated -> previous_starting
-> previous_healthy`, then restored selection persistence. Failed validation leaves service
stopped; failed health invokes `start_checked` cleanup, including signals, and is a
reported rollback failure. Use `stop_selected "$PREVIOUS_IMAGE"` after terminal loss
in rollback before any further attempt. A persistence failure remains incomplete.

### Migrate from root Compose and return to it

This uses the existing root `compose.yaml`; it neither changes nor merges the separate
`007-local-server-deploy` branch. Inventory actual containers/project labels first:

```bash
sudo docker ps --format '{{.ID}} {{.Names}} {{.Label "com.docker.compose.project"}} {{.Label "com.docker.compose.service"}}'
```

Record the actual old project, absolute root Compose and env paths, and configuration
revision. Preserve protected copies of those files and any credential files under a
root-only backup directory chosen by the operator; treat direct-token `.env` as a secret.
Do not print or put it in the nonsecret update record. Keep the original files protected
and unchanged throughout migration; require another backup of any deliberate settings
change. Recovery uses their **current** valid credentials/settings, not restored revoked
credentials. Set the variables below to the actual paths/project; `OLD_PROJECT` must
differ from `openmedia`. The old project wrapper clears inherited environment overrides.

```bash
OLD_PROJECT=REPLACE_ACTUAL_PROJECT
OLD_COMPOSE=/absolute/path/to/compose.yaml
OLD_ENV=/absolute/path/to/.env
old_dc() {
  sudo env -i PATH=/usr/sbin:/usr/bin:/sbin:/bin docker compose \
    --project-name "$OLD_PROJECT" --env-file "$OLD_ENV" --file "$OLD_COMPOSE" "$@"
}
```

Run this discovery/preservation block in the same Bash session. If any command fails,
stop; do not run the activation block. Save the actual printed `OLD_CONTENT` and
`OLD_PIN` in the protected record for a later session. The local tag retains the old
content even when the original local tag changes. No registry digest is fabricated.
The override is a protected host-only file, not a repository edit.

```bash
set -euo pipefail
test "$OLD_PROJECT" != openmedia
[[ "$OLD_COMPOSE" = /* && "$OLD_ENV" = /* ]]
old_container=$(old_dc ps --status running -q openmedia)
test -n "$old_container"
# This directory contains credentials: protect it and include it only in encrypted backups.
sudo install -d --mode=0700 --owner=root --group=root /opt/openmedia/migration
sudo install --mode=0600 --owner=root --group=root "$OLD_COMPOSE" /opt/openmedia/migration/old-compose.yaml
sudo install --mode=0600 --owner=root --group=root "$OLD_ENV" /opt/openmedia/migration/old.env
OLD_CONTENT=$(sudo docker inspect --format '{{.Image}}' "$old_container")
[[ "$OLD_CONTENT" =~ ^sha256:[0-9a-f]{64}$ ]]
OLD_PIN="openmedia-recovery:${OLD_CONTENT#sha256:}"
sudo docker image tag "$OLD_CONTENT" "$OLD_PIN"
sudo docker image inspect "$OLD_PIN" --format '{{.Id}}'
printf 'old project=%s container=%s content=%s recovery=%s\n' \
  "$OLD_PROJECT" "$old_container" "$OLD_CONTENT" "$OLD_PIN"
sudo install -d --mode=0700 --owner=root --group=root /opt/openmedia/migration
printf 'services:\n  openmedia:\n    image: %s\n' "$OLD_PIN" | \
  sudo tee /opt/openmedia/migration/recovery.yaml >/dev/null
sudo chmod 0600 /opt/openmedia/migration/recovery.yaml
old_recovery() {
  old_dc --file /opt/openmedia/migration/recovery.yaml "$@"
}
test "$(old_recovery config --images)" = "$OLD_PIN"
```

Before stopping the old poller, complete verification, pull and isolated preflight for
the new service. If these fail, the old project continues running. New project discovery
must succeed and show no running poller. Retain the old configuration and pinned image.

```bash
(
set -euo pipefail
python3 scripts/release/validate_release.py verify --directory release-assets \
  --image "$CANDIDATE_IMAGE" --version "$version" --source-revision "$revision" \
  --policy release/verification-policy.json
dc "$CANDIDATE_IMAGE" config --quiet
dc "$CANDIDATE_IMAGE" pull openmedia
dc "$CANDIDATE_IMAGE" run --rm --no-deps -T --pull never \
  openmedia python -m openmedia --check-config
running=$(dc "$CANDIDATE_IMAGE" ps --status running -q openmedia)
test -z "$running"
test "$(sudo docker inspect --format '{{.State.Running}}' "$old_container")" = true
old_dc stop --timeout 30 openmedia
test "$(sudo docker inspect --format '{{.State.Running}}' "$old_container")" = false
old_running=$(old_dc ps --status running -q openmedia)
test -z "$old_running"
start_checked "$CANDIDATE_IMAGE"
persist_selected "$CANDIDATE_IMAGE"
confirm_selection "$CANDIDATE_IMAGE"
printf '%s\n' 'Migration selection persisted; verify real delivery before acceptance.'
)
```

If migration fails after old stop, or the operator chooses to return, first stop/confirm
the new candidate. Then use preserved **local content**, current old-project settings and
current credentials. Missing local content or incompatible settings blocks recovery;
never substitute a freshly built image or an assumed registry digest. The override and
`--no-build --pull never` prevent accidental rebuild/pull. After interruption, run
`old_recovery stop --timeout 30 openmedia`, confirm no running old service, and also
confirm the new candidate stopped before retrying. Keep using the recovery override for
future old-project operations until deliberately reconciling its image configuration.

```bash
(
set -euo pipefail
stop_selected "$CANDIDATE_IMAGE"
test "$(sudo docker image inspect "$OLD_PIN" --format '{{.Id}}')" = "$OLD_CONTENT"
test "$(old_recovery config --images)" = "$OLD_PIN"
old_recovery run --rm --no-deps -T --pull never openmedia python -m openmedia --check-config
old_recovery stop --timeout 30 openmedia
running=$(old_recovery ps --status running -q openmedia)
test -z "$running"
cleanup_old() {
  old_recovery stop --timeout 30 openmedia || return 1
  local running
  running=$(old_recovery ps --status running -q openmedia) || return 1
  test -z "$running"
}
trap 'status=$?; trap - EXIT; if ! cleanup_old; then echo "Old-project cleanup unconfirmed; inspect before recovery" >&2; fi; exit "$status"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
old_recovery up --no-build --pull never --force-recreate --wait --wait-timeout 180 openmedia
restored=$(old_recovery ps -q openmedia)
test -n "$restored"
test "$(sudo docker inspect --format '{{.Image}}' "$restored")" = "$OLD_CONTENT"
test "$(sudo docker inspect --format '{{.State.Health.Status}}' "$restored")" = healthy
trap - EXIT INT TERM
printf '%s\n' 'Old project recovered from pinned local content; verify delivery and record return.'
)
```

On return, the published project stays stopped; its selected env is retained for a future
deliberate migration and does not describe the old project's local image. Record this
explicitly. Real update/rollback/migration timing, active-work cleanup and actual Telegram
recovery remain **T064**, separate from controlled shell/lifecycle checks.

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

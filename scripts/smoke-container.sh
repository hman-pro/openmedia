#!/usr/bin/env bash
# Native, offline production-restriction checks. Requires Docker and host Python 3.
set -euo pipefail
if [[ $# != 1 ]]; then echo 'usage: smoke-container.sh IMAGE' >&2; exit 2; fi
image=$1
repo=$(cd "$(dirname "$0")/.." && pwd)
fixtures=$(mktemp -d "${TMPDIR:-/tmp}/openmedia-smoke.XXXXXXXX")
name="openmedia-smoke-$$-${RANDOM}"
volume="${name}-permissions"
cleanup() { docker rm -f "$name" "${name}-fixture" >/dev/null 2>&1 || true; docker volume rm "$volume" >/dev/null 2>&1 || true; chmod -R u+rwX "$fixtures"; rm -rf "$fixtures"; }
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
chmod 755 "$fixtures"
cp "$repo/tests/fixtures/deployment/probe.py" "$fixtures/probe.py"
printf '%s\n' '123456789:offline-smoke-fake-token' > "$fixtures/valid"
printf '%s\n' 'malformed offline token' > "$fixtures/malformed"
chmod 644 "$fixtures/valid" "$fixtures/malformed" "$fixtures/probe.py"
# Docker Desktop bind sharing can hide mode-000 files as missing. Create the negative
# secret on the Linux filesystem instead; it is still opened by UID 10001 in every check.
docker volume create "$volume" >/dev/null
docker run --rm --name "${name}-fixture" --network none --read-only --user 0:0 \
    --cap-drop ALL --security-opt no-new-privileges:true \
    --mount "type=volume,source=$volume,target=/negative" "$image" python -c \
    "from pathlib import Path; p=Path('/negative/unreadable'); p.write_text('123456789:offline-unreadable-fake-token'); p.chmod(0)"
common=(--name "$name" --network none --user 10001:10001 --init --read-only
    --cap-drop ALL --security-opt no-new-privileges:true --restart unless-stopped
    --cpus 2 --memory 2g --tmpfs /tmp:rw,noexec,nosuid,size=536870912,mode=1777
    --stop-timeout 30 --log-driver json-file --log-opt max-size=10m --log-opt max-file=3
    --mount "type=volume,source=$volume,target=/negative,readonly"
    --mount "type=bind,source=$fixtures,target=/probe,readonly"
    --mount "type=bind,source=$fixtures/valid,target=/run/secrets/telegram_bot_token,readonly")
check() {
    local expected=$1 category=$2
    shift 2
    docker create "${common[@]}" "$@" "$image" python -m openmedia --check-config >/dev/null
    set +e
    docker start --attach "$name" > "$fixtures/output" 2>&1
    local attach_status=$?
    set -e
    # Docker attach status is not authoritative; inspect the actual process exit.
    local actual
    actual=$(docker inspect --format '{{.State.ExitCode}}' "$name")
    docker rm -f "$name" >/dev/null
    if [[ $actual != "$expected" ]]; then cat "$fixtures/output" >&2; echo "expected $expected, got $actual (attach $attach_status)" >&2; exit 1; fi
    if [[ -n $category ]]; then grep -F "$category" "$fixtures/output" >/dev/null; fi
    if grep -E 'offline-smoke-fake-token|offline-unreadable-fake-token|malformed offline token|/probe/|/negative/' "$fixtures/output" >/dev/null; then
        echo 'unsafe CLI output' >&2; exit 1
    fi
}
check 0 '' -e TELEGRAM_BOT_TOKEN_FILE=/run/secrets/telegram_bot_token
check 2 'unreadable file' -e TELEGRAM_BOT_TOKEN_FILE=/probe/missing
check 2 'unreadable file' -e TELEGRAM_BOT_TOKEN_FILE=/negative/unreadable
check 2 'invalid token shape' -e TELEGRAM_BOT_TOKEN_FILE=/probe/malformed
check 2 'mutually exclusive' -e TELEGRAM_BOT_TOKEN= -e TELEGRAM_BOT_TOKEN_FILE=/run/secrets/telegram_bot_token
check 2 'TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN_FILE'
docker create "${common[@]}" -e TELEGRAM_BOT_TOKEN_FILE=/run/secrets/telegram_bot_token "$image" python /probe/probe.py >/dev/null
docker inspect "$name" > "$fixtures/inspect.json"
python3 - "$fixtures/inspect.json" <<'PY'
import json, sys
c = json.load(open(sys.argv[1]))[0]
h = c['HostConfig']
assert c['Config']['User'] == '10001:10001'
assert h['NetworkMode'] == 'none' and h['Init'] and h['ReadonlyRootfs']
assert h['CapDrop'] == ['ALL'] and 'no-new-privileges:true' in h['SecurityOpt']
assert h['NanoCpus'] == 2000000000 and h['Memory'] == 2147483648
assert h['RestartPolicy']['Name'] == 'unless-stopped'
assert c['Config']['StopTimeout'] == 30
assert h['LogConfig'] == {'Type':'json-file','Config':{'max-size':'10m','max-file':'3'}}
assert all(flag in h['Tmpfs']['/tmp'].split(',') for flag in ('noexec','nosuid','size=536870912'))
assert not c['Config'].get('ExposedPorts') and not h.get('PortBindings')
assert all(not m['RW'] for m in c['Mounts'] if m['Type'] in ('bind', 'volume'))
assert {m['Destination'] for m in c['Mounts'] if m['Type'] == 'bind'} == {'/probe', '/run/secrets/telegram_bot_token'}
print('effective production restrictions: pass')
PY
docker start --attach "$name"
status=$(docker inspect --format '{{.State.ExitCode}}' "$name")
[[ $status == 0 ]]
docker image inspect --format 'smoke Docker image ID: {{.Id}}; platform: {{.Os}}/{{.Architecture}}' "$image"
echo 'offline restricted smoke: pass (synthetic health only; no polling)'

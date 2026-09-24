#!/usr/bin/env bash
# Run the bot on a development machine: preflight, sync, check config, start.
#
# The bot token comes from the OS keyring, never from a file. Store it once:
#   macOS:  security add-generic-password -s openmedia-bot-test-token -a "$USER" -w
#   Linux:  secret-tool store --label="OpenMedia test bot" service openmedia-bot-test-token
# An already-exported TELEGRAM_BOT_TOKEN takes precedence over the keyring.
# Non-secret settings are read from .env when it exists. Extra arguments are passed to the bot.
set -euo pipefail
cd "$(dirname "$0")/.."

keyring_service=openmedia-bot-test-token

for bin in uv ffmpeg ffprobe deno; do
  command -v "$bin" >/dev/null || { echo "dev.sh: missing on PATH: $bin" >&2; exit 1; }
done

env_args=()
if [[ -f .env ]]; then
  if grep -Eq '^[[:space:]]*(export[[:space:]]+)?TELEGRAM_BOT_TOKEN=[^[:space:]#]' .env; then
    echo "dev.sh: .env holds a TELEGRAM_BOT_TOKEN value; keep the token in the keyring instead" >&2
    exit 1
  fi
  env_args=(--env-file .env)
fi

if [[ -z "${TELEGRAM_BOT_TOKEN:-}" ]]; then
  case "$(uname -s)" in
    Darwin) TELEGRAM_BOT_TOKEN=$(security find-generic-password -s "$keyring_service" -w) ;;
    Linux)  TELEGRAM_BOT_TOKEN=$(secret-tool lookup service "$keyring_service") ;;
    *)      echo "dev.sh: no keyring support on $(uname -s); export TELEGRAM_BOT_TOKEN" >&2; exit 1 ;;
  esac || { echo "dev.sh: no keyring entry for $keyring_service" >&2; exit 1; }
fi
export TELEGRAM_BOT_TOKEN

# macOS /tmp is a symlink, and the bot refuses a symlinked workspace. Exported values win over
# .env in `uv run`, so only fill the default when .env does not set it either.
if [[ "$(uname -s)" == Darwin ]] && ! grep -Eqs '^[[:space:]]*(export[[:space:]]+)?OPENMEDIA_WORK_DIR=' .env; then
  export OPENMEDIA_WORK_DIR="${OPENMEDIA_WORK_DIR:-/private/tmp/openmedia}"
fi

uv sync --locked --group dev
uv run --locked ${env_args[@]+"${env_args[@]}"} python -m openmedia --check-config
exec uv run --locked ${env_args[@]+"${env_args[@]}"} python -m openmedia "$@"

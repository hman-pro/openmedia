# OpenMedia

A Telegram bot that takes one public media link, shows the native formats the source
actually offers, and delivers the selected output in the requesting private chat. Source
streams are never transcoded or re-encoded. When YouTube exposes video and audio separately,
OpenMedia can combine one explicitly selected pair with FFmpeg stream copy.

Supported routes are public, single-item YouTube videos, LinkedIn videos/images, and Instagram
videos/images. Playlists, live streams, carousels, login-required content, cookies, source
credentials, databases, queues, and persistent media storage are outside the current scope.

The service uses Python 3.13, python-telegram-bot 22.8, yt-dlp 2026.8.19, Instaloader 4.15.3,
Deno 2.9.6, and a pinned FFmpeg build. Downloads are capped at 50,000,000 bytes, with two
active work slots, one Instagram slot, 100 pending previews, and a 128 MiB per-job workspace.

## Development

```sh
uv sync --locked --group dev     # install from the lock
uv run --locked pytest tests/unit tests/contract tests/integration
```

Controlled tests disable unapproved network access. Live-source validation is deliberately
opt-in and requires a private manifest; see
[`specs/001-media-download/quickstart.md`](specs/001-media-download/quickstart.md).

## Run locally

```sh
cp .env.example .env
uv run --locked --env-file .env python -m openmedia --check-config
uv run --locked --env-file .env python -m openmedia
```

## Diagnostic log (development)

Off by default. Turn it on while tracing a problem:

```sh
export OPENMEDIA_DIAGNOSTIC_LOG=1
export OPENMEDIA_DIAGNOSTIC_LOG_DIR="$PWD/logs"   # absolute, outside OPENMEDIA_WORK_DIR
uv run --locked --env-file .env python -m openmedia
```

One JSON Lines file per UTC day is written: `logs/openmedia-YYYY-MM-DD.log`. Every stage of a
request shares one `request_id`:

```sh
f="logs/openmedia-$(date -u +%F).log"
jq -r 'select(.stage=="received") | [.ts, .request_id, .source_url] | @tsv' "$f"
grep -h <request_id> logs/openmedia-*.log | jq -c '{ts, stage, outcome, error_category}'
jq -c 'select(.level=="ERROR")' "$f"
```

The files contain submitted links and Telegram chat and user identifiers, kept for at most 14
day files and 50 MB in total. The console never shows them. The bot token, signed media URLs,
and media bytes are never written. `OPENMEDIA_DIAGNOSTIC_LOG_LEVEL` (default `DEBUG`) sets the
detail. Contract: [`specs/002-file-logging/contracts/diagnostic-log.md`](specs/002-file-logging/contracts/diagnostic-log.md).

## Container

```sh
docker build --tag openmedia:local .
docker run --rm --env-file .env \
  --read-only --cpus=2 --memory=2g \
  --tmpfs /tmp:rw,noexec,nosuid,size=536870912,mode=1777 \
  openmedia:local python -m openmedia --check-config
```

The image runs as UID/GID 10001, exposes no ports, bundles EJS/Deno/FFmpeg, and performs no
runtime executable downloads. Deployment, live-source, real Telegram, and timing checks remain
separate release gates. With the diagnostic flag on, add a volume, because the image filesystem
is read-only: `-e OPENMEDIA_DIAGNOSTIC_LOG=1 -v openmedia-logs:/var/log/openmedia`. Current evidence is recorded in
[`specs/001-media-download/validation.md`](specs/001-media-download/validation.md).

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
separate release gates; current evidence is recorded in
[`specs/001-media-download/validation.md`](specs/001-media-download/validation.md).

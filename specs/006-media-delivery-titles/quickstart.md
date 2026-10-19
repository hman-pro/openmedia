# Validation Guide: Media Delivery Titles

Use this guide to validate the implemented delivery labels. Record exact results and open
release gates in [validation.md](validation.md); these instructions do not themselves
constitute evidence that a check passed.

## Prerequisites and setup

Use Python 3.13, uv, FFmpeg/ffprobe, Deno, and the repository's controlled fixtures.
The runtime dependency `regex==2026.8.31` is pinned in `pyproject.toml` and `uv.lock`.
Labels are derived by `src/openmedia/media_titles.py` and supplied by
`src/openmedia/delivery.py` after file/identity validation and before the send retry loop.

```sh
uv sync --locked --group dev
uv run --locked pytest tests/unit/test_media_titles.py tests/contract/test_delivery_errors.py tests/integration/test_download_flow.py tests/integration/test_youtube_music_flow.py tests/integration/test_request_isolation.py tests/integration/test_refresh.py tests/integration/test_diagnostic_trace.py
uv run --locked pytest
```

All listed test paths exist. Controlled tests use fake Telegram transport and injected
clocks; do not use live requests or real sleeps.

## Acceptance matrix

| Case | Expected result |
|---|---|
| Titled supported video, silent video, audio, music, picture | Correct caption and safe filename, existing delivery method, identical bytes |
| Missing/blank/control-only/invisible-only metadata | Untitled media caption and fallback stem |
| Normalized ASCII lengths 63, 64, 65 | First two unchanged; 65 shortened to 63 plus ellipsis |
| CJK, combining accents, skin tones, flags, ZWJ emoji near limit | At most 64 code points; no partial clusters; extension intact |
| Complete filenames at 239, 240, 241 UTF-8 bytes before shortening | First two unchanged if within stem limit; 241 shortened at whole grapheme boundary with ellipsis and extension within 240 bytes |
| 64 four-byte Unicode characters | Caption remains 64 code points; filename stem shortened to satisfy complete-filename byte cap |
| One cluster exceeds available code-point or byte budget | Ellipsis only on the affected caption or stem; filename retains selected extension |
| Slashes, traversal, reserved names, invalid characters | Safe single filename; literal caption preserves permitted visible text |
| Same title with different selected extensions | Correct selected extension on each delivered file |
| Two concurrent distinct titles | No metadata leakage between requests |
| Expired URL refresh and RetryAfter | Original title/fallback retained, retry labels identical |
| Ambiguous upload, blocked bot, timeout, oversized file | Existing result and send-count policy retained |
| Existing preview cards, including music | Existing 200-character title limit and `Untitled video` fallback, contents, choices, and status unchanged |

Use the fake transport to assert caption, filename, explicit parsing settings, file bytes,
send counts, and video hints. Check disabled/default diagnostics do not gain title output.

## Packaging and deployment

```sh
uv build
docker build --tag openmedia:local .
docker run --rm --entrypoint python openmedia:local -c 'import regex; import openmedia.media_titles'
uv run --locked --env-file .env python -m openmedia --check-config
docker run --rm --env-file .env \
  --read-only --cpus=2 --memory=2g \
  --tmpfs /tmp:rw,noexec,nosuid,size=536870912,mode=1777 \
  openmedia:local python -m openmedia --check-config
```

The image installs locked runtime dependencies via `uv sync --locked --no-dev`. Verify
the installed regex version and required license notices in the wheel, source distribution,
and image against [THIRD_PARTY_NOTICES.md](../../THIRD_PARTY_NOTICES.md).

`--check-config` validates settings and the bundled runtime without connecting to Telegram.
It does not establish successful polling startup or health. Container build/import,
configured startup, and health remain separate release checks: perform the
[README container procedure](../../README.md#container) with runtime-supplied settings and
bounded temporary storage, then verify `python -m openmedia --healthcheck` inside the
running container. Polling startup contacts Telegram; do it only when separately authorized.
Do not put a token in command arguments or committed files. Record unavailable Docker,
credentials, authorization, startup, or health checks as unverified; keep the release gate
open until all required checks pass. A local build or configuration check alone does not
establish container readiness.

## Optional real Telegram check

Do not send real Telegram messages unless separately and explicitly authorized; this
guide and its task list are not authorization. Once authorized, use a configured
development bot to submit one public titled video and
one YouTube Music track, inspect the media caption and saved filename, and confirm
native bytes and current playback behavior. Check a long/Unicode title where available.
Real-source checks remain opt-in and separate from controlled tests; record client and
outcome without credentials. See [contract](contracts/telegram-bot.md) for exact expectations.

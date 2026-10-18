# Validation Guide: Media Delivery Titles

This guide applies after implementation. No runtime behavior was changed during planning.

## Prerequisites and setup

Use Python 3.13, uv, FFmpeg/ffprobe, Deno, and the repository's controlled fixtures.
Implementation must add regex==2026.8.31 and update uv.lock together before these checks.

```sh
uv sync --locked --group dev
uv run --locked pytest tests/unit/test_media_titles.py tests/contract/test_delivery_errors.py tests/integration/test_download_flow.py tests/integration/test_youtube_music_flow.py tests/integration/test_request_isolation.py tests/integration/test_refresh.py
uv run --locked pytest
```

The new unit test path will exist after implementation. Controlled tests use fake
Telegram transport and injected clocks; do not use live requests or real sleeps.

## Acceptance matrix

| Case | Expected result |
|---|---|
| Titled supported video, silent video, audio, music, picture | Correct caption and safe filename, existing delivery method, identical bytes |
| Missing/blank/control-only metadata | Untitled media caption and fallback stem |
| Normalized ASCII lengths 63, 64, 65 | First two unchanged; 65 shortened to 63 plus ellipsis |
| CJK, combining accents, skin tones, flags, ZWJ emoji near limit | At most 64 code points; no partial clusters; extension intact |
| Complete filenames at 239, 240, 241 UTF-8 bytes before shortening | First two unchanged if within stem limit; 241 shortened at whole grapheme boundary with ellipsis and extension within 240 bytes |
| 64 four-byte Unicode characters | Caption remains 64 code points; filename stem shortened to satisfy complete-filename byte cap |
| One cluster exceeds available code-point or byte budget | Ellipsis only as shortened title |
| Slashes, traversal, reserved names, invalid characters | Safe single filename; literal caption preserves permitted visible text |
| Same title with different selected extensions | Correct selected extension on each delivered file |
| Two concurrent distinct titles | No metadata leakage between requests |
| Expired URL refresh and RetryAfter | Original title/fallback retained, retry labels identical |
| Ambiguous upload, blocked bot, timeout, oversized file | Existing result and send-count policy retained |
| Existing preview cards | Existing title limit, contents, choices, and status unchanged |

Use the fake transport to assert caption, filename, explicit parsing settings, file bytes,
send counts, and video hints. Check disabled/default diagnostics do not gain title output.

## Packaging and deployment

```sh
uv build
docker build --tag openmedia:local .
docker run --rm --entrypoint python openmedia:local -c 'import regex; import openmedia.media_titles'
uv run --locked --env-file .env python -m openmedia --check-config
```

Also run the repository's established configured container startup smoke check with
runtime-supplied settings; do not put a token in command arguments or committed files.
Record unavailable credentials, Docker, or external smoke checks as unverified rather
than claiming release readiness. Confirm applicable third-party notices accompany distribution.

## Optional real Telegram check

With an authorized configured development bot, submit one public titled video and
one YouTube Music track, inspect the media caption and saved filename, and confirm
native bytes and current playback behavior. Check a long/Unicode title where available.
Real-source checks remain opt-in and separate from controlled tests; record client and
outcome without credentials. See [contract](contracts/telegram-bot.md) for exact expectations.

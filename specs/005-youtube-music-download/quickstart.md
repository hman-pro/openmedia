# Quickstart Validation: YouTube Music Downloads

This is the implementation validation guide. Controlled acceptance is implemented and
recorded in validation.md; live source, manual Telegram and container release checks remain
separate requirements.

## Prerequisites and setup

Use Python 3.13, uv, FFmpeg/ffprobe, and Deno as in README. Work from the repository root.
Supply Telegram credentials only through the existing .env/keyring workflow; never commit
or print them. No YouTube account, cookies, or subscription is required or permitted.

```bash
uv sync --locked --group dev
uv run --locked --env-file .env python -m openmedia --check-config
uv run --locked pytest tests/unit tests/contract tests/integration
```

The controlled suite must use sanitized fixtures, fake Telegram transport, and injected
clocks. It must not connect to a source or wait on wall-clock sleeps. See the three
[contracts](contracts/music-links.md) and [data model](data-model.md) for precise outcomes.

## Controlled acceptance matrix

| Scenario | Expected evidence |
| --- | --- |
| Public music watch, several audio versions | One best eligible native document, zero taps, no keyboard |
| Same track with list/si/index/radio/t context | Same whole item, no other item inspected |
| Extractor reports ordinary YouTube canonical URL | Music canonical URL and AUDIO survive serialization and refresh |
| Metadata/artwork missing | Existing text/card fallback; successful file still delivered |
| Several known/unknown sizes and ties | Prefer eligible native AAC/M4A/MP4; existing 003 ranking within each group, native fallback if none eligible |
| Video-only or absent native audio | no_native_audio; no video or conversion |
| All audio oversized, video fits | too_large; no video fallback |
| Unknown-size download exceeds cap | Stopped, no send, existing cleanup and explanation |
| Album/playlist-only or invalid/repeated ID | No download, correct single-track or unsupported guidance |
| Private/removed, live, rate-limited, deadline, source change | Appropriate category and actionable explanation |
| Duplicate submission/callback, busy and concurrent users | Existing isolation; no duplicate delivery or hidden queue |
| Failure or shutdown during checking/download/send | Owned files cleaned under existing bounded policy |
| Music failure and refused input with diagnostics on/off | Existing privacy and trace rules |
| Ordinary YouTube, LinkedIn, Instagram | Existing media choices and workflows unchanged |

Compare delivered bytes with fixture source bytes, not only file extensions or reported
media types. Assert that conversion, merge, and tag-writing paths are never invoked for music.
Record commands and outcomes in this feature's validation.md during implementation.

## Opt-in real-source checks

Extend `tests/fixtures/live-sources.example.json` during implementation with `youtube-music`
and `youtube-music-context` cases (`platform=youtube`, `media_type=audio`, expected identity
of the public track). Update the live suite to assert AUDIO metadata and music canonical URL,
choose the audio-only option, and retain exact source-format verification. Copy the manifest
outside version control and replace placeholders with credential-free public examples.

```bash
export OPENMEDIA_LIVE_MANIFEST=/absolute/path/to/live-sources.json
uv run --locked pytest -m live tests/live/test_sources.py
```

Record time, region, pinned versions, per-case identity/format/bytes, and actual failures.
A skip, restriction, or source outage is a limitation, not a pass. URL matching and fixture
success do not prove anonymous live download availability.

## Manual Telegram check

Run `scripts/dev.sh`. In a private chat, share one public music track, then the same track
with playlist context, a collection-only link, and an ordinary YouTube video link. Verify
music sends a document automatically with card progress, context does not download more
tracks, collection-only gives guidance, and the ordinary link retains video choices.
Download the received document and compare its bytes against the same selected native
source sample where available. Observe failure and retry wording without exposing secrets.

## Container and release gate

```bash
docker build --tag openmedia:local .
```

Perform the existing README container startup/health smoke check with runtime-only token
injection and bounded temporary storage. Verify startup requires no executable downloads.
Record build/startup and live/manual results before claiming deployment readiness. No
container configuration change is planned; a successful build alone does not prove delivery.

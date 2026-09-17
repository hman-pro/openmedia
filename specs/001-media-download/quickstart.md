# Quickstart and Validation: Media Download Workflow

These commands are the acceptance guide for the implemented service. Controlled tests and the
container build are runnable from the repository; live-source and Telegram checks require the
private inputs described below and are never treated as passing when those inputs are absent.

## Prerequisites

- Python 3.13 and uv. The current validated local environment uses Python 3.13.15 and uv
  0.12.15; local YouTube checks require Deno 2.9.6 and FFmpeg/ffprobe.
- Docker for the Linux container build and startup checks.
- A dedicated Telegram bot token from BotFather and two test Telegram accounts for manual
  isolation checks. Use a separate token from any running bot deployment.
- Credential-free, publicly accessible single-media examples for all five source categories.
  Use small media you are permitted to download; record the source conditions and sizes.

Run commands from the repository root. Source contract: [contracts/source-adapters.md](contracts/source-adapters.md).
Configuration and lifecycle: [contracts/runtime.md](contracts/runtime.md).

## Install and run controlled validation

The committed `uv.lock` is authoritative. Consumers and validation use it rather than
resolving new versions:

```sh
uv sync --locked --group dev
uv run --locked pytest tests/unit tests/contract tests/integration
```

Expected: tests pass without source credentials, a Telegram token, or outbound network access.
Mock Telegram and source HTTP boundaries; use an explicit loopback allowance only inside
controlled test transports. Production destination guards must remain enabled by default.

The suite must prove:

Preview thumbnails are optional separate photo messages; the complete format descriptions
and keyboard always live in a text message. This keeps all eight labels readable and paging
consistent. Runtime structured events include acknowledgment/preview elapsed time, delivery
time since selection, outcomes, and sanitized upstream error classes for the timing audit.

| Scenario | Required result |
|---|---|
| Valid link, no selection | Metadata/options only; no primary media download |
| Selected format | Exact native file delivered to originating chat; one output |
| Public access | First-time and returning users accepted without registration |
| Metadata absent | Missing title/creator/thumbnail does not block valid media |
| Single/multiple formats | Explicit selection required for both |
| Two users/repeated callbacks | Correct ownership; no duplicate work |
| Replacement/busy/expiry | Atomic state transitions from data model |
| Large/chunked/unknown size | Actual byte cap enforced; clear reason and cleanup |
| Timeout/blocked bot/uncertain send | Terminal outcome; no automatic duplicate upload |
| Process timeout/restart | Child group reaped; no continued writes; stale options rejected |
| LinkedIn attachment parser | Real image selected; avatar/preview/multi-image not misidentified |
| Unsafe URL/redirect/path | Private destination and path traversal blocked in every transport |
| Temporary files and credentials | Cleanup deadlines met; token absent from worker environment and logs |

## Local bot run

```sh
cp .env.example .env
```

Edit `.env` locally with the test token and documented configuration; do not commit it.

```sh
uv run --locked --env-file .env python -m openmedia --check-config
uv run --locked --env-file .env python -m openmedia
```

Expected: redacted startup diagnostics and polling readiness. Send a supported link directly
to the bot, review metadata, select a native format, and receive a file attachment. Check that
an image is sent as a document so its native bytes are preserved. The no-selection check must
show no primary media file in the work directory.

`--healthcheck` is for the running container. It reads the parent-written health snapshot and
does not contact Telegram or start a second poller. It passes only when both the 15-second
heartbeat and the last successful long-poll response are younger than 90 seconds.

## Source integration checks

Implementation provides `tests/fixtures/live-sources.example.json` with entries containing
`case_id`, `platform`, `media_type`, `url`, and expected identity/type. Copy it outside version
control and fill real examples; do not include signed URLs, private posts, or cookies.

```sh
OPENMEDIA_LIVE_MANIFEST=/tmp/openmedia-live-sources.json uv run --locked pytest tests/live -m live
```

This opt-in suite inspects each source first, then explicitly selects an eligible small native
option for download and removes it. It does not send Telegram messages. Missing manifest means
skip with a reason, not success. A required media category with no passing example blocks the
release matrix even if all mocked tests pass. Run from the intended deployment network too.

| Required category | Check |
|---|---|
| YouTube video | Native video; native audio if offered; absence of converted options |
| LinkedIn video | Correct post identity and chosen video file |
| LinkedIn image | One explicit attachment; exclude article previews |
| Instagram video | One video/reel; no carousel flattening |
| Instagram image | Original source image format; no photo recompression |

Record dependency/image versions, time, network location, source identity, media type/format,
size, and result. A rate-limited/login-required example records that limitation; it does not
prove the whole platform works. Resolve failures before claiming FR-002/SC-001 are complete.

## Container build and startup

```sh
docker build --tag openmedia:local .
docker run --rm --env-file .env --tmpfs /tmp:rw,noexec,nosuid,size=536870912,mode=1777 openmedia:local python -m openmedia --check-config
docker run --detach --name openmedia-validation --init --restart=no --env-file .env --read-only --cpus=2 --memory=2g --tmpfs /tmp:rw,noexec,nosuid,size=536870912,mode=1777 --stop-timeout=30 openmedia:local
docker exec openmedia-validation python -m openmedia --healthcheck
```

Wait for startup readiness before the healthcheck; no ports are exposed. Dockerfile must
install `/app/.venv` on the read-only image and put its executables on PATH. Deno's executable
and EJS are bundled in the image; scratch/cache writes use `/tmp` and need no executable mount.
Stop the local development poller before running the container with the same token.

The pinned image toolchain is CPython 3.13.15, uv 0.12.15, Deno 2.9.6, and Debian FFmpeg
`7:5.1.9-0+deb12u1`. The FFmpeg build enables GPL components; distribution obligations and
the locked Python closure are recorded in `THIRD_PARTY_NOTICES.md`.

Manually run the Telegram happy path and two-user scenarios against the container. Then:

```sh
docker stop --time 30 openmedia-validation
docker rm openmedia-validation
```

Expected: clean termination within 20s, no surviving workers, no credentials in logs, no
persistent media after removal. Test startup cleanup using controlled stale files in an
integration test; tmpfs alone disappearing on removal does not prove in-process cleanup.

## Acceptance timing and completion

For SC-002, run 20 eligible inspections at concurrency no greater than two (one for Instagram)
and record time from link submission to acknowledgment and preview. At least 19 must meet
2s and 30s respectively. For SC-003, explicitly select 20 eligible files of at most 20 MB;
at least 19 must arrive within 2 minutes. Record source/messaging availability so external
outages are distinguished from performance failures, not silently discarded.

**Exclusion rule (fixed before the run)**: a sample may be excluded only when its request log
records a source HTTP 429 or 5xx, a Telegram `retry_after` or 5xx, or a connection failure to
either service. Delays from OpenMedia's own limiter or capacity are never excluded. Replace
each excluded sample with a new request. More than 5 exclusions in a run makes it inconclusive:
repeat it later; it does not pass. Record every exclusion with its logged cause.

The request log is one JSON object per line, keyed by `request_id`. `acknowledgment` and
`preview` records carry `elapsed_seconds` from link submission; the `delivery` record carries
`selected_elapsed_seconds` from the accepted selection. Every request ends with one `terminal`
record whose `external_causes` lists the excusable causes seen for that request (`429`, `5xx`,
`connection_failure`, `retry_after`). An empty list means the sample counts, however slow it was.

Use accelerated clocks for the 900s preview expiry and cleanup tests, and at least one real
subprocess test to verify timeout kills the worker rather than just stopping its awaiter.
Use independent accounts for SC-005. Complete SC-006 with one link and one first-page format
selection. Review all 16 functional requirements against the contracts and record results.
Record results in `validation.md`. Controlled test success cannot replace the live compatibility,
real Telegram, clean container shutdown, or timing gates.

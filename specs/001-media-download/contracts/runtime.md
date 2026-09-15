# Runtime and Deployment Contract

## Deployment shape

One Linux container runs one polling bot parent and at most two source workers. Run as
UID/GID 10001 with `--init`, a read-only image filesystem, and a writable temporary mount.
No inbound ports, database, queue, or persistent media volume are needed. Bundle Python,
the locked package environment, Deno, and EJS. The image must not download executable
components at startup. Deno runs only the bundled challenge helper with its restricted
permissions. No FFmpeg dependency is planned.

## Configuration

| Variable | Default | Validation/meaning |
|---|---|---|
| TELEGRAM_BOT_TOKEN | Required | Runtime secret; never logged or passed to source workers |
| OPENMEDIA_WORK_DIR | `/tmp/openmedia` | Owned directory on bounded writable filesystem |
| OPENMEDIA_MAX_FILE_BYTES | `50000000` | Positive; cannot exceed the validated hosted API ceiling |
| OPENMEDIA_MAX_WORKERS | `2` | Positive; shared across inspection and download-through-delivery |
| OPENMEDIA_MAX_PENDING | `100` | Positive; preview capacity reserved when admitting inspection |
| OPENMEDIA_WORKSPACE_BYTES | `134217728` | Per-job ceiling; must exceed maximum output size |
| OPENMEDIA_LOG_LEVEL | `INFO` | Reject invalid levels; upstream transport debug logs remain disabled |

Fixed acceptance values: inspection 60s, selection expiry 900s, processing 600s, cleanup 900s.
Changing them requires a spec update, rather than undocumented environment overrides.
Reserve the final five seconds of each inspection/processing deadline for cancellation
and reaping so shutdown work does not extend the specified request deadline.
Operational defaults: Instagram concurrency 1; polling handler concurrency 8; Telegram pool
16 plus polling; terminal TTL 900s with 1,000-record maximum; sweeper every 60s. Honor source
retry-after without exceeding deadlines. Maintain parent-owned source rate counters between
workers; counters expire when their applicable rate window ends. Unsupported rate-window
information uses a bounded cooldown rather than aggressive retry.

Telegram output uses a local per-chat limiter of one ordinary message/edit per second and
an overall cap of 20 ordinary sends/edits per second. Callback acknowledgments are handled
promptly through their separate method. Source progress is coalesced into stage messages,
not relayed once per downloaded fragment. Saturation and upstream 429 are measured; timing
criteria apply within documented service capacity, not during external throttling.

## Files, lifecycle, and health

Use the temporary mount for downloads, worker scratch data, and a nonsecret heartbeat file.
Initially allocate 512 MiB tmpfs, 2 GiB container RAM, and 2 CPUs; tmpfs consumes that memory
budget. The image startup checks configuration, Deno/EJS availability, work-directory
writability, stale-file cleanup, and token usability before reporting readiness.

CLI contracts to implement:

- `python -m openmedia --check-config`: validate local settings/runtime without networking;
  return 0 on success, nonzero with a redacted reason otherwise. No token value is printed.
- `python -m openmedia`: start polling; only one instance may use the token. Drop pending
  Telegram updates at startup, matching the spec's no-resume behavior.
- `python -m openmedia --healthcheck`: check a parent-written heartbeat is younger than
  90s and polling had a successful response within 90s; do not create another poller or
  contact Telegram from the healthcheck. Return nonzero if stale.

Update the heartbeat every 15s only after startup has completed; include last successful
poll time. A startup grace period of 120s precedes Docker health failures. Temporary upstream
outages may mark health degraded; an unhealthy flag alone must not cause an application
restart loop. Exit nonzero on unrecoverable startup failures.

SIGTERM stops new admission, cancels tasks, terminates worker process groups, closes uploads,
and removes scratch files. Escalate unresponsive workers to kill after 5s and exit within
20s; deployment gives 30s stop grace. Cleanup failure is logged and retried by the next sweep
or startup. Process restart discards requests and invalidates old callbacks. Lost/uncertain
uploads are never automatically repeated.

## Build and notices

Implementation commits `uv.lock` and exact image/tool version or digest pins. Runtime builds
use locked dependencies and retain third-party notices; dev tools are excluded from the
runtime layer. `.env`, local media, `.git`, credentials, and test fixture artifacts are
excluded by `.dockerignore`. Log rotation is configured by the container runtime.

The build/startup smoke test and live source matrix are required before claiming deployment
readiness. This contract specifies the future image; planning does not build or deploy it.

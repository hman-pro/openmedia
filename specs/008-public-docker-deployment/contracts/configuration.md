# Configuration Contract

Extends [feature 001 runtime](../../001-media-download/contracts/runtime.md) and retains
[feature 002 diagnostics](../../002-file-logging/contracts/diagnostic-log.md). The existing
runtime contract is amended during implementation to reference this mutually exclusive
token interface. Other settings and fixed deadlines keep their current meaning.

## Token sources

| Input | Behavior |
|---|---|
| `TELEGRAM_BOT_TOKEN` only | Existing runtime environment token, with existing validation retained |
| `TELEGRAM_BOT_TOKEN_FILE` only | Absolute file path, loaded once for each process's settings initialization |
| Both keys present | Configuration error before reading either input, including empty values |
| Neither present | Configuration error identifying the two supported alternatives |

`Settings.from_env(mapping)` remains injectable for controlled tests. It resolves the
token before constructing the existing `Settings` object; the token remains in
`telegram_bot_token`, excluded from repr. There is no new printable field containing
the token, secret content, or path. Existing callers constructing Settings directly
remain compatible. Neither token input nor loaded token is added to worker payloads
or their minimal environment.

### New file input validation

1. Path value is nonempty, absolute, and NUL-free. Do not expand shell expressions,
   interpolate credentials, or search fallback locations.
2. Open read-only and nonblocking on supported Linux/POSIX hosts, inspect the opened
   descriptor, and require a regular file. This prevents FIFOs/devices from blocking
   preflight. Read at most 4,097 bytes; reject more than 4,096 bytes. Always close.
3. Decode as ASCII. Allow one optional terminal LF or CRLF, removed once. Do not
   otherwise strip or normalize content. Reject BOM, blank content, extra lines,
   embedded whitespace/control characters, or a second trailing newline.
4. Require the resulting token to match `[0-9]+:[A-Za-z0-9_-]+` over the whole value.
   Do not hard-code current Telegram token lengths. This is local shape validation,
   not proof that Telegram accepts the credential.

The legacy direct input keeps its current nonblank/NUL/line-break checks; this feature
does not retroactively tighten it to the new file grammar. Both sources still undergo
normal Telegram authentication only when polling startup is explicitly requested.

### Errors and confidentiality

Return configuration exit code 2 through the existing CLI. Fixed messages identify
`TELEGRAM_BOT_TOKEN_FILE` and one of: invalid path, unreadable file, nonregular file,
oversized file, empty content, invalid encoding, or invalid token shape. Conflict errors
name both setting keys. Do not print the path, file contents, token fragments, or raw
OS/decoding/validation exceptions. Suppress exception chaining for secret-read/parse
failures so formatted tracebacks remain safe even before logging is configured.

Tests inspect stdout/stderr, str/repr, formatted traceback, ordinary console output,
and enabled diagnostic output with sentinel tokens and malicious path/content text.
Unreadability is injected in unit tests and exercised as UID 10001 in container checks;
host-root chmod behavior alone is not an unreadable-file test.

## CLI behavior

| Command | Required result |
|---|---|
| `python -m openmedia --check-config` | Local settings, bundled executables/EJS, writable work and optional diagnostic storage; no network, poller, heartbeat, or deletion of another bot's workspaces; 0 valid, 2 invalid |
| `python -m openmedia` | Existing validation/startup, token authentication, drop pending updates, exactly one polling owner; readiness only after a successful poll |
| `python -m openmedia --healthcheck` | Existing local heartbeat/poll freshness check; no new poller or network; 0 healthy, 1 unhealthy, 2 invalid configuration |

The healthcheck reads settings, including the mounted secret, each time it runs.
It must not log secret contents or create diagnostic files. Keep heartbeat every
15 seconds, 90-second freshness limits, 120-second image health start period, and
existing 30-second interval/5-second timeout/3 retries. Compose's startup health wait
is bounded separately at 180 seconds; successful local preflight does not imply health.

## Published Compose interface

The deployment uses an explicit project `openmedia`, service `openmedia`, and files
under `/opt/openmedia`. `deploy.env` is used for Compose interpolation, not as an
unfiltered service `env_file`. Map allowed nonsecret runtime settings explicitly.

| Host setting | Meaning |
|---|---|
| `OPENMEDIA_IMAGE` | Required `ghcr.io/hman-pro/openmedia@sha256:` plus 64 hexadecimal digits; examples contain no floating default |
| `OPENMEDIA_TOKEN_FILE` | Absolute host file path, default `/opt/openmedia/secrets/telegram_bot_token` |
| Existing permitted `OPENMEDIA_*` limits/log settings | Explicit mappings with existing defaults/validation; no deadline overrides |

Container environment sets `TELEGRAM_BOT_TOKEN_FILE=/run/secrets/telegram_bot_token`;
it does not map `TELEGRAM_BOT_TOKEN`. The source path is a file-backed secret named
`telegram_bot_token`, targeted at that read-only mount. Do not include either token
value in `.env.example`, build arguments, image labels, Compose interpolation output,
or release assets. Use explicit absolute Compose/env paths and command-scoped candidate
image overrides; shell environment precedence is documented.

The published service has no `build`, ports, Docker socket, source credential mounts,
or persistent media volume. It retains UID/GID 10001, init, read-only root,
`cap_drop: [ALL]`, no-new-privileges, `restart: unless-stopped`, 2 CPUs, 2 GiB RAM,
512 MiB `/tmp` tmpfs with noexec/nosuid, 30-second stop grace, and json-file console
rotation at 10 MiB × 3. Work directory remains `/tmp/openmedia`.

Default diagnostics are off. An operator enabling them must explicitly provision
feature 002's writable protected log mount; no default log volume is introduced.

## Host ownership contract

The guide targets standard rootful Docker without user-namespace remapping. The host
secret is owned by `root:10001`, mode `0640`, within a root-owned protected directory
(mode `0700` is suitable). Numeric GID 10001 must not be assigned to unrelated host
users; document this check. The container reads through the mounted file as UID/GID
10001; host parent-directory traversal is performed by the privileged Docker daemon.

Compose's file-secret `uid`, `gid`, and `mode` attributes do not change host-backed
ownership. Validate actual read access under production restrictions. These secrets
do not encrypt host storage. The operator protects host access and backups. Rotating
an atomically replaced file requires service recreation as defined in
[operations.md](operations.md).

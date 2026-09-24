# OpenMedia

Telegram bot that takes one public media link, shows the native formats available, and
delivers the selected file unchanged. Python 3.13, one container, no database.

## Where truth lives

Spec-kit drives this repo. Read before writing code:

| Document | Read it when |
|---|---|
| `specs/001-media-download/tasks.md` | Always — it is the ordered work list and the progress record |
| `specs/001-media-download/plan.md` | Choosing a module, layout, or dependency |
| `specs/001-media-download/contracts/` | Implementing the Telegram, adapter, or runtime boundary |
| `specs/001-media-download/data-model.md` | Defining or changing an entity field |
| `specs/002-file-logging/tasks.md` | Working on the diagnostic log file |
| `specs/002-file-logging/contracts/diagnostic-log.md` | Touching logging, env variables, or what may be written to disk |
| `specs/003-streamlined-bot-ux/tasks.md` | Working on the card, choices, or status |
| `specs/003-streamlined-bot-ux/contracts/` | Touching what users see or which version is picked |
| `specs/004-linkedin-share-links/tasks.md` | Working on LinkedIn short links or post recognition |
| `specs/004-linkedin-share-links/contracts/` | Touching LinkedIn address recognition, short-link resolution, or refusal diagnostics |
| `.specify/memory/constitution.md` | A change adds a service, dependency, or platform |

`.specify/feature.json` holds one repo-global `feature_directory`. Switching features
rewrites it for every session in this checkout.

## Working rhythm

One branch per feature, one commit per phase.

1. Branch once: `git checkout -b 001-media-download`
2. Run `/speckit-implement` scoped to a single phase, never the whole file
3. Mark each finished task `[X]` in `tasks.md` as you go — it is the only state that
   survives a context reset, and a later run resumes from the unchecked boxes
4. Commit at the phase boundary: `feat(001): phase N <name>`

Phases are strictly sequential: Setup → Foundational → US1 → US2 → US3 → Polish.

## Constraints that code review will not catch

- **Deliver source-encoded streams, never re-encoded.** A choice is one native upstream
  file byte-for-byte, or exactly one video plus one audio stream merged by FFmpeg stream
  copy (`-c copy`) into a compatible container and labeled combined. Transcoding, scaling,
  and format conversion stay out. FFmpeg only ever reads local files.
- **YouTube uses `player_client=default,android`.** `default` supplies fetchable adaptive
  streams; `android` pins muxed format 18. `ios` is SABR-only and unusable. Change the list
  only with fresh live evidence (research §6).
- **Delivery cap is 50,000,000 bytes because Telegram's hosted Bot API caps uploads at
  50 MB.** Raising it needs a local Bot API server, which is a second service and a plan
  revision.
- **Anonymous access only.** No stored cookies, logins, or source credentials. Cookies a
  source issues to a logged-out visitor may be held in memory for one worker operation and
  discarded; they are never persisted, shared across requests, or supplied by an operator
  (`MetadataHTTP` jar, Instagram hosts only). A category that needs authentication is a
  scope decision, not an implementation detail.
- **State lives in memory.** Bounded maps and tombstones. Introducing a database, queue,
  or second service needs a plan revision first.
- **Deadlines are fixed in code**, not configurable: 60s inspect, 900s selection expiry,
  600s download-and-send, 900s cleanup.
- **Callback data carries an integer `option_id`**, never a URL, extractor expression, or
  path. Map it server-side.
- Keep the bot token out of logs, `repr`, and error text.
- **Links and Telegram identifiers are logged only through `openmedia.diagnostic`**
  (`diagnostics.event`), never through a logger that reaches the console. That logger does
  not propagate and is disabled unless `OPENMEDIA_DIAGNOSTIC_LOG=1`.

## Commands

```bash
uv sync --locked --group dev     # install from the lock
uv run pytest                    # controlled tests; network is disabled in conftest
uv run pytest -m live            # opt-in, hits real sources, run deliberately
uv run python -m openmedia --check-config
scripts/dev.sh                   # dev run: preflight, sync, check, start; token from keyring
```

Controlled tests use fixtures and a fake Telegram transport. When a test needs the
network, it belongs under `tests/live/` behind the `live` marker.

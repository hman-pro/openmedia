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

- **Deliver one native upstream format, byte-for-byte.** When yt-dlp offers video and
  audio as separate streams, mark the combined option unavailable and say why. FFmpeg,
  merging, remuxing, and transcoding stay out of this project.
- **Anonymous access only.** No stored cookies, logins, or source credentials. A category
  that needs authentication is a scope decision, not an implementation detail.
- **State lives in memory.** Bounded maps and tombstones. Introducing a database, queue,
  or second service needs a plan revision first.
- **Deadlines are fixed in code**, not configurable: 60s inspect, 900s selection expiry,
  600s download-and-send, 900s cleanup.
- **Callback data carries an integer `option_id`**, never a URL, extractor expression, or
  path. Map it server-side.
- Keep the bot token out of logs, `repr`, and error text.

## Commands

```bash
uv sync --locked --group dev     # install from the lock
uv run pytest                    # controlled tests; network is disabled in conftest
uv run pytest -m live            # opt-in, hits real sources, run deliberately
uv run python -m openmedia --check-config
```

Controlled tests use fixtures and a fake Telegram transport. When a test needs the
network, it belongs under `tests/live/` behind the `live` marker.

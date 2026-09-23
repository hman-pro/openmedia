# Validation: LinkedIn Share Links

## Baseline

- Date: 2026-09-23
- Branch: `004-linkedin-share-links` at `03ce9e9` (before any 004 code change)
- Commands: `uv sync --locked --group dev && uv run pytest`
- Result: green — 517 passed, 3 deselected (the `live` tests excluded by default), 0 failed

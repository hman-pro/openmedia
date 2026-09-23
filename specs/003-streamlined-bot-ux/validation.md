# Validation: Streamlined Bot UX

## Baseline

- Date: 2026-09-23
- Branch: `003-streamlined-bot-ux` at `69e2274` (before any 003 code change)
- Commands: `uv sync --locked --group dev && uv run pytest`
- Result: green — 357 passed, 1 deselected (the `live` test excluded by default), 0 failed

## Inline video gate (R7)

- Date: 2026-09-23
- Command: `uv run pytest -m live tests/live/test_inline_video.py -rs -rP` (real token, private chat)
- Result: 2 passed — gate open, FR-009 stands

| Clip | Returned message type | SHA-256 equal | SHA-256 |
|---|---|---|---|
| `with_sound.mp4` (H.264 + AAC, 640×360) | `video` | yes | `4ce084623333a8b9b289b87fe752bebe9a8bae90c117b5f2e92744a5fef89bbd` |
| `silent.mp4` (H.264 only, 360×640) | `video` | yes | `39fdff979f91ab4a82e8e09b95201183018bc75d9bb809c048efd697a394ff89` |

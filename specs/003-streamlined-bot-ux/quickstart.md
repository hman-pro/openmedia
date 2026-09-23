# Quickstart: Validate Streamlined Bot UX

## 1. Install and run controlled tests

```bash
uv sync --locked --group dev
uv run pytest tests/unit/test_choices.py          # policy, contracts/choice-policy.md table
uv run pytest tests/contract/test_bot_preview.py  # card text, buttons, no pagination
uv run pytest tests/contract/test_bot_callbacks.py tests/integration/test_download_flow.py
uv run pytest                                     # full controlled suite, network disabled
```

Expected: all pass. The contract tests use the fake Telegram transport and assert on the
methods called (`sendPhoto`/`editMessageText`/`editMessageCaption`/`deleteMessage`/
`sendVideo`/`sendDocument`) and on the exact text.

## 2. Scenario checks (fake transport, controlled fixtures)

| Scenario | Fixture | Expect |
|---|---|---|
| YouTube video, thumbnail | `tests/fixtures/ytdlp` YouTube info | Photo card with title + duration; 3 buttons `Video`, `Video (no sound)`, `Audio only`; checking message deleted |
| No thumbnail | same, thumbnail fetch fails | Checking message edited into the card |
| Tap `Audio only` | — | Keyboard removed; caption status `Audio only — downloading…` → `sending…` → `sent.`; `sendDocument` |
| Tap `Video` | — | `sendVideo` with `supports_streaming=True` |
| LinkedIn muxed video | `tests/fixtures/linkedin` | Card without keyboard, `Video — only version available, downloading…`, then `sendVideo` |
| Instagram picture | `tests/fixtures/instagram` image | No card, no buttons; `Picture — downloading…` → `sent.`; `sendDocument`; bytes equal fixture |
| Every video choice too large | size-inflated fixture | No keyboard; too-large meaning from 001 |
| Download fails | worker stub failure | Same status surface ends in `<Label> — downloading failed. …` |
| Old `p:` callback | crafted payload | Answered as invalid; no state change |

Message count (SC-004): after a successful run the fake chat holds exactly two bot messages.

## 3. Manual run against Telegram

```bash
uv run python -m openmedia --check-config
uv run python -m openmedia
```

In a private chat with the bot, send one link of each kind and check what you see:

1. A YouTube video → one card, three buttons, tap `Video` → the video plays inline. Send the
   link again and tap `Video (no sound)` → it plays inline and is not shown as a looping
   animation (SC-005). Do both on an iPhone and on an Android phone.
2. A LinkedIn video post → the video arrives without a tap.
3. An Instagram picture → the picture arrives as a file, with no buttons.

## 4. Live gate for inline video (research R7), run deliberately

```bash
uv run pytest -m live tests/live/test_inline_video.py
```

The test uploads a <20 MB H.264/AAC MP4 and a silent H.264 MP4 with `sendVideo`, fetches each
back with `getFile`, and compares SHA-256 with the upload. It records the returned message
type (`video` or `animation`).

- Hashes equal → FR-009 holds; record the result in `validation.md`.
- Hash differs → stop. Revise FR-009 (send video as a document) before merging User Story 1.

## 5. Diagnostic log (optional)

With `OPENMEDIA_DIAGNOSTIC_LOG=1`, one request shows `inspection_finished` with
`choices` and `selection` with `automatic`. No URL besides the `received` link, no identifiers
outside `received`.

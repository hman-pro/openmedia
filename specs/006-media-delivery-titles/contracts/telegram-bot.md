# Telegram Delivery Contract (006)

Extends the delivery surfaces in features 001, 003, and 005.

| Selected media | Existing delivery | Added labels |
|---|---|---|
| Video / silent video | send_video with existing streaming and measured hints | Plain caption and title-derived filename |
| Audio / YouTube Music | send_document | Plain caption and title-derived filename |
| Picture | send_document, unchanged bytes | Plain caption and title-derived filename |

## Title rules

- Read the original request's `metadata.title_or_caption`; absent, blank, or
  display-empty text becomes `Untitled media`.
- Apply the normalization and filename rules in [research.md](../research.md#4-normalization-and-safe-filenames).
- Caption and sanitized filename stem each have an independent 64-code-point budget.
  Exactly 64 points remain unshortened unless the filename byte budget requires
  shortening the stem. Longer captions retain the longest whole-grapheme prefix
  fitting 63 points, followed by `…`. A single oversize cluster yields `…`.
- Complete filenames MUST fit within 240 UTF-8 bytes, including ellipsis, dot, and
  selected extension. When either stem or byte limit requires shortening, reserve
  one code point and three bytes for `…` and the UTF-8 bytes of the dot/extension;
  retain the longest whole-grapheme prefix fitting both remaining budgets.
- Append dot and selected extension after shortening the filename stem. Extension is
  never inferred from source text, removed, or counted against the stem budget.
- Send literal text using explicit `parse_mode=None` and no entities; punctuation is
  not interpreted as markup. Telegram client automatic link detection is outside bot control.
- For `Summer walk` and selected `mp4`, send caption `Summer walk`, filename
  `Summer walk.mp4`. For 65 ASCII `a` characters, both title surfaces use 63 `a`
  characters plus `…`, followed by `.mp4` only in the filename.
- `A/B` displays literally as the caption and uses `A_B.<extension>` as filename.
  Missing title uses `Untitled media` and `Untitled media.<extension>`.

## Inherited behavior

Preview cards retain their own 200-character title policy and status text. No extra
message, tap, or source request is introduced. Output labels never rename disk files
or modify bytes/tags. Media ID and selected-format validation precede upload. Request-local
labels stay fixed on retries; source refresh retains original request title metadata.
All original deadline, rate-limit, upload ambiguity, failure, privacy, and cleanup rules apply.

This contract is implemented at the validated delivery boundary. Features
[001](../../001-media-download/contracts/telegram-bot.md#media-delivery-titles-amended-by-006),
[003](../../003-streamlined-bot-ux/contracts/telegram-bot.md#media-delivery-titles-amended-by-006), and
[005](../../005-youtube-music-download/contracts/telegram-bot.md#media-delivery-titles-amended-by-006)
link to these delivery-label rules. Controlled acceptance evidence and pending external
release checks are recorded in [validation.md](../validation.md#t020--requirements-reconciliation-and-external-acceptance-2026-10-19-local).

# Telegram Bot Contract (003)

Replaces the "Preview and selection" section and parts of "Download and delivery" in
`specs/001-media-download/contracts/telegram-bot.md`. Inputs, audience, callback
validation, and the conflict/failure meaning table from 001 stay in force.

## Progress surface

1. On an accepted link, send one plain message: `Checking link…`. Record it as the request's
   status message.
2. From then on the request has exactly one status surface, edited in place at each stage.
   A new message is sent only when an edit fails for a reason other than "message is not
   modified" (for example, the user deleted it).
3. Busy/admission rejections that happen before step 1 are plain replies, as in 001.

## Video card

Shown when inspection finds a video and the choice set has two or three entries.

| With thumbnail | Without thumbnail (or photo upload failed) |
|---|---|
| New photo message, card as caption, keyboard attached; then delete `Checking link…` (best effort) | Edit `Checking link…` into the card text, keyboard attached |

Card text, in order, plain text only (never parsed as markup):

1. Title, truncated to 200 characters; `Untitled video` when absent.
2. Duration as `m:ss` or `h:mm:ss`; the line is omitted when unknown.
3. At most one "unavailable" line (research R9), built from `missing`:
   `Not available: <labels>.` for kinds the source does not offer and
   `Too large to send: <labels>.` for kinds that exceed the limit. Labels follow kind order,
   joined by `, `. When both apply they share the line, for example
   `Not available: Audio only. Too large to send: Video.` No line when nothing is missing.
   No platform, creator, link, codec,
   container, resolution, bitrate, or size appears anywhere.

Keyboard: one row per kept choice, in order `Video`, `Video (no sound)`, `Audio only`. Button
text is exactly the label. No numbers, no pagination row.

## Automatic delivery

- **One video choice**: show the card without a keyboard, status
  `<Label> — only version available, downloading…`, and start downloading. No tap.
- **Picture**: no card. The `Checking link…` message becomes `Picture — downloading…`.
- **No video choice**: the status surface shows the 001 failure meaning (`too_large` or
  `no_formats`) and resubmission guidance. No keyboard.

## Callbacks

- Only `s:<32-hex-request-id>:<option_id>` is valid; `option_id` is 0–2. The `p:` page
  payload of 001 is removed and treated as malformed.
- All 001 checks still apply: exact syntax, 64-byte limit, user, chat, preview message ID,
  expiry, state, prompt answer to every callback.
- On acceptance: remove the keyboard, answer the callback with the label, and set the status
  to `<Label> — downloading…`.

## Stage text

| Stage | Status text |
|---|---|
| downloading | `<Label> — downloading…` |
| sending | `<Label> — sending…` |
| completed | `<Label> — sent.` |
| failed | `<Label> — <stage> failed. <next step from 001 table>` |
| upload unconfirmed | `<Label> — could not confirm sending. Check this chat before sending the link again.` |

On a video card the status is the last line of the caption, below the title and duration.

## Delivery method

| Choice | Telegram method | Notes |
|---|---|---|
| Video, Video (no sound) | `sendVideo`, `supports_streaming=true`, width/height/duration when known | File is MP4/H.264 (+AAC); see research R7 gate |
| Audio only | `sendDocument` | Native bytes, any adapter-accepted format |
| Picture | `sendDocument` | Never `sendPhoto`: that recompresses |

The 001 rules on ambiguous uploads, `RetryAfter` retries within the deadline, blocked bots,
and never retrying an ambiguous upload apply to both methods.

## Help text

(amended) `/start` and `/help` reply with different texts. Both are plain text (no
`parse_mode`). `/start` is one line that points to `/help`, and `/help` holds the usage steps
and limits. The 50 MB cap and the 15-minute expiry in `/help` must match
`MAX_HOSTED_FILE_BYTES` and `SELECTION_SECONDS`.

`/start`: "Send me one public YouTube, LinkedIn, or Instagram link and I'll send the file back.
Details: /help"

`/help`:

```
Send one public link and I'll send the media back unchanged.

How to use:
1. Paste one link here: a YouTube video, LinkedIn post, or Instagram post.
2. For videos, tap Video, Video (no sound), or Audio only. Pictures are sent straight away.
3. Wait for the file. Big videos can take a few minutes.

Good to know:
• Public posts only. Private, login-only, or age-restricted posts won't work.
• Files over 50 MB can't be sent (Telegram's limit).
• Choices expire after 15 minutes. Send the link again if they do.
• One link per message, in this private chat.
```

## Bot profile

(amended) At startup the bot reads its description and short description and writes each one
with `setMyDescription` / `setMyShortDescription` only when Telegram's copy differs. This runs
as a background task. A failure is logged by exception type only and never blocks polling.

Description (≤512 characters, shown in an empty chat before `/start`): "Send one public
YouTube, LinkedIn, or Instagram link and get the media file back, unchanged. Files up to
50 MB. Tap Start, then paste a link."

Short description (≤120 characters, shown on the profile and when shared): "Public YouTube,
LinkedIn, and Instagram media, sent back unchanged."

## Amendments to 001 artifacts

Applied during implementation, each marked "(amended by 003)":

1. `contracts/telegram-bot.md`: "Preview and selection" and the `p:` payload point here;
   "Download and delivery" names `sendVideo` for video choices.
2. `spec.md`: FR-004, FR-005, and FR-007 (images and single-choice videos) point to 003.
3. `data-model.md`: `options` holds the ≤3 policy-kept options; new request fields per
   003 data model.
4. `specs/002-file-logging/data-model.md`: add `choices` and `automatic` keys.

# Telegram Music Workflow Contract

Extends [003 Telegram contract](../../003-streamlined-bot-ux/contracts/telegram-bot.md).
Existing private-chat, admission, busy, deadline, replacement, and callback isolation apply.

## Successful workflow

1. A supported music track submission produces `Checking link…` under normal admission.
2. Show the existing thumbnail card with available title and duration; use the existing text
   fallback when artwork cannot be used. No format table or selection keyboard.
3. Atomically claim the highest-ranked eligible audio option, then show
   `Audio only — downloading…` (do not say “only version available” for music).
4. Reuse `Audio only — sending…` and `Audio only — sent.` as progress and completion.
5. Deliver exactly one document file in its source format; final chat contains the card and
   file, subject to existing fallback presentation. Embedded tags/artwork stay unchanged.

Automatic status selection may use metadata.media_kind=AUDIO to suppress the ordinary
single-video “only version available” wording. This is display behavior, not a new request
state. Duplicate callbacks cannot start a second download, even though no keyboard is shown.

## Refusals and failures

| Meaning/category | User message or existing behavior |
| --- | --- |
| music_collection | Only one track is supported. Send a YouTube Music track link. |
| no_native_audio | The source has no downloadable native audio-only option. Send another public track link. |
| unsupported_url | Existing supported-public-link guidance |
| unavailable | Existing anonymous-unavailable explanation without an asserted cause |
| too_large | Existing size-limit message and another-link guidance |
| rate_limited / timeout | Existing source-busy or stage-specific timeout guidance |
| format_unavailable during download | Existing selected-format-changed message; resubmit |
| delivery failed or uncertain | Existing send guidance; never resend automatically |

Pre-admission refusals use existing feature 004 diagnostic-only logging. Accepted music
failures carry request trace and category through existing diagnostic events. No source
credentials, internal exception text, or links appear in console output. Help/start and
input guidance should name YouTube Music as supported without promising playlist downloads,
MP3, inline audio playback, or authenticated access.

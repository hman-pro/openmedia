# Telegram Bot Contract

## Inputs and audience

Any Telegram user may submit one recognized public media URL in a private chat without
registration. Parse Telegram URL/text-link entities, with surrounding text permitted. Count
only entities whose host belongs to YouTube, LinkedIn, or Instagram; ignore other URLs. Reject
zero or multiple supported-platform URLs, then unsupported routes and collection/live URLs,
with a short explanation. (amended by 004) An `lnkd.in/p/<code>` link counts as a supported
LinkedIn link; see [telegram-bot.md (004)](../../004-linkedin-share-links/contracts/telegram-bot.md#accepting-a-short-link). Ignore edits to previous messages as new requests. Optional `/start` and
`/help` explain supported sources and usage; neither is a prerequisite. Groups receive only
a private-chat instruction; no extraction or source preview is performed there.

## Preview and selection

(amended by 003) This section is replaced by the video card, automatic delivery, callback,
and stage-text rules in `specs/003-streamlined-bot-ux/contracts/telegram-bot.md`, with the
choice set defined in `specs/003-streamlined-bot-ux/contracts/choice-policy.md`. The text
below records the original 001 behavior; where it conflicts with 003, 003 wins.

1. Acknowledge the accepted link with a checking state.
2. Present platform, canonical source link, and available title/caption, creator, duration,
   and thumbnail. Missing thumbnail or failed thumbnail fetch must not block the text preview.
3. Show selectable options with type, native extension, quality, audio inclusion for video,
   and known/estimated/unknown size. Explain excluded choices in text without actionable
   selection buttons. With no eligible choices, end with the reason and resubmission guidance.
4. Require explicit selection even for a single option. Source inspection may retrieve
   metadata/manifests and a separate thumbnail, but must not save the primary media file.

Show at most eight format buttons per page, ordered by video with sound, audio, silent video,
and images; within each type order by quality descending. Previous/next buttons reveal all
eligible options without changing them. One selection remains the only required action when
the desired format is on the first page. Pagination is optional navigation, not a mandatory
extra confirmation step. Use plain text and numbered short labels where necessary; metadata
is not interpreted as Telegram markup. Truncate long descriptions and split text rather than
exceeding Telegram message limits.

Callback payloads:

- `s:<32-hex-request-id>:<option-index>` selects an option.
- `p:<32-hex-request-id>:<page-index>` changes the displayed page. (amended by 003) Removed:
  a `p:` payload is now malformed, and `s:` carries an `option_id` of 0–2; see
  `specs/003-streamlined-bot-ux/contracts/telegram-bot.md` "Callbacks".

Payloads must fit 64 UTF-8 bytes and contain no URLs, file paths, format expressions, or
credentials. Validate exact syntax and bounds; verify user ID, chat ID, preview message ID,
request expiry, and current state. Answer every callback promptly, including malformed or
stale ones. A forged or foreign callback cannot inspect another user's request details.

## Download and delivery

After an accepted selection, remove the keyboard and show the selected choice and downloading
state, then sending. Upload the local file with `sendDocument` to preserve native bytes.
(amended by 003) `Video` and `Video (no sound)` choices are uploaded with `sendVideo`
(`supports_streaming=true`) so they play inline; `Audio only` and pictures stay on
`sendDocument`. See `specs/003-streamlined-bot-ux/contracts/telegram-bot.md` "Delivery method".
Do not require a media-player-compatible format or convert an image into a photo upload.
A successful returned Message confirms delivery; a separate completion notice is optional
because the delivered attachment itself completes the flow.

If the upload outcome is ambiguous, say it could not be confirmed and ask the user to check
the chat before resubmitting. Never retry that upload automatically. Definite rate-limit
rejections may be retried only within the remaining processing deadline. A blocked bot or
failed notification does not stop cleanup.

## Conflict and failure messages

| Condition | Required meaning |
|---|---|
| Invalid/multiple links | Send one supported public media link |
| Private/login-required/removed | Content cannot be opened without logging in; name the possible causes (private, removed, followers/connections only) without asserting one; send another public link |
| Multi-item/live | Only one finished media item is supported |
| No native audio | Source does not provide a downloadable audio-only option |
| Too large/no deliverable choice | File exceeds the current delivery limit; choose another available option or link |
| Request already working | Current request is processing; wait before submitting another |
| Global or Instagram capacity/cooldown | Service/source is busy; retry later; no hidden queue |
| Duplicate selection | Already processing or completed; no duplicate work |
| Expired/replaced/restarted request | Submit the link again to obtain current choices |
| Source format changed | Selected option unavailable; submit the link again |
| Deadline/resource failure | Identify checking/downloading/sending failure and a retry step |
| LinkedIn short link cannot be opened (amended by 004) | The link could not be opened; send the post's full linkedin.com address |
| LinkedIn short link leads outside a supported post (amended by 004) | The link does not lead to a supported post; send a public LinkedIn post link |

The two 004 rows are the `short_link_unresolved` and `short_link_not_post` categories; their
exact text is in [telegram-bot.md (004)](../../004-linkedin-share-links/contracts/telegram-bot.md#new-failure-meanings).

English is the initial message language. Error messages expose no internal exceptions or
credentials. Busy responses preserve any pending selection and its original expiry.

Reference: [Telegram Bot API](https://core.telegram.org/bots/api). The compact payload and
attachment behavior are based on documented Telegram constraints; presentation details are
OpenMedia design choices. See `runtime.md` for resource values and `../data-model.md` for races.

## YouTube Music extension (amended by 005)

Public music watch links request one complete native audio track, including listening
context; album/playlist-only addresses are refused with single-track guidance. Music
uses a track card and automatic document delivery without selection buttons. Native
bytes/tags remain unchanged. Error guidance distinguishes `music_collection` and
`no_native_audio` without suggesting video fallback. Existing private-chat, limits,
deadline, isolation and diagnostic rules apply. See [005 Telegram contract](../../005-youtube-music-download/contracts/telegram-bot.md).

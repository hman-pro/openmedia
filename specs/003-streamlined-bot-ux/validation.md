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

## US1

- Date: 2026-09-23
- Branch: `003-streamlined-bot-ux` on top of `f4708eb` (phase 2), phase 3 uncommitted
- Command: `uv run pytest` — green, 491 passed, 3 deselected (`live`), 0 failed
- Rows walked with the fake transport and controlled fixtures (quickstart §2):

| Scenario | Evidence (test) | Result |
|---|---|---|
| YouTube video, thumbnail | `test_bot_preview.py::test_send_card_with_thumbnail_sends_photo_then_deletes_checking`, `test_youtube_card_has_three_plain_buttons_in_kind_order`, `test_card_has_at_most_three_lines_besides_the_title_sc001` | Pass: one `sendPhoto` carrying caption (title + duration) and buttons `Video`, `Video (no sound)`, `Audio only`, then `deleteMessage` of `Checking link…`; no `sendMessage` |
| No thumbnail | `test_send_card_without_thumbnail_edits_checking_message`, `test_send_card_falls_back_to_edit_when_photo_fails` | Pass: `Checking link…` edited into the card with its keyboard; no new message |
| Tap `Video` | `test_download_flow.py::test_youtube_card_offers_three_choices_and_video_downloads_format_18`, `test_delivery_errors.py::test_video_kinds_use_send_video_with_streaming_and_known_metadata` | Pass: exactly format `18` downloaded; `sendVideo` with `supports_streaming=True` and known width/height/duration |
| LinkedIn muxed video | `test_download_flow.py::test_linkedin_progressive_single_video_is_claimed_and_sent_without_a_tap`, `test_bot_preview.py::test_automatic_choice_set_renders_card_without_keyboard` | Pass for US1 scope: card without keyboard, `publish_and_claim`, download starts without a callback, delivered on the `video` path (`sendVideo`). The kept rendition is yt-dlp format `1` (higher bitrate of two unknown-codec MP4s, R2 tie-break), not `0` as the T018 task line says; the test pins `1`. The `Video — only version available, downloading…` line on the card belongs to US3 (T032); until then progress is still sent as separate messages |
| Every video choice too large | `test_download_flow.py::test_every_video_candidate_over_the_limit_fails_as_too_large`, `test_bot_errors.py::test_all_excluded_preview_sends_exactly_one_notice_saying_nothing_fits` | Pass: no card, no keyboard, one failure notice with the 001 `too_large` meaning at stage `checking` |
| Old `p:` callback | `test_bot_callbacks.py::test_page_callback_gets_the_invalid_choice_alert_without_touching_the_registry`, `test_malformed_callbacks_are_rejected` | Pass: answered with the invalid-choice alert; registry untouched; no edit |

## US2

- Date: 2026-09-23
- Branch: `003-streamlined-bot-ux` on top of `12791dc` (phase 3), phase 4 uncommitted
- Command: `uv run pytest` — green, 494 passed, 3 deselected (`live`), 0 failed
- Row walked with the fake transport and controlled fixtures (quickstart §2):

| Scenario | Evidence (test) | Result |
|---|---|---|
| Instagram picture | `test_download_flow.py::test_single_picture_is_claimed_on_the_checking_message_and_sent_as_a_document[instagram]` (and `[linkedin]`), `test_picture_over_the_delivery_limit_fails_as_too_large` | Pass for US2 scope: preview callable never called (no card, no buttons, no `sendPhoto`); `publish_and_claim` on the `Checking link…` message ID; download starts without a callback; one `sendDocument` with `filename` `media.jpg` whose uploaded bytes equal the downloaded bytes. An image over the limit fails at `checking` with the 001 `too_large` meaning. The `Picture — downloading…` → `sent.` edits on the same message belong to US3 (T032); until then progress is still sent as separate messages |

## US3

- Date: 2026-09-23
- Branch: `003-streamlined-bot-ux` on top of `55fe424` (phase 4), phase 5 uncommitted
- Command: `uv run pytest` — green, 506 passed, 3 deselected (`live`), 0 failed
- Runs drive the real `RuntimeCallbacks` from `openmedia.__main__` over `fake_bot` (real
  `telegram.Bot`, fake transport); only the worker-backed inspect and download are stubbed.
  Bot messages = `sendMessage` + `sendPhoto` + `sendVideo` + `sendDocument` − `deleteMessage`.

| Scenario | Evidence (test in `test_download_flow.py`) | Sent | Deleted | Bot messages (SC-004) | Status edits on the one surface |
|---|---|---|---|---|---|
| Tapped video, thumbnail | `test_runtime_tapped_video_edits_the_card_caption_and_leaves_two_messages` | 3 (`Checking link…`, photo card, `sendVideo`) | 1 | **2** | caption: `Video — downloading…` → `sending…` → `sent.`, card text kept above |
| Automatic video, no thumbnail (LinkedIn) | `test_runtime_automatic_video_edits_the_card_text_and_leaves_two_messages` | 2 (`Checking link…`, `sendVideo`) | 0 | **2** | text: card published with `Video — only version available, downloading…` → `sending…` → `sent.` |
| Picture (Instagram) | `test_runtime_picture_edits_the_checking_message_and_leaves_two_messages` | 2 (`Checking link…`, `sendDocument`) | 0 | **2** | text: `Picture — downloading…` → `sending…` → `sent.` |
| Download fails | `test_runtime_worker_failure_ends_on_the_same_status_surface` | 2 | 1 | 1 (the card) | caption: `Video — downloading…` → `Video — downloading failed. <next step>` |
| Upload unconfirmed (502) | `test_runtime_unconfirmed_upload_ends_with_could_not_confirm_on_the_card` | — | — | — | caption ends in `Video — could not confirm sending. Check this chat before sending the link again.` |

- In every row `sendMessage` is called exactly once (`Checking link…`); no stage, success,
  or failure sends a new message. `update_status` contract rows (edit text vs caption with
  prefix, "message is not modified" ignored, one fallback `sendMessage` on any other edit
  error) pass in `test_bot_preview.py::test_update_status_*`.
- Callback path: the keyboard is still removed at once (`editMessageReplyMarkup`) and the
  callback is answered with the label as a toast; no confirmation message is sent.
- `Tap Audio only` (quickstart §2) is covered by the same runtime path as the tapped video
  row (label from the selected option); it has no dedicated runtime test.

## Completion (T038)

- Date: 2026-09-23
- Branch: `003-streamlined-bot-ux` at `960b4dc`

### Automated checks

| Check | Result |
|---|---|
| `uv run pytest` | green: 517 passed, 3 deselected (`live`), 0 failed (baseline 357) |
| `uv run python -m openmedia --check-config` | `configuration valid` (token redacted) |

The 20 warnings are python-telegram-bot `PTBDeprecationWarning` about `retry_after` as an
integer, raised through `src/openmedia/delivery.py`, which 003 does not touch.

### Manual Telegram run (quickstart §3)

Run on one iPhone and one Android phone in a private chat, bot started locally with
`OPENMEDIA_DIAGNOSTIC_LOG=1`. Times are from the console stage log.

| Case | Result |
|---|---|
| YouTube `Video` (auto-dubbed video, 17.4 MB merged) | delivered and confirmed; card in 2.1 s, 5.8 s from tap to delivery; plays inline on both phones |
| YouTube `Video (no sound)` | plays inline on both phones, not shown as a looping animation (SC-005 holds) |
| Instagram (4.8 MB) | delivered and confirmed; card in 5.1 s, 4.1 s from tap to delivery |
| LinkedIn, two app-shared links (`lnkd.in/p/…`) | rejected as unsupported before a request is created; see limitations |

### Defects found and fixed during this run

Both lie in 001's yt-dlp adapter; 003 exposed them.

- `697210f fix(001): keep only the original-language audio track`: an auto-dubbed video with
  100 audio streams produced 840 merge pairs and a 3 MB inspect result, over the worker
  protocol's 2 MiB line limit, so inspection failed as `internal`. Now 42 pairs, 182 KB, and
  the audio is the original language rather than a dub.
- `960b4dc fix(001): download YouTube streams in ranged pieces`: a whole-file GET is
  throttled by YouTube (measured 32 KB/s vs 9 MB/s ranged), so a merged choice took 120 s or
  dropped its connection. Now 1–2 s per choice. A dropped or stalled connection is also
  reported as `timeout` instead of `internal`.

### Remaining limitations

- ~~**LinkedIn app share links (`lnkd.in`) are unsupported.**~~ Resolved by 004: `lnkd.in/p/…` links are resolved in the inspect worker; see [004 validation](../004-linkedin-share-links/validation.md). They 301 to
  `linkedin.com/posts/…`, but recognition never contacts the source, so the short host is
  refused. Supporting it adds a pre-recognition network hop and is a scope decision for a
  follow-up feature. Resolved by hand, one of the two sampled links downloads (a picture).
- ~~**Some LinkedIn post slugs end in a hyphenated code**~~ Resolved by 004 (research R6/R7); see [004 validation](../004-linkedin-share-links/validation.md). (`…-7508434034927017984-lwx-`). Both
  our slug pattern and yt-dlp's `LinkedInIE` (`-\w{4}`) reject it; not yet investigated.
- **Merged `Video` may pair low-bitrate audio.** Pairs with equal video bitrate fall through
  to the lowest `option_id`, which picked HE-AAC 139 (49 kbps) over AAC 140 (130 kbps).
  Playable; a tie-break on audio bitrate is a follow-up.
- **Opus audio on iOS**: `Audio only` is usually Opus 251 (`.webm`), which iOS may need
  another app to play (accepted in the spec edge cases).
- **LinkedIn usually offers one choice**, so it is delivered without a tap.
- ~~**Rejected links leave no diagnostic event**~~ Resolved by 004: refused messages write a `refused` entry; see [004 validation](../004-linkedin-share-links/validation.md)., which slowed diagnosis of the LinkedIn case.
- **Local runs on macOS** need `OPENMEDIA_WORK_DIR=/private/tmp/openmedia`: `/tmp` is a
  symlink and the workspace sweep refuses a symlinked root. The container is unaffected.

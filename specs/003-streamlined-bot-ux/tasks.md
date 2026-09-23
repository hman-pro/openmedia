---

description: "Task list for 003 streamlined bot UX"
---

# Tasks: Streamlined Bot UX

**Input**: Design documents from `/specs/003-streamlined-bot-ux/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/telegram-bot.md,
contracts/choice-policy.md, quickstart.md

**Tests**: Included. The constitution requires validation of changed success and failure
paths with controlled fixtures, and 001/002 were built test-first. Write each test task
before its implementation task and confirm it fails.

**Organization**: Grouped by user story. Commit at each phase boundary:
`feat(003): phase N <name>`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an unfinished task)
- **[Story]**: US1, US2, US3 from spec.md
- Controlled tests use `fake_bot` / `FakeTelegramTransport` from `tests/conftest.py`
  (`queue_result`, `queue_error`, `calls_to`) and fixtures under `tests/fixtures/`

---

## Phase 1: Setup (release gate first)

**Purpose**: Answer the one open risk (research R7) before building on it.

- [X] T001 Run `uv sync --locked --group dev && uv run pytest` on branch `003-streamlined-bot-ux` and confirm the baseline is green before any change; note the pass count in `specs/003-streamlined-bot-ux/validation.md` (create the file with a "Baseline" section).
- [X] T002 Create `tests/live/test_inline_video.py`, every test marked `@pytest.mark.live`. Skip with an actionable reason unless both `TELEGRAM_BOT_TOKEN` and `OPENMEDIA_LIVE_CHAT_ID` are set in the environment (never read or write a token file; the operator exports the token from the OS keyring for the run). In `tmp_path`, generate two test clips with ffmpeg from `lavfi` sources: `with_sound.mp4` (H.264 + AAC, 5 s, 640×360) and `silent.mp4` (H.264 only, 5 s, 360×640). For each: `sendVideo(supports_streaming=True, width, height, duration)`, take the returned message's `video` (or `animation`, or `document`) `file_id`, `getFile`, download the bytes, assert SHA-256 equals the uploaded file, and record the returned message type in the assertion message. Delete both sent messages at the end.
- [X] T003 Run `uv run pytest -m live tests/live/test_inline_video.py -rs` with a real token and chat, and record in `specs/003-streamlined-bot-ux/validation.md` under "Inline video gate (R7)": date, both hashes equal or not, and the message type for each clip. **Gate**: if either hash differs, stop and bring the result to the maintainer; FR-009 must be revised before Phase 3 starts.

**Checkpoint**: Inline video is proven byte-preserving (or the spec is revised).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The pure choice policy, request fields, the automatic claim, and all fixed text.

**⚠️ CRITICAL**: No user story work begins until this phase is complete.

- [X] T004 Move `_codec_family` from `src/openmedia/sources/ytdlp.py` to `src/openmedia/sources/__init__.py` as public `codec_family` (same mapping: `avc1`/`h264`→`h264`, `av01`/`av1`→`av1`, `mp4a`/`aac`→`aac`, `vp9`→`vp9`, `opus`→`opus`, else lowercased input), add it to `__all__`, and import it in `ytdlp.py`. No behavior change; `uv run pytest tests/contract/test_ytdlp.py tests/integration/test_merge.py` stays green.
- [X] T005 [P] Write failing tests in `tests/unit/test_choices.py` covering every row of the "Required test cases" table in `specs/003-streamlined-bot-ux/contracts/choice-policy.md`, plus the guarantees: output is a subset of input with only `option_id` changed; at most one option per kind; order `video`, `silent`, `audio`; ids `0..n-1`; deterministic; never raises on empty or all-excluded input. Build `FormatOption` fixtures directly with `transport_ref={"vcodec": ..., "acodec": ...}` (merged options carry the merge's `vcodec`/`acodec`). Also assert `missing` values are exactly `not_offered` or `too_large`, and `automatic is True` iff exactly one option is kept.
- [X] T006 Create `src/openmedia/choices.py` to pass T005: `ChoiceKind(StrEnum)` with `VIDEO="video"`, `SILENT="silent"`, `AUDIO="audio"`, `IMAGE="image"`; `kind_of(option) -> ChoiceKind` derived as in data-model ("`media_type=video`, `includes_audio=true`" → video; "`includes_audio=false`" → silent; audio → audio; image → image); frozen `ChoiceSet(options: tuple[FormatOption, ...], missing: Mapping[ChoiceKind, str], automatic: bool)`; `choose(options, *, media_kind, max_file_bytes) -> ChoiceSet`. Rules verbatim from research R1–R3: phone-playable = extension `mp4`, `codec_family(vcodec) == "h264"`, and `codec_family(acodec) == "aac"` when `includes_audio` (unknown-codec `mp4` handled as last resort below); only `availability == "selectable"` inputs; size filter first ("known size (exact or estimated) is at most the delivery limit. Only if no candidate has a known size, consider unknown-size candidates"); shorter side is `min(width, height)` when both are known, "the one known dimension when only one is", unknown when neither is; tier 1 ≤ 720 takes the largest, else tier 2 takes the smallest; unknown dimensions rank in tier 1 below every known-dimension candidate; an `mp4` whose `vcodec` (and, for `video`, `acodec`) is absent is a last-resort candidate "used only when no known-codec candidate of that kind exists"; ties: known codecs before unknown, higher bitrate, exact before estimated, lower `option_id`. Audio: highest bitrate, same size filter, any extension. Image: the single selectable image option. Rebind kept options with `dataclasses.replace(option, option_id=i)`. No I/O, no Telegram import.
- [X] T007 [P] Add failing tests to `tests/integration/test_merge.py` for the post-download check in `_validate_selected_streams` (research R1, analysis C1): for an `mp4` video option whose `transport_ref` has no `vcodec`, a probed file with H.264 video (and AAC audio when `includes_audio`) passes; VP9, AV1, or HEVC video, or non-AAC audio with `includes_audio`, raises `SourceAdapterError(FORMAT_UNAVAILABLE, stage="download")` and the file is deleted; options with known codecs keep today's behavior. Generate the tiny input clips with real ffmpeg from `lavfi` sources, reusing `make_sources`/`tool` in that file (an H.264/AAC MP4 as the passing case; an MPEG-4 Part 2 (`mpeg4`) MP4 as the non-H.264 case, since that encoder ships with every ffmpeg build).
- [X] T008 In `src/openmedia/sources/ytdlp.py` `_validate_selected_streams`, when `option.media_type == "video"`, `option.extension == "mp4"`, and `reference.get("vcodec")` is falsy, require `codec_family(video[0]["codec_name"]) == "h264"` and, when `option.includes_audio`, `codec_family(audio[0]["codec_name"]) == "aac"`; otherwise raise as for a changed codec. Pass T007.
- [X] T009 [P] Write failing tests in `tests/unit/test_models.py` for new `DownloadRequest` fields: `status_message_id` "Positive integer or null" (0 and negatives raise `ValueError`); `status_is_caption: bool = False`; `status_prefix: str | None = None`, and that `status_prefix` does not appear in `repr` (like `work_directory`).
- [X] T010 Add the three fields to `DownloadRequest` in `src/openmedia/models.py` to pass T009 (`status_prefix` with `field(default=None, repr=False)`).
- [X] T011 [P] Write failing tests in `tests/unit/test_coordinator.py` for `RequestRegistry.publish_and_claim(request_id, *, metadata, options, preview_message_id, now=None) -> SelectionResult`: from `checking` with the work reservation held it returns `ACCEPTED` with `option = options[0]`, sets `selected_option_id == 0`, `processing_deadline == now + 600`, `preview_expires_at is None`, `state == downloading`, and the request **remains** in the work (and, for Instagram, Instagram) reservations so `active_work_count` is unchanged; it returns a non-accepted result and changes nothing when the request is not `checking`, not the user's active request, replaced, or unknown; `ValueError` when `options` is not exactly one entry.
- [X] T012 Implement `publish_and_claim` in `src/openmedia/coordinator.py` to pass T011, under `_registry_lock` only (the same lock as `publish_preview`; the per-user guard is not needed because `submit` is the request's only writer while it is `checking`), reusing the eligibility checks of `publish_preview` and the bookkeeping of `claim_selection` (discard `_pending_reservations`, keep `_work_reservations`/`_instagram_reservations`).
- [X] T013 [P] Rewrite `tests/unit/test_option_labels.py` as failing tests for new pure helpers in `src/openmedia/presentation.py`, exact strings from research R9 and `contracts/telegram-bot.md`: `choice_label(kind)` → `Video`, `Video (no sound)`, `Audio only`, `Picture`; `card_text(metadata, choice_set, status=None)` → title truncated to 200 characters or `Untitled video`, then duration `m:ss`/`h:mm:ss` (line omitted when unknown), then at most one unavailable line: one line built from `missing`: `Not available: <labels>.` for `not_offered` kinds and `Too large to send: <labels>.` for `too_large` kinds, labels in kind order joined by `, `; when both apply, the two sentences share the line (e.g. `Not available: Audio only. Too large to send: Video.`); no line when nothing is missing (assert exact strings for: one kind not offered, two kinds not offered, one too large, one not offered plus one too large), then the status line when given; total ≤ 1,024 characters; contains none of `Platform:`, `Source:`, `Creator:`, `http`, `MiB`, `kbps`, `avc1`, `mp4a`, `webm`, `opus`. `status_text(label, stage, *, automatic=False, next_step=None, unknown=False)` → `<Label> — downloading…`, `<Label> — only version available, downloading…`, `<Label> — sending…`, `<Label> — sent.`, `<Label> — <stage> failed. <next step>`, `<Label> — could not confirm sending. Check this chat before sending the link again.`; `CHECKING_TEXT == "Checking link…"`.
- [X] T014 Implement `choice_label`, `card_text`, `status_text`, and `CHECKING_TEXT` in `src/openmedia/presentation.py` to pass T013. Keep `sort_options` (used by `ytdlp.normalize_info`). Keep `option_label`/`format_size` for now; T024 removes them.

**Checkpoint**: `uv run pytest tests/unit` green. Commit `feat(003): phase 2 foundational`.

---

## Phase 3: User Story 1 - Pick a video in one tap from three plain choices (Priority: P1) 🎯 MVP

**Goal**: A video link yields one card (thumbnail, title, duration) with ≤3 labeled buttons;
a tap delivers an inline-playable video or an audio file; a single possible choice is sent
without a tap.

**Independent Test**: Controlled run with YouTube, Instagram, and LinkedIn yt-dlp fixtures
and the fake transport: card content and buttons match the contract, and each choice is
delivered with the right Telegram method (quickstart §2, US1 rows).

### Tests for User Story 1

- [X] T015 [P] [US1] Rewrite `tests/contract/test_bot_preview.py` as failing tests for `build_card(request_id, metadata, choice_set, status=None) -> RenderedCard(text, keyboard | None)` in `src/openmedia/bot.py`, using `normalize_info` on `tests/fixtures/ytdlp/youtube-video.json` then `choose`: exactly three buttons with texts `Video`, `Video (no sound)`, `Audio only` in that order and callback data `s:<request_id>:0|1|2`; every callback ≤ 64 UTF-8 bytes; no pagination row; `keyboard is None` when `choice_set.automatic`; text equals `card_text(...)`; the card has at most 3 lines besides the title (SC-001), checked on the YouTube card before and after a status line is added. For `send_card(bot, *, chat_id, rendered, thumbnail_path, checking_message_id) -> tuple[int, bool]`: with a thumbnail → one `sendPhoto` carrying `caption` and `reply_markup`, then `deleteMessage` of `checking_message_id`, returns `(photo_id, True)`; `deleteMessage` error is ignored; without a thumbnail, or when `sendPhoto` fails → `editMessageText` on `checking_message_id` with text and keyboard, no `sendMessage`, returns `(checking_message_id, False)`.
- [X] T016 [P] [US1] Update `tests/contract/test_bot_callbacks.py` as failing tests: `p:<rid>:<n>` payloads are rejected by `parse_callback_data` as malformed and answered with the invalid-choice alert without touching the registry; an accepted selection answers the callback with the plain label (e.g. `Audio only`) and removes the keyboard; `option_id` 3 on a 3-choice request yields the `INVALID_OPTION` answer. Remove the pagination cases and any assertion on numbered labels.
- [X] T017 [P] [US1] Add failing tests to `tests/contract/test_delivery_errors.py` for `deliver_media` in `src/openmedia/delivery.py`: `video` and `silent` kinds call `sendVideo` with `supports_streaming=True` and `width`/`height`/`duration` when known (omitted when unknown); `audio` calls `sendDocument`; a `sendVideo` result whose message carries `video`, `animation`, or `document` is `confirmed`; the 001 semantics hold for `sendVideo` too: `RetryAfter` retried only inside the deadline, `TimedOut`/`NetworkError` → `unknown`/`ambiguous_upload` with no retry, `Forbidden` → `blocked`, `BadRequest` → `telegram_rejected`.
- [X] T018 [P] [US1] Rewrite the flow tests in `tests/integration/test_download_flow.py` as failing tests driving `MediaWorkflow` with injected callables: (a) `tests/fixtures/ytdlp/youtube-video.json` (heights only, no 720p stream) → card published with 3 choices bound as `video` = format `18` (360p muxed, tier 1), `silent` = `137` (1080p, smallest in tier 2), `audio` = `140`; selecting `Video` downloads exactly format `18` and delivers via the video path; (b) `tests/fixtures/ytdlp/linkedin-video-progressive.json` (two MP4s with no codecs, dimensions, or size) → `video` = format `0` as a last-resort candidate, `publish_and_claim` is used, no keyboard, download starts without a callback, delivered via the video path; (c) every video candidate over the limit and no audio → no card keyboard, failure with the 001 `too_large` meaning; (d) only VP9/AV1 video and no audio → failure with the `no_formats` meaning; (e) automatic video whose `publish_and_claim` returns non-accepted (request replaced after the card was sent) → no download starts and the failure is reported at stage `checking`.
- [X] T019 [P] [US1] Update `tests/integration/test_diagnostic_trace.py`: `inspection_finished` carries `choices` (list of kind strings, e.g. `["video","silent","audio"]`) and `selection` carries `automatic` (`false` after a tap, `true` for the LinkedIn automatic flow); no URL or identifier appears in either.

### Implementation for User Story 1

- [X] T020 [US1] In `src/openmedia/bot.py`: replace `RenderedPreview`/`build_preview`/`send_preview`/`selected_label` with `RenderedCard`, `build_card`, `send_card` per T015; restrict `_CALLBACK` to `^s:([0-9a-f]{32}):(0|[1-9][0-9]{0,9})$` and delete the `p` branch in `BotHandlers.callback`; confirmation text is `choice_label(kind_of(option))`; set `HELP_TEXT` to the text in `contracts/telegram-bot.md` "Help text". Card text is plain text (no `parse_mode`).
- [X] T021 [US1] In `src/openmedia/delivery.py`, rename `deliver_document` to `deliver_media(bot, *, request, downloaded, owned_directory, max_file_bytes, deadline, duration_seconds=None, ...)` and choose `bot.send_video(..., video=file, supports_streaming=True, width=..., height=..., duration=...)` for `video`/`silent` kinds and `bot.send_document` otherwise, keeping the pre-send validation and the retry/ambiguity loop unchanged for both. Pass T017.
- [X] T022 [US1] In `src/openmedia/coordinator.py` `MediaWorkflow`: add constructor argument `max_file_bytes: int`; in `submit`, after the media-identity check call `choose(result.options, media_kind=result.metadata.media_kind, max_file_bytes=self.max_file_bytes)`; if it keeps nothing raise `SourceAdapterError(ErrorCategory.TOO_LARGE if "too_large" in missing.values() else ErrorCategory.NO_FORMATS, stage="checking")`; emit `inspection_finished` with `options=len(result.options)` and `choices=[kind values]`; change the `publish_preview` callable to receive `(request, result, choice_set)`; when `choice_set.automatic` call `registry.publish_and_claim` instead of `registry.publish_preview`; if it does not return `ACCEPTED`, raise `WorkflowError("request changed before automatic claim")` inside the inspection block so the request fails at stage `checking` and the card's status shows the failure (analysis U4); otherwise, **after** leaving the inspection `asyncio.timeout` block and cleanup, `await self.process_claimed(request, option, automatic=True)`; add `automatic: bool = False` to `process_claimed` and pass it to the `selection` event. Pass T018 and T019.
- [X] T023 [US1] In `src/openmedia/__main__.py`: in `status("checking")` send `CHECKING_TEXT` and store the returned message ID in `request.status_message_id`; make `preview(request, result, choice_set)` call `build_card`/`send_card` with `checking_message_id=request.status_message_id`, then set `request.status_message_id`, `request.status_is_caption`, and `request.status_prefix` (the card text without a status line) and return the card message ID; construct `MediaWorkflow(..., max_file_bytes=self.settings.max_file_bytes)`; call `deliver_media` with `duration_seconds=request.metadata.duration_seconds`.
- [X] T024 [US1] Remove `option_label`, `format_size`, and every `selected_label` use from `src/openmedia/presentation.py`, `src/openmedia/bot.py`, and `src/openmedia/__main__.py`; update `tests/contract/test_ytdlp.py` to assert on option fields instead of label strings. `grep -rn "option_label\|format_size\|selected_label\|page_size" src tests` returns nothing.
- [X] T025 [US1] Run `uv run pytest`; all green. Walk quickstart §2 rows "YouTube video, thumbnail", "No thumbnail", "Tap Video", "LinkedIn muxed video", "Every video choice too large", "Old p: callback" and record results in `specs/003-streamlined-bot-ux/validation.md` under "US1".

**Checkpoint**: US1 works on its own (status messages may still be separate until US3).
Commit `feat(003): phase 3 US1 three-choice card`.

---

## Phase 4: User Story 2 - Receive a picture immediately, without choosing (Priority: P2)

**Goal**: An image post is delivered as a file with no card and no buttons.

**Independent Test**: Instagram and LinkedIn image fixtures with the fake transport: no
`sendPhoto`, no keyboard, one `sendDocument` whose bytes equal the fixture (quickstart §2,
"Instagram picture").

### Tests for User Story 2

- [ ] T026 [P] [US2] Add failing tests to `tests/integration/test_download_flow.py`: an Instagram single-image inspection (from `tests/fixtures/instagram/instagram-image-single-post.json` via the adapter's normalization) and a LinkedIn single image (`tests/fixtures/linkedin/linkedin-image-single.html`) each go through `publish_and_claim` with `preview_message_id == request.status_message_id`, never call the preview callable, deliver via `sendDocument` with `filename` ending in the native extension, and the uploaded bytes equal the downloaded bytes; an image over the delivery limit fails with the 001 `too_large` meaning.

### Implementation for User Story 2

- [ ] T027 [US2] In `src/openmedia/coordinator.py` `MediaWorkflow.submit`, when `result.metadata.media_kind == MediaKind.IMAGE`, skip the preview callable and call `registry.publish_and_claim(..., preview_message_id=request.status_message_id)`, then continue as the automatic path of T022. Raise `WorkflowError` if `status_message_id` is missing. Pass T026.
- [ ] T028 [US2] Confirm in `src/openmedia/delivery.py` that the `image` kind always uses `send_document` (never `send_photo`) and add a one-line comment citing "`sendPhoto` recompresses" from `contracts/telegram-bot.md`. Run `uv run pytest`; record the "Instagram picture" quickstart row in `validation.md` under "US2".

**Checkpoint**: US1 and US2 both pass. Commit `feat(003): phase 4 US2 automatic pictures`.

---

## Phase 5: User Story 3 - See what the bot is doing in one live status line (Priority: P3)

**Goal**: One message per request carries progress, edited in place, ending in the outcome.

**Independent Test**: Fake-transport runs of a tapped video, an automatic video, a picture,
and a failing download: exactly two bot messages remain after success, and the status text
sequence matches the contract "Stage text" table (quickstart §2, SC-004).

### Tests for User Story 3

- [ ] T029 [P] [US3] Add failing contract tests to `tests/contract/test_bot_preview.py` for `update_status(bot, request, text) -> None` in `src/openmedia/bot.py`: `status_is_caption=False` → `editMessageText` on `status_message_id`; `True` → `editMessageCaption` whose caption is `status_prefix` + newline + text; a `BadRequest` "message is not modified" is ignored with no other call; any other edit error → exactly one `sendMessage` with the same text, and `status_message_id` then points to the new message with `status_is_caption=False`.
- [ ] T030 [P] [US3] Add failing integration tests to `tests/integration/test_download_flow.py` with the real runtime callbacks from `src/openmedia/__main__.py` over `fake_bot`: after a successful tapped video, automatic video, and picture, the chat holds exactly two bot messages (count `sendMessage`+`sendPhoto`+`sendVideo`+`sendDocument` minus successful `deleteMessage`), and the edit sequence is `<Label> — downloading…` (or `… only version available, downloading…`), `<Label> — sending…`, `<Label> — sent.`; a worker failure ends with `<Label> — downloading failed. <next step>` on the same message; an unconfirmed upload ends with the "could not confirm sending" text; no `sendMessage` is used for any of these stages.

### Implementation for User Story 3

- [ ] T031 [US3] Implement `update_status` in `src/openmedia/bot.py` to pass T029.
- [ ] T032 [US3] In `src/openmedia/__main__.py`, change `status(request, stage)` for `downloading` and `sending` to call `update_status` with `status_text(label, stage, automatic=...)`, where `label = choice_label(kind_of(request.option(request.selected_option_id)))`; add a `completed` stage called by `MediaWorkflow.process_claimed` in `src/openmedia/coordinator.py` after a confirmed delivery (best effort: a failure to edit never changes the terminal state).
- [ ] T033 [US3] In `src/openmedia/__main__.py` `notify_failure`, edit the status surface with `status_text(label, failed_stage, next_step=result.next_step, unknown=result.status == "unknown")` via `update_status`; when no option was selected yet (checking-stage failure), edit `status_message_id` to the plain 001 failure text; fall back to `sendMessage` only when `status_message_id` is `None`. Pass T030.
- [ ] T034 [US3] In the callback path of `src/openmedia/bot.py`, keep the immediate keyboard removal (`editMessageReplyMarkup`, it blocks a second tap before the workflow's first edit) and do not send a confirmation message; the first status edit (`<Label> — downloading…`) comes from the workflow's `downloading` stage, not from a separate confirmation message. Run `uv run pytest`; record SC-004 counts in `validation.md` under "US3".

**Checkpoint**: All three stories pass independently. Commit `feat(003): phase 5 US3 in-place status`.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [ ] T035 [P] Amend `specs/001-media-download/contracts/telegram-bot.md`, `specs/001-media-download/spec.md` (FR-004, FR-005, FR-007), and `specs/001-media-download/data-model.md` (`options`, new request fields), each change marked "(amended by 003)" and pointing to the 003 file, per `contracts/telegram-bot.md` "Amendments to 001 artifacts".
- [ ] T036 [P] Amend `specs/002-file-logging/data-model.md` Log Entry table with `choices` ("array of string", `inspection_finished`) and `automatic` ("boolean", `selection`), marked "(amended by 003)".
- [ ] T037 [P] Add 003 rows to the "Where truth lives" table in `CLAUDE.md`: `specs/003-streamlined-bot-ux/tasks.md` (working on the card, choices, or status) and `specs/003-streamlined-bot-ux/contracts/` (touching what users see or which version is picked).
- [ ] T038 Run `uv run pytest`, `uv run python -m openmedia --check-config`, and the manual Telegram run in quickstart §3 on one iPhone and one Android phone (YouTube `Video` and `Video (no sound)`, LinkedIn video, Instagram picture), confirming SC-005: both video choices play inline in the default player and the silent one is not shown as a looping animation, or record that it is. Record checks, results, and remaining limitations (Opus audio on iOS; LinkedIn usually one choice) in `specs/003-streamlined-bot-ux/validation.md` "Completion".

---

## Dependencies & Execution Order

- **Phase 1** → **Phase 2** → US1 → US2 → US3 → Polish (CLAUDE.md: phases are strictly
  sequential, one commit per phase).
- T003 is a hard gate: a failing hash stops work before Phase 3.
- US2 depends on `publish_and_claim` (T012), the automatic path in T022, and `status_message_id` being recorded in T023.
- US3 depends on `status_message_id` being recorded (T023) and on `deliver_media` (T021).
- Within a phase: test task before its implementation task; T004 before T006 and T008; T014 before
  T015's implementation (T020).

## Parallel Opportunities

- Phase 2: T005, T007, T009, T011, T013 (five test files) together; then T006, T008, T010, T012, T014
  touch different files and can also run together.
- US1 tests: T015, T016, T017, T018, T019 are separate files.
- US3 tests: T029 and T030 together.
- Polish: T035, T036, T037 together.

```text
# Phase 2 test batch
T005 tests/unit/test_choices.py
T007 tests/integration/test_merge.py
T009 tests/unit/test_models.py
T011 tests/unit/test_coordinator.py
T013 tests/unit/test_option_labels.py
```

## Implementation Strategy

- **MVP = Phase 1–3 (US1)**. It removes the format list for every video, which is the core
  complaint. Stop there, run quickstart §3 with a real phone, and decide whether to continue.
- US2 adds pictures without a tap (≈1 hour). US3 cleans up messages (≈2–3 hours).
- Rough effort with tests: Phase 2 ≈ 3 hours, US1 ≈ 4–5 hours, US2 ≈ 1 hour, US3 ≈ 2–3 hours,
  Polish ≈ 1 hour.

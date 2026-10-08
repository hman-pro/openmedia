from __future__ import annotations

import pytest

from openmedia.bot import InputError, failure_message, parse_link_message
from openmedia.sources import ErrorCategory, SourceAdapterError


@pytest.mark.parametrize(
    "text",
    [
        "no links",
        "https://example.com/not-supported",
        "https://youtu.be/abcDEF12345 https://instagram.com/p/DdExample1/",
        "https://www.youtube.com/playlist?list=PL123 https://youtu.be/abcDEF12345",
    ],
)
def test_invalid_or_multiple_supported_links_are_rejected(text: str) -> None:
    with pytest.raises((InputError, SourceAdapterError)):
        parse_link_message(text, chat_type="private")


def test_groups_are_directed_to_private_chat() -> None:
    with pytest.raises(InputError, match="private chat"):
        parse_link_message("https://youtu.be/abcDEF12345", chat_type="supergroup")


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/playlist?list=PL123",
        "https://www.youtube.com/live/abcDEF12345",
    ],
)
def test_collection_and_live_routes_are_rejected(url: str) -> None:
    with pytest.raises(SourceAdapterError) as caught:
        parse_link_message(url, chat_type="private")
    assert caught.value.category is ErrorCategory.UNSUPPORTED_COLLECTION


@pytest.mark.parametrize("category", list(ErrorCategory))
def test_every_adapter_error_has_sanitized_guidance(category: ErrorCategory) -> None:
    message = failure_message(category, stage="checking")
    assert message
    assert "traceback" not in message.lower()
    assert "token" not in message.lower()
    assert any(word in message.lower() for word in ("send", "submit", "choose", "retry", "later", "check"))


def private_update(text: str, reply):
    from types import SimpleNamespace

    return SimpleNamespace(
        edited_message=None,
        effective_user=SimpleNamespace(id=7),
        effective_chat=SimpleNamespace(id=7, type="private"),
        effective_message=SimpleNamespace(text=text, entities=(), reply_text=reply),
    )


def oversized_option(index: int):
    from openmedia.models import FormatOption

    return FormatOption(
        option_id=index, adapter="yt_dlp", source_format_id=f"{index}+140", media_type="video",
        extension="mp4", mime_type="video/mp4", includes_audio=True, size_bytes=99_000_000,
        size_kind="estimated", availability="excluded",
        unavailable_reason="Combined size is unknown or exceeds the delivery limit",
    )


async def test_all_excluded_preview_sends_exactly_one_notice_saying_nothing_fits() -> None:
    from unittest.mock import AsyncMock

    from openmedia.bot import BotHandlers, build_card
    from openmedia.coordinator import MediaWorkflow, RequestRegistry
    from openmedia.models import MediaMetadata
    from openmedia.sources import InspectResult

    sent: list[str] = []
    metadata = MediaMetadata("youtube", "https://www.youtube.com/watch?v=abcDEF12345", "abcDEF12345")

    async def inspect(request):
        return InspectResult(metadata, (oversized_option(0), oversized_option(1)))

    cards: list[object] = []

    async def preview(request, result, choice_set):
        cards.append(build_card(request.request_id, result.metadata, choice_set))
        return 1

    async def notify(request, result):
        sent.append(f"The {result.failed_stage} stage failed. {result.next_step}")

    workflow = MediaWorkflow(RequestRegistry(), inspect=inspect, publish_preview=preview,
        download=AsyncMock(), deliver=AsyncMock(), status=AsyncMock(), notify_failure=notify,
        max_file_bytes=50_000_000)
    reply = AsyncMock(side_effect=sent.append)
    await BotHandlers(workflow)._submit(private_update("https://youtu.be/abcDEF12345", reply), None)
    assert len(sent) == 1
    assert "none of the available choices" in sent[0].lower()
    assert "smaller available option" not in sent[0]
    # Nothing fits, so no card (and no keyboard) is ever rendered.
    assert cards == []


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [
        ("user_busy", "your current request is still processing"),
        ("work_busy", "the service is busy"),
        ("pending_full", "the service is busy"),
        ("instagram_busy", "instagram is busy"),
    ],
)
async def test_busy_admission_outcomes_have_distinct_guidance(outcome: str, expected: str) -> None:
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from openmedia.bot import BotHandlers
    from openmedia.coordinator import AdmissionOutcome, WorkflowBusy

    workflow = SimpleNamespace(
        submit=AsyncMock(side_effect=WorkflowBusy(AdmissionOutcome(outcome))), notify_failure=None)
    reply = AsyncMock()
    await BotHandlers(workflow)._submit(private_update("https://youtu.be/abcDEF12345", reply), None)
    text = reply.await_args.args[0].lower()
    assert expected in text
    assert "queue" in text or outcome == "user_busy"
    if outcome == "user_busy":
        assert "wait" in text and "retry later" not in text
    else:
        assert "retry later" in text


@pytest.mark.parametrize("stage", ["downloading", "sending"])
def test_limit_failure_after_selection_advises_resubmitting(stage: str) -> None:
    message = failure_message(ErrorCategory.TOO_LARGE, stage=stage)
    assert "selected file exceeds the delivery limit" in message
    assert "submit the link again" in message.lower()
    assert "available option" not in message


@pytest.mark.parametrize(
    ("text", "replies"),
    [("good morning everyone", False), ("see youtu.be/abcDEF12345", True)],
)
async def test_group_messages_get_guidance_only_when_they_contain_a_supported_link(text, replies) -> None:
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from openmedia.bot import BotHandlers

    reply = AsyncMock()
    workflow = SimpleNamespace(submit=AsyncMock(), notify_failure=None)
    update = SimpleNamespace(
        edited_message=None,
        effective_user=SimpleNamespace(id=7),
        effective_chat=SimpleNamespace(id=-100, type="supergroup"),
        effective_message=SimpleNamespace(text=text, entities=(), reply_text=reply),
    )
    context = SimpleNamespace(application=SimpleNamespace(create_task=AsyncMock()))
    await BotHandlers(workflow).message(update, context)
    assert reply.await_count == int(replies)
    if replies:
        assert "private chat" in reply.await_args.args[0]
    workflow.submit.assert_not_awaited()
    context.application.create_task.assert_not_called()


def test_native_audio_and_no_format_messages_are_explicit() -> None:
    assert "audio-only" in failure_message(ErrorCategory.FORMAT_UNAVAILABLE, stage="audio")
    assert "no downloadable" in failure_message(ErrorCategory.NO_FORMATS, stage="checking")


def test_unavailable_names_possible_causes_without_asserting_one() -> None:
    message = failure_message(ErrorCategory.UNAVAILABLE, stage="checking")
    assert message == (
        "That content can't be opened without logging in. It may be private, removed, "
        "or shared only with the author's followers or connections. Send another public link."
    )


SHORT_LINK_TEXTS = {
    "SHORT_LINK_UNRESOLVED":
        "That LinkedIn link could not be opened. Send the post's full linkedin.com address.",
    "SHORT_LINK_NOT_POST":
        "That LinkedIn link does not lead to a supported post. Send a public LinkedIn post link.",
}


@pytest.mark.parametrize(("name", "expected"), sorted(SHORT_LINK_TEXTS.items()))
def test_short_link_failures_have_exact_guidance(name: str, expected: str) -> None:
    message = failure_message(getattr(ErrorCategory, name), stage="checking")
    assert message == expected
    for fragment in ("http", "lnkd.in", "www."):
        assert fragment not in message


def test_sanitized_guidance_parametrization_covers_short_link_categories() -> None:
    values = {category.value for category in ErrorCategory}
    assert {"short_link_unresolved", "short_link_not_post"} <= values


@pytest.mark.parametrize(("command", "text_name"), [("start", "START_TEXT"), ("help", "HELP_TEXT")])
async def test_start_and_help_reply_with_their_own_text(command: str, text_name: str) -> None:
    from unittest.mock import AsyncMock

    import openmedia.bot as bot

    reply = AsyncMock()
    await getattr(bot.BotHandlers(workflow=None), command)(private_update(f"/{command}", reply), None)
    reply.assert_awaited_once_with(getattr(bot, text_name))


def test_start_is_one_line_that_points_to_help() -> None:
    from openmedia.bot import START_TEXT

    assert "\n" not in START_TEXT
    assert "/help" in START_TEXT


def test_help_limits_match_the_fixed_deadlines_and_cap() -> None:
    from openmedia.bot import HELP_TEXT
    from openmedia.config import MAX_HOSTED_FILE_BYTES, SELECTION_SECONDS

    assert f"{MAX_HOSTED_FILE_BYTES // 1_000_000} MB" in HELP_TEXT
    assert f"{SELECTION_SECONDS // 60} minutes" in HELP_TEXT


def test_profile_texts_fit_telegram_limits_and_name_the_cap() -> None:
    from openmedia.bot import DESCRIPTION_TEXT, SHORT_DESCRIPTION_TEXT
    from openmedia.config import MAX_HOSTED_FILE_BYTES

    assert len(DESCRIPTION_TEXT) <= 512
    assert len(SHORT_DESCRIPTION_TEXT) <= 120
    assert f"{MAX_HOSTED_FILE_BYTES // 1_000_000} MB" in DESCRIPTION_TEXT


@pytest.mark.parametrize("current", ["", "stale text"])
async def test_profile_is_written_only_when_telegram_copy_differs(current: str) -> None:
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from openmedia.bot import DESCRIPTION_TEXT, SHORT_DESCRIPTION_TEXT, publish_profile

    bot = SimpleNamespace(
        get_my_description=AsyncMock(return_value=SimpleNamespace(description=current)),
        get_my_short_description=AsyncMock(
            return_value=SimpleNamespace(short_description=SHORT_DESCRIPTION_TEXT)),
        set_my_description=AsyncMock(),
        set_my_short_description=AsyncMock(),
    )
    await publish_profile(bot)
    bot.set_my_description.assert_awaited_once_with(DESCRIPTION_TEXT)
    bot.set_my_short_description.assert_not_awaited()


async def test_profile_failure_is_logged_and_swallowed(caplog) -> None:
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from telegram.error import NetworkError

    from openmedia.__main__ import _publish_profile

    bot = SimpleNamespace(get_my_description=AsyncMock(side_effect=NetworkError("down")))
    await _publish_profile(bot)
    assert "bot profile not updated (NetworkError)" in caplog.text


@pytest.mark.parametrize("path", ["/playlist?list=PLexample", "/watch?list=PLexample", "/browse/MPREb_album"])
async def test_music_collection_refusal_performs_no_source_work(path: str) -> None:
    from unittest.mock import AsyncMock
    from openmedia.bot import BotHandlers
    from openmedia.coordinator import MediaWorkflow, RequestRegistry

    inspect, download, deliver, status = AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock()
    workflow = MediaWorkflow(RequestRegistry(monotonic=lambda: 10), inspect=inspect,
        publish_preview=AsyncMock(), download=download, deliver=deliver, status=status,
        max_file_bytes=50_000_000)
    reply = AsyncMock()
    await BotHandlers(workflow)._submit(private_update("https://music.youtube.com" + path, reply), None)
    reply.assert_awaited_once_with("Only one track is supported. Send a YouTube Music track link.")
    inspect.assert_not_awaited()
    download.assert_not_awaited()
    deliver.assert_not_awaited()
    status.assert_not_awaited()


@pytest.mark.parametrize(("category", "stage", "expected"), [
    ("no_native_audio", "checking", "The source has no downloadable native audio-only option. Send another public track link."),
    ("too_large", "checking", "None of the available choices fits"),
    ("unavailable", "checking", "can't be opened without logging in"),
    ("rate_limited", "checking", "source is busy"),
    ("timeout", "checking", "checking stage timed out"),
    ("timeout", "downloading", "downloading stage timed out"),
    ("format_unavailable", "downloading", "selected native format changed"),
    ("internal", "sending", "sending stage failed"),
])
def test_music_failure_guidance_retains_stage_and_retry(category, stage, expected) -> None:
    text = failure_message(category, stage=stage)
    assert expected in text
    assert "Choose a video" not in text
    assert any(word in text.lower() for word in ("send", "submit", "retry"))


@pytest.mark.parametrize("oversize", [False, True])
async def test_empty_music_choices_end_with_audio_reason_and_no_card(oversize) -> None:
    from unittest.mock import AsyncMock
    from openmedia.coordinator import MediaWorkflow, RequestRegistry
    from openmedia.models import FormatOption, MediaMetadata
    from openmedia.sources import InspectResult
    url = "https://music.youtube.com/watch?v=abcDEF12345"
    option = (FormatOption(0, "yt_dlp", "140", "audio", "m4a", "audio/mp4",
        size_bytes=50_000_001, size_kind="exact", availability="excluded", unavailable_reason="too large")
        if oversize else FormatOption(0, "yt_dlp", "18", "video", "mp4", "video/mp4", includes_audio=True))
    registry = RequestRegistry(monotonic=lambda: 10)
    preview, download, deliver, notify = AsyncMock(), AsyncMock(), AsyncMock(), AsyncMock()
    workflow = MediaWorkflow(registry, inspect=AsyncMock(return_value=InspectResult(
        MediaMetadata("youtube", url, "abcDEF12345", media_kind="audio"), (option,))),
        publish_preview=preview, download=download, deliver=deliver, status=AsyncMock(),
        notify_failure=notify, max_file_bytes=50_000_000)
    with pytest.raises(SourceAdapterError) as caught:
        await workflow.submit(user_id=7, chat_id=7, text=url, chat_type="private")
    expected = "too_large" if oversize else "no_native_audio"
    assert caught.value.category.value == expected
    result = notify.call_args.args[1]
    assert result.failed_stage == "checking" and result.error_category == expected
    assert "video" not in result.next_step.lower()
    preview.assert_not_awaited(); download.assert_not_awaited(); deliver.assert_not_awaited()
    assert registry.active_work_count == 0


@pytest.mark.parametrize(("stage", "category", "unknown"), [
    ("checking", "no_native_audio", False), ("downloading", "format_unavailable", False),
    ("sending", "internal", False), ("sending", "timeout", True),
])
async def test_music_failure_finishes_existing_status_surface(tmp_path, stage, category, unknown) -> None:
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from openmedia.__main__ import RuntimeCallbacks
    from openmedia.config import Settings
    from openmedia.coordinator import RequestRegistry
    from openmedia.models import DeliveryResult, FormatOption, MediaMetadata

    url = "https://music.youtube.com/watch?v=abcDEF12345"
    request = RequestRegistry(monotonic=lambda: 10).new_request(user_id=7, chat_id=77,
        source_url=url, platform="youtube", media_id="abcDEF12345")
    request.status_message_id = 55
    if stage != "checking":
        request.metadata = MediaMetadata("youtube", url, "abcDEF12345", media_kind="audio")
        request.options = (FormatOption(0, "yt_dlp", "140", "audio", "m4a", "audio/mp4"),)
        request.selected_option_id = 0
        request.status_prefix = "Track\n0:42"
        request.status_is_caption = True
    bot = SimpleNamespace(edit_message_text=AsyncMock(), edit_message_caption=AsyncMock(), send_message=AsyncMock())
    callbacks = RuntimeCallbacks(Settings.from_env({"TELEGRAM_BOT_TOKEN": "123456789:offline",
        "OPENMEDIA_WORK_ROOT": str(tmp_path)}), SimpleNamespace(bot=bot))
    result = DeliveryResult(status="unknown" if unknown else "failed", error_category=category,
        failed_stage=stage, next_step="Check this chat before submitting the link again." if unknown
        else failure_message(category, stage=stage))
    await callbacks.notify_failure(request, result)
    edit = bot.edit_message_text if stage == "checking" else bot.edit_message_caption
    edit.assert_awaited_once()
    bot.send_message.assert_not_awaited()
    text = edit.call_args.kwargs["text" if stage == "checking" else "caption"]
    assert "video" not in text.lower()
    assert "Check this chat before sending the link again." in text if unknown else result.next_step in text
    if stage != "checking":
        assert text.startswith("Track\n0:42\n")

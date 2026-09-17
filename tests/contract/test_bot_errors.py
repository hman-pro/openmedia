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

    from openmedia.bot import BotHandlers, build_preview
    from openmedia.coordinator import MediaWorkflow, RequestRegistry
    from openmedia.models import MediaMetadata
    from openmedia.sources import InspectResult

    sent: list[str] = []
    metadata = MediaMetadata("youtube", "https://www.youtube.com/watch?v=abcDEF12345", "abcDEF12345")

    async def inspect(request):
        return InspectResult(metadata, (oversized_option(0), oversized_option(1)))

    async def preview(request, result):
        build_preview(request_id=request.request_id, metadata=result.metadata, options=result.options)
        return 1

    async def notify(request, result):
        sent.append(f"The {result.failed_stage} stage failed. {result.next_step}")

    workflow = MediaWorkflow(RequestRegistry(), inspect=inspect, publish_preview=preview,
        download=AsyncMock(), deliver=AsyncMock(), status=AsyncMock(), notify_failure=notify)
    reply = AsyncMock(side_effect=sent.append)
    await BotHandlers(workflow)._submit(private_update("https://youtu.be/abcDEF12345", reply), None)
    assert len(sent) == 1
    assert "none of the available choices" in sent[0].lower()
    assert "smaller available option" not in sent[0]


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

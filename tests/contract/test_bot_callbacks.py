from __future__ import annotations

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from openmedia.bot import BotHandlers, InputError, parse_callback_data
from openmedia.coordinator import RequestRegistry, SelectionOutcome
from openmedia.models import FormatOption, MediaMetadata


RID = "0123456789abcdef0123456789abcdef"
INVALID_CHOICE = "This choice is invalid. Please submit the link again."

# The three policy-kept choices of a video card, in kind order (contracts/telegram-bot.md).
THREE_CHOICES = (
    FormatOption(0, "fixture", "18", "video", "mp4", "video/mp4", height=360, includes_audio=True),
    FormatOption(1, "fixture", "137", "video", "mp4", "video/mp4", height=1080, includes_audio=False),
    FormatOption(2, "fixture", "140", "audio", "m4a", "audio/mp4"),
)


async def _published_request(options=THREE_CHOICES):
    registry = RequestRegistry()
    request = registry.new_request(
        user_id=1,
        chat_id=1,
        source_url="https://youtu.be/abcDEF12345",
        platform="youtube",
        media_id="abcDEF12345",
    )
    await registry.admit(request)
    await registry.publish_preview(
        request.request_id,
        metadata=MediaMetadata("youtube", request.source_url, request.media_id),
        options=options,
        preview_message_id=9,
    )
    return registry, request


def _query(data: str, **overrides):
    fields = dict(
        data=data,
        from_user=SimpleNamespace(id=1),
        message=SimpleNamespace(chat=SimpleNamespace(id=1), message_id=9),
        answer=AsyncMock(),
        edit_message_reply_markup=AsyncMock(),
        edit_message_text=AsyncMock(),
    )
    fields.update(overrides)
    return SimpleNamespace(**fields)


def _context(jobs: list, order: list | None = None):
    def create_task(coro, **kwargs):
        if order is not None:
            order.append("scheduled")
        job = asyncio.create_task(coro)
        jobs.append(job)
        return job

    return SimpleNamespace(application=SimpleNamespace(create_task=create_task))


@pytest.mark.parametrize("failed_call", ["answer", "edit_message_reply_markup"])
async def test_claimed_job_starts_despite_callback_transport_failure(failed_call):
    registry, request = await _published_request()
    query = _query(f"s:{request.request_id}:0")
    getattr(query, failed_call).side_effect = RuntimeError("offline")
    jobs: list = []
    process = AsyncMock()
    workflow = SimpleNamespace(registry=registry, process_claimed=process)
    await BotHandlers(workflow).callback(SimpleNamespace(callback_query=query), _context(jobs))
    await asyncio.gather(*jobs)
    assert process.await_count == 1


@pytest.mark.parametrize(
    ("option_id", "label"),
    [(0, "Video"), (1, "Video (no sound)"), (2, "Audio only")],
)
async def test_accepted_selection_answers_with_the_plain_label_and_removes_the_keyboard(option_id, label):
    registry, request = await _published_request()
    order: list[str] = []
    query = _query(
        f"s:{request.request_id}:{option_id}",
        answer=AsyncMock(side_effect=lambda *a, **k: order.append("answer")),
    )
    jobs: list = []
    process = AsyncMock()
    workflow = SimpleNamespace(registry=registry, process_claimed=process)
    await BotHandlers(workflow).callback(SimpleNamespace(callback_query=query), _context(jobs, order))
    await asyncio.gather(*jobs)
    assert order == ["scheduled", "answer"]
    assert query.answer.await_args.args[0] == label
    assert query.answer.await_args.kwargs.get("show_alert") in (None, False)
    query.edit_message_reply_markup.assert_awaited_once_with(reply_markup=None)
    assert process.await_count == 1
    assert process.await_args.args[1].option_id == option_id


async def test_option_beyond_the_three_choices_is_answered_as_invalid_option():
    registry, request = await _published_request()
    query = _query(f"s:{request.request_id}:3")
    jobs: list = []
    process = AsyncMock()
    workflow = SimpleNamespace(registry=registry, process_claimed=process)
    await BotHandlers(workflow).callback(SimpleNamespace(callback_query=query), _context(jobs))
    await asyncio.gather(*jobs)
    assert jobs == []
    process.assert_not_awaited()
    query.answer.assert_awaited_once_with(
        BotHandlers._selection_feedback(SelectionOutcome.INVALID_OPTION), show_alert=True
    )
    query.edit_message_reply_markup.assert_not_awaited()
    # The request is still waiting for a valid choice.
    retry = await registry.claim_selection(
        request.request_id, user_id=1, chat_id=1, preview_message_id=9, option_id=2
    )
    assert retry.outcome is SelectionOutcome.ACCEPTED


def test_selection_callback_grammar_and_64_byte_ceiling() -> None:
    payload = f"s:{RID}:2"
    action = parse_callback_data(payload)
    assert action.request_id == RID
    assert action.index == 2
    assert len(payload.encode()) <= 64


@pytest.mark.parametrize(
    "payload",
    [
        "",
        f"x:{RID}:0",
        f"s:{RID.upper()}:0",
        f"s:{RID}:-1",
        f"s:{RID}:01",
        f"s:{RID}:999999999999",
        "s:bad:0",
        # The 001 page payload is removed and treated as malformed (research, callbacks).
        f"p:{RID}:0",
        f"p:{RID}:1",
        f"p:{RID}:12",
    ],
)
def test_malformed_callbacks_are_rejected(payload: str) -> None:
    with pytest.raises(InputError):
        parse_callback_data(payload)


@pytest.mark.parametrize("page", [0, 1, 12])
async def test_page_callback_gets_the_invalid_choice_alert_without_touching_the_registry(page):
    registry = MagicMock(name="registry")
    registry.claim_selection = AsyncMock()
    registry.authorize_preview_callback = AsyncMock()
    process = AsyncMock()
    workflow = SimpleNamespace(registry=registry, process_claimed=process)
    query = _query(f"p:{RID}:{page}")
    jobs: list = []
    await BotHandlers(workflow).callback(SimpleNamespace(callback_query=query), _context(jobs))
    query.answer.assert_awaited_once_with(INVALID_CHOICE, show_alert=True)
    assert registry.mock_calls == []
    assert jobs == []
    process.assert_not_awaited()
    query.edit_message_text.assert_not_awaited()
    query.edit_message_reply_markup.assert_not_awaited()


async def test_owner_chat_message_state_and_option_bounds_are_atomic() -> None:
    registry = RequestRegistry()
    request = registry.new_request(
        user_id=1,
        chat_id=2,
        source_url="https://www.youtube.com/watch?v=abcDEF12345",
        platform="youtube",
        media_id="abcDEF12345",
    )
    await registry.admit(request)
    await registry.publish_preview(
        request.request_id,
        metadata=MediaMetadata("youtube", request.source_url, request.media_id),
        options=THREE_CHOICES,
        preview_message_id=9,
        now=10,
    )
    foreign = await registry.claim_selection(request.request_id, user_id=99, chat_id=2, preview_message_id=9, option_id=0, now=11)
    wrong_chat = await registry.claim_selection(request.request_id, user_id=1, chat_id=3, preview_message_id=9, option_id=0, now=11)
    wrong_message = await registry.claim_selection(request.request_id, user_id=1, chat_id=2, preview_message_id=8, option_id=0, now=11)
    wrong_option = await registry.claim_selection(request.request_id, user_id=1, chat_id=2, preview_message_id=9, option_id=3, now=11)
    assert foreign.outcome is SelectionOutcome.NOT_OWNER
    assert wrong_chat.outcome is SelectionOutcome.NOT_OWNER
    assert wrong_message.outcome is SelectionOutcome.STALE
    assert wrong_option.outcome is SelectionOutcome.INVALID_OPTION
    accepted = await registry.claim_selection(request.request_id, user_id=1, chat_id=2, preview_message_id=9, option_id=0, now=11)
    repeated = await registry.claim_selection(request.request_id, user_id=1, chat_id=2, preview_message_id=9, option_id=0, now=11)
    assert accepted.outcome is SelectionOutcome.ACCEPTED
    assert repeated.outcome is SelectionOutcome.PROCESSING
    assert "already processing" in BotHandlers._selection_feedback(repeated.outcome)

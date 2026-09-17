from __future__ import annotations

import pytest

from openmedia.bot import InputError, parse_callback_data
from openmedia.coordinator import RequestRegistry, SelectionOutcome
from openmedia.models import FormatOption, MediaMetadata


RID = "0123456789abcdef0123456789abcdef"


@pytest.mark.parametrize("failed_call", ["answer", "edit_message_reply_markup"])
async def test_claimed_job_starts_despite_callback_transport_failure(failed_call):
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from openmedia.bot import BotHandlers
    registry = RequestRegistry()
    request = registry.new_request(user_id=1, chat_id=1, source_url="https://youtu.be/abcDEF12345", platform="youtube", media_id="abcDEF12345")
    await registry.admit(request)
    option = FormatOption(0, "fixture", "18", "video", "mp4", "video/mp4", includes_audio=True)
    await registry.publish_preview(request.request_id, metadata=MediaMetadata("youtube", request.source_url, request.media_id), options=(option,), preview_message_id=9)
    query = SimpleNamespace(data=f"s:{request.request_id}:0", from_user=SimpleNamespace(id=1),
        message=SimpleNamespace(chat=SimpleNamespace(id=1), message_id=9), answer=AsyncMock(), edit_message_reply_markup=AsyncMock())
    getattr(query, failed_call).side_effect = RuntimeError("offline")
    jobs = []
    def create_task(coro, **kwargs):
        job = asyncio.create_task(coro); jobs.append(job); return job
    process = AsyncMock()
    workflow = SimpleNamespace(registry=registry, process_claimed=process)
    await BotHandlers(workflow).callback(SimpleNamespace(callback_query=query), SimpleNamespace(application=SimpleNamespace(create_task=create_task)))
    await asyncio.gather(*jobs)
    assert process.await_count == 1


async def test_accepted_selection_names_the_chosen_option_after_scheduling_work():
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from openmedia.bot import BotHandlers
    registry = RequestRegistry()
    request = registry.new_request(user_id=1, chat_id=1, source_url="https://youtu.be/abcDEF12345", platform="youtube", media_id="abcDEF12345")
    await registry.admit(request)
    option = FormatOption(0, "fixture", "18", "video", "mp4", "video/mp4", height=360, includes_audio=True)
    await registry.publish_preview(request.request_id, metadata=MediaMetadata("youtube", request.source_url, request.media_id), options=(option,), preview_message_id=9)
    order: list[str] = []
    query = SimpleNamespace(data=f"s:{request.request_id}:0", from_user=SimpleNamespace(id=1),
        message=SimpleNamespace(chat=SimpleNamespace(id=1), message_id=9),
        answer=AsyncMock(side_effect=lambda *a, **k: order.append("answer")), edit_message_reply_markup=AsyncMock())
    jobs = []
    def create_task(coro, **kwargs):
        order.append("scheduled"); job = asyncio.create_task(coro); jobs.append(job); return job
    workflow = SimpleNamespace(registry=registry, process_claimed=AsyncMock())
    await BotHandlers(workflow).callback(SimpleNamespace(callback_query=query), SimpleNamespace(application=SimpleNamespace(create_task=create_task)))
    await asyncio.gather(*jobs)
    assert order == ["scheduled", "answer"]
    assert "Selected 1. video · MP4 · 360p" in query.answer.await_args.args[0]


@pytest.mark.parametrize("payload", [f"s:{RID}:0", f"p:{RID}:12"])
def test_callback_grammar_and_64_byte_ceiling(payload: str) -> None:
    action = parse_callback_data(payload)
    assert action.request_id == RID
    assert len(payload.encode()) <= 64


@pytest.mark.parametrize(
    "payload",
    ["", f"x:{RID}:0", f"s:{RID.upper()}:0", f"s:{RID}:-1", f"s:{RID}:01", f"s:{RID}:999999999999", "s:bad:0"],
)
def test_malformed_callbacks_are_rejected(payload: str) -> None:
    with pytest.raises(InputError):
        parse_callback_data(payload)


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
    option = FormatOption(0, "fixture", "18", "video", "mp4", "video/mp4", includes_audio=True)
    await registry.publish_preview(
        request.request_id,
        metadata=MediaMetadata("youtube", request.source_url, request.media_id),
        options=(option,),
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
    from openmedia.bot import BotHandlers
    assert "already processing" in BotHandlers._selection_feedback(repeated.outcome)

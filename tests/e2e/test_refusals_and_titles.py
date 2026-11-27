"""Refusals the user sees, group behaviour, and 006 captions/filenames as delivered."""

from __future__ import annotations

import asyncio

from openmedia.bot import ONE_LINK_GUIDANCE, failure_message
from openmedia.media_titles import derive_media_titles
from openmedia.sources import ErrorCategory
from tests.e2e import E2E

pytestmark = E2E


async def test_text_without_a_link_gets_one_link_guidance(chat):
    result = await chat.exchange("hello, no link here", tap=False, quiet=3)
    assert result.final_text == ONE_LINK_GUIDANCE and not result.files


async def test_two_links_in_one_message_get_one_link_guidance(chat, case):
    result = await chat.exchange(f"{case('youtube-video')} {case('linkedin-video')}", tap=False, quiet=3)
    assert result.final_text == ONE_LINK_GUIDANCE and not result.files


async def test_media_with_every_choice_over_the_limit_is_refused(chat, case):
    result = await chat.exchange(case("youtube-all-over-limit"), tap=False)
    assert not result.files and not result.buttons
    expected = failure_message(ErrorCategory.TOO_LARGE, stage="checking")
    assert result.final_text == f"The checking stage failed. {expected}"


async def test_link_in_a_group_is_not_delivered(chat, case):
    from telethon.tl.functions.messages import CreateChatRequest, DeleteChatRequest

    bot = await chat.client.get_entity(chat.bot)
    created = await chat.client(CreateChatRequest(users=[bot], title="openmedia e2e group check"))
    group = getattr(created, "updates", created).chats[0]
    try:
        await chat.client.send_message(group, case("youtube-video"), link_preview=False)
        await asyncio.sleep(15)
        messages = await chat.client.get_messages(group, limit=10)
        assert not any(m.document for m in messages)
    finally:
        await chat.client(DeleteChatRequest(chat_id=group.id))


async def test_title_with_a_slash_keeps_the_caption_and_makes_a_safe_filename(chat, case):
    result = await chat.exchange(case("youtube-title-slash"), prefer=("Audio only",))
    assert len(result.files) == 1, result.final_status
    received = result.files[0]
    expected = derive_media_titles(result.card_title, "m4a")
    assert received.caption == expected.caption and "/" in received.caption
    assert received.filename == expected.filename  # stem under 60 characters: Telegram keeps it


async def test_title_with_emoji_keeps_the_caption_literally(chat, case):
    result = await chat.exchange(case("youtube-title-emoji"), prefer=("Video",))
    assert len(result.files) == 1, result.final_status
    received = result.files[0]
    assert received.caption == derive_media_titles(result.card_title, "mp4").caption
    # Telegram's Bot API replaces emoji in filenames with spaces (006 SC-002 note).
    assert received.filename and received.filename.endswith(".mp4")

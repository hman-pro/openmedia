from __future__ import annotations

from pathlib import Path

import pytest

from openmedia.bot import InputError, build_preview, parse_link_message, send_preview
from openmedia.models import FormatOption, MediaMetadata


def option(index: int, *, audio: bool = True) -> FormatOption:
    return FormatOption(
        option_id=index,
        adapter="yt_dlp",
        source_format_id=str(index),
        media_type="video",
        extension="mp4",
        mime_type="video/mp4",
        height=1080 - index,
        includes_audio=audio,
    )


def metadata(**changes: object) -> MediaMetadata:
    values = {
        "platform": "youtube",
        "canonical_url": "https://www.youtube.com/watch?v=abcDEF12345",
        "media_id": "abcDEF12345",
    }
    values.update(changes)
    return MediaMetadata(**values)


def test_first_time_private_user_can_submit_one_supported_link_among_unrelated_urls() -> None:
    route = parse_link_message(
        "hello https://example.com/x https://youtu.be/abcDEF12345 thanks",
        chat_type="private",
    )
    assert route.platform == "youtube"
    with pytest.raises(InputError, match="private chat"):
        parse_link_message("https://youtu.be/abcDEF12345", chat_type="group")


def telegram_message(text: str, *entities: tuple[str, int, int, str | None]):
    from datetime import datetime, timezone

    from telegram import Chat, Message, MessageEntity

    return Message(
        message_id=1,
        date=datetime.now(timezone.utc),
        chat=Chat(id=1, type="private"),
        text=text,
        entities=[
            MessageEntity(type=kind, offset=offset, length=length, url=url)
            for kind, offset, length, url in entities
        ],
    )


@pytest.mark.parametrize(
    ("text", "entity", "expected"),
    [
        ("youtube.com/watch?v=abcDEF12345", ("url", 0, 31, None), "https://youtube.com/watch?v=abcDEF12345"),
        ("http://youtu.be/abcDEF12345", ("url", 0, 27, None), "https://youtu.be/abcDEF12345"),
        ("see this video", ("text_link", 4, 5, "https://youtu.be/abcDEF12345"), "https://youtu.be/abcDEF12345"),
    ],
)
def test_links_are_taken_from_telegram_url_and_text_link_entities(text, entity, expected) -> None:
    from openmedia.bot import message_links

    links = message_links(telegram_message(text, entity))
    assert links == (expected,)
    route = parse_link_message(text, chat_type="private", links=links)
    assert (route.platform, route.media_id) == ("youtube", "abcDEF12345")


def test_entity_link_plus_unrelated_url_counts_one_supported_link() -> None:
    from openmedia.bot import message_links

    text = "example.com/x and youtu.be/abcDEF12345"
    links = message_links(telegram_message(text, ("url", 0, 13, None), ("url", 18, 20, None)))
    assert links == ("https://youtu.be/abcDEF12345",)


def test_scheme_less_link_in_plain_text_is_recognized_without_entities() -> None:
    route = parse_link_message("look: youtu.be/abcDEF12345.", chat_type="private")
    assert route.media_id == "abcDEF12345"
    with pytest.raises(InputError):
        parse_link_message("https://example.com/?next=youtu.be/abcDEF12345", chat_type="private")


async def test_handler_passes_extracted_links_to_the_workflow() -> None:
    import asyncio
    from types import SimpleNamespace
    from unittest.mock import AsyncMock

    from openmedia.bot import BotHandlers

    message = telegram_message("see this video", ("text_link", 4, 5, "https://youtu.be/abcDEF12345"))
    reply = AsyncMock()
    workflow = SimpleNamespace(submit=AsyncMock(), notify_failure=None)
    jobs = []
    context = SimpleNamespace(application=SimpleNamespace(
        create_task=lambda coro, **kwargs: jobs.append(asyncio.ensure_future(coro))))
    update = SimpleNamespace(
        edited_message=None,
        effective_message=SimpleNamespace(text=message.text, entities=message.entities,
            parse_entities=message.parse_entities, reply_text=reply),
        effective_user=SimpleNamespace(id=1),
        effective_chat=SimpleNamespace(id=1, type="private"),
    )
    await BotHandlers(workflow).message(update, context)
    await asyncio.gather(*jobs)
    reply.assert_not_awaited()
    assert workflow.submit.await_args.kwargs["links"] == ("https://youtu.be/abcDEF12345",)


def test_preview_omits_absent_metadata_and_keeps_explicit_single_choice() -> None:
    rendered = build_preview(
        request_id="0123456789abcdef0123456789abcdef",
        metadata=metadata(),
        options=(option(0, audio=False),),
    )
    assert "Title:" not in rendered.text
    assert "Creator:" not in rendered.text
    assert "silent" in rendered.text
    assert rendered.keyboard.inline_keyboard[0][0].callback_data == (
        "s:0123456789abcdef0123456789abcdef:0"
    )


def test_every_excluded_choice_is_explained_or_summarized() -> None:
    excluded = [
        FormatOption(option_id=index, adapter="yt_dlp", source_format_id=f"{index}+140",
            media_type="video", extension="mp4", mime_type="video/mp4", includes_audio=True,
            availability="excluded", unavailable_reason="Combined size is unknown or exceeds the delivery limit")
        for index in range(1, 11)
    ]
    rendered = build_preview(request_id="a" * 32, metadata=metadata(), options=(option(0), *excluded))
    assert rendered.text.count("Unavailable:") == 4
    assert "6 more choices are unavailable: Combined size is unknown or exceeds the delivery limit" in rendered.text


def test_preview_paginates_eight_options_with_compact_callbacks() -> None:
    rendered = build_preview(
        request_id="0123456789abcdef0123456789abcdef",
        metadata=metadata(title_or_caption="Fixture", creator="Creator"),
        options=tuple(option(index) for index in range(10)),
        page=0,
    )
    selection_buttons = [row[0] for row in rendered.keyboard.inline_keyboard if row[0].callback_data.startswith("s:")]
    assert len(selection_buttons) == 8
    assert all(len(button.callback_data.encode()) <= 64 for button in selection_buttons)
    assert any(button.callback_data.endswith(":1") for row in rendered.keyboard.inline_keyboard for button in row if button.callback_data.startswith("p:"))


class CaptureBot:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, object]]] = []

    async def send_message(self, **kwargs):
        self.calls.append(("message", kwargs))
        return type("Message", (), {"message_id": 10})()

    async def send_photo(self, **kwargs):
        assert hasattr(kwargs["photo"], "read")
        self.calls.append(("photo", kwargs))
        return type("Message", (), {"message_id": 11})()


async def test_worker_thumbnail_is_uploaded_from_local_file_and_is_optional(tmp_path: Path) -> None:
    rendered = build_preview(
        request_id="0123456789abcdef0123456789abcdef",
        metadata=metadata(),
        options=(option(0),),
    )
    bot = CaptureBot()
    assert await send_preview(bot, chat_id=1, rendered=rendered) == 10
    thumbnail = tmp_path / "thumb.jpg"
    thumbnail.write_bytes(b"fixture")
    assert await send_preview(bot, chat_id=1, rendered=rendered, thumbnail_path=thumbnail) == 10
    assert [kind for kind, _ in bot.calls] == ["message", "photo", "message"]


async def test_long_thumbnail_preview_keeps_every_option_and_audio_guidance(tmp_path):
    rendered = build_preview(request_id="a" * 32,
        metadata=metadata(title_or_caption="x" * 500, creator="y" * 200),
        options=tuple(option(index) for index in range(9)))
    path = tmp_path / "thumbnail.jpg"; path.write_bytes(b"image")
    bot = CaptureBot()
    await send_preview(bot, chat_id=1, rendered=rendered, thumbnail_path=path)
    assert bot.calls[-1][0] == "message"
    assert "8. video" in bot.calls[-1][1]["text"]
    assert "audio-only" in bot.calls[-1][1]["text"]

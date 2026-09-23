from __future__ import annotations

from pathlib import Path

import pytest

from openmedia.bot import InputError, parse_link_message
from openmedia.choices import ChoiceSet, choose
from openmedia.models import MediaMetadata
from openmedia.presentation import card_text


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


# --- 003 video card (contracts/telegram-bot.md "Video card", SC-001) ---------------------

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "ytdlp"
REQUEST_ID = "0123456789abcdef0123456789abcdef"
LIMIT = 50_000_000


def inspected(name: str):
    import json

    from openmedia.sources.ytdlp import normalize_info

    result = normalize_info(json.loads((FIXTURES / name).read_text()), max_file_bytes=LIMIT)
    choice_set = choose(result.options, media_kind=result.metadata.media_kind, max_file_bytes=LIMIT)
    return result.metadata, choice_set


@pytest.fixture
def youtube() -> tuple[MediaMetadata, ChoiceSet]:
    return inspected("youtube-video.json")


def all_buttons(rendered) -> list:
    return [button for row in rendered.keyboard.inline_keyboard for button in row]


def test_youtube_card_has_three_plain_buttons_in_kind_order(youtube) -> None:
    from openmedia.bot import build_card

    meta, choice_set = youtube
    rendered = build_card(REQUEST_ID, meta, choice_set)
    rows = rendered.keyboard.inline_keyboard
    assert [[button.text for button in row] for row in rows] == [
        ["Video"], ["Video (no sound)"], ["Audio only"],
    ]
    assert [button.callback_data for button in all_buttons(rendered)] == [
        f"s:{REQUEST_ID}:0", f"s:{REQUEST_ID}:1", f"s:{REQUEST_ID}:2",
    ]


def test_card_callbacks_fit_telegram_limit_and_have_no_pagination(youtube) -> None:
    from openmedia.bot import build_card

    meta, choice_set = youtube
    rendered = build_card(REQUEST_ID, meta, choice_set)
    buttons = all_buttons(rendered)
    assert len(buttons) <= 3
    assert all(len(button.callback_data.encode("utf-8")) <= 64 for button in buttons)
    assert not any(button.callback_data.startswith("p:") for button in buttons)
    assert all(button.callback_data.startswith("s:") for button in buttons)


def test_card_text_is_card_text_with_and_without_status(youtube) -> None:
    from openmedia.bot import build_card

    meta, choice_set = youtube
    assert build_card(REQUEST_ID, meta, choice_set).text == card_text(meta, choice_set)
    status = "Video — downloading…"
    rendered = build_card(REQUEST_ID, meta, choice_set, status=status)
    assert rendered.text == card_text(meta, choice_set, status)
    assert rendered.text.splitlines()[-1] == status


def test_automatic_choice_set_renders_card_without_keyboard() -> None:
    from openmedia.bot import build_card

    meta, choice_set = inspected("linkedin-video-progressive.json")
    assert choice_set.automatic
    rendered = build_card(REQUEST_ID, meta, choice_set, status="Video — only version available, downloading…")
    assert rendered.keyboard is None
    assert rendered.text == card_text(meta, choice_set, "Video — only version available, downloading…")


def test_card_has_at_most_three_lines_besides_the_title_sc001(youtube) -> None:
    from openmedia.bot import build_card

    meta, choice_set = youtube
    # Worst case for the YouTube card: an unavailable line is present too.
    worst = ChoiceSet(options=choice_set.options[:2], missing={"audio": "too_large"}, automatic=False)
    for current in (choice_set, worst):
        before = build_card(REQUEST_ID, meta, current)
        after = build_card(REQUEST_ID, meta, current, status="Video — downloading…")
        for rendered in (before, after):
            lines = rendered.text.splitlines()
            assert lines[0] == meta.title_or_caption
            assert len(lines) - 1 <= 3
            assert len(all_buttons(rendered)) <= 3


# --- send_card: one status surface, photo when possible ----------------------------------

CHECKING_ID = 7


def message_result(message_id: int, **extra: object) -> dict[str, object]:
    return {"message_id": message_id, "date": 0, "chat": {"id": 1, "type": "private"}, **extra}


def photo_result(message_id: int) -> dict[str, object]:
    return message_result(message_id, photo=[{
        "file_id": "photo-file", "file_unique_id": "photo-unique", "width": 320, "height": 180,
    }], caption="card")


@pytest.fixture
def thumbnail(tmp_path: Path) -> Path:
    path = tmp_path / "thumb.jpg"
    path.write_bytes(b"fixture-thumbnail")
    return path


async def test_send_card_with_thumbnail_sends_photo_then_deletes_checking(
    fake_bot, fake_transport, youtube, thumbnail
) -> None:
    from openmedia.bot import build_card, send_card

    meta, choice_set = youtube
    rendered = build_card(REQUEST_ID, meta, choice_set)
    fake_transport.queue_result("sendPhoto", photo_result(42))
    result = await send_card(
        fake_bot, chat_id=1, rendered=rendered, thumbnail_path=thumbnail,
        checking_message_id=CHECKING_ID,
    )
    assert result == (42, True)
    photos = fake_transport.calls_to("sendPhoto")
    assert len(photos) == 1
    assert photos[0].parameters["caption"] == rendered.text
    assert "parse_mode" not in photos[0].parameters
    markup = photos[0].parameters["reply_markup"]
    if isinstance(markup, str):
        import json

        markup = json.loads(markup)
    assert [row[0]["text"] for row in markup["inline_keyboard"]] == [
        "Video", "Video (no sound)", "Audio only",
    ]
    deletes = fake_transport.calls_to("deleteMessage")
    assert [call.parameters["message_id"] for call in deletes] == [CHECKING_ID]
    methods = [call.method for call in fake_transport.calls]
    assert methods.index("sendPhoto") < methods.index("deleteMessage")
    assert not fake_transport.calls_to("sendMessage")
    assert not fake_transport.calls_to("editMessageText")


async def test_send_card_ignores_delete_failure(fake_bot, fake_transport, youtube, thumbnail) -> None:
    from openmedia.bot import build_card, send_card

    meta, choice_set = youtube
    rendered = build_card(REQUEST_ID, meta, choice_set)
    fake_transport.queue_result("sendPhoto", photo_result(43))
    fake_transport.queue_error("deleteMessage", "Bad Request: message to delete not found")
    result = await send_card(
        fake_bot, chat_id=1, rendered=rendered, thumbnail_path=thumbnail,
        checking_message_id=CHECKING_ID,
    )
    assert result == (43, True)


def assert_edited_checking_message(fake_transport, rendered) -> None:
    edits = fake_transport.calls_to("editMessageText")
    assert len(edits) == 1
    assert edits[0].parameters["message_id"] == CHECKING_ID
    assert edits[0].parameters["text"] == rendered.text
    assert "parse_mode" not in edits[0].parameters
    assert "reply_markup" in edits[0].parameters
    assert not fake_transport.calls_to("sendMessage")
    assert not fake_transport.calls_to("deleteMessage")


async def test_send_card_without_thumbnail_edits_checking_message(fake_bot, fake_transport, youtube) -> None:
    from openmedia.bot import build_card, send_card

    meta, choice_set = youtube
    rendered = build_card(REQUEST_ID, meta, choice_set)
    fake_transport.queue_result("editMessageText", message_result(CHECKING_ID, text=rendered.text))
    result = await send_card(
        fake_bot, chat_id=1, rendered=rendered, thumbnail_path=None,
        checking_message_id=CHECKING_ID,
    )
    assert result == (CHECKING_ID, False)
    assert not fake_transport.calls_to("sendPhoto")
    assert_edited_checking_message(fake_transport, rendered)


async def test_send_card_falls_back_to_edit_when_photo_fails(
    fake_bot, fake_transport, youtube, thumbnail
) -> None:
    from openmedia.bot import build_card, send_card

    meta, choice_set = youtube
    rendered = build_card(REQUEST_ID, meta, choice_set)
    fake_transport.queue_error("sendPhoto", "Bad Request: IMAGE_PROCESS_FAILED")
    fake_transport.queue_result("editMessageText", message_result(CHECKING_ID, text=rendered.text))
    result = await send_card(
        fake_bot, chat_id=1, rendered=rendered, thumbnail_path=thumbnail,
        checking_message_id=CHECKING_ID,
    )
    assert result == (CHECKING_ID, False)
    assert len(fake_transport.calls_to("sendPhoto")) == 1
    assert_edited_checking_message(fake_transport, rendered)

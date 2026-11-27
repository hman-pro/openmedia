"""A Telegram user-API client that plays the user's side of a conversation with the bot.

One `BotChat.exchange` sends a message, optionally taps a card button, and waits until the
bot's latest message is no longer progress. Results carry message texts (links redacted),
button labels, tap answers and received files (attributes, size, sha256), never links or
Telegram identifiers.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import time
from dataclasses import dataclass, field
from typing import Any

from telethon import TelegramClient, events
from telethon.tl.types import (
    DocumentAttributeAnimated,
    DocumentAttributeFilename,
    DocumentAttributeVideo,
    MessageMediaDocument,
    MessageMediaPhoto,
)


URL = re.compile(r"https?://\S+")
INSTAGRAM_SPACING_SECONDS = 60.0  # keep anonymous Instagram traffic sparse between cases


def redact(text: str | None) -> str:
    return URL.sub("<url>", text or "")


@dataclass
class ReceivedFile:
    kind: str  # video | gif | audio | voice | document
    mime: str
    size: int
    caption: str
    filename: str | None
    supports_streaming: bool | None
    animated: bool
    data: bytes = field(repr=False, default=b"")

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.data).hexdigest()


@dataclass
class Exchange:
    events: list[dict[str, Any]] = field(default_factory=list)
    buttons: list[str] = field(default_factory=list)
    choice: str | None = None
    tap_answers: list[str | None] = field(default_factory=list)
    files: list[ReceivedFile] = field(default_factory=list)
    timed_out: bool = False
    card: Any = field(default=None, repr=False)
    card_seconds: float | None = None

    @property
    def card_title(self) -> str | None:
        """First line of the card, which is the title for cards that show one."""
        texts = [e["text"] for e in self.events if self.card is not None and e["id"] == self.card.id]
        return texts[0].splitlines()[0] if texts and texts[0] else None

    @property
    def final_text(self) -> str:
        return self.events[-1]["text"] if self.events else ""

    @property
    def final_status(self) -> str:
        """Last line of the last bot message: the status line or the reply text."""
        lines = self.final_text.splitlines()
        return lines[-1] if lines else ""


def _file(message: Any, data: bytes) -> ReceivedFile:
    document = message.media.document
    filename = None
    streaming = None
    animated = False
    for attribute in document.attributes:
        if isinstance(attribute, DocumentAttributeFilename):
            filename = attribute.file_name
        elif isinstance(attribute, DocumentAttributeVideo):
            streaming = attribute.supports_streaming
        elif isinstance(attribute, DocumentAttributeAnimated):
            animated = True
    kind = ("video" if message.video else "gif" if message.gif else "audio" if message.audio
            else "voice" if message.voice else "document")
    return ReceivedFile(kind=kind, mime=document.mime_type, size=document.size,
                        caption=message.message or "", filename=filename,
                        supports_streaming=streaming, animated=animated, data=data)


class BotChat:
    """The private chat between the test account and the bot under test."""

    def __init__(self, client: TelegramClient, bot: Any):
        self.client = client
        self.bot = bot
        self._queue: asyncio.Queue = asyncio.Queue()
        self._last_instagram = -1e9

    async def start(self) -> None:
        self.client.add_event_handler(self._new, events.NewMessage(chats=self.bot, incoming=True))
        self.client.add_event_handler(self._edit, events.MessageEdited(chats=self.bot, incoming=True))
        await self.client.get_me()  # starts the update stream

    async def _new(self, event: Any) -> None:
        self._queue.put_nowait((time.monotonic(), "new", event.message))

    async def _edit(self, event: Any) -> None:
        self._queue.put_nowait((time.monotonic(), "edit", event.message))

    async def instagram_pause(self) -> None:
        await asyncio.sleep(max(0.0, INSTAGRAM_SPACING_SECONDS - (time.monotonic() - self._last_instagram)))
        self._last_instagram = time.monotonic()

    async def exchange(
        self,
        text: str,
        *,
        prefer: tuple[str, ...] = (),
        tap: bool = True,
        tap_delay: float = 0.8,
        double_tap: bool = False,
        download: bool = True,
        timeout: float = 420.0,
        quiet: float = 6.0,
    ) -> Exchange:
        """Send `text`, tap the first preferred label on the card, and wait for the outcome.

        Finished when the bot's latest message is not progress (does not end in "…") and
        nothing else arrives for `quiet` seconds, or after `timeout`. `tap_delay` keeps taps
        human-like; 0 taps as soon as the card arrives.
        """
        while not self._queue.empty():
            self._queue.get_nowait()
        result = Exchange()
        started = time.monotonic()
        sent = await self.client.send_message(self.bot, text, link_preview=False)
        delivered: list[Any] = []
        done_at: float | None = None
        deadline = started + timeout
        while True:
            wait = (done_at if done_at is not None else deadline) - time.monotonic()
            if wait <= 0:
                result.timed_out = done_at is None
                break
            try:
                arrived, kind, message = await asyncio.wait_for(self._queue.get(), wait)
            except TimeoutError:
                result.timed_out = done_at is None
                break
            if message.id <= sent.id:
                continue
            body = message.message or ""
            rows = getattr(message.reply_markup, "rows", None) if message.reply_markup else None
            labels = [button.text for row in rows for button in row.buttons] if rows else []
            result.events.append({"t": round(arrived - started, 3), "kind": kind, "id": message.id,
                                  "text": redact(body), "buttons": labels})
            if isinstance(message.media, MessageMediaDocument):
                delivered.append(message)
            if labels and result.card is None:
                result.card, result.buttons = message, labels
                result.card_seconds = round(arrived - started, 3)
                if tap:
                    await asyncio.sleep(tap_delay)
                    result.choice = next((p for p in prefer if p in labels), labels[0])
                    taps = [message.click(text=result.choice) for _ in range(2 if double_tap else 1)]
                    answers = await asyncio.gather(*taps, return_exceptions=True)
                    result.tap_answers = [type(a).__name__ if isinstance(a, BaseException)
                                          else getattr(a, "message", None) for a in answers]
            elif result.card is None and isinstance(message.media, MessageMediaPhoto):
                result.card = message  # a thumbnail card without buttons (automatic choice)
            progress = body.rstrip().endswith("…") or bool(labels and tap)
            done_at = None if progress else time.monotonic() + quiet
        for message in delivered:
            data = await self.client.download_media(message, file=bytes) if download else b""
            result.files.append(_file(message, data))
        return result

"""Telegram-facing parsing and presentation kept separate from source adapters."""

from __future__ import annotations

from dataclasses import dataclass
import asyncio
from pathlib import Path
import re
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity
from telegram.error import BadRequest
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, filters

from openmedia import diagnostics
from openmedia.choices import ChoiceSet, kind_of
from openmedia.models import DownloadRequest, MediaMetadata
from openmedia.presentation import MAX_CAPTION_CHARACTERS, card_text, choice_label
from openmedia.sources import (
    _BARE_SUPPORTED_HOST,
    _SCHEME,
    ErrorCategory,
    SourceAdapterError,
    SourceRoute,
    recognize_source_url,
    supported_links,
    supported_urls_in_text,
)


PRIVATE_CHAT_GUIDANCE = "Please send the link in a private chat with this bot."
ONE_LINK_GUIDANCE = "Send exactly one supported public YouTube, LinkedIn, or Instagram link."
HELP_TEXT = (
    "Send one public YouTube video, LinkedIn post, or Instagram post in this private chat. "
    "Videos: pick Video, Video (no sound), or Audio only. Pictures are sent as-is."
)
# A refusal record keeps at most this many raw link candidates, each cut to this length
# (004 data-model "Refusal record").
REFUSAL_MAX_LINKS = 5
REFUSAL_MAX_LINK_CHARACTERS = 2_048
# Only the selection payload exists; the 001 ``p:`` page payload is malformed (003 contract).
_CALLBACK = re.compile(r"^s:([0-9a-f]{32}):(0|[1-9][0-9]{0,9})$")


def failure_message(category: ErrorCategory | str, *, stage: str) -> str:
    error = ErrorCategory(category)
    if error is ErrorCategory.UNSUPPORTED_URL:
        return "Send one supported public media link."
    if error is ErrorCategory.UNSUPPORTED_COLLECTION:
        return "Only one finished media item is supported. Send a single-item link."
    if error is ErrorCategory.UNAVAILABLE:
        return "That content is not publicly available. Send another public link."
    if error is ErrorCategory.NO_FORMATS:
        return "There is no downloadable native option. Send another public link."
    if error is ErrorCategory.FORMAT_UNAVAILABLE:
        if stage == "audio":
            return "The source has no downloadable native audio-only option. Choose a video or send another link."
        return "The selected native format changed or is unavailable. Submit the link again."
    if error is ErrorCategory.TOO_LARGE:
        if stage == "checking":
            return (
                "None of the available choices fits the current delivery limit, so nothing "
                "can be sent. Send another public link."
            )
        # After selection the preview is already closed, so there is nothing left to choose.
        return (
            "The selected file exceeds the delivery limit. Submit the link again to review "
            "the current choices."
        )
    if error is ErrorCategory.RATE_LIMITED:
        return "The source is busy. Retry the public link later."
    if error is ErrorCategory.TIMEOUT:
        return f"The {stage} stage timed out. Retry the link later."
    if error is ErrorCategory.STORAGE_EXHAUSTED:
        return f"The {stage} stage ran out of temporary space. Retry the link later."
    if error is ErrorCategory.UNSAFE_DESTINATION:
        return "That source destination cannot be accessed safely. Send another public link."
    if error is ErrorCategory.INVALID_SOURCE_RESPONSE:
        return "The source returned an unsupported response. Submit the link again later."
    if error is ErrorCategory.SHORT_LINK_UNRESOLVED:
        return "That LinkedIn link could not be opened. Send the post's full linkedin.com address."
    if error is ErrorCategory.SHORT_LINK_NOT_POST:
        return "That LinkedIn link does not lead to a supported post. Send a public LinkedIn post link."
    return f"The {stage} stage failed. Retry the link later."


class InputError(ValueError):
    """An input problem whose message is suitable for Telegram."""


@dataclass(frozen=True, slots=True)
class RenderedCard:
    text: str
    keyboard: InlineKeyboardMarkup | None


@dataclass(frozen=True, slots=True)
class CallbackAction:
    action: str
    request_id: str
    index: int


def parse_callback_data(data: str) -> CallbackAction:
    if len(data.encode("utf-8")) > 64:
        raise InputError("This choice is invalid. Please submit the link again.")
    match = _CALLBACK.fullmatch(data)
    if match is None:
        raise InputError("This choice is invalid. Please submit the link again.")
    index = int(match.group(2))
    if index > 2_147_483_647:
        raise InputError("This choice is invalid. Please submit the link again.")
    return CallbackAction("s", match.group(1), index)


def message_link_candidates(message: Any) -> tuple[str, ...]:
    """Raw link candidates from a message, supported or not, in message order.

    Telegram URL/text-link entities are authoritative whenever the message carries any: a
    ``text_link`` hides its URL behind display text, and Telegram marks scheme-less links as
    ``url`` entities. Without entities, each whitespace-separated token that holds ``://`` or
    names a supported host bare is one candidate. The rest of the text is never returned.
    """
    entities = getattr(message, "entities", None) or ()
    kinds = (MessageEntity.URL, MessageEntity.TEXT_LINK)
    if any(entity.type in kinds for entity in entities):
        parsed = message.parse_entities(list(kinds))
        return tuple(
            entity.url if entity.type == MessageEntity.TEXT_LINK else value
            for entity, value in parsed.items()
            if entity.type != MessageEntity.TEXT_LINK or entity.url
        )
    candidates: list[str] = []
    for token in (getattr(message, "text", None) or "").split():
        if "://" in token:
            scheme = _SCHEME.search(token)
            candidates.append(token[scheme.start():] if scheme is not None else token)
        elif _BARE_SUPPORTED_HOST.match(bare := token.lstrip("(<[{\"'")):
            candidates.append(bare)
    return tuple(candidates)


def message_links(message: Any) -> tuple[str, ...]:
    """Supported-platform links among the message's link candidates, in order."""
    return supported_links(message_link_candidates(message))


def refusal_reason(
    chat_type: str, candidates: tuple[str, ...], links: tuple[str, ...], exc: BaseException | None
) -> str:
    """Why a message was turned away, by the data-model "Refusal record" rules in order."""
    if chat_type != "private" and links:
        return "not_private"
    if not candidates:
        return "no_link"
    if not links:
        return "unsupported_link"
    if len(links) > 1:
        return "too_many_links"
    if isinstance(exc, SourceAdapterError):
        return ErrorCategory(exc.category).value
    return ErrorCategory.UNSUPPORTED_URL.value


def _record_refusal(
    chat: Any, user: Any, candidates: tuple[str, ...], links: tuple[str, ...],
    exc: BaseException | None = None,
) -> None:
    # Only the diagnostic logger may see links and identifiers; never pass message text.
    diagnostics.event(
        "refused",
        origin="input",
        reason=refusal_reason(chat.type, candidates, links, exc),
        links=[link[:REFUSAL_MAX_LINK_CHARACTERS] for link in candidates[:REFUSAL_MAX_LINKS]],
        chat_id=chat.id,
        user_id=user.id,
    )


def parse_link_message(
    text: str, *, chat_type: str, links: tuple[str, ...] | None = None
) -> SourceRoute:
    if chat_type != "private":
        raise InputError(PRIVATE_CHAT_GUIDANCE)
    urls = supported_urls_in_text(text) if links is None else supported_links(links)
    if len(urls) != 1:
        raise InputError(ONE_LINK_GUIDANCE)
    return recognize_source_url(urls[0])


def build_card(
    request_id: str,
    metadata: MediaMetadata,
    choice_set: ChoiceSet,
    status: str | None = None,
) -> RenderedCard:
    """Plain-text card plus one button per kept choice; no keyboard for an automatic choice."""
    text = card_text(metadata, choice_set, status)
    if choice_set.automatic:
        return RenderedCard(text, None)
    rows = []
    for option in choice_set.options:
        data = f"s:{request_id}:{option.option_id}"
        if len(data.encode("utf-8")) > 64:
            raise ValueError("callback data exceeds Telegram's 64-byte boundary")
        rows.append([InlineKeyboardButton(choice_label(kind_of(option)), callback_data=data)])
    return RenderedCard(text, InlineKeyboardMarkup(rows) if rows else None)


async def send_card(
    bot: Any,
    *,
    chat_id: int,
    rendered: RenderedCard,
    thumbnail_path: Path | None,
    checking_message_id: int,
) -> tuple[int, bool]:
    """Show the card on the request's one status surface; return ``(message_id, is_caption)``.

    With a thumbnail the card becomes a photo caption and ``Checking link…`` is deleted (best
    effort). Without one, or when the photo upload fails, ``Checking link…`` is edited into
    the card. The thumbnail is a worker-provided local file, never a URL for Telegram to fetch.
    """
    if thumbnail_path is not None:
        photo_id: int | None = None
        try:
            with Path(thumbnail_path).open("rb") as thumbnail:
                message = await bot.send_photo(
                    chat_id=chat_id,
                    photo=thumbnail,
                    caption=rendered.text,
                    reply_markup=rendered.keyboard,
                )
            photo_id = int(message.message_id)
        except Exception:
            photo_id = None
        if photo_id is not None:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=checking_message_id)
            except Exception:
                pass
            return photo_id, True
    await bot.edit_message_text(
        chat_id=chat_id,
        message_id=checking_message_id,
        text=rendered.text,
        reply_markup=rendered.keyboard,
    )
    return checking_message_id, False


def _not_modified(exc: BaseException) -> bool:
    return isinstance(exc, BadRequest) and "message is not modified" in str(exc).lower()


def _status_caption(prefix: str | None, text: str) -> str:
    if not prefix:
        return text[:MAX_CAPTION_CHARACTERS]
    # The status line is never cut; only the card text above it gives way to the caption cap.
    room = MAX_CAPTION_CHARACTERS - len(text) - 1
    if len(prefix) > room:
        prefix = prefix[: max(0, room - 1)].rstrip() + "…"
    return f"{prefix}\n{text}"


async def update_status(bot: Any, request: DownloadRequest, text: str) -> None:
    """Edit the request's one status surface in place (contracts/telegram-bot.md, research R6).

    A photo card keeps its card text above the status line. "Message is not modified" is
    ignored; any other edit failure, or a request with no status message yet, sends one new
    plain message, which becomes the surface.
    """
    if request.status_message_id is None:
        await _replace_status_message(bot, request, text)
        return
    try:
        if request.status_is_caption:
            await bot.edit_message_caption(
                chat_id=request.chat_id,
                message_id=request.status_message_id,
                caption=_status_caption(request.status_prefix, text),
            )
        else:
            await bot.edit_message_text(
                chat_id=request.chat_id,
                message_id=request.status_message_id,
                text=text,
            )
        return
    except Exception as exc:
        if _not_modified(exc):
            return
    await _replace_status_message(bot, request, text)


async def _replace_status_message(bot: Any, request: DownloadRequest, text: str) -> None:
    message = await bot.send_message(chat_id=request.chat_id, text=text)
    request.status_message_id = int(message.message_id)
    request.status_is_caption = False


class BotHandlers:
    """Short Telegram handlers; long work is scheduled through the application."""

    def __init__(self, workflow: Any) -> None:
        self.workflow = workflow

    async def help(self, update: Any, context: Any) -> None:
        message = update.effective_message
        if message is not None:
            await message.reply_text(HELP_TEXT)

    async def message(self, update: Any, context: Any) -> None:
        # Edited messages never create new work.
        if update.edited_message is not None:
            return
        message = update.effective_message
        user = update.effective_user
        chat = update.effective_chat
        if message is None or user is None or chat is None:
            return
        candidates = message_link_candidates(message)
        links = supported_links(candidates)
        if chat.type != "private":
            # Ordinary group chatter is ignored; only a shared link earns the private-chat
            # pointer, and nothing from a group is ever inspected or previewed.
            if links:
                _record_refusal(chat, user, candidates, links)
                await message.reply_text(PRIVATE_CHAT_GUIDANCE)
            return
        try:
            parse_link_message(message.text or "", chat_type=chat.type, links=links)
        except Exception as exc:
            _record_refusal(chat, user, candidates, links, exc)
            if isinstance(exc, InputError):
                text = str(exc)
            elif isinstance(exc, SourceAdapterError):
                text = failure_message(exc.category, stage=exc.stage)
            else:
                text = ONE_LINK_GUIDANCE
            await message.reply_text(text)
            return
        context.application.create_task(
            self._submit(update, context, links),
            update=update,
            name="openmedia-inspect",
        )

    async def _submit(self, update: Any, context: Any, links: tuple[str, ...] | None = None) -> None:
        from openmedia.coordinator import WorkflowBusy

        try:
            await self.workflow.submit(
                user_id=update.effective_user.id,
                chat_id=update.effective_chat.id,
                text=update.effective_message.text or "",
                chat_type=update.effective_chat.type,
                links=message_links(update.effective_message) if links is None else links,
            )
        except WorkflowBusy as busy:
            await update.effective_message.reply_text(self._admission_feedback(busy.outcome))
        except Exception as exc:
            # A failure after admission was already reported by the workflow's notifier;
            # replying here too would send the user the same failure twice.
            if getattr(self.workflow, "notify_failure", None) is not None:
                return
            if isinstance(exc, SourceAdapterError):
                text = failure_message(exc.category, stage=exc.stage)
            else:
                text = "I could not check that public item. Please send another public link."
            await update.effective_message.reply_text(text)

    async def callback(self, update: Any, context: Any) -> None:
        from openmedia.coordinator import SelectionOutcome

        query = update.callback_query
        if query is None:
            return
        try:
            action = parse_callback_data(query.data or "")
        except InputError as exc:
            await query.answer(str(exc), show_alert=True)
            return
        message = query.message
        if message is None:
            await query.answer("Submit the link again.", show_alert=True)
            return
        selection = await self.workflow.registry.claim_selection(
            action.request_id,
            user_id=query.from_user.id,
            chat_id=message.chat.id,
            preview_message_id=message.message_id,
            option_id=action.index,
        )
        if (
            selection.outcome is not SelectionOutcome.ACCEPTED
            or selection.request is None
            or selection.option is None
        ):
            await query.answer(self._selection_feedback(selection.outcome), show_alert=True)
            return
        # There must be no awaited Telegram operation between reservation and supervision.
        job = self.workflow.process_claimed(selection.request, selection.option)
        try:
            context.application.create_task(job, update=update, name="openmedia-download")
        except BaseException:
            job.close()
            await self.workflow.registry.finalize(selection.request.request_id, state="failed")
            raise
        # No confirmation message: the callback answer is a toast, the keyboard goes at once so
        # a second tap cannot land before the workflow's first edit, and `<Label> — downloading…`
        # comes from the workflow's `downloading` stage on the card itself (003 "Callbacks").
        label = choice_label(kind_of(selection.option))
        for action in (
            lambda: query.answer(label),
            lambda: query.edit_message_reply_markup(reply_markup=None),
        ):
            try:
                async with asyncio.timeout(2):
                    await action()
            except Exception:
                pass

    @staticmethod
    def _admission_feedback(outcome: Any) -> str:
        """Busy guidance per the contract table: the user's own work is not service load."""
        from openmedia.coordinator import AdmissionOutcome

        if outcome is AdmissionOutcome.USER_BUSY:
            return (
                "Your current request is still processing. Please wait for it to finish "
                "before sending another link."
            )
        if outcome is AdmissionOutcome.INSTAGRAM_BUSY:
            return "Instagram is busy right now. Please retry later; your link was not queued."
        return "The service is busy right now. Please retry later; your link was not queued."

    @staticmethod
    def _selection_feedback(outcome: Any) -> str:
        from openmedia.coordinator import SelectionOutcome

        if outcome in {SelectionOutcome.WORK_BUSY, SelectionOutcome.INSTAGRAM_BUSY}:
            return "The service or source is busy. Your choices remain available; retry shortly."
        if outcome is SelectionOutcome.INVALID_OPTION:
            return "That option is unavailable. Use a current choice."
        if outcome is SelectionOutcome.COMPLETED:
            return "That request is already completed; no duplicate download was started."
        if outcome is SelectionOutcome.PROCESSING:
            return "That request is already processing. Please wait; no duplicate download was started."
        if outcome is SelectionOutcome.EXPIRED:
            return "Those choices expired. Submit the link again."
        if outcome is SelectionOutcome.REPLACED:
            return "Those choices were replaced. Submit the link again for current choices."
        # Foreign and missing requests intentionally receive the same response.
        return "This choice is stale. Submit the link again for current choices."


def register_handlers(application: Any, workflow: Any) -> BotHandlers:
    handlers = BotHandlers(workflow)
    application.add_handler(CommandHandler(["start", "help"], handlers.help))
    application.add_handler(CallbackQueryHandler(handlers.callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.message))
    return handlers

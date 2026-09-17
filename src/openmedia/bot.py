"""Telegram-facing parsing and presentation kept separate from source adapters."""

from __future__ import annotations

from dataclasses import dataclass
import asyncio
from pathlib import Path
import re
from typing import Any

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, MessageEntity
from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler, filters

from openmedia.models import Availability, FormatOption, MediaMetadata
from openmedia.presentation import option_label, sort_options
from openmedia.sources import (
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
    "Send one public YouTube video, LinkedIn video/image post, or Instagram video/image "
    "post in this private chat. I will show native choices before downloading anything."
)
_CALLBACK = re.compile(r"^(s|p):([0-9a-f]{32}):(0|[1-9][0-9]{0,9})$")


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
    return f"The {stage} stage failed. Retry the link later."


class InputError(ValueError):
    """An input problem whose message is suitable for Telegram."""


@dataclass(frozen=True, slots=True)
class RenderedPreview:
    text: str
    keyboard: InlineKeyboardMarkup
    page: int
    page_count: int


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
    index = int(match.group(3))
    if index > 2_147_483_647:
        raise InputError("This choice is invalid. Please submit the link again.")
    return CallbackAction(match.group(1), match.group(2), index)


def message_links(message: Any) -> tuple[str, ...]:
    """Supported-platform links from Telegram URL/text-link entities, else from plain text.

    A ``text_link`` hides its URL behind display text, and Telegram marks scheme-less links
    as ``url`` entities, so entities are authoritative whenever the message carries any.
    """
    entities = getattr(message, "entities", None) or ()
    kinds = (MessageEntity.URL, MessageEntity.TEXT_LINK)
    if any(entity.type in kinds for entity in entities):
        parsed = message.parse_entities(list(kinds))
        return supported_links(
            entity.url if entity.type == MessageEntity.TEXT_LINK else value
            for entity, value in parsed.items()
            if entity.type != MessageEntity.TEXT_LINK or entity.url
        )
    return supported_urls_in_text(getattr(message, "text", None) or "")


def parse_link_message(
    text: str, *, chat_type: str, links: tuple[str, ...] | None = None
) -> SourceRoute:
    if chat_type != "private":
        raise InputError(PRIVATE_CHAT_GUIDANCE)
    urls = supported_urls_in_text(text) if links is None else supported_links(links)
    if len(urls) != 1:
        raise InputError(ONE_LINK_GUIDANCE)
    return recognize_source_url(urls[0])


def selected_label(option: FormatOption) -> str:
    """The numbered label a user saw in the preview, used to confirm their choice."""
    return f"{option.option_id + 1}. {option_label(option)}"


def _duration(seconds: float) -> str:
    total = int(seconds)
    minutes, second = divmod(total, 60)
    hours, minute = divmod(minutes, 60)
    if hours:
        return f"{hours:d}:{minute:02d}:{second:02d}"
    return f"{minute:d}:{second:02d}"


def build_preview(
    *,
    request_id: str,
    metadata: MediaMetadata,
    options: tuple[FormatOption, ...] | list[FormatOption],
    page: int = 0,
    page_size: int = 8,
) -> RenderedPreview:
    if page_size != 8:
        raise ValueError("Telegram preview pages contain exactly eight choices")
    selectable = [
        option for option in sort_options(options) if option.availability is Availability.SELECTABLE
    ]
    if not selectable:
        raise SourceAdapterError(ErrorCategory.TOO_LARGE if options else ErrorCategory.NO_FORMATS, stage="checking")
    page_count = (len(selectable) + page_size - 1) // page_size
    if page < 0 or page >= page_count:
        raise ValueError("preview page is out of range")
    start = page * page_size
    visible = selectable[start : start + page_size]

    lines = [f"Platform: {metadata.platform.title()}", f"Source: {metadata.canonical_url}"]
    if metadata.title_or_caption is not None:
        lines.append(f"Title: {metadata.title_or_caption[:500]}")
    if metadata.creator is not None:
        lines.append(f"Creator: {metadata.creator[:200]}")
    if metadata.duration_seconds is not None:
        lines.append(f"Duration: {_duration(metadata.duration_seconds)}")
    lines.append("")
    lines.append("Choose one native format:")
    for option in visible:
        lines.append(selected_label(option))
    if metadata.media_kind == "video" and not any(option.media_type == "audio" for option in options):
        lines.append("The source has no downloadable native audio-only option.")
    excluded = [option for option in options if option.availability is Availability.EXCLUDED]
    for option in excluded[:4]:
        lines.append(f"Unavailable: {option_label(option)} — {option.unavailable_reason}")
    if len(excluded) > 4:
        # Keep the message short, but never let an excluded choice go unexplained.
        reasons = "; ".join(dict.fromkeys(str(option.unavailable_reason) for option in excluded[4:]))
        lines.append(f"{len(excluded) - 4} more choices are unavailable: {reasons[:300]}")

    rows = [
        [
            InlineKeyboardButton(
                str(option.option_id + 1),
                callback_data=f"s:{request_id}:{option.option_id}",
            )
        ]
        for option in visible
    ]
    navigation: list[InlineKeyboardButton] = []
    if page > 0:
        navigation.append(
            InlineKeyboardButton("Previous", callback_data=f"p:{request_id}:{page - 1}")
        )
    if page + 1 < page_count:
        navigation.append(
            InlineKeyboardButton("Next", callback_data=f"p:{request_id}:{page + 1}")
        )
    if navigation:
        rows.append(navigation)
    keyboard = InlineKeyboardMarkup(rows)
    for row in keyboard.inline_keyboard:
        for button in row:
            if button.callback_data is None or len(button.callback_data.encode("utf-8")) > 64:
                raise ValueError("callback data exceeds Telegram's 64-byte boundary")
    return RenderedPreview("\n".join(lines)[:4096], keyboard, page, page_count)


async def send_preview(
    bot: Any,
    *,
    chat_id: int,
    rendered: RenderedPreview,
    thumbnail_path: Path | None = None,
) -> int:
    """Upload a worker-provided thumbnail path, never ask Telegram to fetch its URL."""
    if thumbnail_path is not None:
        try:
            with Path(thumbnail_path).open("rb") as thumbnail:
                await bot.send_photo(chat_id=chat_id, photo=thumbnail)
        except Exception:
            pass
    # The keyboard always belongs to a text message, so pagination and full option
    # descriptions work identically with or without an optional thumbnail.
    message = await bot.send_message(chat_id=chat_id, text=rendered.text, reply_markup=rendered.keyboard)
    return int(message.message_id)


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
        links = message_links(message)
        if chat.type != "private":
            # Ordinary group chatter is ignored; only a shared link earns the private-chat
            # pointer, and nothing from a group is ever inspected or previewed.
            if links:
                await message.reply_text(PRIVATE_CHAT_GUIDANCE)
            return
        try:
            parse_link_message(message.text or "", chat_type=chat.type, links=links)
        except Exception as exc:
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
        if action.action == "p":
            message = query.message
            if message is None:
                await query.answer("Submit the link again.", show_alert=True)
                return
            authorized = await self.workflow.registry.authorize_preview_callback(
                action.request_id,
                user_id=query.from_user.id,
                chat_id=message.chat.id,
                preview_message_id=message.message_id,
            )
            if authorized.outcome is not SelectionOutcome.ACCEPTED or authorized.request is None:
                await query.answer(self._selection_feedback(authorized.outcome), show_alert=True)
                return
            request = authorized.request
            if request.metadata is None:
                await query.answer("Submit the link again.", show_alert=True)
                return
            try:
                rendered = build_preview(
                    request_id=request.request_id,
                    metadata=request.metadata,
                    options=request.options,
                    page=action.index,
                )
            except ValueError:
                await query.answer("That page is unavailable.", show_alert=True)
                return
            await query.answer()
            await query.edit_message_text(text=rendered.text, reply_markup=rendered.keyboard)
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
        confirmation = f"Selected {selected_label(selection.option)}"[:200]
        for action in (
            lambda: query.answer(confirmation),
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

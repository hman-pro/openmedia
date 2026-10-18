"""Workflow-level flow tests for the three-choice card and automatic delivery (003 T018).

Each test drives ``MediaWorkflow`` end to end with injected callables: real yt-dlp fixture
normalization and the real choice policy, fake inspect/download/deliver around them. They
pin the coordinator contract from ``specs/003-streamlined-bot-ux`` (research R2, R8; data
model "State transitions"; contracts/telegram-bot.md "Automatic delivery").

The picture flows (003 T026) run the real Instagram and LinkedIn normalization and the real
``deliver_media`` against a recording bot, so the Telegram method, file name, and uploaded
bytes are what the runtime would send.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from openmedia.bot import failure_message
from openmedia.choices import ChoiceKind, kind_of
from openmedia.coordinator import MediaWorkflow, RequestRegistry, WorkflowError
from openmedia.delivery import deliver_media
from openmedia.models import DeliveryResult, FormatOption, MediaMetadata, MediaType, RequestState
from openmedia.sources import DownloadResult, ErrorCategory, InspectResult, SourceAdapterError
from openmedia.sources.instagram import normalize_post
from openmedia.sources.linkedin import parse_embed
from openmedia.sources.ytdlp import normalize_info


FIXTURES = Path(__file__).parents[1] / "fixtures" / "ytdlp"
LIMIT = 50_000_000
CARD_MESSAGE_ID = 55


def fixture_result(name: str) -> InspectResult:
    return normalize_info(json.loads((FIXTURES / name).read_text()), max_file_bytes=LIMIT)


class Harness:
    """Injected callables plus a record of what the workflow did with them."""

    def __init__(self, tmp_path: Path, result: InspectResult) -> None:
        self.tmp_path = tmp_path
        self.result = result
        self.registry = RequestRegistry()
        self.calls: list[Any] = []
        self.statuses: list[str] = []
        self.cards: list[Any] = []
        self.downloads: list[FormatOption] = []
        self.delivered: list[tuple[FormatOption, DownloadResult]] = []
        self.failures: list[DeliveryResult] = []
        self.registry_calls: list[str] = []
        self.registry_kwargs: list[tuple[str, dict[str, Any]]] = []
        self.on_card = None
        self._spy_registry()

    def _spy_registry(self) -> None:
        registry = self.registry
        for name in ("publish_preview", "publish_and_claim"):
            original = getattr(registry, name)

            def spy(*args: Any, _name: str = name, _original: Any = original, **kwargs: Any) -> Any:
                self.registry_calls.append(_name)
                self.registry_kwargs.append((_name, dict(kwargs)))
                return _original(*args, **kwargs)

            setattr(registry, name, spy)

    async def inspect(self, request):
        self.calls.append("inspect")
        return self.result

    async def preview(self, request, result, choice_set):
        self.calls.append("card")
        self.cards.append(choice_set)
        if self.on_card is not None:
            await self.on_card(request)
        return CARD_MESSAGE_ID

    async def download(self, request, option):
        self.calls.append(("download", option.source_format_id))
        self.downloads.append(option)
        path = self.tmp_path / f"selected.{option.extension}"
        path.write_bytes(b"exact-selected-bytes")
        return DownloadResult(
            path=path,
            actual_bytes=path.stat().st_size,
            media_id=request.media_id,
            source_format_id=option.source_format_id,
            media_type=option.media_type,
            extension=option.extension,
            mime_type=option.mime_type,
        )

    async def deliver(self, request, downloaded):
        assert request.state is RequestState.SENDING
        selected = request.options[request.selected_option_id]
        self.calls.append(("deliver", downloaded.source_format_id))
        self.delivered.append((selected, downloaded))
        return DeliveryResult(status="confirmed", message_id=99, actual_bytes=downloaded.actual_bytes)

    async def status(self, _request, stage):
        self.statuses.append(stage)

    async def notify_failure(self, _request, result):
        self.failures.append(result)

    def workflow(self) -> MediaWorkflow:
        return MediaWorkflow(
            self.registry,
            inspect=self.inspect,
            publish_preview=self.preview,
            download=self.download,
            deliver=self.deliver,
            status=self.status,
            notify_failure=self.notify_failure,
            max_file_bytes=LIMIT,
        )

    def downloaded_any(self) -> bool:
        return any(isinstance(call, tuple) and call[0] == "download" for call in self.calls)


def assert_video_path(harness: Harness, source_format_id: str) -> None:
    """The file reached delivery as a `video` kind choice, which the runtime sends with sendVideo."""
    assert len(harness.delivered) == 1
    selected, downloaded = harness.delivered[0]
    assert kind_of(selected) is ChoiceKind.VIDEO
    assert downloaded.media_type == MediaType.VIDEO
    assert downloaded.source_format_id == source_format_id


async def test_youtube_card_offers_three_choices_and_video_downloads_format_18(tmp_path: Path) -> None:
    result = fixture_result("youtube-video.json")
    harness = Harness(tmp_path, result)
    workflow = harness.workflow()

    request = await workflow.submit(
        user_id=7, chat_id=77, text=result.metadata.canonical_url, chat_type="private"
    )

    assert request.state is RequestState.AWAITING_SELECTION
    assert harness.registry_calls == ["publish_preview"]
    assert not harness.downloaded_any()

    assert len(harness.cards) == 1
    card = harness.cards[0]
    assert card.automatic is False
    # Heights only, no 720p stream: tier 1 largest is 360p muxed 18; tier 2 smallest is 137.
    assert [(option.option_id, kind_of(option), option.source_format_id) for option in card.options] == [
        (0, ChoiceKind.VIDEO, "18"),
        (1, ChoiceKind.SILENT, "137"),
        (2, ChoiceKind.AUDIO, "140"),
    ]
    # The request is bound to exactly the kept choices, never the full adapter list.
    assert [option.source_format_id for option in request.options] == ["18", "137", "140"]

    delivered = await workflow.select(
        request_id=request.request_id,
        user_id=7,
        chat_id=77,
        preview_message_id=CARD_MESSAGE_ID,
        option_id=0,
    )

    assert delivered.status == "confirmed"
    assert [option.source_format_id for option in harness.downloads] == ["18"]
    assert_video_path(harness, "18")
    assert harness.statuses == ["checking", "downloading", "sending", "completed"]
    terminal = harness.registry.terminal(request.request_id)
    assert terminal is not None
    assert terminal.state is RequestState.COMPLETED


async def test_linkedin_progressive_single_video_is_claimed_and_sent_without_a_tap(tmp_path: Path) -> None:
    result = fixture_result("linkedin-video-progressive.json")
    harness = Harness(tmp_path, result)
    workflow = harness.workflow()

    request = await workflow.submit(
        user_id=8, chat_id=88, text=result.metadata.canonical_url, chat_type="private"
    )

    assert len(harness.cards) == 1
    card = harness.cards[0]
    # One kept choice: shown without a keyboard and claimed atomically (research R8).
    assert card.automatic is True
    assert len(card.options) == 1
    chosen = card.options[0]
    assert chosen.option_id == 0
    assert kind_of(chosen) is ChoiceKind.VIDEO
    # Both renditions are unknown-codec last-resort candidates; R2 breaks the tie on the
    # higher bitrate, which the adapter already binds to option_id 0 (yt-dlp format "1").
    assert chosen.source_format_id == "1"
    assert "publish_and_claim" in harness.registry_calls
    assert "publish_preview" not in harness.registry_calls

    # No callback: the download started from submit itself and the file was delivered.
    assert [option.source_format_id for option in harness.downloads] == ["1"]
    assert_video_path(harness, "1")
    assert harness.statuses == ["checking", "downloading", "sending", "completed"]
    terminal = harness.registry.terminal(request.request_id)
    assert terminal is not None
    assert terminal.state is RequestState.COMPLETED
    assert terminal.confirmed_message_id == 99


def synthetic_result(options: tuple[FormatOption, ...]) -> InspectResult:
    return InspectResult(
        metadata=MediaMetadata(
            platform="youtube",
            canonical_url="https://www.youtube.com/watch?v=abcDEF12345",
            media_id="abcDEF12345",
        ),
        options=options,
    )


def video_option(option_id: int, format_id: str, *, vcodec: str, acodec: str | None, size: int, height: int) -> FormatOption:
    return FormatOption(
        option_id=option_id,
        adapter="fixture",
        source_format_id=format_id,
        media_type="video",
        extension="mp4",
        mime_type="video/mp4",
        height=height,
        includes_audio=acodec is not None,
        size_bytes=size,
        size_kind="exact",
        transport_ref={"url": "https://cdn.invalid/v", "vcodec": vcodec, "acodec": acodec or "none"},
    )


async def assert_checking_failure(harness: Harness, category: ErrorCategory) -> None:
    workflow = harness.workflow()
    with pytest.raises(SourceAdapterError) as caught:
        await workflow.submit(
            user_id=9, chat_id=99, text="https://youtu.be/abcDEF12345", chat_type="private"
        )
    assert caught.value.category is category
    assert caught.value.stage == "checking"
    # No card and therefore no keyboard; nothing was downloaded.
    assert harness.cards == []
    assert harness.registry_calls == []
    assert not harness.downloaded_any()
    assert len(harness.failures) == 1
    failure = harness.failures[0]
    assert failure.error_category == category.value
    assert failure.failed_stage == "checking"
    assert failure.next_step == failure_message(category, stage="checking")


async def test_every_video_candidate_over_the_limit_fails_as_too_large(tmp_path: Path) -> None:
    result = synthetic_result((
        video_option(0, "22", vcodec="avc1.64001F", acodec="mp4a.40.2", size=LIMIT + 1, height=720),
        video_option(1, "136", vcodec="avc1.4d401f", acodec=None, size=LIMIT + 5, height=720),
    ))
    await assert_checking_failure(Harness(tmp_path, result), ErrorCategory.TOO_LARGE)


async def test_only_vp9_and_av1_video_fails_as_no_formats(tmp_path: Path) -> None:
    result = synthetic_result((
        video_option(0, "248", vcodec="vp9", acodec=None, size=4_000_000, height=1080),
        video_option(1, "399", vcodec="av01.0.08M.08", acodec=None, size=3_000_000, height=1080),
    ))
    await assert_checking_failure(Harness(tmp_path, result), ErrorCategory.NO_FORMATS)


async def test_automatic_claim_on_a_replaced_request_fails_at_checking(tmp_path: Path) -> None:
    result = fixture_result("linkedin-video-progressive.json")
    harness = Harness(tmp_path, result)

    async def replace_after_card(request) -> None:
        # The request stops being the active checking request after its card was sent.
        await harness.registry.finalize(request.request_id, state=RequestState.REPLACED)

    harness.on_card = replace_after_card
    workflow = harness.workflow()

    with pytest.raises(WorkflowError):
        await workflow.submit(
            user_id=10, chat_id=100, text=result.metadata.canonical_url, chat_type="private"
        )

    assert len(harness.cards) == 1
    assert harness.cards[0].automatic is True
    assert harness.registry_calls == ["publish_and_claim"]
    assert not harness.downloaded_any()
    assert harness.delivered == []
    assert "downloading" not in harness.statuses
    assert len(harness.failures) == 1
    assert harness.failures[0].failed_stage == "checking"


# --- User Story 2: pictures are sent without a card or a tap (003 T026) -----------------

CHECKING_MESSAGE_ID = 41
IMAGE_BYTES = b"\xff\xd8\xff\xe0" + b"exact-native-picture-bytes" + b"\xff\xd9"
INSTAGRAM_FIXTURES = Path(__file__).parents[1] / "fixtures" / "instagram"
LINKEDIN_FIXTURES = Path(__file__).parents[1] / "fixtures" / "linkedin"
LINKEDIN_ACTIVITY = "7505650038253965312"


def instagram_image_result(*, content_length: int | None = len(IMAGE_BYTES)) -> InspectResult:
    post = json.loads((INSTAGRAM_FIXTURES / "instagram-image-single-post.json").read_text())
    return normalize_post(post, content_type="image/jpeg", content_length=content_length)


def linkedin_image_result() -> InspectResult:
    return parse_embed(
        (LINKEDIN_FIXTURES / "linkedin-image-single.html").read_text(),
        requested_activity_id=LINKEDIN_ACTIVITY,
        fetched_url=f"https://www.linkedin.com/embed/feed/update/urn:li:share:{LINKEDIN_ACTIVITY}",
    )


class RecordingBot:
    """Stands in for ``telegram.Bot`` behind ``deliver_media``: records method, name, bytes."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.uploaded: list[bytes] = []

    async def _send(self, method: str, file_arg: str, kwargs: dict[str, Any]):
        recorded = dict(kwargs)
        self.uploaded.append(recorded.pop(file_arg).read())
        self.calls.append((method, recorded))
        return type("Message", (), {"message_id": 99, "document": object(), "video": None, "animation": None})()

    async def send_document(self, **kwargs: Any):
        return await self._send("send_document", "document", kwargs)

    async def send_video(self, **kwargs: Any):
        return await self._send("send_video", "video", kwargs)

    async def send_photo(self, **kwargs: Any):
        return await self._send("send_photo", "photo", kwargs)


class PictureHarness(Harness):
    """The runtime's `Checking link…` message ID and real delivery for picture flows."""

    def __init__(self, tmp_path: Path, result: InspectResult) -> None:
        super().__init__(tmp_path, result)
        self.bot = RecordingBot()
        self.downloaded_bytes: list[bytes] = []

    async def status(self, request, stage):
        await super().status(request, stage)
        if stage == "checking":
            # __main__ stores the `Checking link…` message ID here (T023).
            request.status_message_id = CHECKING_MESSAGE_ID

    async def download(self, request, option):
        self.calls.append(("download", option.source_format_id))
        self.downloads.append(option)
        path = self.tmp_path / f"picture.{option.extension}"
        path.write_bytes(IMAGE_BYTES)
        self.downloaded_bytes.append(path.read_bytes())
        return DownloadResult(
            path=path,
            actual_bytes=path.stat().st_size,
            media_id=request.media_id,
            source_format_id=option.source_format_id,
            media_type=option.media_type,
            extension=option.extension,
            mime_type=option.mime_type,
        )

    async def deliver(self, request, downloaded):
        assert request.state is RequestState.SENDING
        selected = request.options[request.selected_option_id]
        self.calls.append(("deliver", downloaded.source_format_id))
        self.delivered.append((selected, downloaded))
        return await deliver_media(
            self.bot,
            request=request,
            downloaded=downloaded,
            owned_directory=self.tmp_path,
            max_file_bytes=LIMIT,
            deadline=100,
            monotonic=lambda: 0,
        )


@pytest.mark.parametrize(
    ("result_factory", "extension"),
    [(instagram_image_result, "jpg"), (linkedin_image_result, "jpg")],
    ids=["instagram", "linkedin"],
)
async def test_single_picture_is_claimed_on_the_checking_message_and_sent_as_a_document(
    tmp_path: Path, result_factory, extension: str
) -> None:
    result = result_factory()
    assert result.metadata.media_kind == "image"
    harness = PictureHarness(tmp_path, result)
    workflow = harness.workflow()

    request = await workflow.submit(
        user_id=11, chat_id=111, text=result.metadata.canonical_url, chat_type="private"
    )

    # No card: the preview callable is never called for a picture (FR-008, contract
    # "Automatic delivery": the `Checking link…` message carries the status).
    assert harness.cards == []
    assert "card" not in harness.calls
    assert harness.registry_calls == ["publish_and_claim"]
    _, claim_kwargs = harness.registry_kwargs[0]
    assert request.status_message_id == CHECKING_MESSAGE_ID
    assert claim_kwargs["preview_message_id"] == request.status_message_id
    assert [option.media_type for option in claim_kwargs["options"]] == ["image"]

    # Downloaded without a tap and delivered as a document with the native extension.
    assert len(harness.downloads) == 1
    assert kind_of(harness.downloads[0]) is ChoiceKind.IMAGE
    assert harness.statuses == ["checking", "downloading", "sending", "completed"]
    assert [method for method, _ in harness.bot.calls] == ["send_document"]
    _, sent = harness.bot.calls[0]
    assert sent["chat_id"] == 111
    assert sent["filename"].endswith(f".{extension}")
    assert harness.bot.uploaded == harness.downloaded_bytes == [IMAGE_BYTES]

    terminal = harness.registry.terminal(request.request_id)
    assert terminal is not None
    assert terminal.state is RequestState.COMPLETED
    assert terminal.confirmed_message_id == 99


async def test_picture_over_the_delivery_limit_fails_as_too_large(tmp_path: Path) -> None:
    result = instagram_image_result(content_length=LIMIT + 1)
    harness = PictureHarness(tmp_path, result)
    workflow = harness.workflow()

    with pytest.raises(SourceAdapterError) as caught:
        await workflow.submit(
            user_id=12, chat_id=122, text=result.metadata.canonical_url, chat_type="private"
        )

    assert caught.value.category is ErrorCategory.TOO_LARGE
    assert caught.value.stage == "checking"
    assert harness.cards == []
    assert harness.registry_calls == []
    assert not harness.downloaded_any()
    assert harness.bot.calls == []
    assert len(harness.failures) == 1
    failure = harness.failures[0]
    assert failure.error_category == ErrorCategory.TOO_LARGE.value
    assert failure.failed_stage == "checking"
    assert failure.next_step == failure_message(ErrorCategory.TOO_LARGE, stage="checking")


# --- User Story 3: one live status surface, two bot messages per success (003 T030) ------
#
# These drive the real ``RuntimeCallbacks`` from ``openmedia.__main__`` (status, preview,
# deliver, notify_failure) over ``fake_bot``, a real ``telegram.Bot`` whose only fake part is
# the transport. Only the worker-backed inspect and download are replaced, so every Bot API
# call below is what the runtime would put on the wire (contracts/telegram-bot.md
# "Progress surface" and "Stage text"; spec SC-004).

from dataclasses import replace as dataclass_replace  # noqa: E402
from types import SimpleNamespace  # noqa: E402

from openmedia import __main__ as runtime  # noqa: E402
from openmedia.config import Settings  # noqa: E402
from tests.conftest import FAKE_BOT_TOKEN  # noqa: E402

RUNTIME_CHECKING_ID = 41
RUNTIME_PHOTO_CARD_ID = 60
RUNTIME_DELIVERED_ID = 99
SENT_METHODS = ("sendMessage", "sendPhoto", "sendVideo", "sendDocument")
EDIT_METHODS = ("editMessageText", "editMessageCaption")
UNCONFIRMED_TEXT = "could not confirm sending. Check this chat before sending the link again."


def runtime_message(message_id: int, chat_id: int, **extra: Any) -> dict[str, Any]:
    return {"message_id": message_id, "date": 0, "chat": {"id": chat_id, "type": "private"}, **extra}


class RuntimeFlow:
    """Real runtime callbacks over ``fake_bot``; fake worker-backed inspect and download."""

    def __init__(
        self,
        tmp_path: Path,
        fake_bot: Any,
        fake_transport: Any,
        result: InspectResult,
        *,
        chat_id: int,
        payload: bytes = b"exact-selected-bytes",
        download_error: BaseException | None = None,
    ) -> None:
        self.tmp_path = tmp_path
        self.transport = fake_transport
        self.result = result
        self.chat_id = chat_id
        self.payload = payload
        self.download_error = download_error
        self.registry = RequestRegistry()
        settings = Settings(telegram_bot_token=FAKE_BOT_TOKEN, work_dir=tmp_path / "work")
        self.callbacks = runtime.RuntimeCallbacks(settings, SimpleNamespace(bot=fake_bot))
        self.workflow = MediaWorkflow(
            self.registry,
            inspect=self.inspect,
            publish_preview=self.callbacks.preview,
            download=self.download,
            deliver=self.callbacks.deliver,
            status=self.callbacks.status,
            notify_failure=self.callbacks.notify_failure,
            max_file_bytes=LIMIT,
        )
        # `Checking link…` is the first sendMessage. Extra IDs keep a runtime that still sends
        # a new message per stage parseable, so the test fails on the count, not on a parse.
        fake_transport.queue_result("sendMessage", runtime_message(RUNTIME_CHECKING_ID, chat_id, text="Checking link…"))
        for extra in range(8):
            fake_transport.queue_result("sendMessage", runtime_message(200 + extra, chat_id, text="x"))
        fake_transport.queue_result("sendPhoto", runtime_message(RUNTIME_PHOTO_CARD_ID, chat_id))

    async def inspect(self, request):
        directory = self.tmp_path / "work" / request.request_id
        directory.mkdir(parents=True, exist_ok=True)
        request.work_directory = directory
        return self.result

    async def download(self, request, option):
        if self.download_error is not None:
            raise self.download_error
        path = request.work_directory / f"selected.{option.extension}"
        path.write_bytes(self.payload)
        return DownloadResult(
            path=path,
            actual_bytes=path.stat().st_size,
            media_id=request.media_id,
            source_format_id=option.source_format_id,
            media_type=option.media_type,
            extension=option.extension,
            mime_type=option.mime_type,
        )

    # -- what the chat now holds ------------------------------------------------------------

    def bot_messages(self) -> int:
        sent = sum(len(self.transport.calls_to(method)) for method in SENT_METHODS)
        return sent - len(self.transport.calls_to("deleteMessage"))

    def status_edits(self) -> list[tuple[int, str]]:
        """``(message_id, status line)`` for every status edit, card publication excluded."""
        edits = []
        for call in self.transport.calls:
            if call.method not in EDIT_METHODS:
                continue
            params = call.parameters
            if params.get("reply_markup") is not None:
                continue  # the card itself, edited from `Checking link…` with its keyboard
            body = params.get("caption") if call.method == "editMessageCaption" else params.get("text")
            edits.append((int(params["message_id"]), str(body).rsplit("\n", 1)[-1]))
        return edits


def youtube_with_thumbnail(tmp_path: Path) -> InspectResult:
    thumbnail = tmp_path / "thumbnail.jpg"
    thumbnail.write_bytes(b"\xff\xd8\xff\xe0thumb\xff\xd9")
    return dataclass_replace(fixture_result("youtube-video.json"), thumbnail_path=thumbnail)


def queue_video_sent(transport: Any, chat_id: int) -> None:
    transport.queue_result("sendVideo", runtime_message(RUNTIME_DELIVERED_ID, chat_id, video={
        "file_id": "v", "file_unique_id": "u", "width": 640, "height": 360, "duration": 1}))


async def tap_video(flow: RuntimeFlow, *, user_id: int) -> tuple[Any, DeliveryResult]:
    request = await flow.workflow.submit(
        user_id=user_id, chat_id=flow.chat_id, text=flow.result.metadata.canonical_url, chat_type="private"
    )
    assert request.state is RequestState.AWAITING_SELECTION
    delivered = await flow.workflow.select(
        request_id=request.request_id,
        user_id=user_id,
        chat_id=flow.chat_id,
        preview_message_id=request.preview_message_id,
        option_id=0,
    )
    return request, delivered


async def test_runtime_tapped_video_edits_the_card_caption_and_leaves_two_messages(
    tmp_path: Path, fake_bot: Any, fake_transport: Any
) -> None:
    flow = RuntimeFlow(tmp_path, fake_bot, fake_transport, youtube_with_thumbnail(tmp_path), chat_id=301)
    queue_video_sent(fake_transport, 301)

    request, delivered = await tap_video(flow, user_id=31)

    assert delivered.status == "confirmed"
    # Photo card replaced `Checking link…`; the card and the video are all that remain (SC-004).
    assert len(fake_transport.calls_to("sendMessage")) == 1
    assert flow.bot_messages() == 2
    assert request.status_message_id == RUNTIME_PHOTO_CARD_ID
    assert request.status_is_caption is True
    assert flow.status_edits() == [
        (RUNTIME_PHOTO_CARD_ID, "Video — downloading…"),
        (RUNTIME_PHOTO_CARD_ID, "Video — sending…"),
        (RUNTIME_PHOTO_CARD_ID, "Video — sent."),
    ]
    # Caption edits re-render the card text above the status line.
    for call in fake_transport.calls_to("editMessageCaption"):
        assert call.parameters["caption"].startswith(request.status_prefix + "\n")


async def test_runtime_automatic_video_edits_the_card_text_and_leaves_two_messages(
    tmp_path: Path, fake_bot: Any, fake_transport: Any
) -> None:
    result = fixture_result("linkedin-video-progressive.json")
    assert result.thumbnail_path is None
    flow = RuntimeFlow(tmp_path, fake_bot, fake_transport, result, chat_id=302)
    queue_video_sent(fake_transport, 302)

    request = await flow.workflow.submit(
        user_id=32, chat_id=302, text=result.metadata.canonical_url, chat_type="private"
    )

    terminal = flow.registry.terminal(request.request_id)
    assert terminal is not None and terminal.state is RequestState.COMPLETED
    # No thumbnail: `Checking link…` became the card, so it is the one status surface.
    assert len(fake_transport.calls_to("sendMessage")) == 1
    assert fake_transport.calls_to("sendPhoto") == []
    assert flow.bot_messages() == 2
    assert request.status_message_id == RUNTIME_CHECKING_ID
    assert flow.status_edits() == [
        (RUNTIME_CHECKING_ID, "Video — only version available, downloading…"),
        (RUNTIME_CHECKING_ID, "Video — sending…"),
        (RUNTIME_CHECKING_ID, "Video — sent."),
    ]


async def test_runtime_picture_edits_the_checking_message_and_leaves_two_messages(
    tmp_path: Path, fake_bot: Any, fake_transport: Any
) -> None:
    result = instagram_image_result()
    flow = RuntimeFlow(tmp_path, fake_bot, fake_transport, result, chat_id=303, payload=IMAGE_BYTES)
    fake_transport.queue_result("sendDocument", runtime_message(RUNTIME_DELIVERED_ID, 303, document={
        "file_id": "d", "file_unique_id": "u"}))

    request = await flow.workflow.submit(
        user_id=33, chat_id=303, text=result.metadata.canonical_url, chat_type="private"
    )

    terminal = flow.registry.terminal(request.request_id)
    assert terminal is not None and terminal.state is RequestState.COMPLETED
    # The `Checking link…` message and the picture document (SC-004).
    assert len(fake_transport.calls_to("sendMessage")) == 1
    assert len(fake_transport.calls_to("sendDocument")) == 1
    assert flow.bot_messages() == 2
    assert flow.status_edits() == [
        (RUNTIME_CHECKING_ID, "Picture — downloading…"),
        (RUNTIME_CHECKING_ID, "Picture — sending…"),
        (RUNTIME_CHECKING_ID, "Picture — sent."),
    ]


async def test_runtime_worker_failure_ends_on_the_same_status_surface(
    tmp_path: Path, fake_bot: Any, fake_transport: Any
) -> None:
    error = SourceAdapterError(ErrorCategory.UNAVAILABLE, stage="downloading")
    flow = RuntimeFlow(
        tmp_path, fake_bot, fake_transport, youtube_with_thumbnail(tmp_path), chat_id=304, download_error=error
    )

    request, delivered = await tap_video(flow, user_id=34)

    assert delivered.status == "failed"
    assert delivered.failed_stage == "downloading"
    next_step = failure_message(ErrorCategory.UNAVAILABLE, stage="downloading")
    assert delivered.next_step == next_step
    # The failure edits the card; no new message is sent for it.
    assert len(fake_transport.calls_to("sendMessage")) == 1
    assert fake_transport.calls_to("sendVideo") == []
    assert flow.bot_messages() == 1
    assert flow.status_edits() == [
        (RUNTIME_PHOTO_CARD_ID, "Video — downloading…"),
        (RUNTIME_PHOTO_CARD_ID, f"Video — downloading failed. {next_step}"),
    ]


async def test_runtime_unconfirmed_upload_ends_with_could_not_confirm_on_the_card(
    tmp_path: Path, fake_bot: Any, fake_transport: Any
) -> None:
    flow = RuntimeFlow(tmp_path, fake_bot, fake_transport, youtube_with_thumbnail(tmp_path), chat_id=305)
    # A 502 surfaces as NetworkError: Telegram may have accepted the body (ambiguous upload).
    fake_transport.queue_error("sendVideo", "Bad Gateway", status_code=502)

    request, delivered = await tap_video(flow, user_id=35)

    assert delivered.status == "unknown"
    assert len(fake_transport.calls_to("sendMessage")) == 1
    assert flow.status_edits() == [
        (RUNTIME_PHOTO_CARD_ID, "Video — downloading…"),
        (RUNTIME_PHOTO_CARD_ID, "Video — sending…"),
        (RUNTIME_PHOTO_CARD_ID, f"Video — {UNCONFIRMED_TEXT}"),
    ]


# --- 004 User Story 1: LinkedIn short links (004 T011) ------------------------------------
#
# A `lnkd.in/p/<code>` link is admitted under its short code, resolved inside inspection, and
# rebound to the resolved post's identity before choices are published (tasks T015; data
# model "DownloadRequest"; contracts/telegram-bot.md "Accepting a short link" and "New
# failure meanings"). A full-address request keeps the strict identity check.

from openmedia.sources import recognize_source_url  # noqa: E402
from openmedia.workers import WorkerRemoteError  # noqa: E402

SHORT_LINK = "https://lnkd.in/p/dAjqaykT"
SHORT_CODE = "dAjqaykT"
RESOLVED_ACTIVITY = "7508424761698410497"
RESOLVED_POST = (
    "https://www.linkedin.com/posts/"
    f"sample-author_sample-text-share-{RESOLVED_ACTIVITY}-2cX9/"
)


def short_link_result(*, canonical_url: str = RESOLVED_POST, media_id: str = RESOLVED_ACTIVITY) -> InspectResult:
    """The normalized progressive LinkedIn fixture as the resolved post reports it."""
    result = fixture_result("linkedin-video-progressive.json")
    metadata = dataclass_replace(result.metadata, canonical_url=canonical_url, media_id=media_id)
    return dataclass_replace(result, metadata=metadata)


class ShortLinkHarness(Harness):
    """Records the order of status and inspect, and the request identity each one saw."""

    def __init__(self, tmp_path: Path, result: InspectResult) -> None:
        super().__init__(tmp_path, result)
        self.seen_at_inspect: list[tuple[str, str, str]] = []
        self.media_id_at_download: list[str] = []

    async def status(self, request, stage):
        self.calls.append(("status", stage))
        await super().status(request, stage)

    async def inspect(self, request):
        self.seen_at_inspect.append((request.platform, request.media_id, request.source_url))
        return await super().inspect(request)

    async def download(self, request, option):
        self.media_id_at_download.append(request.media_id)
        downloaded = await super().download(request, option)
        # The worker reports the resolved post's ID; it must match the rebound request.
        return dataclass_replace(downloaded, media_id=RESOLVED_ACTIVITY)


async def submit_short_link(workflow: MediaWorkflow, *, user_id: int, chat_id: int):
    return await workflow.submit(
        user_id=user_id, chat_id=chat_id, text=SHORT_LINK, chat_type="private", links=(SHORT_LINK,)
    )


async def test_short_link_is_admitted_by_code_and_rebound_to_the_resolved_post(tmp_path: Path) -> None:
    harness = ShortLinkHarness(tmp_path, short_link_result())
    workflow = harness.workflow()

    request = await submit_short_link(workflow, user_id=41, chat_id=401)

    # Admitted under the short code with the short link as its source URL.
    assert harness.seen_at_inspect == [("linkedin", SHORT_CODE, SHORT_LINK)]
    # `Checking link…` is shown before resolution/inspection starts.
    assert harness.calls.index(("status", "checking")) < harness.calls.index("inspect")

    # From here on, exactly what the full post address produces (automatic single video).
    assert len(harness.cards) == 1
    assert harness.cards[0].automatic is True
    assert harness.registry_calls == ["publish_and_claim"]
    assert harness.statuses == ["checking", "downloading", "sending", "completed"]

    # Identity was rebound to the resolved post after inspection: the request now carries
    # the route of the inspected canonical URL (T015 sets `route.canonical_url`).
    assert request.media_id == RESOLVED_ACTIVITY
    assert request.source_url == recognize_source_url(RESOLVED_POST).canonical_url
    # The download ran under, and was validated against, the rebound ID.
    assert harness.media_id_at_download == [RESOLVED_ACTIVITY]
    assert_video_path(harness, "1")
    terminal = harness.registry.terminal(request.request_id)
    assert terminal is not None
    assert terminal.state is RequestState.COMPLETED
    assert terminal.confirmed_message_id == 99


@pytest.mark.parametrize(
    ("canonical_url", "media_id"),
    [
        ("https://www.youtube.com/watch?v=abcdefghijk", RESOLVED_ACTIVITY),
        (RESOLVED_POST, "7507745133358940161"),
    ],
    ids=["resolved-to-youtube", "linkedin-id-differs"],
)
async def test_short_link_with_a_mismatched_resolved_identity_fails_at_checking(
    tmp_path: Path, canonical_url: str, media_id: str
) -> None:
    harness = ShortLinkHarness(tmp_path, short_link_result(canonical_url=canonical_url, media_id=media_id))
    workflow = harness.workflow()

    with pytest.raises(WorkflowError, match="inspection returned a different media identity"):
        await submit_short_link(workflow, user_id=42, chat_id=402)

    assert harness.calls.count("inspect") == 1
    assert harness.cards == []
    assert harness.registry_calls == []
    assert not harness.downloaded_any()
    assert len(harness.failures) == 1
    assert harness.failures[0].failed_stage == "checking"


class FailingInspectFlow(RuntimeFlow):
    """Real runtime callbacks; the worker-backed inspect raises the given error."""

    def __init__(self, *args: Any, inspect_error: BaseException, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.inspect_error = inspect_error

    async def inspect(self, request):
        await super().inspect(request)
        raise self.inspect_error


@pytest.mark.parametrize(
    ("category", "detail", "text"),
    [
        (
            "short_link_not_post",
            "outside_linkedin",
            "That LinkedIn link does not lead to a supported post. Send a public LinkedIn post link.",
        ),
        (
            "short_link_unresolved",
            "not_found",
            "That LinkedIn link could not be opened. Send the post's full linkedin.com address.",
        ),
    ],
    ids=["not-a-post", "unresolved"],
)
async def test_short_link_resolution_failure_ends_on_the_checking_message_without_a_keyboard(
    tmp_path: Path, fake_bot: Any, fake_transport: Any, category: str, detail: str, text: str
) -> None:
    error = WorkerRemoteError(category, "inspection", detail)
    flow = FailingInspectFlow(
        tmp_path, fake_bot, fake_transport, short_link_result(), chat_id=306, inspect_error=error
    )

    with pytest.raises(WorkerRemoteError):
        await submit_short_link(flow.workflow, user_id=36, chat_id=306)

    # Only `Checking link…` was sent; no card, no photo, nothing downloaded or delivered.
    assert len(fake_transport.calls_to("sendMessage")) == 1
    assert fake_transport.calls_to("sendPhoto") == []
    assert fake_transport.calls_to("sendVideo") == []
    assert flow.bot_messages() == 1
    edits = [
        call for call in fake_transport.calls
        if call.method in EDIT_METHODS
    ]
    assert len(edits) == 1
    params = edits[0].parameters
    assert int(params["message_id"]) == RUNTIME_CHECKING_ID
    assert params.get("reply_markup") is None
    assert str(params["text"]).endswith(text)
    # The destination address never appears in what the user sees.
    assert "linkedin.com/posts" not in str(params["text"])


async def test_full_address_request_keeps_the_strict_identity_check_and_is_never_rebound(
    tmp_path: Path,
) -> None:
    full_address = f"https://www.linkedin.com/posts/sample-author_sample-text-share-{RESOLVED_ACTIVITY}-2cX9/"
    other_post = "https://www.linkedin.com/posts/other-author_other-text-share-7507745133358940161-abcd/"
    # Inspection reports a different, self-consistent post: no rebinding for a full address.
    harness = Harness(tmp_path, short_link_result(canonical_url=other_post, media_id="7507745133358940161"))
    seen: list[Any] = []
    original_inspect = harness.inspect

    async def inspect(request):
        seen.append(request)
        return await original_inspect(request)

    harness.inspect = inspect  # type: ignore[method-assign]
    workflow = harness.workflow()

    with pytest.raises(WorkflowError, match="inspection returned a different media identity"):
        await workflow.submit(user_id=43, chat_id=403, text=full_address, chat_type="private")

    assert len(seen) == 1
    request = seen[0]
    assert request.media_id == RESOLVED_ACTIVITY
    assert request.source_url == recognize_source_url(full_address).canonical_url
    assert harness.cards == []
    assert harness.registry_calls == []
    assert len(harness.failures) == 1
    assert harness.failures[0].failed_stage == "checking"


# --- 006 User Story 1: titles accompany the final native-media upload (T005) ----------

from openmedia.presentation import card_text  # noqa: E402


class TitledDeliveryHarness(Harness):
    """Real delivery boundary with recorded API kwargs and an injected clock.

    Recording before Telegram serialization distinguishes explicit ``parse_mode=None``
    from an omitted kwarg: PTB intentionally removes None values from wire parameters.
    """

    def __init__(self, tmp_path: Path, result: InspectResult, clock: Any) -> None:
        super().__init__(tmp_path, result)
        self.registry.monotonic = clock
        self.clock = clock
        self.bot = RecordingBot()
        self.preview_texts: list[str] = []

    async def status(self, request, stage):
        await super().status(request, stage)
        if stage == "checking":
            request.status_message_id = CHECKING_MESSAGE_ID

    async def preview(self, request, result, choice_set):
        self.preview_texts.append(card_text(result.metadata, choice_set))
        return await super().preview(request, result, choice_set)

    async def download(self, request, option):
        downloaded = await super().download(request, option)
        # Measured hints deliberately differ from the source listing so metadata labels
        # cannot accidentally change which dimensions/duration the player receives.
        if option.media_type is MediaType.VIDEO:
            downloaded = dataclass_replace(downloaded, width=854, height=480, duration_seconds=7.4)
        return downloaded

    async def deliver(self, request, downloaded):
        assert request.state is RequestState.SENDING
        selected = request.options[request.selected_option_id]
        self.delivered.append((selected, downloaded))
        return await deliver_media(
            self.bot,
            request=request,
            downloaded=downloaded,
            owned_directory=self.tmp_path,
            max_file_bytes=LIMIT,
            deadline=request.processing_deadline,
            duration_seconds=request.metadata.duration_seconds,
            monotonic=self.clock,
        )


@pytest.mark.parametrize(
    ("source", "choice", "expected_method", "extension", "format_id", "automatic", "has_card"),
    [
        ("youtube", ChoiceKind.VIDEO, "send_video", "mp4", "18", False, True),
        ("youtube", ChoiceKind.SILENT, "send_video", "mp4", "137", False, True),
        ("youtube", ChoiceKind.AUDIO, "send_document", "m4a", "140", False, True),
        ("linkedin", ChoiceKind.VIDEO, "send_video", "mp4", "1", True, True),
        ("instagram", ChoiceKind.VIDEO, "send_video", "mp4", "dash-1", True, True),
        ("instagram-picture", ChoiceKind.IMAGE, "send_document", "jpg", None, True, False),
        ("linkedin-picture", ChoiceKind.IMAGE, "send_document", "jpg", None, True, False),
    ],
    ids=["youtube-video", "youtube-silent-video", "youtube-audio", "linkedin-video",
         "instagram-video", "instagram-picture", "linkedin-picture"],
)
async def test_source_title_is_on_the_final_media_call_without_changing_delivery(
    tmp_path: Path, fake_clock: Any, source: str, choice: ChoiceKind,
    expected_method: str, extension: str, format_id: str | None,
    automatic: bool, has_card: bool,
) -> None:
    if source == "instagram-picture":
        result = instagram_image_result()
    elif source == "linkedin-picture":
        result = linkedin_image_result()
    else:
        fixture = {
            "youtube": "youtube-video.json",
            "linkedin": "linkedin-video-progressive.json",
            "instagram": "instagram-video.json",
        }[source]
        result = fixture_result(fixture)
    title = f"{source} Summer walk"
    result = dataclass_replace(
        result, metadata=dataclass_replace(result.metadata, title_or_caption=title)
    )
    harness = TitledDeliveryHarness(tmp_path, result, fake_clock)
    workflow = harness.workflow()
    request = await workflow.submit(
        user_id=61, chat_id=601, text=result.metadata.canonical_url, chat_type="private"
    )
    if not automatic:
        assert request.state is RequestState.AWAITING_SELECTION
        assert harness.downloads == []
        selected = next(option for option in request.options if kind_of(option) is choice)
        delivered = await workflow.select(
            request_id=request.request_id, user_id=61, chat_id=601,
            preview_message_id=CARD_MESSAGE_ID, option_id=selected.option_id,
        )
        assert delivered.status == "confirmed"
    else:
        # Automatic media require no callback or additional user action.
        assert harness.registry_calls == ["publish_and_claim"]

    assert len(harness.cards) == int(has_card)
    if has_card:
        assert harness.cards[0].automatic is automatic
        assert harness.preview_texts[0].splitlines()[0] == title
    else:
        assert harness.preview_texts == []
    assert harness.statuses == ["checking", "downloading", "sending", "completed"]
    assert len(harness.downloads) == len(harness.delivered) == 1
    selected, downloaded = harness.delivered[0]
    assert kind_of(selected) is choice
    if format_id is not None:
        assert selected.source_format_id == downloaded.source_format_id == format_id
    assert selected.extension == downloaded.extension == extension
    assert downloaded.path == tmp_path / f"selected.{extension}"
    assert downloaded.path.read_bytes() == b"exact-selected-bytes"
    assert harness.bot.uploaded == [b"exact-selected-bytes"]
    assert [method for method, _ in harness.bot.calls] == [expected_method]
    _, sent = harness.bot.calls[0]
    assert sent["chat_id"] == 601
    if expected_method == "send_video":
        assert sent["supports_streaming"] is True
        assert (sent["width"], sent["height"], sent["duration"]) == (854, 480, 7)
    else:
        assert not {"supports_streaming", "width", "height", "duration"}.intersection(sent)
    terminal = harness.registry.terminal(request.request_id)
    assert terminal is not None and terminal.state is RequestState.COMPLETED
    assert terminal.confirmed_message_id == 99
    # These assertions target the final upload, independently of the preceding card.
    assert sent.get("caption") == title
    assert sent["filename"] == f"{title}.{extension}"
    assert "parse_mode" in sent and sent["parse_mode"] is None
    assert "caption_entities" not in sent


@pytest.mark.parametrize(
    ("title", "expected_preview"),
    [("a" * 200, "a" * 200), ("b" * 201, "b" * 199 + "…"), (None, "Untitled video")],
    ids=["exactly-200", "over-200", "existing-preview-fallback"],
)
async def test_delivery_title_policy_does_not_replace_the_preview_card_title_policy(
    tmp_path: Path, fake_clock: Any, title: str | None, expected_preview: str,
) -> None:
    result = fixture_result("youtube-video.json")
    result = dataclass_replace(
        result, metadata=dataclass_replace(result.metadata, title_or_caption=title)
    )
    harness = Harness(tmp_path, result)
    harness.registry.monotonic = fake_clock
    request = await harness.workflow().submit(
        user_id=62, chat_id=602, text=result.metadata.canonical_url, chat_type="private"
    )
    assert request.state is RequestState.AWAITING_SELECTION
    assert len(harness.cards) == 1
    assert harness.downloads == []
    assert card_text(request.metadata, harness.cards[0]).splitlines()[0] == expected_preview

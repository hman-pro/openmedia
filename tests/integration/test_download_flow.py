"""Workflow-level flow tests for the three-choice card and automatic delivery (003 T018).

Each test drives ``MediaWorkflow`` end to end with injected callables: real yt-dlp fixture
normalization and the real choice policy, fake inspect/download/deliver around them. They
pin the coordinator contract from ``specs/003-streamlined-bot-ux`` (research R2, R8; data
model "State transitions"; contracts/telegram-bot.md "Automatic delivery").
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from openmedia.bot import failure_message
from openmedia.choices import ChoiceKind, kind_of
from openmedia.coordinator import MediaWorkflow, RequestRegistry, WorkflowError
from openmedia.models import DeliveryResult, FormatOption, MediaMetadata, MediaType, RequestState
from openmedia.sources import DownloadResult, ErrorCategory, InspectResult, SourceAdapterError
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
        self.on_card = None
        self._spy_registry()

    def _spy_registry(self) -> None:
        registry = self.registry
        for name in ("publish_preview", "publish_and_claim"):
            original = getattr(registry, name)

            def spy(*args: Any, _name: str = name, _original: Any = original, **kwargs: Any) -> Any:
                self.registry_calls.append(_name)
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
    assert harness.statuses == ["checking", "downloading", "sending"]
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
    assert harness.statuses == ["checking", "downloading", "sending"]
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

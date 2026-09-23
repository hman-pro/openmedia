from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter, TimedOut

from openmedia.delivery import deliver_media
from openmedia.models import DownloadRequest, FormatOption
from openmedia.sources import DownloadResult

# Each kind maps to the Telegram method that must carry it (contracts/telegram-bot.md
# "Delivery method"): both video choices play inline, audio stays a native document.
KINDS = {
    "video": dict(media_type="video", extension="mp4", mime_type="video/mp4", includes_audio=True),
    "silent": dict(media_type="video", extension="mp4", mime_type="video/mp4", includes_audio=False),
    "audio": dict(media_type="audio", extension="m4a", mime_type="audio/mp4", includes_audio=None),
}
METHOD = {"video": "send_video", "silent": "send_video", "audio": "send_document"}
FILE_ARG = {"send_video": "video", "send_document": "document"}


def selected_request(
    tmp_path: Path,
    kind: str = "video",
    *,
    width: int | None = 640,
    height: int | None = 360,
) -> tuple[DownloadRequest, DownloadResult]:
    shape = KINDS[kind]
    dims = {"width": width, "height": height} if shape["media_type"] == "video" else {}
    option = FormatOption(
        option_id=0,
        adapter="fixture",
        source_format_id="native",
        **shape,
        **dims,
    )
    request = DownloadRequest(
        request_id="0123456789abcdef0123456789abcdef",
        user_id=1,
        chat_id=2,
        source_url="https://www.youtube.com/watch?v=abcDEF12345",
        platform="youtube",
        media_id="abcDEF12345",
        state="sending",
        options=(option,),
        selected_option_id=0,
        work_directory=tmp_path,
    )
    path = tmp_path / f"selected.{shape['extension']}"
    path.write_bytes(b"fixture-native-bytes")
    result = DownloadResult(
        path,
        path.stat().st_size,
        request.media_id,
        "native",
        shape["media_type"],
        shape["extension"],
        shape["mime_type"],
    )
    return request, result


class Bot:
    """Fake Telegram bot recording which send method ran and with what arguments."""

    def __init__(self, *outcomes, carrier: str = "video") -> None:
        self.outcomes = list(outcomes)
        self.carrier = carrier
        self.calls: list[tuple[str, dict]] = []
        self.bytes: list[bytes] = []

    async def _send(self, method: str, kwargs: dict):
        recorded = dict(kwargs)
        self.bytes.append(recorded.pop(FILE_ARG[method]).read())
        self.calls.append((method, recorded))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        attributes = {"message_id": outcome, "video": None, "animation": None, "document": None}
        attributes[self.carrier] = object()
        return type("Message", (), attributes)()

    async def send_video(self, **kwargs):
        return await self._send("send_video", kwargs)

    async def send_document(self, **kwargs):
        return await self._send("send_document", kwargs)


async def deliver(bot: Bot, tmp_path: Path, kind: str = "video", **kwargs):
    request, result = selected_request(
        tmp_path,
        kind,
        width=kwargs.get("width", 640),
        height=kwargs.get("height", 360),
    )
    return await deliver_media(
        bot,
        request=request,
        downloaded=result,
        owned_directory=tmp_path,
        max_file_bytes=50_000_000,
        deadline=100,
        duration_seconds=kwargs.get("duration_seconds"),
        monotonic=kwargs.get("monotonic", lambda: 0),
        sleep=kwargs.get("sleep", asyncio.sleep),
    )


@pytest.mark.parametrize("kind", ["video", "silent"])
async def test_video_kinds_use_send_video_with_streaming_and_known_metadata(kind, tmp_path: Path) -> None:
    bot = Bot(77)
    result = await deliver(bot, tmp_path, kind, duration_seconds=12)
    assert result.status == "confirmed"
    assert result.message_id == 77
    assert [method for method, _ in bot.calls] == ["send_video"]
    _, kwargs = bot.calls[0]
    assert kwargs["chat_id"] == 2
    assert kwargs["supports_streaming"] is True
    assert kwargs["width"] == 640
    assert kwargs["height"] == 360
    assert kwargs["duration"] == 12
    assert bot.bytes == [b"fixture-native-bytes"]


@pytest.mark.parametrize("kind", ["video", "silent"])
async def test_video_metadata_is_omitted_when_unknown(kind, tmp_path: Path) -> None:
    bot = Bot(77)
    result = await deliver(bot, tmp_path, kind, width=None, height=None, duration_seconds=None)
    assert result.status == "confirmed"
    method, kwargs = bot.calls[0]
    assert method == "send_video"
    assert kwargs["supports_streaming"] is True
    for key in ("width", "height", "duration"):
        assert kwargs.get(key) is None, key


async def test_audio_uses_send_document(tmp_path: Path) -> None:
    bot = Bot(55, carrier="document")
    result = await deliver(bot, tmp_path, "audio", duration_seconds=12)
    assert result.status == "confirmed"
    assert result.message_id == 55
    assert [method for method, _ in bot.calls] == ["send_document"]
    assert "supports_streaming" not in bot.calls[0][1]
    assert bot.bytes == [b"fixture-native-bytes"]


@pytest.mark.parametrize("carrier", ["video", "animation", "document"])
async def test_send_video_confirmed_whatever_message_type_telegram_returns(carrier, tmp_path: Path) -> None:
    bot = Bot(88, carrier=carrier)
    result = await deliver(bot, tmp_path, "silent", duration_seconds=5)
    assert [method for method, _ in bot.calls] == ["send_video"]
    assert result.status == "confirmed"
    assert result.message_id == 88
    assert result.actual_bytes == len(b"fixture-native-bytes")


@pytest.mark.parametrize("kind", ["video", "silent", "audio"])
@pytest.mark.parametrize(
    ("error", "category"),
    [(BadRequest("rejected"), "telegram_rejected"), (Forbidden("blocked"), "blocked")],
)
async def test_definite_rejections_are_failed(kind, error, category, tmp_path: Path) -> None:
    bot = Bot(error)
    result = await deliver(bot, tmp_path, kind)
    assert result.status == "failed"
    assert result.error_category == category
    assert len(bot.calls) == 1
    assert bot.calls[0][0] == METHOD[kind]


@pytest.mark.parametrize("kind", ["video", "silent", "audio"])
async def test_retry_after_retries_only_inside_same_deadline(kind, tmp_path: Path) -> None:
    now = [0.0]

    async def advance(seconds: float) -> None:
        now[0] += seconds

    bot = Bot(RetryAfter(2), 88)
    result = await deliver(bot, tmp_path, kind, monotonic=lambda: now[0], sleep=advance)
    assert result.status == "confirmed"
    assert result.message_id == 88
    assert [method for method, _ in bot.calls] == [METHOD[kind], METHOD[kind]]


@pytest.mark.parametrize("kind", ["video", "silent", "audio"])
async def test_retry_after_past_deadline_is_not_retried(kind, tmp_path: Path) -> None:
    now = [0.0]

    async def advance(seconds: float) -> None:
        now[0] += seconds

    bot = Bot(RetryAfter(500), 88)
    result = await deliver(bot, tmp_path, kind, monotonic=lambda: now[0], sleep=advance)
    assert result.status == "failed"
    assert result.error_category == "rate_limited"
    assert len(bot.calls) == 1


@pytest.mark.parametrize("kind", ["video", "silent", "audio"])
@pytest.mark.parametrize("error", [NetworkError("connection lost after upload"), TimedOut("timed out")])
async def test_ambiguous_network_outcome_is_unknown_and_never_retried(kind, error, tmp_path: Path) -> None:
    bot = Bot(error, 99)
    result = await deliver(bot, tmp_path, kind)
    assert result.status == "unknown"
    assert result.error_category == "ambiguous_upload"
    assert "check" in result.next_step.lower()
    assert len(bot.calls) == 1
    assert bot.calls[0][0] == METHOD[kind]


async def test_changed_format_or_size_is_rejected_before_send(tmp_path: Path) -> None:
    request, result = selected_request(tmp_path)
    changed = DownloadResult(result.path, result.actual_bytes, result.media_id, "different", "video", "mp4", "video/mp4")
    bot = Bot(99)
    delivery = await deliver_media(
        bot,
        request=request,
        downloaded=changed,
        owned_directory=tmp_path,
        max_file_bytes=50_000_000,
        deadline=100,
        monotonic=lambda: 0,
    )
    assert delivery.status == "failed"
    assert delivery.error_category == "format_changed"
    assert bot.calls == []

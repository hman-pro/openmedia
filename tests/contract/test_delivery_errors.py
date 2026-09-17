from __future__ import annotations

from pathlib import Path

import pytest
from telegram.error import BadRequest, Forbidden, NetworkError, RetryAfter

from openmedia.delivery import deliver_document
from openmedia.models import DownloadRequest, FormatOption
from openmedia.sources import DownloadResult


def selected_request(tmp_path: Path) -> tuple[DownloadRequest, DownloadResult]:
    option = FormatOption(
        option_id=0,
        adapter="fixture",
        source_format_id="native",
        media_type="video",
        extension="mp4",
        mime_type="video/mp4",
        includes_audio=True,
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
    path = tmp_path / "selected.mp4"
    path.write_bytes(b"fixture-native-bytes")
    result = DownloadResult(path, path.stat().st_size, request.media_id, "native", "video", "mp4", "video/mp4")
    return request, result


class Bot:
    def __init__(self, *outcomes) -> None:
        self.outcomes = list(outcomes)
        self.calls = 0
        self.bytes: list[bytes] = []

    async def send_document(self, **kwargs):
        self.calls += 1
        self.bytes.append(kwargs["document"].read())
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return type("Message", (), {"message_id": outcome})()


async def deliver(bot: Bot, tmp_path: Path, **kwargs):
    request, result = selected_request(tmp_path)
    return await deliver_document(
        bot,
        request=request,
        downloaded=result,
        owned_directory=tmp_path,
        max_file_bytes=50_000_000,
        deadline=100,
        monotonic=kwargs.get("monotonic", lambda: 0),
        sleep=kwargs.get("sleep", __import__("asyncio").sleep),
    )


@pytest.mark.parametrize(
    ("error", "category"),
    [(BadRequest("rejected"), "telegram_rejected"), (Forbidden("blocked"), "blocked")],
)
async def test_definite_rejections_are_failed(error, category, tmp_path: Path) -> None:
    bot = Bot(error)
    result = await deliver(bot, tmp_path)
    assert result.status == "failed"
    assert result.error_category == category
    assert bot.calls == 1


async def test_retry_after_retries_only_inside_same_deadline(tmp_path: Path) -> None:
    now = [0.0]

    async def advance(seconds: float) -> None:
        now[0] += seconds

    bot = Bot(RetryAfter(2), 88)
    result = await deliver(bot, tmp_path, monotonic=lambda: now[0], sleep=advance)
    assert result.status == "confirmed"
    assert result.message_id == 88
    assert bot.calls == 2


async def test_ambiguous_network_outcome_is_unknown_and_never_retried(tmp_path: Path) -> None:
    bot = Bot(NetworkError("connection lost after upload"), 99)
    result = await deliver(bot, tmp_path)
    assert result.status == "unknown"
    assert "check" in result.next_step.lower()
    assert bot.calls == 1


async def test_changed_format_or_size_is_rejected_before_send(tmp_path: Path) -> None:
    request, result = selected_request(tmp_path)
    changed = DownloadResult(result.path, result.actual_bytes, result.media_id, "different", "video", "mp4", "video/mp4")
    bot = Bot(99)
    delivery = await deliver_document(
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
    assert bot.calls == 0

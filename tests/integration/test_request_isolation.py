from __future__ import annotations

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from openmedia.coordinator import (
    AdmissionOutcome,
    MediaWorkflow,
    ParentRateController,
    RequestRegistry,
    SelectionOutcome,
)
from openmedia.delivery import deliver_media
from openmedia.models import FormatOption, MediaMetadata, RequestState
from openmedia.sources import DownloadResult, InspectResult


def request(registry: RequestRegistry, user: int, platform: str = "youtube"):
    return registry.new_request(
        user_id=user,
        chat_id=user * 10,
        source_url="https://www.instagram.com/p/DdExample1/" if platform == "instagram" else f"https://www.youtube.com/watch?v=fixture{user}",
        platform=platform,
        media_id=f"fixture{user}",
    )


async def preview(registry: RequestRegistry, item, message_id: int = 5, now: float = 10) -> None:
    option = FormatOption(0, "fixture", "native", "video", "mp4", "video/mp4", includes_audio=True)
    await registry.publish_preview(
        item.request_id,
        metadata=MediaMetadata(item.platform, item.source_url, item.media_id),
        options=(option,),
        preview_message_id=message_id,
        now=now,
    )


async def test_two_users_and_global_instagram_capacity_are_isolated() -> None:
    registry = RequestRegistry(max_workers=2, max_instagram_workers=1)
    first, second = request(registry, 1, "instagram"), request(registry, 2, "instagram")
    outcomes = await asyncio.gather(registry.admit(first), registry.admit(second))
    assert sorted(item.outcome for item in outcomes) == [AdmissionOutcome.ADMITTED, AdmissionOutcome.INSTAGRAM_BUSY]
    assert registry.active_request_by_user.get(1) != registry.active_request_by_user.get(2)


async def test_duplicate_selection_and_replacement_never_publish_stale_work() -> None:
    registry = RequestRegistry()
    old = request(registry, 1)
    await registry.admit(old)
    await preview(registry, old)
    replacement = request(registry, 1)
    assert (await registry.admit(replacement)).outcome is AdmissionOutcome.REPLACED
    stale = await registry.claim_selection(old.request_id, user_id=1, chat_id=10, preview_message_id=5, option_id=0, now=11)
    assert stale.outcome is SelectionOutcome.REPLACED
    assert not await registry.is_current(old.request_id, RequestState.CHECKING)


async def test_preview_expiry_terminal_ttl_limit_and_restart_invalidation() -> None:
    now = [10.0]
    registry = RequestRegistry(selection_seconds=5, terminal_ttl=10, terminal_limit=2, monotonic=lambda: now[0])
    item = request(registry, 1)
    await registry.admit(item)
    await preview(registry, item, now=10)
    expired = await registry.claim_selection(item.request_id, user_id=1, chat_id=10, preview_message_id=5, option_id=0, now=15)
    assert expired.outcome is SelectionOutcome.EXPIRED
    for user in (2, 3):
        now[0] = 16 + user
        other = request(registry, user)
        await registry.admit(other)
        await registry.finalize(other.request_id, state=RequestState.FAILED, now=now[0])
    assert len(registry.terminal_by_id) == 2
    await registry.prune(now=30)
    assert not registry.terminal_by_id
    restarted = RequestRegistry()
    assert item.request_id not in restarted.requests_by_id
    assert restarted.terminal(item.request_id) is None


async def test_pending_capacity_is_bounded_at_one_hundred() -> None:
    registry = RequestRegistry(max_workers=101, max_pending=100)
    admitted = [await registry.admit(request(registry, user)) for user in range(100)]
    assert all(item.outcome is AdmissionOutcome.ADMITTED for item in admitted)
    assert (await registry.admit(request(registry, 101))).outcome is AdmissionOutcome.PENDING_FULL


async def test_parent_instagram_cooldown_survives_worker_events() -> None:
    now = [100.0]
    rate = ParentRateController(monotonic=lambda: now[0])
    await rate.handle_limited({"platform": "instagram", "retry_after": 60})
    reply = await rate.handle_request(
        {"platform": "instagram", "request_class": "metadata", "deadline": 200}
    )
    assert reply == {"allowed": True, "delay": 60.0}
    denied = await rate.handle_request(
        {"platform": "instagram", "request_class": "metadata", "deadline": 150}
    )
    assert denied["allowed"] is False


async def test_music_concurrent_users_busy_duplicate_callbacks_and_restart(tmp_path):
    from unittest.mock import AsyncMock
    import pytest
    from openmedia.coordinator import MediaWorkflow, WorkflowBusy
    from openmedia.models import DeliveryResult
    from openmedia.sources import DownloadResult, InspectResult

    registry = RequestRegistry(monotonic=lambda: 10)
    url = "https://music.youtube.com/watch?v=abcDEF12345"
    metadata = MediaMetadata("youtube", url, "abcDEF12345", media_kind="audio")
    option = FormatOption(0, "yt_dlp", "140", "audio", "m4a", "audio/mp4")
    arrived = [asyncio.Event(), asyncio.Event()]
    release = asyncio.Event()
    requests = {}
    downloads = []
    async def download(item, selected):
        requests[item.user_id] = item
        downloads.append((item.request_id, item.user_id, selected.source_format_id))
        arrived[item.user_id - 1].set()
        await release.wait()
        path = tmp_path / f"{item.request_id}.m4a"
        path.write_bytes(bytes([item.user_id]))
        return DownloadResult(path, 1, item.media_id, selected.source_format_id, "audio", "m4a", "audio/mp4")
    delivered = []
    async def deliver(item, result):
        delivered.append((item.user_id, result.path.read_bytes()))
        return DeliveryResult(status="confirmed", message_id=100 + item.user_id, actual_bytes=1)
    workflow = MediaWorkflow(registry, inspect=AsyncMock(return_value=InspectResult(metadata, (option,))),
        publish_preview=AsyncMock(return_value=55), download=download, deliver=deliver,
        status=AsyncMock(), max_file_bytes=50_000_000)
    first = asyncio.create_task(workflow.submit(user_id=1, chat_id=10, text=url, chat_type="private"))
    await arrived[0].wait()
    with pytest.raises(WorkflowBusy) as busy:
        await workflow.submit(user_id=1, chat_id=10, text=url, chat_type="private")
    assert busy.value.outcome is AdmissionOutcome.USER_BUSY
    second = asyncio.create_task(workflow.submit(user_id=2, chat_id=20, text=url, chat_type="private"))
    await arrived[1].wait()
    with pytest.raises(WorkflowBusy) as global_busy:
        await workflow.submit(user_id=3, chat_id=30, text=url, chat_type="private")
    assert global_busy.value.outcome is AdmissionOutcome.WORK_BUSY
    for user in (1, 2):
        with pytest.raises(WorkflowBusy):
            await workflow.select(request_id=requests[user].request_id, user_id=user,
                chat_id=user * 10, preview_message_id=55, option_id=0)
    wrong_user = await registry.claim_selection(requests[1].request_id, user_id=2,
        chat_id=20, preview_message_id=55, option_id=0)
    assert wrong_user.outcome is not SelectionOutcome.ACCEPTED
    release.set()
    completed = await asyncio.gather(first, second)
    assert len(downloads) == 2 and len({item[0] for item in downloads}) == 2
    assert sorted(delivered) == [(1, b"\x01"), (2, b"\x02")]
    assert all(item.state is RequestState.COMPLETED for item in completed)
    for item in completed:
        assert (await registry.claim_selection(item.request_id, user_id=item.user_id,
            chat_id=item.chat_id, preview_message_id=55, option_id=0)).outcome is not SelectionOutcome.ACCEPTED
        restarted = RequestRegistry(monotonic=lambda: 10)
        assert (await restarted.claim_selection(item.request_id, user_id=item.user_id,
            chat_id=item.chat_id, preview_message_id=55, option_id=0)).outcome is SelectionOutcome.NOT_FOUND
    assert registry.active_work_count == 0


# Feature 006: exercise final serialized uploads, beyond preview metadata or labels
# computed by the test. Both downloads and Bot API sends overlap without clock sleeps.
@pytest.mark.parametrize(
    "titles",
    [("Summer walk", "Winter song"), ("Shared title", "Shared title")],
    ids=["different-titles", "same-title"],
)
@pytest.mark.parametrize(
    ("media_type", "extension", "mime_type", "method"),
    [
        ("video", "mp4", "video/mp4", "sendVideo"),
        ("audio", "m4a", "audio/mp4", "sendDocument"),
    ],
    ids=["video", "audio-document"],
)
async def test_concurrent_delivery_titles_and_owned_files_remain_request_local(
    tmp_path: Path, fake_bot, fake_transport, fake_clock, monkeypatch,
    titles: tuple[str, str], media_type: str, extension: str, mime_type: str, method: str,
) -> None:
    registry = RequestRegistry(monotonic=fake_clock)
    both_downloads = asyncio.Event()
    both_uploads = asyncio.Event()
    downloads = {}
    uploads = {}
    native_bytes = {1: b"first-native-media\x00\x01", 2: b"second-native-media\x00\xff"}
    original_request = fake_transport.do_request

    async def record_upload(url, method, request_data=None, **timeouts):
        chat_id = int(request_data.parameters["chat_id"])
        parts = list(request_data.multipart_data.values())
        assert len(parts) == 1
        filename, content, _content_type = parts[0]
        uploaded_bytes = content.read() if hasattr(content, "read") else content
        uploads[chat_id] = (url.rsplit("/", 1)[-1], dict(request_data.parameters), filename, uploaded_bytes)
        if len(uploads) == 2:
            both_uploads.set()
        await both_uploads.wait()
        fake_transport.queue_result(url.rsplit("/", 1)[-1], {
            "message_id": 90 + chat_id,
            "date": 0,
            "chat": {"id": chat_id, "type": "private"},
        })
        return await original_request(url, method, request_data=request_data, **timeouts)

    monkeypatch.setattr(fake_transport, "do_request", record_upload)

    async def inspect(item):
        return InspectResult(
            MediaMetadata(
                item.platform, item.source_url, item.media_id,
                title_or_caption=titles[item.user_id - 1], media_kind=media_type,
            ),
            (FormatOption(
                0, "fixture", "native", media_type, extension, mime_type,
                includes_audio=True if media_type == "video" else None,
            ),),
        )

    async def download(item, selected):
        # Identical upstream titles must never become workspace or file identities.
        directory = tmp_path / item.request_id
        directory.mkdir()
        item.work_directory = directory
        path = directory / f"selected.{selected.extension}"
        path.write_bytes(native_bytes[item.user_id])
        downloads[item.user_id] = (item, path)
        if len(downloads) == 2:
            both_downloads.set()
        await both_downloads.wait()
        return DownloadResult(
            path, path.stat().st_size, item.media_id, selected.source_format_id,
            selected.media_type, selected.extension, selected.mime_type,
        )

    async def deliver(item, downloaded):
        return await deliver_media(
            fake_bot, request=item, downloaded=downloaded,
            owned_directory=item.work_directory, max_file_bytes=50_000_000,
            deadline=item.processing_deadline, monotonic=fake_clock,
        )

    workflow = MediaWorkflow(
        registry, inspect=inspect, publish_preview=AsyncMock(return_value=55),
        download=download, deliver=deliver, status=AsyncMock(), max_file_bytes=50_000_000,
    )
    completed = await asyncio.gather(*(
        workflow.submit(
            user_id=user, chat_id=user * 10,
            text=f"https://www.youtube.com/watch?v={'abcDEF12345' if user == 1 else 'xyzABC98765'}",
            chat_type="private",
        )
        for user in (1, 2)
    ))

    # Check infrastructure, independent lifecycle, and byte/path preservation before
    # the new label assertions, so a red result identifies missing title integration.
    assert both_downloads.is_set() and both_uploads.is_set()
    assert len(downloads) == len(uploads) == 2
    assert len({item.request_id for item in completed}) == 2
    assert completed[0].metadata is not completed[1].metadata
    assert all(item.state is RequestState.COMPLETED for item in completed)
    assert registry.active_work_count == 0
    assert not registry.active_request_by_user
    assert len(fake_transport.calls_to(method)) == 2
    assert {path for _, path in downloads.values()} == {
        tmp_path / item.request_id / f"selected.{extension}" for item in completed
    }
    assert len({path.parent for _, path in downloads.values()}) == 2
    for item in completed:
        original, path = downloads[item.user_id]
        assert original is item
        assert item.work_directory == path.parent
        assert list(path.parent.iterdir()) == [path]
        assert path.read_bytes() == native_bytes[item.user_id]
        sent_method, _parameters, _filename, uploaded_bytes = uploads[item.chat_id]
        assert sent_method == method
        assert uploaded_bytes == native_bytes[item.user_id]
        assert item.delivery_result.actual_bytes == len(native_bytes[item.user_id])
        terminal = registry.terminal(item.request_id)
        assert terminal.state is RequestState.COMPLETED
        assert terminal.confirmed_message_id == 90 + item.chat_id

    for item in completed:
        _method, parameters, filename, _bytes = uploads[item.chat_id]
        title = titles[item.user_id - 1]
        assert (parameters.get("caption"), filename) == (title, f"{title}.{extension}")

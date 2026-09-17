from __future__ import annotations

from openmedia.coordinator import AdmissionOutcome, RequestRegistry, SelectionOutcome
from openmedia.models import FormatOption, MediaMetadata, RequestState


def option(option_id: int = 0) -> FormatOption:
    return FormatOption(
        option_id=option_id,
        adapter="yt_dlp",
        source_format_id="18",
        media_type="video",
        extension="mp4",
        mime_type="video/mp4",
        includes_audio=True,
    )


def request(registry: RequestRegistry, user: int, platform: str = "youtube"):
    return registry.new_request(
        user_id=user,
        chat_id=user,
        source_url=f"https://example.com/{user}",
        platform=platform,
        media_id=str(user),
    )


async def preview(registry: RequestRegistry, item, now: float = 10) -> None:
    metadata = MediaMetadata(
        platform=item.platform,
        canonical_url=item.source_url,
        media_id=item.media_id,
    )
    assert await registry.publish_preview(
        item.request_id,
        metadata=metadata,
        options=(option(),),
        preview_message_id=50,
        now=now,
    )


async def test_admission_reserves_nonwaiting_capacity_and_one_instagram_slot() -> None:
    registry = RequestRegistry(max_workers=2, max_instagram_workers=1)
    first = request(registry, 1, "instagram")
    second = request(registry, 2, "instagram")
    third = request(registry, 3)
    assert (await registry.admit(first)).outcome is AdmissionOutcome.ADMITTED
    assert (await registry.admit(second)).outcome is AdmissionOutcome.INSTAGRAM_BUSY
    assert (await registry.admit(third)).outcome is AdmissionOutcome.ADMITTED
    assert registry.active_work_count == 2


async def test_preview_releases_work_but_keeps_pending_reservation() -> None:
    registry = RequestRegistry()
    item = request(registry, 1)
    await registry.admit(item)
    await preview(registry, item)
    assert item.state is RequestState.AWAITING_SELECTION
    assert registry.active_work_count == 0
    assert registry.pending_count == 1


async def test_full_capacity_preserves_current_preview() -> None:
    registry = RequestRegistry(max_workers=1)
    pending = request(registry, 1)
    await registry.admit(pending)
    await preview(registry, pending)
    working = request(registry, 2)
    await registry.admit(working)

    selection = await registry.claim_selection(
        pending.request_id,
        user_id=1,
        chat_id=1,
        preview_message_id=50,
        option_id=0,
        now=11,
    )
    assert selection.outcome is SelectionOutcome.WORK_BUSY
    assert pending.state is RequestState.AWAITING_SELECTION
    replacement = request(registry, 1)
    admitted = await registry.admit(replacement)
    assert admitted.outcome is AdmissionOutcome.WORK_BUSY
    assert registry.active_request_by_user[1] == pending.request_id


async def test_selection_claim_is_atomic_and_duplicate_is_stale() -> None:
    registry = RequestRegistry()
    item = request(registry, 1)
    await registry.admit(item)
    await preview(registry, item)
    first = await registry.claim_selection(
        item.request_id,
        user_id=1,
        chat_id=1,
        preview_message_id=50,
        option_id=0,
        now=11,
    )
    second = await registry.claim_selection(
        item.request_id,
        user_id=1,
        chat_id=1,
        preview_message_id=50,
        option_id=0,
        now=11,
    )
    assert first.outcome is SelectionOutcome.ACCEPTED
    assert second.outcome is SelectionOutcome.PROCESSING
    assert item.processing_deadline == 611
    assert registry.pending_count == 0


async def test_replacement_invalidates_old_preview_only_after_capacity() -> None:
    registry = RequestRegistry()
    old = request(registry, 1)
    await registry.admit(old)
    await preview(registry, old)
    new = request(registry, 1)
    result = await registry.admit(new)
    assert result.outcome is AdmissionOutcome.REPLACED
    assert registry.terminal(old.request_id).state is RequestState.REPLACED  # type: ignore[union-attr]
    assert registry.active_request_by_user[1] == new.request_id


async def test_stale_worker_cannot_publish_after_finalization() -> None:
    registry = RequestRegistry()
    item = request(registry, 1)
    await registry.admit(item)
    await registry.finalize(item.request_id, state=RequestState.FAILED)
    metadata = MediaMetadata(
        platform="youtube", canonical_url=item.source_url, media_id=item.media_id
    )
    assert not await registry.publish_preview(
        item.request_id,
        metadata=metadata,
        options=(option(),),
        preview_message_id=50,
    )


async def test_notification_failure_cannot_prevent_finalization() -> None:
    registry = RequestRegistry()
    item = request(registry, 1)
    await registry.admit(item)

    async def broken_notification() -> None:
        raise RuntimeError("Telegram unavailable")

    assert await registry.finalize(
        item.request_id, state=RequestState.FAILED, notify=broken_notification
    )
    assert item.request_id not in registry.requests_by_id
    assert registry.active_work_count == 0
    assert registry.pending_count == 0
    assert registry.user_lock_count == 0


async def test_pending_capacity_is_reserved_at_inspection_admission() -> None:
    registry = RequestRegistry(max_pending=1)
    first = request(registry, 1)
    second = request(registry, 2)
    assert (await registry.admit(first)).outcome is AdmissionOutcome.ADMITTED
    assert (await registry.admit(second)).outcome is AdmissionOutcome.PENDING_FULL


async def test_closed_admission_also_refuses_new_selection_claims() -> None:
    """Shutdown drains queued callbacks; none of them may start work after the cancel sweep."""
    registry = RequestRegistry()
    item = request(registry, 1)
    await registry.admit(item)
    await preview(registry, item)
    await registry.close_admission()

    claimed = await registry.claim_selection(
        item.request_id, user_id=1, chat_id=1, preview_message_id=50, option_id=0, now=11
    )

    assert claimed.outcome is SelectionOutcome.WORK_BUSY
    assert item.state is RequestState.AWAITING_SELECTION
    assert registry.active_work_count == 0

from __future__ import annotations

from pathlib import Path

from openmedia.coordinator import MediaWorkflow, RequestRegistry
from openmedia.models import DeliveryResult, FormatOption, MediaMetadata, RequestState
from openmedia.sources import DownloadResult, InspectResult


async def test_mocked_happy_path_downloads_only_selected_exact_file(tmp_path: Path) -> None:
    registry = RequestRegistry()
    calls: list[object] = []
    statuses: list[str] = []

    async def inspect(request):
        calls.append("inspect")
        return InspectResult(
            metadata=MediaMetadata(
                platform="youtube",
                canonical_url=request.source_url,
                media_id=request.media_id,
            ),
            options=(
                FormatOption(
                    option_id=0,
                    adapter="fixture",
                    source_format_id="18",
                    media_type="video",
                    extension="mp4",
                    mime_type="video/mp4",
                    includes_audio=True,
                ),
            ),
        )

    async def preview(request, result):
        calls.append(("preview", len(result.options)))
        return 55

    async def download(request, option):
        calls.append(("download", option.source_format_id))
        path = tmp_path / "selected.mp4"
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

    async def deliver(request, result):
        calls.append(("deliver", request.chat_id, result.path.read_bytes(), result.extension))
        assert request.state is RequestState.SENDING
        return DeliveryResult(status="confirmed", message_id=99, actual_bytes=result.actual_bytes)

    async def status(_request, stage):
        statuses.append(stage)

    workflow = MediaWorkflow(
        registry,
        inspect=inspect,
        publish_preview=preview,
        download=download,
        deliver=deliver,
        status=status,
    )
    request = await workflow.submit(
        user_id=7,
        chat_id=77,
        text="https://youtu.be/abcDEF12345",
        chat_type="private",
    )
    assert request.state is RequestState.AWAITING_SELECTION
    assert not any(isinstance(call, tuple) and call[0] == "download" for call in calls)

    result = await workflow.select(
        request_id=request.request_id,
        user_id=7,
        chat_id=77,
        preview_message_id=55,
        option_id=0,
    )
    assert result.status == "confirmed"
    assert calls[-1] == ("deliver", 77, b"exact-selected-bytes", "mp4")
    assert statuses == ["checking", "downloading", "sending"]
    terminal = registry.terminal(request.request_id)
    assert terminal is not None
    assert terminal.state is RequestState.COMPLETED
    assert terminal.confirmed_message_id == 99

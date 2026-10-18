"""Controlled plain-track acceptance; synthetic source bytes, no live-source claim."""
from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from openmedia.bot import build_card
from openmedia.coordinator import MediaWorkflow, RequestRegistry
from openmedia.delivery import deliver_media
from openmedia.models import RequestState
from openmedia.presentation import status_text
from openmedia.sources import DownloadInput, recognize_source_url
from openmedia.sources.ytdlp import YtDlpAdapter, normalize_info

LIMIT = 50_000_000


@pytest.mark.parametrize("context", ["", "&list=PLexample&index=2&radio=1&si=share", "&t=42"])
@pytest.mark.parametrize("missing_metadata", [False, True])
async def test_plain_track_automatically_delivers_one_unchanged_document(tmp_path: Path, missing_metadata: bool, monkeypatch, context: str) -> None:
    info = json.loads((Path(__file__).parents[1] / "fixtures/ytdlp/youtube-music.json").read_text())
    if missing_metadata:
        for key in ("title", "uploader", "duration", "thumbnail"):
            info.pop(key, None)
    url = "https://music.youtube.com/watch?v=fixtureYT01"
    source = tmp_path / "source.m4a"
    ffmpeg = shutil.which("ffmpeg")
    assert ffmpeg is not None, "FFmpeg is required to generate the synthetic source fixture"
    subprocess.run([ffmpeg, "-nostdin", "-v", "error", "-f", "lavfi", "-i",
        "sine=frequency=440:duration=1", "-c:a", "aac", "-vn",
        "-metadata", "title=Embedded source tag", str(source)], check=True)
    source_bytes = source.read_bytes()
    cards, statuses, uploaded, selected, document_calls = [], [], [], [], []
    registry = RequestRegistry(monotonic=lambda: 10)

    def forbidden(*args, **kwargs):
        raise AssertionError("music must not merge or convert source bytes")
    monkeypatch.setattr("openmedia.sources.ytdlp.merge_streams", forbidden)

    async def inspect(request):
        assert request.platform == "youtube"
        return normalize_info(info, max_file_bytes=LIMIT, source_route=recognize_source_url(request.source_url))

    async def preview(request, result, choices):
        rendered = build_card(request.request_id, result.metadata, choices)
        assert rendered.keyboard is None
        assert choices.automatic and not choices.missing
        cards.append((result.metadata, rendered))
        return 55

    class Rate:
        def acquire(self, platform, request_class, *, deadline):
            assert platform == "youtube"

    class Transport:
        def download(self, url, destination, **kwargs):
            assert url == "https://media.example.invalid/audio"
            Path(destination).write_bytes(source_bytes)
            return len(source_bytes)

    original_run = subprocess.run
    def probe_only(command, *args, **kwargs):
        assert Path(command[0]).name == "ffprobe", "download must not convert or rewrite tags"
        return original_run(command, *args, **kwargs)
    monkeypatch.setattr("openmedia.sources.ytdlp.subprocess.run", probe_only)

    async def download(request, option):
        selected.append(option)
        return YtDlpAdapter().download(DownloadInput(
            request_id=request.request_id, metadata=request.metadata, option=option,
            work_directory=tmp_path, deadline=100, output_limit=LIMIT,
            workspace_limit=128 * 1024 * 1024), transport=Transport(), rate_control=Rate())

    async def send_document(**kwargs):
        uploaded.append(kwargs["document"].read())
        document_calls.append(kwargs)
        return SimpleNamespace(message_id=99, document=object())

    async def forbidden_audio_player(**kwargs):
        raise AssertionError("music must remain a document, not an audio-player message")

    async def deliver(request, result):
        bot = SimpleNamespace(send_document=send_document, send_audio=forbidden_audio_player)
        return await deliver_media(bot, request=request,
            downloaded=result, owned_directory=tmp_path, max_file_bytes=LIMIT,
            deadline=100, monotonic=lambda: 10)

    async def status(request, stage):
        statuses.append(stage)

    workflow = MediaWorkflow(registry, inspect=inspect, publish_preview=preview,
        download=download, deliver=deliver, status=status, max_file_bytes=LIMIT)

    async def forbidden_selection(**kwargs):
        raise AssertionError("music must finish automatically without a selection tap")

    monkeypatch.setattr(workflow, "select", forbidden_selection)
    request = await workflow.submit(user_id=7, chat_id=77, text=url + context, chat_type="private")
    assert request.state is RequestState.COMPLETED
    assert request.preview_expires_at is None
    assert [(o.option_id, o.source_format_id) for o in selected] == [(0, "140")]
    assert selected[0].extension == "m4a"
    # Byte equality also preserves the embedded title, independently of upload labels.
    assert uploaded == [source_bytes]
    assert len(document_calls) == 1
    if not missing_metadata:
        call = document_calls[0]
        assert call.get("caption") == info["title"]
        assert call["filename"] == f"{info['title']}.m4a"
        assert "parse_mode" in call and call["parse_mode"] is None
        assert "caption_entities" not in call
    assert statuses == ["checking", "downloading", "sending", "completed"]
    assert len(cards) == 1
    if missing_metadata:
        assert cards[0][0].title_or_caption is None
        assert cards[0][0].duration_seconds is None
    assert status_text("Audio only", "downloading", automatic=True, media_kind="audio") == "Audio only — downloading…"
    assert status_text("Audio only", "sending") == "Audio only — sending…"
    assert status_text("Audio only", "completed") == "Audio only — sent."


async def test_runtime_music_card_starts_with_accurate_download_status(tmp_path, monkeypatch) -> None:
    from unittest.mock import AsyncMock
    import openmedia.__main__ as runtime
    from openmedia.choices import choose
    from openmedia.config import Settings

    url = "https://music.youtube.com/watch?v=fixtureYT01"
    info = json.loads((Path(__file__).parents[1] / "fixtures/ytdlp/youtube-music.json").read_text())
    result = normalize_info(info, max_file_bytes=LIMIT, source_route=recognize_source_url(url))
    request = RequestRegistry(monotonic=lambda: 10).new_request(
        user_id=7, chat_id=77, source_url=url, platform="youtube", media_id="fixtureYT01")
    request.status_message_id = 1
    send = AsyncMock(return_value=(55, False))
    monkeypatch.setattr(runtime, "send_card", send)
    callbacks = runtime.RuntimeCallbacks(Settings.from_env({"TELEGRAM_BOT_TOKEN": "123456789:offline",
        "OPENMEDIA_WORK_ROOT": str(tmp_path)}), SimpleNamespace(bot=object()))
    await callbacks.preview(request, result, choose(result.options, media_kind="audio", max_file_bytes=LIMIT))
    rendered = send.call_args.kwargs["rendered"]
    assert rendered.keyboard is None
    assert "Audio only — downloading…" in rendered.text
    assert "only version available" not in rendered.text


async def test_ordinary_youtube_keeps_video_choices_in_music_feature(tmp_path) -> None:
    from unittest.mock import AsyncMock
    from openmedia.choices import kind_of

    info = json.loads((Path(__file__).parents[1] / "fixtures/ytdlp/youtube-music.json").read_text())
    url = "https://www.youtube.com/watch?v=fixtureYT01"
    result = normalize_info(info, max_file_bytes=LIMIT, source_route=recognize_source_url(url))
    inspect = AsyncMock(return_value=result)
    preview = AsyncMock(return_value=55)
    download, deliver = AsyncMock(), AsyncMock()
    workflow = MediaWorkflow(RequestRegistry(monotonic=lambda: 10), inspect=inspect,
        publish_preview=preview, download=download, deliver=deliver, status=AsyncMock(), max_file_bytes=LIMIT)
    request = await workflow.submit(user_id=7, chat_id=77, text=url, chat_type="private")
    assert request.state is RequestState.AWAITING_SELECTION
    assert [kind_of(o).value for o in request.options] == ["video", "silent", "audio"]
    assert build_card(request.request_id, result.metadata, preview.call_args.args[2]).keyboard is not None
    download.assert_not_awaited()
    deliver.assert_not_awaited()

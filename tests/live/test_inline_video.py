"""Live gate for inline video delivery (research R7, quickstart section 4).

The Bot API does not promise that a file sent with ``sendVideo`` is stored byte for byte.
FR-009 relies on it, so this check uploads two small H.264 clips with ``sendVideo``, fetches
each back with ``getFile``, and compares SHA-256 with the upload. The returned message type
(``video``, ``animation``, or ``document``) is recorded in every assertion message, because
clients may present a silent MP4 as a looping animation.

It reaches the real Telegram Bot API, so it runs only when the operator exports
``TELEGRAM_BOT_TOKEN`` (from the OS keyring, for this run only) and ``OPENMEDIA_LIVE_CHAT_ID``.
The token is never read from or written to a file, and never appears in test output.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import pytest
from telegram import Bot, Message

TOKEN_ENV_VAR = "TELEGRAM_BOT_TOKEN"
CHAT_ENV_VAR = "OPENMEDIA_LIVE_CHAT_ID"

# Generous per-call limits: uploads are small, but the hosted Bot API can be slow.
UPLOAD_TIMEOUT = 120.0
READ_TIMEOUT = 60.0


@dataclass(frozen=True)
class Clip:
    name: str
    width: int
    height: int
    duration: int
    with_audio: bool


CLIPS = [
    Clip("with_sound.mp4", width=640, height=360, duration=5, with_audio=True),
    Clip("silent.mp4", width=360, height=640, duration=5, with_audio=False),
]


@pytest.fixture
def live_telegram() -> tuple[str, int | str]:
    """Return the token and chat from the environment, or skip with an actionable reason."""
    token = os.environ.get(TOKEN_ENV_VAR, "")
    chat = os.environ.get(CHAT_ENV_VAR, "")
    if not token or not chat:
        pytest.skip(
            f"Set both {TOKEN_ENV_VAR} and {CHAT_ENV_VAR} to run the inline video gate. "
            f"Export the token from the OS keyring for this shell only (never a file), and set "
            f"{CHAT_ENV_VAR} to a chat the bot may post in (numeric id, or @channelname)."
        )
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg is not on PATH; it is needed to generate the test clips.")
    try:
        chat_id: int | str = int(chat)
    except ValueError:
        chat_id = chat
    return token, chat_id


def make_clip(directory: Path, clip: Clip) -> Path:
    """Generate a tiny H.264 MP4 (plus AAC when ``with_audio``) from lavfi sources."""
    path = directory / clip.name
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-y",
        "-f", "lavfi",
        "-i", f"testsrc2=size={clip.width}x{clip.height}:rate=25:duration={clip.duration}",
    ]  # fmt: skip
    if clip.with_audio:
        command += ["-f", "lavfi", "-i", f"sine=frequency=440:duration={clip.duration}"]
        command += ["-c:a", "aac", "-b:a", "96k"]
    else:
        command += ["-an"]
    command += [
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-profile:v", "main",
        "-movflags", "+faststart", "-t", str(clip.duration), str(path),
    ]  # fmt: skip
    subprocess.run(command, check=True, capture_output=True, timeout=120)
    return path


def returned_media(message: Message) -> tuple[str, str]:
    """Return the message type Telegram chose and that attachment's ``file_id``."""
    for kind in ("video", "animation", "document"):
        attachment = getattr(message, kind)
        if attachment is not None:
            return kind, attachment.file_id
    pytest.fail("sendVideo returned a message with no video, animation, or document")


@pytest.mark.live
@pytest.mark.parametrize("clip", CLIPS, ids=[clip.name for clip in CLIPS])
async def test_send_video_preserves_bytes(
    live_telegram: tuple[str, int | str], clip: Clip, tmp_path: Path
) -> None:
    token, chat_id = live_telegram
    path = make_clip(tmp_path, clip)
    uploaded = path.read_bytes()
    assert len(uploaded) < 20_000_000, "clip must stay under the 20 MB getFile download limit"
    expected = hashlib.sha256(uploaded).hexdigest()

    async with Bot(token) as bot:
        sent: Message | None = None
        try:
            with path.open("rb") as handle:
                sent = await bot.send_video(
                    chat_id=chat_id,
                    video=handle,
                    filename=clip.name,
                    supports_streaming=True,
                    width=clip.width,
                    height=clip.height,
                    duration=clip.duration,
                    write_timeout=UPLOAD_TIMEOUT,
                    read_timeout=READ_TIMEOUT,
                )
            kind, file_id = returned_media(sent)
            remote = await bot.get_file(file_id, read_timeout=READ_TIMEOUT)
            # Never print ``remote.file_path``: on the hosted Bot API it embeds the token.
            downloaded = bytes(await remote.download_as_bytearray(read_timeout=UPLOAD_TIMEOUT))
            actual = hashlib.sha256(downloaded).hexdigest()
            assert actual == expected, (
                f"{clip.name}: Telegram returned it as `{kind}` and the stored bytes differ "
                f"(uploaded {len(uploaded)} B sha256={expected}, "
                f"fetched {len(downloaded)} B sha256={actual}). Gate fails: revise FR-009."
            )
            print(f"{clip.name}: message type `{kind}`, sha256 equal ({expected})")
        finally:
            if sent is not None:
                await bot.delete_message(chat_id=sent.chat_id, message_id=sent.message_id)

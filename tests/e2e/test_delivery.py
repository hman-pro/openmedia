"""Each supported category reaches the user as one native file through the real bot."""

from __future__ import annotations

import shutil
import subprocess
import json

import pytest

from openmedia.bot import failure_message
from openmedia.media_titles import derive_media_titles
from openmedia.sources import ErrorCategory
from tests.e2e import E2E

pytestmark = E2E

# case ID, button to tap (empty = automatic), message kind, MIME type
DELIVERIES = [
    ("youtube-video", ("Audio only",), "document", "audio/mp4"),
    ("linkedin-video", (), "video", "video/mp4"),
    ("linkedin-image", (), "document", "image/jpeg"),
    ("instagram-video", (), "video", "video/mp4"),
    ("youtube-music", (), "document", "audio/mp4"),
]


@pytest.mark.parametrize(("case_id", "prefer", "kind", "mime"), DELIVERIES, ids=[d[0] for d in DELIVERIES])
async def test_category_is_delivered_as_one_native_file(chat, case, case_id, prefer, kind, mime):
    if case_id.startswith("instagram"):
        await chat.instagram_pause()
    result = await chat.exchange(case(case_id), prefer=prefer)

    assert not result.timed_out, result.events
    assert result.final_status.endswith("— sent."), result.final_status
    assert len(result.files) == 1, result.events
    received = result.files[0]
    assert (received.kind, received.mime) == (kind, mime)
    assert received.size == len(received.data) > 0
    if kind == "video":
        assert received.supports_streaming and not received.animated  # inline, not a loop
    if result.card_title:
        extension = (received.filename or "").rsplit(".", 1)[-1]
        assert received.caption == derive_media_titles(result.card_title, extension).caption
    assert len(received.caption) <= 64


async def test_linkedin_short_hyphen_and_full_links_deliver_identical_bytes(chat, case):
    digests = set()
    for case_id in ("linkedin-video", "linkedin-short-video", "linkedin-hyphen-code"):
        result = await chat.exchange(case(case_id))
        assert len(result.files) == 1, (case_id, result.final_status)
        digests.add(result.files[0].sha256)
    assert len(digests) == 1


async def test_instagram_picture_is_delivered_or_refused_as_login_only(chat, case):
    await chat.instagram_pause()
    result = await chat.exchange(case("instagram-image"))
    if not result.files:
        assert result.final_status.endswith(failure_message(ErrorCategory.UNAVAILABLE, stage="checking"))
        pytest.xfail("Instagram refuses anonymous picture access from this network (T066: source-blocked)")
    assert result.files[0].mime.startswith("image/")


async def test_combined_video_carries_one_video_and_one_audio_stream(chat, case, tmp_path):
    if shutil.which("ffprobe") is None:
        pytest.skip("ffprobe is not installed")
    result = await chat.exchange(case("youtube-video"), prefer=("Video",))
    assert result.choice == "Video" and len(result.files) == 1, result.final_status
    received = result.files[0]
    assert received.kind == "video" and received.supports_streaming
    path = tmp_path / "combined.mp4"
    path.write_bytes(received.data)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "json", str(path)],
                           capture_output=True, text=True, check=True)
    assert sorted(s["codec_type"] for s in json.loads(probe.stdout)["streams"]) == ["audio", "video"]

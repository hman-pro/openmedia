"""YouTube Music: one automatic native audio document; context and offset keep the track."""

from __future__ import annotations

import urllib.parse

from openmedia.bot import failure_message
from openmedia.sources import ErrorCategory
from tests.e2e import E2E

pytestmark = E2E


def _with_offset(url: str, seconds: int) -> str:
    parts = urllib.parse.urlsplit(url)
    query = urllib.parse.parse_qsl(parts.query) + [("t", str(seconds))]
    return urllib.parse.urlunsplit(parts._replace(query=urllib.parse.urlencode(query)))


def _playlist_of(url: str) -> str:
    listing = dict(urllib.parse.parse_qsl(urllib.parse.urlsplit(url).query)).get("list")
    assert listing, "the youtube-music-context case needs a list= parameter"
    return f"https://music.youtube.com/playlist?list={listing}"


async def test_plain_context_and_offset_links_deliver_the_same_whole_track(chat, case):
    plain = case("youtube-music")
    digests = {}
    for name, link in (("plain", plain), ("context", case("youtube-music-context")),
                       ("offset", _with_offset(plain, 45))):
        result = await chat.exchange(link)
        assert not result.buttons, f"{name}: music must not show a picker"
        assert any(e["text"].endswith("Audio only — downloading…") for e in result.events), name
        assert result.final_status == "Audio only — sent.", (name, result.final_status)
        assert len(result.files) == 1 and result.files[0].mime == "audio/mp4", name
        digests[name] = result.files[0].sha256
    assert len(set(digests.values())) == 1, digests


async def test_collection_only_link_is_refused_without_a_file(chat, case):
    result = await chat.exchange(_playlist_of(case("youtube-music-context")))
    assert not result.files
    assert result.final_status.endswith(failure_message(ErrorCategory.MUSIC_COLLECTION, stage="checking"))


async def test_ordinary_youtube_keeps_its_video_choices(chat, case):
    result = await chat.exchange(case("youtube-video"), tap=False, download=False, quiet=3)
    assert result.buttons == ["Video", "Video (no sound)", "Audio only"]

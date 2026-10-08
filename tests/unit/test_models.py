from __future__ import annotations

import pytest

from openmedia.models import (
    Availability,
    DeliveryResult,
    DownloadRequest,
    FormatOption,
    MediaMetadata,
)


def video_option(**changes: object) -> FormatOption:
    values = {
        "option_id": 0,
        "adapter": "yt_dlp",
        "source_format_id": "18",
        "media_type": "video",
        "extension": "mp4",
        "mime_type": "video/mp4",
        "includes_audio": True,
    }
    values.update(changes)
    return FormatOption(**values)  # type: ignore[arg-type]


def test_metadata_does_not_infer_optional_text_and_rejects_hidden_collection() -> None:
    metadata = MediaMetadata(
        platform="youtube",
        canonical_url="https://www.youtube.com/watch?v=abc",
        media_id="abc",
    )
    assert metadata.title_or_caption is None
    assert metadata.creator is None
    with pytest.raises(ValueError, match="multiple"):
        MediaMetadata(
            platform="instagram",
            canonical_url="https://www.instagram.com/p/abc/",
            media_id="abc",
            media_kind="image",
            media_count=2,
        )


def test_image_duration_and_format_invariants() -> None:
    with pytest.raises(ValueError, match="absent"):
        MediaMetadata(
            platform="instagram",
            canonical_url="https://www.instagram.com/p/abc/",
            media_id="abc",
            media_kind="image",
            duration_seconds=1,
        )
    with pytest.raises(ValueError, match="includes_audio"):
        FormatOption(
            option_id=0,
            adapter="instagram",
            source_format_id="image",
            media_type="image",
            extension="jpg",
            mime_type="image/jpeg",
            includes_audio=False,
        )


def test_format_option_is_request_local_secret_safe_and_exactly_sized() -> None:
    option = video_option(
        size_bytes=100,
        size_kind="exact",
        transport_ref={"url": "https://signed.example/secret"},
    )
    assert "signed.example" not in repr(option)
    with pytest.raises(TypeError):
        option.transport_ref["url"] = "changed"  # type: ignore[index]
    with pytest.raises(ValueError, match="unknown"):
        video_option(size_bytes=100, size_kind="unknown")


def test_excluded_options_need_a_user_facing_reason() -> None:
    with pytest.raises(ValueError, match="reason"):
        video_option(availability=Availability.EXCLUDED)


def test_delivery_confirmation_and_unknown_outcome_are_unambiguous() -> None:
    confirmed = DeliveryResult(status="confirmed", message_id=5, actual_bytes=100)
    assert confirmed.message_id == 5
    unknown = DeliveryResult(
        status="unknown",
        error_category="upload_ambiguous",
        failed_stage="sending",
        next_step="Check the chat before resubmitting.",
    )
    assert unknown.status == "unknown"
    with pytest.raises(ValueError, match="message_id"):
        DeliveryResult(status="confirmed", actual_bytes=100)


def test_download_request_has_immutable_options_and_valid_selection() -> None:
    option = video_option()
    request = DownloadRequest(
        request_id="0123456789abcdef0123456789abcdef",
        user_id=1,
        chat_id=1,
        source_url="https://www.youtube.com/watch?v=abc",
        platform="youtube",
        media_id="abc",
        options=[option],  # type: ignore[arg-type]
        selected_option_id=0,
        created_at=10,
    )
    assert request.options == (option,)
    assert request.option(0) is option
    with pytest.raises(ValueError, match="selected_option_id"):
        DownloadRequest(
            request_id="1123456789abcdef0123456789abcdef",
            user_id=1,
            chat_id=1,
            source_url="https://www.youtube.com/watch?v=abc",
            platform="youtube",
            media_id="abc",
            options=(option,),
            selected_option_id=99,
        )


def minimal_request(**changes: object) -> DownloadRequest:
    values: dict[str, object] = {
        "request_id": "2123456789abcdef0123456789abcdef",
        "user_id": 1,
        "chat_id": 1,
        "source_url": "https://www.youtube.com/watch?v=abc",
        "platform": "youtube",
        "media_id": "abc",
    }
    values.update(changes)
    return DownloadRequest(**values)  # type: ignore[arg-type]


def test_download_request_status_surface_defaults() -> None:
    request = minimal_request()
    assert request.status_message_id is None
    assert request.status_is_caption is False
    assert request.status_prefix is None


def test_download_request_accepts_status_surface_values() -> None:
    request = minimal_request(
        status_message_id=42,
        status_is_caption=True,
        status_prefix="Some title\n1:23",
    )
    assert request.status_message_id == 42
    assert request.status_is_caption is True
    assert request.status_prefix == "Some title\n1:23"
    request.status_message_id = 43
    assert request.status_message_id == 43


@pytest.mark.parametrize("message_id", [0, -1])
def test_download_request_rejects_nonpositive_status_message_id(message_id: int) -> None:
    with pytest.raises(ValueError, match="status_message_id"):
        minimal_request(status_message_id=message_id)


def test_download_request_status_prefix_is_kept_out_of_repr() -> None:
    request = minimal_request(
        status_message_id=7,
        status_prefix="Secret caption title",
        work_directory=None,
    )
    assert "Secret caption title" not in repr(request)
    assert "status_prefix" not in repr(request)
    assert "work_directory" not in repr(request)


@pytest.mark.parametrize("duration", [None, 0, 123.5])
def test_audio_metadata_preserves_optional_values(duration: float | None) -> None:
    from openmedia.models import MediaKind

    metadata = MediaMetadata(
        platform="youtube", canonical_url="https://music.youtube.com/watch?v=abcDEF12345",
        media_id="abcDEF12345", media_kind="audio", duration_seconds=duration,
    )
    assert metadata.media_kind is MediaKind.AUDIO
    assert metadata.media_count == 1
    assert metadata.duration_seconds == duration
    assert metadata.title_or_caption is None
    assert metadata.creator is None
    assert metadata.thumbnail_url is None


def test_audio_metadata_retains_supplied_text_and_artwork() -> None:
    metadata = MediaMetadata(
        platform="youtube", canonical_url="https://music.youtube.com/watch?v=abcDEF12345",
        media_id="abcDEF12345", media_kind="audio", title_or_caption="Track",
        creator="Artist", thumbnail_url="https://example.invalid/art.jpg", duration_seconds=42,
    )
    assert (metadata.title_or_caption, metadata.creator, metadata.duration_seconds) == ("Track", "Artist", 42)
    assert metadata.thumbnail_url == "https://example.invalid/art.jpg"


@pytest.mark.parametrize(("changes", "message"), [
    ({"duration_seconds": -1}, "nonnegative"),
    ({"media_count": 2}, "multiple"),
    ({"media_count": 0}, "at least one"),
    ({"title_or_caption": " "}, "absent"),
])
def test_audio_metadata_rejects_invalid_single_item(changes: dict[str, object], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        MediaMetadata(
            platform="youtube", canonical_url="https://music.youtube.com/watch?v=abcDEF12345",
            media_id="abcDEF12345", media_kind="audio", **changes,
        )

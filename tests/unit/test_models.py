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

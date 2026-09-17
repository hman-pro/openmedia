from __future__ import annotations

import pytest

from openmedia.bot import InputError, failure_message, parse_link_message
from openmedia.sources import ErrorCategory, SourceAdapterError


@pytest.mark.parametrize(
    "text",
    [
        "no links",
        "https://example.com/not-supported",
        "https://youtu.be/abcDEF12345 https://instagram.com/p/DdExample1/",
        "https://www.youtube.com/playlist?list=PL123 https://youtu.be/abcDEF12345",
    ],
)
def test_invalid_or_multiple_supported_links_are_rejected(text: str) -> None:
    with pytest.raises((InputError, SourceAdapterError)):
        parse_link_message(text, chat_type="private")


def test_groups_are_directed_to_private_chat() -> None:
    with pytest.raises(InputError, match="private chat"):
        parse_link_message("https://youtu.be/abcDEF12345", chat_type="supergroup")


@pytest.mark.parametrize(
    "url",
    [
        "https://www.youtube.com/playlist?list=PL123",
        "https://www.youtube.com/live/abcDEF12345",
    ],
)
def test_collection_and_live_routes_are_rejected(url: str) -> None:
    with pytest.raises(SourceAdapterError) as caught:
        parse_link_message(url, chat_type="private")
    assert caught.value.category is ErrorCategory.UNSUPPORTED_COLLECTION


@pytest.mark.parametrize("category", list(ErrorCategory))
def test_every_adapter_error_has_sanitized_guidance(category: ErrorCategory) -> None:
    message = failure_message(category, stage="checking")
    assert message
    assert "traceback" not in message.lower()
    assert "token" not in message.lower()
    assert any(word in message.lower() for word in ("send", "submit", "choose", "retry", "later", "check"))


def test_native_audio_and_no_format_messages_are_explicit() -> None:
    assert "audio-only" in failure_message(ErrorCategory.FORMAT_UNAVAILABLE, stage="audio")
    assert "no downloadable" in failure_message(ErrorCategory.NO_FORMATS, stage="checking")

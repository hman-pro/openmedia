from __future__ import annotations

from openmedia.models import FormatOption
from openmedia.presentation import option_label, sort_options


def make(option_id: int, media_type: str, *, height: int | None = None, audio: bool | None = None, size: int | None = None, size_kind: str = "unknown") -> FormatOption:
    return FormatOption(
        option_id=option_id,
        adapter="fixture",
        source_format_id=str(option_id),
        media_type=media_type,
        extension={"video": "mp4", "audio": "m4a", "image": "jpg"}[media_type],
        mime_type={"video": "video/mp4", "audio": "audio/mp4", "image": "image/jpeg"}[media_type],
        height=height,
        includes_audio=audio,
        size_bytes=size,
        size_kind=size_kind,
    )


def test_options_sort_by_semantic_type_then_quality() -> None:
    options = [
        make(0, "image"),
        make(1, "video", height=720, audio=False),
        make(2, "audio"),
        make(3, "video", height=360, audio=True),
        make(4, "video", height=1080, audio=True),
    ]
    assert [option.option_id for option in sort_options(options)] == [4, 3, 2, 1, 0]


def test_labels_preserve_size_certainty_and_silent_video() -> None:
    assert "12 B" in option_label(make(0, "audio", size=12, size_kind="exact"))
    assert "estimated" in option_label(make(1, "image", size=2048, size_kind="estimated"))
    label = option_label(make(2, "video", height=720, audio=False))
    assert "silent" in label
    assert "size unknown" in label

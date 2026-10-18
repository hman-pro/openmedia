"""Short-title delivery labels follow the feature 006 data model.

Filename constraint: "Safe stem plus dot and selected extension; extension outside
stem budget; at most 240 UTF-8 bytes for the complete filename, including any
ellipsis; upload label only".

These tests derive upload labels without creating or renaming a local media file.
Unicode shortening and unsafe-title cases belong to the later robustness tasks.
"""

import pytest

from openmedia.media_titles import DeliveryLabels, derive_media_titles


def assert_filename_constraint(labels: DeliveryLabels, stem: str, extension: str) -> None:
    """Verify the selected extension is appended outside the safe stem budget."""
    assert labels.filename == f"{stem}.{extension}"
    assert len(stem) <= 64
    assert len(labels.filename.encode("utf-8")) <= 240


def test_short_safe_title_supplies_caption_and_filename() -> None:
    labels = derive_media_titles("Summer walk", "mp4")

    assert isinstance(labels, DeliveryLabels)
    assert labels.caption == "Summer walk"
    assert_filename_constraint(labels, "Summer walk", "mp4")


def test_identical_title_uses_each_selected_extension() -> None:
    labels_by_extension = {
        extension: derive_media_titles("Summer walk", extension)
        for extension in ("mp4", "m4a", "jpg")
    }

    for extension, labels in labels_by_extension.items():
        assert labels.caption == "Summer walk"
        assert_filename_constraint(labels, "Summer walk", extension)
    assert len({labels.filename for labels in labels_by_extension.values()}) == 3


@pytest.mark.parametrize(
    ("title", "extension"),
    [("Summer walk.mp4", "m4a"), ("Summer walk.mp4", "mp4")],
)
def test_source_suffix_is_preserved_before_selected_extension(
    title: str, extension: str
) -> None:
    labels = derive_media_titles(title, extension)

    assert labels.caption == title
    assert_filename_constraint(labels, title, extension)

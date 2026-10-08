from __future__ import annotations

from pathlib import Path

import pytest

from openmedia.models import FormatOption, MediaMetadata
from openmedia.sources import DownloadInput, ErrorCategory, InspectInput, SourceAdapterError


def test_operation_inputs_are_fixed_and_bounded(tmp_path: Path) -> None:
    request = InspectInput(
        source_url="https://www.youtube.com/watch?v=abc",
        request_id="0123456789abcdef0123456789abcdef",
        work_directory=tmp_path,
        deadline=10,
    )
    assert request.operation == "inspect"
    with pytest.raises(TypeError):
        InspectInput(
            source_url=request.source_url,
            request_id=request.request_id,
            work_directory=tmp_path,
            deadline=10,
            operation="download",  # type: ignore[call-arg]
        )
    with pytest.raises(ValueError, match="request_id"):
        InspectInput(
            source_url=request.source_url,
            request_id="bad",
            work_directory=tmp_path,
            deadline=10,
        )


def test_download_binds_exact_server_option(tmp_path: Path) -> None:
    metadata = MediaMetadata(
        platform="youtube",
        canonical_url="https://www.youtube.com/watch?v=abc",
        media_id="abc",
    )
    option = FormatOption(
        option_id=0,
        adapter="yt_dlp",
        source_format_id="18",
        media_type="video",
        extension="mp4",
        mime_type="video/mp4",
        includes_audio=True,
    )
    request = DownloadInput(
        request_id="0123456789abcdef0123456789abcdef",
        metadata=metadata,
        option=option,
        work_directory=tmp_path,
        deadline=20,
        output_limit=100,
        workspace_limit=200,
    )
    assert request.operation == "download"
    assert request.option.source_format_id == "18"


def test_source_errors_expose_only_normalized_category() -> None:
    error = SourceAdapterError(ErrorCategory.RATE_LIMITED, stage="inspection", retry_after=5)
    assert str(error) == "rate_limited during inspection"
    assert error.retry_after == 5


@pytest.mark.parametrize(("category", "stage"), [
    ("music_collection", "input"), ("no_native_audio", "inspection"),
])
def test_music_error_envelope_reconstruction(category: str, stage: str) -> None:
    error = SourceAdapterError(category, stage=stage)
    assert error.category is ErrorCategory(category)
    assert error.stage == stage
    assert str(error) == f"{category} during {stage}"
    assert ErrorCategory.UNSUPPORTED_COLLECTION.value == "unsupported_collection"
    assert ErrorCategory.NO_FORMATS.value == "no_formats"
    assert ErrorCategory.FORMAT_UNAVAILABLE.value == "format_unavailable"

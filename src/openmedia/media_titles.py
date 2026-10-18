"""Pure, request-local labels for media uploads.

Labels are upload metadata only, never local paths. Do not include their values in
diagnostic events or exception messages.
"""

from dataclasses import dataclass, field


TITLE_CODE_POINT_LIMIT = 64
FILENAME_BYTE_LIMIT = 240
FALLBACK_TITLE = "Untitled media"


@dataclass(frozen=True)
class DeliveryLabels:
    """Immutable labels whose source text is excluded from representations."""

    caption: str = field(repr=False)
    filename: str = field(repr=False)


def derive_media_titles(title: str | None, extension: str) -> DeliveryLabels:
    """Derive upload labels using an already validated selected extension.

    This foundation supplies neutral labels; source-title derivation is added in
    the titled-item implementation task. No source text is logged or persisted.
    """
    return DeliveryLabels(
        caption=FALLBACK_TITLE,
        filename=f"{FALLBACK_TITLE}.{extension}",
    )

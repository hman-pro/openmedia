"""OpenMedia: a Telegram bot that delivers one public media link, unchanged.

The package is laid out as described in `specs/001-media-download/plan.md`: handlers,
coordinator, workers, delivery, network guards, and three source adapters under
`openmedia.sources`. Phase 1 establishes the package only; no workflow behaviour exists yet.
"""

__all__ = ["__version__"]

__version__ = "0.1.0"

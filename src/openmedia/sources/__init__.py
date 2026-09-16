"""Source adapters.

Each adapter normalizes one upstream into the shared shape defined by
`specs/001-media-download/contracts/source-adapters.md`: `inspect` returns metadata and
native format options, `download` retrieves exactly one previously selected option. Routing
lives here; `ytdlp`, `instagram`, and `linkedin` modules arrive in later phases.
"""

__all__: list[str] = []

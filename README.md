# OpenMedia

A Telegram bot that takes one public media link, shows the native formats the source
actually offers, and delivers the selected file byte-for-byte unchanged. No transcoding,
no merging, no credentials, no database.

Specification, plan, and ordered task list live in `specs/001-media-download/`.

```sh
uv sync --locked --group dev     # install from the lock
uv run pytest                    # controlled tests; network is disabled in conftest
uv run pytest -m live            # opt-in, hits real sources, run deliberately
```

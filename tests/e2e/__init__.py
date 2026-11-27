"""Opt-in end-to-end checks that drive a running bot from a Telegram test account.

Test modules set ``pytestmark = E2E`` and must not import Telethon at module level: the
default run collects this package (then deselects it) without the ``e2e`` group installed.
"""

import pytest

# One client for the whole run: every e2e test shares the session event loop.
E2E = [pytest.mark.e2e, pytest.mark.asyncio(loop_scope="session")]

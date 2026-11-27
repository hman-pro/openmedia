"""Fixtures for the opt-in end-to-end suite (see tests/e2e/README.md).

The suite plays the user: a dedicated Telegram test account sends links to a running bot
over the Telegram user API, taps card buttons and checks what arrives. It needs:

* a running bot: `scripts/dev.sh` for the dev bot (default target), or the deployed
  production bot with `OPENMEDIA_E2E_TARGET=prod`;
* the test account's API id/hash and login session plus the target bot's username, from
  the environment or the OS keyring (`tests/e2e/keychain.py`; create the session with
  `uv run --group e2e python -m tests.e2e.login`);
* the private live manifest named by `OPENMEDIA_LIVE_MANIFEST` (same file as the live
  suite), with the e2e case IDs listed in the README.

Anything missing skips with a reason; a skip never reads as a pass. Each test module sets
`pytestmark = E2E` (tests/e2e/__init__.py) so the marker exists before `-m` deselection.
"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import pytest
import pytest_asyncio

from tests.e2e import keychain

TARGET_ENV_VAR = "OPENMEDIA_E2E_TARGET"
MANIFEST_ENV_VAR = "OPENMEDIA_LIVE_MANIFEST"
SLOW_ENV_VAR = "OPENMEDIA_E2E_SLOW"


@pytest.fixture(scope="session")
def cases() -> dict[str, str]:
    """Case ID → URL from the private manifest; skip when it is not configured."""
    location = os.environ.get(MANIFEST_ENV_VAR)
    if not location or not Path(location).is_file():
        pytest.skip(f"{MANIFEST_ENV_VAR} is not set to an existing private manifest.")
    manifest = json.loads(Path(location).read_text())
    # `e2e_cases` holds e2e-only examples the live source suite must not iterate.
    return {case["case_id"]: case["url"] for case in manifest["cases"] + manifest.get("e2e_cases", [])}


@pytest.fixture
def case(cases: dict[str, str]):
    def get(case_id: str) -> str:
        if case_id not in cases:
            pytest.skip(f"manifest has no case `{case_id}`")
        return cases[case_id]
    return get


@pytest.fixture(scope="session")
def slow() -> None:
    if os.environ.get(SLOW_ENV_VAR) != "1":
        pytest.skip(f"slow case; set {SLOW_ENV_VAR}=1 to run it")


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def chat() -> AsyncIterator[Any]:
    """The test account's private chat with the target bot, ready for exchanges."""
    telethon = pytest.importorskip("telethon", reason="install the e2e group: uv run --group e2e …")
    from telethon.sessions import StringSession

    from tests.e2e.client import BotChat

    target = os.environ.get(TARGET_ENV_VAR, "dev")
    if target not in keychain.BOT_USERNAMES:
        pytest.fail(f"{TARGET_ENV_VAR} must be one of {sorted(keychain.BOT_USERNAMES)}")
    values = {name: keychain.lookup(service) for name, service in (
        ("api_id", keychain.API_ID), ("api_hash", keychain.API_HASH),
        ("session", keychain.SESSION), ("bot", keychain.BOT_USERNAMES[target]))}
    missing = [name for name, value in values.items() if not value]
    if missing:
        pytest.skip(f"e2e credentials not configured: {', '.join(missing)} (tests/e2e/README.md)")

    client = telethon.TelegramClient(StringSession(values["session"]), int(values["api_id"]),
                                     values["api_hash"])
    await client.connect()
    try:
        if not await client.is_user_authorized():
            pytest.skip("the e2e session is not authorized; run `python -m tests.e2e.login`")
        bot = await client.get_input_entity(values["bot"])
        chat = BotChat(client, bot)
        await chat.start()
        reply = await chat.exchange("/start", tap=False, timeout=15, quiet=2)
        if not reply.events:
            pytest.skip(f"the {target} bot did not answer /start; is it running (scripts/dev.sh)?")
        yield chat
    finally:
        await client.disconnect()

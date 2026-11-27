"""One-time login of the e2e test account; stores the session in the OS keyring.

    uv run --group e2e python -m tests.e2e.login

Needs the API id/hash in the keyring first (tests/e2e/README.md). Prompts for the test
account's phone number, the login code and, if set, the two-step password. The session
string is never printed or written to a file; revoke it in Telegram > Settings > Devices.
"""

from __future__ import annotations

import asyncio
import getpass

from telethon import TelegramClient
from telethon.sessions import StringSession

from tests.e2e import keychain


async def main() -> None:
    api_id, api_hash = keychain.lookup(keychain.API_ID), keychain.lookup(keychain.API_HASH)
    if not api_id or not api_hash:
        raise SystemExit("Store the API id and hash first (tests/e2e/README.md).")
    client = TelegramClient(StringSession(), int(api_id), api_hash)
    await client.start(phone=lambda: input("Test account phone (+country…): "),
                       code_callback=lambda: input("Login code from Telegram: "),
                       password=lambda: getpass.getpass("Two-step password (Enter if none): "))
    me = await client.get_me()
    keychain.store(keychain.SESSION, client.session.save())
    await client.disconnect()
    print(f"Logged in (bot account: {bool(me.bot)}). Session stored in the OS keyring.")


if __name__ == "__main__":
    asyncio.run(main())

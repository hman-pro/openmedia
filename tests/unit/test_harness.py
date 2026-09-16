"""Self-checks for the shared test harness.

The Phase 1 checkpoint claims that controlled tests cannot accidentally reach Telegram or
a social source. That claim is only worth as much as a test that demonstrates it.
"""

from __future__ import annotations

import socket

import pytest

from tests.conftest import BlockedNetworkAccess, FakeClock


class TestNetworkIsolation:
    def test_outbound_connection_is_refused(self) -> None:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        with pytest.raises(BlockedNetworkAccess):
            sock.connect(("api.telegram.org", 443))

    def test_dns_resolution_is_refused(self) -> None:
        with pytest.raises(BlockedNetworkAccess):
            socket.getaddrinfo("www.youtube.com", 443)

    def test_create_connection_is_refused(self) -> None:
        with pytest.raises(BlockedNetworkAccess):
            socket.create_connection(("www.instagram.com", 443))


class TestFakeTelegramTransport:
    async def test_bot_call_is_recorded_and_answered_from_the_script(
        self, fake_bot, fake_transport
    ) -> None:
        fake_transport.queue_result(
            "sendMessage",
            {
                "message_id": 7,
                "date": 1_700_000_000,
                "chat": {"id": 42, "type": "private"},
                "text": "choose a format",
            },
        )

        message = await fake_bot.send_message(chat_id=42, text="choose a format")

        assert message.message_id == 7
        sent = fake_transport.calls_to("sendMessage")
        assert len(sent) == 1
        assert sent[0].parameters["chat_id"] == 42

    async def test_queued_error_surfaces_as_a_telegram_error(
        self, fake_bot, fake_transport
    ) -> None:
        from telegram.error import Forbidden

        fake_transport.queue_error("sendMessage", "Forbidden: bot was blocked by the user", status_code=403)

        with pytest.raises(Forbidden):
            await fake_bot.send_message(chat_id=42, text="here is your file")


class TestFakeClock:
    def test_advances_only_when_told(self) -> None:
        clock = FakeClock(start=100.0)
        assert clock() == 100.0
        clock.advance(900.0)
        assert clock() == 1_000.0

    def test_refuses_to_move_backwards(self) -> None:
        with pytest.raises(ValueError):
            FakeClock().advance(-1.0)

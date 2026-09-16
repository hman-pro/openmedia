"""Shared conventions for OpenMedia's controlled test suite.

Three guarantees are established here, because every later phase depends on them:

1. **Controlled tests cannot reach the network.** An autouse fixture blocks outbound
   TCP and name resolution for every test that is not marked ``live``. A test that
   silently talks to Telegram, YouTube, Instagram, or LinkedIn is not a controlled test;
   it is a flaky one whose failures track someone else's outage.
2. **Telegram is exercised through a fake transport**, not a mock of our own code. The
   fake implements ``telegram.request.BaseRequest``, so python-telegram-bot builds and
   validates real request payloads and parses real Bot API envelopes; only the socket is
   replaced. That keeps the Telegram contract under test instead of our idea of it.
3. **Time is injected, never slept through.** Deadlines in this project are fixed in code
   (60s inspect, 900s selection expiry, 600s download-and-send, 900s cleanup), so tests
   assert on them with a fake monotonic clock they advance by hand.

Fixture conventions for sanitized source data live in ``tests/fixtures/README.md``.
"""

from __future__ import annotations

import json
import socket
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from telegram.request import BaseRequest, RequestData

# A syntactically shaped but obviously non-functional token. Controlled tests must never
# carry a real credential, and the network block means this one could not be used anyway.
FAKE_BOT_TOKEN = "123456789:AAEXAMPLE-controlled-tests-only-not-a-real-token"


# --------------------------------------------------------------------------------------
# 1. Network isolation
# --------------------------------------------------------------------------------------


class BlockedNetworkAccess(RuntimeError):
    """Raised when a controlled test attempts to open an outbound connection."""


def _blocked(detail: str) -> BlockedNetworkAccess:
    return BlockedNetworkAccess(
        f"Controlled tests may not use the network ({detail}). Use the fake Telegram "
        "transport or a sanitized fixture; if the test genuinely needs a real source, "
        "move it under tests/live/ and mark it with @pytest.mark.live."
    )


@pytest.fixture(autouse=True)
def block_network(request: pytest.FixtureRequest) -> Iterator[None]:
    """Refuse outbound connections and DNS for every test not marked ``live``.

    Connect-time and resolution-time interception is deliberate: constructing a socket is
    harmless and some libraries do it at import, so blocking the constructor would break
    tests for no safety gain. Nothing leaves the machine without one of these calls.
    """
    if request.node.get_closest_marker("live") is not None:
        yield
        return

    real_connect = socket.socket.connect
    real_connect_ex = socket.socket.connect_ex
    real_create_connection = socket.create_connection
    real_getaddrinfo = socket.getaddrinfo

    inet_families = {socket.AF_INET, socket.AF_INET6}

    def guarded_connect(self: socket.socket, address: Any) -> Any:
        if self.family in inet_families:
            raise _blocked(f"socket.connect to {address!r}")
        return real_connect(self, address)

    def guarded_connect_ex(self: socket.socket, address: Any) -> Any:
        if self.family in inet_families:
            raise _blocked(f"socket.connect_ex to {address!r}")
        return real_connect_ex(self, address)

    def guarded_create_connection(address: Any, *args: Any, **kwargs: Any) -> Any:
        raise _blocked(f"socket.create_connection to {address!r}")

    def guarded_getaddrinfo(host: Any, port: Any, *args: Any, **kwargs: Any) -> Any:
        raise _blocked(f"DNS resolution of {host!r}")

    socket.socket.connect = guarded_connect  # type: ignore[method-assign]
    socket.socket.connect_ex = guarded_connect_ex  # type: ignore[method-assign]
    socket.create_connection = guarded_create_connection  # type: ignore[assignment]
    socket.getaddrinfo = guarded_getaddrinfo  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.socket.connect = real_connect  # type: ignore[method-assign]
        socket.socket.connect_ex = real_connect_ex  # type: ignore[method-assign]
        socket.create_connection = real_create_connection  # type: ignore[assignment]
        socket.getaddrinfo = real_getaddrinfo  # type: ignore[assignment]


# --------------------------------------------------------------------------------------
# 2. Fake Telegram transport
# --------------------------------------------------------------------------------------


class RecordedCall:
    """One Bot API call as python-telegram-bot actually serialized it."""

    __slots__ = ("method", "url", "parameters")

    def __init__(self, url: str, method: str, request_data: RequestData | None) -> None:
        self.url = url
        self.method = url.rsplit("/", 1)[-1]
        self.parameters: dict[str, Any] = (
            dict(request_data.parameters) if request_data is not None else {}
        )

    def __repr__(self) -> str:  # pragma: no cover - diagnostic only
        return f"RecordedCall(method={self.method!r}, parameters={self.parameters!r})"


class FakeTelegramTransport(BaseRequest):
    """A ``BaseRequest`` that answers from a script instead of a socket.

    Responses are queued per Bot API method name. A method with no queued response gets
    ``{"ok": true, "result": true}``, which is what the real API returns for the many
    calls whose only meaningful answer is acknowledgement. Queue an explicit response
    whenever a test depends on the content.
    """

    def __init__(self) -> None:
        super().__init__()
        self.calls: list[RecordedCall] = []
        self._responses: dict[str, list[tuple[int, dict[str, Any]]]] = {}

    # -- scripting ---------------------------------------------------------------------

    def queue_result(self, method: str, result: Any) -> None:
        """Queue one successful Bot API result for ``method`` (e.g. ``sendDocument``)."""
        self._responses.setdefault(method, []).append((200, {"ok": True, "result": result}))

    def queue_error(
        self, method: str, description: str, *, status_code: int = 400, **extra: Any
    ) -> None:
        """Queue one Bot API error, so failure handling is tested against real shapes."""
        body: dict[str, Any] = {
            "ok": False,
            "error_code": status_code,
            "description": description,
        }
        body.update(extra)
        self._responses.setdefault(method, []).append((status_code, body))

    # -- inspection --------------------------------------------------------------------

    def calls_to(self, method: str) -> list[RecordedCall]:
        return [call for call in self.calls if call.method == method]

    # -- BaseRequest -------------------------------------------------------------------

    @property
    def read_timeout(self) -> float | None:
        return None

    async def initialize(self) -> None:
        return None

    async def shutdown(self) -> None:
        return None

    async def do_request(
        self,
        url: str,
        method: str,
        request_data: RequestData | None = None,
        **_timeouts: Any,
    ) -> tuple[int, bytes]:
        call = RecordedCall(url, method, request_data)
        self.calls.append(call)
        queued = self._responses.get(call.method)
        if queued:
            status_code, body = queued.pop(0)
        else:
            status_code, body = 200, {"ok": True, "result": True}
        return status_code, json.dumps(body).encode("utf-8")


@pytest.fixture
def fake_transport() -> FakeTelegramTransport:
    return FakeTelegramTransport()


@pytest.fixture
def fake_bot(fake_transport: FakeTelegramTransport) -> Any:
    """A real ``telegram.Bot`` whose only fake part is the transport.

    Separate transports for API calls and ``getUpdates`` mirror the plan's requirement
    that polling uses its own connection.
    """
    from telegram import Bot

    return Bot(
        token=FAKE_BOT_TOKEN,
        request=fake_transport,
        get_updates_request=FakeTelegramTransport(),
    )


# --------------------------------------------------------------------------------------
# 3. Monotonic clock
# --------------------------------------------------------------------------------------


class FakeClock:
    """A hand-advanced stand-in for ``time.monotonic``.

    Modules that enforce a deadline take a ``monotonic: Callable[[], float]`` argument
    defaulting to ``time.monotonic``; tests pass ``fake_clock`` instead. Advancing the
    clock rather than patching the global keeps pytest's own timing intact and makes a
    900-second expiry assertion cost nothing.
    """

    __slots__ = ("_now",)

    def __init__(self, start: float = 1_000.0) -> None:
        self._now = start

    def __call__(self) -> float:
        return self._now

    @property
    def now(self) -> float:
        return self._now

    def advance(self, seconds: float) -> float:
        if seconds < 0:
            raise ValueError("a monotonic clock cannot move backwards")
        self._now += seconds
        return self._now


@pytest.fixture
def fake_clock() -> FakeClock:
    return FakeClock()


@pytest.fixture
def monotonic(fake_clock: FakeClock) -> Callable[[], float]:
    """The callable form, for injecting straight into a deadline-aware constructor."""
    return fake_clock

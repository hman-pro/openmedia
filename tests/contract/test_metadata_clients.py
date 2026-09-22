from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import requests
from yt_dlp.networking import Request

from openmedia.sources import TransportResponse, SourceAdapterError
from openmedia.sources.http import MetadataHTTP


def test_real_requests_and_ytdlp_interfaces_use_bounded_transport():
    calls = []
    class Transport:
        def fetch(self, url, **kwargs):
            calls.append(kwargs)
            self.on_request()
            self.on_response(200, {})
            return TransportResponse(url, 200, {"content-type": "application/json"}, b'{"ok":true}')
    rate = SimpleNamespace(acquire=Mock(), limited=Mock(), observe=Mock())
    transport = Transport()
    client = MetadataHTTP(transport, rate, SimpleNamespace(deadline=10, metadata_limit=32), "instagram")
    with client.requests():
        assert requests.get("https://example.invalid", headers={"Cookie": "private"}).json() == {"ok": True}
    with client.bound():
        assert client.ytdlp(Request("https://example.invalid", data=b"payload")).read() == b'{"ok":true}'
    assert len(calls) == rate.acquire.call_count == 2
    assert all(call["limit"] == 32 and call["deadline"] == 10 for call in calls)
    assert all("Cookie" not in call["headers"] for call in calls)
    assert calls[1]["method"] == "POST"
    assert transport.on_request is None


def test_upstream_429_updates_parent_cooldown_and_aborts():
    transport = SimpleNamespace()
    rate = SimpleNamespace(acquire=Mock(), limited=Mock())
    client = MetadataHTTP(transport, rate, SimpleNamespace(deadline=10, metadata_limit=32), "instagram")
    with client.bound():
        with pytest.raises(SourceAdapterError):
            transport.on_response(429, {"retry-after": "75"})
    rate.limited.assert_called_once_with("instagram", "metadata", retry_after=75)


# --------------------------------------------------------------------------------------
# Real library clients. Nothing below injects a post loader or a parsed info dict: the
# actual Instaloader and yt-dlp request paths run, and conftest's network block turns any
# request that escapes the guarded transport into a failure.
# --------------------------------------------------------------------------------------

import json
import time

from openmedia.sources import ErrorCategory, InspectInput
from openmedia.sources.instagram import InstagramImageAdapter
from openmedia.sources.ytdlp import YtDlpAdapter


SHORTCODE = "gbStjFIaB4"
POST_ITEM = {"code": SHORTCODE, "pk": "1", "media_type": 1, "taken_at": 1383855278,
    "user": {"pk": "2", "username": "example_creator"}, "caption": {"text": "Sanitized caption"},
    "image_versions2": {"candidates": [{"url": "https://scontent.example.invalid/native-image"}]}}
POST_BODY = json.dumps({"status": "ok",
    "data": {"xdt_api__v1__media__shortcode__web_info": {"items": [POST_ITEM]}}}).encode()


class LibraryTransport:
    def __init__(self, status=200, body=b"{}", headers=None, error=None):
        self.status, self.body, self.headers, self.error = status, body, dict(headers or {}), error
        self.on_request = self.on_response = None
        self.fetches = []

    def fetch(self, url, **kwargs):
        self.fetches.append((url, kwargs))
        if self.on_request:
            self.on_request()
        if self.error is not None:
            raise self.error
        if self.on_response:
            self.on_response(self.status, self.headers)
        return TransportResponse(url, self.status, {"content-type": "application/json", **self.headers}, self.body)

    def head(self, url, **kwargs):
        return TransportResponse(url, 200, {"content-type": "image/jpeg", "content-length": "100"}, b"")


def library_rate():
    return SimpleNamespace(acquire=Mock(), limited=Mock(), observe=Mock())


def inspect_input(tmp_path, url):
    return InspectInput(source_url=url, request_id="a" * 32, work_directory=tmp_path,
        deadline=time.monotonic() + 30, metadata_limit=65_536)


@pytest.fixture
def no_library_sleep(monkeypatch):
    def sleep(seconds):
        raise AssertionError("a metadata library slept instead of surfacing the upstream outcome")
    monkeypatch.setattr(time, "sleep", sleep)


def test_real_instaloader_lazy_field_reads_stay_inside_the_guard(tmp_path, no_library_sleep):
    original_send = requests.Session.send
    transport, rate = LibraryTransport(body=POST_BODY), library_rate()

    result = InstagramImageAdapter().inspect(
        inspect_input(tmp_path, f"https://www.instagram.com/p/{SHORTCODE}/"), transport=transport, rate_control=rate)

    assert result.metadata.media_id == SHORTCODE and result.metadata.creator == "example_creator"
    # Instaloader first GETs the homepage for a CSRF token, then issues one GraphQL POST.
    queries = [call for _url, call in transport.fetches if call["method"] == "POST"]
    assert len(queries) == 1, "every lazy Post field must be served by the one guarded metadata query"
    assert 1 <= len(transport.fetches) <= 2
    for url, call in transport.fetches:
        assert url.startswith("https://www.instagram.com/")
        assert call["limit"] == 65_536 and call["deadline"] is not None
        assert {key.lower() for key in call["headers"]}.isdisjoint({"cookie", "authorization", "proxy-authorization"})
        assert call["headers"]["Accept-Encoding"] == "identity"
    assert rate.acquire.call_count >= len(transport.fetches), "each library request passes parent rate control"
    assert ("instagram", "metadata") in [item.args for item in rate.acquire.call_args_list]
    assert requests.Session.send is original_send and transport.on_request is None


@pytest.mark.parametrize("status", [429, 500])
def test_real_instaloader_reports_upstream_limits_without_library_retries(tmp_path, no_library_sleep, status):
    transport = LibraryTransport(status=status, body=b'{"status":"fail"}', headers={"retry-after": "75"})
    rate = library_rate()

    with pytest.raises(SourceAdapterError) as caught:
        InstagramImageAdapter().inspect(
            inspect_input(tmp_path, f"https://www.instagram.com/p/{SHORTCODE}/"), transport=transport, rate_control=rate)

    # No retry storm: at most the CSRF GET plus one query, and a 429 aborts on the first response.
    assert len(transport.fetches) <= (1 if status == 429 else 2)
    assert sum(call["method"] == "POST" for _url, call in transport.fetches) <= 1
    rate.observe.assert_called_with("instagram", status)
    if status == 429:
        assert caught.value.category is ErrorCategory.RATE_LIMITED
        rate.limited.assert_called_once_with("instagram", "metadata", retry_after=75)
    else:
        assert caught.value.category is ErrorCategory.UNAVAILABLE
        rate.limited.assert_not_called()


def test_real_instaloader_connection_failure_is_observed_once(tmp_path, no_library_sleep):
    transport, rate = LibraryTransport(error=ConnectionError("reset")), library_rate()

    with pytest.raises(SourceAdapterError) as caught:
        InstagramImageAdapter().inspect(
            inspect_input(tmp_path, f"https://www.instagram.com/p/{SHORTCODE}/"), transport=transport, rate_control=rate)

    assert caught.value.category is ErrorCategory.UNAVAILABLE
    assert len(transport.fetches) == 1
    rate.observe.assert_called_once_with("instagram", None)


def test_real_ytdlp_extractor_requests_are_bounded_and_report_rate_limits(tmp_path, no_library_sleep):
    transport = LibraryTransport(status=429, body=b"", headers={"retry-after": "120"})
    rate = library_rate()

    with pytest.raises(SourceAdapterError) as caught:
        YtDlpAdapter().inspect(inspect_input(tmp_path, "https://www.youtube.com/watch?v=abcDEF12345"),
            transport=transport, rate_control=rate)

    assert caught.value.category is ErrorCategory.RATE_LIMITED
    assert len(transport.fetches) == 1
    url, call = transport.fetches[0]
    assert url.startswith("https://www.youtube.com/") and call["limit"] == 65_536
    assert {key.lower() for key in call["headers"]}.isdisjoint({"cookie", "authorization", "proxy-authorization"})
    rate.limited.assert_called_once_with("youtube", "metadata", retry_after=120)


def test_worker_child_applies_the_socket_guard_around_library_code(monkeypatch, capsys, tmp_path):
    """A library path that bypasses the patched clients must still hit the destination policy."""
    import io
    import socket
    import sys

    import openmedia.sources as sources
    from openmedia import workers

    def inspect(self, request, **kwargs):
        socket.getaddrinfo("internal.example.invalid", 80)
        raise AssertionError("the socket guard was not active inside the worker operation")

    monkeypatch.setattr(sources.SourceRouter, "inspect", inspect)
    message = {"operation": "inspect", "source_url": "https://youtu.be/abcDEF12345", "request_id": "a" * 32,
        "work_directory": str(tmp_path), "deadline": time.monotonic() + 30}
    monkeypatch.setattr(sys, "stdin", io.StringIO(json.dumps(message) + "\n"))
    guarded_before = socket.getaddrinfo

    assert workers._child_main() == 1

    events = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert events[-1] == {"event": "error", "category": "unsafe_destination", "stage": None}
    assert socket.getaddrinfo is guarded_before


# --------------------------------------------------------------------------------------
# Source-issued anonymous cookies live for one Instagram operation and go nowhere else.
# --------------------------------------------------------------------------------------


class CookieTransport:
    """Issues cookies on the first response and records every outgoing header set."""

    def __init__(self, issued=("csrftoken=issued-token; Path=/; Secure", "mid=issued-mid; Path=/"), final_host=None):
        self.issued, self.final_host, self.sent = issued, final_host, []
        self.on_request = self.on_response = None

    def fetch(self, url, **kwargs):
        self.sent.append((url, dict(kwargs["headers"])))
        final = url if self.final_host is None else f"https://{self.final_host}/"
        cookies = self.issued if len(self.sent) == 1 else ()
        return TransportResponse(final, 200, {"content-type": "application/json"}, b"{}", cookies)


def cookie_client(transport, platform="instagram"):
    return MetadataHTTP(transport, library_rate(), SimpleNamespace(deadline=10, metadata_limit=32), platform)


def sent_cookie(headers):
    return next((value for key, value in headers.items() if key.lower() == "cookie"), None)


def test_instagram_operation_returns_only_source_issued_cookies():
    transport = CookieTransport()
    client = cookie_client(transport)
    client.fetch("https://www.instagram.com/", headers={"Cookie": "sessionid=operator-secret"})
    client.fetch("https://www.instagram.com/graphql/query", method="POST", data=b"q", headers={"Cookie": "sessionid=operator-secret"})
    assert sent_cookie(transport.sent[0][1]) is None
    assert sent_cookie(transport.sent[1][1]) == "csrftoken=issued-token; mid=issued-mid"
    assert "operator-secret" not in repr(transport.sent)
    assert "issued-token" not in repr(client) and "issued-token" not in repr(vars(client).keys())


def test_requests_session_receives_issued_cookies_for_the_csrf_header():
    transport = CookieTransport()
    client = cookie_client(transport)
    with client.requests():
        session = requests.Session()
        session.get("https://www.instagram.com/")
        assert session.cookies.get("csrftoken") == "issued-token"
        session.post("https://www.instagram.com/graphql/query", data=b"q")
    assert sent_cookie(transport.sent[1][1]) == "csrftoken=issued-token; mid=issued-mid"


def test_ytdlp_path_uses_the_same_operation_jar():
    transport = CookieTransport()
    client = cookie_client(transport)
    with client.bound():
        client.ytdlp(Request("https://www.instagram.com/reel/abc/"))
        client.ytdlp(Request("https://www.instagram.com/graphql/query", data=b"q"))
    assert sent_cookie(transport.sent[1][1]) == "csrftoken=issued-token; mid=issued-mid"


@pytest.mark.parametrize("platform,url", [("youtube", "https://www.youtube.com/watch?v=x"), ("linkedin", "https://www.linkedin.com/posts/x")])
def test_other_platforms_never_record_or_send_cookies(platform, url):
    transport = CookieTransport()
    client = cookie_client(transport, platform)
    client.fetch(url)
    client.fetch(url, headers={"Cookie": "a=b"})
    assert [sent_cookie(headers) for _url, headers in transport.sent] == [None, None]


def test_jar_is_bound_to_instagram_hosts_in_both_directions():
    transport = CookieTransport()
    client = cookie_client(transport)
    client.fetch("https://www.instagram.com/")
    client.fetch("https://scontent.cdninstagram.com/image")
    client.fetch("https://instagram.com.evil.invalid/")
    assert [sent_cookie(headers) for _url, headers in transport.sent[1:]] == [None, None]

    foreign = CookieTransport(final_host="tracker.example.invalid")
    client = cookie_client(foreign)
    client.fetch("https://www.instagram.com/")
    client.fetch("https://www.instagram.com/graphql/query")
    assert sent_cookie(foreign.sent[1][1]) is None, "cookies set by a non-Instagram final host are not recorded"


def test_operations_share_no_cookies():
    first, second = CookieTransport(), CookieTransport(issued=())
    cookie_client(first).fetch("https://www.instagram.com/")
    other = cookie_client(second)
    other.fetch("https://www.instagram.com/")
    other.fetch("https://www.instagram.com/graphql/query")
    assert [sent_cookie(headers) for _url, headers in second.sent] == [None, None]


def test_no_cookie_file_is_configured_for_ytdlp():
    from openmedia.sources.ytdlp import YTDLP_OPTIONS
    assert YTDLP_OPTIONS["cookiefile"] is None

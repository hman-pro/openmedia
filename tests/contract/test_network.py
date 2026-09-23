from __future__ import annotations

import socket
from pathlib import Path

import pytest

from openmedia.network import (
    FileBoundaryError,
    GuardedHTTPTransport,
    PublicEndpointPolicy,
    ResponseTooLarge,
    UnsafeDestination,
    redirect_headers,
    validate_owned_file,
)


def answer(address: str):
    def resolver(host: str, port: int, **_kwargs: object):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))]

    return resolver


@pytest.mark.parametrize(
    "address",
    ["127.0.0.1", "10.0.0.1", "169.254.1.2", "224.0.0.1", "0.0.0.0"],
)
def test_private_and_special_destinations_are_rejected(address: str) -> None:
    policy = PublicEndpointPolicy(resolver=answer(address))
    with pytest.raises(UnsafeDestination):
        policy.resolve("https://media.example/file")


def test_ipv6_loopback_is_rejected() -> None:
    def resolver(host: str, port: int, **_kwargs: object):
        return [(socket.AF_INET6, socket.SOCK_STREAM, 6, "", ("::1", port, 0, 0))]

    with pytest.raises(UnsafeDestination):
        PublicEndpointPolicy(resolver=resolver).resolve("https://media.example/file")


def test_dns_answers_are_pinned_and_revalidated_per_request() -> None:
    answers = iter(["93.184.216.34", "127.0.0.1"])

    def resolver(host: str, port: int, **_kwargs: object):
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (next(answers), port))]

    policy = PublicEndpointPolicy(resolver=resolver)
    first = policy.resolve("https://media.example/file")
    assert first.addresses == ("93.184.216.34",)
    with pytest.raises(UnsafeDestination):
        policy.resolve("https://media.example/file")


@pytest.mark.parametrize(
    "url",
    [
        "http://media.example/file",
        "https://user:pass@media.example/file",
        "file:///etc/passwd",
    ],
)
def test_unsafe_url_shapes_are_rejected(url: str) -> None:
    with pytest.raises(UnsafeDestination):
        PublicEndpointPolicy(resolver=answer("93.184.216.34")).resolve(url)


def test_redirect_limit_and_host_header_scrubbing() -> None:
    policy = PublicEndpointPolicy(resolver=answer("93.184.216.34"), max_redirects=5)
    policy.check_redirect_count(5)
    with pytest.raises(UnsafeDestination, match="redirect"):
        policy.check_redirect_count(6)

    headers = {
        "Authorization": "secret",
        "Cookie": "session=secret",
        "X-Api-Key": "secret",
        "Accept": "image/*",
    }
    assert redirect_headers(headers, "a.example", "b.example") == {"Accept": "image/*"}
    assert redirect_headers(headers, "a.example", "a.example") == headers


def test_proxy_environment_is_never_inherited(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:8080")
    assert GuardedHTTPTransport.uses_proxy_environment is False


def test_tls_server_name_is_original_hostname() -> None:
    endpoint = PublicEndpointPolicy(resolver=answer("93.184.216.34")).resolve(
        "https://media.example/file"
    )
    assert endpoint.tls_server_name == "media.example"
    assert endpoint.connect_host == "93.184.216.34"


def test_response_limit_counts_streamed_chunks() -> None:
    policy = PublicEndpointPolicy(resolver=answer("93.184.216.34"))
    with pytest.raises(ResponseTooLarge):
        policy.collect_chunks([b"123", b"456"], limit=5)
    assert policy.collect_chunks([b"12", b"34"], limit=4) == b"1234"


@pytest.mark.parametrize("status", [403, 410, 429, 500])
def test_download_http_errors_never_become_media_files(tmp_path, monkeypatch, status):
    from types import SimpleNamespace
    from unittest.mock import Mock
    from openmedia.sources import SourceAdapterError
    transport = GuardedHTTPTransport()
    response = SimpleNamespace(status=status, read=Mock(side_effect=AssertionError("must not read error body")))
    monkeypatch.setattr(transport, "_open", lambda *args, **kwargs: (SimpleNamespace(close=lambda: None), response, "https://example.invalid"))
    with pytest.raises(SourceAdapterError) as caught:
        transport.download("https://example.invalid", tmp_path / "selected.mp4", output_limit=100, workspace_limit=200)
    assert caught.value.category == ("rate_limited" if status == 429 else "unavailable")
    assert not list(tmp_path.iterdir())


def test_compressed_metadata_cannot_expand_past_limit(monkeypatch):
    import gzip, io
    from types import SimpleNamespace
    body = gzip.compress(b"x" * 1000)
    response = SimpleNamespace(status=200, read=io.BytesIO(body).read,
        getheader=lambda name: str(len(body)) if name.lower() == "content-length" else None,
        getheaders=lambda: [("content-encoding", "gzip")])
    transport = GuardedHTTPTransport()
    monkeypatch.setattr(transport, "_open", lambda *args, **kwargs: (SimpleNamespace(close=lambda: None), response, "https://example.invalid"))
    with pytest.raises(ResponseTooLarge):
        transport.fetch("https://example.invalid", limit=100)


def test_real_transport_limits_metadata_client_redirects(monkeypatch):
    from types import SimpleNamespace
    from unittest.mock import Mock
    from openmedia.sources.http import MetadataHTTP
    class Connection:
        def __init__(self, *args, **kwargs): pass
        def request(self, *args, **kwargs): pass
        def getresponse(self):
            return SimpleNamespace(status=302, getheaders=lambda: [], getheader=lambda name: "https://example.invalid/next")
        def close(self): pass
    monkeypatch.setattr("openmedia.network._PinnedHTTPSConnection", Connection)
    transport = GuardedHTTPTransport(policy=PublicEndpointPolicy(resolver=answer("93.184.216.34")))
    rate = SimpleNamespace(acquire=Mock(), limited=Mock())
    client = MetadataHTTP(transport, rate, SimpleNamespace(deadline=transport.monotonic()+10, metadata_limit=100), "youtube")
    with client.bound(), pytest.raises(UnsafeDestination):
        client.ytdlp("https://example.invalid")
    assert rate.acquire.call_count == 6


def test_output_must_be_regular_and_inside_owned_directory(tmp_path: Path) -> None:
    owned = tmp_path / "owned"
    owned.mkdir()
    output = owned / "result.bin"
    output.write_bytes(b"safe")
    assert validate_owned_file(output, owned, max_bytes=4) == 4

    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"outside")
    with pytest.raises(FileBoundaryError):
        validate_owned_file(outside, owned, max_bytes=100)

    symlink = owned / "link.bin"
    symlink.symlink_to(outside)
    with pytest.raises(FileBoundaryError):
        validate_owned_file(symlink, owned, max_bytes=100)


def test_actual_file_size_is_enforced(tmp_path: Path) -> None:
    output = tmp_path / "large.bin"
    output.write_bytes(b"12345")
    with pytest.raises(ResponseTooLarge):
        validate_owned_file(output, tmp_path, max_bytes=4)


def test_repeated_set_cookie_headers_survive_outside_the_header_dict(monkeypatch):
    import io
    from types import SimpleNamespace
    pairs = [("Set-Cookie", "csrftoken=abc; Path=/; Secure"), ("Content-Type", "text/html"), ("set-cookie", "mid=xyz; Path=/")]
    response = SimpleNamespace(status=200, read=io.BytesIO(b"ok").read, getheader=lambda name: None, getheaders=lambda: pairs)
    transport = GuardedHTTPTransport()
    monkeypatch.setattr(transport, "_open", lambda *args, **kwargs: (SimpleNamespace(close=lambda: None), response, "https://example.invalid"))
    result = transport.fetch("https://example.invalid", limit=100)
    assert result.set_cookies == ("csrftoken=abc; Path=/; Secure", "mid=xyz; Path=/")
    assert "abc" not in repr(result) and "xyz" not in repr(result)
    assert transport.head("https://example.invalid").set_cookies == result.set_cookies


def _ranged_source(monkeypatch, transport, body: bytes):
    # Serves `&range=a-b` query pieces the way YouTube does: 200 with only the requested bytes.
    import io
    import re
    from types import SimpleNamespace
    requested: list[str] = []

    def open_(url, **_kwargs):
        requested.append(url)
        start, end = map(int, re.search(r"[?&]range=(\d+)-(\d+)$", url).groups())
        piece = body[start:end + 1]
        response = SimpleNamespace(status=200, read=io.BytesIO(piece).read,
            getheader=lambda name: str(len(piece)) if name.lower() == "content-length" else None)
        return SimpleNamespace(close=lambda: None), response, url

    monkeypatch.setattr(transport, "_open", open_)
    return requested


@pytest.mark.parametrize("size", [10, 8])
def test_ranged_download_fetches_bounded_pieces_into_one_file(tmp_path, monkeypatch, size):
    # YouTube throttles a whole-file GET to about playback speed; ranged pieces arrive at full speed.
    body = bytes(range(size))
    transport = GuardedHTTPTransport()
    requested = _ranged_source(monkeypatch, transport, body)
    destination = tmp_path / "component-audio"
    written = transport.download("https://media.example/a?id=1", destination, output_limit=100,
        workspace_limit=200, range_bytes=4)
    assert written == size and destination.read_bytes() == body
    assert requested[:3] == ["https://media.example/a?id=1&range=0-3", "https://media.example/a?id=1&range=4-7",
        "https://media.example/a?id=1&range=8-11"]


def test_ranged_download_enforces_the_limit_across_pieces(tmp_path, monkeypatch):
    transport = GuardedHTTPTransport()
    _ranged_source(monkeypatch, transport, bytes(10))
    with pytest.raises(ResponseTooLarge):
        transport.download("https://media.example/a?id=1", tmp_path / "component-audio", output_limit=6,
            workspace_limit=200, range_bytes=4)
    assert not list(tmp_path.iterdir())


SHARE_POST_LOCATION = "https://www.linkedin.com/posts/x-share-7508424761698410497-2cX9/"


def _scripted_connections(monkeypatch, statuses):
    # Each opened connection answers with the next scripted status; a 301 points at the LinkedIn post.
    from types import SimpleNamespace
    opened: list[object] = []
    remaining = iter(statuses)

    class Connection:
        def __init__(self, *args, **kwargs):
            opened.append(self)
            self.status = next(remaining)

        def request(self, *args, **kwargs):
            pass

        def getresponse(self):
            location = SHARE_POST_LOCATION if self.status == 301 else None
            pairs = [("Location", location)] if location else []
            return SimpleNamespace(
                status=self.status,
                getheaders=lambda: pairs,
                getheader=lambda name: location if name.lower() == "location" else None,
            )

        def close(self):
            pass

    monkeypatch.setattr("openmedia.network._PinnedHTTPSConnection", Connection)
    return opened


def test_head_without_following_returns_the_first_redirect(monkeypatch):
    from unittest.mock import Mock
    opened = _scripted_connections(monkeypatch, [301, 200])
    transport = GuardedHTTPTransport(policy=PublicEndpointPolicy(resolver=answer("93.184.216.34")))
    transport.on_request = Mock()
    result = transport.head("https://lnkd.in/eAbCdEf", follow_redirects=False)
    assert result.status == 301
    assert result.headers["location"] == SHARE_POST_LOCATION
    assert len(opened) == 1
    assert transport.on_request.call_count == 1


def test_head_follows_redirects_by_default(monkeypatch):
    opened = _scripted_connections(monkeypatch, [301, 200])
    transport = GuardedHTTPTransport(policy=PublicEndpointPolicy(resolver=answer("93.184.216.34")))
    result = transport.head("https://lnkd.in/eAbCdEf")
    assert result.status == 200
    assert len(opened) == 2


@pytest.mark.parametrize(
    ("url", "address"),
    [("http://lnkd.in/eAbCdEf", "93.184.216.34"), ("https://lnkd.in/eAbCdEf", "127.0.0.1")],
)
def test_head_without_following_still_enforces_the_endpoint_policy(monkeypatch, url, address):
    opened = _scripted_connections(monkeypatch, [301])
    transport = GuardedHTTPTransport(policy=PublicEndpointPolicy(resolver=answer(address)))
    with pytest.raises(UnsafeDestination):
        transport.head(url, follow_redirects=False)
    assert opened == []


def test_head_without_following_reports_its_status_to_the_response_hook(monkeypatch):
    # The worker's rate-limit hook must see a 429 on the short-link HEAD, as for any request.
    seen: list[int] = []
    opened = _scripted_connections(monkeypatch, [429])
    transport = GuardedHTTPTransport(policy=PublicEndpointPolicy(resolver=answer("93.184.216.34")))

    def hook(status, headers):
        seen.append(status)
        raise RuntimeError("rate limited")

    transport.on_response = hook
    with pytest.raises(RuntimeError, match="rate limited"):
        transport.head("https://lnkd.in/p/dAjqaykT", follow_redirects=False)
    assert seen == [429]
    assert len(opened) == 1

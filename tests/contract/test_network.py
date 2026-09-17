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

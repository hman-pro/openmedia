"""Public-destination HTTP transport and request-owned file validation."""

from __future__ import annotations

import http.client
import ipaddress
import os
import socket
import ssl
import zlib
import stat
import time
from collections.abc import Callable, Iterable, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import SplitResult, urljoin, urlsplit

from openmedia.sources import TransportResponse


METADATA_LIMIT = 8 * 1024 * 1024
THUMBNAIL_LIMIT = 1024 * 1024
SENSITIVE_REDIRECT_HEADERS = frozenset(
    {"authorization", "cookie", "proxy-authorization", "x-api-key"}
)
REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})


class NetworkBoundaryError(RuntimeError):
    pass


class UnsafeDestination(NetworkBoundaryError):
    pass


class ResponseTooLarge(NetworkBoundaryError):
    pass


class FileBoundaryError(NetworkBoundaryError):
    pass


@dataclass(frozen=True, slots=True)
class PublicEndpoint:
    url: str
    hostname: str
    port: int
    request_target: str
    addresses: tuple[str, ...]

    @property
    def connect_host(self) -> str:
        return self.addresses[0]

    @property
    def tls_server_name(self) -> str:
        return self.hostname


class PublicEndpointPolicy:
    """Validate and pin a fresh set of public addresses for one connection."""

    def __init__(
        self,
        *,
        resolver: Callable[..., list[tuple[object, ...]]] = socket.getaddrinfo,
        max_redirects: int = 5,
    ) -> None:
        self._resolver = resolver
        self.max_redirects = max_redirects

    def resolve(self, url: str) -> PublicEndpoint:
        parts = urlsplit(url)
        self._validate_url(parts)
        assert parts.hostname is not None
        hostname = parts.hostname.rstrip(".").lower()
        port = parts.port or 443
        try:
            answers = self._resolver(
                hostname, port, type=socket.SOCK_STREAM, proto=socket.IPPROTO_TCP
            )
        except (OSError, UnicodeError) as exc:
            raise UnsafeDestination("destination name could not be safely resolved") from exc
        addresses: list[str] = []
        for answer in answers:
            sockaddr = answer[4]
            address = str(sockaddr[0])
            try:
                parsed = ipaddress.ip_address(address)
            except ValueError as exc:
                raise UnsafeDestination("resolver returned an invalid address") from exc
            if (
                not parsed.is_global
                or parsed.is_multicast
                or parsed.is_reserved
                or parsed.is_unspecified
                or parsed.is_loopback
                or parsed.is_link_local
                or parsed.is_private
            ):
                raise UnsafeDestination("destination resolved to a non-public address")
            normalized = parsed.compressed
            if normalized not in addresses:
                addresses.append(normalized)
        if not addresses:
            raise UnsafeDestination("destination has no public address")
        target = parts.path or "/"
        if parts.query:
            target = f"{target}?{parts.query}"
        return PublicEndpoint(url, hostname, port, target, tuple(addresses))

    def check_redirect_count(self, count: int) -> None:
        if count > self.max_redirects:
            raise UnsafeDestination("redirect limit exceeded")

    @staticmethod
    def collect_chunks(chunks: Iterable[bytes], *, limit: int) -> bytes:
        if limit <= 0:
            raise ValueError("response limit must be positive")
        body = bytearray()
        for chunk in chunks:
            if len(body) + len(chunk) > limit:
                raise ResponseTooLarge(f"response exceeded {limit} bytes")
            body.extend(chunk)
        return bytes(body)

    @staticmethod
    def _validate_url(parts: SplitResult) -> None:
        if parts.scheme.lower() != "https":
            raise UnsafeDestination("only HTTPS destinations are allowed")
        if not parts.hostname:
            raise UnsafeDestination("destination hostname is required")
        if parts.username is not None or parts.password is not None:
            raise UnsafeDestination("URL userinfo is forbidden")
        if parts.fragment:
            raise UnsafeDestination("URL fragments are not sent to source transports")
        try:
            port = parts.port
        except ValueError as exc:
            raise UnsafeDestination("destination port is invalid") from exc
        if port is not None and port != 443:
            raise UnsafeDestination("only the HTTPS default port is allowed")


def redirect_headers(
    headers: Mapping[str, str], old_hostname: str, new_hostname: str
) -> dict[str, str]:
    if old_hostname.rstrip(".").lower() == new_hostname.rstrip(".").lower():
        return dict(headers)
    return {
        name: value
        for name, value in headers.items()
        if name.lower() not in SENSITIVE_REDIRECT_HEADERS
    }


def _single_headers(response: http.client.HTTPResponse) -> dict[str, str]:
    # Set-Cookie repeats and carries values; it travels in TransportResponse.set_cookies instead.
    return {name.lower(): value for name, value in response.getheaders() if name.lower() != "set-cookie"}


def _set_cookies(response: http.client.HTTPResponse) -> tuple[str, ...]:
    return tuple(value for name, value in response.getheaders() if name.lower() == "set-cookie")


class _PinnedHTTPSConnection(http.client.HTTPSConnection):
    """Connect to a validated address while verifying the original TLS hostname."""

    def __init__(
        self,
        endpoint: PublicEndpoint,
        *,
        timeout: float,
        context: ssl.SSLContext,
    ) -> None:
        super().__init__(endpoint.hostname, endpoint.port, timeout=timeout, context=context)
        self._endpoint = endpoint

    def connect(self) -> None:
        raw_socket = socket.create_connection(
            (self._endpoint.connect_host, self._endpoint.port), self.timeout
        )
        try:
            self.sock = self._context.wrap_socket(
                raw_socket, server_hostname=self._endpoint.tls_server_name
            )
        except BaseException:
            raw_socket.close()
            raise


class GuardedHTTPTransport:
    """A direct HTTPS transport that never inherits proxy configuration."""

    uses_proxy_environment = False

    def __init__(
        self,
        *,
        policy: PublicEndpointPolicy | None = None,
        ssl_context: ssl.SSLContext | None = None,
        monotonic: Callable[[], float] = time.monotonic,
        chunk_size: int = 64 * 1024,
    ) -> None:
        self.policy = policy or PublicEndpointPolicy()
        self.ssl_context = ssl_context or ssl.create_default_context()
        self.monotonic = monotonic
        self.chunk_size = chunk_size
        self.on_request = None
        self.on_response = None

    def head(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None = None,
        deadline: float | None = None,
    ) -> TransportResponse:
        connection, response, final_url = self._open(
            url, headers=headers, deadline=deadline, method="HEAD"
        )
        try:
            response_headers = _single_headers(response)
            return TransportResponse(final_url, response.status, response_headers, b"", _set_cookies(response))
        finally:
            connection.close()

    def fetch(
        self,
        url: str,
        *,
        limit: int,
        headers: Mapping[str, str] | None = None,
        deadline: float | None = None,
        method: str = "GET",
        data: bytes | None = None,
    ) -> TransportResponse:
        connection, response, final_url = self._open(
            url, headers=headers, deadline=deadline, method=method, data=data
        )
        try:
            self._check_content_length(response, limit)
            body = self.policy.collect_chunks(
                iter(lambda: response.read(self.chunk_size), b""), limit=limit
            )
            response_headers = _single_headers(response)
            encoding = response_headers.get("content-encoding", "identity").lower()
            if encoding in {"gzip", "deflate"}:
                decoder = zlib.decompressobj(16 + zlib.MAX_WBITS if encoding == "gzip" else zlib.MAX_WBITS)
                body = decoder.decompress(body, limit + 1)
                if len(body) > limit or decoder.unconsumed_tail:
                    raise ResponseTooLarge("decoded metadata exceeds limit")
                if not decoder.eof:
                    raise NetworkBoundaryError("incomplete compressed metadata")
                response_headers.pop("content-encoding", None)
                response_headers["content-length"] = str(len(body))
            elif encoding != "identity":
                raise NetworkBoundaryError("unsupported metadata encoding")
            return TransportResponse(final_url, response.status, response_headers, body, _set_cookies(response))
        finally:
            connection.close()

    def fetch_metadata(
        self, url: str, *, headers: Mapping[str, str] | None = None, deadline: float | None = None
    ) -> TransportResponse:
        return self.fetch(url, limit=METADATA_LIMIT, headers=headers, deadline=deadline)

    def fetch_thumbnail(
        self, url: str, *, headers: Mapping[str, str] | None = None, deadline: float | None = None
    ) -> TransportResponse:
        return self.fetch(url, limit=THUMBNAIL_LIMIT, headers=headers, deadline=deadline)

    def download(
        self,
        url: str,
        destination: Path,
        *,
        output_limit: int,
        workspace_limit: int,
        headers: Mapping[str, str] | None = None,
        deadline: float | None = None,
        range_bytes: int | None = None,
    ) -> int:
        """Stream one URL into a new owned file.

        With ``range_bytes``, the file is fetched as ``range=start-end`` query pieces of at most
        that size, as yt-dlp does for YouTube: a whole-file GET is throttled to about playback
        speed. A piece shorter than requested ends the file.
        """
        if output_limit <= 0 or workspace_limit <= 0:
            raise ValueError("download limits must be positive")
        if range_bytes is not None and range_bytes <= 0:
            raise ValueError("range_bytes must be positive")
        destination = Path(destination)
        if not destination.is_absolute() or destination.name in ("", ".", ".."):
            raise FileBoundaryError("destination must be a named absolute path")
        parent = destination.parent.resolve(strict=True)
        if parent != destination.parent:
            raise FileBoundaryError("destination parent cannot traverse a symlink")
        used = workspace_usage(parent)
        remaining_workspace = workspace_limit - used
        if remaining_workspace <= 0:
            raise ResponseTooLarge("workspace limit is already exhausted")
        limit = min(output_limit, remaining_workspace)

        descriptor: int | None = None
        written = 0

        def create() -> int:
            # Created only once the source answered 2xx, so a refused attempt leaves nothing behind.
            nonlocal descriptor
            if descriptor is None:
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
                if hasattr(os, "O_NOFOLLOW"):
                    flags |= os.O_NOFOLLOW
                descriptor = os.open(destination, flags, 0o600)
            return descriptor

        try:
            while True:
                piece_url = url
                if range_bytes is not None:
                    separator = "&" if urlsplit(url).query else "?"
                    piece_url = f"{url}{separator}range={written}-{written + range_bytes - 1}"
                piece = self._download_piece(piece_url, create, headers=headers, deadline=deadline,
                    limit=limit, written=written)
                written += piece
                if range_bytes is None or piece < range_bytes:
                    break
            os.fsync(create())
        except BaseException:
            if descriptor is not None:
                os.close(descriptor)
                descriptor = None
            try:
                destination.unlink()
            except FileNotFoundError:
                pass
            raise
        finally:
            if descriptor is not None:
                os.close(descriptor)
        validate_owned_file(destination, parent, max_bytes=output_limit)
        return written

    def _download_piece(
        self,
        url: str,
        create: Callable[[], int],
        *,
        headers: Mapping[str, str] | None,
        deadline: float | None,
        limit: int,
        written: int,
    ) -> int:
        connection, response, _final_url = self._open(url, headers=headers, deadline=deadline)
        try:
            if not 200 <= response.status < 300:
                # Classified from the status line alone; the error body is never read or written.
                from openmedia.sources import EXPIRED_URL, SourceAdapterError, ErrorCategory
                category = ErrorCategory.RATE_LIMITED if response.status == 429 else ErrorCategory.UNAVAILABLE
                detail = EXPIRED_URL if response.status in {403, 410} else None
                raise SourceAdapterError(category, stage="download", detail=detail)
            self._check_content_length(response, limit - written)
            descriptor = create()
            received = 0
            while chunk := response.read(self.chunk_size):
                if written + received + len(chunk) > limit:
                    raise ResponseTooLarge(f"download exceeded {limit} bytes")
                view = memoryview(chunk)
                while view:
                    count = os.write(descriptor, view)
                    view = view[count:]
                received += len(chunk)
            return received
        finally:
            connection.close()

    def _open(
        self,
        url: str,
        *,
        headers: Mapping[str, str] | None,
        deadline: float | None,
        method: str = "GET",
        data: bytes | None = None,
    ) -> tuple[_PinnedHTTPSConnection, http.client.HTTPResponse, str]:
        current_url = url
        current_headers = dict(headers or {})
        current_headers.setdefault("User-Agent", "OpenMedia/0.1")
        for redirect_count in range(self.policy.max_redirects + 1):
            if self.on_request is not None:
                self.on_request()
            endpoint = self.policy.resolve(current_url)
            timeout = self._remaining(deadline)
            connection = _PinnedHTTPSConnection(
                endpoint, timeout=timeout, context=self.ssl_context
            )
            try:
                connection.request(method, endpoint.request_target, body=data, headers=current_headers)
                response = connection.getresponse()
                if self.on_response is not None:
                    self.on_response(response.status, {key.lower(): value for key, value in response.getheaders()})
            except BaseException:
                connection.close()
                raise
            if response.status not in REDIRECT_STATUSES:
                return connection, response, current_url
            location = response.getheader("Location")
            connection.close()
            if not location:
                raise UnsafeDestination("redirect response omitted Location")
            next_url = urljoin(current_url, location)
            if response.status == 303 or (response.status in {301, 302} and method == "POST"):
                method, data = "GET", None
            self.policy.check_redirect_count(redirect_count + 1)
            next_parts = urlsplit(next_url)
            old_parts = urlsplit(current_url)
            if not next_parts.hostname:
                raise UnsafeDestination("redirect destination has no hostname")
            current_headers = redirect_headers(
                current_headers, old_parts.hostname or "", next_parts.hostname
            )
            current_url = next_url
        raise UnsafeDestination("redirect limit exceeded")

    def _remaining(self, deadline: float | None) -> float:
        if deadline is None:
            return 30.0
        remaining = deadline - self.monotonic()
        if remaining <= 0:
            raise TimeoutError("network deadline expired")
        return min(remaining, 30.0)

    @staticmethod
    def _check_content_length(response: http.client.HTTPResponse, limit: int) -> None:
        raw_length = response.getheader("Content-Length")
        if raw_length is None:
            return
        try:
            length = int(raw_length, 10)
        except ValueError as exc:
            raise NetworkBoundaryError("invalid Content-Length") from exc
        if length < 0:
            raise NetworkBoundaryError("invalid Content-Length")
        if length > limit:
            raise ResponseTooLarge(f"response declared {length} bytes, limit is {limit}")


def workspace_usage(directory: Path) -> int:
    """Count regular files without following symlinks."""
    total = 0
    pending = [Path(directory)]
    while pending:
        current = pending.pop()
        for entry in current.iterdir():
            info = entry.lstat()
            if stat.S_ISLNK(info.st_mode):
                raise FileBoundaryError("workspace contains a symlink")
            if stat.S_ISREG(info.st_mode):
                total += info.st_size
            elif stat.S_ISDIR(info.st_mode):
                pending.append(entry)
            else:
                raise FileBoundaryError("workspace contains a special file")
    return total


def validate_owned_file(path: Path, owned_directory: Path, *, max_bytes: int) -> int:
    """Validate a worker result without following a symlink or accepting traversal."""
    if max_bytes < 0:
        raise ValueError("max_bytes cannot be negative")
    try:
        owned = Path(owned_directory).resolve(strict=True)
        candidate = Path(path)
        info = candidate.lstat()
    except (FileNotFoundError, OSError) as exc:
        raise FileBoundaryError("worker result does not exist safely") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISREG(info.st_mode):
        raise FileBoundaryError("worker result must be a regular non-symlink file")
    try:
        resolved = candidate.resolve(strict=True)
        resolved.relative_to(owned)
    except (ValueError, OSError) as exc:
        raise FileBoundaryError("worker result is outside its owned directory") from exc
    if info.st_size > max_bytes:
        raise ResponseTooLarge(f"worker result exceeded {max_bytes} bytes")
    return info.st_size


@contextmanager
def guard_public_sockets(policy: PublicEndpointPolicy):
    """Apply the destination policy to third-party HTTP clients inside one worker.

    Standard TLS clients keep the original hostname for certificate verification while
    their connect-time DNS answer is validated immediately before use. Workers are
    single-purpose subprocesses, so this process-local patch cannot affect unrelated jobs.
    """
    original = socket.getaddrinfo

    def guarded(host: object, port: object, *args: object, **kwargs: object):
        if not isinstance(host, str):
            raise UnsafeDestination("destination hostname must be text")
        try:
            numeric_port = int(port) if port is not None else 443
        except (TypeError, ValueError) as exc:
            raise UnsafeDestination("destination port is invalid") from exc
        if numeric_port != 443:
            raise UnsafeDestination("only HTTPS destinations are allowed")
        answers = original(host, numeric_port, *args, **kwargs)
        for answer in answers:
            address = ipaddress.ip_address(str(answer[4][0]))
            if (
                not address.is_global
                or address.is_multicast
                or address.is_reserved
                or address.is_unspecified
                or address.is_loopback
                or address.is_link_local
                or address.is_private
            ):
                raise UnsafeDestination("destination resolved to a non-public address")
        if not answers:
            raise UnsafeDestination("destination has no public address")
        return answers

    socket.getaddrinfo = guarded  # type: ignore[assignment]
    try:
        yield
    finally:
        socket.getaddrinfo = original  # type: ignore[assignment]

"""Bound the HTTP interfaces used by the two reused metadata libraries."""

from contextlib import contextmanager
from io import BytesIO
from unittest.mock import patch
from urllib.parse import urlsplit

from openmedia.sources import ErrorCategory, SourceAdapterError


class MetadataHTTP:
    def __init__(self, transport, rate, request, platform):
        self.transport, self.rate, self.request, self.platform = transport, rate, request, platform
        # Cookies Instagram issues to a logged-out visitor, held for this one operation only.
        self._cookies: dict[str, str] = {}

    def __repr__(self):
        return f"MetadataHTTP(platform={self.platform!r})"

    def _carries_cookies(self, url):
        host = (urlsplit(str(url)).hostname or "").rstrip(".").lower()
        return self.platform == "instagram" and (host == "instagram.com" or host.endswith(".instagram.com"))

    def _record_cookies(self, response):
        if not self._carries_cookies(response.url):
            return
        for line in response.set_cookies:
            name, separator, value = line.split(";", 1)[0].partition("=")
            if separator and name.strip():
                self._cookies[name.strip()] = value.strip()

    def fetch(self, url, *, method="GET", headers=None, data=None):
        headers = {key: value for key, value in dict(headers or {}).items()
            if key.lower() not in {"cookie", "authorization", "proxy-authorization", "accept-encoding"}}
        headers["Accept-Encoding"] = "identity"
        # Caller-supplied cookies were dropped above; only this operation's jar is ever sent.
        if self._cookies and self._carries_cookies(url):
            headers["Cookie"] = "; ".join(f"{name}={value}" for name, value in self._cookies.items())
        if data is not None and not isinstance(data, bytes):
            if isinstance(data, str):
                data = data.encode()
            else:
                raise SourceAdapterError(ErrorCategory.INVALID_SOURCE_RESPONSE, stage="inspection")
        try:
            response = self.transport.fetch(str(url), method=method, data=data, headers=headers,
                limit=self.request.metadata_limit, deadline=self.request.deadline)
        except (ConnectionError, TimeoutError, OSError):
            observe = getattr(self.rate, "observe", None)
            if observe:
                observe(self.platform, None)
            raise
        self._record_cookies(response)
        return response

    @contextmanager
    def bound(self):
        # Workers are single-operation processes; hooks cover redirects as well as initial requests.
        previous_request = getattr(self.transport, "on_request", None)
        previous_response = getattr(self.transport, "on_response", None)
        def before():
            self.rate.acquire(self.platform, "metadata", deadline=self.request.deadline)
        def after(status, headers):
            observe = getattr(self.rate, "observe", None)
            if observe:
                observe(self.platform, status)
            if status == 429:
                raw = headers.get("retry-after", "")
                retry = float(raw) if raw.isdigit() else None
                self.rate.limited(self.platform, "metadata", retry_after=retry)
                raise SourceAdapterError(ErrorCategory.RATE_LIMITED, stage="inspection")
        self.transport.on_request, self.transport.on_response = before, after
        try:
            yield
        finally:
            self.transport.on_request, self.transport.on_response = previous_request, previous_response

    def ytdlp(self, request):
        from yt_dlp.networking import Request, Response
        from yt_dlp.networking.exceptions import HTTPError
        if isinstance(request, str):
            request = Request(request)
        response = self.fetch(request.url, method=request.method, headers=request.headers, data=request.data)
        wrapped = Response(BytesIO(response.body), response.url, response.headers, status=response.status)
        if response.status >= 400:
            raise HTTPError(wrapped)
        return wrapped

    @contextmanager
    def requests(self):
        import requests
        def send(session, request, **kwargs):
            response = self.fetch(request.url, method=request.method, headers=request.headers, data=request.body)
            wrapped = requests.Response()
            wrapped.status_code, wrapped.url = response.status, response.url
            wrapped.headers.update(response.headers)
            wrapped._content = response.body
            wrapped.request = request
            # Instaloader derives its X-CSRFToken header from the session's own jar.
            if self._carries_cookies(response.url):
                for name, value in self._cookies.items():
                    session.cookies.set(name, value, domain=".instagram.com", path="/")
            wrapped.encoding = requests.utils.get_encoding_from_headers(wrapped.headers)
            return wrapped
        with self.bound(), patch.object(requests.Session, "send", send):
            yield

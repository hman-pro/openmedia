"""Bound the HTTP interfaces used by the two reused metadata libraries."""

from contextlib import contextmanager
from io import BytesIO
from unittest.mock import patch

from openmedia.sources import ErrorCategory, SourceAdapterError


class MetadataHTTP:
    def __init__(self, transport, rate, request, platform):
        self.transport, self.rate, self.request, self.platform = transport, rate, request, platform

    def fetch(self, url, *, method="GET", headers=None, data=None):
        headers = {key: value for key, value in dict(headers or {}).items()
            if key.lower() not in {"cookie", "authorization", "proxy-authorization", "accept-encoding"}}
        headers["Accept-Encoding"] = "identity"
        if data is not None and not isinstance(data, bytes):
            if isinstance(data, str):
                data = data.encode()
            else:
                raise SourceAdapterError(ErrorCategory.INVALID_SOURCE_RESPONSE, stage="inspection")
        try:
            return self.transport.fetch(str(url), method=method, data=data, headers=headers,
                limit=self.request.metadata_limit, deadline=self.request.deadline)
        except (ConnectionError, TimeoutError, OSError):
            observe = getattr(self.rate, "observe", None)
            if observe:
                observe(self.platform, None)
            raise

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
            wrapped.encoding = requests.utils.get_encoding_from_headers(wrapped.headers)
            return wrapped
        with self.bound(), patch.object(requests.Session, "send", send):
            yield

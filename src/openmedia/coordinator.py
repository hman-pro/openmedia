"""Atomic in-memory request ownership and capacity primitives."""

from __future__ import annotations

import asyncio
import secrets
import time
from collections import OrderedDict
from collections.abc import Awaitable, Callable, Sequence
from contextlib import asynccontextmanager
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any, AsyncIterator

from openmedia.models import (
    DeliveryResult,
    DownloadRequest,
    FormatOption,
    MediaMetadata,
    RequestState,
)
from openmedia.sources import DownloadResult, InspectResult


class AdmissionOutcome(StrEnum):
    ADMITTED = "admitted"
    REPLACED = "replaced"
    USER_BUSY = "user_busy"
    WORK_BUSY = "work_busy"
    INSTAGRAM_BUSY = "instagram_busy"
    PENDING_FULL = "pending_full"
    DUPLICATE_ID = "duplicate_id"


class SelectionOutcome(StrEnum):
    ACCEPTED = "accepted"
    PROCESSING = "processing"
    WORK_BUSY = "work_busy"
    INSTAGRAM_BUSY = "instagram_busy"
    NOT_FOUND = "not_found"
    NOT_OWNER = "not_owner"
    STALE = "stale"
    EXPIRED = "expired"
    COMPLETED = "completed"
    REPLACED = "replaced"
    INVALID_OPTION = "invalid_option"


@dataclass(frozen=True, slots=True)
class AdmissionResult:
    outcome: AdmissionOutcome
    request: DownloadRequest | None = None
    replaced_request_id: str | None = None


@dataclass(frozen=True, slots=True)
class SelectionResult:
    outcome: SelectionOutcome
    request: DownloadRequest | None = None
    option: FormatOption | None = None


@dataclass(frozen=True, slots=True)
class TerminalRecord:
    request_id: str
    user_id: int
    chat_id: int
    state: RequestState
    terminal_at: float
    confirmed_message_id: int | None = None


@dataclass(slots=True)
class _LockEntry:
    lock: asyncio.Lock
    references: int = 0


Notifier = Callable[[], Awaitable[Any]]


class RequestRegistry:
    """Own all mutable request state and reserve finite capacity without waiting."""

    def __init__(
        self,
        *,
        max_workers: int = 2,
        max_instagram_workers: int = 1,
        max_pending: int = 100,
        selection_seconds: int = 900,
        processing_seconds: int = 600,
        terminal_ttl: int = 900,
        terminal_limit: int = 1_000,
        monotonic: Callable[[], float] = time.monotonic,
    ) -> None:
        for name, value in (
            ("max_workers", max_workers),
            ("max_instagram_workers", max_instagram_workers),
            ("max_pending", max_pending),
            ("terminal_ttl", terminal_ttl),
            ("terminal_limit", terminal_limit),
        ):
            if value <= 0:
                raise ValueError(f"{name} must be positive")
        if max_instagram_workers > max_workers:
            raise ValueError("Instagram worker capacity cannot exceed global capacity")
        self.max_workers = max_workers
        self.max_instagram_workers = max_instagram_workers
        self.max_pending = max_pending
        self.selection_seconds = selection_seconds
        self.processing_seconds = processing_seconds
        self.terminal_ttl = terminal_ttl
        self.terminal_limit = terminal_limit
        self.monotonic = monotonic

        self.requests_by_id: dict[str, DownloadRequest] = {}
        self.active_request_by_user: dict[int, str] = {}
        self.terminal_by_id: OrderedDict[str, TerminalRecord] = OrderedDict()
        self._user_locks: dict[int, _LockEntry] = {}
        self._registry_lock = asyncio.Lock()
        self._work_reservations: set[str] = set()
        self._instagram_reservations: set[str] = set()
        self._pending_reservations: set[str] = set()
        self._closed = False
        self.source_busy: Callable[[str], bool] = lambda platform: False

    @property
    def active_work_count(self) -> int:
        return len(self._work_reservations)

    @property
    def instagram_work_count(self) -> int:
        return len(self._instagram_reservations)

    @property
    def pending_count(self) -> int:
        return len(self._pending_reservations)

    @property
    def user_lock_count(self) -> int:
        return len(self._user_locks)

    def new_request(
        self,
        *,
        user_id: int,
        chat_id: int,
        source_url: str,
        platform: str,
        media_id: str,
    ) -> DownloadRequest:
        return DownloadRequest(
            request_id=secrets.token_hex(16),
            user_id=user_id,
            chat_id=chat_id,
            source_url=source_url,
            platform=platform,
            media_id=media_id,
            state=RequestState.CHECKING,
            created_at=self.monotonic(),
        )

    async def admit(self, request: DownloadRequest) -> AdmissionResult:
        if request.state is not RequestState.CHECKING:
            raise ValueError("new requests must start in checking state")
        async with self._user_guard(request.user_id):
            async with self._registry_lock:
                self._prune_terminal_locked(self.monotonic())
                if self._closed:
                    return AdmissionResult(AdmissionOutcome.WORK_BUSY)
                if request.request_id in self.requests_by_id or request.request_id in self.terminal_by_id:
                    return AdmissionResult(AdmissionOutcome.DUPLICATE_ID)
                active_id = self.active_request_by_user.get(request.user_id)
                active = self.requests_by_id.get(active_id) if active_id else None
                if active is not None and active.state is not RequestState.AWAITING_SELECTION:
                    return AdmissionResult(AdmissionOutcome.USER_BUSY, active)
                capacity = self._capacity_outcome(request.platform, needs_pending=active is None)
                if capacity is not None:
                    # Most importantly, do not invalidate an existing awaiting preview.
                    return AdmissionResult(capacity, active)

                replaced_id: str | None = None
                if active is not None:
                    replaced_id = active.request_id
                    self._pending_reservations.discard(active.request_id)
                    self._terminalize_locked(active, RequestState.REPLACED, self.monotonic())

                self.requests_by_id[request.request_id] = request
                self.active_request_by_user[request.user_id] = request.request_id
                self._work_reservations.add(request.request_id)
                self._pending_reservations.add(request.request_id)
                if self._is_instagram(request):
                    self._instagram_reservations.add(request.request_id)
                outcome = AdmissionOutcome.REPLACED if replaced_id else AdmissionOutcome.ADMITTED
                return AdmissionResult(outcome, request, replaced_id)

    async def publish_preview(
        self,
        request_id: str,
        *,
        metadata: MediaMetadata,
        options: Sequence[FormatOption],
        preview_message_id: int,
        now: float | None = None,
    ) -> bool:
        """Publish only while the same request is still the active checking request."""
        async with self._registry_lock:
            request = self.requests_by_id.get(request_id)
            if (
                request is None
                or request.state is not RequestState.CHECKING
                or self.active_request_by_user.get(request.user_id) != request_id
                or request_id not in self._work_reservations
            ):
                return False
            bound_options = tuple(options)
            if not bound_options:
                raise ValueError("a preview requires at least one option")
            request.metadata = metadata
            request.options = bound_options
            request.preview_message_id = preview_message_id
            request.preview_expires_at = (self.monotonic() if now is None else now) + self.selection_seconds
            request.state = RequestState.AWAITING_SELECTION
            self._work_reservations.discard(request_id)
            self._instagram_reservations.discard(request_id)
            return True

    async def claim_selection(
        self,
        request_id: str,
        *,
        user_id: int,
        chat_id: int,
        preview_message_id: int,
        option_id: int,
        now: float | None = None,
    ) -> SelectionResult:
        async with self._user_guard(user_id):
            async with self._registry_lock:
                request = self.requests_by_id.get(request_id)
                if request is None:
                    terminal = self.terminal_by_id.get(request_id)
                    if terminal is not None:
                        if terminal.user_id != user_id or terminal.chat_id != chat_id:
                            return SelectionResult(SelectionOutcome.NOT_OWNER)
                        if terminal.state is RequestState.COMPLETED:
                            return SelectionResult(SelectionOutcome.COMPLETED)
                        if terminal.state is RequestState.EXPIRED:
                            return SelectionResult(SelectionOutcome.EXPIRED)
                        if terminal.state is RequestState.REPLACED:
                            return SelectionResult(SelectionOutcome.REPLACED)
                    return SelectionResult(SelectionOutcome.NOT_FOUND)
                if request.user_id != user_id or request.chat_id != chat_id:
                    return SelectionResult(SelectionOutcome.NOT_OWNER)
                if self.active_request_by_user.get(user_id) != request_id:
                    return SelectionResult(SelectionOutcome.STALE, request)
                if request.state is not RequestState.AWAITING_SELECTION:
                    return SelectionResult(SelectionOutcome.PROCESSING if request.state in {RequestState.DOWNLOADING, RequestState.SENDING} else SelectionOutcome.STALE, request)
                current = self.monotonic() if now is None else now
                if request.preview_expires_at is None or current >= request.preview_expires_at:
                    self._terminalize_locked(request, RequestState.EXPIRED, current)
                    return SelectionResult(SelectionOutcome.EXPIRED)
                if request.preview_message_id != preview_message_id:
                    return SelectionResult(SelectionOutcome.STALE, request)
                try:
                    option = request.option(option_id)
                except KeyError:
                    return SelectionResult(SelectionOutcome.INVALID_OPTION, request)
                if option.availability != "selectable":
                    return SelectionResult(SelectionOutcome.INVALID_OPTION, request)

                if self._closed:
                    return SelectionResult(SelectionOutcome.WORK_BUSY, request)
                capacity = self._capacity_outcome(request.platform, needs_pending=False)
                if capacity is AdmissionOutcome.INSTAGRAM_BUSY:
                    return SelectionResult(SelectionOutcome.INSTAGRAM_BUSY, request)
                if capacity is not None:
                    return SelectionResult(SelectionOutcome.WORK_BUSY, request)

                self._work_reservations.add(request_id)
                if self._is_instagram(request):
                    self._instagram_reservations.add(request_id)
                self._pending_reservations.discard(request_id)
                request.selected_option_id = option_id
                request.processing_deadline = current + self.processing_seconds
                request.state = RequestState.DOWNLOADING
                return SelectionResult(SelectionOutcome.ACCEPTED, request, option)

    async def authorize_preview_callback(
        self,
        request_id: str,
        *,
        user_id: int,
        chat_id: int,
        preview_message_id: int,
        now: float | None = None,
    ) -> SelectionResult:
        """Authorize pagination without changing or exposing another user's request."""
        async with self._user_guard(user_id):
            async with self._registry_lock:
                request = self.requests_by_id.get(request_id)
                if request is None:
                    terminal = self.terminal_by_id.get(request_id)
                    if terminal is not None and (
                        terminal.user_id != user_id or terminal.chat_id != chat_id
                    ):
                        return SelectionResult(SelectionOutcome.NOT_OWNER)
                    if terminal is not None and terminal.state is RequestState.COMPLETED:
                        return SelectionResult(SelectionOutcome.COMPLETED)
                    if terminal is not None and terminal.state is RequestState.EXPIRED:
                        return SelectionResult(SelectionOutcome.EXPIRED)
                    if terminal is not None and terminal.state is RequestState.REPLACED:
                        return SelectionResult(SelectionOutcome.REPLACED)
                    return SelectionResult(SelectionOutcome.NOT_FOUND)
                if request.user_id != user_id or request.chat_id != chat_id:
                    return SelectionResult(SelectionOutcome.NOT_OWNER)
                if (
                    request.state is not RequestState.AWAITING_SELECTION
                    or self.active_request_by_user.get(user_id) != request_id
                    or request.preview_message_id != preview_message_id
                ):
                    return SelectionResult(SelectionOutcome.STALE, request)
                current = self.monotonic() if now is None else now
                if request.preview_expires_at is None or current >= request.preview_expires_at:
                    self._terminalize_locked(request, RequestState.EXPIRED, current)
                    return SelectionResult(SelectionOutcome.EXPIRED)
                return SelectionResult(SelectionOutcome.ACCEPTED, request)

    async def transition(
        self,
        request_id: str,
        *,
        expected: RequestState | str,
        new_state: RequestState | str,
    ) -> bool:
        expected_state = RequestState(expected)
        target = RequestState(new_state)
        allowed = {
            (RequestState.DOWNLOADING, RequestState.SENDING),
        }
        if (expected_state, target) not in allowed:
            raise ValueError("unsupported nonterminal transition")
        async with self._registry_lock:
            request = self.requests_by_id.get(request_id)
            if (
                request is None
                or request.state is not expected_state
                or self.active_request_by_user.get(request.user_id) != request_id
            ):
                return False
            request.state = target
            return True

    async def is_current(self, request_id: str, expected: RequestState | str) -> bool:
        """Publication guard for stale worker results."""
        expected_state = RequestState(expected)
        async with self._registry_lock:
            request = self.requests_by_id.get(request_id)
            return bool(
                request is not None
                and request.state is expected_state
                and self.active_request_by_user.get(request.user_id) == request_id
            )

    async def finalize(
        self,
        request_id: str,
        *,
        state: RequestState | str,
        delivery_result: DeliveryResult | None = None,
        notify: Notifier | None = None,
        now: float | None = None,
    ) -> bool:
        target = RequestState(state)
        if target not in {
            RequestState.COMPLETED,
            RequestState.FAILED,
            RequestState.EXPIRED,
            RequestState.REPLACED,
        }:
            raise ValueError("finalize requires a terminal state")
        async with self._registry_lock:
            request = self.requests_by_id.get(request_id)
            if request is None:
                return False
            request.delivery_result = delivery_result
            self._terminalize_locked(
                request, target, self.monotonic() if now is None else now
            )

        # State/capacity release precedes best-effort user notification.
        if notify is not None:
            try:
                await notify()
            except Exception:
                pass
        return True

    async def close_admission(self) -> None:
        async with self._registry_lock:
            self._closed = True

    async def prune(self, *, now: float | None = None) -> None:
        async with self._registry_lock:
            self._prune_terminal_locked(self.monotonic() if now is None else now)

    async def expire_pending(self, *, now: float | None = None) -> list[str]:
        current = self.monotonic() if now is None else now
        expired: list[str] = []
        async with self._registry_lock:
            for request in list(self.requests_by_id.values()):
                if (
                    request.state is RequestState.AWAITING_SELECTION
                    and request.preview_expires_at is not None
                    and current >= request.preview_expires_at
                ):
                    expired.append(request.request_id)
                    self._terminalize_locked(request, RequestState.EXPIRED, current)
            self._prune_terminal_locked(current)
        return expired

    def terminal(self, request_id: str) -> TerminalRecord | None:
        return self.terminal_by_id.get(request_id)

    def _capacity_outcome(
        self, platform: str, *, needs_pending: bool
    ) -> AdmissionOutcome | None:
        if self.source_busy(platform):
            return AdmissionOutcome.INSTAGRAM_BUSY if platform == "instagram" else AdmissionOutcome.WORK_BUSY
        if len(self._work_reservations) >= self.max_workers:
            return AdmissionOutcome.WORK_BUSY
        if platform.lower() == "instagram" and (
            len(self._instagram_reservations) >= self.max_instagram_workers
        ):
            return AdmissionOutcome.INSTAGRAM_BUSY
        if needs_pending and len(self._pending_reservations) >= self.max_pending:
            return AdmissionOutcome.PENDING_FULL
        return None

    @staticmethod
    def _is_instagram(request: DownloadRequest) -> bool:
        return request.platform.lower() == "instagram"

    def _terminalize_locked(
        self, request: DownloadRequest, state: RequestState, terminal_at: float
    ) -> None:
        request_id = request.request_id
        user_id = request.user_id
        chat_id = request.chat_id
        request.state = state
        self._work_reservations.discard(request_id)
        self._instagram_reservations.discard(request_id)
        self._pending_reservations.discard(request_id)
        self.requests_by_id.pop(request_id, None)
        if self.active_request_by_user.get(user_id) == request_id:
            self.active_request_by_user.pop(user_id, None)
        lock_entry = self._user_locks.get(user_id)
        if (
            lock_entry is not None
            and lock_entry.references == 0
            and not lock_entry.lock.locked()
        ):
            self._user_locks.pop(user_id, None)
        confirmed_message_id = None
        if request.delivery_result is not None and request.delivery_result.status == "confirmed":
            confirmed_message_id = request.delivery_result.message_id
        self.terminal_by_id[request_id] = TerminalRecord(
            request_id=request_id,
            user_id=user_id,
            chat_id=chat_id,
            state=state,
            terminal_at=terminal_at,
            confirmed_message_id=confirmed_message_id,
        )
        self.terminal_by_id.move_to_end(request_id)
        self._prune_terminal_locked(terminal_at)

    def _prune_terminal_locked(self, now: float) -> None:
        cutoff = now - self.terminal_ttl
        while self.terminal_by_id:
            first_id = next(iter(self.terminal_by_id))
            first = self.terminal_by_id[first_id]
            if len(self.terminal_by_id) <= self.terminal_limit and first.terminal_at > cutoff:
                break
            self.terminal_by_id.popitem(last=False)

    @asynccontextmanager
    async def _user_guard(self, user_id: int) -> AsyncIterator[None]:
        async with self._registry_lock:
            entry = self._user_locks.get(user_id)
            if entry is None:
                entry = _LockEntry(asyncio.Lock())
                self._user_locks[user_id] = entry
            entry.references += 1
        await entry.lock.acquire()
        try:
            yield
        finally:
            entry.lock.release()
            async with self._registry_lock:
                entry.references -= 1
                if entry.references == 0 and user_id not in self.active_request_by_user:
                    self._user_locks.pop(user_id, None)


class WorkflowError(RuntimeError):
    pass


class WorkflowBusy(WorkflowError):
    def __init__(self, outcome: AdmissionOutcome | SelectionOutcome) -> None:
        self.outcome = outcome
        super().__init__(outcome.value)


InspectCallable = Callable[[DownloadRequest], Awaitable[InspectResult]]
PreviewCallable = Callable[[DownloadRequest, InspectResult], Awaitable[int]]
DownloadCallable = Callable[[DownloadRequest, FormatOption], Awaitable[DownloadResult]]
DeliverCallable = Callable[[DownloadRequest, DownloadResult], Awaitable[DeliveryResult]]
StatusCallable = Callable[[DownloadRequest, str], Awaitable[Any]]
CleanupCallable = Callable[[DownloadRequest], Awaitable[Any]]


class MediaWorkflow:
    """Small orchestration layer for the inspect → choose → download → send journey."""

    def __init__(
        self,
        registry: RequestRegistry,
        *,
        inspect: InspectCallable,
        publish_preview: PreviewCallable,
        download: DownloadCallable,
        deliver: DeliverCallable,
        status: StatusCallable,
        cleanup: CleanupCallable | None = None,
        notify_failure: Callable[[DownloadRequest, DeliveryResult], Awaitable[Any]] | None = None,
        inspection_seconds: float = 60,
        reap_reserve: float = 5,
    ) -> None:
        self.registry = registry
        self._inspect = inspect
        self._publish_preview = publish_preview
        self._download = download
        self._deliver = deliver
        self._status = status
        self._cleanup = cleanup
        self.notify_failure = notify_failure
        self.inspection_seconds = inspection_seconds
        self.reap_reserve = reap_reserve

    async def submit(
        self,
        *,
        user_id: int,
        chat_id: int,
        text: str,
        chat_type: str,
    ) -> DownloadRequest:
        from openmedia.bot import parse_link_message

        route = parse_link_message(text, chat_type=chat_type)
        request = self.registry.new_request(
            user_id=user_id,
            chat_id=chat_id,
            source_url=route.canonical_url,
            platform=route.platform,
            media_id=route.media_id,
        )
        admission = await self.registry.admit(request)
        if admission.outcome not in {AdmissionOutcome.ADMITTED, AdmissionOutcome.REPLACED}:
            raise WorkflowBusy(admission.outcome)
        try:
            async with asyncio.timeout(max(0, request.created_at + self.inspection_seconds - self.reap_reserve - self.registry.monotonic())):
                await self._status(request, "checking")
                result = await self._inspect(request)
                if result.metadata.media_id != request.media_id:
                    raise WorkflowError("inspection returned a different media identity")
                preview_message_id = await self._publish_preview(request, result)
                published = await self.registry.publish_preview(
                    request.request_id,
                    metadata=result.metadata,
                    options=result.options,
                    preview_message_id=preview_message_id,
                )
                if not published:
                    raise WorkflowError("request was replaced before preview publication")
                await self._run_cleanup(request)
                return request
        except BaseException as exc:
            await self._run_cleanup(request)
            await self._fail(request, exc, "checking")
            raise

    async def select(
        self,
        *,
        request_id: str,
        user_id: int,
        chat_id: int,
        preview_message_id: int,
        option_id: int,
    ) -> DeliveryResult:
        selection = await self.registry.claim_selection(
            request_id,
            user_id=user_id,
            chat_id=chat_id,
            preview_message_id=preview_message_id,
            option_id=option_id,
        )
        if selection.outcome is not SelectionOutcome.ACCEPTED:
            raise WorkflowBusy(selection.outcome)
        assert selection.request is not None
        assert selection.option is not None
        return await self.process_claimed(selection.request, selection.option)

    async def process_claimed(
        self,
        request: DownloadRequest,
        option: FormatOption,
    ) -> DeliveryResult:
        """Continue a selection already atomically claimed by a short callback handler."""
        request_id = request.request_id
        try:
            async with asyncio.timeout(max(0, (request.processing_deadline or self.registry.monotonic()) - self.reap_reserve - self.registry.monotonic())):
                await self._status(request, "downloading")
                downloaded = await self._download(request, option)
                self._validate_download(request, option, downloaded)
                if not await self.registry.transition(
                    request_id,
                    expected=RequestState.DOWNLOADING,
                    new_state=RequestState.SENDING,
                ):
                    raise WorkflowError("download result belongs to a stale request")
                await self._status(request, "sending")
                delivered = await self._deliver(request, downloaded)
                terminal = (
                    RequestState.COMPLETED
                    if delivered.status == "confirmed"
                    else RequestState.FAILED
                )
                await self._run_cleanup(request)
                await self.registry.finalize(
                    request_id,
                    state=terminal,
                    delivery_result=delivered,
                )
                if delivered.status != "confirmed":
                    delivered = await self._notify(request, delivered)
                return delivered
        except BaseException as exc:
            stage = "sending" if request.state is RequestState.SENDING else "downloading"
            await self._run_cleanup(request)
            failed = await self._fail(request, exc, stage)
            if self.notify_failure is not None and not isinstance(exc, asyncio.CancelledError):
                return failed
            raise

    async def _fail(self, request: DownloadRequest, exc: BaseException, stage: str) -> DeliveryResult:
        from openmedia.bot import failure_message
        from openmedia.sources import ErrorCategory
        from openmedia.workers import WorkerTimeout
        category = getattr(exc, "category", "internal")
        if isinstance(exc, (TimeoutError, WorkerTimeout)):
            category = "timeout"
        if isinstance(exc, OSError) and exc.errno == 28:
            category = "storage_exhausted"
        try:
            category = ErrorCategory(category).value
        except ValueError:
            category = "internal"
        unknown = stage == "sending" and isinstance(exc, (TimeoutError, asyncio.CancelledError))
        result = DeliveryResult(status="unknown" if unknown else "failed", error_category=category,
            failed_stage=stage, next_step=("Check this chat before submitting the link again." if unknown
                else failure_message(category, stage=stage)))
        await self.registry.finalize(request.request_id, state=RequestState.FAILED, delivery_result=result)
        if not isinstance(exc, asyncio.CancelledError):
            result = await self._notify(request, result)
        return result

    async def _notify(self, request: DownloadRequest, result: DeliveryResult) -> DeliveryResult:
        if self.notify_failure is not None:
            try:
                async with asyncio.timeout(5):
                    await self.notify_failure(request, result)
                result = replace(result, notification_sent=True)
            except Exception:
                pass
        request.delivery_result = result
        return result

    async def _run_cleanup(self, request: DownloadRequest) -> None:
        if self._cleanup is None:
            return
        try:
            await self._cleanup(request)
        except Exception:
            # Final state and capacity release never depend on cleanup success; the runtime
            # sweeper retries leftovers every 60 seconds and at startup.
            return

    @staticmethod
    def _validate_download(
        request: DownloadRequest, option: FormatOption, result: DownloadResult
    ) -> None:
        if (
            result.media_id != request.media_id
            or result.source_format_id != option.source_format_id
            or str(result.media_type) != option.media_type.value
            or result.extension.lower().removeprefix(".") != option.extension
            or result.mime_type != option.mime_type
        ):
            raise WorkflowError("downloaded output does not match the selected option")
        try:
            actual = result.path.stat().st_size
        except OSError as exc:
            raise WorkflowError("downloaded output is unavailable") from exc
        if actual != result.actual_bytes:
            raise WorkflowError("downloaded output byte count changed")


class ParentRateController:
    """Bounded process-owned cooldown state shared across short-lived workers."""

    def __init__(self, *, monotonic: Callable[[], float] = time.monotonic) -> None:
        self.monotonic = monotonic
        self._lock = asyncio.Lock()
        self._cooldown_until: dict[str, float] = {}
        self._last_request: dict[tuple[str, str], float] = {}

    def is_cooling_down(self, platform: str) -> bool:
        return self._cooldown_until.get(platform, 0) > self.monotonic()

    async def handle_request(self, event: dict[str, Any]) -> dict[str, Any]:
        platform = str(event.get("platform", ""))
        request_class = str(event.get("request_class", ""))
        deadline = float(event.get("deadline", 0))
        now = self.monotonic()
        async with self._lock:
            self._prune(now)
            delay = max(0.0, self._cooldown_until.get(platform, 0.0) - now)
            if platform == "instagram":
                delay = max(
                    delay,
                    1.0 - (now - self._last_request.get((platform, request_class), -10.0)),
                )
            if now + delay >= deadline:
                return {"allowed": False, "delay": 0}
            self._last_request[(platform, request_class)] = now + delay
            return {"allowed": True, "delay": delay}

    async def handle_limited(self, event: dict[str, Any]) -> None:
        platform = str(event.get("platform", ""))
        retry = event.get("retry_after")
        try:
            seconds = float(retry) if retry is not None else 60.0
        except (TypeError, ValueError):
            seconds = 60.0
        seconds = min(max(seconds, 0.0), 900.0)
        async with self._lock:
            self._cooldown_until[platform] = max(
                self._cooldown_until.get(platform, 0.0), self.monotonic() + seconds
            )

    def _prune(self, now: float) -> None:
        self._cooldown_until = {
            key: value for key, value in self._cooldown_until.items() if value > now
        }
        self._last_request = {
            key: value for key, value in self._last_request.items() if now - value < 900
        }

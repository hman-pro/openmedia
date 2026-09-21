"""OpenMedia process entry point and polling composition root."""

from __future__ import annotations

import argparse
import asyncio
import bisect
import importlib.util
import json
import logging
import os
import shutil
import sys
import time
from collections.abc import Awaitable, Callable, Mapping, Sequence
from pathlib import Path
from typing import Any, TypeVar
from contextlib import suppress
from dataclasses import fields

from telegram.ext import Application, ApplicationBuilder, ExtBot
from telegram.request import HTTPXRequest

from openmedia.bot import build_preview, register_handlers, selected_label, send_preview
from openmedia.config import ConfigError, Settings
from openmedia.coordinator import MediaWorkflow, ParentRateController, RequestRegistry
from openmedia.delivery import deliver_document
from openmedia.diagnostics import REQUEST_CONTEXT, configure_diagnostics, event, redact
from openmedia.models import DeliveryResult, DownloadRequest, FormatOption
from openmedia.sources import DownloadInput, DownloadResult, InspectInput, InspectResult
from openmedia.workers import (
    WorkerSupervisor,
    cleanup_request_directory,
    create_request_directory,
    decode_download_result,
    decode_inspect_result,
    download_payload,
    inspect_payload,
    sweep_work_directories,
)


T = TypeVar("T")
HEALTH_FILENAME = ".openmedia-health.json"
HEALTH_MAX_AGE_SECONDS = 90.0
HEARTBEAT_INTERVAL_SECONDS = 15.0
# Shutdown budget: 12s owned work + 2s after the SIGKILL backstop + 5s PTB stop = 19s < 20s.
SHUTDOWN_WORK_SECONDS = 12.0
SHUTDOWN_KILL_SECONDS = 2.0
SHUTDOWN_STOP_SECONDS = 5.0
SWEEP_INTERVAL_SECONDS = 60.0
# The only logged causes that may excuse an acceptance-timing sample (quickstart exclusion rule).
EXTERNAL_FAILURE_CLASSES = frozenset({"429", "5xx", "connection_failure", "retry_after"})
MAX_TRACKED_EXTERNAL_REQUESTS = 1000


class SafeLogFormatter(logging.Formatter):
    """Redact the final rendered message, including chained exception tracebacks."""

    def __init__(self, *args: Any, secrets: tuple[str, ...] = (), **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.secrets = secrets

    def format(self, record: logging.LogRecord) -> str:
        return redact(super().format(record), self.secrets)


def configure_logging(settings: Settings) -> None:
    handler = logging.StreamHandler()
    # The handler owns the console level so the diagnostic file can lower the root level
    # without adding a single line to the console.
    handler.setLevel(settings.log_level)
    handler.setFormatter(SafeLogFormatter("%(message)s", secrets=(settings.telegram_bot_token,)))
    logging.basicConfig(level=settings.log_level, handlers=[handler], force=True)
    for name in ("httpx", "httpcore", "telegram", "urllib3", "requests"):
        logging.getLogger(name).setLevel(logging.WARNING)


class RuntimeHealth:
    """Cross-process health snapshot written only by a successfully polling parent."""

    def __init__(
        self,
        path: Path,
        *,
        wall_time: Callable[[], float] = time.time,
    ) -> None:
        self.path = Path(path)
        self.wall_time = wall_time
        self.last_poll: float | None = None
        self.ready = False

    def record_successful_poll(self) -> None:
        self.last_poll = self.wall_time()
        self.ready = True
        self.write()

    def write(self) -> None:
        if not self.ready or self.last_poll is None:
            return
        now = self.wall_time()
        value = {
            "ready": True,
            "heartbeat": now,
            "last_successful_poll": self.last_poll,
        }
        temporary = self.path.with_name(f"{self.path.name}.tmp-{os.getpid()}")
        temporary.write_text(json.dumps(value, separators=(",", ":")), encoding="utf-8")
        temporary.chmod(0o600)
        os.replace(temporary, self.path)

    async def maintain(self) -> None:
        while True:
            if self.ready:
                self.write()
            await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)

    def remove(self) -> None:
        self.path.unlink(missing_ok=True)


class ManagedApplication(Application):
    """Cancel owned work before PTB's stop waits for background task completion."""

    __slots__ = ("work_tasks",)

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.work_tasks: set[asyncio.Task[Any]] = set()

    def create_task(self, coroutine: Any, update: Any = None, *, name: str | None = None) -> asyncio.Task[Any]:
        task = (super().create_task(coroutine, update=update, name=name) if self.running
            else asyncio.create_task(coroutine, name=name))
        self.work_tasks.add(task)
        task.add_done_callback(self.work_tasks.discard)
        return task

    async def stop(self) -> None:
        registry = self.bot_data.get("openmedia_registry")
        if registry is not None:
            await registry.close_admission()
        tasks = tuple(self.work_tasks)
        for task in tasks:
            task.cancel()
        log = logging.getLogger("openmedia")
        if tasks:
            _done, pending = await asyncio.wait(tasks, timeout=SHUTDOWN_WORK_SECONDS)
            if pending:
                log.warning("shutdown work exceeded its budget; killing source worker groups")
                callbacks = self.bot_data.get("openmedia_callbacks")
                if callbacks is not None:
                    callbacks.supervisor.kill_active()
                await asyncio.wait(pending, timeout=SHUTDOWN_KILL_SECONDS)
        # Never raise: PTB skips shutdown() and post_shutdown when stop() fails.
        try:
            async with asyncio.timeout(SHUTDOWN_STOP_SECONDS):
                await super().stop()
        except TimeoutError:
            log.warning("telegram application stop exceeded its budget")


class HealthTrackingBot(ExtBot[None]):
    """Record only completed getUpdates calls; failures never refresh health."""

    def __init__(self, *args: Any, runtime_health: RuntimeHealth, **kwargs: Any) -> None:
        self._runtime_health = runtime_health
        self._ordinary_messages = OrdinaryMessageLimiter()
        # PTB freezes public Bot attributes, so observers are appended to this private list.
        self._external_observers: list[Callable[[str, str], None]] = []
        super().__init__(*args, **kwargs)

    @property
    def external_observers(self) -> list[Callable[[str, str], None]]:
        return self._external_observers

    async def _send_message(self, endpoint: str, data: Any, *args: Any, **kwargs: Any) -> Any:
        from telegram.error import BadRequest, RetryAfter, NetworkError
        action = super()._send_message
        try:
            return await self._ordinary_messages.run(int(data["chat_id"]),
                lambda: action(endpoint, data, *args, **kwargs))
        except BadRequest:
            # A NetworkError subclass, but it is our request that was wrong, not Telegram's service.
            raise
        except (RetryAfter, NetworkError) as exc:
            cause = "retry_after" if isinstance(exc, RetryAfter) else "connection_failure"
            request_id = REQUEST_CONTEXT.get()
            logging.getLogger("openmedia").info(json.dumps({"request_id": request_id,
                "stage": "telegram_response", "upstream_status_class": cause}))
            if request_id is not None:
                for observer in self.external_observers:
                    observer(request_id, cause)
            raise

    async def get_updates(self, *args: Any, **kwargs: Any) -> Any:
        updates = await super().get_updates(*args, **kwargs)
        self._runtime_health.record_successful_poll()
        return updates


def sweep_threshold(cleanup_seconds: float) -> float:
    """Age at which a leftover workspace is swept.

    A sweep can miss the threshold by an instant and the next tick can drift, so two
    intervals of slack keep worst-case removal inside the cleanup ceiling. The result
    stays above the 600s processing deadline, so a workspace in use is never swept.
    """
    return max(0.0, cleanup_seconds - 2 * SWEEP_INTERVAL_SECONDS)


def check_runtime_health(
    path: Path,
    *,
    wall_time: Callable[[], float] = time.time,
    max_age: float = HEALTH_MAX_AGE_SECONDS,
) -> tuple[bool, str]:
    """Read health state without contacting Telegram or starting a second poller."""

    try:
        value = json.loads(Path(path).read_text(encoding="utf-8"))
        heartbeat = float(value["heartbeat"])
        last_poll = float(value["last_successful_poll"])
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return False, "health state is missing or invalid"
    now = wall_time()
    if value.get("ready") is not True:
        return False, "polling is not ready"
    if heartbeat > now + 5 or last_poll > now + 5:
        return False, "health state is from the future"
    if now - heartbeat >= max_age:
        return False, "heartbeat is stale"
    if now - last_poll >= max_age:
        return False, "last successful poll is stale"
    return True, "healthy"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openmedia",
        description="Telegram bot delivering one public media link in a native upstream format.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check-config", action="store_true")
    mode.add_argument("--healthcheck", action="store_true")
    return parser


class OrdinaryMessageLimiter:
    """One ordinary chat send/s and twenty globally; callbacks bypass this limiter.

    A send reserves its slot synchronously and then waits outside any lock, so a chat that is
    queueing replies (repeated invalid input) delays only itself, never other chats.
    """

    CHAT_INTERVAL = 1.0
    GLOBAL_LIMIT = 20
    GLOBAL_WINDOW = 1.0

    def __init__(self, *, monotonic: Callable[[], float] = time.monotonic) -> None:
        self.monotonic = monotonic
        self._chat_next: dict[int, float] = {}
        self._global_times: list[float] = []  # sorted; includes reserved future sends

    def reserve(self, chat_id: int, now: float) -> float:
        """Return the earliest send time honoring both bounds, and book it."""
        self._chat_next = {key: stamp for key, stamp in self._chat_next.items() if stamp > now}
        self._global_times = [stamp for stamp in self._global_times if now - stamp < self.GLOBAL_WINDOW]
        at = max(now, self._chat_next.get(chat_id, now))
        while True:
            position = bisect.bisect_right(self._global_times, at)
            booked = [*self._global_times[:position], at, *self._global_times[position:]]
            # Any GLOBAL_LIMIT + 1 consecutive sends must span at least one full window.
            conflict = next(
                (booked[index + 1] if index == position else booked[index]
                    for index in range(max(0, position - self.GLOBAL_LIMIT), position + 1)
                    if index + self.GLOBAL_LIMIT < len(booked)
                    and booked[index + self.GLOBAL_LIMIT] - booked[index] < self.GLOBAL_WINDOW),
                None,
            )
            if conflict is None:
                break
            at = conflict + self.GLOBAL_WINDOW
        self._global_times.insert(position, at)
        self._chat_next[chat_id] = at + self.CHAT_INTERVAL
        return at

    async def run(self, chat_id: int, action: Callable[[], Awaitable[T]]) -> T:
        now = self.monotonic()
        delay = self.reserve(chat_id, now) - now
        if delay > 0:
            await asyncio.sleep(delay)
        return await action()


class RuntimeCallbacks:
    def __init__(self, settings: Settings, application: Application[Any, ...]) -> None:
        self.settings = settings
        self.application = application
        self.supervisor = WorkerSupervisor()
        self.rate = ParentRateController()
        self.failed_cleanup: set[Path] = set()
        self._external: dict[str, list[str]] = {}
        observers = getattr(getattr(application, "bot", None), "external_observers", None)
        if observers is not None:
            observers.append(self.external_failure)

    def external_failure(self, request_id: str, cause: str) -> None:
        """Remember an excusable upstream cause until the request's terminal record is written."""
        if cause not in EXTERNAL_FAILURE_CLASSES:
            return
        causes = self._external.setdefault(request_id, [])
        if cause not in causes:
            causes.append(cause)
        while len(self._external) > MAX_TRACKED_EXTERNAL_REQUESTS:
            self._external.pop(next(iter(self._external)))

    def terminal(self, request: DownloadRequest, **values: Any) -> None:
        self.observe(request, "terminal",
            external_causes=self._external.pop(request.request_id, []), **values)

    def observe(self, request: DownloadRequest, stage: str, **values: Any) -> None:
        logging.getLogger("openmedia").info(json.dumps({"request_id": request.request_id,
            "platform": request.platform, "stage": stage,
            "elapsed_seconds": round(time.monotonic() - request.created_at, 4), **values}, separators=(",", ":")))

    def upstream(self, request: DownloadRequest, event: Mapping[str, Any]) -> None:
        status = event.get("upstream_status_class")
        if status in {"2xx", "3xx", "4xx", "429", "5xx", "connection_failure"}:
            self.observe(request, "source_response", upstream_status_class=status)
            self.external_failure(request.request_id, status)

    def _worker_deadline(self, request_deadline: float) -> float:
        """The instant in-worker work must stop: the request deadline less the reap reserve.

        Rate grants and guarded-transport timeouts inside the worker end here, so a delay that
        cannot finish is refused as rate_limited instead of being cut off by cancellation.
        """
        return request_deadline - self.supervisor.termination_grace

    def _supervision_timeout(self, request_deadline: float) -> float:
        # The supervisor spends its final termination_grace seconds reaping, so its own budget
        # ends at the worker deadline and reaping completes by the request deadline.
        return max(0.1, request_deadline - time.monotonic())

    async def inspect(self, request: DownloadRequest) -> InspectResult:
        directory = create_request_directory(self.settings.work_dir, request.request_id)
        request.work_directory = directory
        request_deadline = request.created_at + self.settings.inspection_seconds
        input_value = InspectInput(
            source_url=request.source_url,
            request_id=request.request_id,
            work_directory=directory,
            deadline=self._worker_deadline(request_deadline),
            output_limit=self.settings.max_file_bytes,
        )
        value = await self.supervisor.run(
            "inspect",
            inspect_payload(input_value),
            timeout=self._supervision_timeout(request_deadline),
            on_rate_request=self.rate.handle_request,
            on_rate_limited=self.rate.handle_limited,
            on_progress=lambda event: self.upstream(request, event),
        )
        if not isinstance(value, Mapping):
            raise RuntimeError("inspect worker returned an invalid result")
        return decode_inspect_result(value)

    async def preview(self, request: DownloadRequest, result: InspectResult) -> int:
        rendered = build_preview(
            request_id=request.request_id,
            metadata=result.metadata,
            options=result.options,
        )
        message_id = await send_preview(self.application.bot, chat_id=request.chat_id,
            rendered=rendered, thumbnail_path=result.thumbnail_path)
        self.observe(request, "preview")
        return message_id

    async def download(self, request: DownloadRequest, option: FormatOption) -> DownloadResult:
        directory = request.work_directory
        if directory is None:
            directory = create_request_directory(self.settings.work_dir, request.request_id)
            request.work_directory = directory
        deadline = request.processing_deadline
        if deadline is None or request.metadata is None:
            raise RuntimeError("selected request has no processing context")
        input_value = DownloadInput(
            request_id=request.request_id,
            metadata=request.metadata,
            option=option,
            work_directory=directory,
            deadline=self._worker_deadline(deadline),
            output_limit=self.settings.max_file_bytes,
            workspace_limit=self.settings.workspace_bytes,
        )
        value = await self.supervisor.run(
            "download",
            download_payload(input_value),
            timeout=self._supervision_timeout(deadline),
            on_rate_request=self.rate.handle_request,
            on_rate_limited=self.rate.handle_limited,
            on_progress=lambda event: self.upstream(request, event),
        )
        if not isinstance(value, Mapping):
            raise RuntimeError("download worker returned an invalid result")
        return decode_download_result(value)

    async def deliver(self, request: DownloadRequest, result: DownloadResult) -> DeliveryResult:
        if request.work_directory is None or request.processing_deadline is None:
            raise RuntimeError("selected request has no delivery context")
        result = await deliver_document(
                self.application.bot,
                request=request,
                downloaded=result,
                owned_directory=request.work_directory,
                max_file_bytes=self.settings.max_file_bytes,
                deadline=request.processing_deadline,
        )
        selected_at = request.processing_deadline - self.settings.processing_seconds
        self.observe(request, "delivery", outcome=result.status.value, bytes=result.actual_bytes,
            selected_elapsed_seconds=round(time.monotonic() - selected_at, 4),
            error_category=result.error_category)
        if result.status == "confirmed":
            self.terminal(request, outcome=result.status.value)
        return result

    async def status(self, request: DownloadRequest, stage: str) -> None:
        REQUEST_CONTEXT.set(request.request_id)
        self.observe(request, stage)
        labels = {
            "checking": "Checking the public link…",
            "downloading": "Downloading the selected native format…",
            "sending": "Sending the file…",
        }
        text = labels[stage]
        if stage == "downloading" and request.selected_option_id is not None:
            text = f"Downloading your choice: {selected_label(request.option(request.selected_option_id))}"
        await self.application.bot.send_message(
                chat_id=request.chat_id,
                text=text,
        )
        if stage == "checking":
            self.observe(request, "acknowledgment")

    async def cleanup(self, request: DownloadRequest) -> None:
        directory = request.work_directory
        request.work_directory = None
        if directory is not None:
            try:
                cleanup_request_directory(directory, owned_root=self.settings.work_dir)
                event("cleanup", request=request, outcome="removed")
            except OSError as exc:
                self.failed_cleanup.add(directory)
                logging.getLogger("openmedia").warning("workspace cleanup deferred")
                event("cleanup", request=request, level=logging.WARNING, outcome="deferred",
                    exc_info=(type(exc), exc, exc.__traceback__))

    async def notify_failure(self, request: DownloadRequest, result: DeliveryResult) -> None:
        self.terminal(request, outcome=result.status.value, error_category=result.error_category,
            failed_stage=result.failed_stage)
        outcome = "could not be confirmed" if result.status == "unknown" else "failed"
        await self.application.bot.send_message(
            chat_id=request.chat_id, text=f"The {result.failed_stage} stage {outcome}. {result.next_step}")

    async def maintain(self, registry: RequestRegistry) -> None:
        while True:
            await asyncio.sleep(SWEEP_INTERVAL_SECONDS)
            await self.sweep_once(registry)

    async def sweep_once(self, registry: RequestRegistry) -> None:
        log = logging.getLogger("openmedia")
        expired = cleanup_retried = cleanup_failed = swept = 0
        # One failing step must not end maintenance: expiry, retries, and sweeps all recur.
        try:
            expired = len(await registry.expire_pending())
        except Exception:
            log.warning("pending expiry failed; retrying on next sweep")
        for directory in tuple(self.failed_cleanup):
            try:
                cleanup_request_directory(directory, owned_root=self.settings.work_dir)
                self.failed_cleanup.discard(directory)
                cleanup_retried += 1
            except OSError:
                cleanup_failed += 1
                log.warning("workspace cleanup retry failed")
            except ValueError:
                # Not an owned workspace any more; the age sweep covers whatever remains.
                self.failed_cleanup.discard(directory)
        try:
            removed = sweep_work_directories(
                self.settings.work_dir,
                older_than=sweep_threshold(self.settings.cleanup_seconds),
            )
            swept = len(removed)
        except Exception:
            log.warning("workspace sweep failed; retrying on next sweep")
        if expired or cleanup_retried or cleanup_failed or swept:
            event("sweep", origin="sweep", expired=expired, cleanup_retried=cleanup_retried,
                cleanup_failed=cleanup_failed, swept=swept)


def run_with_diagnostics(settings: Settings, run: Callable[[], None]) -> None:
    """Bracket one bot run with lifecycle entries; stopping the writer flushes what is queued."""
    stop_diagnostics = configure_diagnostics(settings)
    reason = "signal"  # run_polling returns normally only after SIGINT/SIGTERM/SIGABRT
    try:
        event("startup", origin="lifecycle", settings={
            item.name: getattr(settings, item.name) for item in fields(settings) if item.repr})
        run()
    except BaseException as exc:
        reason = "error"
        event("crash", origin="lifecycle", level=logging.CRITICAL,
            exc_info=(type(exc), exc, exc.__traceback__))
        raise
    finally:
        event("shutdown", origin="lifecycle", reason=reason)
        stop_diagnostics()


def validate_local_runtime(settings: Settings) -> None:
    settings.work_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
    if settings.work_dir.is_symlink() or not settings.work_dir.is_dir():
        raise ConfigError("OPENMEDIA_WORK_DIR must be an owned writable directory")
    probe = settings.work_dir / ".config-probe"
    try:
        probe.write_bytes(b"")
        probe.unlink()
    except OSError as exc:
        raise ConfigError("OPENMEDIA_WORK_DIR is not writable") from exc
    for executable in ("deno", "ffmpeg", "ffprobe"):
        if shutil.which(executable) is None:
            raise ConfigError(f"required runtime executable is unavailable: {executable}")
    # yt-dlp runs YouTube challenge scripts from the bundled EJS package with remote
    # component fetching disabled, so a missing package cannot be recovered at run time.
    if importlib.util.find_spec("yt_dlp_ejs") is None:
        raise ConfigError("required bundled EJS challenge scripts (yt_dlp_ejs) are unavailable")
    # Deliberately no sweep: --check-config may run beside a live bot sharing this work
    # directory. The polling startup path removes leftovers before readiness instead.


def build_application(settings: Settings) -> tuple[Application[Any, ...], RequestRegistry]:
    registry = RequestRegistry(
        max_workers=settings.max_workers,
        max_pending=settings.max_pending,
        selection_seconds=settings.selection_seconds,
        processing_seconds=settings.processing_seconds,
    )

    health = RuntimeHealth(settings.work_dir / HEALTH_FILENAME)

    async def post_init(application: Application[Any, ...]) -> None:
        callbacks = application.bot_data["openmedia_callbacks"]
        application.bot_data["openmedia_maintenance"] = application.create_task(
            callbacks.maintain(registry),
            name="openmedia-maintenance",
        )
        application.bot_data["openmedia_health_task"] = application.create_task(
            health.maintain(),
            name="openmedia-health",
        )

    async def post_stop(application: Application[Any, ...]) -> None:
        await registry.close_admission()

    async def post_shutdown(application: Application[Any, ...]) -> None:
        for key in ("openmedia_maintenance", "openmedia_health_task"):
            task = application.bot_data.get(key)
            if task is None:
                continue
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
        health.remove()
        # All owned work is cancelled by now, so every remaining request workspace is ours.
        with suppress(OSError, ValueError):
            sweep_work_directories(settings.work_dir, older_than=0)

    bot = HealthTrackingBot(
        token=settings.telegram_bot_token,
        request=HTTPXRequest(connection_pool_size=16),
        get_updates_request=HTTPXRequest(connection_pool_size=1),
        runtime_health=health,
    )

    application = (
        ApplicationBuilder()
        .application_class(ManagedApplication)
        .bot(bot)
        .concurrent_updates(8)
        .post_init(post_init)
        .post_stop(post_stop)
        .post_shutdown(post_shutdown)
        .build()
    )
    callbacks = RuntimeCallbacks(settings, application)
    registry.source_busy = callbacks.rate.is_cooling_down
    workflow = MediaWorkflow(
        registry,
        inspect=callbacks.inspect,
        publish_preview=callbacks.preview,
        download=callbacks.download,
        deliver=callbacks.deliver,
        status=callbacks.status,
        cleanup=callbacks.cleanup,
        notify_failure=callbacks.notify_failure,
    )
    register_handlers(application, workflow)
    application.bot_data["openmedia_registry"] = registry
    application.bot_data["openmedia_callbacks"] = callbacks
    application.bot_data["openmedia_health"] = health
    return application, registry


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = Settings.from_env()
    except ConfigError as exc:
        print(f"openmedia: configuration error: {exc}", file=sys.stderr)
        return 2
    if args.healthcheck:
        healthy, reason = check_runtime_health(settings.work_dir / HEALTH_FILENAME)
        stream = sys.stdout if healthy else sys.stderr
        print(f"openmedia: {reason}", file=stream)
        return 0 if healthy else 1
    try:
        validate_local_runtime(settings)
    except ConfigError as exc:
        print(f"openmedia: configuration error: {exc}", file=sys.stderr)
        return 2
    configure_logging(settings)
    if args.check_config:
        print(
            f"openmedia: configuration valid (token={settings.redacted_token}, "
            f"work_dir={settings.work_dir})"
        )
        return 0
    # This process is about to own the work directory, so every leftover workspace is stale
    # (FR-015 recovery cleanup) and is removed before polling reports readiness.
    sweep_work_directories(settings.work_dir, older_than=0)
    def poll() -> None:
        application, _registry = build_application(settings)
        application.run_polling(drop_pending_updates=True, close_loop=True)

    run_with_diagnostics(settings, poll)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

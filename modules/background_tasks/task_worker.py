from __future__ import annotations

from dataclasses import dataclass
from threading import Event
from typing import Any, Callable, Dict, Optional
import traceback

from modules.background_tasks.task_types import TaskType


ProgressFn = Callable[[dict], None]
HandlerFn = Callable[["TaskContext"], Any]


@dataclass
class TaskContext:
    """
    Passed into task handlers.
    Handlers should periodically check ctx.is_cancelled() and return early.
    """

    task_id: str
    task_type: TaskType
    payload: Dict[str, Any]
    cancel_event: Event
    report_progress: Callable[[int, str], None]

    def is_cancelled(self) -> bool:
        return bool(self.cancel_event.is_set())


@dataclass
class TaskEnvelope:
    """Internal queue item."""

    task_id: str
    task_type: TaskType
    payload: Dict[str, Any]
    cancel_event: Event


class TaskWorker:
    """
    Background worker that consumes TaskEnvelope and executes handler based on task type.
    """

    def __init__(
        self,
        *,
        worker_id: int,
        queue_get,
        queue_task_done,
        get_handler: Callable[[TaskType], Optional[HandlerFn]],
        on_started: Callable[[str], None],
        on_progress: Callable[[str, int, str], None],
        on_completed: Callable[[str, Any], None],
        on_failed: Callable[[str, str], None],
        on_cancelled: Callable[[str], None],
        progress_callback: Optional[ProgressFn] = None,
    ) -> None:
        self.worker_id = int(worker_id)
        self._queue_get = queue_get
        self._queue_task_done = queue_task_done
        self._get_handler = get_handler

        self._on_started = on_started
        self._on_progress = on_progress
        self._on_completed = on_completed
        self._on_failed = on_failed
        self._on_cancelled = on_cancelled

        self._progress_callback = progress_callback

    def _emit(self, stage: str, message: str, extra: Optional[dict] = None) -> None:
        if not self._progress_callback:
            return
        payload = {"stage": stage, "message": message, "worker_id": self.worker_id}
        if extra:
            payload.update(extra)
        try:
            self._progress_callback(payload)
        except Exception:
            pass

    def run_forever(self, *, stop_event: Event) -> None:
        while not stop_event.is_set():
            try:
                env: TaskEnvelope = self._queue_get(timeout=0.2)
            except Exception:
                continue

            try:
                if env.cancel_event.is_set():
                    self._on_cancelled(env.task_id)
                    continue

                handler = self._get_handler(env.task_type)
                if handler is None:
                    self._on_failed(env.task_id, f"No handler registered for task type {env.task_type}")
                    continue

                self._on_started(env.task_id)
                self._emit("task_start", f"Start {env.task_type}", {"task_id": env.task_id, "task_type": env.task_type})

                def _report(pct: int, msg: str) -> None:
                    self._on_progress(env.task_id, pct, msg)
                    self._emit("task_progress", msg, {"task_id": env.task_id, "pct": pct})

                ctx = TaskContext(
                    task_id=env.task_id,
                    task_type=env.task_type,
                    payload=env.payload,
                    cancel_event=env.cancel_event,
                    report_progress=_report,
                )

                result = handler(ctx)
                if env.cancel_event.is_set():
                    self._on_cancelled(env.task_id)
                    continue
                self._on_completed(env.task_id, result)
                self._emit("task_done", f"Done {env.task_type}", {"task_id": env.task_id})
            except Exception as e:
                tb = traceback.format_exc(limit=8)
                self._on_failed(env.task_id, f"{type(e).__name__}: {e}\n{tb}")
                self._emit("task_error", f"Failed {env.task_type}: {e}", {"task_id": env.task_id})
            finally:
                try:
                    self._queue_task_done()
                except Exception:
                    pass


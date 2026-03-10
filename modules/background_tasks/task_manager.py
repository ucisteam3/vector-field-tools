from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event, Lock, Thread
from typing import Any, Callable, Dict, List, Optional
import time
import uuid

from modules.background_tasks.task_queue import TaskQueue
from modules.background_tasks.task_types import TaskStatus, TaskType
from modules.background_tasks.task_worker import HandlerFn, TaskEnvelope, TaskWorker, TaskContext
from modules.runtime_manager import RuntimeManager


ProgressFn = Callable[[dict], None]


@dataclass
class Task:
    id: str
    type: TaskType
    status: TaskStatus = TaskStatus.pending
    progress: int = 0
    message: str = ""
    payload: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=lambda: time.time())
    started_at: Optional[float] = None
    finished_at: Optional[float] = None
    error: Optional[str] = None
    result: Any = None


class BackgroundTaskManager:
    """
    Background Task Manager
    - task queueing (Queue)
    - multiple worker threads sized by hardware tier
    - progress tracking + cancellation
    - keeps last 20 completed tasks in history
    """

    def __init__(self, *, progress_callback: Optional[ProgressFn] = None) -> None:
        self._lock = Lock()
        self._queue = TaskQueue()
        self._stop_event = Event()
        self._workers: List[Thread] = []

        self._tasks: Dict[str, Task] = {}
        self._cancel_flags: Dict[str, Event] = {}
        self._history: List[Task] = []

        self._handlers: Dict[TaskType, HandlerFn] = {}
        self._progress_callback = progress_callback

        self._register_default_handlers()

    # ---------------------------
    # Handlers
    # ---------------------------
    def register_handler(self, task_type: TaskType, handler: HandlerFn) -> None:
        with self._lock:
            self._handlers[task_type] = handler

    def _get_handler(self, task_type: TaskType) -> Optional[HandlerFn]:
        with self._lock:
            return self._handlers.get(task_type)

    def _register_default_handlers(self) -> None:
        """
        Minimal built-in integrations (safe, additive).
        Other operations can be registered from backend/app bootstrap.
        """

        def runtime_update(ctx: TaskContext):
            ctx.report_progress(5, "Checking runtime updates...")
            RuntimeManager.auto_update_tick(progress_callback=None)
            ctx.report_progress(100, "Runtime update check complete")
            return {"ok": True}

        def download_model(ctx: TaskContext):
            model = str(ctx.payload.get("model") or "small")
            if ctx.is_cancelled():
                return None
            ctx.report_progress(1, f"Downloading Whisper model: {model}")
            RuntimeManager.ensure_whisper_model(model_name=model, progress_callback=lambda ev: None)
            ctx.report_progress(100, f"Whisper model ready: {model}")
            return {"model": model, "ok": True}

        self.register_handler(TaskType.RUNTIME_UPDATE, runtime_update)
        self.register_handler(TaskType.DOWNLOAD_MODEL, download_model)

    # ---------------------------
    # Worker sizing
    # ---------------------------
    def _worker_count(self) -> int:
        hw = RuntimeManager.detect_hardware()
        tier = RuntimeManager.classify_performance(hw)
        if tier == "POTATO_PC":
            return 1
        if tier == "MEDIUM_PC":
            return 2
        return 4

    # ---------------------------
    # Lifecycle
    # ---------------------------
    def start(self) -> None:
        with self._lock:
            if self._workers:
                return

            n = self._worker_count()
            for i in range(n):
                w = TaskWorker(
                    worker_id=i,
                    queue_get=self._queue.get,
                    queue_task_done=self._queue.task_done,
                    get_handler=self._get_handler,
                    on_started=self._on_started,
                    on_progress=self._on_progress,
                    on_completed=self._on_completed,
                    on_failed=self._on_failed,
                    on_cancelled=self._on_cancelled,
                    progress_callback=self._progress_callback,
                )
                t = Thread(target=w.run_forever, kwargs={"stop_event": self._stop_event}, daemon=True)
                t.start()
                self._workers.append(t)

    def stop(self) -> None:
        self._stop_event.set()

    # ---------------------------
    # Task API
    # ---------------------------
    def submit(self, task_type: TaskType, payload: Optional[Dict[str, Any]] = None) -> str:
        self.start()
        tid = str(uuid.uuid4())
        cancel = Event()
        task = Task(id=tid, type=task_type, payload=dict(payload or {}))
        with self._lock:
            self._tasks[tid] = task
            self._cancel_flags[tid] = cancel
        self._queue.put(TaskEnvelope(task_id=tid, task_type=task_type, payload=task.payload, cancel_event=cancel))
        self._emit("task_queued", f"Queued {task_type}", {"task_id": tid, "task_type": str(task_type)})
        return tid

    def cancel_task(self, task_id: str) -> bool:
        with self._lock:
            ev = self._cancel_flags.get(task_id)
            task = self._tasks.get(task_id)
        if not ev or not task:
            return False
        ev.set()
        self._emit("task_cancel", f"Cancel requested {task_id}", {"task_id": task_id})
        return True

    def get_task(self, task_id: str) -> Optional[Task]:
        with self._lock:
            t = self._tasks.get(task_id)
            return t

    def list_tasks(self) -> Dict[str, Any]:
        """
        For frontend API:
          - active tasks
          - last 20 completed tasks (history)
        """
        with self._lock:
            active = [self._tasks[k] for k in self._tasks.keys() if self._tasks[k].status in {TaskStatus.pending, TaskStatus.running}]
            hist = list(self._history)
        return {
            "active": [self._task_to_dict(t) for t in active],
            "history": [self._task_to_dict(t) for t in hist][-20:],
            "queue_size": self._queue.qsize(),
            "worker_count": len(self._workers) or self._worker_count(),
        }

    # ---------------------------
    # Worker callbacks (thread-safe)
    # ---------------------------
    def _on_started(self, task_id: str) -> None:
        with self._lock:
            t = self._tasks.get(task_id)
            if not t:
                return
            t.status = TaskStatus.running
            t.started_at = time.time()
            t.progress = max(t.progress, 0)

    def _on_progress(self, task_id: str, pct: int, msg: str) -> None:
        with self._lock:
            t = self._tasks.get(task_id)
            if not t:
                return
            t.progress = int(max(0, min(100, pct)))
            t.message = str(msg or "")

    def _on_completed(self, task_id: str, result: Any) -> None:
        with self._lock:
            t = self._tasks.get(task_id)
            if not t:
                return
            t.status = TaskStatus.completed
            t.progress = 100
            t.finished_at = time.time()
            t.result = result
            self._push_history(t)

    def _on_failed(self, task_id: str, error: str) -> None:
        with self._lock:
            t = self._tasks.get(task_id)
            if not t:
                return
            t.status = TaskStatus.failed
            t.finished_at = time.time()
            t.error = str(error or "Unknown error")
            self._push_history(t)

    def _on_cancelled(self, task_id: str) -> None:
        with self._lock:
            t = self._tasks.get(task_id)
            if not t:
                return
            t.status = TaskStatus.cancelled
            t.finished_at = time.time()
            t.message = "Cancelled"
            self._push_history(t)

    def _push_history(self, task: Task) -> None:
        # Keep last 20 completed/failed/cancelled tasks
        self._history.append(task)
        self._history = self._history[-20:]

    # ---------------------------
    # Progress emit
    # ---------------------------
    def _emit(self, stage: str, message: str, extra: Optional[dict] = None) -> None:
        if not self._progress_callback:
            return
        payload = {"stage": stage, "message": message}
        if extra:
            payload.update(extra)
        try:
            self._progress_callback(payload)
        except Exception:
            pass

    # ---------------------------
    # Serialization
    # ---------------------------
    @staticmethod
    def _task_to_dict(t: Task) -> Dict[str, Any]:
        return {
            "id": t.id,
            "type": str(t.type),
            "status": str(t.status),
            "progress": int(t.progress),
            "message": t.message,
            "created_at": t.created_at,
            "started_at": t.started_at,
            "finished_at": t.finished_at,
            "error": t.error,
        }


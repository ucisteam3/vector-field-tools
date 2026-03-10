from __future__ import annotations

from queue import Queue
from typing import Optional

from modules.background_tasks.task_worker import TaskEnvelope


class TaskQueue:
    def __init__(self) -> None:
        self.q: Queue[TaskEnvelope] = Queue()

    def put(self, item: TaskEnvelope) -> None:
        self.q.put(item)

    def get(self, timeout: Optional[float] = None) -> TaskEnvelope:
        return self.q.get(timeout=timeout)

    def task_done(self) -> None:
        self.q.task_done()

    def join(self) -> None:
        self.q.join()

    def empty(self) -> bool:
        return self.q.empty()

    def qsize(self) -> int:
        try:
            return self.q.qsize()
        except Exception:
            return 0


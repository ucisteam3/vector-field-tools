from __future__ import annotations

from dataclasses import dataclass, field
from queue import Queue
from typing import Any, Dict, Optional
import uuid


@dataclass
class RenderJob:
    """
    Generic render job payload.
    export pipeline should pass a processing_config from ProcessingEngine.
    """

    input_video: str
    clip_start: float
    clip_end: float
    output_path: str
    processing_config: Dict[str, Any] = field(default_factory=dict)
    job_id: str = field(default_factory=lambda: str(uuid.uuid4()))

    # Failsafe/retry
    attempts: int = 0
    max_attempts: int = 2
    last_error: Optional[str] = None


class JobQueueManager:
    def __init__(self) -> None:
        self.job_queue: Queue[RenderJob] = Queue()
        self.total_jobs: int = 0

    def add_job(self, job: RenderJob) -> None:
        self.job_queue.put(job)
        self.total_jobs += 1

    def get_job(self, timeout: Optional[float] = None) -> RenderJob:
        return self.job_queue.get(timeout=timeout)

    def task_done(self) -> None:
        self.job_queue.task_done()

    def join(self) -> None:
        self.job_queue.join()

    def empty(self) -> bool:
        return self.job_queue.empty()

    def qsize(self) -> int:
        try:
            return self.job_queue.qsize()
        except Exception:
            return 0


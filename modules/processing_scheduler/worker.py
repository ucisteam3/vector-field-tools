from __future__ import annotations

from typing import Callable, Optional
import traceback

from modules.processing_scheduler.queue_manager import RenderJob, JobQueueManager


ProcessFn = Callable[[RenderJob], None]
ProgressFn = Callable[[dict], None]


class Worker:
    """
    Worker that pulls jobs from a shared JobQueueManager and executes process_fn(job).
    Failures are re-queued until max_attempts is reached.
    """

    def __init__(
        self,
        *,
        worker_id: int,
        queue: JobQueueManager,
        process_fn: ProcessFn,
        progress_callback: Optional[ProgressFn] = None,
    ) -> None:
        self.worker_id = int(worker_id)
        self.queue = queue
        self.process_fn = process_fn
        self.progress_callback = progress_callback

    def _emit(self, stage: str, message: str, extra: Optional[dict] = None) -> None:
        if not self.progress_callback:
            return
        payload = {"stage": stage, "message": message, "worker_id": self.worker_id}
        if extra:
            payload.update(extra)
        try:
            self.progress_callback(payload)
        except Exception:
            pass

    def run_once(self) -> bool:
        """
        Process a single job. Returns True if a job was processed, False if queue was empty.
        """
        if self.queue.empty():
            return False
        try:
            job = self.queue.get_job(timeout=0.2)
        except Exception:
            return False

        try:
            self._emit("worker", f"Start job {job.job_id}", {"job_id": job.job_id})
            self.process_fn(job)
            self._emit("worker", f"Done job {job.job_id}", {"job_id": job.job_id})
        except Exception as e:
            job.attempts += 1
            job.last_error = f"{type(e).__name__}: {e}"
            tb = traceback.format_exc(limit=5)
            self._emit(
                "worker_error",
                f"Job failed {job.job_id} (attempt {job.attempts}/{job.max_attempts}): {job.last_error}",
                {"job_id": job.job_id, "error": job.last_error, "trace": tb},
            )
            if job.attempts <= job.max_attempts:
                # Requeue
                self.queue.job_queue.put(job)
        finally:
            try:
                self.queue.task_done()
            except Exception:
                pass

        return True


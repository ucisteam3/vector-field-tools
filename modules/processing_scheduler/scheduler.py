from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, Future
from typing import Callable, Dict, Optional, Any, List
import time

try:
    import psutil  # type: ignore
except Exception:
    psutil = None  # type: ignore

from modules.runtime_manager import RuntimeManager
from modules.processing_scheduler.queue_manager import JobQueueManager, RenderJob
from modules.processing_scheduler.worker import Worker, ProcessFn, ProgressFn


class SmartProcessingScheduler:
    """
    SmartProcessingScheduler
    - Uses RuntimeManager hardware classification to pick worker count.
    - Uses ProcessingEngine config (encoder) to limit GPU workers.
    - Monitors CPU load (psutil) and throttles when usage > 90%.
    - Requeues failed jobs (Worker handles retry).
    """

    def __init__(
        self,
        *,
        process_fn: ProcessFn,
        progress_callback: Optional[ProgressFn] = None,
    ) -> None:
        self.queue = JobQueueManager()
        self.process_fn = process_fn
        self.progress_callback = progress_callback

        self.total_jobs: int = 0
        self.completed_jobs: int = 0
        self.running_jobs: int = 0

        self._stop: bool = False

    def _emit(self, stage: str, message: str, extra: Optional[dict] = None) -> None:
        if not self.progress_callback:
            return
        payload = {
            "stage": stage,
            "message": message,
            "total_jobs": self.total_jobs,
            "completed_jobs": self.completed_jobs,
            "running_jobs": self.running_jobs,
            "queued_jobs": self.queue.qsize(),
        }
        if extra:
            payload.update(extra)
        try:
            self.progress_callback(payload)
        except Exception:
            pass

    # ---------------------------
    # Job queue API
    # ---------------------------
    def add_job(self, job: RenderJob) -> None:
        self.queue.add_job(job)
        self.total_jobs = self.queue.total_jobs
        self._emit("queue", f"Job added {job.job_id}", {"job_id": job.job_id})

    def stop(self) -> None:
        self._stop = True

    # ---------------------------
    # Worker sizing
    # ---------------------------
    def _cpu_overloaded(self) -> bool:
        if psutil is None:
            return False
        try:
            # Short interval read.
            cpu = float(psutil.cpu_percent(interval=0.2))
            return cpu >= 90.0
        except Exception:
            return False

    def _compute_worker_count(self, *, encoder: Optional[str] = None) -> int:
        hw = RuntimeManager.detect_hardware()
        tier = RuntimeManager.classify_performance(hw)
        cores = int(hw.cores or 0)

        if tier == "POTATO_PC":
            max_workers = 1
        elif tier == "MEDIUM_PC":
            max_workers = min(max(1, cores // 2), 3)
        else:
            max_workers = min(max(1, cores // 2), 6)

        # GPU limits
        enc = (encoder or "").lower()
        if enc in ["h264_nvenc", "hevc_nvenc", "av1_nvenc"]:
            max_workers = min(max_workers, 3)
        if enc in ["h264_amf", "hevc_amf", "av1_amf"]:
            max_workers = min(max_workers, 3)

        return max(1, int(max_workers))

    # ---------------------------
    # Run loop
    # ---------------------------
    def _run_worker_loop(self, worker_id: int) -> None:
        worker = Worker(worker_id=worker_id, queue=self.queue, process_fn=self.process_fn, progress_callback=self.progress_callback)
        while not self._stop:
            did = worker.run_once()
            if not did:
                # queue empty -> exit
                return

    def run(self, *, encoder: Optional[str] = None) -> Dict[str, Any]:
        """
        Run all queued jobs with dynamic worker sizing and throttling.
        Returns final summary.
        """
        self._stop = False
        self.completed_jobs = 0
        self.running_jobs = 0
        self.total_jobs = self.queue.total_jobs

        max_workers = self._compute_worker_count(encoder=encoder)
        self._emit("scheduler", f"Starting scheduler with {max_workers} workers", {"max_workers": max_workers, "encoder": encoder})

        futures: List[Future] = []
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            # Spawn workers gradually, pausing when CPU overloaded
            for wid in range(max_workers):
                if self._stop:
                    break
                while self._cpu_overloaded() and not self._stop:
                    self._emit("throttle", "CPU usage high (>90%), delaying worker spawn...")
                    time.sleep(0.5)
                self.running_jobs += 1
                futures.append(pool.submit(self._run_worker_loop, wid))

            # Monitor completion
            while futures and not self._stop:
                done = [f for f in futures if f.done()]
                for f in done:
                    futures.remove(f)
                    self.running_jobs = max(0, self.running_jobs - 1)
                    # Worker loop ended; may still have queued jobs (requeued failures, etc.)
                    if not self.queue.empty() and not self._stop:
                        # Respawn a worker, but respect throttle
                        while self._cpu_overloaded() and not self._stop:
                            self._emit("throttle", "CPU usage high (>90%), delaying worker respawn...")
                            time.sleep(0.5)
                        self.running_jobs += 1
                        futures.append(pool.submit(self._run_worker_loop, max_workers + int(time.time()) % 100000))

                # Update completed count heuristically:
                # completed = total - (queued remaining)
                queued = self.queue.qsize()
                self.completed_jobs = max(0, self.total_jobs - queued)
                self._emit("progress", "Rendering...", {})

                if self.queue.empty() and all(f.done() for f in futures):
                    break
                time.sleep(0.3)

        self.completed_jobs = self.total_jobs
        self.running_jobs = 0
        self._emit("done", "All jobs completed")
        return {
            "total_jobs": self.total_jobs,
            "completed_jobs": self.completed_jobs,
            "running_jobs": self.running_jobs,
            "queued_jobs": self.queue.qsize(),
        }


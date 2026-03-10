from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Any
import os
import subprocess

from modules.runtime_paths import ffmpeg_cmd
from modules.processing_engine.engine import get_best_processing_config
from modules.batch_encoder.filter_graph_builder import FilterGraphBuilder, BatchClipSpec
from modules.batch_encoder.batch_builder import BatchJob


ProgressFn = Callable[[dict], None]
FallbackFn = Callable[[BatchClipSpec], None]


def _ensure_parent(p: str) -> None:
    Path(p).parent.mkdir(parents=True, exist_ok=True)


class BatchExecutor:
    """
    Executes one FFmpeg process for a batch of clips from a single input.
    Failsafe: if ffmpeg fails, fallback_fn will be called per clip (if provided).
    """

    def __init__(self, *, progress_callback: Optional[ProgressFn] = None):
        self.progress_callback = progress_callback
        self.fgb = FilterGraphBuilder()

    def _emit(self, stage: str, message: str, extra: Optional[dict] = None) -> None:
        if not self.progress_callback:
            return
        payload = {"stage": stage, "message": message}
        if extra:
            payload.update(extra)
        try:
            self.progress_callback(payload)
        except Exception:
            pass

    def build_command(self, batch: BatchJob, *, processing_override: str = "auto") -> List[str]:
        if not Path(batch.input_video).exists():
            raise FileNotFoundError(f"Input missing: {batch.input_video}")
        for c in batch.clips:
            _ensure_parent(c.output)

        proc = get_best_processing_config(override=processing_override)
        enc_args = list(proc.get("ffmpeg_args") or [])

        fc = self.fgb.build(batch.clips)

        cmd: List[str] = [
            ffmpeg_cmd(),
            "-y",
            "-hide_banner",
            "-loglevel",
            "warning",
            "-i",
            str(batch.input_video),
            "-filter_complex",
            fc,
        ]

        # Map each clip output, applying encoder args per output.
        # Per-output options in FFmpeg should come before the output filename.
        for i, c in enumerate(batch.clips):
            cmd += ["-map", f"[v{i}out]"]
            cmd += ["-map", f"[a{i}out]"]
            cmd += enc_args
            cmd += ["-c:a", "aac", "-b:a", "128k"]
            cmd += [str(c.output)]

        return cmd

    def execute_batch(
        self,
        batch: BatchJob,
        *,
        processing_override: str = "auto",
        fallback_fn: Optional[FallbackFn] = None,
    ) -> Dict[str, Any]:
        """
        Run batch encoding. Returns summary.
        """
        cmd = self.build_command(batch, processing_override=processing_override)
        self._emit("batch", f"Rendering {len(batch.clips)} clips in single pipeline.", {"clip_count": len(batch.clips)})
        print("[BATCH ENCODER]")
        print(f"Rendering {len(batch.clips)} clips in single pipeline.")
        print(" ".join(cmd))

        creationflags = 0x08000000 if os.name == "nt" else 0
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, creationflags=creationflags)
        except Exception as e:
            r = None
            err = f"{type(e).__name__}: {e}"
            self._emit("batch_error", f"Batch process failed to start: {err}", {"error": err})

        ok = bool(r is not None and getattr(r, "returncode", 1) == 0)
        if ok:
            self._emit("batch_done", "Batch completed")
            return {"ok": True, "returncode": 0, "clips": len(batch.clips)}

        # Batch failed -> failsafe
        out_txt = ""
        if r is not None:
            out_txt = (r.stdout or "") + (r.stderr or "")
        self._emit("batch_fail", "Batch failed; falling back to individual renders", {"returncode": getattr(r, "returncode", None), "log": out_txt[-2000:]})

        if fallback_fn:
            for c in batch.clips:
                try:
                    fallback_fn(c)
                except Exception:
                    pass
            return {"ok": False, "returncode": getattr(r, "returncode", None), "fallback": True, "clips": len(batch.clips)}

        return {"ok": False, "returncode": getattr(r, "returncode", None), "fallback": False, "clips": len(batch.clips), "log": out_txt[-2000:]}


from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional
import os

from modules.pipeline_optimizer.pipeline_builder import PipelineBuilder, PipelineJob


@dataclass
class OptimizerResult:
    command: List[str]
    encoder: str
    plugin: str


class ClipRenderingPipelineOptimizer:
    """
    High-level API:
      - builds a single FFmpeg command per clip (no temp video files)
      - logs final command
    """

    def __init__(self) -> None:
        self.builder = PipelineBuilder()

    def build(self, job: PipelineJob) -> OptimizerResult:
        cmd = self.builder.build_command(job)
        # Extract encoder/plugin info heuristically from args
        encoder = "unknown"
        plugin = "auto"
        try:
            if "-c:v" in cmd:
                encoder = cmd[cmd.index("-c:v") + 1]
            if encoder == "h264_nvenc":
                plugin = "nvenc"
            elif encoder == "h264_amf":
                plugin = "amf"
            elif encoder == "libx264":
                plugin = "cpu"
        except Exception:
            pass

        print("[PIPELINE] Running FFmpeg:")
        print(" ".join(cmd))
        return OptimizerResult(command=cmd, encoder=encoder, plugin=plugin)


from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from modules.batch_encoder.filter_graph_builder import BatchClipSpec


@dataclass
class BatchJob:
    input_video: str
    clips: List[BatchClipSpec]


class BatchBuilder:
    """
    Groups clip specs by input video, splits into batches.
    Batch mode enabled only if clip_count >= 3.
    """

    def __init__(self, *, max_clips_per_batch: int = 6, enable_threshold: int = 3) -> None:
        self.max_clips_per_batch = int(max(1, max_clips_per_batch))
        self.enable_threshold = int(max(1, enable_threshold))

    def build_batches(self, input_video: str, clips: List[BatchClipSpec]) -> List[BatchJob]:
        if len(clips) < self.enable_threshold:
            # Not worth batching
            return [BatchJob(input_video=input_video, clips=clips)]

        out: List[BatchJob] = []
        buf: List[BatchClipSpec] = []
        for c in clips:
            buf.append(c)
            if len(buf) >= self.max_clips_per_batch:
                out.append(BatchJob(input_video=input_video, clips=buf))
                buf = []
        if buf:
            out.append(BatchJob(input_video=input_video, clips=buf))
        return out


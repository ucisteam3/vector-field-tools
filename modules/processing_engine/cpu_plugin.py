from __future__ import annotations

from typing import Any, Dict, List

from modules.processing_engine.base_plugin import BaseProcessingPlugin


class CPUPlugin(BaseProcessingPlugin):
    name = "cpu"
    label = "CPU (libx264)"
    acceleration = "cpu"

    def is_available(self, hardware_info: Dict[str, Any]) -> bool:
        # Always available as fallback.
        return True

    def get_encoder(self) -> str:
        return "libx264"

    def get_ffmpeg_args(self) -> List[str]:
        # Good default quality/speed tradeoff.
        return ["-c:v", "libx264", "-preset", "fast", "-crf", "23"]


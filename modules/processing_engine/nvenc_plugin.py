from __future__ import annotations

from typing import Any, Dict, List

from modules.processing_engine.base_plugin import BaseProcessingPlugin


class NVENCPlugin(BaseProcessingPlugin):
    name = "nvenc"
    label = "NVIDIA NVENC"
    acceleration = "nvidia"

    def is_available(self, hardware_info: Dict[str, Any]) -> bool:
        # Activate only if CUDA is available (RuntimeManager uses torch.cuda.is_available()).
        return bool(hardware_info.get("cuda"))

    def get_encoder(self) -> str:
        return "h264_nvenc"

    def get_ffmpeg_args(self) -> List[str]:
        # Conservative default bitrate preset; can be tuned later.
        return ["-c:v", "h264_nvenc", "-preset", "p4", "-b:v", "5M"]


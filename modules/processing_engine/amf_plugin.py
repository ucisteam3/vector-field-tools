from __future__ import annotations

from typing import Any, Dict, List

from modules.processing_engine.base_plugin import BaseProcessingPlugin


class AMFPlugin(BaseProcessingPlugin):
    name = "amf"
    label = "AMD AMF"
    acceleration = "amd"

    def is_available(self, hardware_info: Dict[str, Any]) -> bool:
        gpu = str(hardware_info.get("gpu") or "").lower()
        # RuntimeManager.detect_gpu_vendor() can provide vendor, but engine passes gpu string too.
        return ("amd" in gpu) or ("radeon" in gpu) or (hardware_info.get("gpu_vendor") == "amd")

    def get_encoder(self) -> str:
        return "h264_amf"

    def get_ffmpeg_args(self) -> List[str]:
        return ["-c:v", "h264_amf", "-quality", "speed"]


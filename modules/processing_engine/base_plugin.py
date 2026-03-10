from __future__ import annotations

from typing import Any, Dict, List


class BaseProcessingPlugin:
    """
    Base class for video processing plugins.

    Plugins decide:
      - availability based on hardware info
      - encoder name
      - ffmpeg encoder args
    """

    name: str = "base"
    label: str = "Base"
    acceleration: str = "none"  # none | nvidia | amd | cpu

    def is_available(self, hardware_info: Dict[str, Any]) -> bool:
        return False

    def get_encoder(self) -> str:
        raise NotImplementedError

    def get_ffmpeg_args(self) -> List[str]:
        raise NotImplementedError

    def describe(self) -> Dict[str, Any]:
        return {
            "plugin": self.name,
            "label": self.label,
            "acceleration": self.acceleration,
            "encoder": self.get_encoder(),
            "ffmpeg_args": self.get_ffmpeg_args(),
        }


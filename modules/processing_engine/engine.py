from __future__ import annotations

from typing import Any, Dict, List, Optional

from modules.processing_engine.cpu_plugin import CPUPlugin
from modules.processing_engine.nvenc_plugin import NVENCPlugin
from modules.processing_engine.amf_plugin import AMFPlugin
from modules.runtime_manager import RuntimeManager, HardwareInfo


def _hw_to_dict(hw: Any) -> Dict[str, Any]:
    """
    Normalize hardware info input to a dict.
    Accepts:
      - RuntimeManager.HardwareInfo dataclass
      - dict with keys cpu/cores/ram_gb/gpu/vram_gb/cuda
    """
    if isinstance(hw, dict):
        d = dict(hw)
    elif isinstance(hw, HardwareInfo):
        d = {
            "cpu": hw.cpu,
            "cores": hw.cores,
            "ram_gb": hw.ram_gb,
            "gpu": hw.gpu,
            "vram_gb": hw.vram_gb,
            "cuda": hw.cuda,
        }
    else:
        # Best effort: ask RuntimeManager
        h = RuntimeManager.detect_hardware()
        d = {
            "cpu": h.cpu,
            "cores": h.cores,
            "ram_gb": h.ram_gb,
            "gpu": h.gpu,
            "vram_gb": h.vram_gb,
            "cuda": h.cuda,
        }
    # Add vendor hint when available
    try:
        d["gpu_vendor"] = RuntimeManager.detect_gpu_vendor()
    except Exception:
        pass
    return d


class ProcessingEngine:
    """
    Plugin-based processing engine that selects optimal encoder pipeline
    based on detected hardware, with optional manual override.
    """

    def __init__(self, plugins: Optional[List[Any]] = None):
        # Priority: NVENC > AMF > CPU
        self.plugins = plugins or [NVENCPlugin(), AMFPlugin(), CPUPlugin()]

    def select_best_plugin(self, hardware_info: Dict[str, Any]) -> Any:
        for p in self.plugins:
            try:
                if p.is_available(hardware_info):
                    return p
            except Exception:
                continue
        return CPUPlugin()

    def select_plugin_with_override(self, hardware_info: Dict[str, Any], override: str) -> Any:
        """
        override:
          - "auto" (recommended)
          - "cpu"
          - "nvidia"
          - "amd"
        """
        o = (override or "auto").strip().lower()
        if o in ["auto", "recommended", ""]:
            return self.select_best_plugin(hardware_info)
        if o in ["cpu", "cpu_only"]:
            return CPUPlugin()
        if o in ["nvidia", "nvenc", "nvidia_gpu"]:
            p = NVENCPlugin()
            return p if p.is_available(hardware_info) else CPUPlugin()
        if o in ["amd", "amf", "amd_gpu"]:
            p = AMFPlugin()
            return p if p.is_available(hardware_info) else CPUPlugin()
        # Unknown override -> auto
        return self.select_best_plugin(hardware_info)

    def get_best_processing_config(self, *, override: str = "auto", hardware: Any = None) -> Dict[str, Any]:
        hw = _hw_to_dict(hardware if hardware is not None else RuntimeManager.detect_hardware())
        plugin = self.select_plugin_with_override(hw, override)

        mode = "CPU Only"
        if plugin.name == "nvenc":
            mode = "GPU Acceleration"
        elif plugin.name == "amf":
            mode = "GPU Acceleration"

        return {
            "processing_mode": mode,
            "encoder": plugin.get_encoder(),
            "plugin": plugin.name,
            "plugin_label": getattr(plugin, "label", plugin.name),
            "hardware_acceleration": getattr(plugin, "acceleration", "none"),
            "ffmpeg_args": plugin.get_ffmpeg_args(),
            "hardware": hw,
        }


def get_best_processing_config(*, override: str = "auto", hardware: Any = None) -> Dict[str, Any]:
    """
    Convenience function for callers (backend/UI/pipeline).
    """
    engine = ProcessingEngine()
    return engine.get_best_processing_config(override=override, hardware=hardware)


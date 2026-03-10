"""
Runtime Manager

Single responsibility: manage application runtime dependencies that must live
inside the application directory (runtime/*).

This module is additive and does not change existing pipeline behavior by itself.
Call RuntimeManager.initialize() at app start, and use get_status() for frontend.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional
import os
import platform
import shutil
import subprocess
import time

try:
    import psutil  # type: ignore
except Exception:
    psutil = None  # type: ignore

try:
    import torch  # type: ignore
except Exception:
    torch = None  # type: ignore

try:
    import whisper  # type: ignore
except Exception:
    whisper = None  # type: ignore

from modules.runtime_paths import (
    PROJECT_ROOT,
    RUNTIME_DIR,
    FFMPEG_PATH,
    FFPROBE_PATH,
    WHISPER_MODELS_DIR,
    ffmpeg_cmd,
    ffprobe_cmd,
    whisper_download_root,
)


WHISPER_MODEL_OPTIONS: List[str] = ["tiny", "base", "small", "medium", "large"]


@dataclass(frozen=True)
class HardwareInfo:
    cpu: str
    cores: int
    ram_gb: float
    gpu: Optional[str]
    vram_gb: Optional[float]
    cuda: bool


class RuntimeManager:
    """
    RuntimeManager manages bundled/runtime dependencies in:
      runtime/bin, runtime/models, runtime/gpu, runtime/temp, runtime/downloads

    It does NOT modify unrelated modules; it only provides utilities and checks.
    """

    # --- Runtime directories ---
    root: Path = PROJECT_ROOT
    runtime_dir: Path = RUNTIME_DIR
    bin_dir: Path = RUNTIME_DIR / "bin"
    models_dir: Path = RUNTIME_DIR / "models"
    whisper_dir: Path = WHISPER_MODELS_DIR
    gpu_dir: Path = RUNTIME_DIR / "gpu"
    cuda_dir: Path = RUNTIME_DIR / "gpu" / "cuda"
    amd_dir: Path = RUNTIME_DIR / "gpu" / "amd"
    temp_dir: Path = RUNTIME_DIR / "temp"
    downloads_dir: Path = RUNTIME_DIR / "downloads"

    # --- Runtime binaries ---
    ffmpeg_path: Path = FFMPEG_PATH
    ffprobe_path: Path = FFPROBE_PATH

    @classmethod
    def initialize(cls) -> None:
        """Create runtime directory structure if missing."""
        cls.bin_dir.mkdir(parents=True, exist_ok=True)
        cls.models_dir.mkdir(parents=True, exist_ok=True)
        cls.whisper_dir.mkdir(parents=True, exist_ok=True)
        cls.gpu_dir.mkdir(parents=True, exist_ok=True)
        cls.cuda_dir.mkdir(parents=True, exist_ok=True)
        cls.amd_dir.mkdir(parents=True, exist_ok=True)
        cls.temp_dir.mkdir(parents=True, exist_ok=True)
        cls.downloads_dir.mkdir(parents=True, exist_ok=True)

    # ---------------------------
    # FFmpeg runtime verification
    # ---------------------------
    @classmethod
    def verify_ffmpeg(cls) -> bool:
        """
        Verify bundled FFmpeg exists. Does NOT download.
        Raises RuntimeError if missing, per spec.
        """
        if not cls.ffmpeg_path.exists() or not cls.ffprobe_path.exists():
            raise RuntimeError("FFmpeg runtime missing")
        return True

    @classmethod
    def ffmpeg_paths(cls) -> Dict[str, str]:
        """Return resolved command paths used by the app (bundled if exists, else PATH fallback)."""
        return {
            "ffmpeg": ffmpeg_cmd(),
            "ffprobe": ffprobe_cmd(),
            "bundled_ffmpeg_exists": str(cls.ffmpeg_path.exists()).lower(),
            "bundled_ffprobe_exists": str(cls.ffprobe_path.exists()).lower(),
            "bundled_ffmpeg_path": str(cls.ffmpeg_path),
            "bundled_ffprobe_path": str(cls.ffprobe_path),
        }

    # ---------------------------
    # Whisper model management
    # ---------------------------
    @classmethod
    def _model_file_path(cls, model_name: str) -> Path:
        # openai-whisper stores as <model>.pt inside download_root
        return cls.whisper_dir / f"{model_name}.pt"

    @classmethod
    def is_model_installed(cls, model_name: str) -> bool:
        if model_name not in WHISPER_MODEL_OPTIONS:
            return False
        return cls._model_file_path(model_name).exists()

    @classmethod
    def installed_models(cls) -> List[str]:
        out: List[str] = []
        for m in WHISPER_MODEL_OPTIONS:
            if cls.is_model_installed(m):
                out.append(m)
        return out

    @classmethod
    def download_model(cls, model_name: str) -> bool:
        """
        Download model into runtime/models/whisper using whisper.load_model(download_root=...).
        Returns True if installed after attempt.
        """
        if model_name not in WHISPER_MODEL_OPTIONS:
            raise ValueError(f"Unknown whisper model: {model_name}")
        if whisper is None:
            raise RuntimeError("Whisper library not installed")

        cls.initialize()
        root = whisper_download_root()
        # CPU device is enough to trigger download; avoids requiring CUDA just to fetch model.
        _ = whisper.load_model(model_name, device="cpu", download_root=root)
        return cls.is_model_installed(model_name)

    # ---------------------------
    # GPU runtime management
    # ---------------------------
    @classmethod
    def is_cuda_installed(cls) -> bool:
        """
        Optional GPU runtime marker check.
        Since CUDA runtime bundling/downloading is platform- and licensing-dependent,
        we treat 'installed' as: directory contains any file (or marker).
        """
        try:
            if not cls.cuda_dir.exists():
                return False
            return any(cls.cuda_dir.iterdir())
        except Exception:
            return False

    @classmethod
    def is_amd_runtime_installed(cls) -> bool:
        try:
            if not cls.amd_dir.exists():
                return False
            return any(cls.amd_dir.iterdir())
        except Exception:
            return False

    @classmethod
    def download_cuda_runtime(cls) -> None:
        """
        Placeholder: create marker file for now.
        Real CUDA runtime download requires a chosen distribution source and EULA handling.
        """
        cls.initialize()
        marker = cls.cuda_dir / "RUNTIME_NOT_INSTALLED.txt"
        if not marker.exists():
            marker.write_text(
                "CUDA runtime download is not configured.\n"
                "Place your CUDA runtime files into runtime/gpu/cuda/.\n",
                encoding="utf-8",
            )

    @classmethod
    def download_amd_runtime(cls) -> None:
        """Placeholder marker; see download_cuda_runtime()."""
        cls.initialize()
        marker = cls.amd_dir / "RUNTIME_NOT_INSTALLED.txt"
        if not marker.exists():
            marker.write_text(
                "AMD runtime download is not configured.\n"
                "Place your AMD runtime files into runtime/gpu/amd/.\n",
                encoding="utf-8",
            )

    # ---------------------------
    # Hardware detection
    # ---------------------------
    @classmethod
    def detect_hardware(cls) -> HardwareInfo:
        cpu = platform.processor() or platform.uname().processor or "Unknown"
        cores = os.cpu_count() or 0

        ram_gb = 0.0
        if psutil is not None:
            try:
                ram_gb = float(psutil.virtual_memory().total) / 1024 / 1024 / 1024
            except Exception:
                ram_gb = 0.0

        cuda = False
        gpu_name: Optional[str] = None
        vram_gb: Optional[float] = None

        if torch is not None:
            try:
                cuda = bool(torch.cuda.is_available())
                if cuda and torch.cuda.device_count():
                    gpu_name = torch.cuda.get_device_name(0)
                    try:
                        props = torch.cuda.get_device_properties(0)
                        total_mem = float(getattr(props, "total_memory", 0) or 0)
                        if total_mem > 0:
                            vram_gb = total_mem / 1024 / 1024 / 1024
                    except Exception:
                        pass
            except Exception:
                cuda = False

        return HardwareInfo(
            cpu=cpu,
            cores=int(cores),
            ram_gb=float(ram_gb),
            gpu=gpu_name,
            vram_gb=vram_gb,
            cuda=bool(cuda),
        )

    # ---------------------------
    # Performance classification
    # ---------------------------
    @classmethod
    def classify_performance(cls, hw: Optional[HardwareInfo] = None) -> str:
        hw = hw or cls.detect_hardware()
        has_gpu = bool(hw.gpu) or bool(hw.cuda)
        vram = float(hw.vram_gb or 0.0)

        if hw.cores >= 8 and hw.ram_gb >= 32.0 and vram >= 8.0:
            return "SULTAN_PC"
        if hw.cores >= 6 and hw.ram_gb >= 16.0:
            return "MEDIUM_PC"
        if hw.cores < 4 or hw.ram_gb < 8.0 or not has_gpu:
            return "POTATO_PC"
        return "POTATO_PC"

    # ---------------------------
    # Auto processing config
    # ---------------------------
    @classmethod
    def _ffmpeg_has_encoder(cls, encoder_name: str) -> bool:
        """
        Detect encoder availability using bundled ffmpeg if present.
        """
        try:
            r = subprocess.run(
                [ffmpeg_cmd(), "-hide_banner", "-encoders"],
                capture_output=True,
                text=True,
                timeout=8,
                creationflags=0x08000000 if os.name == "nt" else 0,
            )
            out = (r.stdout or "") + (r.stderr or "")
            return encoder_name.lower() in out.lower()
        except Exception:
            return False

    @classmethod
    def recommend_processing_config(cls) -> Dict[str, str]:
        hw = cls.detect_hardware()
        tier = cls.classify_performance(hw)

        # Default encoder for safety
        encoder = "libx264"
        mode = "cpu"
        whisper_model = "tiny"

        # Encoder selection
        nvenc_ok = hw.cuda and cls._ffmpeg_has_encoder("h264_nvenc")
        amf_ok = cls._ffmpeg_has_encoder("h264_amf")

        if tier == "SULTAN_PC":
            mode = "gpu" if (hw.cuda or cls.is_cuda_installed() or cls.is_amd_runtime_installed()) else "mixed"
            whisper_model = "medium"
            if nvenc_ok:
                encoder = "h264_nvenc"
            elif amf_ok:
                encoder = "h264_amf"
            else:
                encoder = "libx264"
        elif tier == "MEDIUM_PC":
            mode = "mixed"
            whisper_model = "small"
            if nvenc_ok:
                encoder = "h264_nvenc"
            elif amf_ok:
                encoder = "h264_amf"
            else:
                encoder = "libx264"
        else:
            mode = "cpu"
            whisper_model = "tiny" if hw.ram_gb < 8.0 else "base"
            encoder = "libx264"

        return {"mode": mode, "encoder": encoder, "whisper_model": whisper_model}

    # ---------------------------
    # Temp file cleanup
    # ---------------------------
    @classmethod
    def cleanup_temp(cls, *, older_than_hours: float = 24.0) -> Dict[str, Any]:
        """
        Deletes files in runtime/temp older than threshold.
        Returns summary {deleted, kept, errors}.
        """
        cls.initialize()
        cutoff = time.time() - (older_than_hours * 3600.0)
        deleted = 0
        kept = 0
        errors: List[str] = []

        try:
            for p in cls.temp_dir.glob("**/*"):
                try:
                    if p.is_dir():
                        continue
                    st = p.stat()
                    if st.st_mtime < cutoff:
                        p.unlink(missing_ok=True)
                        deleted += 1
                    else:
                        kept += 1
                except Exception as e:
                    errors.append(f"{p}: {e}")
        except Exception as e:
            errors.append(str(e))

        # Best-effort: remove empty dirs
        try:
            for d in sorted([x for x in cls.temp_dir.glob("**/*") if x.is_dir()], reverse=True):
                try:
                    d.rmdir()
                except Exception:
                    pass
        except Exception:
            pass

        return {"deleted": deleted, "kept": kept, "errors": errors}

    # ---------------------------
    # Frontend/API status payload
    # ---------------------------
    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """
        Status payload for frontend API:
          - hardware info
          - installed models
          - gpu runtime availability
          - ffmpeg runtime presence
          - recommended processing config
        """
        cls.initialize()
        hw = cls.detect_hardware()
        tier = cls.classify_performance(hw)
        rec = cls.recommend_processing_config()

        ffmpeg_ok = bool(cls.ffmpeg_path.exists() and cls.ffprobe_path.exists())

        return {
            "paths": {
                "project_root": str(cls.root),
                "runtime_dir": str(cls.runtime_dir),
                "bin_dir": str(cls.bin_dir),
                "whisper_dir": str(cls.whisper_dir),
                "gpu_dir": str(cls.gpu_dir),
                "temp_dir": str(cls.temp_dir),
                "downloads_dir": str(cls.downloads_dir),
                "ffmpeg": str(cls.ffmpeg_path),
                "ffprobe": str(cls.ffprobe_path),
            },
            "ffmpeg": {
                "bundled_present": ffmpeg_ok,
                "error": None if ffmpeg_ok else "FFmpeg runtime missing",
            },
            "whisper": {
                "available": whisper is not None,
                "models_dir": str(cls.whisper_dir),
                "installed": cls.installed_models(),
                "options": WHISPER_MODEL_OPTIONS,
            },
            "gpu_runtime": {
                "cuda_installed": cls.is_cuda_installed(),
                "amd_installed": cls.is_amd_runtime_installed(),
                "torch_cuda_available": bool(hw.cuda),
            },
            "hardware": {
                "cpu": hw.cpu,
                "cores": hw.cores,
                "ram_gb": round(hw.ram_gb, 2),
                "gpu": hw.gpu,
                "vram_gb": round(float(hw.vram_gb), 2) if hw.vram_gb is not None else None,
                "cuda": hw.cuda,
                "tier": tier,
            },
            "recommended": rec,
        }


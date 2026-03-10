"""Runtime paths for bundled binaries/models.

This module is additive and safe: if bundled binaries do not exist,
callers may fall back to system PATH.
"""

from __future__ import annotations

from pathlib import Path
import os

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RUNTIME_DIR = PROJECT_ROOT / "runtime"

FFMPEG_PATH = RUNTIME_DIR / "bin" / ("ffmpeg.exe" if os.name == "nt" else "ffmpeg")
FFPROBE_PATH = RUNTIME_DIR / "bin" / ("ffprobe.exe" if os.name == "nt" else "ffprobe")

WHISPER_MODELS_DIR = RUNTIME_DIR / "models" / "whisper"


def ffmpeg_cmd() -> str:
    """Return bundled ffmpeg path if present, else 'ffmpeg'."""
    return str(FFMPEG_PATH) if FFMPEG_PATH.exists() else "ffmpeg"


def ffprobe_cmd() -> str:
    """Return bundled ffprobe path if present, else 'ffprobe'."""
    return str(FFPROBE_PATH) if FFPROBE_PATH.exists() else "ffprobe"


def whisper_download_root() -> str:
    """Whisper model download root inside app directory."""
    WHISPER_MODELS_DIR.mkdir(parents=True, exist_ok=True)
    return str(WHISPER_MODELS_DIR)

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
import json
import os
import platform
import subprocess
import time
import urllib.request
import zipfile

try:
    import hashlib
except Exception:
    hashlib = None  # type: ignore

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

    # --- Manifest / update scheduling ---
    manifest_path: Path = RUNTIME_DIR / "manifest.json"
    update_interval_sec: int = 24 * 3600

    # Default FFmpeg sources (Windows static builds)
    ffmpeg_zip_url: str = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
    ffmpeg_remote_version_url: str = "https://www.gyan.dev/ffmpeg/builds/release-version"

    @classmethod
    def _emit(cls, progress_callback, *, stage: str, pct: Optional[int] = None, message: str = "", extra: Optional[dict] = None) -> None:
        """Send progress events to UI (best-effort)."""
        if not progress_callback or not callable(progress_callback):
            return
        payload = {"stage": stage, "message": message}
        if pct is not None:
            payload["pct"] = int(max(0, min(100, pct)))
        if extra:
            payload.update(extra)
        try:
            progress_callback(payload)
        except Exception:
            pass

    # ---------------------------
    # Manifest
    # ---------------------------
    @classmethod
    def _default_manifest(cls) -> dict:
        return {
            "ffmpeg_version": "",
            "whisper_models": [],
            "cuda_installed": False,
            "amd_installed": False,
            "last_update_check_ts": 0,
        }

    @classmethod
    def load_manifest(cls) -> dict:
        cls.initialize()
        try:
            if cls.manifest_path.exists():
                data = json.loads(cls.manifest_path.read_text(encoding="utf-8")) or {}
                if isinstance(data, dict):
                    return {**cls._default_manifest(), **data}
        except Exception:
            pass
        return cls._default_manifest()

    @classmethod
    def save_manifest(cls, patch: dict) -> dict:
        cls.initialize()
        prev = cls.load_manifest()
        safe_patch = patch if isinstance(patch, dict) else {}
        merged = {**prev, **safe_patch}
        cls.manifest_path.write_text(json.dumps(merged, indent=2), encoding="utf-8")
        return merged

    # ---------------------------
    # Safe download helpers
    # ---------------------------
    @classmethod
    def _download_file(cls, url: str, dest: Path, *, progress_callback=None) -> Path:
        """
        Download into runtime/downloads then return the path.
        Uses atomic temp + rename.
        """
        cls.initialize()
        dest.parent.mkdir(parents=True, exist_ok=True)
        tmp = dest.with_suffix(dest.suffix + ".part")
        if tmp.exists():
            try:
                tmp.unlink()
            except Exception:
                pass

        cls._emit(progress_callback, stage="downloading", pct=0, message=f"Downloading: {url}")

        req = urllib.request.Request(url, headers={"User-Agent": "HEATMAP5-RuntimeManager/1.0"})
        with urllib.request.urlopen(req, timeout=60) as r:
            total = int(r.headers.get("Content-Length") or 0)
            read = 0
            chunk = 1024 * 256
            with open(tmp, "wb") as f:
                while True:
                    b = r.read(chunk)
                    if not b:
                        break
                    f.write(b)
                    read += len(b)
                    if total > 0:
                        pct = int(min(99, (read / total) * 100))
                        cls._emit(progress_callback, stage="downloading", pct=pct, message=f"Downloading... {pct}%")

        if tmp.stat().st_size <= 0:
            raise RuntimeError("Download failed (empty file)")
        try:
            tmp.replace(dest)
        except Exception:
            # fallback copy
            data = tmp.read_bytes()
            dest.write_bytes(data)
            try:
                tmp.unlink()
            except Exception:
                pass
        cls._emit(progress_callback, stage="downloading", pct=100, message="Download complete")
        return dest

    @classmethod
    def _sha256(cls, path: Path) -> Optional[str]:
        if hashlib is None:
            return None
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    # ---------------------------
    # FFmpeg auto install/update
    # ---------------------------
    @classmethod
    def _detect_local_ffmpeg_version(cls) -> str:
        """
        Detect local version via `ffmpeg -version`.
        Returns a short version like '6.1' when possible.
        """
        try:
            r = subprocess.run(
                [ffmpeg_cmd(), "-version"],
                capture_output=True,
                text=True,
                timeout=8,
                creationflags=0x08000000 if os.name == "nt" else 0,
            )
            out = (r.stdout or "") + (r.stderr or "")
            # Example: "ffmpeg version 6.1.1-..."
            import re
            m = re.search(r"ffmpeg version\s+([0-9]+(?:\.[0-9]+){0,2})", out, re.IGNORECASE)
            return m.group(1) if m else ""
        except Exception:
            return ""

    @staticmethod
    def _version_tuple(v: str) -> tuple:
        import re
        nums = [int(x) for x in re.findall(r"\d+", v or "")]
        return tuple(nums[:3] + [0] * max(0, 3 - len(nums)))

    @classmethod
    def _get_remote_ffmpeg_version(cls) -> str:
        try:
            req = urllib.request.Request(cls.ffmpeg_remote_version_url, headers={"User-Agent": "HEATMAP5-RuntimeManager/1.0"})
            with urllib.request.urlopen(req, timeout=15) as r:
                txt = (r.read() or b"").decode("utf-8", errors="ignore").strip()
            # Typically returns like "2024-xx-xx-git-..." or "6.1"
            # Prefer first numeric version seen.
            import re
            m = re.search(r"([0-9]+(?:\.[0-9]+){0,2})", txt)
            return m.group(1) if m else txt
        except Exception:
            return ""

    @classmethod
    def _extract_ffmpeg_binaries_from_zip(cls, zip_path: Path, *, progress_callback=None) -> None:
        cls._emit(progress_callback, stage="extracting", pct=0, message="Extracting FFmpeg...")
        with zipfile.ZipFile(zip_path, "r") as z:
            names = z.namelist()
            ffmpeg_member = next((n for n in names if n.lower().endswith("/bin/ffmpeg.exe") or n.lower().endswith("\\bin\\ffmpeg.exe")), None)
            ffprobe_member = next((n for n in names if n.lower().endswith("/bin/ffprobe.exe") or n.lower().endswith("\\bin\\ffprobe.exe")), None)
            if not ffmpeg_member or not ffprobe_member:
                # Some zips contain ffmpeg.exe directly under bin/
                ffmpeg_member = ffmpeg_member or next((n for n in names if n.lower().endswith("ffmpeg.exe")), None)
                ffprobe_member = ffprobe_member or next((n for n in names if n.lower().endswith("ffprobe.exe")), None)
            if not ffmpeg_member or not ffprobe_member:
                raise RuntimeError("FFmpeg zip invalid: missing ffmpeg.exe/ffprobe.exe")

            cls.bin_dir.mkdir(parents=True, exist_ok=True)
            z.extract(ffmpeg_member, path=cls.temp_dir)
            z.extract(ffprobe_member, path=cls.temp_dir)

            src_ffmpeg = cls.temp_dir / ffmpeg_member
            src_ffprobe = cls.temp_dir / ffprobe_member
            if not src_ffmpeg.exists() or not src_ffprobe.exists():
                raise RuntimeError("FFmpeg zip extract failed")

            # Move into runtime/bin (replace)
            dst_ffmpeg = cls.ffmpeg_path
            dst_ffprobe = cls.ffprobe_path
            dst_ffmpeg.parent.mkdir(parents=True, exist_ok=True)
            try:
                src_ffmpeg.replace(dst_ffmpeg)
            except Exception:
                dst_ffmpeg.write_bytes(src_ffmpeg.read_bytes())
            try:
                src_ffprobe.replace(dst_ffprobe)
            except Exception:
                dst_ffprobe.write_bytes(src_ffprobe.read_bytes())

        cls._emit(progress_callback, stage="extracting", pct=100, message="FFmpeg extracted")

    @classmethod
    def ensure_ffmpeg_installed(cls, *, progress_callback=None, allow_update: bool = True, force_update_check: bool = False) -> dict:
        """
        Ensure FFmpeg binaries exist. If missing -> auto-download/install.
        If allow_update -> check remote version every 24h and update if newer.
        Returns manifest after changes.
        """
        cls.initialize()
        manifest = cls.load_manifest()

        # Install if missing
        if not cls.ffmpeg_path.exists() or not cls.ffprobe_path.exists():
            cls._emit(progress_callback, stage="ffmpeg", pct=0, message="FFmpeg missing. Installing...")
            zip_name = "ffmpeg-release-essentials.zip"
            zip_path = cls.downloads_dir / zip_name
            cls._download_file(cls.ffmpeg_zip_url, zip_path, progress_callback=progress_callback)
            cls._extract_ffmpeg_binaries_from_zip(zip_path, progress_callback=progress_callback)
            ver = cls._detect_local_ffmpeg_version()
            manifest = cls.save_manifest({"ffmpeg_version": ver})
            cls._emit(progress_callback, stage="ffmpeg", pct=100, message=f"FFmpeg installed ({ver or 'unknown'})")

        # Update check schedule
        now = int(time.time())
        last = int(manifest.get("last_update_check_ts") or 0)
        due = force_update_check or (now - last >= cls.update_interval_sec)
        if allow_update and due:
            cls._emit(progress_callback, stage="update_check", pct=0, message="Checking FFmpeg updates...")
            local_v = manifest.get("ffmpeg_version") or cls._detect_local_ffmpeg_version()
            remote_v = cls._get_remote_ffmpeg_version()
            manifest = cls.save_manifest({"last_update_check_ts": now, "ffmpeg_version": local_v})

            if remote_v and local_v and cls._version_tuple(remote_v) > cls._version_tuple(local_v):
                cls._emit(progress_callback, stage="ffmpeg_update", pct=0, message=f"Updating FFmpeg {local_v} -> {remote_v}")
                zip_name = "ffmpeg-release-essentials.zip"
                zip_path = cls.downloads_dir / zip_name
                cls._download_file(cls.ffmpeg_zip_url, zip_path, progress_callback=progress_callback)
                cls._extract_ffmpeg_binaries_from_zip(zip_path, progress_callback=progress_callback)
                new_v = cls._detect_local_ffmpeg_version() or remote_v
                manifest = cls.save_manifest({"ffmpeg_version": new_v})
                cls._emit(progress_callback, stage="ffmpeg_update", pct=100, message=f"FFmpeg updated ({new_v})")
            else:
                cls._emit(progress_callback, stage="update_check", pct=100, message="FFmpeg up to date")

        return manifest

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
        cls._emit(None, stage="whisper", pct=0, message=f"Downloading Whisper model: {model_name}")
        _ = whisper.load_model(model_name, device="cpu", download_root=root)
        # Update manifest
        man = cls.load_manifest()
        models = set([str(x) for x in (man.get("whisper_models") or []) if str(x).strip()])
        models.add(model_name)
        cls.save_manifest({"whisper_models": sorted(models)})
        return cls.is_model_installed(model_name)

    @classmethod
    def ensure_whisper_model(cls, model_name: str, *, progress_callback=None) -> bool:
        """Ensure selected whisper model exists locally; download if missing and update manifest."""
        cls.initialize()
        if model_name not in WHISPER_MODEL_OPTIONS:
            raise ValueError(f"Unknown whisper model: {model_name}")
        if cls.is_model_installed(model_name):
            return True
        cls._emit(progress_callback, stage="whisper", pct=0, message=f"Downloading Whisper model: {model_name}")
        ok = cls.download_model(model_name)
        cls._emit(progress_callback, stage="whisper", pct=100, message=f"Whisper model ready: {model_name}")
        return ok

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
    def detect_gpu_vendor(cls) -> Optional[str]:
        """
        Best-effort GPU vendor detection.
        Returns 'nvidia' | 'amd' | None
        """
        # Prefer torch CUDA -> NVIDIA
        try:
            if torch is not None and bool(torch.cuda.is_available()):
                return "nvidia"
        except Exception:
            pass

        # Windows: query video controller names
        if os.name == "nt":
            try:
                r = subprocess.run(
                    ["wmic", "path", "win32_VideoController", "get", "name"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                    creationflags=0x08000000,
                )
                out = (r.stdout or "") + (r.stderr or "")
                lo = out.lower()
                if "nvidia" in lo:
                    return "nvidia"
                if "amd" in lo or "radeon" in lo:
                    return "amd"
            except Exception:
                pass
        return None

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
        cls.save_manifest({"cuda_installed": cls.is_cuda_installed()})

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
        cls.save_manifest({"amd_installed": cls.is_amd_runtime_installed()})

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

    @classmethod
    def cleanup_downloads(cls, *, older_than_hours: float = 24.0) -> Dict[str, Any]:
        """Deletes files in runtime/downloads older than threshold."""
        cls.initialize()
        cutoff = time.time() - (older_than_hours * 3600.0)
        deleted = 0
        kept = 0
        errors: List[str] = []
        try:
            for p in cls.downloads_dir.glob("**/*"):
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
        return {"deleted": deleted, "kept": kept, "errors": errors}

    # ---------------------------
    # Periodic auto update check
    # ---------------------------
    @classmethod
    def auto_update_tick(cls, *, progress_callback=None) -> dict:
        """
        Call this periodically (e.g. app start) to perform scheduled update checks.
        Current scope:
          - FFmpeg update check (24h)
        """
        return cls.ensure_ffmpeg_installed(progress_callback=progress_callback, allow_update=True, force_update_check=False)

    # ---------------------------
    # First run experience
    # ---------------------------
    @classmethod
    def first_run_setup(cls, *, selected_whisper_model: str = "small", progress_callback=None) -> Dict[str, Any]:
        """
        One-shot setup:
          - create dirs
          - install/update FFmpeg
          - ensure whisper model
          - detect hardware
          - recommend processing config
          - cleanup temp/downloads
        Returns RuntimeManager.get_status() after setup.
        """
        cls._emit(progress_callback, stage="init", pct=0, message="Initializing runtime...")
        cls.initialize()
        cls._emit(progress_callback, stage="init", pct=10, message="Ensuring FFmpeg...")
        cls.ensure_ffmpeg_installed(progress_callback=progress_callback, allow_update=True, force_update_check=True)
        cls._emit(progress_callback, stage="init", pct=60, message="Ensuring Whisper model...")
        cls.ensure_whisper_model(selected_whisper_model, progress_callback=progress_callback)
        cls._emit(progress_callback, stage="init", pct=80, message="Cleaning up old temp/downloads...")
        cls.cleanup_temp(older_than_hours=24.0)
        cls.cleanup_downloads(older_than_hours=24.0)
        cls._emit(progress_callback, stage="init", pct=100, message="Runtime ready")
        return cls.get_status()

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


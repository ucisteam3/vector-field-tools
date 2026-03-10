from __future__ import annotations

"""
Frame Analysis Cache System

Stores expensive analysis results (faces/motion/segments/metadata) per video hash:
  runtime/cache/<video_hash>/
    metadata.json
    faces.json
    motion.json
    segments.json

This module is additive. Callers can:
  - generate_video_hash(video_path)
  - cache = FrameAnalysisCache(video_path)
  - cache.load_partial(...) / cache.save_partial(...)
  - cache.cleanup(max_videos=20)
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
import hashlib
import json
import os
import time

from modules.runtime_paths import RUNTIME_DIR


def generate_video_hash(video_path: str) -> str:
    """
    Stable SHA1 based on:
      - absolute normalized path
      - file size
      - modified time (ns resolution when available)
    """
    p = Path(video_path)
    try:
        ap = str(p.resolve())
    except Exception:
        ap = str(p.absolute())
    ap = os.path.normcase(ap)

    try:
        st = p.stat()
        size = int(st.st_size)
        mtime = int(getattr(st, "st_mtime_ns", int(st.st_mtime * 1e9)))
    except Exception:
        size = 0
        mtime = 0

    raw = f"{ap}|{size}|{mtime}".encode("utf-8", errors="ignore")
    return hashlib.sha1(raw).hexdigest()


@dataclass
class CachePaths:
    root: Path
    metadata: Path
    faces: Path
    motion: Path
    segments: Path


class FrameAnalysisCache:
    def __init__(self, video_path: str):
        self.video_path = str(video_path)
        self.video_hash = generate_video_hash(self.video_path)
        self.cache_root = Path(RUNTIME_DIR) / "cache" / self.video_hash
        self.paths = CachePaths(
            root=self.cache_root,
            metadata=self.cache_root / "metadata.json",
            faces=self.cache_root / "faces.json",
            motion=self.cache_root / "motion.json",
            segments=self.cache_root / "segments.json",
        )

    # ---------------------------
    # Core filesystem helpers
    # ---------------------------
    def ensure_dir(self) -> None:
        self.paths.root.mkdir(parents=True, exist_ok=True)

    def exists(self) -> bool:
        return self.paths.root.exists()

    def _read_json(self, path: Path) -> Optional[Any]:
        try:
            if not path.exists():
                return None
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return None

    def _write_json(self, path: Path, obj: Any) -> None:
        self.ensure_dir()
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
        tmp.replace(path)

    # ---------------------------
    # Cache validation
    # ---------------------------
    def is_valid_for_video(self) -> bool:
        """
        Valid if metadata.json exists and matches current hash inputs.
        Since the cache folder name already includes the hash, this mainly
        guards against manual moves/copies.
        """
        md = self._read_json(self.paths.metadata)
        if not isinstance(md, dict):
            return False
        return str(md.get("video_hash") or "") == self.video_hash

    # ---------------------------
    # Load / Save (partial)
    # ---------------------------
    def load_partial(
        self,
        *,
        metadata: bool = True,
        faces: bool = True,
        motion: bool = True,
        segments: bool = True,
    ) -> Dict[str, Any]:
        """
        Partial cache loading.
        Returns dict with keys present only when file exists + parses successfully.
        """
        out: Dict[str, Any] = {}
        if metadata:
            v = self._read_json(self.paths.metadata)
            if v is not None:
                out["metadata"] = v
        if faces:
            v = self._read_json(self.paths.faces)
            if v is not None:
                out["faces"] = v
        if motion:
            v = self._read_json(self.paths.motion)
            if v is not None:
                out["motion"] = v
        if segments:
            v = self._read_json(self.paths.segments)
            if v is not None:
                out["segments"] = v
        return out

    def save_metadata(self, *, duration: Optional[float] = None, fps: Optional[float] = None, extra: Optional[dict] = None) -> None:
        """
        Save metadata.json.
        """
        payload: Dict[str, Any] = {
            "video_path": self.video_path,
            "video_hash": self.video_hash,
            "saved_at": int(time.time()),
        }
        if duration is not None:
            payload["duration"] = float(duration)
        if fps is not None:
            payload["fps"] = float(fps)
        if extra and isinstance(extra, dict):
            payload.update(extra)
        self._write_json(self.paths.metadata, payload)

    def save_faces(self, faces_obj: Any) -> None:
        self._write_json(self.paths.faces, faces_obj)

    def save_motion(self, motion_obj: Any) -> None:
        self._write_json(self.paths.motion, motion_obj)

    def save_segments(self, segments_obj: Any) -> None:
        self._write_json(self.paths.segments, segments_obj)

    def has_faces(self) -> bool:
        return self.paths.faces.exists()

    def has_motion(self) -> bool:
        return self.paths.motion.exists()

    def has_segments(self) -> bool:
        return self.paths.segments.exists()

    # ---------------------------
    # High-level helpers
    # ---------------------------
    def check_cache(self) -> Tuple[bool, Dict[str, Any]]:
        """
        Returns (hit, data)
        - hit=True means metadata exists & valid.
        - data contains any available cached parts (partial allowed).
        """
        if not self.exists():
            return False, {}
        data = self.load_partial(metadata=True, faces=True, motion=True, segments=True)
        hit = self.is_valid_for_video()
        return hit, data

    # ---------------------------
    # Cleanup
    # ---------------------------
    @staticmethod
    def cleanup(*, max_videos: int = 20) -> Dict[str, Any]:
        """
        Limit cache to maximum N video entries by deleting oldest directories.
        Oldest = directory mtime (fallback: metadata saved_at).
        """
        root = Path(RUNTIME_DIR) / "cache"
        root.mkdir(parents=True, exist_ok=True)

        entries = [p for p in root.iterdir() if p.is_dir()]
        if len(entries) <= max_videos:
            return {"deleted": 0, "kept": len(entries)}

        def entry_key(p: Path) -> float:
            try:
                md = p / "metadata.json"
                if md.exists():
                    j = json.loads(md.read_text(encoding="utf-8"))
                    if isinstance(j, dict) and j.get("saved_at"):
                        return float(j.get("saved_at"))
            except Exception:
                pass
            try:
                return float(p.stat().st_mtime)
            except Exception:
                return 0.0

        entries.sort(key=entry_key)
        to_delete = entries[: max(0, len(entries) - int(max_videos))]

        deleted = 0
        for d in to_delete:
            try:
                # rmtree without importing shutil at module import time
                for sub in sorted(d.glob("**/*"), reverse=True):
                    try:
                        if sub.is_file():
                            sub.unlink(missing_ok=True)
                        elif sub.is_dir():
                            sub.rmdir()
                    except Exception:
                        pass
                try:
                    d.rmdir()
                except Exception:
                    pass
                deleted += 1
            except Exception:
                pass

        kept = max(0, len(entries) - deleted)
        return {"deleted": deleted, "kept": kept}


"""
FFmpeg runner — execute FFmpeg with logging and error capture.
Also provides get_video_info, gpu_available, ffmpeg_has_filters for pipeline use.
"""

import os
import re
import subprocess
import sys
from typing import Tuple

from modules.runtime_paths import ffmpeg_cmd, ffprobe_cmd


def get_video_info(path: str) -> Tuple[int, int, float]:
    """Get video width, height, fps via ffprobe. Returns (w, h, fps)."""
    try:
        r = subprocess.run(
            [ffprobe_cmd(), "-v", "error", "-select_streams", "v:0",
             "-show_entries", "stream=width,height,r_frame_rate", "-of", "csv=p=0", path],
            capture_output=True, text=True, timeout=10,
            creationflags=0x08000000 if os.name == "nt" else 0,
        )
        if r.returncode == 0 and r.stdout:
            parts = r.stdout.strip().split(",")
            w, h = int(parts[0]), int(parts[1])
            fps = 30.0
            if len(parts) >= 3 and "/" in parts[2]:
                num, den = parts[2].split("/")
                if int(den) != 0:
                    fps = int(num) / int(den)
            return w, h, fps
    except Exception:
        pass
    return 1920, 1080, 30.0


def gpu_available() -> bool:
    """Detect GPU via ffmpeg -hwaccels."""
    try:
        r = subprocess.run(
            [ffmpeg_cmd(), "-hwaccels"],
            capture_output=True, text=True, timeout=5,
            creationflags=0x08000000 if os.name == "nt" else 0,
        )
        out = (r.stdout or "") + (r.stderr or "")
        return "cuda" in out.lower()
    except Exception:
        return False


_ffmpeg_filters_cache = None


def ffmpeg_has_filters(*names: str) -> dict:
    """Check which of the given filter names exist in this FFmpeg build."""
    global _ffmpeg_filters_cache
    if _ffmpeg_filters_cache is None:
        try:
            r = subprocess.run(
                [ffmpeg_cmd(), "-filters"],
                capture_output=True, text=True, timeout=10,
                creationflags=0x08000000 if os.name == "nt" else 0,
            )
            out = (r.stdout or "") + (r.stderr or "")
            _ffmpeg_filters_cache = out.lower()
        except Exception:
            _ffmpeg_filters_cache = ""
    out = _ffmpeg_filters_cache
    return {n: bool(re.search(r"\b" + re.escape(n.lower()) + r"\b", out)) for n in names}


def run_ffmpeg(
    cmd: list,
    *,
    progress_callback=None,
    encode_duration: float = None,
) -> int:
    """
    Run FFmpeg command: print command, stream logs in real time, capture errors, return exit code.
    Uses subprocess.Popen for real-time output.
    """
    print("")
    print("FFMPEG FILTER GRAPH:")
    try:
        idx = cmd.index("-filter_complex")
        if idx + 1 < len(cmd):
            print(cmd[idx + 1])
    except ValueError:
        print("(none)")
    print("FFMPEG COMMAND:")
    print(" ".join(cmd))
    print("")

    time_pat = None
    if encode_duration and encode_duration > 0:
        import re
        time_pat = re.compile(r"time=(\d+):(\d+):(\d+)\.(\d+)")

    creationflags = 0x08000000 if os.name == "nt" else 0
    startupinfo = None
    if sys.platform == "win32":
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            encoding="utf-8",
            errors="replace",
            creationflags=creationflags,
            startupinfo=startupinfo,
        )
    except Exception as e:
        print(f"  [EXEC ERROR] Failed to run ffmpeg: {e}")
        return -1

    err_lines = []
    for line in process.stdout:
        line = line.strip()
        if not line:
            continue
        if "Error" in line or "error" in line or "Cannot" in line or "nvenc" in line.lower():
            err_lines.append(line[:300])
        if encode_duration and encode_duration > 0 and time_pat and "time=" in line:
            m = time_pat.search(line)
            if m and progress_callback and callable(progress_callback):
                h, mn, s, ms = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
                elapsed = h * 3600 + mn * 60 + s + ms / 1000.0
                pct = 50 + int(48 * min(1.0, elapsed / encode_duration))
                try:
                    progress_callback(pct, f"Mengode video... {int(elapsed)}s")
                except Exception:
                    pass
        if any(k in line for k in ["frame=", "time=", "size=", "speed="]):
            print(f"    [FFMPEG] {line}", end="\r")
        elif "Error" in line or "error" in line:
            print(f"    [FFMPEG ERROR] {line}")

    process.wait()
    print("")
    if process.returncode != 0 and err_lines:
        print(f"  [FFMPEG FAIL] Exit {process.returncode}, last errors:")
        for e in err_lines[-5:]:
            print(f"    {e}")
    return process.returncode

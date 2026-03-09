"""
FFmpeg runner — execute FFmpeg with logging and error capture.
"""

import os
import subprocess
import sys


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
    print("FFMPEG FILTER GRAPH:")
    # Filter graph is the arg after -filter_complex
    try:
        idx = cmd.index("-filter_complex")
        if idx + 1 < len(cmd):
            print(cmd[idx + 1])
    except ValueError:
        pass
    print("FFMPEG COMMAND:")
    print(" ".join(cmd))

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

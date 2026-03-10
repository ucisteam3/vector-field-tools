#!/usr/bin/env python3
"""
Standalone YouTube download diagnostic script.
Does NOT import or modify modules/download_manager or other app code.

Usage:
  python test_youtube_download.py <youtube_url>
  python test_youtube_download.py <youtube_url> --cookies path/to/cookies.txt

1) Lists available formats first (detect SABR / storyboard-only).
2) Tries authenticated download strategies (cookies-from-browser chrome).
   Close Chrome before running or cookie copy will fail.
"""

import subprocess
import sys
from pathlib import Path

# Output folder for test downloads (under project root if run from HEATMAP5)
OUTPUT_DIR = Path(__file__).resolve().parent / "test_youtube_download_output"
OUT_TEMPLATE = str(OUTPUT_DIR / "%(title)s.%(ext)s")


def ytdlp_cmd(*args):
    """Single yt-dlp invocation prefix: python -m yt_dlp (works without yt-dlp on PATH)."""
    return [sys.executable, "-m", "yt_dlp", "--no-warnings", *args]


def run_and_print(cmd, timeout=120):
    """Run subprocess and print full stdout+stderr combined."""
    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            creationflags=0x08000000 if sys.platform == "win32" else 0,
        )
        out = result.stdout or ""
        if out.strip():
            print(out)
        else:
            print("(no output)")
        return result.returncode
    except subprocess.TimeoutExpired:
        print("Timeout.")
        return -1
    except Exception as e:
        print(f"Error: {e}")
        return -1


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    url = args[0] if args else None
    cookie_file = None
    if "--cookies" in sys.argv:
        i = sys.argv.index("--cookies")
        if i + 1 < len(sys.argv):
            cookie_file = sys.argv[i + 1]

    if not url:
        print("Usage: python test_youtube_download.py <youtube_url> [--cookies path/to.txt]")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n========== YouTube Download Test ==========")
    print(f"URL: {url}")
    print(f"Output dir: {OUTPUT_DIR}")
    if cookie_file:
        print(f"Cookie file (optional -F only): {cookie_file}")
    print()

    # ------ STEP 1 — CHECK AVAILABLE FORMATS ------
    print("\n====== STEP 1 — CHECK AVAILABLE FORMATS ======\n")
    print("--- yt-dlp -F (no auth) ---")
    run_and_print(ytdlp_cmd("-F", url), timeout=90)

    if cookie_file and Path(cookie_file).exists():
        print("\n--- yt-dlp -F (with --cookies file) ---")
        run_and_print(
            ytdlp_cmd("--cookies", str(Path(cookie_file).resolve()), "-F", url),
            timeout=90,
        )

    # ------ STEP 2 — DOWNLOAD STRATEGIES ------
    print("\nIMPORTANT: Close Chrome before running cookies-from-browser.\n")

    strategies = [
        {
            "name": "Cookies From Browser",
            "cmd": ytdlp_cmd(
                "--cookies-from-browser", "chrome",
                "-o", OUT_TEMPLATE,
                "-f", "best",
                url,
            ),
        },
        {
            "name": "Force Best Video+Audio",
            "cmd": ytdlp_cmd(
                "--cookies-from-browser", "chrome",
                "-o", OUT_TEMPLATE,
                "-f", "bv*+ba/best",
                url,
            ),
        },
        {
            "name": "Android Client",
            "cmd": ytdlp_cmd(
                "--cookies-from-browser", "chrome",
                "--extractor-args", "youtube:player_client=android",
                "-o", OUT_TEMPLATE,
                "-f", "best",
                url,
            ),
        },
        {
            "name": "TV Client",
            "cmd": ytdlp_cmd(
                "--cookies-from-browser", "chrome",
                "--extractor-args", "youtube:player_client=tv",
                "-o", OUT_TEMPLATE,
                "-f", "best",
                url,
            ),
        },
        {
            "name": "iOS Client",
            "cmd": ytdlp_cmd(
                "--cookies-from-browser", "chrome",
                "--extractor-args", "youtube:player_client=ios",
                "-o", OUT_TEMPLATE,
                "-f", "best",
                url,
            ),
        },
    ]

    for strat in strategies:
        print(f"\n------ Trying Strategy: {strat['name']} ------\n")
        code = run_and_print(strat["cmd"], timeout=600)
        if code == 0:
            print(f"\nSUCCESS with strategy: {strat['name']}")
            print(f"Check folder: {OUTPUT_DIR}")
            break
        print(f"(exit code {code})\n")

    print("\n========== Test Complete ==========")
    print("If all failed: age restriction / SABR / cookie DB locked / client restriction.\n")


if __name__ == "__main__":
    main()

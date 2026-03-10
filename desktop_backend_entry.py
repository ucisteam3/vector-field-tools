#!/usr/bin/env python3
"""
Desktop backend entrypoint for packaging (PyInstaller).

Goal: run backend with a stable PROJECT ROOT in packaged builds.
This does not change backend logic; it only sets working directory and sys.path.
"""

import os
import sys


def _project_root() -> str:
    # In PyInstaller builds, sys.executable is inside the app folder.
    if getattr(sys, "frozen", False):
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


ROOT = _project_root()
os.chdir(ROOT)
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import uvicorn  # noqa: E402
from backend.server import app  # noqa: E402


if __name__ == "__main__":
    port = 8001
    print(f"Starting AI Video Clipper API at http://localhost:{port}")
    uvicorn.run(app, host="127.0.0.1", port=port)


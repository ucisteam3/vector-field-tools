#!/usr/bin/env python3
"""
AI Video Clipper - Web entrypoint.
Desktop (Tkinter) UI has been removed. Use the web app instead.

Run:  python main.py   OR   python server.py
Then open: http://localhost:3000 (start frontend with: cd frontend && npm run dev)
API runs at: http://localhost:8000
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
sys.path.insert(0, str(ROOT))

# Delegate to server
import uvicorn
sys.path.insert(0, str(ROOT))
from backend.server import app

if __name__ == "__main__":
    print("AI Video Clipper - Web API at http://localhost:8000")
    print("Start frontend: cd frontend && npm run dev  then open http://localhost:3000")
    uvicorn.run(app, host="0.0.0.0", port=8000)

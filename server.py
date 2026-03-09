#!/usr/bin/env python3
"""
Unified server entry point. Run from project root:
  python server.py

Starts FastAPI backend on port 8000.
Frontend: cd frontend && npm run dev (port 3000)
Then open: http://localhost:3000
"""

import os
import sys

# Ensure we run from project root
ROOT = os.path.dirname(os.path.abspath(__file__))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

import uvicorn
from backend.server import app

if __name__ == "__main__":
    # Single-port backend to avoid confusion
    port = 8001
    print(f"Starting AI Video Clipper API at http://localhost:{port}")
    print("Frontend: cd frontend && npm run dev  (then open http://localhost:3000)")
    uvicorn.run(app, host="0.0.0.0", port=port)

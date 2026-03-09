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

import socket
import uvicorn
from backend.server import app

def _port_free(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("0.0.0.0", port))
            return True
    except OSError:
        return False

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 0)) or None
    if port is None or port == 0:
        for p in [8001, 8002, 8003]:
            if _port_free(p):
                port = p
                break
        else:
            port = 8001  # uvicorn will show the real error
    print(f"Starting AI Video Clipper API at http://localhost:{port}")
    print("Frontend: cd frontend && npm run dev  (then open http://localhost:3000)")
    if port != 8001:
        print(f"  (Port 8001 was in use; using {port}. Set NEXT_PUBLIC_API_PORT={port} if frontend cannot connect.)")
    uvicorn.run(app, host="0.0.0.0", port=port)

"""
FastAPI server for local AI video clipping web app.
Run: python server.py
Then open: http://localhost:3000 (frontend) and proxy API to http://localhost:8000
"""

import os
import sys
from pathlib import Path

# Windows encoding fix: wrap stdout/stderr to replace problematic Unicode before write
# Catches AI responses, tracebacks, and any print() with arrows/emoji
_REPLACE = (
    ("\u2192", "->"),
    ("\u27a1", "->"),
    ("\u2713", "OK"),
    ("\u2714", "OK"),
    ("\u2717", "X"),
    ("\u26a0", "!"),
)


def _safe_encode(s: str) -> str:
    for old, new in _REPLACE:
        s = s.replace(old, new)
    return s


class _SafeStream:
    def __init__(self, stream):
        self._stream = stream

    def write(self, s):
        if isinstance(s, str):
            s = _safe_encode(s)
        self._stream.write(s)

    def flush(self):
        self._stream.flush()

    def __getattr__(self, k):
        return getattr(self._stream, k)


# Apply UTF-8 reconfigure first, then wrap to catch any remaining bad chars
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        if sys.stderr is not sys.stdout and hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8")
    except (OSError, AttributeError):
        pass

# Wrap streams so ANY output with \u2192 etc gets sanitized (fallback for cp1252)
try:
    sys.stdout = _SafeStream(sys.stdout)
    if sys.stderr is not sys.stdout:
        sys.stderr = _SafeStream(sys.stderr)
except Exception:
    pass

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

# Mock tkinter.messagebox for headless operation (before any module imports it)
import tkinter
try:
    _tk_mb = getattr(tkinter, "messagebox", None)
    if _tk_mb:
        _tk_mb.showerror = lambda *a, **k: None
        _tk_mb.showinfo = lambda *a, **k: None
        _tk_mb.showwarning = lambda *a, **k: None
        _tk_mb.askyesno = lambda *a, **k: True
except Exception:
    pass

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional, Any

from backend.project_manager import (
    create_project,
    get_project,
    list_projects,
    update_project,
    delete_project,
    get_project_dir,
    get_clip_path,
    get_video_path,
    PROJECTS_DIR,
)
from backend.analysis_service import run_analysis, get_analysis_status, _safe_str
from backend.clip_service import export_clip, export_all_clips

app = FastAPI(title="AI Video Clipper", version="1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Request/Response Models ---

class AnalyzeRequest(BaseModel):
    youtube_url: str


class ExportClipRequest(BaseModel):
    project_id: str
    clip_id: int  # 0-based clip index
    settings: Optional[dict[str, Any]] = None


# --- API Endpoints ---

@app.post("/analyze")
def analyze(req: AnalyzeRequest):
    """Start analysis for a YouTube URL. Returns project_id immediately."""
    url = req.youtube_url.strip()
    # Fetch title first for instant display
    title = "Processing..."
    try:
        import subprocess
        import json as _json
        r = subprocess.run(
            [sys.executable, "-m", "yt_dlp", "--dump-json", "--no-download", "--no-warnings", url],
            capture_output=True, text=True, timeout=20,
            creationflags=0x08000000 if os.name == "nt" else 0,
        )
        if r.returncode == 0 and r.stdout.strip():
            data = _json.loads(r.stdout.split("\n")[0])
            title = data.get("title") or "Video"
    except Exception:
        pass
    meta = create_project(title=title, youtube_url=url)
    project_id = meta["project_id"]
    update_project(project_id, status="analyzing")
    run_analysis(project_id, url)
    return {"project_id": project_id, "title": title}


def _sanitize_project(meta: dict) -> dict:
    """Ensure error/title/clips are safe for Windows encoding (no Unicode arrows etc)."""
    out = dict(meta)
    if out.get("error"):
        out["error"] = _safe_str(out["error"])
    if out.get("title"):
        out["title"] = _safe_str(out["title"])
    if out.get("clips"):
        out["clips"] = [
            {**c, "title": _safe_str(c.get("title", ""))}
            for c in out["clips"]
        ]
    return out


@app.get("/projects")
def projects_list():
    """List all projects."""
    return [_sanitize_project(p) for p in list_projects()]


@app.get("/project/{project_id}")
def project_detail(project_id: str):
    """Get project metadata and clips."""
    meta = get_project(project_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Project not found")
    return _sanitize_project(meta)


@app.get("/project/{project_id}/status")
def project_status(project_id: str):
    """Get analysis status (for polling during processing)."""
    st = get_analysis_status(project_id)
    if st.get("error"):
        st = dict(st)
        st["error"] = _safe_str(st["error"])
    return st


@app.post("/project/{project_id}/retry")
def project_retry(project_id: str):
    """Retry analysis for a failed project. Uses stored youtube_url."""
    meta = get_project(project_id)
    if not meta:
        raise HTTPException(status_code=404, detail="Project not found")
    url = meta.get("youtube_url")
    if not url:
        raise HTTPException(status_code=400, detail="No YouTube URL for this project")
    update_project(project_id, status="analyzing", error=None)
    run_analysis(project_id, url)
    return {"ok": True}


@app.get("/video/{project_id}")
def serve_video(project_id: str):
    """Serve the source video file."""
    vp = get_video_path(project_id)
    if not vp or not vp.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    return FileResponse(vp, media_type="video/mp4")


@app.get("/clip/{project_id}/{clip_filename:path}")
def serve_clip(project_id: str, clip_filename: str):
    """Serve a clip video file."""
    cp = get_clip_path(project_id, clip_filename)
    if not cp or not cp.exists():
        raise HTTPException(status_code=404, detail="Clip not found")
    return FileResponse(cp, media_type="video/mp4")


@app.post("/project/{project_id}/export/{clip_index:int}")
def export_single_clip(project_id: str, clip_index: int):
    """Export a single clip with default settings (no subtitle/watermark)."""
    fn = export_clip(project_id, clip_index, None)
    if not fn:
        raise HTTPException(status_code=404, detail="Export failed")
    return {"clip_path": f"clips/{fn}"}


@app.post("/export_clip")
def export_clip_with_settings(req: ExportClipRequest):
    """Export a clip with full settings. project_id, clip_id (index), settings."""
    fn = export_clip(req.project_id, req.clip_id, req.settings)
    if not fn:
        raise HTTPException(status_code=404, detail="Export failed")
    return {"clip_path": f"clips/{fn}"}


# Upload directories
BGM_UPLOAD_DIR = PROJECT_ROOT / "temp" / "bgm_uploads"
WATERMARK_UPLOAD_DIR = PROJECT_ROOT / "temp" / "watermark_uploads"


@app.post("/upload_bgm")
async def upload_bgm(file: UploadFile = File(...)):
    """Upload BGM audio file. Returns path for use in export settings."""
    import uuid
    BGM_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "").suffix or ".mp3"
    if ext.lower() not in (".mp3", ".wav", ".m4a", ".aac", ".ogg"):
        ext = ".mp3"
    name = f"{uuid.uuid4().hex}{ext}"
    path = BGM_UPLOAD_DIR / name
    content = await file.read()
    path.write_bytes(content)
    # Return path relative to PROJECT_ROOT for settings
    rel = str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    return {"path": rel, "filename": name}


@app.post("/upload_watermark_image")
async def upload_watermark_image(file: UploadFile = File(...)):
    """Upload watermark image. Returns path for use in export settings."""
    import uuid
    WATERMARK_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "").suffix or ".png"
    if ext.lower() not in (".png", ".jpg", ".jpeg", ".webp", ".gif"):
        ext = ".png"
    name = f"{uuid.uuid4().hex}{ext}"
    path = WATERMARK_UPLOAD_DIR / name
    content = await file.read()
    path.write_bytes(content)
    rel = str(path.relative_to(PROJECT_ROOT)).replace("\\", "/")
    return {"path": rel, "filename": name}


COOKIE_FILE = PROJECT_ROOT / "www.youtube.com_cookies.txt"


@app.post("/upload_cookies")
async def upload_cookies_endpoint(file: UploadFile = File(...)):
    """Upload YouTube cookies file. Helps bypass age/region restrictions."""
    if not (file.filename or "").lower().endswith(".txt"):
        raise HTTPException(status_code=400, detail="Hanya file .txt")
    content = await file.read()
    COOKIE_FILE.parent.mkdir(parents=True, exist_ok=True)
    COOKIE_FILE.write_bytes(content)
    return {"ok": True, "path": str(COOKIE_FILE)}


@app.get("/cookies_status")
def cookies_status():
    """Check if YouTube cookies file exists."""
    exists = COOKIE_FILE.exists()
    size = COOKIE_FILE.stat().st_size if exists else 0
    return {"exists": exists, "size_kb": round(size / 1024, 1)}


@app.get("/fonts")
def list_fonts():
    """List available font names for subtitles and watermark."""
    try:
        from modules.font_manager import VIRAL_FONTS
        fonts = ["Arial"] + sorted(VIRAL_FONTS.keys())
        return fonts
    except Exception:
        return ["Arial", "Roboto-Bold", "Poppins-Bold", "Anton-Regular"]


@app.post("/project/{project_id}/export-all")
def export_all(project_id: str):
    """Export all clips for a project."""
    exported = export_all_clips(project_id)
    return {"exported": exported}


@app.delete("/project/{project_id}")
def delete_project_endpoint(project_id: str):
    """Delete a project."""
    if not delete_project(project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    return {"ok": True}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

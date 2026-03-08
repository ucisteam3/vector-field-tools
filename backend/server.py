"""
FastAPI server for local AI video clipping web app.
Run: python server.py  (or: run_web.bat)
Then open: http://localhost:3000 (frontend) and proxy API to http://localhost:8000
"""

import os
import sys
from pathlib import Path

# Windows encoding fix - MUST run before any other output (prevents \u2192 charmap errors)
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
try:
    from backend.encoding_fix import apply
    apply()
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


def _log_gpu_status():
    """Log GPU/CUDA availability and configure for ~90% utilization."""
    try:
        import torch
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0) if torch.cuda.device_count() else "NVIDIA GPU"
            torch.cuda.set_per_process_memory_fraction(0.9)
            if hasattr(torch.backends, "cudnn") and hasattr(torch.backends.cudnn, "benchmark"):
                torch.backends.cudnn.benchmark = True
            print(f"[GPU] CUDA: {name} - 90% VRAM, optimasi kecepatan aktif")
        else:
            print("[GPU] CUDA tidak terdeteksi - menggunakan CPU")
    except ImportError:
        print("[GPU] PyTorch tidak terinstall")
    except Exception as e:
        print(f"[GPU] Config: {e}")


_log_gpu_status()


@app.exception_handler(Exception)
def global_exception_handler(request, exc):
    """Log and return 500 for unhandled exceptions. Let HTTPException pass through."""
    if isinstance(exc, HTTPException):
        raise exc
    import traceback
    print(f"[SERVER] Unhandled exception: {exc}")
    traceback.print_exc()
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc), "type": type(exc).__name__},
    )


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
    export_settings: Optional[dict[str, Any]] = None


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
    if req.export_settings:
        update_project(project_id, export_settings=req.export_settings)
    update_project(project_id, status="analyzing")
    run_analysis(project_id, url)
    return {"project_id": project_id, "title": title}


def _sanitize_project(meta: dict) -> dict:
    """Ensure error/title/clips are safe for Windows encoding (no Unicode arrows etc)."""
    try:
        out = dict(meta)
        if out.get("error"):
            out["error"] = _safe_str(str(out["error"]))
        if out.get("title"):
            out["title"] = _safe_str(str(out["title"]))
        if out.get("clips"):
            out["clips"] = [
                {**c, "title": _safe_str(str(c.get("title", "")))}
                for c in out["clips"]
            ]
        return out
    except Exception as e:
        print(f"[SERVER] _sanitize_project error: {e}")
        return meta


@app.get("/gpu_status")
def gpu_status():
    """Check CUDA/GPU availability for debugging."""
    try:
        import torch
        cuda = torch.cuda.is_available()
        out = {
            "cuda_available": cuda,
            "device_name": torch.cuda.get_device_name(0) if cuda and torch.cuda.device_count() else None,
            "pytorch_version": torch.__version__,
        }
        return out
    except ImportError:
        return {"cuda_available": False, "device_name": None, "pytorch_version": None}


@app.get("/projects")
def projects_list():
    """List all projects."""
    try:
        projects = list_projects()
        return [_sanitize_project(p) for p in projects]
    except Exception as e:
        print(f"[SERVER] projects_list error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}")


@app.get("/project/{project_id}")
def project_detail(project_id: str):
    """Get project metadata and clips."""
    try:
        meta = get_project(project_id)
        if not meta:
            raise HTTPException(status_code=404, detail="Project not found")
        return _sanitize_project(meta)
    except HTTPException:
        raise
    except Exception as e:
        print(f"[SERVER] project_detail error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to load project: {str(e)}")


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


@app.get("/clip/{project_id}/extract/{clip_index:int}")
def extract_clip_segment(project_id: str, clip_index: int):
    """
    Extract clip segment from source video using ffmpeg.
    ffmpeg -ss start -to end -i video.mp4 -c copy clip.mp4
    Returns the generated clip file for download.
    """
    import subprocess
    meta = get_project(project_id)
    if not meta or not meta.get("clips"):
        raise HTTPException(status_code=404, detail="Project not found")
    clips = meta["clips"]
    if clip_index < 0 or clip_index >= len(clips):
        raise HTTPException(status_code=404, detail="Clip not found")
    vp = get_video_path(project_id)
    if not vp or not vp.exists():
        raise HTTPException(status_code=404, detail="Video not found")
    clip_info = clips[clip_index]
    start = float(clip_info.get("start", 0))
    end = float(clip_info.get("end", 0))
    if end <= start:
        raise HTTPException(status_code=400, detail="Invalid clip duration")
    title = (clip_info.get("title") or f"clip_{clip_index + 1}")[:80]
    safe_name = "".join(c for c in title if c.isalnum() or c in (" ", "-", "_")).strip() or f"clip_{clip_index + 1}"
    out_dir = PROJECTS_DIR / project_id / "clips"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{safe_name}_{clip_index}.mp4"
    try:
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(start),
            "-to", str(end),
            "-i", str(vp),
            "-c", "copy",
            "-avoid_negative_ts", "1",
            str(out_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, creationflags=0x08000000 if __import__("os").name == "nt" else 0)
        if result.returncode != 0 or not out_path.exists():
            raise HTTPException(status_code=500, detail="FFmpeg extraction failed")
        return FileResponse(out_path, media_type="video/mp4", filename=f"{safe_name}.mp4")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Extraction timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/clip/{project_id}/{clip_filename:path}")
def serve_clip(project_id: str, clip_filename: str):
    """Serve a clip video file (exported clip by filename)."""
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
    try:
        fn = export_clip(req.project_id, req.clip_id, req.settings)
        if not fn:
            raise HTTPException(status_code=404, detail="Export failed")
        return {"clip_path": f"clips/{fn}"}
    except HTTPException:
        raise
    except Exception as e:
        print(f"[SERVER] export_clip error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Export failed: {str(e)}")


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

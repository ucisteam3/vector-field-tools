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
    """Log GPU/CUDA and FFmpeg NVENC/NVDEC availability."""
    try:
        import torch
        import subprocess
        if torch.cuda.is_available():
            name = torch.cuda.get_device_name(0) if torch.cuda.device_count() else "NVIDIA GPU"
            torch.cuda.set_per_process_memory_fraction(0.9)
            if hasattr(torch.backends, "cudnn") and hasattr(torch.backends.cudnn, "benchmark"):
                torch.backends.cudnn.benchmark = True
            print(f"[GPU] CUDA: {name} - 90% VRAM, optimasi kecepatan aktif")
        else:
            print("[GPU] CUDA tidak terdeteksi - menggunakan CPU")
        # Detect GPU via ffmpeg -hwaccels (NVDEC)
        hwaccel_cuda = False
        try:
            h = subprocess.run(["ffmpeg", "-hwaccels"], capture_output=True, text=True, timeout=5,
                               creationflags=0x08000000 if __import__("os").name == "nt" else 0)
            hwaccel_cuda = "cuda" in ((h.stdout or "") + (h.stderr or "")).lower()
            print(f"[GPU] FFmpeg NVDEC (hwaccel cuda): {'OK' if hwaccel_cuda else 'Tidak'}")
        except Exception as e:
            print(f"[GPU] FFmpeg -hwaccels: {e}")
        # Cek FFmpeg NVENC + test encode
        try:
            r = subprocess.run(["ffmpeg", "-encoders"], capture_output=True, text=True, timeout=5,
                               creationflags=0x08000000 if __import__("os").name == "nt" else 0)
            nvenc_ok = "h264_nvenc" in (r.stdout or "")
            if nvenc_ok:
                # Quick test: 1 frame encode
                t = subprocess.run(
                    ["ffmpeg", "-y", "-f", "lavfi", "-i", "testsrc=duration=0.1:size=1280x720:rate=1",
                     "-c:v", "h264_nvenc", "-frames:v", "1", "-f", "null", "-"],
                    capture_output=True, text=True, timeout=10,
                    creationflags=0x08000000 if __import__("os").name == "nt" else 0)
                nvenc_ok = t.returncode == 0
                if not nvenc_ok:
                    print(f"[GPU] FFmpeg NVENC: encoder ada tapi test gagal - {t.stderr[-150:] if t.stderr else 'unknown'}")
            print(f"[GPU] FFmpeg NVENC: {'OK' if nvenc_ok else 'Tidak bisa dipakai - gunakan CPU'}")
        except Exception as ex:
            print(f"[GPU] FFmpeg NVENC: {ex}")
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


# Export job progress store (job_id -> status)
_export_jobs: dict[str, dict] = {}
import threading
import uuid
_export_lock = threading.Lock()


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


@app.get("/clip/{project_id}/thumbnail/{clip_index:int}")
def clip_thumbnail(project_id: str, clip_index: int):
    """
    Extract a single frame from the clip as thumbnail (9:16 crop).
    Frame taken ~1s into clip or 15% of duration.
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
    duration = end - start
    if duration <= 0:
        raise HTTPException(status_code=400, detail="Invalid clip duration")
    # Frame at 1s in or 15% of duration
    seek = start + min(1.0, duration * 0.15)
    out_dir = PROJECTS_DIR / project_id / "clips"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"_thumb_{clip_index}_{int(start)}_{int(end)}.jpg"
    if out_path.exists():
        return FileResponse(out_path, media_type="image/jpeg")
    try:
        cmd = [
            "ffmpeg", "-y",
            "-ss", str(seek),
            "-i", str(vp),
            "-vf", "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=540:960",
            "-vframes", "1",
            str(out_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, creationflags=0x08000000 if __import__("os").name == "nt" else 0)
        if result.returncode != 0 or not out_path.exists():
            raise HTTPException(status_code=500, detail="Thumbnail failed")
        return FileResponse(out_path, media_type="image/jpeg")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Thumbnail timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/clip/{project_id}/preview/{clip_index:int}")
def preview_clip_segment(project_id: str, clip_index: int):
    """
    Quick preview: extract segment with 9:16 center crop. No effects (zoom, subtitle, etc).
    For Play button - fast, vertical aspect.
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
    out_dir = PROJECTS_DIR / project_id / "clips"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"_preview_{clip_index}.mp4"
    try:
        duration = end - start
        # -ss after -i for A/V sync
        cmd = [
            "ffmpeg", "-y",
            "-i", str(vp),
            "-ss", str(start),
            "-t", str(duration),
            "-vf", "crop=ih*9/16:ih:(iw-ih*9/16)/2:0,scale=1080:1920",
            "-c:a", "aac",
            "-avoid_negative_ts", "1",
            str(out_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, creationflags=0x08000000 if __import__("os").name == "nt" else 0)
        if result.returncode != 0 or not out_path.exists():
            raise HTTPException(status_code=500, detail="FFmpeg preview failed")
        return FileResponse(out_path, media_type="video/mp4", filename=f"preview_{clip_index}.mp4")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Preview timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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
    cache_path = out_dir / f"_extract_{clip_index}_{int(start)}_{int(end)}.mp4"
    if cache_path.exists():
        return FileResponse(cache_path, media_type="video/mp4", filename=f"{safe_name}.mp4")
    out_path = out_dir / f"{safe_name}_{clip_index}.mp4"
    try:
        duration = end - start
        cmd = [
            "ffmpeg", "-y",
            "-i", str(vp),
            "-ss", str(start),
            "-t", str(duration),
            "-c", "copy",
            "-avoid_negative_ts", "1",
            str(cache_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=120, creationflags=0x08000000 if __import__("os").name == "nt" else 0)
        if result.returncode != 0 or not cache_path.exists():
            raise HTTPException(status_code=500, detail="FFmpeg extraction failed")
        return FileResponse(cache_path, media_type="video/mp4", filename=f"{safe_name}.mp4")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Extraction timeout")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/clip/{project_id}/{clip_filename:path}")
def serve_clip(project_id: str, clip_filename: str, download: bool = False):
    """Serve a clip video file. inline=preview (no IDM), download=1 for attachment."""
    cp = get_clip_path(project_id, clip_filename)
    if not cp or not cp.exists():
        raise HTTPException(status_code=404, detail="Clip not found")
    disp = "attachment" if download else "inline"
    return FileResponse(cp, media_type="video/mp4", headers={"Content-Disposition": disp})


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
    last_error = None
    try:
        fn = export_clip(req.project_id, req.clip_id, req.settings)
        if fn:
            return {"clip_path": f"clips/{fn}"}
    except HTTPException:
        raise
    except Exception as e:
        last_error = str(e)
        print(f"[SERVER] export_clip error: {e}")
        import traceback
        traceback.print_exc()
    # Fallback: simple extract (-c copy) when full export fails
    # Use -ss before -i for speed (avoid timeout on long videos)
    try:
        meta = get_project(req.project_id)
        if not meta or not meta.get("clips"):
            raise HTTPException(status_code=404, detail="Project not found")
        clips = meta["clips"]
        if req.clip_id < 0 or req.clip_id >= len(clips):
            raise HTTPException(status_code=404, detail="Clip not found")
        clip_info = clips[req.clip_id]
        start = float(clip_info.get("start", 0))
        end = float(clip_info.get("end", 0))
        if end <= start:
            raise HTTPException(status_code=400, detail="Invalid clip duration")
        vp = get_video_path(req.project_id)
        if not vp or not vp.exists():
            raise HTTPException(status_code=404, detail="Video not found")
        title = (clip_info.get("title") or f"clip_{req.clip_id + 1}")[:80]
        safe_name = "".join(c for c in title if c.isalnum() or c in (" ", "-", "_")).strip() or f"clip_{req.clip_id + 1}"
        out_dir = PROJECTS_DIR / req.project_id / "clips"
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / f"{safe_name}.mp4"
        import subprocess
        duration = end - start
        # -ss after -i for A/V sync (before -i = keyframe seek, causes desync)
        cmd = ["ffmpeg", "-y", "-i", str(vp), "-ss", str(start), "-t", str(duration), "-c", "copy", "-avoid_negative_ts", "make_zero", str(out_path)]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=180, creationflags=0x08000000 if __import__("os").name == "nt" else 0)
        if result.returncode == 0 and out_path.exists():
            return {"clip_path": f"clips/{safe_name}.mp4"}
        err_msg = result.stderr[-500:] if result.stderr else "FFmpeg gagal"
        last_error = f"FFmpeg: {err_msg[:150]}"
        print(f"[SERVER] Fallback ffmpeg stderr: {err_msg}")
    except HTTPException:
        raise
    except Exception as fallback_err:
        last_error = str(fallback_err)
        print(f"[SERVER] Fallback extract failed: {fallback_err}")
        import traceback
        traceback.print_exc()
    detail = "Export gagal. Pastikan backend berjalan dan cek log."
    if last_error:
        detail = f"Export gagal: {last_error[:200]}"
    raise HTTPException(status_code=500, detail=detail)


def _run_export_job(job_id: str, project_id: str, clip_id: int, settings: Optional[dict]):
    """Background worker for async export with progress."""
    def on_progress(percent: int, message: str):
        with _export_lock:
            if job_id in _export_jobs:
                j = _export_jobs[job_id]
                j["progress"] = percent
                j["message"] = message
                logs = j.setdefault("logs", [])
                entry = f"[{percent}%] {message}"
                if not logs or logs[-1] != entry:
                    logs.append(entry)
                    if len(logs) > 30:
                        logs.pop(0)

    with _export_lock:
        _export_jobs[job_id] = {"progress": 0, "message": "Memulai...", "status": "running", "clip_path": None, "error": None, "logs": ["[0%] Memulai export..."]}

    try:
        fn = export_clip(project_id, clip_id, settings, progress_callback=on_progress)
        if fn:
            with _export_lock:
                _export_jobs[job_id].update(progress=100, message="Selesai", status="done", clip_path=f"clips/{fn}")
        else:
            with _export_lock:
                _export_jobs[job_id].update(status="error", error="Export gagal", progress=0)
    except Exception as e:
        with _export_lock:
            _export_jobs[job_id].update(status="error", error=str(e)[:200], progress=0)
        import traceback
        traceback.print_exc()


@app.post("/export_clip_async")
def export_clip_async(req: ExportClipRequest):
    """Start export in background. Returns job_id. Poll /export_clip_status?job_id=xxx for progress."""
    job_id = str(uuid.uuid4())[:8]
    t = threading.Thread(target=_run_export_job, args=(job_id, req.project_id, req.clip_id, req.settings))
    t.daemon = True
    t.start()
    return {"job_id": job_id}


@app.get("/export_clip_status")
def export_clip_status(job_id: str):
    """Get export progress. Returns {progress, message, status, clip_path?, error?}."""
    with _export_lock:
        job = _export_jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/job_status/{job_id}")
def job_status(job_id: str):
    """Alias for export progress. Returns same as GET /export_clip_status?job_id=."""
    return export_clip_status(job_id)


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

"""
Analysis Service - Runs video analysis pipeline in background using existing AI modules.
Headless workflow: Download -> Transcribe -> AI Segments -> Match -> Titles -> Save.
"""

import os
import re
import json
import shutil
import threading
from pathlib import Path
from datetime import timedelta

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys_path_added = False


def _ensure_sys_path():
    global sys_path_added
    if not sys_path_added:
        import sys
        sys.path.insert(0, str(PROJECT_ROOT))
        # CRITICAL: cwd ke project root (sama seperti desktop app python main.py)
        os.chdir(PROJECT_ROOT)
        sys_path_added = True


# In-memory progress and status per project
_analysis_status = {}
_analysis_lock = threading.Lock()

# Unicode chars that cause Windows charmap errors - replace with ASCII
_UNICODE_REPLACEMENTS = (
    ("\u2192", "->"),   # rightwards arrow
    ("\u2713", "OK"),   # check mark
    ("\u2714", "OK"),   # heavy check
    ("\u2717", "FAIL"), # cross
    ("\u26a0", "WARNING"),  # warning
    ("\u27a1", "->"),   # rightwards arrow (variant)
)


def _safe_str(s: str) -> str:
    """Replace Unicode chars that cause Windows charmap errors."""
    if not s or not isinstance(s, str):
        return s
    for old, new in _UNICODE_REPLACEMENTS:
        s = s.replace(old, new)
    return s


def _set_status(project_id: str, status: str, progress: str = None, error: str = None):
    with _analysis_lock:
        s = _analysis_status.get(project_id, {})
        s["status"] = status
        if progress is not None:
            s["progress"] = _safe_str(progress)
        if error is not None:
            s["error"] = _safe_str(error)
        _analysis_status[project_id] = s


def _compute_eta(progress: str) -> tuple[int, str]:
    """Compute ETA from real progress when possible. Conservative estimates otherwise."""
    import re
    if not progress:
        return (300, "~5 min")
    p = progress.lower()

    # 1) Rendering clips N/M — AKURAT: sisa (M-N) × ~100 detik/klip
    mr = re.search(r"rendering\s+clips\s+(\d+)\s*/\s*(\d+)", p, re.I)
    if mr:
        try:
            current, total = int(mr.group(1)), int(mr.group(2))
            if total > 0 and current < total:
                remaining_clips = total - current
                secs_per_clip = 100  # conservative: 1.5–2 min per clip
                secs = remaining_clips * secs_per_clip
                if secs >= 60:
                    return (secs, f"~{secs // 60} min")
                return (secs, f"~{secs} detik")
            return (60, "~1 min")
        except (ValueError, TypeError):
            pass

    # 2) Download percentage — AKURAT dari progress nyata
    m = re.search(r"downloading\.+[\s]*([\d.]+)\s*%", p, re.I)
    if m:
        try:
            pct = float(m.group(1))
            remaining_pct = max(0, (100 - pct) / 100)
            secs = int(remaining_pct * 300)
            if secs >= 120:
                return (secs, f"~{secs // 60} min")
            return (secs, f"~{secs} detik")
        except ValueError:
            pass

    # 3) Fase lain — estimasi konservatif (sedikit overestimate)
    estimates = {
        "copying": (45, "~45 detik"),
        "download complete": (120, "~2 min"),
        "preparing": (90, "~1.5 min"),
        "downloading subtitles": (45, "~45 detik"),
        "extracting transcript": (90, "~1.5 min"),
        "transcribing with ai": (180, "~3 min"),
        "detecting viral": (120, "~2 min"),
        "matching segments": (45, "~45 detik"),
        "generating titles": (90, "~1.5 min"),
        "rendering": (600, "~10 min"),  # fallback jika belum dapat N/M
        "starting": (300, "~5 min"),
    }
    for key, (secs, msg) in estimates.items():
        if key in p:
            return (secs, msg)
    return (120, "~2 min")


def get_analysis_status(project_id: str) -> dict:
    with _analysis_lock:
        s = _analysis_status.get(project_id, {"status": "idle", "progress": "Memulai..."}).copy()
        if s.get("status") == "analyzing" and s.get("progress"):
            eta_secs, eta_msg = _compute_eta(s["progress"])
            s["eta_seconds"] = eta_secs
            s["eta_message"] = eta_msg
        return s


def run_analysis(project_id: str, youtube_url: str, on_progress=None):
    """Run full analysis in background. Updates project metadata on completion."""
    _set_status(project_id, "analyzing", "Starting...")

    def _run():
        _ensure_sys_path()
        try:
            from backend.encoding_fix import apply
            apply()
        except Exception:
            pass
        from backend.project_manager import get_project, update_project, get_project_dir, PROJECTS_DIR

        project_dir = get_project_dir(project_id)
        video_dest = project_dir / "video.mp4"

        def prog(msg):
            _set_status(project_id, "analyzing", msg)
            if on_progress:
                on_progress(msg)

        try:
            prog("Downloading video...")
            # Use existing modules - need a context that provides the parent interface
            from backend.web_context import WebAppContext

            ctx = WebAppContext(project_dir, on_progress=prog)
            ctx.progress_var.set = lambda m: prog(m)

            # Download to default downloads/ then copy to project
            video_path = ctx.download_youtube_video(youtube_url)
            if not video_path or not os.path.exists(video_path):
                raise Exception("Failed to download video")

            prog("Copying video...")
            shutil.copy2(video_path, video_dest)
            base_src = Path(video_path).stem
            base_dst = "video"
            for ext in [".id.vtt", ".vtt", ".en.vtt", ".srt", ".words.json"]:
                sidecar = Path(video_path).parent / (base_src + ext)
                if sidecar.exists():
                    shutil.copy2(sidecar, project_dir / (base_dst + ext))

            prog("Downloading subtitles...")
            ctx.download_subtitles_only(youtube_url, str(video_dest))

            ctx.video_path = str(video_dest)
            ctx.current_video_path = str(video_dest)
            ctx.sub_transcriptions = {}

            # Fetch metadata (title, channel)
            import subprocess
            import sys
            try:
                cmd = [sys.executable, "-m", "yt_dlp", "--dump-json", "--flat-playlist", "--no-warnings", youtube_url]
                r = subprocess.run(cmd, capture_output=True, text=True, timeout=30, creationflags=0x08000000 if os.name == "nt" else 0)
                if r.returncode == 0:
                    meta = json.loads(r.stdout)
                    ctx.video_title = meta.get("title", "Unknown")
                    ctx.channel_name = meta.get("uploader", "Unknown")
            except Exception:
                pass

            prog("Extracting transcript...")
            manual_text = ""
            sidecar = ctx.find_sidecar_caption(str(video_dest))
            if sidecar.get("found"):
                path = sidecar["path"]
                if sidecar.get("kind") == "words_json":
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    subs = {}
                    if isinstance(data, dict) and "words" in data:
                        for i, w in enumerate(data["words"]):
                            s = w.get("s") or w.get("start", 0)
                            e = w.get("e") or w.get("end", 0)
                            if s > 1000:
                                s, e = s / 1000, e / 1000
                            subs[i] = {"start": s, "end": e, "text": w.get("t") or w.get("text", "")}
                    else:
                        for k, v in data.items():
                            try:
                                subs[int(k)] = v
                            except (ValueError, TypeError):
                                subs[k] = v
                    ctx.sub_transcriptions = subs
                    for _, d in sorted(subs.items()):
                        if isinstance(d, dict) and "start" in d and "text" in d:
                            manual_text += f"{timedelta(seconds=int(d['start']))} {d['text']}\n"
                else:
                    ctx.sub_transcriptions = ctx.parse_vtt(path)
                    for _, d in sorted(ctx.sub_transcriptions.items()):
                        if isinstance(d, dict) and "start" in d and "text" in d:
                            manual_text += f"{timedelta(seconds=int(d['start']))} {d['text']}\n"
                manual_text = manual_text.strip()

            transcriptions = {}
            heatmap_segments = []
            should_run_title_gen = True

            # Prefer Opus-style multi-clip AI segmentation when we have transcript (10-30 clips).
            # Only use parse_structured_segments for explicit chapter-style input (e.g. "01:45-03:30 | Title").
            has_chapter_format = manual_text and "|" in manual_text and re.search(r"\d{1,2}:\d{2}\s*-\s*\d", manual_text)
            if has_chapter_format:
                guessed = ctx.parse_structured_segments(manual_text)
                if guessed and len(guessed) > 1:
                    ctx.analysis_results = ctx.match_segments_with_content(
                        [{"start": g["start"], "end": g["end"], "avg_activity": 0.99} for g in guessed.values()],
                        guessed,
                    )
                    should_run_title_gen = False
                else:
                    has_chapter_format = False
            if not has_chapter_format:
                if not manual_text:
                    prog("Transcribing with AI...")
                    transcriptions = None
                    # Prefer Whisper+CUDA when available (much faster than Google Speech)
                    try:
                        import torch
                        use_whisper_gpu = torch.cuda.is_available()
                    except Exception:
                        use_whisper_gpu = False
                    if use_whisper_gpu:
                        transcriptions = ctx.transcribe_to_segments(str(video_dest))
                        if transcriptions:
                            ctx.sub_transcriptions = transcriptions
                    if not transcriptions:
                        audio_path = ctx.download_youtube_audio(youtube_url)
                        if audio_path and os.path.exists(audio_path):
                            transcriptions = ctx.transcribe_audio_file(audio_path)
                        else:
                            transcriptions = ctx.extract_audio_and_transcribe(str(video_dest))
                        if transcriptions:
                            ctx.sub_transcriptions = transcriptions
                else:
                    transcriptions = ctx.sub_transcriptions or ctx.parse_manual_transcript(manual_text)
                    if transcriptions and not ctx.sub_transcriptions:
                        ctx.sub_transcriptions = transcriptions

                if transcriptions:
                    from modules.ai_engine import AIEngine
                    ai_engine = AIEngine(ctx)
                    ctx.openai_available = getattr(ai_engine, "openai_available", False)

                    prog("Detecting viral moments...")
                    ai_segments = ctx.get_viral_segments_from_ai(transcriptions, keyword=None)
                    if ai_segments:
                        transcriptions = ai_segments
                        should_run_title_gen = False
                        for _, t in ai_segments.items():
                            heatmap_segments.append({"start": t["start"], "end": t["end"], "avg_activity": 0.99})
                    else:
                        heatmap_segments = ctx.analyze_video_heatmap(str(video_dest))
                else:
                    heatmap_segments = ctx.analyze_video_heatmap(str(video_dest))

                prog("Matching segments...")
                ctx.analysis_results = ctx.match_segments_with_content(heatmap_segments, transcriptions)

            if should_run_title_gen and ctx.analysis_results and ctx.openai_available:
                prog("Generating titles...")
                ctx.generate_segment_titles_parallel()

            # Build clips list for metadata (PART 8: id, title, start, end, duration, score)
            clips = []
            for i, r in enumerate(ctx.analysis_results):
                title = _safe_str((r.get("clickbait_title") or r.get("topic") or "Clip").strip())
                safe = "".join(c for c in title[:50] if c.isalnum() or c in (" ", "-", "_")).strip()
                if not safe:
                    safe = f"clip_{i+1}"
                clips.append({
                    "id": i + 1,
                    "title": title,
                    "start": r["start"],
                    "end": r["end"],
                    "duration": r["end"] - r["start"],
                    "score": int(r.get("final_score") or r.get("viral_score", r.get("virality_score", 0))),
                    "clip_path": None,  # Filled when exported
                })

            update_project(project_id,
                title=_safe_str(ctx.video_title or "Unknown"),
                video_path="video.mp4",
                clips=clips,
                status="analyzing",
                error=None,
            )
            num_clips = len(clips)
            prog("Rendering clips...")

            def render_progress(current: int, total: int):
                _set_status(project_id, "analyzing", f"Rendering clips {current}/{total}...")

            try:
                from backend.clip_service import export_all_clips
                meta = get_project(project_id)
                settings = meta.get("export_settings")
                export_all_clips(project_id, settings, on_progress=render_progress)
            except Exception as pre_render_err:
                import traceback
                traceback.print_exc()
                print(f"[ANALYSIS] Pre-render error (non-fatal): {pre_render_err}")
            update_project(project_id, status="ready", error=None)
            _set_status(project_id, "ready", "Analysis complete!")

        except Exception as e:
            import traceback
            traceback.print_exc()
            err_msg = _safe_str(str(e))
            update_project(project_id, status="error", error=err_msg)
            _set_status(project_id, "error", error=err_msg)

    t = threading.Thread(target=_run, daemon=True)
    t.start()

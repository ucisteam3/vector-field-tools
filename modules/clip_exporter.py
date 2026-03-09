"""
Clip Exporter Module
Handles clip downloading, encoding, and voiceover generation
"""

import os
import subprocess
import asyncio
import sys
import time
import threading
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

# Local temp directory for this app
LOCAL_TEMP_DIR = Path("temp")

try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False

# Import subtitle generation if available
try:
    from modules.subtitle_engine import generate_karaoke_ass
    SUBTITLE_ENGINE_AVAILABLE = True
except ImportError:
    SUBTITLE_ENGINE_AVAILABLE = False
    print("[WARNING] Subtitle engine not available")

# Import face tracking if available
try:
    from modules.face_tracker import FaceTracker
    import cv2
    import numpy as np
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False

# Import podcast smart tracker
try:
    from modules.podcast_smart_tracker import PodcastSmartTracker
    PODCAST_SMART_AVAILABLE = True
except ImportError:
    PODCAST_SMART_AVAILABLE = False


def _get_video_info(path: str) -> tuple[int, int, float]:
    """Get video width, height, fps via ffprobe. Returns (w, h, fps)."""
    try:
        r = subprocess.run(
            ['ffprobe', '-v', 'error', '-select_streams', 'v:0',
             '-show_entries', 'stream=width,height,r_frame_rate', '-of', 'csv=p=0', path],
            capture_output=True, text=True, timeout=10,
            creationflags=0x08000000 if os.name == "nt" else 0
        )
        if r.returncode == 0 and r.stdout:
            parts = r.stdout.strip().split(',')
            w, h = int(parts[0]), int(parts[1])
            fps = 30.0
            if len(parts) >= 3 and '/' in parts[2]:
                num, den = parts[2].split('/')
                if int(den) != 0:
                    fps = int(num) / int(den)
            return w, h, fps
    except Exception:
        pass
    return 1920, 1080, 30.0


def _gpu_available() -> bool:
    """Detect GPU via ffmpeg -hwaccels. Returns True if cuda available."""
    try:
        r = subprocess.run(
            ["ffmpeg", "-hwaccels"],
            capture_output=True, text=True, timeout=5,
            creationflags=0x08000000 if os.name == "nt" else 0
        )
        out = (r.stdout or "") + (r.stderr or "")
        return "cuda" in out.lower()
    except Exception:
        return False


_ffmpeg_filters_cache = None

def _ffmpeg_has_filters(*names: str) -> dict:
    """Check which of the given filter names exist in this FFmpeg build. Returns dict name -> bool."""
    global _ffmpeg_filters_cache
    if _ffmpeg_filters_cache is None:
        try:
            r = subprocess.run(
                ["ffmpeg", "-filters"],
                capture_output=True, text=True, timeout=10,
                creationflags=0x08000000 if os.name == "nt" else 0
            )
            out = (r.stdout or "") + (r.stderr or "")
            _ffmpeg_filters_cache = out.lower()
        except Exception:
            _ffmpeg_filters_cache = ""
    import re
    out = _ffmpeg_filters_cache
    return {n: bool(re.search(r"\b" + re.escape(n.lower()) + r"\b", out)) for n in names}


def finalize_filter_graph(fc: str) -> str:
    """Never end a filter graph with a semicolon. Use before running FFmpeg."""
    return (fc.strip().rstrip(";") if fc else fc) or ""


def finalize_filter(fc):
    """Alias for finalize_filter_graph for backward compatibility."""
    return finalize_filter_graph(fc)


def append_filter(fc: str, chain: str) -> str:
    """Safe builder: prevents accidental double semicolons between filter chains."""
    if not fc or not fc.strip():
        return chain.strip() if chain else ""
    if not chain or not chain.strip():
        return fc.strip()
    return fc.strip().rstrip(";") + ";" + chain.strip().lstrip(";")


def _safe_messagebox(kind, title, message):
    """Show messagebox only when GUI is available (desktop). In web/headless, just print to avoid crash."""
    try:
        if kind == "error" and hasattr(messagebox, "showerror"):
            messagebox.showerror(title, message)
        elif kind == "info" and hasattr(messagebox, "showinfo"):
            messagebox.showinfo(title, message)
    except Exception:
        print(f"  [{title}] {message}")


class ClipExporter:
    """Manages clip export operations including download, encoding, and voiceover.
    Backend-safe: works with WebAppContext via safe_parent_call."""
    
    def __init__(self, parent):
        """
        Initialize Clip Exporter
        
        Args:
            parent: Reference to YouTubeHeatmapAnalyzer or WebAppContext (can be None)
        """
        self.parent = parent

    def safe_parent_call(self, method, *args, **kwargs):
        """Safely call a parent method if it exists. Returns None if parent=None or method missing."""
        if self.parent is None:
            return None
        if hasattr(self.parent, method):
            return getattr(self.parent, method)(*args, **kwargs)
        return None
    
    async def _amake_voiceover(self, text, output_path):
        """Internal async method for edge-tts"""
        communicate = edge_tts.Communicate(text, "id-ID-GadisNeural") # Female Indonesian voice
        await communicate.save(output_path)

    def generate_voiceover(self, text, output_path):
        """Generate voice over using edge-tts (Sync wrapper)"""
        try:
            if self.parent and hasattr(self.parent, "_amake_voiceover"):
                asyncio.run(self.parent._amake_voiceover(text, output_path))
            else:
                asyncio.run(self._amake_voiceover(text, output_path))
            return True
        except Exception as e:
            print(f"  [ERROR] VoiceOver generation failed: {e}")
            return False

    def _download_worker(self, segments_to_download):
        """Background worker for downloading clips"""
        try:
            clips_dir = Path("clips")
            clips_dir.mkdir(exist_ok=True)
            
            total = len(segments_to_download)
            for i, result in enumerate(segments_to_download):
                if self.parent and hasattr(self.parent, "progress_var"):
                    self.parent.progress_var.set(f"Mengunduh klip {i+1}/{total}...")
                if self.parent and hasattr(self.parent, "root"):
                    self.parent.root.after(0, self.parent.root.update_idletasks)
                if self.parent and hasattr(self.parent, "download_clip"):
                    self.parent.download_clip(result, clips_dir, i+1)
                else:
                    self.download_clip(result, clips_dir, i+1)
            
            if self.parent and hasattr(self.parent, "progress_var"):
                self.parent.progress_var.set(f"Selesai! {total} klip disimpan di folder 'clips'.")
            print(f"\n============================================================")
            print(f"Analysis & Export Complete! {total} klip berhasil disimpan.")
            print(f"============================================================\n")
            if self.parent and hasattr(self.parent, "root"):
                if hasattr(messagebox, "showinfo"):
                    self.parent.root.after(0, lambda: messagebox.showinfo("Berhasil", f"{total} klip berhasil diunduh!"))
        except Exception as e:
            if self.parent and hasattr(self.parent, "root"):
                if hasattr(messagebox, "showerror"):
                    self.parent.root.after(0, lambda: messagebox.showerror("Kesalahan", f"Thread pengunduhan gagal: {str(e)}"))
            print(f"  [ERROR] Thread pengunduhan gagal: {e}")
        finally:
            if self.parent and hasattr(self.parent, "download_btn") and hasattr(self.parent, "root"):
                self.parent.root.after(0, lambda: self.parent.download_btn.config(state=tk.NORMAL))

    def detect_leading_silence(self, video_path, start_time, check_duration=3.0):
        """Detect silence at the beginning of the clip segment"""
        # [INSTANT START] Analyze first 3 seconds for silence
        try:
            import subprocess
            import re
            
            cmd = [
                'ffmpeg', 
                '-ss', str(start_time),
                '-t', str(check_duration),
                '-i', str(video_path),
                '-af', 'silencedetect=noise=-30dB:d=0.1',
                '-f', 'null', 
                '-'
            ]
            
            # Run FFmpeg (silencedetect writes to stderr)
            result = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                universal_newlines=True,
                creationflags=0x08000000 
            )
            
            output = result.stderr
            
            # Check if silence starts at roughly 0
            # [silencedetect @ ...] silence_start: 0.000000
            # [silencedetect @ ...] silence_end: 1.230000
            
            s_start = re.search(r'silence_start:\s*([0-9\.]+)', output)
            s_end = re.search(r'silence_end:\s*([0-9\.]+)', output)
            
            if s_start and s_end:
                start_val = float(s_start.group(1))
                end_val = float(s_end.group(1))
                
                # If silence starts at the beginning (allow 0.1s tolerance)
                if start_val < 0.1:
                    trim_amount = end_val
                    # Cap trim amount (don't trim more than 2s to be safe)
                    trim_amount = min(trim_amount, 2.0)
                    
                    if trim_amount > 0.1:
                        print(f"  [INSTANT START] Detect Silence: {trim_amount:.2f}s (Adjusting Start Time)")
                        return trim_amount
            
            return 0.0
            
        except Exception as e:
            print(f"  [SILENCE DETECT ERROR] {e}")
            return 0.0

    def _progress(self, percent: int, message: str):
        """Report progress if callback is set."""
        cb = getattr(self.parent, "export_progress_callback", None)
        if cb and callable(cb):
            try:
                cb(percent, message)
            except Exception:
                pass

    def download_clip(self, result, output_dir=None, clip_num=None):
        """Download a single clip using ffmpeg with high quality re-encoding."""
        try:
            self._progress(0, "Memulai export...")
        except Exception:
            pass
        if not self.parent:
            print("  [ERROR] Export context (parent) missing.")
            return False
        video_path = getattr(self.parent, "video_path", None)
        if not video_path or not str(video_path).strip():
            print("  [ERROR] Video path not set.")
            _safe_messagebox("error", "Error", "Video belum diunduh!")
            return False

        # [INSTANT START] Leading silence detection disabled to avoid export pipeline crashes
        try:
            self._progress(2, "Skipping silence detection...")
        except Exception:
            pass

        if not isinstance(result, dict):
            print("  [ERROR] Invalid result: not a dict.")
            return False
        try:
            silence_offset = 0
            if silence_offset > 0:
                result["start"] = result.get("start", 0) + silence_offset

            output_dir = Path(output_dir) if output_dir is not None else Path("clips")
            output_dir.mkdir(parents=True, exist_ok=True)

            topic = result.get("topic") or "Clip"
            safe_topic = "".join(c for c in str(topic)[:50] if c.isalnum() or c in (" ", "-", "_")).strip()
            if not safe_topic:
                safe_topic = f"clip_{clip_num or 'selected'}"
            output_filename = f"{safe_topic}.mp4"
            output_path = output_dir / output_filename

            start = float(result.get("start", 0))
            end = float(result.get("end", start + 30))
            duration = max(0.1, end - start)
            result["start"] = start
            result["end"] = end
        except Exception as e:
            print(f"  [EXPORT ERROR] Setup failed: {e}")
            import traceback
            traceback.print_exc()
            return False

        try:
            # Use ffmpeg to extract clip
            import subprocess
            
            # Check if ffmpeg is available
            try:
                subprocess.run(
                    ["ffmpeg", "-version"],
                    capture_output=True,
                    check=True,
                    creationflags=(0x08000000 if os.name == "nt" else 0),
                )
            except (subprocess.CalledProcessError, FileNotFoundError):
                _safe_messagebox("error", "Kesalahan",
                    "FFmpeg tidak ditemukan. Silakan instal FFmpeg dan tambahkan ke PATH.")
                return False
            
            # Voice Over Hook Logic
            voiceover_path = None
            if EDGE_TTS_AVAILABLE and getattr(self.parent, "use_voiceover_var", None) and self.parent.use_voiceover_var.get() and result.get("hook_script"):
                gen_vox = getattr(self.parent, "generate_voiceover", None)
                if callable(gen_vox):
                    print(f"  [AI VOX] Generating hook: {result['hook_script']}")
                    temp_vox = Path(LOCAL_TEMP_DIR) / f"vox_{int(time.time())}.mp3"
                    if gen_vox(result["hook_script"], str(temp_vox)):
                        voiceover_path = temp_vox

            # --- SUBTITLE GENERATION (Word-Level Karaoke) ---
            ass_path = None
            _sv = getattr(self.parent, "subtitle_enabled_var", None)
            subtitle_enabled = bool(_sv and getattr(_sv, "get", None) and _sv.get()) if _sv else False
            if subtitle_enabled:
                try:
                    # 1. Prepare Settings for this Clip (Copy global)
                    clip_settings = self.parent.custom_settings.copy()
                    clip_settings['clip_start_time'] = result['start']
                    
                    # Search for Source VTT file (if mode is youtube_cc)
                    # Pattern: video_name.id.vtt or video_name.vtt or video_name.en.vtt
                    # Search for Source VTT file (if mode is youtube_cc OR auto)
                    # Pattern: video_name.id.vtt or video_name.vtt or video_name.en.vtt
                    current_mode = clip_settings.get("whisper_model", "auto")
                    
                    if current_mode == "youtube_cc" or current_mode == "auto":
                        vid_path = Path(self.parent.video_path)
                        base_stem = vid_path.stem # video
                        parent = vid_path.parent
                        
                        # Try common patterns
                        found_vtt = None
                        for ext in [".id.vtt", ".vtt", ".en.vtt", ".id.srv1", ".id.vtt", ".en.srv1"]:
                             # Also try simpler stem (sometimes yt-dlp adds id to filename but not vtt, or vice versa)
                             # Strategy: check direct concatenation
                             candidate = parent / f"{base_stem}{ext}"
                             if candidate.exists():
                                 found_vtt = str(candidate)
                                 break
                        
                        if found_vtt:
                            print(f"  [SUBTITLE] Found Youtube CC (Auto): {found_vtt}")
                            clip_settings['video_vtt_path'] = found_vtt
                            # Force mode to use CC logic downstream
                            clip_settings['whisper_model'] = "youtube_cc" 
                        else:
                            if current_mode == "auto":
                                print(f"  [SUBTITLE] Auto Mode: No CC found. Fallback to AI (Small).")
                                clip_settings['whisper_model'] = "small"
                            else:
                                print(f"  [SUBTITLE] WARN: Mode 'youtube_cc' active but NO .vtt file found! Will skip or fallback?")
                                clip_settings['whisper_model'] = "small"
                    
                    # 1. Extract audio from original video for this specific segment
                    temp_audio_cut = Path(LOCAL_TEMP_DIR) / f"sub_audio_{int(time.time())}.wav"
                    # [A/V SYNC] -ss AFTER -i for frame-accurate seek (avoids audio/video desync)
                    sub_cmd = [
                        'ffmpeg', '-y', '-i', str(self.parent.video_path),
                        '-ss', str(result['start']), '-t', str(duration),
                        '-ac', '1', '-ar', '16000', str(temp_audio_cut)
                    ]
                    subprocess.run(sub_cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)
                    
                    if temp_audio_cut.exists():
                        # 2. Generate ASS
                        temp_ass = Path(LOCAL_TEMP_DIR) / f"karaoke_{int(time.time())}.ass"
                        if generate_karaoke_ass(temp_audio_cut, temp_ass, clip_settings):
                            ass_path = temp_ass
                            # [DEBUG] Check if ASS is valid and has content
                            if temp_ass.exists():
                                sz = temp_ass.stat().st_size
                                print(f"  [DEBUG] ASS Generated success: {temp_ass} (Size: {sz} bytes)")
                                # Check if it has events
                                with open(temp_ass, 'r', encoding='utf-8') as f:
                                    content = f.read()
                                    if "[Events]" in content and "Dialogue:" in content:
                                        print(f"  [DEBUG] ASS has valid [Events] and Dialogue lines.")
                                    else:
                                        print(f"  [DEBUG] WARNING: ASS file exists but seems to have NO dialogue!")
                            else:
                                print(f"  [DEBUG] generate_karaoke_ass returned True but file MISSING?")
                        else:
                            print(f"  [DEBUG] generate_karaoke_ass returned False")
                        
                        try: temp_audio_cut.unlink()
                        except: pass
                except Exception as e:
                    print(f"  [SUBTITLE ERROR] {e}")

            # Prepare base FFmpeg filters and inputs
            # Check if BGM is enabled and file exists
            bgm_enabled = self.parent.custom_settings.get("bgm_enabled", False)
            bgm_file_path = self.parent.custom_settings.get("bgm_file_path", "")
            has_bgm = bgm_enabled and bgm_file_path and os.path.exists(bgm_file_path)
            
            if has_bgm:
                print(f"  [BGM] File: {os.path.basename(bgm_file_path)}")
                print(f"  [BGM] Volume: -10dB (0.316x)")
                print(f"  [BGM] Mode: Auto-Loop (menyesuaikan durasi clip)")
            
            if voiceover_path:
                # Filter: Pad VOX or amix with ducking? 
                # Let's use amix with volume adjustment: VOX at 1.5, BG at 0.4
                if has_bgm:
                    # Complex: Original Audio + Voiceover + BGM
                    # BGM at -10dB = volume=0.316 (10^(-10/20) ~= 0.316)
                    # Original at 1.0 (KEEP FULL VOLUME), VOX at 1.5, BGM at 0.316
                    audio_filter = (
                        "[1:a]volume=1.5[vox];"
                        "[0:a]volume=1.0[bg];"
                        "[2:a]volume=0.316,aloop=loop=-1:size=2e+09[bgm];"  # Loop BGM, -10dB
                        "[bg][vox]amix=inputs=2:duration=first[mix1];"
                        "[mix1][bgm]amix=inputs=2:duration=first:dropout_transition=2"
                    )
                    input_args = ['-i', str(self.parent.video_path), '-i', str(voiceover_path), '-i', bgm_file_path]
                else:
                    # Original at 1.0 (KEEP FULL VOLUME), VOX at 1.5
                    audio_filter = "[1:a]volume=1.5[vox];[0:a]volume=1.0[bg];[bg][vox]amix=inputs=2:duration=first:dropout_transition=2"
                    input_args = ['-i', str(self.parent.video_path), '-i', str(voiceover_path)]
            else:
                if has_bgm:
                    # Only BGM + Original Audio
                    # BGM at -10dB = volume=0.316
                    audio_filter = (
                        "[0:a]volume=1.0[orig];"
                        "[1:a]volume=0.316,aloop=loop=-1:size=2e+09[bgm];"  # Loop BGM, -10dB
                        "[orig][bgm]amix=inputs=2:duration=first:dropout_transition=2"
                    )
                    input_args = ['-i', str(self.parent.video_path), '-i', bgm_file_path]
                else:
                    audio_filter = "[0:a]anull"  # Passthrough
                    input_args = ['-i', str(self.parent.video_path)]


            # Construct Filter Complex
            fc_str = ""
            _raw_mode = self.parent.custom_settings.get("export_mode", "landscape_fit")
            # Normalize: ensure only supported modes (portrait=face_tracking, landscape_fit, podcast_smart)
            if _raw_mode in ("portrait", "face_tracking", "9:16", "portrait_9_16"):
                export_mode = "face_tracking"
            elif _raw_mode == "landscape_fit":
                export_mode = "landscape_fit"
            elif _raw_mode == "podcast_smart":
                export_mode = "podcast_smart"
            else:
                export_mode = "landscape_fit"
            mode_label = {"podcast_smart": "Podcast Smart", "face_tracking": "9:16 Portrait", "landscape_fit": "Landscape Fit"}.get(export_mode, export_mode)
            self._progress(3, f"Mode: {mode_label}...")
            print(f"  [EXPORT] Mode: {export_mode} ({mode_label})")

            # Heavy filters force CPU fallback (no CUDA equivalents: zoompan, subtitles, drawtext, boxblur, overlay)
            has_heavy_filters = (
                self.parent.custom_settings.get("dynamic_zoom_enabled", False) or
                bool(ass_path) or
                self.parent.custom_settings.get("watermark_enabled", False) or
                self.parent.custom_settings.get("overlay_enabled", False) or
                self.parent.custom_settings.get("source_credit_enabled", False)
            )

            # Podcast Smart: pre-process video with per-frame active-speaker crop
            effective_video_path = str(self.parent.video_path)
            effective_start = result['start']
            effective_duration = duration
            if export_mode == "podcast_smart" and PODCAST_SMART_AVAILABLE:
                self._progress(5, "Podcast Smart: 1 FPS analysis...")
                print("  [PODCAST SMART] Active speaker (1 FPS) - analyzing...")
                try:
                    tracker = PodcastSmartTracker(smoothing_factor=0.15, face_margin=1.4)
                    crop_boxes = tracker.analyze_video(
                        str(self.parent.video_path),
                        start_time=result['start'],
                        duration=duration,
                        sample_rate=5,
                    )
                    tracker.close()
                    pad_start = max(0, result['start'] - 0.2)
                    pad_end = result['start'] + duration + 0.2
                    pad_dur = pad_end - pad_start
                    temp_full = Path(LOCAL_TEMP_DIR) / f"podcast_full_{int(time.time())}.mp4"
                    temp_audio = Path(LOCAL_TEMP_DIR) / f"podcast_audio_{int(time.time())}.m4a"
                    Path(LOCAL_TEMP_DIR).mkdir(parents=True, exist_ok=True)
                    subprocess.run([
                        'ffmpeg', '-y', '-ss', str(pad_start), '-t', str(pad_dur),
                        '-i', str(self.parent.video_path),
                        '-vn', '-acodec', 'copy', '-avoid_negative_ts', 'make_zero',
                        str(temp_audio)
                    ], capture_output=True, creationflags=0x08000000 if os.name == "nt" else 0)
                    use_gpu_mux = _gpu_available() and getattr(self.parent, 'gpu_var', None) and self.parent.gpu_var.get()
                    self._progress(15, "Podcast Smart: Decode + crop...")
                    src_w, src_h, fps = _get_video_info(str(self.parent.video_path))
                    decode_cmd = [
                        'ffmpeg', '-y', '-ss', str(pad_start), '-t', str(pad_dur),
                        '-i', str(self.parent.video_path),
                        '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', f'{src_w}x{src_h}',
                        '-an', '-'
                    ]
                    nvenc_args = ['-c:v', 'h264_nvenc', '-preset', 'p5', '-tune', 'hq',
                        '-rc:v', 'vbr', '-cq:v', '19', '-b:v', '6M', '-maxrate', '10M', '-bufsize', '12M']
                    cpu_args = ['-c:v', 'libx264', '-preset', 'fast', '-crf', '23']
                    enc_args = nvenc_args if use_gpu_mux else cpu_args
                    encode_cmd = [
                        'ffmpeg', '-y',
                        '-f', 'rawvideo', '-pix_fmt', 'bgr24', '-s', '1080x1920', '-r', str(fps),
                        '-i', 'pipe:0', '-i', str(temp_audio),
                        *enc_args, '-c:a', 'aac', '-b:a', '192k', '-shortest',
                        '-fflags', '+genpts', '-avoid_negative_ts', 'make_zero',
                        '-max_muxing_queue_size', '1024', str(temp_full)
                    ]
                    proc_decode = subprocess.Popen(
                        decode_cmd, stdout=subprocess.PIPE,
                        creationflags=0x08000000 if os.name == "nt" else 0
                    )
                    proc_encode = subprocess.Popen(
                        encode_cmd, stdin=subprocess.PIPE,
                        creationflags=0x08000000 if os.name == "nt" else 0
                    )
                    frame_size = src_w * src_h * 3
                    total_frames = len(crop_boxes)
                    frame_idx = 0
                    try:
                        while frame_idx < total_frames:
                            raw = proc_decode.stdout.read(frame_size)
                            if len(raw) < frame_size:
                                break
                            frame = np.frombuffer(raw, dtype=np.uint8).reshape((src_h, src_w, 3))
                            box_idx = min(frame_idx, len(crop_boxes) - 1)
                            x, y, cw, ch = (int(v) for v in crop_boxes[box_idx])
                            if cw > 0 and ch > 0:
                                cropped = frame[y:y+ch, x:x+cw]
                                if cropped.size:
                                    scaled = cv2.resize(cropped, (1080, 1920))
                                    proc_encode.stdin.write(scaled.tobytes())
                            frame_idx += 1
                            if frame_idx % 30 == 0:
                                pct = 15 + int(30 * frame_idx / max(1, total_frames))
                                self._progress(min(pct, 45), f"Podcast Smart: Frame {frame_idx}/{total_frames}")
                    finally:
                        proc_decode.stdout.close()
                        proc_encode.stdin.close()
                    proc_decode.wait()
                    proc_encode.wait()
                    if proc_decode.returncode != 0 or proc_encode.returncode != 0:
                        print(f"  [PODCAST] Encode gagal (decode={proc_decode.returncode}, encode={proc_encode.returncode})")
                        raise RuntimeError("Podcast smart encode gagal.")
                    effective_video_path = str(temp_full)
                    effective_start = 0
                    effective_duration = pad_end - pad_start
                    try:
                        temp_audio.unlink(missing_ok=True)
                    except Exception:
                        pass
                except Exception as e:
                    print(f"  [PODCAST SMART ERROR] {e} - falling back to center crop")

            # Use effective video path for inputs (podcast_smart replaces with pre-cropped temp)
            if input_args[0] == '-i':
                input_args[1] = effective_video_path

            use_pure_gpu_possible = _gpu_available() and getattr(self.parent, 'gpu_var', None) and self.parent.gpu_var.get()
            base_supports_gpu = False

            # --- Mode 1: Podcast Smart (preprocessed 1080x1920) — output 9:16, only setsar ---
            if export_mode == "podcast_smart" and effective_video_path != str(self.parent.video_path):
                base_supports_gpu = True
                if use_pure_gpu_possible and not has_heavy_filters:
                    fc_str = "[0:v]scale_cuda=1080:1920[v_mixed];"
                else:
                    fc_str = "[0:v]setsar=1[v_mixed];"
                print("  [MODE] Podcast Smart — video sudah 9:16 dari preprocessing")
            # --- Mode 2: Portrait / Face Tracking — center crop 9:16 (safer crop expr) ---
            elif export_mode == "face_tracking":
                fc_str = "[0:v]setsar=1,crop=ih*9/16:ih:(iw-(ih*9/16))/2:0,scale=1080:1920[v_mixed];"
                print("  [MODE] 9:16 Portrait — center crop 1080x1920")
            # --- Mode 3: Landscape Fit + Podcast fallback ---
            else:
                self._progress(25, "Mempersiapkan filter...")
                if export_mode == "podcast_smart" and effective_video_path == str(self.parent.video_path):
                    print("  [MODE] Podcast Smart fallback — 9:16 center crop")
                    fc_str = "[0:v]setsar=1,crop=ih*9/16:ih:(iw-(ih*9/16))/2:0,scale=1080:1920[v_mixed];"
                elif export_mode == "landscape_fit":
                    # Letterboxed 9:16: scale to fit then pad
                    fc_str = "[0:v]setsar=1,scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:black[v_mixed];"
                    print("  [MODE] Landscape Fit — letterbox/pillarbox 9:16 (1080x1920)")
                else:
                    # Legacy: blur background + overlay
                    fc_str = (
                        f"[0:v]setsar=1,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=20:10[bg_v];"
                        f"[0:v]setsar=1,scale=1080:-1[fg_v];"
                        f"[bg_v][fg_v]overlay=(W-w)/2:(H-h)/2[v_mixed];"
                    )
                    print("  [MODE] Legacy blur background — 9:16")
            
            # Save base filter (video only up to [v_mixed]) for "Filter not found" retry
            base_fc_str = fc_str
            base_last_v_label = "[v_mixed]"
            
            # --- Check FFmpeg filter availability (avoid "Filter not found" on minimal builds) ---
            _has = _ffmpeg_has_filters("subtitles", "drawtext", "zoompan", "hflip")
            # --- DYNAMIC ZOOM (skip if FFmpeg has no 'zoompan') ---
            zoom_enabled = self.parent.custom_settings.get("dynamic_zoom_enabled", False) and _has.get("zoompan", True)
            if zoom_enabled:
                zoom_strength = float(self.parent.custom_settings.get("dynamic_zoom_strength", 1.55))
                zoom_speed = float(self.parent.custom_settings.get("dynamic_zoom_speed", 0.0032))
                zoom_strength = max(1.1, min(2.0, zoom_strength))
                zoom_speed = max(0.0015, min(0.008, zoom_speed))
                print(f"  [DYNAMIC ZOOM] strength={zoom_strength}, speed={zoom_speed}")
                fc_str += f"[v_mixed]zoompan=z='min(zoom+{zoom_speed:.4f},{zoom_strength:.2f})':d=1:s=1080x1920[v_zoom];"
                last_v_label = "[v_zoom]"
            else:
                last_v_label = "[v_mixed]"
            
            # --- VIDEO FLIP (skip if FFmpeg has no 'hflip') ---
            flip_enabled = self.parent.custom_settings.get("video_flip_enabled", False) and _has.get("hflip", True)
            if flip_enabled:
                print(f"  [FLIP] Horizontal flip enabled (anti-copyright)")
                fc_str += f"{last_v_label}hflip[v_flipped];"
                last_v_label = "[v_flipped]"
            
            # --- SUBTITLE OVERLAY (skip if FFmpeg build has no 'subtitles' filter, e.g. no libass) ---
            if ass_path and _has.get("subtitles", True):
                safe_ass_path = str(ass_path).replace("\\", "/").replace(":", "\\:")
                fonts_dir = str(Path("assets/fonts").resolve()).replace("\\", "/").replace(":", "\\:")
                fc_str += f"{last_v_label}subtitles='{safe_ass_path}':fontsdir='{fonts_dir}'[v_sub];"
                last_v_label = "[v_sub]"
            elif ass_path and not _has.get("subtitles", True):
                print("  [EXPORT] Skipping subtitles (FFmpeg filter 'subtitles' not in this build).")
            
            # --- WATERMARK LOGIC (skip if FFmpeg has no 'drawtext') ---
            if self.parent.custom_settings.get("watermark_enabled") and _has.get("drawtext", True):
                try:
                    wm_type = self.parent.custom_settings.get("watermark_type", "text")
                    wm_pos_x_pct = self.parent.custom_settings.get("watermark_pos_x", 50)
                    wm_pos_y_margin = self.parent.custom_settings.get("watermark_pos_y", 50)
                    
                    # Position Logic
                    # X: Percentage (centered anchor) -> (W * pct/100) - (w/2)
                    # Y: Bottom Margin (px) -> H - h - margin
                    
                    if wm_type == "text":
                        wm_text = self.parent.custom_settings.get("watermark_text", "Watermark")
                        if wm_text:
                            # [FIX] Scale watermark size for 1080p (Slider is 8-96, Output needs to match Subtitle scale)
                            # Applying 10x multiplier to match subtitle_engine logic
                            wm_base_size = self.parent.custom_settings.get("watermark_size", 48)
                            wm_size = int(wm_base_size * 10)
                            wm_font_name = self.parent.custom_settings.get("watermark_font", "Arial")
                            # Map Font Name to File
                            from modules.font_manager import VIRAL_FONTS
                            font_path = None
                            
                            # 1. Try Viral Fonts (Assets)
                            if wm_font_name in VIRAL_FONTS:
                                local_font = f"assets/fonts/{VIRAL_FONTS[wm_font_name][1]}"
                                if os.path.exists(local_font):
                                    font_path = local_font
                            
                            # 2. Try Direct Filename match
                            if not font_path:
                                candidate = f"assets/fonts/{wm_font_name}.ttf"
                                if os.path.exists(candidate):
                                    font_path = candidate
                            
                            # 3. Fallback to Safe Asset Font (Roboto-Bold)
                            if not font_path:
                                fallback = "assets/fonts/Roboto-Bold.ttf"
                                if os.path.exists(fallback):
                                    font_path = fallback
                                else:
                                    # Absolute panic fallback
                                    try:
                                        import glob
                                        found = glob.glob("assets/fonts/*.ttf")
                                        if found: font_path = found[0]
                                    except: pass
                            
                            if font_path:
                                font_abs = os.path.abspath(font_path).replace("\\", "/").replace(":", "\\:").replace("'", "")
                            else:
                                font_abs = "arial.ttf" # Should not happen if assets exist
                            
                            wm_col = self.parent.custom_settings.get("watermark_color", "#FFFFFF").replace("#", "0x")
                            wm_op = self.parent.custom_settings.get("watermark_opacity", 80) / 100.0
                            wm_out_w = self.parent.custom_settings.get("watermark_outline_width", 2)
                            wm_out_col = self.parent.custom_settings.get("watermark_outline_color", "#000000").replace("#", "0x")
                            
                            safe_wm_text = wm_text.replace(":", "\\:").replace("'", "")
                            
                            # Text Position Expr:
                            # x = (W*pct/100) - (text_w/2)
                            # y = H - text_h - margin
                            x_expr = f"(W*{wm_pos_x_pct}/100)-(text_w/2)"
                            y_expr = f"H-text_h-{wm_pos_y_margin}"
                            
                            fc_str += f"{last_v_label}drawtext=text='{safe_wm_text}':fontfile='{font_abs}':fontsize={wm_size}:fontcolor={wm_col}@{wm_op}:borderw={wm_out_w}:bordercolor={wm_out_col}@{wm_op}:x={x_expr}:y={y_expr}[v_wm];"
                            last_v_label = "[v_wm]"

                    elif wm_type == "image":
                        wm_path = self.parent.custom_settings.get("watermark_image_path")
                        if wm_path and os.path.exists(wm_path):
                            # Add input
                            input_args.extend(['-i', wm_path])
                            wm_idx = (len(input_args) // 2) - 1
                            
                            scale_pct = self.parent.custom_settings.get("watermark_image_scale", 50) / 100.0
                            wm_op = self.parent.custom_settings.get("watermark_image_opacity", 100) / 100.0
                            
                            # Complex filter for Image: scale, opacity, overlay
                            # We need to process the watermark image first
                            
                            # 1. Scale & Opacity
                            wm_proc = f"[wm_proc_{wm_idx}]"
                            fc_str += f"[{wm_idx}:v]format=rgba,scale=iw*{scale_pct}:-1,colorchannelmixer=aa={wm_op}{wm_proc};"
                            
                            # 2. Overlay
                            # x = (W*pct/100) - (w/2)
                            # y = H - h - margin
                            x_expr = f"(W*{wm_pos_x_pct}/100)-(w/2)"
                            y_expr = f"H-h-{wm_pos_y_margin}"
                            
                            fc_str += f"{last_v_label}{wm_proc}overlay=x='{x_expr}':y='{y_expr}'[v_wm];"
                            last_v_label = "[v_wm]"
                            
                except Exception as e:
                    print(f"[EXPORT ERROR] Watermark failed: {e}")

            # --- OVERLAY LOGIC (Second Watermark) ---
            if self.parent.custom_settings.get("overlay_enabled") and _has.get("drawtext", True):
                try:
                    ov_type = self.parent.custom_settings.get("overlay_type", "text")
                    ov_pos_x_pct = self.parent.custom_settings.get("overlay_pos_x", 50)
                    ov_pos_y_margin = self.parent.custom_settings.get("overlay_pos_y", 200)
                    
                    if ov_type == "text":
                        ov_text = self.parent.custom_settings.get("overlay_text", "Overlay")
                        if ov_text:
                            # Scale overlay size for 1080p
                            ov_base_size = self.parent.custom_settings.get("overlay_size", 48)
                            ov_size = int(ov_base_size * 10)
                            ov_font_name = self.parent.custom_settings.get("overlay_font", "Arial")
                            
                            # Map Font Name to File
                            from modules.font_manager import VIRAL_FONTS
                            font_path = None
                            
                            # 1. Try Viral Fonts (Assets)
                            if ov_font_name in VIRAL_FONTS:
                                local_font = f"assets/fonts/{VIRAL_FONTS[ov_font_name][1]}"
                                if os.path.exists(local_font):
                                    font_path = local_font
                            
                            # 2. Try Direct Filename match
                            if not font_path:
                                candidate = f"assets/fonts/{ov_font_name}.ttf"
                                if os.path.exists(candidate):
                                    font_path = candidate
                            
                            # 3. Fallback to Safe Asset Font
                            if not font_path:
                                fallback = "assets/fonts/Roboto-Bold.ttf"
                                if os.path.exists(fallback):
                                    font_path = fallback
                                else:
                                    try:
                                        import glob
                                        found = glob.glob("assets/fonts/*.ttf")
                                        if found: font_path = found[0]
                                    except: pass
                            
                            if font_path:
                                font_abs = os.path.abspath(font_path).replace("\\", "/").replace(":", "\\:").replace("'", "")
                            else:
                                font_abs = "arial.ttf"
                            
                            ov_col = self.parent.custom_settings.get("overlay_color", "#FFFFFF").replace("#", "0x")
                            ov_op = self.parent.custom_settings.get("overlay_opacity", 80) / 100.0
                            ov_out_w = self.parent.custom_settings.get("overlay_outline_width", 2)
                            ov_out_col = self.parent.custom_settings.get("overlay_outline_color", "#000000").replace("#", "0x")
                            
                            safe_ov_text = ov_text.replace(":", "\\:").replace("'", "")
                            
                            # Position expressions
                            x_expr = f"(W*{ov_pos_x_pct}/100)-(text_w/2)"
                            y_expr = f"H-text_h-{ov_pos_y_margin}"
                            
                            fc_str += f"{last_v_label}drawtext=text='{safe_ov_text}':fontfile='{font_abs}':fontsize={ov_size}:fontcolor={ov_col}@{ov_op}:borderw={ov_out_w}:bordercolor={ov_out_col}@{ov_op}:x={x_expr}:y={y_expr}[v_ov];"
                            last_v_label = "[v_ov]"

                    elif ov_type == "image":
                        ov_path = self.parent.custom_settings.get("overlay_image_path")
                        if ov_path and os.path.exists(ov_path):
                            # Add input
                            input_args.extend(['-i', ov_path])
                            ov_idx = (len(input_args) // 2) - 1
                            
                            scale_pct = self.parent.custom_settings.get("overlay_image_scale", 50) / 100.0
                            ov_op = self.parent.custom_settings.get("overlay_image_opacity", 100) / 100.0
                            
                            # Process overlay image
                            ov_proc = f"[ov_proc_{ov_idx}]"
                            fc_str += f"[{ov_idx}:v]format=rgba,scale=iw*{scale_pct}:-1,colorchannelmixer=aa={ov_op}{ov_proc};"
                            
                            # Overlay position
                            x_expr = f"(W*{ov_pos_x_pct}/100)-(w/2)"
                            y_expr = f"H-h-{ov_pos_y_margin}"
                            
                            fc_str += f"{last_v_label}{ov_proc}overlay=x='{x_expr}':y='{y_expr}'[v_ov];"
                            last_v_label = "[v_ov]"
                            
                except Exception as e:
                    print(f"[EXPORT ERROR] Overlay failed: {e}")

            # --- SOURCE CREDIT LOGIC ---
            if self.parent.custom_settings.get("source_credit_enabled") and _has.get("drawtext", True):
                try:
                    # Prioritas utama: pakai metadata channel asli yang sudah diambil di main.py
                    channel_name = getattr(self.parent, "channel_name", None)
                    if not channel_name or channel_name == "Unknown Channel":
                        # Fallback 1: coba ambil dari label UI jika ada
                        if self.parent and hasattr(self.parent, "channel_name_label"):
                            try:
                                ui_channel = self.parent.channel_name_label.cget("text")
                                if ui_channel and ui_channel != "-":
                                    channel_name = ui_channel
                            except Exception:
                                pass

                    if not channel_name or channel_name == "Unknown Channel":
                        # Fallback 2: heuristik dari nama file (hanya jika ada pola " - ")
                        if self.parent.video_path:
                            video_path = Path(self.parent.video_path)
                            video_stem = video_path.stem  # filename without extension
                            
                            # Common patterns: "ChannelName - Video Title [ID].mp4"
                            # Hanya gunakan jika ada separator " - " untuk menghindari menggunakan judul video
                            if ' - ' in video_stem:
                                channel_name = video_stem.split(' - ')[0]
                                # Remove video ID if present (pattern: [xxxxx] at end)
                                channel_name = channel_name.split('[')[0].strip()

                    # Jika tetap gagal, gunakan placeholder yang aman
                    if not channel_name:
                        channel_name = "Unknown Channel"
                    
                    # Create credit text (hanya nama channel, bukan judul video)
                    credit_text = f"Source: {channel_name}"
                    
                    print(f"  [SOURCE CREDIT] Adding: {credit_text}")
                    
                    # Font settings
                    credit_font_name = self.parent.custom_settings.get("source_credit_font", "Arial")
                    credit_size = int(self.parent.custom_settings.get("source_credit_fontsize", 17) * 10)  # Scale for 1080p (match watermark/overlay)
                    
                    # Map Font Name to File
                    from modules.font_manager import VIRAL_FONTS
                    font_path = None
                    
                    # 1. Try Viral Fonts (Assets)
                    if credit_font_name in VIRAL_FONTS:
                        local_font = f"assets/fonts/{VIRAL_FONTS[credit_font_name][1]}"
                        if os.path.exists(local_font):
                            font_path = local_font
                    
                    # 2. Try Direct Filename match
                    if not font_path:
                        candidate = f"assets/fonts/{credit_font_name}.ttf"
                        if os.path.exists(candidate):
                            font_path = candidate
                    
                    # 3. Fallback to Safe Asset Font
                    if not font_path:
                        fallback = "assets/fonts/Roboto-Bold.ttf"
                        if os.path.exists(fallback):
                            font_path = fallback
                        else:
                            try:
                                import glob
                                found = glob.glob("assets/fonts/*.ttf")
                                if found: font_path = found[0]
                            except: pass
                    
                    if font_path:
                        font_abs = os.path.abspath(font_path).replace("\\", "/").replace(":", "\\:").replace("'", "")
                    else:
                        font_abs = "arial.ttf"
                    
                    # Color and opacity
                    credit_col = self.parent.custom_settings.get("source_credit_color", "#FFFFFF").replace("#", "0x")
                    credit_op = self.parent.custom_settings.get("source_credit_opacity", 80) / 100.0
                    
                    # Position preset
                    position = self.parent.custom_settings.get("source_credit_position", "bottom-right")
                    offset_x = self.parent.custom_settings.get("source_credit_pos_x", 50)
                    offset_y = self.parent.custom_settings.get("source_credit_pos_y", 100)
                    
                    # Calculate position based on preset
                    if position == "top-left":
                        x_expr = f"{offset_x}"
                        y_expr = f"{offset_y}"
                    elif position == "top-right":
                        x_expr = f"W-text_w-{offset_x}"
                        y_expr = f"{offset_y}"
                    elif position == "bottom-left":
                        x_expr = f"{offset_x}"
                        y_expr = f"H-text_h-{offset_y}"
                    else:  # bottom-right (default)
                        x_expr = f"W-text_w-{offset_x}"
                        y_expr = f"H-text_h-{offset_y}"
                    
                    # Escape text
                    safe_credit_text = credit_text.replace(":", "\\:").replace("'", "")
                    
                    # Add drawtext filter
                    fc_str += f"{last_v_label}drawtext=text='{safe_credit_text}':fontfile='{font_abs}':fontsize={credit_size}:fontcolor={credit_col}@{credit_op}:x={x_expr}:y={y_expr}[v_credit];"
                    last_v_label = "[v_credit]"
                    
                except Exception as e:
                    print(f"  [SOURCE CREDIT ERROR] {e}")

            # Legacy: no FPS or timestamp manipulation — pipe ends at [v_out] (no trailing semicolon)
            fc_str += f"{last_v_label}[v_out]"
            # Full video chain (no audio) — for CPU fallback so we keep mode 9:16 + watermark, avoid anull/aresample
            fc_str_video_only = fc_str

            # --- AUDIO PITCH (optional) ---
            # aresample=async=1:first_pts=0 keeps audio in sync with video
            pitch_enabled = self.parent.custom_settings.get("audio_pitch_enabled", False)
            pitch_semitones = float(self.parent.custom_settings.get("audio_pitch_semitones", 0))
            pitch_semitones = max(-4, min(4, pitch_semitones))
            if pitch_enabled and pitch_semitones != 0:
                rate_in = 48000 * (2 ** (pitch_semitones / 12.0))
                print(f"  [AUDIO PITCH] {pitch_semitones:+.1f} semitones -> asetrate={rate_in:.0f},aresample=48000")
                fc_str += ";" + f"{audio_filter}[a_pitch_in];[a_pitch_in]asetrate={rate_in:.0f},aresample=48000[a_sync];[a_sync]aresample=async=1:first_pts=0[a_out]"
            else:
                fc_str += ";" + f"{audio_filter}[a_sync];[a_sync]aresample=async=1:first_pts=0[a_out]"

            # Minimal and ultra-minimal: only scale + -map 0:a — must always succeed on any FFmpeg build
            minimal_fc_str_video_only = "[0:v]scale=1080:1920[v_out]"
            ultra_minimal_fc = "[0:v]scale=1080:1920[v_out]"
            # With audio in graph (for non-minimal path): base + passthrough to [v_out] then audio
            minimal_fc_str = base_fc_str + "[v_mixed]scale=iw:ih[v_out];" + audio_filter + "[a_sync];[a_sync]aresample=async=1:first_pts=0[a_out]"
                
            # GPU vs CPU pipeline
            use_pure_gpu = use_pure_gpu_possible and not has_heavy_filters and base_supports_gpu
            use_cpu = not use_pure_gpu
            use_video_only_minimal = False

            filter_complex_cpu = None  # for NVENC fallback
            if use_pure_gpu:
                # Pure GPU: decode(GPU) -> scale_cuda/crop_cuda -> NVENC. No hwdownload/hwupload.
                filter_complex = fc_str
                print("  [GPU] Pure pipeline: NVDEC + scale_cuda/crop_cuda + NVENC")
            elif use_pure_gpu_possible and not has_heavy_filters and not base_supports_gpu:
                # GPU decode/encode with CPU filters (hwdownload -> filters -> hwupload)
                filter_complex_cpu = fc_str  # save for fallback when NVENC fails
                fc_str = "[0:v]hwdownload,format=nv12[v0];" + fc_str.replace("[0:v]", "[v0]")
                fc_str = fc_str.replace(f"{last_v_label}[v_out]", f"{last_v_label}hwupload_cuda[v_out]")
                filter_complex = fc_str
                use_cpu = False  # Still using NVENC
                print("  [GPU] Hybrid: NVDEC + CPU filters + NVENC")
            else:
                # CPU fallback: full video chain (mode 9:16 + zoom/subtitle/watermark jika tersedia), audio via -map 0:a
                use_video_only_minimal = True
                filter_complex = fc_str_video_only
                filter_complex_cpu = fc_str_video_only
                use_cpu = True
                if has_heavy_filters:
                    print("  [CPU] Fallback: chain video penuh (mode 9:16 + watermark jika drawtext ada), audio direct.")
            use_gpu_encode = use_pure_gpu or (use_pure_gpu_possible and not use_cpu)

            def get_ffmpeg_cmd(force_cpu=False):
                if effective_video_path != str(self.parent.video_path):
                    pad_start = effective_start
                    pad_duration = effective_duration
                else:
                    pad_start = max(0, result['start'] - 0.2)
                    pad_end = result['start'] + duration + 0.2
                    pad_duration = pad_end - pad_start
                first_input = input_args[:2]
                rest_inputs = input_args[2:] if len(input_args) > 2 else []
                use_gpu_this = use_gpu_encode and not force_cpu
                fc = (filter_complex_cpu if force_cpu and filter_complex_cpu else filter_complex)
                fc = finalize_filter_graph(fc)
                print("FFMPEG FILTER GRAPH:")
                print(fc)
                hwaccel = ['-hwaccel', 'cuda', '-hwaccel_output_format', 'cuda'] if use_gpu_this else []
                if effective_video_path == str(self.parent.video_path):
                    print(f"  [CLIP-FIRST] Processing only {pad_duration:.1f}s segment (no full-video decode)")
                map_a = '0:a' if use_video_only_minimal else '[a_out]'
                base_cmd = [
                    'ffmpeg', '-y', '-fflags', '+genpts', '-avoid_negative_ts', 'make_zero',
                    '-ss', str(pad_start), '-t', str(pad_duration),
                    *hwaccel, *first_input,
                    *rest_inputs,
                    '-filter_complex', fc,
                    '-map', '[v_out]', '-map', map_a,
                    '-max_muxing_queue_size', '1024',
                ]
                if use_gpu_this:
                    base_cmd.extend([
                        '-c:v', 'h264_nvenc', '-preset', 'p5', '-tune', 'hq',
                        '-rc:v', 'vbr', '-cq:v', '19', '-b:v', '6M', '-maxrate', '10M', '-bufsize', '12M',
                        '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
                        str(output_path)
                    ])
                else:
                    base_cmd.extend([
                        '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
                        '-maxrate', '8M', '-c:a', 'aac', '-b:a', '192k', '-ar', '48000',
                        str(output_path)
                    ])
                return base_cmd

            # Execution logic with real-time feedback
            def run_ffmpeg_realtime(cmd, description, encode_duration=None, encoder_label=""):
                enc_info = f" ({encoder_label})" if encoder_label else ""
                self._progress(50, f"Mengode video{enc_info}...")
                print(f"  [{description}] Executing FFmpeg...")
                print("FFMPEG COMMAND:")
                print(" ".join(cmd))
                import sys # Import sys for platform check
                import re
                time_pat = re.compile(r'time=(\d+):(\d+):(\d+)\.(\d+)')
                try:
                    # Use Popen to capture output in real-time
                    if sys.platform == 'win32':
                        startupinfo = subprocess.STARTUPINFO()
                        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        process = subprocess.Popen(
                            cmd, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.STDOUT, 
                            universal_newlines=True,
                            encoding='utf-8', 
                            errors='replace',
                            startupinfo=startupinfo,
                            creationflags=0x08000000 
                        )
                    else:
                        process = subprocess.Popen(
                            cmd, 
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.STDOUT, 
                            universal_newlines=True,
                            encoding='utf-8',
                            errors='replace'
                        )
                    
                    err_lines = []
                    for line in process.stdout:
                        line = line.strip()
                        if line:
                            if "Error" in line or "error" in line or "Cannot" in line or "nvenc" in line.lower():
                                err_lines.append(line[:300])
                            # Parse time= for progress (50-98%)
                            if encode_duration and encode_duration > 0 and "time=" in line:
                                m = time_pat.search(line)
                                if m:
                                    h, mn, s, ms = int(m.group(1)), int(m.group(2)), int(m.group(3)), int(m.group(4))
                                    elapsed = h * 3600 + mn * 60 + s + ms / 1000.0
                                    pct = 50 + int(48 * min(1.0, elapsed / encode_duration))
                                    self._progress(pct, f"Mengode video{enc_info}... {int(elapsed)}s")
                            if any(k in line for k in ["frame=", "time=", "size=", "speed="]):
                                print(f"    [FFMPEG] {line}", end='\r')
                            elif "Error" in line or "error" in line:
                                print(f"    [FFMPEG ERROR] {line}")
                    
                    process.wait()
                    print("")
                    if process.returncode != 0 and err_lines:
                        print(f"  [FFMPEG FAIL] Exit {process.returncode}, last errors:")
                        for e in err_lines[-5:]:
                            print(f"    {e}")
                    return process.returncode
                    
                except Exception as e:
                    print(f"  [EXEC ERROR] Failed to run ffmpeg: {e}")
                    return -1

            # Compute encode duration for progress (used in run_ffmpeg_realtime)
            encode_dur = effective_duration if effective_video_path != str(self.parent.video_path) else duration + 0.4

            if use_gpu_encode:
                print("  Using NVENC GPU encoder")
                cmd = get_ffmpeg_cmd()
                ret_code = run_ffmpeg_realtime(cmd, "GPU-NVENC", encode_dur, encoder_label="NVENC GPU")
                if ret_code == 0:
                    self._progress(100, "Selesai (NVENC)")
                    print(f"  [SUCCESS] Klip {clip_num or ''} berhasil diekspor (GPU)")
                    if clip_num is None:
                        _safe_messagebox("info", "Berhasil", f"Klip berhasil diekspor (GPU):\n{output_filename}")
                    return True
                print(f"  [GPU] NVENC gagal (exit {ret_code}). Mencoba fallback CPU (libx264)...")
                if filter_complex_cpu is not None:
                    self._progress(45, "Fallback CPU encoding...")
                    cmd_cpu = get_ffmpeg_cmd(force_cpu=True)
                    ret_cpu = run_ffmpeg_realtime(cmd_cpu, "CPU-x264", encode_dur, encoder_label="libx264 CPU")
                    if ret_cpu == 0:
                        self._progress(100, "Selesai (CPU)")
                        print(f"  [SUCCESS] Klip {clip_num or ''} berhasil diekspor (CPU fallback)")
                        if clip_num is None:
                            _safe_messagebox("info", "Berhasil", f"Klip berhasil diekspor (CPU):\n{output_filename}")
                        return True
                if clip_num is None:
                    _safe_messagebox("error", "Kesalahan", "NVENC gagal dan fallback CPU tidak tersedia. Cek log konsol.")
                return False

            print(f"  [CPU] Mengekspor dengan libx264...")
            cmd = get_ffmpeg_cmd()
            ret_code = run_ffmpeg_realtime(cmd, "CPU-x264", encode_dur, encoder_label="libx264 CPU")
            if ret_code == 0:
                self._progress(100, "Selesai (CPU libx264)")
                print(f"  [SUCCESS] Klip {clip_num or ''} berhasil diekspor (CPU)")
                if clip_num is None:
                    _safe_messagebox("info", "Berhasil", f"Klip berhasil diekspor (CPU):\n{output_filename}")
                return True
            # Retry 1: minimal video-only (mode 9:16, setsar/crop/scale/pad), audio -map 0:a
            print(f"  [CPU] Filter not found? Mencoba export minimal (mode 9:16)...")
            filter_complex = minimal_fc_str_video_only
            filter_complex_cpu = minimal_fc_str_video_only
            cmd_min = get_ffmpeg_cmd()
            ret_min = run_ffmpeg_realtime(cmd_min, "CPU-x264-minimal", encode_dur, encoder_label="libx264 CPU")
            if ret_min == 0:
                self._progress(100, "Selesai (CPU minimal)")
                print(f"  [SUCCESS] Klip {clip_num or ''} berhasil diekspor (CPU, filter minimal)")
                if clip_num is None:
                    _safe_messagebox("info", "Berhasil", f"Klip berhasil diekspor (tanpa zoom/subtitle/watermark):\n{output_filename}")
                return True
            # Retry 2: ultra-minimal — HANYA scale (tanpa setsar/crop/pad), pasti jalan di semua FFmpeg
            print(f"  [CPU] Filter not found lagi. Mencoba ultra-minimal (hanya scale 9:16)...")
            filter_complex = ultra_minimal_fc
            filter_complex_cpu = ultra_minimal_fc
            cmd_ultra = get_ffmpeg_cmd()
            ret_ultra = run_ffmpeg_realtime(cmd_ultra, "CPU-x264-ultra-minimal", encode_dur, encoder_label="libx264 CPU")
            if ret_ultra == 0:
                self._progress(100, "Selesai (ultra-minimal)")
                print(f"  [SUCCESS] Klip {clip_num or ''} berhasil diekspor (hanya scale 9:16)")
                if clip_num is None:
                    _safe_messagebox("info", "Berhasil", f"Klip berhasil diekspor (mode ultra-minimal 9:16):\n{output_filename}")
                return True
            print(f"  [ERROR] Ekspor gagal total.")
            if clip_num is None:
                _safe_messagebox("error", "Kesalahan", "Gagal mengekspor klip. Cek log konsol.")
            return False
                    
        except Exception as e:
            if clip_num is None:
                _safe_messagebox("error", "Kesalahan", f"Gagal mengekspor klip: {str(e)}")
            print(f"  [EXPORT ERROR] {e}")
            import traceback
            traceback.print_exc()
            return False


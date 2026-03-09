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

# Import export pipeline (filter build + FFmpeg run + fallbacks)
try:
    from modules.export_pipeline import export_clip
    EXPORT_PIPELINE_AVAILABLE = True
except ImportError:
    EXPORT_PIPELINE_AVAILABLE = False


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
    """Web/headless: no GUI. Just log. Desktop could inject a real messagebox if needed."""
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


            # Construct Filter Complex — delegate to export_pipeline
            _raw_mode = self.parent.custom_settings.get("export_mode", "landscape_fit")
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

            # Podcast Smart: pre-process video with per-frame active-speaker crop (sets effective_*)
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

            if not EXPORT_PIPELINE_AVAILABLE:
                print("  [ERROR] Export pipeline not available.")
                if clip_num is None:
                    _safe_messagebox("error", "Kesalahan", "Modul export pipeline tidak tersedia.")
                return False
            return export_clip(
                input_video=str(self.parent.video_path),
                output_video=str(output_path),
                start=result["start"],
                duration=duration,
                mode=export_mode,
                subtitles=ass_path,
                voiceover_path=voiceover_path,
                bgm_file_path=bgm_file_path if has_bgm else None,
                custom_settings=self.parent.custom_settings,
                parent=self.parent,
                effective_video_path=effective_video_path,
                effective_start=effective_start,
                effective_duration=effective_duration,
                progress_callback=self._progress,
                clip_num=clip_num,
                output_filename=output_filename,
                safe_messagebox=_safe_messagebox,
            )
                    
        except Exception as e:
            if clip_num is None:
                _safe_messagebox("error", "Kesalahan", f"Gagal mengekspor klip: {str(e)}")
            print(f"  [EXPORT ERROR] {e}")
            import traceback
            traceback.print_exc()
            return False


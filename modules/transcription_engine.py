"""
Transcription Engine Module
Handles audio/video transcription using Whisper (local)
"""

import os
import subprocess
import tempfile
from pathlib import Path

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

try:
    import torch
    CUDA_AVAILABLE = torch.cuda.is_available()
except Exception:
    CUDA_AVAILABLE = False

# [PART 6] Load Whisper model once and reuse across transcriptions (lazy load on first use)
# Shared cache for transcription_engine and subtitle_engine (karaoke)
_whisper_model_cache = None
_whisper_model_key = None  # (model_name, device, download_root) to detect config change


def get_cached_whisper_model(model_name: str, device: str, download_root=None):
    """Load Whisper model once and cache; reuse on subsequent calls. Use from any module."""
    global _whisper_model_cache, _whisper_model_key
    key = (model_name, device, download_root)
    if _whisper_model_cache is not None and _whisper_model_key == key:
        return _whisper_model_cache
    if not WHISPER_AVAILABLE:
        return None
    kwargs = {"device": device}
    if download_root:
        kwargs["download_root"] = download_root
    model = whisper.load_model(model_name, **kwargs)
    _whisper_model_cache = model
    _whisper_model_key = key
    return model


class TranscriptionEngine:
    """Manages all transcription operations for audio and video files"""
    
    def __init__(self, parent):
        """
        Initialize Transcription Engine
        
        Args:
            parent: Reference to YouTubeHeatmapAnalyzer instance for accessing settings
        """
        self.parent = parent
    
    def _get_whisper_model(self, model_name: str, device: str):
        """Load Whisper model once and cache; reuse on subsequent calls."""
        return get_cached_whisper_model(model_name, device)
    
    def transcribe_video_with_whisper(self, video_path):
        """
        [OFFLINE EARS]
        Uses OpenAI Whisper to transcribe video locally.
        Fallback when APIs fail or manual upload has no transcript.
        """
        if not WHISPER_AVAILABLE:
            print("  [WHISPER] Library not installed. Skipping.")
            return None
            
        print("\n" + "="*40)
        print("[WHISPER] Mulai Transkripsi Offline...")
        print("="*40)
        
        try:
            # 1. Extract Audio
            self.parent.progress_var.set("Whisper: Mengekstrak audio...")
            audio_path = Path("temp") / "whisper_temp.wav"
            
            # Use ffmpeg to extract audio (16k Hz mono for Whisper)
            cmd = [
                'ffmpeg', '-y',
                '-i', str(video_path),
                '-ar', '16000',
                '-ac', '1', 
                '-c:a', 'pcm_s16le',
                str(audio_path)
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)
            
            if not audio_path.exists():
                print("  [WHISPER] Gagal ekstrak audio.")
                return None
                
            # 2. Load Model & Transcribe (GPU if CUDA available for RTX 3060 etc., else CPU)
            self.parent.progress_var.set("Whisper: Mendengarkan video...")
            device = "cuda" if CUDA_AVAILABLE else "cpu"
            model_name = "small" if device == "cuda" else "tiny"
            print(f"  [WHISPER] Using model '{model_name}' on {device} (cached)")
            model = self._get_whisper_model(model_name, device)
            
            self.parent.progress_var.set("Whisper: Sedang mengetik transkrip...")
            if device == "cuda":
                print("  [WHISPER] Memproses di GPU (NVIDIA CUDA)...")
            else:
                print("  [WHISPER] Memproses di CPU (20-50% durasi video)...")
            
            result = model.transcribe(str(audio_path), verbose=False, fp16=(device == "cuda"))
            full_text = result["text"]
            
            print(f"  [WHISPER] Selesai! {len(full_text)} karakter terdeteksi.")
            
            # Cleanup
            try: audio_path.unlink()
            except: pass
            
            return full_text
            
        except Exception as e:
            print(f"  [WHISPER FAILED] {e}")
            return None

    def transcribe_to_segments(self, video_path):
        """
        Transcribe video with Whisper, return dict {idx: {start, end, text}} for AI analysis.
        Uses CUDA when available for faster processing.
        """
        if not WHISPER_AVAILABLE:
            return None
        try:
            audio_path = Path("temp") / "whisper_temp.wav"
            audio_path.parent.mkdir(parents=True, exist_ok=True)
            cmd = [
                "ffmpeg", "-y", "-i", str(video_path),
                "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
                str(audio_path)
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000 if os.name == "nt" else 0)
            if not audio_path.exists():
                return None

            device = "cuda" if CUDA_AVAILABLE else "cpu"
            model_name = "medium" if device == "cuda" else "small"
            models_root = os.path.join(os.getcwd(), "assets", "models")
            os.makedirs(models_root, exist_ok=True)
            if self.parent and hasattr(self.parent, "progress_var"):
                self.parent.progress_var.set(f"Whisper ({device}): Transcribing...")
            print(f"  [WHISPER] Using '{model_name}' on {device} (fp16)")
            model = self._get_whisper_model(model_name, device, download_root=models_root)
            result = model.transcribe(str(audio_path), verbose=False, fp16=(device == "cuda"))
            try:
                audio_path.unlink(missing_ok=True)
            except Exception:
                pass

            segments = result.get("segments") or []
            out = {}
            for i, s in enumerate(segments):
                if s.get("text", "").strip():
                    out[i] = {"start": float(s.get("start", 0)), "end": float(s.get("end", 0)), "text": s["text"].strip()}
            return out if out else None
        except Exception as e:
            print(f"  [WHISPER SEGMENTS FAILED] {e}")
            return None

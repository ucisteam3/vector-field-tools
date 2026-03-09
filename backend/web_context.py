"""
Web App Context - Mimics YouTubeHeatmapAnalyzer interface for headless backend use.
All modules expect a 'parent' with specific attributes; this adapter provides them without Tkinter.
"""

import os
import sys
from pathlib import Path
from datetime import timedelta

# Add project root so modules can be imported
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


class MockVar:
    """Mock Tkinter variable for use without GUI"""
    def __init__(self, value=None):
        self._value = value

    def get(self):
        return self._value

    def set(self, value):
        self._value = value


class WebAppContext:
    """
    Headless context that provides the same interface as YouTubeHeatmapAnalyzer
    for the analysis_orchestrator, clip_exporter, and related modules.
    """
    def __init__(self, project_dir: Path, on_progress=None, preferred_ai_provider: str = None):
        self.project_dir = Path(project_dir)
        self.preferred_ai_provider = (preferred_ai_provider or "").strip().lower() or None
        self.video_path = None
        self.current_video_path = None
        self.analysis_results = []
        self.sub_transcriptions = {}
        self.video_title = "Unknown"
        self.channel_name = "Unknown"
        self.on_progress = on_progress or (lambda msg: None)

        # Mock Tkinter variables (modules expect these)
        self.progress_var = MockVar("Ready")
        self.gpu_var = MockVar(True)
        self.use_voiceover_var = MockVar(False)
        self.trend_keyword_var = MockVar("")
        self.subtitle_enabled_var = MockVar(False)
        self.advanced_ai_enabled = MockVar(True)
        self.results_sort_var = MockVar("Skor")

        # Settings - load from config or use defaults (never crash export)
        try:
            from modules.settings_manager import load_settings
            self.custom_settings = load_settings()
        except Exception as e:
            print(f"[WebAppContext] load_settings failed: {e}")
            self.custom_settings = {}
        self.custom_settings.setdefault("export_mode", "face_tracking")
        self.custom_settings.setdefault("watermark_enabled", False)
        self.custom_settings.setdefault("subtitle_enabled", False)

        # Mock root for modules that call root.after()
        self.root = MockRoot(self)

        # Cookie/config paths - SAMA dengan desktop app (absolute path)
        self.last_full_path = None
        cookie_default = PROJECT_ROOT / "www.youtube.com_cookies.txt"
        if cookie_default.exists():
            self.last_full_path = str(cookie_default.resolve())
        self.local_video_mode = False

        # Config/API state (for AI modules)
        self.api_keys = {
            "openai": [],
            "gemini": [],
            "anthropic": [],
            "llama": [],
            "deepseek": [],
            "groq": [],
        }
        self.api_key_state = {
            "openai_idx": 0,
            "gemini_idx": 0,
            "anthropic_idx": 0,
            "llama_idx": 0,
            "deepseek_idx": 0,
            "groq_idx": 0,
        }
        self.rotate_on_error = {
            "openai": True,
            "gemini": True,
            "anthropic": True,
            "llama": True,
            "deepseek": True,
            "groq": True,
        }

        # Back-compat fields used by older modules
        self.user_gemini_keys = []
        self.current_gemini_idx = 0
        self.rotate_gemini = MockVar(True)
        self.gemini_available = False
        self.gemini_client = None
        self.current_genre = MockVar("Umum")
        self.current_style = MockVar("Entertainment")
        self.openai_available = False
        self.gemini_keys = []
        self.current_transcript_path = None
        # All AI providers (only the selected one is used for analysis)
        self.anthropic_available = False
        self.llama_available = False
        self.deepseek_available = False
        self.groq_available = False

        # Load config (never crash export)
        try:
            self._load_config()
        except Exception as e:
            print(f"[WebAppContext] _load_config failed: {e}")
        # When user selected an API provider for this run, only that provider is "available"
        preferred = (self.preferred_ai_provider or "").strip().lower()
        if preferred:
            self.openai_available = preferred == "openai" and bool(self.api_keys.get("openai"))
            self.gemini_available = preferred == "gemini" and bool(self.api_keys.get("gemini"))
            self.anthropic_available = preferred == "anthropic" and bool(self.api_keys.get("anthropic"))
            self.llama_available = preferred == "llama" and bool(self.api_keys.get("llama"))
            self.deepseek_available = preferred == "deepseek" and bool(self.api_keys.get("deepseek"))
            self.groq_available = preferred == "groq" and bool(self.api_keys.get("groq"))
            if preferred != "gemini":
                self.gemini_client = None
        else:
            # No preference: all with keys are available; AIEngine will use OpenAI if present
            self.anthropic_available = bool(self.api_keys.get("anthropic"))
            self.llama_available = bool(self.api_keys.get("llama"))
            self.deepseek_available = bool(self.api_keys.get("deepseek"))
            self.groq_available = bool(self.api_keys.get("groq"))
        # Single flag for "run title/hook/segment AI" when any provider is available
        self.has_ai_provider = (
            self.openai_available or self.gemini_available or self.anthropic_available
            or self.llama_available or self.deepseek_available or self.groq_available
        )
        try:
            self._init_modules()
        except Exception as e:
            print(f"[WebAppContext] _init_modules failed: {e}")

    def _init_modules(self):
        """Lazy init slots - attributes set to None, populated on first property access"""
        self._download_manager = None
        self._ai_segment_analyzer = None
        self._video_analyzer = None
        self._clip_exporter = None
        self._subtitle_parser = None
        self._transcription_engine = None
        self._analysis_orchestrator = None
        self._ai_engine = None

    def _load_config(self):
        """Load config.json and initialize APIs for headless use"""
        config_path = PROJECT_ROOT / "config.json"
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    cfg = __import__("json").load(f)
                # API keys (new format)
                api = cfg.get("api_keys") or {}
                for k in ["openai", "gemini", "anthropic", "llama", "deepseek", "groq"]:
                    v = api.get(k) or []
                    if isinstance(v, list):
                        self.api_keys[k] = [str(x).strip() for x in v if str(x).strip()]

                st = cfg.get("api_key_state") or {}
                for k in list(self.api_key_state.keys()):
                    if k in st:
                        try:
                            self.api_key_state[k] = int(st.get(k) or 0)
                        except Exception:
                            pass

                rot = cfg.get("rotate_on_error") or {}
                for k in list(self.rotate_on_error.keys()):
                    if k in rot:
                        self.rotate_on_error[k] = bool(rot.get(k))

                # Back-compat: keep older fields populated
                self.user_gemini_keys = cfg.get("user_gemini_keys", []) or self.api_keys.get("gemini", [])
                self.current_gemini_idx = int(cfg.get("current_gemini_idx", self.api_key_state.get("gemini_idx", 0)) or 0)
                self.rotate_gemini.set(bool(cfg.get("rotate_gemini", self.rotate_on_error.get("gemini", True))))
                cfg_path = cfg.get("last_full_path")
                if cfg_path and os.path.exists(cfg_path):
                    self.last_full_path = cfg_path
                elif not self.last_full_path:
                    default_cookie = PROJECT_ROOT / "www.youtube.com_cookies.txt"
                    if default_cookie.exists():
                        self.last_full_path = str(default_cookie)
                self.current_genre.set(cfg.get("current_genre", "Umum"))
                self.current_style.set(cfg.get("current_style", "Entertainment"))
                self.gemini_keys = self.user_gemini_keys
                if self.user_gemini_keys:
                    try:
                        from google import genai
                        # Do not always start from index 0; resume from last known idx
                        if self.current_gemini_idx >= len(self.user_gemini_keys):
                            self.current_gemini_idx = 0
                        self.gemini_client = genai.Client(api_key=self.user_gemini_keys[self.current_gemini_idx])
                        self.gemini_available = True
                    except Exception:
                        pass
            except Exception as e:
                print(f"[WEB] Config load: {e}")
        # OpenAI from config.json (preferred) or openai.txt (fallback)
        if self.api_keys.get("openai"):
            self.openai_available = True
        # Fallback to openai.txt for compatibility
        openai_path = PROJECT_ROOT / "openai.txt"
        if openai_path.exists():
            try:
                key = openai_path.read_text().strip()
                if key:
                    self.openai_available = True
            except Exception:
                pass

    def _save_config_partial(self, patch: dict):
        """Merge patch into config.json. Best-effort, never crash export."""
        try:
            cfg_path = PROJECT_ROOT / "config.json"
            cfg = {}
            if cfg_path.exists():
                cfg = __import__("json").loads(cfg_path.read_text(encoding="utf-8"))
            cfg.update(patch)
            cfg_path.write_text(__import__("json").dumps(cfg, indent=4, ensure_ascii=False), encoding="utf-8")
        except Exception:
            pass

    def download_progress_hook(self, d):
        """Progress hook for yt-dlp - reports download % to on_progress"""
        if not self.on_progress:
            return
        if d.get("status") == "downloading":
            p = d.get("_percent_str", "0%")
            self.on_progress(f"Downloading... {p}")
        elif d.get("status") == "finished":
            self.on_progress("Download complete, preparing...")

    @property
    def download_manager(self):
        if getattr(self, "_download_manager", None) is None:
            from modules.download_manager import DownloadManager
            self._download_manager = DownloadManager(self)
        return self._download_manager

    @property
    def ai_engine(self):
        if not hasattr(self, "_ai_engine") or self._ai_engine is None:
            from modules.ai_engine import AIEngine
            self._ai_engine = AIEngine(self)
        return self._ai_engine

    @property
    def ai_segment_analyzer(self):
        if getattr(self, "_ai_segment_analyzer", None) is None:
            from modules.ai_segment_analyzer import AISegmentAnalyzer
            self._ai_segment_analyzer = AISegmentAnalyzer(self)
        return self._ai_segment_analyzer

    @property
    def video_analyzer(self):
        if getattr(self, "_video_analyzer", None) is None:
            from modules.video_analyzer import VideoAnalyzer
            self._video_analyzer = VideoAnalyzer(self)
        return self._video_analyzer

    @property
    def clip_exporter(self):
        if getattr(self, "_clip_exporter", None) is None:
            from modules.clip_exporter import ClipExporter
            self._clip_exporter = ClipExporter(self)
        return self._clip_exporter

    @property
    def subtitle_parser(self):
        if getattr(self, "_subtitle_parser", None) is None:
            from modules.subtitle_parser import SubtitleParser
            self._subtitle_parser = SubtitleParser(self)
        return self._subtitle_parser

    @property
    def transcription_engine(self):
        if getattr(self, "_transcription_engine", None) is None:
            from modules.transcription_engine import TranscriptionEngine
            self._transcription_engine = TranscriptionEngine(self)
        return self._transcription_engine

    @property
    def analysis_orchestrator(self):
        if getattr(self, "_analysis_orchestrator", None) is None:
            from modules.analysis_orchestrator import AnalysisOrchestrator
            self._analysis_orchestrator = AnalysisOrchestrator(self)
        return self._analysis_orchestrator

    # --- Delegates ---
    def download_youtube_video(self, url):
        return self.download_manager.download_youtube_video(url)

    def download_subtitles_only(self, url, video_path):
        return self.download_manager.download_subtitles_only(url, video_path)

    def download_youtube_audio(self, url):
        return self.download_manager.download_youtube_audio(url)

    def find_sidecar_caption(self, video_path, video_id=None):
        return self.subtitle_parser.find_sidecar_caption(video_path, video_id)

    def _parse_json3(self, data):
        """Delegate to subtitle_parser for JSON3 parsing (used by download_manager)."""
        return self.subtitle_parser._parse_json3(data)

    def _fix_sub_overlaps(self, subs):
        """Delegate to subtitle_parser for overlap fixing."""
        return self.subtitle_parser._fix_sub_overlaps(subs)

    def _write_srt_from_data(self, data, out_path, max_words=8):
        """Delegate to subtitle_parser for SRT writing."""
        return self.subtitle_parser._write_srt_from_data(data, out_path, max_words)

    def _write_srt_from_segments(self, segments, out_path):
        """Delegate to subtitle_parser for SRT writing from segments."""
        return self.subtitle_parser._write_srt_from_segments(segments, out_path)

    def parse_vtt(self, path):
        return self.subtitle_parser.parse_vtt(path)

    def parse_manual_transcript(self, text):
        return self.subtitle_parser.parse_manual_transcript(text)

    def parse_structured_segments(self, text):
        return self.subtitle_parser.parse_structured_segments(text)

    def get_viral_segments_from_ai(self, raw_transcript, keyword=None):
        return self.ai_segment_analyzer.get_viral_segments_from_ai(raw_transcript, keyword=keyword)

    def extract_audio_and_transcribe(self, video_path):
        return self.video_analyzer.extract_audio_and_transcribe(video_path)

    def transcribe_audio_file(self, audio_path):
        return self.video_analyzer.transcribe_audio_file(audio_path)

    def transcribe_video_with_whisper(self, video_path):
        return self.transcription_engine.transcribe_video_with_whisper(video_path)

    def transcribe_to_segments(self, video_path):
        """Whisper with CUDA → {idx: {start, end, text}} for AI analysis."""
        return self.transcription_engine.transcribe_to_segments(video_path)

    def get_video_duration(self, video_path):
        return self.video_analyzer.get_video_duration(video_path)

    def _run_parallel_transcription(self, input_path, use_groq=False):
        return self.video_analyzer._run_parallel_transcription(input_path, use_groq)

    def detect_high_engagement_face(self, frame):
        return self.video_analyzer.detect_high_engagement_face(frame)

    def analyze_video_heatmap(self, video_path):
        return self.video_analyzer.analyze_video_heatmap(video_path)

    def match_segments_with_content(self, segments, transcriptions):
        return self.ai_segment_analyzer.match_segments_with_content(segments, transcriptions)

    def generate_segment_titles_parallel(self):
        return self.ai_segment_analyzer.generate_segment_titles_parallel()

    def format_time(self, seconds):
        return str(timedelta(seconds=int(seconds)))

    def clean_viral_title(self, title):
        if not title:
            return ""
        return self.ai_engine.clean_viral_title(title)

    def rotate_gemini_api_key(self):
        if not self.user_gemini_keys:
            return False
        self.current_gemini_idx = (self.current_gemini_idx + 1) % len(self.user_gemini_keys)
        try:
            from google import genai
            self.gemini_client = genai.Client(api_key=self.user_gemini_keys[self.current_gemini_idx])
            self.gemini_available = True
            # Persist idx so we don't always start from 0 next run
            self.api_key_state["gemini_idx"] = self.current_gemini_idx
            self._save_config_partial({"current_gemini_idx": self.current_gemini_idx, "api_key_state": self.api_key_state})
            return True
        except Exception:
            return False

    def get_openai_key(self) -> str | None:
        keys = self.api_keys.get("openai") or []
        if not keys:
            return None
        idx = int(self.api_key_state.get("openai_idx", 0) or 0)
        if idx >= len(keys):
            idx = 0
            self.api_key_state["openai_idx"] = 0
        return keys[idx]

    def _get_provider_key(self, provider: str) -> str | None:
        keys = self.api_keys.get(provider) or []
        if not keys:
            return None
        key_name = provider + "_idx"
        idx = int(self.api_key_state.get(key_name, 0) or 0)
        if idx >= len(keys):
            idx = 0
        return keys[idx]

    def get_anthropic_key(self) -> str | None:
        return self._get_provider_key("anthropic")

    def get_groq_key(self) -> str | None:
        return self._get_provider_key("groq")

    def get_deepseek_key(self) -> str | None:
        return self._get_provider_key("deepseek")

    def get_llama_key(self) -> str | None:
        return self._get_provider_key("llama")

    def rotate_openai_api_key(self) -> bool:
        """Rotate OpenAI key only when called on error."""
        keys = self.api_keys.get("openai") or []
        if not keys:
            return False
        idx = int(self.api_key_state.get("openai_idx", 0) or 0)
        idx = (idx + 1) % len(keys)
        self.api_key_state["openai_idx"] = idx
        self._save_config_partial({"api_key_state": self.api_key_state})
        return True

    def detect_viral_segments_with_openai(self, transcript):
        return self.ai_engine.detect_viral_segments_with_openai(transcript)

    def generate_clickbait_title(self, segment_text, existing_titles=None, max_attempts=3, strict_content=False):
        return self.ai_engine.generate_clickbait_title(segment_text, existing_titles, max_attempts, strict_content)

    def refine_and_score_hook_openai(self, hook_text, max_attempts=2):
        return self.ai_engine.refine_and_score_hook_openai(hook_text, max_attempts)

    def apply_hook_trigger_boost(self, hook_text, hook_score):
        return self.ai_engine.apply_hook_trigger_boost(hook_text, hook_score)

    def clear_results(self):
        self.analysis_results = []
        # No UI to clear

    def update_results_ui(self):
        # No-op for headless
        pass


class MockRoot:
    """Mock Tk root - modules call root.after() for deferred UI updates"""
    def __init__(self, ctx):
        self.ctx = ctx

    def after(self, ms, func, *args):
        # Execute immediately in headless mode (no GUI thread)
        if args:
            func(*args)
        else:
            func()

    def update(self):
        pass

    def update_idletasks(self):
        pass

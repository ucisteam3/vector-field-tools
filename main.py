import tkinter as tk
print("[DEBUG] main.py started execution...")
from tkinter import ttk, scrolledtext, messagebox, filedialog
import shutil
import threading
import os
import re
import time
import cv2
import numpy as np
from datetime import timedelta
import yt_dlp
import json
from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import speech_recognition as sr
from pydub import AudioSegment
import tempfile
from google import genai
import sys
import traceback
import random
import subprocess
from concurrent.futures import ThreadPoolExecutor
from modules.settings_manager import load_settings, save_settings
from modules.subtitle_engine import generate_karaoke_ass
from modules.font_manager import download_default_fonts, load_fonts_from_folder, FONT_DIR
from modules.preview_engine import render_subtitle_preview
print("[DEBUG] Importing FaceTracker...")
from modules.face_tracker import FaceTracker
print("[DEBUG] FaceTracker imported.")
from modules.ai_engine import AIEngine, VIRAL_TITLE_EXAMPLES
from modules.download_manager import DownloadManager
from modules.transcription_engine import TranscriptionEngine
from modules.subtitle_parser import SubtitleParser
from modules.ai_segment_analyzer import AISegmentAnalyzer
from modules.ui_components import CustomLogger, ModernButton
from modules.ui_setup import UISetup
from modules.video_analyzer import VideoAnalyzer
from modules.clip_exporter import ClipExporter
from modules.results_manager import ResultsManager
from modules.analysis_orchestrator import AnalysisOrchestrator
from modules.api_manager import APIManager
from modules.config_manager import ConfigManager
from modules.theme_manager import ThemeManager
try:
    import edge_tts
    EDGE_TTS_AVAILABLE = True
except ImportError:
    EDGE_TTS_AVAILABLE = False
import asyncio
import sys
import subprocess
import tempfile
import shutil
from concurrent.futures import ThreadPoolExecutor

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False

try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    print("[INFO] Whisper library not found. Installing automatically...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "openai-whisper"])
        import whisper
        WHISPER_AVAILABLE = True
        print("[SUCCESS] Whisper library installed successfully.")
    except Exception as e:
        print(f"[ERROR] Failed to install Whisper automatically: {e}")
        WHISPER_AVAILABLE = False

# [FIX] Use Local Temp Directory to avoid filling C: Drive
LOCAL_TEMP_DIR = os.path.join(os.getcwd(), "temp")
if not os.path.exists(LOCAL_TEMP_DIR):
    os.makedirs(LOCAL_TEMP_DIR)

# Note: VIRAL_TITLE_EXAMPLES is now imported from modules.ai_engine
# Note: YDL_Logger is now in modules.download_manager
# Note: CustomLogger and ModernButton from modules.ui_components


class ModernButton(tk.Canvas):
    def __init__(self, parent, text, command=None, width=150, height=40, radius=20, bg_color="#00d2ff", hover_color="#33e0ff", fg_color="#050608"):
        # Safely get parent background to blend in
        try:
            bg_val = parent["bg"]
        except:
            try:
                bg_val = parent.cget("background")
            except:
                bg_val = "#0a0c10" # Default app dark
        
        super().__init__(parent, width=width, height=height, bg=bg_val, highlightthickness=0)
        self.command = command
        self.width = width
        self.height = height
        self.radius = radius
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.fg_color = fg_color
        
        self.rect = self._draw_rounded_rect(0, 0, width, height, radius, bg_color)
        self.text = self.create_text(width/2, height/2, text=text, fill=fg_color, font=("Segoe UI", 10, "bold"))
        
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        
    def _draw_rounded_rect(self, x1, y1, x2, y2, r, color):
        points = [x1+r, y1, x1+r, y1, x2-r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y1+r, x2, y2-r, x2, y2-r, x2, y2, x2-r, y2, x2-r, y2, x1+r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y2-r, x1, y1+r, x1, y1+r, x1, y1]
        return self.create_polygon(points, fill=color, smooth=True)

    def _on_enter(self, event):
        self.itemconfig(self.rect, fill=self.hover_color)
        self.config(cursor="hand2")

    def _on_leave(self, event):
        self.itemconfig(self.rect, fill=self.bg_color)

    def _on_click(self, event):
        if self.command:
            self.command()

class YouTubeHeatmapAnalyzer:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Heatmap Analyzer")
        self.root.geometry("1200x800")
        
        # Set App Icon
        try:
            icon_path = os.path.abspath(os.path.join("assets", "img", "icon.png"))
            if os.path.exists(icon_path):
                from PIL import Image, ImageTk
                # Use PIL to support PNG properly and resize if needed
                icon_img = Image.open(icon_path)
                self.app_icon = ImageTk.PhotoImage(icon_img)
                self.root.iconphoto(True, self.app_icon)
        except Exception as e:
            print(f"[UI] Gagal memuat icon: {e}")

        self.root.state('zoomed') # Full screen by default
        
        # Modern Dark Theme Colors
        # Modern Dark Theme Colors - Premium Look
        self.bg_dark = "#0a0c10"  # Deep space black
        self.bg_darker = "#050608"  # Absolute black
        self.bg_lighter = "#161b22"  # GitHub-style dark gray
        self.fg_light = "#f0f6fc"  # Clean white
        self.fg_muted = "#8b949e"  # Gray text
        self.accent_blue = "#00d2ff"  # Vibrant Light Blue
        self.accent_blue_hover = "#33e0ff"
        self.accent_blue_active = "#00b8e6"
        self.accent_green = "#3fb950"  # Success green
        self.accent_orange = "#f0883e"  # Warning gold
        self.border_color = "#30363d"
        
        self.video_path = None
        self.current_video_path = None
        self.analysis_results = []
        self.is_analyzing = False
        
        # User API keys and settings
        self.user_gemini_keys = []
        self.rotate_gemini = tk.BooleanVar(value=True)
        self.current_gemini_idx = 0
        self.gemini_key_statuses = {} # Track [OK], [LIMIT], [ERROR]
        
        self.gpu_var = tk.BooleanVar(value=True) # Default True if user has GPU
        self.last_cookie_filename = "www.youtube.com_cookies.txt"
        self.last_full_path = None # Store full path of user provided cookie
        
        # Genre and Style selections
        self.genres = ["Umum", "Komedi", "Sports", "Podcast", "Finansial", "Kritik"]
        self.styles = ["Netral", "Sentimen", "Edukatif", "Entertainment", "Informatif", "Komedi"]
        self.current_genre = tk.StringVar(value="Umum")
        self.current_style = tk.StringVar(value="Entertainment")

        # Internal state
        self.gemini_available = False
        self.openai_available = False
        
        # System Spec Detection
        self.pc_level = "Kentang" # Default
        self.ram_gb = 0
        self.cpu_cores = os.cpu_count() or 1
        self.has_nvidia = False
        self.advanced_ai_enabled = tk.BooleanVar(value=False)
        self.use_voiceover_var = tk.BooleanVar(value=False) # Default OFF
        
        # Trend / keyword (untuk bias AI ke niche tertentu)
        self.trend_keyword_var = tk.StringVar(value="")
        
        # Load Persistent Settings (harus sebelum theme_mode_var / font_size_var)
        self.custom_settings = load_settings()
        
        # Theme & aksesibilitas (disimpan di settings)
        self.theme_mode_var = tk.StringVar(value=self.custom_settings.get("theme_mode", "dark"))
        self.font_size_var = tk.IntVar(value=self.custom_settings.get("ui_font_size", 10))
        
        # Hardcoded: Max 3 minutes for all clips (user request)
        # No UI dropdown needed - simplified workflow
        self.subtitle_enabled_var = tk.BooleanVar(value=self.custom_settings.get("subtitle_enabled", False))
        self.watermark_enabled_var = tk.BooleanVar(value=self.custom_settings.get("watermark_enabled", False))
        self.bgm_enabled_var = tk.BooleanVar(value=self.custom_settings.get("bgm_enabled", False))
        self.bgm_file_path_var = tk.StringVar(value=self.custom_settings.get("bgm_file_path", ""))


        # Watermark Vars
        self.watermark_type_var = tk.StringVar(value=self.custom_settings.get("watermark_type", "text"))
        self.watermark_text_var = tk.StringVar(value=self.custom_settings.get("watermark_text", "Sample Watermark"))
        self.watermark_font_var = tk.StringVar(value=self.custom_settings.get("watermark_font", "Arial"))
        self.watermark_size_var = tk.IntVar(value=self.custom_settings.get("watermark_size", 48))
        self.watermark_opacity_var = tk.IntVar(value=self.custom_settings.get("watermark_opacity", 80))
        self.watermark_color_var = tk.StringVar(value=self.custom_settings.get("watermark_color", "#FFFFFF"))
        self.watermark_outline_var = tk.StringVar(value=self.custom_settings.get("watermark_outline_color", "#000000"))
        self.watermark_outline_width_var = tk.IntVar(value=self.custom_settings.get("watermark_outline_width", 2))
        
        self.watermark_image_path_var = tk.StringVar(value=self.custom_settings.get("watermark_image_path", ""))
        self.watermark_scale_var = tk.IntVar(value=self.custom_settings.get("watermark_image_scale", 50))
        self.watermark_img_opacity_var = tk.IntVar(value=self.custom_settings.get("watermark_image_opacity", 100))
        
        self.watermark_pos_x_var = tk.IntVar(value=self.custom_settings.get("watermark_pos_x", 50))
        self.watermark_pos_y_var = tk.IntVar(value=self.custom_settings.get("watermark_pos_y", 50))
        
        # Overlay Vars (Second Watermark)
        self.overlay_enabled_var = tk.BooleanVar(value=self.custom_settings.get("overlay_enabled", False))
        self.overlay_type_var = tk.StringVar(value=self.custom_settings.get("overlay_type", "text"))
        self.overlay_text_var = tk.StringVar(value=self.custom_settings.get("overlay_text", "Sample Overlay"))
        self.overlay_font_var = tk.StringVar(value=self.custom_settings.get("overlay_font", "Arial"))
        self.overlay_size_var = tk.IntVar(value=self.custom_settings.get("overlay_size", 48))
        self.overlay_opacity_var = tk.IntVar(value=self.custom_settings.get("overlay_opacity", 80))
        self.overlay_color_var = tk.StringVar(value=self.custom_settings.get("overlay_color", "#FFFFFF"))
        self.overlay_outline_var = tk.StringVar(value=self.custom_settings.get("overlay_outline_color", "#000000"))
        self.overlay_outline_width_var = tk.IntVar(value=self.custom_settings.get("overlay_outline_width", 2))
        
        self.overlay_image_path_var = tk.StringVar(value=self.custom_settings.get("overlay_image_path", ""))
        self.overlay_scale_var = tk.IntVar(value=self.custom_settings.get("overlay_image_scale", 50))
        self.overlay_img_opacity_var = tk.IntVar(value=self.custom_settings.get("overlay_image_opacity", 100))
        
        self.overlay_pos_x_var = tk.IntVar(value=self.custom_settings.get("overlay_pos_x", 50))
        self.overlay_pos_y_var = tk.IntVar(value=self.custom_settings.get("overlay_pos_y", 200))
        
        # Export Mode Vars
        self.export_mode_var = tk.StringVar(value=self.custom_settings.get("export_mode", "landscape_fit"))
        self.face_tracking_smoothing_var = tk.IntVar(value=self.custom_settings.get("face_tracking_smoothing", 30))
        self.face_tracking_fallback_var = tk.StringVar(value=self.custom_settings.get("face_tracking_fallback", "center"))
        self.video_flip_var = tk.BooleanVar(value=self.custom_settings.get("video_flip_enabled", False))
        self.dynamic_zoom_var = tk.BooleanVar(value=self.custom_settings.get("dynamic_zoom_enabled", False))
        self.dynamic_zoom_strength_var = tk.DoubleVar(value=self.custom_settings.get("dynamic_zoom_strength", 1.4))
        self.dynamic_zoom_speed_var = tk.DoubleVar(value=self.custom_settings.get("dynamic_zoom_speed", 0.0012))
        self.audio_pitch_var = tk.BooleanVar(value=self.custom_settings.get("audio_pitch_enabled", False))
        self.audio_pitch_semitones_var = tk.DoubleVar(value=self.custom_settings.get("audio_pitch_semitones", 0))

        # Source Credit Vars
        self.source_credit_enabled_var = tk.BooleanVar(value=self.custom_settings.get("source_credit_enabled", False))
        self.source_credit_text_var = tk.StringVar(value=self.custom_settings.get("source_credit_text", "Source: Channel Name"))
        self.source_credit_font_var = tk.StringVar(value=self.custom_settings.get("source_credit_font", "Arial"))
        self.source_credit_fontsize_var = tk.IntVar(value=self.custom_settings.get("source_credit_fontsize", 24))
        self.source_credit_color_var = tk.StringVar(value=self.custom_settings.get("source_credit_color", "#FFFFFF"))
        self.source_credit_opacity_var = tk.IntVar(value=self.custom_settings.get("source_credit_opacity", 80))
        self.source_credit_position_var = tk.StringVar(value=self.custom_settings.get("source_credit_position", "bottom-right"))
        self.source_credit_pos_x_var = tk.IntVar(value=self.custom_settings.get("source_credit_pos_x", 50))
        self.source_credit_pos_y_var = tk.IntVar(value=self.custom_settings.get("source_credit_pos_y", 100))

        # Results list sort (Skor / Durasi / Mulai)
        self.results_sort_var = tk.StringVar(value="Skor")

        # Subtitle Vars
        self.sub_font_var = tk.StringVar(value=self.custom_settings.get("subtitle_font", "Arial"))
        self.sub_size_var = tk.IntVar(value=self.custom_settings.get("subtitle_fontsize", 24))
        self.sub_pos_var = tk.IntVar(value=self.custom_settings.get("subtitle_position_y", 50))
        
        # Migration: Check new key, then old key, then default
        text_col = self.custom_settings.get("subtitle_text_color")
        if not text_col:
            text_col = self.custom_settings.get("subtitle_primary_color", "#FFFFFF")
            
        self.sub_color_var = tk.StringVar(value=text_col)
        self.sub_outline_color_var = tk.StringVar(value=self.custom_settings.get("subtitle_outline_color", "#000000"))
        self.sub_highlight_color_var = tk.StringVar(value=self.custom_settings.get("subtitle_highlight_color", "#FFFF00"))

        # TRACE BINDING (Force update on change)
        self.sub_color_var.trace_add("write", lambda *args: self.update_preview())
        self.sub_outline_color_var.trace_add("write", lambda *args: self.update_preview())
        self.sub_highlight_color_var.trace_add("write", lambda *args: self.update_preview())
        
        # Watermark Traces
        self.watermark_color_var.trace_add("write", lambda *args: self.update_preview())
        self.watermark_outline_var.trace_add("write", lambda *args: self.update_preview())

        # [AUTOCLIP STYLE] Hardware Probing (moved before module init)
        self.best_encoder = None
        self.pc_tier = "kentang"
        
        # API Initializations (will be done after config load)

        
        # Initialize AI Engine Module
        self.ai_engine = AIEngine(self)
        print("[AI ENGINE] Initialized successfully")
        
        # Initialize Download Manager Module
        self.download_manager = DownloadManager(self)
        print("[DOWNLOAD MANAGER] Initialized successfully")
        
        # Initialize Transcription Engine Module
        self.transcription_engine = TranscriptionEngine(self)
        print("[TRANSCRIPTION ENGINE] Initialized successfully")
        
        # Initialize Subtitle Parser Module
        self.subtitle_parser = SubtitleParser(self)
        print("[SUBTITLE PARSER] Initialized successfully")
        
        # Initialize AI Segment Analyzer Module
        self.ai_segment_analyzer = AISegmentAnalyzer(self)
        print("[AI SEGMENT ANALYZER] Initialized successfully")
        
        # Initialize UI Setup Module
        self.ui_setup = UISetup(self)
        print("[UI SETUP] Initialized successfully")
        
        # Initialize Video Analyzer Module
        self.video_analyzer = VideoAnalyzer(self)
        print("[VIDEO ANALYZER] Initialized successfully")
        
        # Initialize Clip Exporter Module
        self.clip_exporter = ClipExporter(self)
        print("[CLIP EXPORTER] Initialized successfully")
        
        # Initialize Results Manager Module
        self.results_manager = ResultsManager(self)
        print("[RESULTS MANAGER] Initialized successfully")
        
        # Initialize Analysis Orchestrator Module
        self.analysis_orchestrator = AnalysisOrchestrator(self)
        print("[ANALYSIS ORCHESTRATOR] Initialized successfully")
        
        # Initialize API Manager Module
        self.api_manager = APIManager(self)
        print("[API MANAGER] Initialized successfully")
        
        # Initialize temp directory structure
        self.init_temp_folders()
        
        # Initialize Config Manager Module
        self.config_manager = ConfigManager(self)
        print("[CONFIG MANAGER] Initialized successfully")
        
        # Initialize Theme Manager Module
        self.theme_manager = ThemeManager(self)
        print("[THEME MANAGER] Initialized successfully")
        
        # Now load config after all managers are initialized
        self.load_config()
        
        # Initialize hardware probing
        self.best_encoder = self.probe_encoders()
        self.check_system_specs()
        
        # Initialize APIs
        self.initialize_gemini_api()
        self.openai_available = getattr(self.ai_engine, "openai_available", False)

        self.setup_dark_theme()
        
        # State variables
        self.local_video_mode = False # Initialize explicitly
        
        # Configure root expansion
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        self.setup_ui()
        
        # Font Auto-Download (Background)
        download_default_fonts()

        # Initialize text output redirection
        sys.stdout = CustomLogger(self.details_text)
        sys.stderr = sys.stdout
        
        # Terapkan tema & font dari settings (dark/light, aksesibilitas)
        try:
            mode = self.custom_settings.get("theme_mode", "dark")
            fs = self.custom_settings.get("ui_font_size", 10)
            self.theme_manager.apply_theme(mode, fs)
        except Exception:
            pass

    def probe_encoders(self):
        """
        [AUTOCLIP STYLE] Detect best FFmpeg hardware encoder
        Mimics the robust probing seen in other advanced tools.
        """
        print("\n" + "="*50)
        print("[HARDWARE PROBE] Mendeteksi Encoder Video Terbaik...")
        print("="*50)
        
        # 1. Check list of encoders
        try:
            res = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True, creationflags=0x08000000)
            output = res.stdout
            print(f"  [INFO] FFmpeg -encoders check: OK")
        except FileNotFoundError:
            print(f"  [ERROR] FFmpeg tidak ditemukan! Fallback ke CPU.")
            return 'libx264'
            
        # Priority list (NVIDIA > AMD > INTEL > MAC > CPU)
        candidates = [
            ('h264_nvenc', 'NVIDIA NVENC (Cepat & Tajam)'),
            ('h264_amf', 'AMD AMF (Radeon)'),
            ('h264_qsv', 'Intel QuickSync (iGPU)'),
            ('h264_videotoolbox', 'Apple M1/M2 VideoToolbox'),
        ]
        
        found_encoder = None
        
        for enc_id, friendly_name in candidates:
            if enc_id in output:
                print(f"  [INFO] Probe encoder: {friendly_name} ({enc_id}) ...")
                
                # 2. DUMMY CONVERSION TEST
                # Just seeing it in list isn't enough (phantom drivers). We must test it.
                dummy_test_cmd = [
                    'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=black:s=1280x720:d=1',
                    '-c:v', enc_id, '-f', 'null', '-'
                ]
                
                try:
                    # Run silent test
                    test_res = subprocess.run(dummy_test_cmd, capture_output=True, text=True, creationflags=0x08000000)
                    if test_res.returncode == 0:
                        print(f"  [SUCCESS] Probe BERHASIL! Menggunakan: {friendly_name}")
                        found_encoder = enc_id
                        self.best_encoder_name = friendly_name
                        break
                    else:
                        print(f"  [WARN] Probe GAGAL: {enc_id} ada di list, tapi error saat tes.")
                        # print(f"  -> Error details: {test_res.stderr[:200]}") # Debug allowed
                except Exception as e:
                    print(f"  [WARN] Probe Error: {e}")
            else:
                pass # print(f"  [INFO] Skip: {friendly_name} tidak tersedia.")
        
        if not found_encoder:
            print(f"  [INFO] Tidak ada hardware encoder yang lolos probe. Fallback ke 'libx264' (CPU).")
            self.best_encoder_name = "CPU (libx264)"
            return 'libx264'
            
        return found_encoder

    def check_system_specs(self):
        """Smart detection of PC specs (Sultan vs Kentang)"""
        try:
            # Detect RAM on Windows - Using powershell for better reliability with large RAM
            cmd = "powershell (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory"
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, creationflags=0x08000000)
            if res.returncode == 0 and res.stdout.strip():
                mem_bytes = int(res.stdout.strip())
                self.ram_gb = round(mem_bytes / (1024**3))
            
            # Fallback if powershell fails
            if self.ram_gb == 0:
                cmd = "wmic computersystem get totalphysicalmemory"
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True, creationflags=0x08000000)
                lines = [l.strip() for l in res.stdout.split('\n') if l.strip()]
                if len(lines) > 1:
                    self.ram_gb = round(int(lines[1]) / (1024**3))
            
            # Detect NVIDIA GPU
            try:
                res = subprocess.run("nvidia-smi", shell=True, capture_output=True, creationflags=0x08000000)
                self.has_nvidia = res.returncode == 0
            except:
                self.has_nvidia = False
                
            # Categorize
            if self.ram_gb >= 16 and self.cpu_cores >= 8 and self.has_nvidia:
                self.pc_level = "Sultan 👑"
                self.advanced_ai_enabled.set(True)
            elif self.ram_gb >= 8 and self.has_nvidia:
                self.pc_level = "Mantap ✅"
                self.advanced_ai_enabled.set(True)
            else:
                self.pc_level = "Kentang 🥔"
                self.advanced_ai_enabled.set(False)
                
            print(f"  [SYSTEM] Specs: {self.ram_gb}GB RAM, {self.cpu_cores} Cores, NVIDIA: {self.has_nvidia}")
            print(f"  [SYSTEM] PC Level: {self.pc_level}")
        except Exception as e:
            print(f"  [ERROR] Gagal mendeteksi spek: {e}")

    def initialize_gemini_api(self):
        """Initialize Gemini API with the current user-provided key"""
        return self.api_manager.initialize_gemini_api()


    def on_api_save(self):
        """Save API keys and re-initialize"""
        return self.api_manager.on_api_save()


    def rotate_gemini_api_key(self):
        """Rotate to the next Gemini API key in the user list"""
        return self.api_manager.rotate_gemini_api_key()


    def load_config(self):
        """Load configuration from config.json"""
        return self.config_manager.load_config()


    def save_config(self, full_path=None):
        """Save current configuration to config.json"""
        return self.config_manager.save_config(full_path)


    def setup_dark_theme(self):
        """Configure modern dark theme"""
        return self.theme_manager.setup_dark_theme()


    def setup_ui(self):
        # Notebook for tabs
        self.notebook = ttk.Notebook(self.root, style='Dark.TNotebook')
        self.notebook.pack(expand=True, fill='both', padx=10, pady=10)
        
        # Tabs
        self.analysis_tab = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.settings_tab = ttk.Frame(self.notebook, style='Dark.TFrame')
        
        self.notebook.add(self.analysis_tab, text=' Analisis Video ')
        self.notebook.add(self.settings_tab, text=' Pengaturan ')
        
        # New Customize Tab
        self.customize_tab = ttk.Frame(self.notebook, style='Dark.TFrame')
        self.notebook.add(self.customize_tab, text=' Customize ')
        
        self.setup_analysis_tab()
        self.setup_settings_tab()
        self.setup_customize_tab()
        
    def setup_analysis_tab(self):
        """Setup the Analysis tab UI"""
        return self.ui_setup.setup_analysis_tab()


    def setup_settings_tab(self):
        """Setup the Settings tab UI"""
        return self.ui_setup.setup_settings_tab()


    def update_api_listboxes(self):
        """Update API key listboxes"""
        return self.api_manager.update_api_listboxes()


    def add_gemini_key(self):
        """Add Gemini API key"""
        return self.api_manager.add_gemini_key()


    def test_all_gemini_keys(self):
        """Test all Gemini keys in a background thread"""
        return self.api_manager.test_all_gemini_keys()


    def remove_gemini_key(self):
        """Remove Gemini API key"""
        return self.api_manager.remove_gemini_key()


    def clear_all_gemini_keys(self):
        """Clear all Gemini API keys"""
        return self.api_manager.clear_all_gemini_keys()


    def browse_local_file(self):
        """Allow user to select a local video file instead of downloading"""
        file_path = filedialog.askopenfilename(
            title="Pilih Video Manual",
            filetypes=[("Video Files", "*.mp4 *.mkv *.mov *.avi"), ("All Files", "*.*")]
        )
        if file_path:
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, file_path)
            self.local_video_mode = True # Flag to skip download
            messagebox.showinfo("Mode Manual", "Mode File Lokal Aktif!\n\nPENTING: Jangan lupa Copas Transkrip secara manual karena saya tidak bisa ambil subtitle dari file lokal.")
        
    def start_analysis_thread(self):
        """Start analysis in a separate thread with Metadata Check first"""
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Peringatan", "Harap masukkan URL YouTube!")
            return
        
        # Start workflow in a new thread to keep UI responsive
        def run_workflow():
            try:
                # 1. Fetch Metadata First
                self.progress_var.set("Mengambil Data Video...")
                self.root.update_idletasks()
                
                try:
                    # Quick metadata fetch without downloading
                    # [FIX] Use python -m yt_dlp to ensure it's found
                    cmd = [sys.executable, '-m', 'yt_dlp', '--dump-json', '--flat-playlist', '--no-warnings', url]
                    
                    if sys.platform == 'win32':
                        startupinfo = subprocess.STARTUPINFO()
                        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, 
                                                 startupinfo=startupinfo, encoding='utf-8')
                    else:
                        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8')
                        
                    stdout, stderr = process.communicate()
                    
                    if process.returncode == 0:
                        meta = json.loads(stdout)
                        title = meta.get('title', 'Unknown Title')
                        channel = meta.get('uploader', 'Unknown Channel')

                        # Simpan ke state internal agar bisa dipakai di export / preview
                        self.video_title = title
                        self.channel_name = channel
                        
                        # Update UI (Main Thread via callback)
                        self.root.after(0, lambda: self.video_title_label.configure(text=title))
                        self.root.after(0, lambda: self.channel_name_label.configure(text=channel))
                        print(f"[INFO] Metadata Fetched: {title} | {channel}")
                    else:
                        print(f"[WARN] Failed to fetch metadata: {stderr}")
                        
                except Exception as e:
                    print(f"[WARN] Metadata fetch error: {e}")
                
                # 2. Proceed to Analysis
                self.analyze_video()
                
            except Exception as e:
                print(f"[ERROR] Workflow failed: {e}")
                self.progress_var.set("Siap")
                
        threading.Thread(target=run_workflow, daemon=True).start()

    def update_log(self, message):
        """Thread-safe log update"""
        print(f"[LOG] {message}")
        # self.details_text.insert(tk.END, f"{message}\n") # If needed

    def analyze_video(self):
        """Main analysis logic (called after metadata workflow)"""
        url = self.url_entry.get()
        if not url:
            return

        # Prepare for analysis (clear is scheduled on main thread by orchestrator)
        self.progress_var.set("Memulai analisis...")
        self.update_log("Memulai proses analisis...")
        
        # Auto-detect genre (Empty string passed to analyzer)
        genre = "Auto-Detect" 
        style = "Auto-Detect"
        
        # Start orchestration (blocking call, but we are inside a thread already)
        self.analysis_orchestrator.start_analysis(
            url=url,
            genre=genre,
            style=style,
            use_gpu=self.gpu_var.get(),
            use_voiceover=self.use_voiceover_var.get()
        )


    def download_youtube_subtitles(self, url, video_filepath):
        """Download only VTT subtitles for a video to enable 'Auto CC' mode without AI"""
        return self.download_manager.download_youtube_subtitles(url, video_filepath)

    def download_youtube_video(self, url):
        """Download YouTube video using yt-dlp with ultra-robust 3-pass fallback"""
        return self.download_manager.download_youtube_video(url)

    def setup_customize_tab(self):
        """Setup modern layout for the Customize tab including Live Preview"""
        return self.ui_setup.setup_customize_tab()


    def toggle_watermark_ui(self):
        """Show/Hide Text or Image settings based on type"""
        w_type = self.watermark_type_var.get()
        
        # Clear container first
        self.wm_text_frame.pack_forget()
        self.wm_image_frame.pack_forget()
        
        if w_type == "text":
            self.wm_text_frame.pack(fill='x', pady=5)
        else:
            self.wm_image_frame.pack(fill='x', pady=5)
            
        self.update_preview()

    def toggle_overlay_ui(self):
        """Show/Hide Text or Image settings based on overlay type"""
        o_type = self.overlay_type_var.get()
        
        # Clear container first
        self.ov_text_frame.pack_forget()
        self.ov_image_frame.pack_forget()
        
        if o_type == "text":
            self.ov_text_frame.pack(fill='x', pady=5)
        else:
            self.ov_image_frame.pack(fill='x', pady=5)
            
        self.update_preview()

    def set_watermark_preset(self, preset):
        # Deprecated: Presets removed for bottom-margin consistency
        pass

    def update_preview(self, event=None):
        """Update the subtitle preview and save settings"""
        # Save first to update dictionary
        self.save_custom_settings(silent=True)
        
        # Render
        render_subtitle_preview(self.preview_canvas, self.custom_settings, font_dir=FONT_DIR)

    def save_custom_settings(self, silent=False):
        """Save customize tab settings"""
        self.custom_settings["subtitle_enabled"] = self.subtitle_enabled_var.get()
        self.custom_settings["watermark_enabled"] = self.watermark_enabled_var.get()
        self.custom_settings["bgm_enabled"] = self.bgm_enabled_var.get()
        self.custom_settings["bgm_file_path"] = self.bgm_file_path_var.get()
        
        self.custom_settings["subtitle_font"] = self.sub_font_var.get()
        self.custom_settings["whisper_model"] = self.whisper_model_var.get() # Save model selection
        self.custom_settings["subtitle_fontsize"] = self.sub_size_var.get()
        self.custom_settings["subtitle_position_y"] = self.sub_pos_var.get()
        self.custom_settings["subtitle_text_color"] = self.sub_color_var.get()
        self.custom_settings["subtitle_outline_color"] = self.sub_outline_color_var.get()
        self.custom_settings["subtitle_highlight_color"] = self.sub_highlight_color_var.get()
        try:
            self.custom_settings["subtitle_outline_width"] = self.sub_stroke_width_var.get()
        except: pass

        # Watermark Settings
        try:
            self.custom_settings["watermark_enabled"] = self.watermark_enabled_var.get()
            self.custom_settings["watermark_type"] = self.watermark_type_var.get()
            self.custom_settings["watermark_text"] = self.watermark_text_var.get()
            self.custom_settings["watermark_font"] = self.watermark_font_var.get()
            self.custom_settings["watermark_size"] = self.watermark_size_var.get()
            self.custom_settings["watermark_color"] = self.watermark_color_var.get()
            self.custom_settings["watermark_opacity"] = self.watermark_opacity_var.get()
            self.custom_settings["watermark_outline_color"] = self.watermark_outline_var.get()
            self.custom_settings["watermark_outline_width"] = self.watermark_outline_width_var.get()
            
            self.custom_settings["watermark_image_path"] = self.watermark_image_path_var.get()
            self.custom_settings["watermark_image_scale"] = self.watermark_scale_var.get()
            self.custom_settings["watermark_image_opacity"] = self.watermark_img_opacity_var.get()
            
            self.custom_settings["watermark_pos_x"] = self.watermark_pos_x_var.get()
            self.custom_settings["watermark_pos_y"] = self.watermark_pos_y_var.get()
        except Exception as e:
            print(f"[SETTINGS WARNING] Saving watermark error: {e}")
        
        # Overlay Settings (Second Watermark)
        try:
            self.custom_settings["overlay_enabled"] = self.overlay_enabled_var.get()
            self.custom_settings["overlay_type"] = self.overlay_type_var.get()
            self.custom_settings["overlay_text"] = self.overlay_text_var.get()
            self.custom_settings["overlay_font"] = self.overlay_font_var.get()
            self.custom_settings["overlay_size"] = self.overlay_size_var.get()
            self.custom_settings["overlay_color"] = self.overlay_color_var.get()
            self.custom_settings["overlay_opacity"] = self.overlay_opacity_var.get()
            self.custom_settings["overlay_outline_color"] = self.overlay_outline_var.get()
            self.custom_settings["overlay_outline_width"] = self.overlay_outline_width_var.get()
            
            self.custom_settings["overlay_image_path"] = self.overlay_image_path_var.get()
            self.custom_settings["overlay_image_scale"] = self.overlay_scale_var.get()
            self.custom_settings["overlay_image_opacity"] = self.overlay_img_opacity_var.get()
            
            self.custom_settings["overlay_pos_x"] = self.overlay_pos_x_var.get()
            self.custom_settings["overlay_pos_y"] = self.overlay_pos_y_var.get()
        except Exception as e:
            print(f"[SETTINGS WARNING] Saving overlay error: {e}")
        
        # Export Mode Settings
        try:
            self.custom_settings["export_mode"] = self.export_mode_var.get()
            self.custom_settings["face_tracking_smoothing"] = self.face_tracking_smoothing_var.get()
            # Assuming face_tracking_fallback_var exists, if not, this will raise an error
            self.custom_settings["face_tracking_fallback"] = self.face_tracking_fallback_var.get()
            self.custom_settings["video_flip_enabled"] = self.video_flip_var.get()
            self.custom_settings["dynamic_zoom_enabled"] = self.dynamic_zoom_var.get()
            self.custom_settings["dynamic_zoom_strength"] = self.dynamic_zoom_strength_var.get()
            self.custom_settings["dynamic_zoom_speed"] = self.dynamic_zoom_speed_var.get()
            self.custom_settings["audio_pitch_enabled"] = self.audio_pitch_var.get()
            self.custom_settings["audio_pitch_semitones"] = self.audio_pitch_semitones_var.get()
        except Exception as e:
            print(f"[SETTINGS WARNING] Saving export mode error: {e}")
        
        # Source Credit Settings
        try:
            self.custom_settings["source_credit_enabled"] = self.source_credit_enabled_var.get()
            self.custom_settings["source_credit_text"] = self.source_credit_text_var.get()
            self.custom_settings["source_credit_font"] = self.source_credit_font_var.get()
            self.custom_settings["source_credit_fontsize"] = self.source_credit_fontsize_var.get()
            self.custom_settings["source_credit_color"] = self.source_credit_color_var.get()
            self.custom_settings["source_credit_opacity"] = self.source_credit_opacity_var.get()
            self.custom_settings["source_credit_position"] = self.source_credit_position_var.get()
            self.custom_settings["source_credit_pos_x"] = self.source_credit_pos_x_var.get()
            self.custom_settings["source_credit_pos_y"] = self.source_credit_pos_y_var.get()
        except Exception as e:
            print(f"[SETTINGS WARNING] Saving source credit error: {e}")


        if save_settings(self.custom_settings):
            if not silent: print("[SETTINGS] Preferensi tersimpan.")
        
        # DEBUG
    
    def check_cookie_status(self):
        """Check if YouTube cookies file exists and update label"""
        return self.download_manager.check_cookie_status()

    def download_subtitles_only(self, url, video_path):
        """EXACT implementation from competitor\'s autoclip_decompiled.py"""
        return self.download_manager.download_subtitles_only(url, video_path)


    def download_with_idm(self, url):
        """
        [NUCLEAR OPTION] Use Internet Download Manager (IDMan.exe)
        Bypasses Python throttling completely by handing off to IDM.
        """
        return self.download_manager.download_with_idm(url)
    def update_cookies(self):
        """Open file dialog to import new cookies file"""
        return self.download_manager.update_cookies()

    def download_progress_hook(self, d):
        """Progress hook for yt-dlp"""
        if d['status'] == 'downloading':
            p = d.get('_percent_str', '0%')
            s = d.get('_speed_str', '0MB/s')
            t = d.get('_eta_str', '00:00')
            msg = f"  [DOWNLOAD] {p} | Speed: {s} | ETA: {t}"
            print(msg, end='\r')
        elif d['status'] == 'finished':
            print(f"\n  [SUCCESS] Selesai: {os.path.basename(d.get('filename', 'Video'))}")
    
    def download_youtube_audio(self, url):
        """Download YouTube audio with ultra-robust multi-pass fallback"""
        return self.download_manager.download_youtube_audio(url)
    
    def detect_high_engagement_face(self, frame):
        """Advanced visual analysis using MediaPipe to detect laughter/excitement"""
        return self.video_analyzer.detect_high_engagement_face(frame)


    def analyze_video_heatmap(self, video_path):
        """Analyze video to detect heatmap segments (high activity/engagement areas)"""
        return self.video_analyzer.analyze_video_heatmap(video_path)


    def get_video_duration(self, video_path):
        """Get video duration using ffprobe (much faster than pydub)"""
        return self.video_analyzer.get_video_duration(video_path)


    def extract_audio_and_transcribe(self, video_path):
        """Main method to transcribe audio from a file (video or audio) using parallel processing or Whisper."""
        return self.video_analyzer.extract_audio_and_transcribe(video_path)


    def transcribe_audio_file(self, audio_path):
        """Wrapper for transcribe_audio_file to use the parallel method."""
        return self.video_analyzer.transcribe_audio_file(audio_path)


    def _run_parallel_transcription(self, input_path, use_groq=False):
        """Run parallel transcription on audio chunks"""
        return self.video_analyzer._run_parallel_transcription(input_path, use_groq)


    def clean_viral_title(self, title):
        """Delegate to AI Engine"""
        return self.ai_engine.clean_viral_title(title)
    
    def validate_title_quality(self, title):
        """Delegate to AI Engine"""
        return self.ai_engine.validate_title_quality(title)
    
    def detect_clip_category(self, transcript_text):
        """Delegate to AI Engine"""
        return self.ai_engine.detect_clip_category(transcript_text)


    def analyze_with_gemini(self, text, start_time, end_time, retry_count=0):
        """Delegate to AI Engine"""
        return self.ai_engine.analyze_with_gemini(text, start_time, end_time, retry_count)

    def auto_shorten_title(self, long_title):
        """Delegate to AI Engine"""
        return self.ai_engine.auto_shorten_title(long_title)

    def generate_clickbait_title(self, segment_text, existing_titles=None, max_attempts=3, strict_content=False):
        """Delegate to AI Engine (OpenAI GPT-4o)."""
        return self.ai_engine.generate_clickbait_title(segment_text, existing_titles, max_attempts, strict_content)

    def detect_viral_segments_with_openai(self, transcript):
        """Delegate to AI Engine (OpenAI GPT-4o clip detection)."""
        return self.ai_engine.detect_viral_segments_with_openai(transcript)

    def rank_segments_with_openai(self, segments):
        """Delegate to AI Engine (OpenAI GPT-4o segment ranking)."""
        return self.ai_engine.rank_segments_with_openai(segments)

    def rank_and_score_segments_openai(self, candidates):
        """Delegate to AI Engine (OpenAI GPT-4o final ranking + viral scoring)."""
        return self.ai_engine.rank_and_score_segments_openai(candidates)

    def refine_hook_with_openai(self, hook_text):
        """Delegate to AI Engine (OpenAI GPT-4o hook refinement)."""
        return self.ai_engine.refine_hook_with_openai(hook_text)

    def refine_and_score_hook_openai(self, hook_text, max_attempts=2):
        """Delegate to AI Engine (OpenAI GPT-4o hook refinement + hook scoring)."""
        return self.ai_engine.refine_and_score_hook_openai(hook_text, max_attempts)

    def apply_hook_trigger_boost(self, hook_text, hook_score):
        """Delegate to AI Engine (boost hook score for trigger words)."""
        return self.ai_engine.apply_hook_trigger_boost(hook_text, hook_score)

    def get_viral_segments_from_ai(self, raw_transcript, keyword=None):
        """OpenAI-only viral segment detection and title generation."""
        return self.ai_segment_analyzer.get_viral_segments_from_ai(raw_transcript, keyword=keyword)


    def transcribe_video_with_whisper(self, video_path):
        """
        [OFFLINE EARS]
        Uses OpenAI Whisper to transcribe video locally.
        Fallback when APIs fail or manual upload has no transcript.
        """
        return self.transcription_engine.transcribe_video_with_whisper(video_path)

    async def _amake_voiceover(self, text, output_path):
        """Internal async method for edge-tts"""
        communicate = edge_tts.Communicate(text, "id-ID-GadisNeural") # Female Indonesian voice
        await communicate.save(output_path)

    def generate_voiceover(self, text, output_path):
        """Generate voice over using edge-tts (Sync wrapper)"""
        return self.clip_exporter.generate_voiceover(text, output_path)


    def generate_segment_titles_parallel(self):
        """Use ThreadPoolExecutor to generate titles for all segments simultaneously"""
        return self.ai_segment_analyzer.generate_segment_titles_parallel()


    def match_segments_with_content(self, segments, transcriptions):
        """Match heatmap segments with transcribed content"""
        return self.ai_segment_analyzer.match_segments_with_content(segments, transcriptions)


    def parse_manual_transcript(self, raw_text):
        """Parse raw text with timestamps and merge into meaningful segments (30s - 180s)"""
        return self.subtitle_parser.parse_manual_transcript(raw_text)

    def parse_vtt(self, vtt_path):
        """Parse VTT subtitle file into internal transcription format"""
        return self.subtitle_parser.parse_vtt(vtt_path)

    def format_time(self, seconds):
        """Format seconds to HH:MM:SS"""
        return str(timedelta(seconds=int(seconds)))
    
    def update_results_ui(self):
        """Update the results treeview with analysis results"""
        return self.results_manager.update_results_ui()


    def on_tree_click(self, event):
        """Handle clicks on the treeview, specifically for the checkbox column"""
        return self.results_manager.on_tree_click(event)


    def select_all_segments(self):
        """Check all items in the treeview"""
        return self.results_manager.select_all_segments()


    def deselect_all_segments(self):
        """Uncheck all items in the treeview"""
        return self.results_manager.deselect_all_segments()


    def on_segment_select(self, event):
        """Handle segment selection to show details"""
        return self.results_manager.on_segment_select(event)


    def export_results(self):
        """Export results to JSON file"""
        return self.results_manager.export_results()


    def download_selected_clips(self):
        """Download selected clips (delegates to ResultsManager)"""
        return self.results_manager.download_selected_clips()
    
    def download_all_clips(self):
        """Download all clips in a background thread"""
        return self.results_manager.download_all_clips()


    def generate_titles_for_selected(self):
        """Generate AI titles ONLY for selected (checked) clips - On-Demand Mode"""
        return self.ai_segment_analyzer.generate_titles_for_selected()


    def _download_worker(self, segments_to_download):
        """Background worker for downloading clips"""
        return self.clip_exporter._download_worker(segments_to_download)


    def download_clip(self, result, output_dir=None, clip_num=None):
        """Download a single clip using ffmpeg with high quality re-encoding"""
        return self.clip_exporter.download_clip(result, output_dir, clip_num)


    def preview_selected_segment(self):
        """Play the selected segment in an OpenCV window"""
        selection = self.results_tree.selection()
        if not selection:
            messagebox.showwarning("Peringatan", "Pilih salah satu baris di tabel untuk diputar.")
            return
            
        if not self.video_path or not os.path.exists(self.video_path):
            messagebox.showerror("Kesalahan", "File video tidak ditemukan. Silakan analisis video terlebih dahulu.")
            return
            
        item = self.results_tree.item(selection[0])
        start_str = item['values'][1]
        
        matching_result = None
        for result in self.analysis_results:
            if self.format_time(result['start']) == start_str:
                matching_result = result
                break
        
        if not matching_result:
            return
            
        # Play in background thread to keep UI alive
        threading.Thread(target=self._preview_worker, args=(matching_result,), daemon=True).start()

    def save_thumbnail_for_segment(self):
        """Thumbnail generator/picker: extract frame dari segmen terpilih, simpan sebagai gambar."""
        selection = self.results_tree.selection()
        if not selection:
            messagebox.showwarning("Peringatan", "Pilih salah satu baris di tabel untuk ambil thumbnail.")
            return
        if not self.video_path or not os.path.exists(self.video_path):
            messagebox.showerror("Kesalahan", "File video tidak ditemukan. Silakan analisis video terlebih dahulu.")
            return
        item = self.results_tree.item(selection[0])
        start_str = item['values'][1]
        matching_result = None
        for result in self.analysis_results:
            if self.format_time(result['start']) == start_str:
                matching_result = result
                break
        if not matching_result:
            return
        # Ambil frame di detik 1 dari awal segmen (biasanya ekspresi sudah muncul)
        capture_time = matching_result['start'] + 1.0
        if capture_time >= matching_result['end']:
            capture_time = matching_result['start']
        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            messagebox.showerror("Error", "Tidak dapat membuka video.")
            return
        fps = cap.get(cv2.CAP_PROP_FPS) or 25
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(capture_time * fps))
        ret, frame = cap.read()
        cap.release()
        if not ret or frame is None:
            messagebox.showerror("Error", "Gagal mengambil frame.")
            return
        from tkinter import filedialog
        from PIL import Image, ImageTk
        path = filedialog.asksaveasfilename(
            defaultextension=".jpg",
            filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png"), ("All files", "*.*")],
            initialfile=f"thumbnail_{start_str.replace(':', '-')}.jpg",
            title="Simpan Thumbnail"
        )
        if path:
            try:
                cv2.imwrite(path, frame)
                messagebox.showinfo("Berhasil", f"Thumbnail disimpan:\n{path}")
            except Exception as e:
                messagebox.showerror("Error", f"Gagal menyimpan: {e}")
        else:
            # Tampilkan preview saja (picker)
            win = tk.Toplevel(self.root)
            win.title(f"Thumbnail @ {start_str}")
            win.geometry("640x400")
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            pil_img = Image.fromarray(frame_rgb)
            w, h = pil_img.size
            if w > 640 or h > 360:
                pil_img.thumbnail((640, 360), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(pil_img)
            lbl = tk.Label(win, image=photo)
            lbl.image = photo
            lbl.pack(pady=5)
            def save_from_preview():
                p = filedialog.asksaveasfilename(defaultextension=".jpg", filetypes=[("JPEG", "*.jpg"), ("PNG", "*.png")], title="Simpan Thumbnail")
                if p:
                    try:
                        Image.fromarray(frame_rgb).save(p)
                        messagebox.showinfo("Berhasil", f"Disimpan: {p}")
                        win.destroy()
                    except Exception as ex:
                        messagebox.showerror("Error", str(ex))
            tk.Button(win, text="Simpan ke file...", command=save_from_preview).pack(pady=5)
            tk.Button(win, text="Tutup", command=win.destroy).pack(pady=2)

    def _preview_worker(self, result):
        """Buat klip segment dengan ffmpeg lalu buka dengan pemutar default Windows (Windows Media Player)."""
        start_time = result['start']
        end_time = result['end']
        title = (result.get('topic') or 'Preview')[:60]
        video_path = self.video_path
        try:
            import subprocess
            import time
            temp_dir = Path("temp") / "previews"
            temp_dir.mkdir(parents=True, exist_ok=True)
            for f in temp_dir.glob("*.mp4"):
                try:
                    f.unlink()
                except Exception:
                    pass
            duration = end_time - start_time
            temp_path = temp_dir / f"preview_{int(time.time())}.mp4"
            cmd = [
                'ffmpeg', '-y',
                '-ss', f"{start_time:.3f}",
                '-t', f"{duration:.3f}",
                '-i', str(video_path),
                '-c:v', 'libx264', '-preset', 'ultrafast', '-crf', '23',
                '-c:a', 'aac', '-b:a', '128k',
                str(temp_path)
            ]
            creationflags = 0x08000000 if os.name == 'nt' else 0
            subprocess.run(cmd, creationflags=creationflags, check=True, timeout=120)
            if temp_path.exists():
                os.startfile(str(temp_path))
                print(f"  [PREVIEW] Dibuka dengan Windows Media Player: {title[:40]}...")
            else:
                self.root.after(0, lambda: messagebox.showerror("Preview", "Klip preview gagal dibuat."))
        except subprocess.TimeoutExpired:
            self.root.after(0, lambda: messagebox.showerror("Preview", "FFmpeg timeout. Coba segment lebih pendek."))
        except Exception as e:
            print(f"  [PREVIEW ERROR] {e}")
            import traceback
            traceback.print_exc()
            self.root.after(0, lambda: messagebox.showerror("Preview", f"Gagal membuat klip / membuka pemutar:\n{e}\nPastikan file video ada dan FFmpeg terpasang."))

    def _caption_safe_key(self, s):
        """Sanitize caption key for filename matching."""
        return self.subtitle_parser._caption_safe_key(s)

    def derive_caption_keys(self, video_path, video_id=None):
        """Return a priority-ordered list of possible caption keys."""
        return self.subtitle_parser.derive_caption_keys(video_path, video_id)


    def find_sidecar_caption(self, video_path, video_id=None):
        """Try to find a sidecar caption file for a given video."""
        return self.subtitle_parser.find_sidecar_caption(video_path, video_id)

    def parse_structured_segments(self, text):
        """
        Parse manual/external-AI segment list text into structured segments.
        Accepted line examples:
          - 01:45-03:30
          - 01:45 - 03.30 | optional title
          - 00:01:10-00:03:00 | Title
        """
        return self.subtitle_parser.parse_structured_segments(text)


    def export_ai_package(self):
        """Export current transcript and AI prompt to a folder."""
        if not self.analysis_results and not self.video_path:
             messagebox.showwarning("Export Failed", "Lakukan analisis video terlebih dahulu!")
             return
             
        try:
             # Try to find a transcript (from box or from our analysis)
             manual_text = self.manual_transcript_text.get("1.0", tk.END).strip()
             if not manual_text:
                 messagebox.showwarning("Export Failed", "Transkrip kosong. Pastikan transkrip sudah dimuat/dihasilkan.")
                 return
                 
             # Choose a directory
             output_dir = filedialog.askdirectory(title="Pilih Folder untuk AI Package")
             if not output_dir:
                 return
                 
             video_id = "video_" + str(int(time.time()))
             if self.video_path:
                 video_id = os.path.splitext(os.path.basename(self.video_path))[0]
                 
             pkg_dir = os.path.join(output_dir, f"AI_PACKAGE_{self._caption_safe_key(video_id)}")
             os.makedirs(pkg_dir, exist_ok=True)
             
             # Save transcript as SRT (Convert manual text if it's timestamps)
             # For simplicity, we just save the raw text as TRANSCRIPT.txt and also try to format as SRT
             with open(os.path.join(pkg_dir, "TRANSCRIPT.txt"), 'w', encoding='utf-8') as f:
                 f.write(manual_text)
                 
             # AI Prompt
             prompt = f"""Kamu adalah Viral Content Editor Pro. Tugasmu mencari "Golden Moments" (momen seru) dari transkrip video ini.

KRITERIA WAJIB:
- DURASI: Harus antara 30-90 detik.
- JUDUL: Buat judul deskriptif, menarik, dan SEO-friendly.
- KONTEKS: Ambil momen lucu, informatif, perdebatan, atau kejadian mendadak.

Format Output (WAJIB):
MM:SS - MM:SS | JUDUL KLIP | ALASAN

Transkrip:
{manual_text[:10000]}... (selebihnya dalam file)
"""
             with open(os.path.join(pkg_dir, "PROMPT_GPT_GEMINI.txt"), 'w', encoding='utf-8') as f:
                 f.write(prompt)
                 
             # README
             readme = """CARA PAKAI:
1. Upload file TRANSCRIPT.txt ke ChatGPT (GPT-4o) atau Gemini 1.5 Pro.
2. Copy isi file PROMPT_GPT_GEMINI.txt dan kirim ke AI.
3. Tunggu AI menghasilkan segmen.
4. Copy hasil dari AI (format MM:SS - MM:SS | Judul).
5. Paste ke kotak 'Manual Transcript' di aplikasi AutoClipper Heatmap.
6. Klik 'GAS!' untuk memproses klip tersebut.
"""
             with open(os.path.join(pkg_dir, "README.txt"), 'w', encoding='utf-8') as f:
                 f.write(readme)
                 
             print(f"  [SUCCESS] AI Package exported to: {pkg_dir}")
             messagebox.showinfo("Export Berhasil", f"Folder AI Package dibuat di:\n{pkg_dir}")
             if os.path.exists(pkg_dir):
                 os.startfile(pkg_dir)
             
        except Exception as e:
             messagebox.showerror("Error", f"Gagal mengekspor AI Package: {e}")

    def _parse_json3(self, data):
        """Convert YouTube JSON3 format to internal transcription format."""
        transcriptions = {}
        idx = 0
        events = data.get('events', [])
        
        for event in events:
            segs = event.get('segs', [])
            if not segs: continue
            
            start_ms = float(event.get('tStartMs', 0))
            duration_ms = float(event.get('dDurationMs', 0))
            
            # Combine segments into a single line for this event
            text = "".join([s.get('utf8', '') for s in segs]).strip()
            if not text or text == '\n': continue
            
            transcriptions[idx] = {
                'start': start_ms / 1000.0,
                'end': (start_ms + duration_ms) / 1000.0,
                'text': text
            }
            idx += 1
        return transcriptions

    def _fix_sub_overlaps(self, subs):
        """Remove cumulative 'rolling' text from YouTube auto-subtitles."""
        if not subs: return subs
        
        # Sort by start time just in case
        sorted_keys = sorted(subs.keys(), key=lambda k: subs[k]['start'])
        out = {}
        last_text = ""
        
        for k in sorted_keys:
            curr = subs[k]
            text = curr['text'].strip()
            
            # [CRITICAL] Handle Rolling/Cumulative Text
            # If current text is just the last text + a little bit more,
            # we only want that "little bit more".
            if last_text and text.startswith(last_text):
                new_part = text[len(last_text):].strip()
                if new_part:
                    out[k] = {
                        'start': curr['start'],
                        'end': curr['end'],
                        'text': new_part
                    }
                    last_text = text
                else:
                    # It's an exact duplicate or empty addition, skip
                    continue
            else:
                out[k] = curr
                last_text = text
                
        return out

    def _write_srt_from_data(self, data, out_path, max_words=8):
        """Save transcription data to SRT with grouping for better AI readability."""
        try:
            with open(out_path, 'w', encoding='utf-8') as f:
                idx = 1
                current_group = []
                group_start = None
                group_end = None
                
                # data is usually a dict of {idx: {start, end, text}}
                sorted_items = sorted(data.values(), key=lambda x: x['start'])
                
                for item in sorted_items:
                    if group_start is None:
                        group_start = item['start']
                    
                    current_group.append(item['text'])
                    group_end = item['end']
                    
                    # Split into chunks of max_words or if text is long
                    words_in_group = " ".join(current_group).split()
                    if len(words_in_group) >= max_words:
                        # Flush
                        t0 = self.format_time(group_start)
                        t1 = self.format_time(group_end)
                        f.write(f"{idx}\n{t0.replace('.', ',')} --> {t1.replace('.', ',')}\n{' '.join(current_group)}\n\n")
                        
                        idx += 1
                        current_group = []
                        group_start = None
                
                # Final flush
                if current_group:
                    t0 = self.format_time(group_start)
                    t1 = self.format_time(group_end)
                    f.write(f"{idx}\n{t0.replace('.', ',')} --> {t1.replace('.', ',')}\n{' '.join(current_group)}\n\n")
                
                # Ensure file is written
                f.flush()
                os.fsync(f.fileno())
                    
        except Exception as e:
            print(f"  [ERROR] Gagal menulis SRT: {e}")
    
    def _write_srt_from_segments(self, segments, out_path):
        """Convert segment list to SRT format (from competitor's approach)"""
        try:
            with open(out_path, 'w', encoding='utf-8') as f:
                for idx, seg in enumerate(segments, 1):
                    start_time = self.format_time(seg['start']).replace('.', ',')
                    end_time = self.format_time(seg['end']).replace('.', ',')
                    text = seg['text']
                    f.write(f"{idx}\n{start_time} --> {end_time}\n{text}\n\n")
        except Exception as e:
            print(f"  [ERROR] Gagal menulis SRT dari segments: {e}")

    def clear_results(self):
        """Clear all results (must be called on main thread for GUI updates)."""
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)
        self.analysis_results = []
        self.video_path = None
        if getattr(self, 'current_video_path', None) is not None:
            self.current_video_path = None
        if getattr(self, 'details_text', None) and self.details_text.winfo_exists():
            self.details_text.delete(1.0, tk.END)
        self.progress_var.set("Siap")
        if getattr(self, 'stats_total_label', None):
            self.stats_total_label.config(text="Total: 0 klip")
        if getattr(self, 'stats_avg_label', None):
            self.stats_avg_label.config(text="Rata-rata: -")
        if getattr(self, 'stats_recommended_label', None):
            self.stats_recommended_label.config(text="")
    
    def init_temp_folders(self):
        """Initialize temp folder structure and cleanup old files"""
        from pathlib import Path
        import time
        
        # Create temp directory structure
        temp_dir = Path("temp")
        temp_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (temp_dir / "previews").mkdir(exist_ok=True)
        (temp_dir / "audio").mkdir(exist_ok=True)
        
        print("[TEMP] Temp folder structure initialized: temp/")
        
        # Cleanup old files (older than 24 hours)
        try:
            current_time = time.time()
            cleanup_count = 0
            
            for file in temp_dir.rglob("*"):
                if file.is_file():
                    # Check if file is older than 24 hours (86400 seconds)
                    if file.stat().st_mtime < current_time - 86400:
                        try:
                            file.unlink()
                            cleanup_count += 1
                        except Exception as e:
                            pass  # Ignore locked files
            
            if cleanup_count > 0:
                print(f"[TEMP] Cleaned up {cleanup_count} old temp files")
        except Exception as e:
            print(f"[TEMP] Cleanup warning: {e}")

def main():
    root = tk.Tk()
    app = YouTubeHeatmapAnalyzer(root)
    root.mainloop()

if __name__ == "__main__":
    main()

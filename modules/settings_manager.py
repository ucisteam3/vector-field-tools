import json
import os

SETTINGS_FILE = os.path.join("config", "settings.json")

DEFAULT_SETTINGS = {
    "subtitle_enabled": False,
    "watermark_enabled": False,
    "bgm_enabled": False,
    "bgm_file_path": "",  # Path to BGM audio file (MP3/WAV)
    # Subtitle Customization Defaults
    "clip_duration_range": "Random (15 - 120 Detik)", # New Duration Filter
    "whisper_model": "auto",  # Options: auto, small, medium(240MB) or 'medium' (1.5GB)
    "subtitle_font": "Arial",
    "subtitle_fontsize": 24,
    "subtitle_text_color": "#FFFFFF", # White (Was primary)
    "subtitle_outline_color": "#000000", # Black
    "subtitle_outline_width": 2,
    "subtitle_position_y": 50, # From bottom
    "subtitle_position_y": 50, # From bottom
    "subtitle_highlight_color": "#FFFF00", # Yellow for Karaoke active word

    # Watermark Settings
    "watermark_enabled": False,
    "watermark_type": "text", # 'text' or 'image'
    "watermark_text": "Sample Watermark",
    "watermark_font": "Arial",
    "watermark_size": 48,
    "watermark_color": "#FFFFFF",
    "watermark_opacity": 80, # 0-100
    "watermark_outline_width": 2,
    "watermark_outline_color": "#000000",
    "watermark_image_path": "",
    "watermark_image_scale": 50, # 1-100%
    "watermark_image_opacity": 100,
    "watermark_pos_preset": "Bottom Right",
    "watermark_pos_x": 50, # Offset X
    "watermark_pos_y": 960, # Center (Margin from bottom)
    
    # Overlay Settings (Second Watermark)
    "overlay_enabled": False,
    "overlay_type": "text", # 'text' or 'image'
    "overlay_text": "Sample Overlay",
    "overlay_font": "Arial",
    "overlay_size": 48,
    "overlay_color": "#FFFFFF",
    "overlay_opacity": 80, # 0-100
    "overlay_outline_width": 2,
    "overlay_outline_color": "#000000",
    "overlay_image_path": "",
    "overlay_image_scale": 50, # 1-100%
    "overlay_image_opacity": 100,
    "overlay_pos_x": 50, # X position percentage
    "overlay_pos_y": 200, # Bottom margin (different from watermark)
    
    # Export Mode Settings
    "export_mode": "landscape_fit",  # "landscape_fit" or "face_tracking"
    "face_tracking_smoothing": 30,   # Frames for smoothing (reduce jitter)
    "face_tracking_fallback": "center",  # "center" or "last_position"
    "video_flip_enabled": False,  # Horizontal flip for copyright avoidance
    
    # Dynamic Zoom (Ken Burns style, export)
    "dynamic_zoom_enabled": False,
    "dynamic_zoom_strength": 1.55,  # max zoom factor (1.0 = no zoom, 1.6 = terasa jelas)
    "dynamic_zoom_speed": 0.0032,   # zoom increment per frame (lebih besar = zoom lebih cepat/terasa)
    
    # Audio Pitch (export)
    "audio_pitch_enabled": False,
    "audio_pitch_semitones": 0,     # -4 to +4 semitones, 0 = no change
    
    "source_credit_enabled": False,
    "source_credit_text": "Source: Channel Name",  # Auto-populated from video metadata
    "source_credit_font": "Arial",
    "source_credit_fontsize": 24,
    "source_credit_color": "#FFFFFF",  # White
    "source_credit_opacity": 80,  # 0-100
    "source_credit_position": "bottom-right",  # Preset position
    "source_credit_pos_x": 50,  # X offset from edge
    "source_credit_pos_y": 100,  # Y offset from edge

    # Theme & Aksesibilitas
    "theme_mode": "dark",  # "dark" or "light"
    "ui_font_size": 10,    # Base font size (8-14)

}

def load_settings():
    """Load settings from JSON file, returning defaults if missing"""
    if not os.path.exists(SETTINGS_FILE):
        # Create directory if it doesn't exist (safety check)
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        return DEFAULT_SETTINGS.copy()
    
    try:
        with open(SETTINGS_FILE, "r") as f:
            data = json.load(f)
            # Merge with defaults to ensure all keys exist
            settings = DEFAULT_SETTINGS.copy()
            settings.update(data)
            return settings
    except Exception as e:
        print(f"[SETTINGS] Error loading settings: {e}")
        return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    """Save settings dictionary to JSON file"""
    try:
        os.makedirs(os.path.dirname(SETTINGS_FILE), exist_ok=True)
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
        # print("[SETTINGS] Saved successfully.") # Quiet 
        return True
    except Exception as e:
        print(f"[SETTINGS] Error saving settings: {e}")
        return False

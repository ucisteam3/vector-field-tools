"""
Config Manager Module
Handles configuration loading and saving
"""

import json
import os
import shutil


class ConfigManager:
    """Manages application configuration"""
    
    def __init__(self, parent):
        """
        Initialize Config Manager
        
        Args:
            parent: Reference to YouTubeHeatmapAnalyzer instance
        """
        self.parent = parent
    
    def load_config(self):
        """Load configuration from config.json"""
        config_path = "config.json"
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    config = json.load(f)
                    self.parent.last_cookie_filename = config.get("last_cookie_filename", "www.youtube.com_cookies.txt")
                    self.parent.last_full_path = config.get("last_full_path") # Load saved full path
                    self.parent.current_genre.set(config.get("current_genre", "Umum"))
                    self.parent.current_style.set(config.get("current_style", "Entertainment"))
                    self.parent.user_gemini_keys = config.get("user_gemini_keys", [])
                    self.parent.rotate_gemini.set(config.get("rotate_gemini", True))
                    
                    if not os.path.exists("www.youtube.com_cookies.txt") and config.get("last_full_path"):
                        # If the app cookies file is gone but we have a source, try to re-install it
                        src = config.get("last_full_path")
                        if os.path.exists(src):
                            shutil.copy2(src, "www.youtube.com_cookies.txt")
            except Exception as e:
                print(f"  [WARNING] Gagal memuat config: {e}")

    def save_config(self, full_path=None):
        """Save current configuration to config.json"""
        config = {
            "last_cookie_filename": self.parent.last_cookie_filename,
            "current_genre": self.parent.current_genre.get(),
            "current_style": self.parent.current_style.get(),
            "user_gemini_keys": self.parent.user_gemini_keys,
            "rotate_gemini": self.parent.rotate_gemini.get(),
        }
        if full_path:
            config["last_full_path"] = full_path
            
        try:
            with open("config.json", "w") as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            print(f"  [WARNING] Gagal menyimpan config: {e}")


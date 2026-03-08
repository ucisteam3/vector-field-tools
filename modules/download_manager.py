"""
Download Manager Module
Handles all YouTube video, audio, and subtitle downloads using yt-dlp
"""

import os
import shutil
import time
import subprocess
from pathlib import Path
import yt_dlp
import json

# Project root (sama dengan desktop app - parent dari folder modules)
MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_DIR.parent


class YDL_Logger:
    """Custom logger for yt-dlp to silence unnecessary output"""
    def debug(self, msg):
        pass  # Silence all debug noise

    def warning(self, msg):
        pass  # Silence all warnings

    def error(self, msg):
        # Silence technical format errors to keep UI clean
        if "Requested format is not available" in msg:
            return
        pass


class DownloadManager:
    """Manages all download operations for YouTube videos, audio, and subtitles"""
    
    def __init__(self, parent):
        """
        Initialize Download Manager
        
        Args:
            parent: Reference to YouTubeHeatmapAnalyzer instance for accessing settings
        """
        self.parent = parent
    
    def download_youtube_subtitles(self, url, video_filepath):
        """Download only VTT subtitles for a video to enable 'Auto CC' mode without AI"""
        try:
            # metadata first, using 'best' format to avoid "Requested format is not available"
            sub_opts = {
                'skip_download': True,
                'quiet': True,
                'no_warnings': True,
                'format': 'best',  # CRITICAL: explicitly set to 'best' to avoid filter errors
                'ignoreerrors': True,
            }
            cookie_path = None
            if hasattr(self.parent, 'last_full_path') and self.parent.last_full_path:
                p = Path(self.parent.last_full_path)
                if p.is_absolute() and p.exists():
                    cookie_path = str(p.resolve())
                elif not p.is_absolute() and (PROJECT_ROOT / p).exists():
                    cookie_path = str((PROJECT_ROOT / p).resolve())
            if not cookie_path and (PROJECT_ROOT / "www.youtube.com_cookies.txt").exists():
                cookie_path = str((PROJECT_ROOT / "www.youtube.com_cookies.txt").resolve())
            if cookie_path:
                sub_opts['cookiefile'] = cookie_path

            print(f"   > [SUBTITLE] Mengecek ketersediaan subtitle asli (CC)...")
            info = None
            with yt_dlp.YoutubeDL(sub_opts) as ydl:
                # Try extraction
                try:
                    info = ydl.extract_info(url, download=False)
                except:
                    pass
                
                if not info or 'subtitles' not in info:
                    # Retry with TV client (common fallback in download_video)
                    sub_opts['extractor_args'] = {'youtube': {'player_client': ['tv', 'web']}}
                    try:
                        info = ydl.extract_info(url, download=False)
                    except:
                        pass
            
            if not info:
                print(f"   > [SUBTITLE] Info: Gagal mendapatkan info subtitle (Gunakan Whisper).")
                return
            
            # Check for id, id-orig, en, en-orig
            available_langs = []
            for d in [info.get('subtitles', {}), info.get('automatic_captions', {})]:
                available_langs.extend(d.keys())
            
            target_langs = ['id', 'id-orig', 'en', 'en-orig']
            found_langs = [l for l in target_langs if l in available_langs]
            
            if found_langs:
                vid_path = Path(video_filepath)
                outtmpl = str(vid_path.parent / vid_path.stem) + ".%(ext)s"
                
                dl_opts = sub_opts.copy()
                dl_opts.update({
                    'writesubtitles': True,
                    'writeautomaticsub': True,
                    'subtitleslangs': found_langs,
                    'subtitlesformat': 'vtt',
                    'outtmpl': outtmpl,
                })
                with yt_dlp.YoutubeDL(dl_opts) as ydl:
                    try:
                        ydl.download([url])
                        print(f"   > [SUBTITLE] Penarikan subtitle selesai.")
                    except:
                        pass
            else:
                print(f"   > [SUBTITLE] Info: Subtitle (Indo/English) tidak tersedia di server.")
        except Exception as e:
            print(f"   > [SUBTITLE] Info: Gagal menarik subtitle: {e}")

    def download_youtube_video(self, url):
        """Download YouTube video using yt-dlp with ultra-robust 3-pass fallback"""
        output_dir = PROJECT_ROOT / "downloads"
        output_dir.mkdir(exist_ok=True)

        # Base shared options
        # Helper: Check for ffmpeg
        if not shutil.which('ffmpeg'):
            print("  [WARNING] FFmpeg tidak ditemukan! Download mungkin gagal saat menggabungkan video+audio.")
            from tkinter import messagebox
            messagebox.showwarning("Peringatan FFmpeg", "FFmpeg tidak terdeteksi!\nAplikasi mungkin gagal menggabungkan video & audio resolusi tinggi.\nSilakan jalankan 'install_ffmpeg.bat'.")
            
        # Helper: Check for aria2c (The gold standard for speed)
        aria2_path = shutil.which('aria2c')
        if aria2_path:
            print(f"  [SPEED] Aria2c detected at {aria2_path}! Using for ultra-fast download.")
        
        # Determine cookie file path - SELALU pakai absolute path (sama dengan desktop app)
        cookie_path = None
        if hasattr(self.parent, 'last_full_path') and self.parent.last_full_path:
            p = Path(self.parent.last_full_path)
            if p.is_absolute() and p.exists():
                cookie_path = str(p.resolve())
            elif not p.is_absolute() and (PROJECT_ROOT / p).exists():
                cookie_path = str((PROJECT_ROOT / p).resolve())
        if not cookie_path:
            cookie_file = PROJECT_ROOT / "www.youtube.com_cookies.txt"
            if cookie_file.exists():
                cookie_path = str(cookie_file.resolve())
        if cookie_path:
            print(f"  [COOKIES] Menggunakan: {Path(cookie_path).name} ({Path(cookie_path).stat().st_size} bytes)")

        base_opts = {
            'outtmpl': str(output_dir / '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'logger': YDL_Logger(),
            'progress_hooks': [self.parent.download_progress_hook],
            'cookiefile': cookie_path,
            'writesubtitles': False,
            'writeautomaticsub': False,
            'skip_unavailable_fragments': True,
            'nocheckcertificate': True,
            'geobypass': True,
            'noplaylist': True,
            'cachedir': False,
            'force_ipv4': False,
            'retries': 50,
            'fragment_retries': 50,
            'skip_unavailable_fragments': False,
            'buffersize': 1024 * 1024,
            'concurrent_fragment_downloads': 8,
            'http_chunk_size': 15728640,
        }
            
        # STRATEGY 4: NUCLEAR SPEED (Aria2c Force)
        # Native throttling is persistent. We must use external downloader to split connections.
        
        # Inject Aria2c if available (CRITICAL FOR SPEED)
        if aria2_path:
            base_opts['external_downloader'] = 'aria2c'
            base_opts['external_downloader_args'] = [
                '--quiet',  # Keep aria2 silent so it doesn't mess up our UI
                '-x16',  # 16 connections per server
                '-s16',  # Split file into 16 parts
                '-k1M',  # Min split size 1MB
                '--file-allocation=none',  # Faster startup
            ]
            print(f"  [TURBO] Aria2c AKTIF (16 Koneksi).")
        else:
            # print(f"  [WARNING] Aria2c tidak ditemukan! Download mungkin lambat.")
            pass
            
        # Mode 1: TV CLIENT BYPASS (Paling Berhasil untuk 1080p saat ini)
        # Jalur ini menyamar jadi Smart TV, jarang minta PO Token/Check n.
        ydl_opts_tv = base_opts.copy()
        ydl_opts_tv['cookiefile'] = None
        ydl_opts_tv['extractor_args'] = {'youtube': {'player_client': ['tv', 'web_embedded']}}
        ydl_opts_tv['format_sort'] = ['res:1080', 'res:720', 'quality', 'codec:h264', 'size']
        ydl_opts_tv['format'] = 'bestvideo[height<=1080][height>=720]+bestaudio/best[height<=1080][height>=720]/bestvideo+bestaudio/best'

        # Mode 2: MOBILE BYPASS (Kunci Resolusi 720p-1080p)
        ydl_opts_mobile = base_opts.copy()
        ydl_opts_mobile['cookiefile'] = None
        ydl_opts_mobile['extractor_args'] = {'youtube': {'player_client': ['ios', 'android', 'mweb']}}
        ydl_opts_mobile['format_sort'] = ['res:1080', 'res:720']
        ydl_opts_mobile['format'] = 'bestvideo[height<=1080][height>=720]+bestaudio/best[height<=1080][height>=720]/bestvideo+bestaudio/best'

        # Mode 2.5: ANDROID CREATOR (Cadangan Kuat)
        ydl_opts_creator = base_opts.copy()
        ydl_opts_creator['cookiefile'] = None
        ydl_opts_creator['extractor_args'] = {'youtube': {'player_client': ['android_creator', 'android']}}
        ydl_opts_creator['format_sort'] = ['res:1080', 'res:720']
        ydl_opts_creator['format'] = 'bestvideo[height<=1080][height>=720]+bestaudio/best[height<=1080][height>=720]/bestvideo+bestaudio/best'

        # Mode 3: WEB AUTHENTICATED (HANYA jika video butuh Login)
        ydl_opts_web = base_opts.copy()
        ydl_opts_web['extractor_args'] = {'youtube': {'player_client': ['web']}}
        ydl_opts_web['format_sort'] = ['res:1080', 'res:720']
        ydl_opts_web['format'] = 'bestvideo[height<=1080][height>=720]+bestaudio/best[height<=1080][height>=720]/bestvideo+bestaudio/best'

        # Mode 4: ORIGINAL ANDROID (Cadangan Terakhir Mobile)
        ydl_opts_android = base_opts.copy()
        ydl_opts_android['cookiefile'] = None
        ydl_opts_android['extractor_args'] = {'youtube': {'player_client': ['android', 'mweb']}}
        ydl_opts_android['format_sort'] = ['res:1080', 'res:720']
        ydl_opts_android['format'] = 'bestvideo[height<=1080][height>=720]+bestaudio/best[height<=1080][height>=720]/bestvideo+bestaudio/best'

        # Mode 5: FINAL DESPERATION (Strict 720p)
        ydl_opts_safe = base_opts.copy()
        ydl_opts_safe['cookiefile'] = None
        ydl_opts_safe['format'] = 'bestvideo[height>=720]+bestaudio/best[height>=720]/bestvideo+bestaudio/best'
        ydl_opts_safe['extractor_args'] = {'youtube': {'player_client': ['web', 'android', 'ios']}}

        # Mode 6: BROWSER COOKIES AUTO (Chrome/Edge)
        # Mencoba mengambil cookies langsung dari browser tanpa file .txt
        ydl_opts_browser = base_opts.copy()
        ydl_opts_browser['cookiesfrombrowser'] = ('chrome',)  # Coba Chrome dulu
        ydl_opts_browser['format'] = 'bestvideo[height<=1080][height>=720]+bestaudio/best[height<=1080][height>=720]'

        # Mode 7: EMERGENCY FALLBACK (Strict 720p)
        ydl_opts_fallback_720 = base_opts.copy()
        ydl_opts_fallback_720['format'] = 'bestvideo[height>=720]+bestaudio/best[height>=720]/bestvideo+bestaudio/best'

        # Mode 8: ANONYMOUS / NO COOKIE (Fallback jika cookies user rusak/expired)
        ydl_opts_anon = base_opts.copy()
        ydl_opts_anon['cookiefile'] = None
        ydl_opts_anon['format'] = 'bestvideo[height<=1080][height>=720]+bestaudio/best[height<=1080][height>=720]/bestvideo+bestaudio/best'

        # Mode 9: FORCE IPV4 (Mengatasi blokir IPv6)
        ydl_opts_ipv4 = base_opts.copy()
        ydl_opts_ipv4['force_ipv4'] = True
        
        # Mode 10: SIMPLE BEST (720p floor)
        ydl_opts_simple_best = base_opts.copy()
        ydl_opts_simple_best['format'] = 'best[height>=720]/best'

        # Mode 11: ULTIMATE FALLBACK - No resolution filter (for 480p-only videos)
        ydl_opts_any = base_opts.copy()
        ydl_opts_any['format'] = 'bestvideo+bestaudio/best'

        # Mode 12: ULTIMATE FALLBACK no cookie
        ydl_opts_any_anon = base_opts.copy()
        ydl_opts_any_anon['format'] = 'bestvideo+bestaudio/best'
        ydl_opts_any_anon['cookiefile'] = None

        attempts = []

        # [PRIORITAS COOKIES] Jika user punya cookies, coba dulu dengan cookies!
        has_cookies = cookie_path is not None

        if has_cookies:
            # Mode 0.1: COOKIES SIMPLE (Browser Mimic)
            ydl_opts_simple = base_opts.copy()
            ydl_opts_simple['cookiefile'] = cookie_path
            if 'extractor_args' in ydl_opts_simple:
                del ydl_opts_simple['extractor_args']
            ydl_opts_simple['format'] = 'bestvideo[height<=1080][height>=720]+bestaudio/best[height<=1080][height>=720]/bestvideo+bestaudio/best'

            # Mode 0.2: COOKIES PRIORITY (Default Client)
            ydl_opts_cookie_first = base_opts.copy()
            ydl_opts_cookie_first['cookiefile'] = cookie_path
            ydl_opts_cookie_first['format'] = 'bestvideo[height<=1080][height>=720]+bestaudio/best[height<=1080][height>=720]/bestvideo+bestaudio/best'

            # Mode 0.3: COOKIES + ANDROID
            ydl_opts_cookie_android = base_opts.copy()
            ydl_opts_cookie_android['cookiefile'] = cookie_path
            ydl_opts_cookie_android['extractor_args'] = {'youtube': {'player_client': ['android']}}
            ydl_opts_cookie_android['format'] = 'bestvideo[height<=1080][height>=720]+bestaudio/best[height<=1080][height>=720]/bestvideo+bestaudio/best'

            # Mode 0.4: COOKIES + format ANY (untuk video yang hanya 480p)
            ydl_opts_cookie_any = base_opts.copy()
            ydl_opts_cookie_any['cookiefile'] = cookie_path
            ydl_opts_cookie_any['format'] = 'bestvideo+bestaudio/best'

            attempts.extend([
                ("Cookies Simple", ydl_opts_simple),
                ("Cookies Priority", ydl_opts_cookie_first),
                ("Cookies + Android", ydl_opts_cookie_android),
                ("Cookies + Any Resolution", ydl_opts_cookie_any),
            ])

        # Bypass tanpa cookie
        attempts.extend([
            ("Anonymous Fallback", ydl_opts_anon),
            ("Universal Safety", ydl_opts_safe),
            ("Force IPv4", ydl_opts_ipv4),
        ])

        # Strategi lainnya
        attempts.extend([
            ("Mobile Bypass", ydl_opts_mobile),
            ("Creator Bypass", ydl_opts_creator),
            ("Android Legacy", ydl_opts_android),
            ("Web Authenticated", ydl_opts_web),
            ("Browser Cookies (Chrome)", ydl_opts_browser),
            ("Simple Best 720p", ydl_opts_simple_best),
            ("Emergency 720p", ydl_opts_fallback_720),
            ("Any Resolution", ydl_opts_any_anon),
        ])
        if has_cookies:
            attempts.append(("Any Resolution + Cookies", ydl_opts_any))
        
        # [AUTOCLIP STYLE] Robust Retry Loop
        max_ops_retries = 3
        
        last_error = ""
        current_try = 0
        
        # We loop externally to simulate "Attempt 1/3"
        while current_try < max_ops_retries:
            current_try += 1
            print(f"   > Download attempt {current_try}/{max_ops_retries} via yt-dlp ...")
            self.parent.progress_var.set(f"Mengunduh video (Percobaan {current_try}/{max_ops_retries})...")

            # [DEBUG STEP] Sembunyikan pengecekan format agar tidak bising dan tidak dicontek
            pass
            
            # [CRITICAL UPDATE] Try each strategy independently
            for i, (mode_name, opts) in enumerate(attempts, 1):
                # Obfuscate mode_name to prevent "contek"
                print(f"   > Mencoba metode: {i}...")
                
                # Track files before download
                existing_files = set()
                if output_dir.exists():
                    existing_files = set(output_dir.glob('*'))
                
                try:
                    # Dynamically set robust options
                    opts['quiet'] = True
                    opts['no_warnings'] = True
                    opts['logger'] = YDL_Logger()
                    opts['retries'] = 10
                    opts['fragment_retries'] = 10
                    opts['skip_unavailable_fragments'] = False
                    opts['keepvideo'] = False
                    opts['http_chunk_size'] = 10485760
                    
                    with yt_dlp.YoutubeDL(opts) as ydl:
                        info = ydl.extract_info(url, download=True)
                    
                    # IMPORTANT: Wait a bit for filesystem to sync
                    time.sleep(0.5)
                    
                    if output_dir.exists():
                        new_files = set(output_dir.glob('*')) - existing_files
                        video_extensions = {'.mp4', '.webm', '.mkv', '.avi', '.m4a', '.flv'}
                        
                        for new_file in new_files:
                            if new_file.suffix.lower() in video_extensions:
                                print(f"   > [SUCCESS] Video berhasil didownload: {new_file.name}")
                                # Try to download subtitles separately
                                self.parent.download_youtube_subtitles(url, str(new_file))
                                return str(new_file)
                    
                    # Fallback: try prepare_filename
                    filename = ydl.prepare_filename(info)
                    if os.path.exists(filename) and not filename.endswith(('.vtt', '.srt', '.jpg', '.png', '.webp')):
                        print(f"   > [SUCCESS] Download berhasil dengan strategi: {i}")
                        # Try to download subtitles separately
                        self.parent.download_youtube_subtitles(url, filename)
                        return filename
                                
                except Exception as e:
                    last_error = str(e)
                    continue
            
            # Only wait if ALL strategies in this attempt failed
            print("   > Semua strategi gagal pada percobaan ini. Menunggu sebentar...")
            time.sleep(2 * current_try)

                
        # If all failed, give very detailed instruction
        cookie_hint = "3. **PENTING**: Salin file cookies dari browser ke folder proyek sebagai 'www.youtube.com_cookies.txt'\n"
        if not cookie_path:
            cookie_hint += "   (Aplikasi desktop Anda mungkin punya file ini - cari di folder proyek lama)\n"
        error_msg = f"Gagal mengunduh video setelah {len(attempts)} percobaan: {last_error}\n\n"
        error_msg += "SOLUSI PERBAIKAN:\n"
        error_msg += "1. Video mungkin hanya 480p - sekarang sudah ada fallback, coba lagi.\n"
        error_msg += "2. YouTube mungkin memblokir IP sementara - tunggu 5-10 menit.\n"
        error_msg += cookie_hint
        error_msg += "4. Coba download dengan IDM (opsi di menu desktop).\n"
        error_msg += f"\nDetail: {last_error}"
        print(f"  ERROR: {error_msg}")
        raise Exception(error_msg)

    def download_youtube_audio(self, url):
        """Download YouTube audio with ultra-robust multi-pass fallback"""
        output_dir = Path("downloads")
        output_dir.mkdir(exist_ok=True)
        
        # Determine cookie file path
        cookie_path = 'www.youtube.com_cookies.txt' if os.path.exists('www.youtube.com_cookies.txt') else None
        if hasattr(self.parent, 'last_full_path') and self.parent.last_full_path and os.path.exists(self.parent.last_full_path):
            cookie_path = self.parent.last_full_path
            print(f"  [AUDIO] Using User Cookies: {cookie_path}")
        
        base_opts = {
            'outtmpl': str(output_dir / '%(title)s_audio.%(ext)s'),
            'quiet': False,
            'no_warnings': False,
            'cookiefile': cookie_path,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['id', 'en'],
            'subtitlesformat': 'vtt',
            'nocheckcertificate': True,
            'geobypass': True,
            'noplaylist': True,
            'cachedir': False
        }
        
        # Mode 1: Kualitas M4A
        ydl_opts_m4a = {**base_opts, 'format': 'bestaudio[ext=m4a]/bestaudio/best'}
        
        # Mode 2: Kualitas Standar
        ydl_opts_std = {**base_opts, 'format': 'bestaudio/best'}
        
        # Mode 3: Robust (Targeting Mobile Web)
        ydl_opts_mweb = {**base_opts, 'format': 'bestaudio/best', 'extractor_args': {'youtube': {'player_client': ['mweb']}}}
        
        # Mode 4: Ultra-Robust (Targeting iOS App client - with cookies)
        ydl_opts_ios = {**base_opts, 'format': 'bestaudio/best', 'extractor_args': {'youtube': {'player_client': ['ios']}}}
        
        # Mode 5: iOS NO Cookies (Often bypasses cookie-related PO Token blocks)
        ydl_opts_ios_no = ydl_opts_ios.copy()
        ydl_opts_ios_no['cookiefile'] = None
        
        # Mode 6: Android NO Cookies
        ydl_opts_android_no = {**base_opts, 'format': 'bestaudio/best', 'cookiefile': None, 'extractor_args': {'youtube': {'player_client': ['android']}}}
        
        attempts = [
            ("Kualitas M4A", ydl_opts_m4a),
            ("Kualitas Standar", ydl_opts_std),
            ("Mode Mobile Web", ydl_opts_mweb),
            ("Mode iOS App (Ultra-Robust)", ydl_opts_ios),
            ("Mode iOS (Tanpa Cookies)", ydl_opts_ios_no),
            ("Mode Android (Tanpa Cookies)", ydl_opts_android_no)
        ]
        
        for name, opts in attempts:
            try:
                print(f"  [INFO] Mencoba metode: {name}...")
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    
                    if os.path.exists(filename):
                        return filename
                    
                    # Handle extension changes
                    base_name = Path(filename).stem
                    for ext in ['.m4a', '.webm', '.opus', '.mp3']:
                        potential_file = output_dir / f"{base_name}{ext}"
                        if potential_file.exists():
                            return str(potential_file)
            except Exception as e:
                print(f"  [WARNING] Audio youtube metode {name} = Gagal")
                continue
        
        # Fallback to extraction from video if audio fails
        print("  [INFO] Semua metode download audio gagal. Akan mencoba mengekstrak dari file video langsung.")
        return None

    def download_subtitles_only(self, url, video_path):
        """EXACT implementation from competitor's autoclip_decompiled.py"""
        print("  [SMART] Mendapatkan transkrip (Exact Competitor Strategy)...")
        try:
            import re
            import requests
            
            # Extract video ID
            video_id = None
            if 'youtube.com' in url or 'youtu.be' in url:
                if 'v=' in url:
                    try:
                        video_id = url.split('v=')[1].split('&')[0]
                    except:
                        pass
                elif 'youtu.be/' in url:
                    try:
                        video_id = url.split('youtu.be/')[1].split('?')[0]
                    except:
                        pass
            
            if not video_id:
                print("  [WARN] Tidak dapat mengekstrak video ID")
                return
            
            output_dir = Path(video_path).parent
            base_filename = os.path.splitext(video_path)[0]
            
            # EXACT yt-dlp opts from competitor (lines 1561-1567)
            ydl_opts = {
                'skip_download': True,
                'listsubtitles': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'quiet': True,
                'no_warnings': True,
            }
            
            # Add cookies if available
            if hasattr(self.parent, 'last_full_path') and self.parent.last_full_path and os.path.exists(self.parent.last_full_path):
                ydl_opts['cookiefile'] = self.parent.last_full_path
            elif os.path.exists('www.youtube.com_cookies.txt'):
                ydl_opts['cookiefile'] = 'www.youtube.com_cookies.txt'
            
            # Extract info (lines 1573-1580)
            try:
                import io
                import contextlib
                import sys
                
                captured_stdout = io.StringIO()
                
                # Capture stdout to filter language list
                with contextlib.redirect_stdout(captured_stdout):
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info_dict = ydl.extract_info(url, download=False)
                
                # Process and print filtered output
                output_log = captured_stdout.getvalue()
                for line in output_log.splitlines():
                    # Check if line looks like a language table row (starts with 2-3 char code)
                    # Example: "ab       Abkhazian             vtt, srt..."
                    if re.match(r'^\s*[a-z-]{2,10}\s+[A-Z]', line):
                        # ONLY show Indonesian
                        if 'id ' in line or 'Indonesian' in line or 'id-' in line:
                            print(line)
                    elif "Language" in line and "Formats" in line:
                        # Skip header
                        pass
                    else:
                        # Print everything else
                        if line.strip():
                            print(line)
                    
                    video_id = info_dict.get('id', video_id)
                    video_title = info_dict.get('title', 'Unknown')
                    
                    subtitles = info_dict.get('subtitles', {})
                    auto_captions = info_dict.get('automatic_captions', {})
                    
                    selected_lang_code = None
                    is_auto = False
                    
                    # Priority: id -> en -> first available (lines 1586-1606)
                    for lang in ['id', 'en']:
                        if lang in subtitles:
                            selected_lang_code = lang
                            is_auto = False
                            break
                    
                    if not selected_lang_code:
                        for lang in ['id', 'en']:
                            if lang in auto_captions:
                                selected_lang_code = lang
                                is_auto = True
                                break
                    
                    if not selected_lang_code:
                        # Fallback any
                        if subtitles:
                            selected_lang_code = list(subtitles.keys())[0]
                            is_auto = False
                        elif auto_captions:
                            selected_lang_code = list(auto_captions.keys())[0]
                            is_auto = True
                    
                    if not selected_lang_code:
                        print(f"  [INFO] Transkrip tidak ditemukan untuk {video_id}")
                        return
                    
                    cap_type = "Auto" if is_auto else "Manual"
                    print(f"  [INFO] Transkrip ditemukan (Tipe: {cap_type}, Kode: {selected_lang_code})")
                    
                    subs_list = auto_captions.get(selected_lang_code) if is_auto else subtitles.get(selected_lang_code)
                    
                    # Try JSON3 (lines 1617-1635)
                    json3_url = None
                    if subs_list:
                        for fmt in subs_list:
                            if fmt.get('ext') == 'json3':
                                json3_url = fmt.get('url')
                                break
                    
                    if json3_url:
                        print(f"  [INFO] Mengunduh JSON3 subtitle...")
                        resp = requests.get(json3_url, timeout=20)
                        if resp.status_code == 200:
                            data_json = resp.json()
                            data = self.parent._parse_json3(data_json)
                            if data:
                                data = self.parent._fix_sub_overlaps(data)
                                
                                # Save as .words.json and .srt
                                json_path = base_filename + ".words.json"
                                srt_path = base_filename + ".srt"
                                
                                with open(json_path, 'w', encoding='utf-8') as f:
                                    json.dump(data, f, indent=4)
                                    f.flush()
                                    os.fsync(f.fileno())
                                
                                self.parent._write_srt_from_data(data, srt_path)
                                
                                # [FIX] Populate self.parent.sub_transcriptions for Title Generation
                                # Assume data uses MS if start > 1000 for small values, but let's be safe.
                                # Usually _parse_json3 returns MS.
                                self.parent.sub_transcriptions = {}
                                for i, item in enumerate(data):
                                    # [FIX] Type check - item might not be dict
                                    if not isinstance(item, dict):
                                        continue
                                    
                                    s = float(item.get('start', 0))
                                    e = float(item.get('end', 0))
                                    
                                    # JSON3 format uses milliseconds, convert to seconds
                                    # Simple heuristic: if value > 1000, likely MS
                                    if s > 1000:
                                        s = s / 1000.0
                                        e = e / 1000.0
                                    
                                    self.parent.sub_transcriptions[i] = {
                                        'start': s,
                                        'end': e,
                                        'text': item.get('text', '')
                                    }
                                    

                                # Ensure files are written before returning
                                import time
                                time.sleep(0.1)
                                
                                print(f"  [SUCCESS] Transkrip JSON3 berhasil ({len(data)} baris)!")
                                return
                    
                    # Fallback: yt-dlp download subtitle (SRT/VTT) - lines 1637-1649
                    print(f"  [INFO] JSON3 tidak tersedia, fallback ke SRT/VTT...")
                    outtmpl = str(output_dir / f"{video_id}.%(ext)s")
                    
                    dl_opts = {
                        'skip_download': True,
                        'writesubtitles': True,
                        'writeautomaticsub': True,
                        'subtitleslangs': [selected_lang_code],
                        'subtitlesformat': 'srt/vtt',
                        'outtmpl': outtmpl,
                        'quiet': True,
                        'no_warnings': True,
                    }
                    
                    if ydl_opts.get('cookiefile'):
                        dl_opts['cookiefile'] = ydl_opts['cookiefile']
                    
                    with yt_dlp.YoutubeDL(dl_opts) as ydl:
                        ydl.download([url])
                    
                    # Check for downloaded subtitle
                    for ext in ['srt', 'vtt']:
                        sub_file = output_dir / f"{video_id}.{selected_lang_code}.{ext}"
                        if sub_file.exists():
                            print(f"  [SUCCESS] Subtitle {ext.upper()} downloaded: {sub_file.name}")
                            
                            # Copy to base filename
                            target_srt = base_filename + ".srt"
                            if ext == 'srt':
                                import shutil
                                shutil.copy2(sub_file, target_srt)
                            elif ext == 'vtt':
                                segments = self.parent.parse_vtt(str(sub_file))
                                if segments:
                                    self.parent._write_srt_from_segments(segments, target_srt)
                                    # [FIX] Populate self.parent.sub_transcriptions from VTT/SRT
                                    # self.parent.parse_vtt returns list of dicts with 'start', 'end' (usually Seconds or String?)
                                    # parse_vtt usually returns Seconds (float).
                                    self.parent.sub_transcriptions = {}
                                    for i, seg in enumerate(segments):
                                        # Ensure seconds
                                        s = seg.get('start', 0)
                                        e = seg.get('end', 0)
                                        # If parse_vtt returns string "00:00:12", we need conversion.
                                        # Assuming parse_vtt returns FLOAT SECONDS (standard helper).
                                        self.parent.sub_transcriptions[i] = {
                                            'start': float(s),
                                            'end': float(e),
                                            'text': seg.get('text', '')
                                        }
                            
                            print(f"  [SUCCESS] Subtitle ready!")
                            return
                    
                    print(f"  [WARN] Subtitle download failed")
                    
            except Exception as e:
                print(f"  [ERROR] Gagal mendapatkan subtitle: {e}")
                import traceback
                traceback.print_exc()
                
        except Exception as e:
            print(f"  [WARN] Error: {e}")

    def download_with_idm(self, url):
        """
        [NUCLEAR OPTION] Use Internet Download Manager (IDMan.exe)
        Bypasses Python throttling completely by handing off to IDM.
        """
        output_dir = Path("downloads")
        output_dir.mkdir(exist_ok=True)
        
        print("\n" + "="*40)
        print("[IDM INTEGRATION] Memulai Download via IDM...")
        print("="*40)
        
        # 1. Find IDMan.exe
        idm_path = r"C:\Program Files (x86)\Internet Download Manager\IDMan.exe"
        if not os.path.exists(idm_path):
            idm_path = r"C:\Program Files\Internet Download Manager\IDMan.exe"
            
        if not os.path.exists(idm_path):
            from tkinter import messagebox
            messagebox.showerror("Error IDM", "IDMan.exe tidak ditemukan!\nPastikan IDM terinstall di lokasi standar.")
            return None
            
        try:
            # 2. Extract Direct URL (Stream Link) using yt-dlp
            # IDM cannot download from 'youtube.com/watch' directly via CLI (it gets HTML)
            # We must give it the raw MP4 stream link.
            self.parent.progress_var.set("IDM: Mengekstrak Stream URL dari YouTube...")
            print("  [IDM] Getting direct stream URL...")
            
            # Determine cookie file path for IDM extraction
            cookie_path = 'www.youtube.com_cookies.txt'
            if hasattr(self.parent, 'last_full_path') and self.parent.last_full_path and os.path.exists(self.parent.last_full_path):
                cookie_path = self.parent.last_full_path
                print(f"  [IDM] Using User Cookies: {cookie_path}")
            
            ydl_opts = {
                'format': 'best[height<=1080][height>=720]',  # Min 720p, Max 1080p
                'quiet': True,
                'no_warnings': True,
                'cookiefile': cookie_path,
                'noplaylist': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                stream_url = info.get('url')  # Raw stream URL
                title = info.get('title', 'video').replace('|', '').replace('/', '_')
                ext = info.get('ext', 'mp4')
                filename = f"{title}.{ext}"
                
            if not stream_url:
                raise Exception("Gagal mendapatkan link stream video.")
                
            # 3. Call IDMan.exe
            # /d URL /p PATH /f FILE /n (Silent) /a (Add to queue) /s (Start queue)
            # Note: /s starts the queue immediately
            
            abs_path = str(output_dir.resolve())
            print(f"  [IDM] Sending to IDM: {filename}")
            
            subprocess.run([idm_path, '/d', stream_url, '/p', abs_path, '/f', filename, '/n', '/a'], check=True, creationflags=0x08000000)
            subprocess.run([idm_path, '/s'], check=True, creationflags=0x08000000)  # Start the queue
            
            # 4. Polling Loop (Wait for file)
            self.parent.progress_var.set("IDM: Sedang Mendownload (Cek IDM Anda)...")
            print("  [IDM] Menunggu IDM selesai (Timeout 10 min)...")
            
            target_file = output_dir / filename
            start_time = time.time()
            
            while True:
                if target_file.exists():
                    # Wait for file handle release (simple check size stability)
                    initial_size = target_file.stat().st_size
                    time.sleep(2)
                    if target_file.stat().st_size == initial_size and initial_size > 0:
                        print("  [IDM] Download selesai!")
                        return str(target_file)
                
                if time.time() - start_time > 600:  # 10 min timeout
                    raise Exception("IDM Download Timeout (File tak kunjung muncul).")
                    
                time.sleep(2)
                self.parent.root.update()
                
        except Exception as e:
            print(f"  [IDM ERROR] {e}")
            from tkinter import messagebox
            messagebox.showerror("IDM Gagal", str(e))
            return None

    def update_cookies(self):
        """Open file dialog to import new cookies file"""
        from tkinter import filedialog, messagebox
        file_path = filedialog.askopenfilename(
            title="Pilih File Cookies YouTube (.txt)",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if file_path:
            try:
                self.parent.last_cookie_filename = Path(file_path).name
                self.parent.last_full_path = file_path  # Update runtime path
                dest_path = "www.youtube.com_cookies.txt"
                shutil.copy2(file_path, dest_path)
                self.parent.save_config(full_path=file_path)  # Save persistence
                self.parent.check_cookie_status()
                messagebox.showinfo("Berhasil", f"Cookies dari '{self.parent.last_cookie_filename}' berhasil diperbarui!")
            except Exception as e:
                messagebox.showerror("Kesalahan", f"Gagal menyalin file cookies: {str(e)}")

    def check_cookie_status(self):
        """Check if YouTube cookies file exists and update label"""
        cookie_file = "www.youtube.com_cookies.txt"
        
        # Check for user-provided full path first
        if hasattr(self.parent, 'last_full_path') and self.parent.last_full_path and os.path.exists(self.parent.last_full_path):
            cookie_file = self.parent.last_full_path
             
        if os.path.exists(cookie_file):
            size = os.path.getsize(cookie_file)
            filename = getattr(self.parent, 'last_cookie_filename', Path(cookie_file).name)
            self.parent.cookie_status_label.config(text=f"File: {filename} ({size/1024:.1f} KB) - Aktif ✅", foreground=self.parent.accent_green)
        else:
            self.parent.cookie_status_label.config(text="Status Cookies: Belum Ada ❌", foreground=self.parent.accent_orange)

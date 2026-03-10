"""
Download Manager Module
Handles all YouTube video, audio, and subtitle downloads using yt-dlp.
Backend-safe: no Tkinter, no GUI dependencies. Works with parent=None.
"""

import os
import shutil
import time
import subprocess
from pathlib import Path
import yt_dlp
import json

# Project root (same as desktop app - parent of modules folder)
MODULE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = MODULE_DIR.parent


def _get_cookie_path(parent) -> str | None:
    """Resolve cookie file path. Works with parent=None."""
    if parent is not None and hasattr(parent, 'last_full_path') and parent.last_full_path:
        p = Path(parent.last_full_path)
        if p.is_absolute() and p.exists():
            return str(p.resolve())
        if not p.is_absolute() and (PROJECT_ROOT / p).exists():
            return str((PROJECT_ROOT / p).resolve())
    cookie_file = PROJECT_ROOT / "www.youtube.com_cookies.txt"
    if cookie_file.exists():
        return str(cookie_file.resolve())
    return None


class YDL_Logger:
    """Custom logger for yt-dlp to silence unnecessary output."""
    def debug(self, msg):
        pass

    def warning(self, msg):
        pass

    def error(self, msg):
        if "Requested format is not available" in msg:
            return
        pass


class DownloadManager:
    """
    Manages all download operations for YouTube videos, audio, and subtitles.
    Backend-safe: works with parent=None. No Tkinter or GUI dependencies.
    """
    
    def __init__(self, parent=None):
        """
        Initialize Download Manager.
        Args:
            parent: Optional reference to context (YouTubeHeatmapAnalyzer or WebAppContext).
                   Can be None for standalone/headless use.
        """
        self.parent = parent
    
    def download_youtube_subtitles(self, url, video_filepath):
        """Download only VTT subtitles for a video to enable 'Auto CC' mode without AI."""
        try:
            sub_opts = {
                'skip_download': True,
                'quiet': True,
                'no_warnings': True,
                'format': 'best',
                'ignoreerrors': True,
            }
            cookie_path = _get_cookie_path(self.parent)
            if cookie_path:
                sub_opts['cookiefile'] = cookie_path

            print("[DOWNLOAD] Checking subtitle availability (CC)...")
            info = None
            with yt_dlp.YoutubeDL(sub_opts) as ydl:
                try:
                    info = ydl.extract_info(url, download=False)
                except Exception:
                    pass
                
                if not info or 'subtitles' not in info:
                    sub_opts['extractor_args'] = {'youtube': {'player_client': ['tv', 'web']}}
                    try:
                        info = ydl.extract_info(url, download=False)
                    except Exception:
                        pass
            
            if not info:
                print("[DOWNLOAD] Subtitle info not available (use Whisper instead).")
                return
            
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
                        print("[DOWNLOAD] Subtitle extraction complete.")
                    except Exception:
                        pass
            else:
                print("[DOWNLOAD] Subtitle (Indo/English) not available.")
        except Exception as e:
            print(f"[DOWNLOAD] Subtitle download failed: {e}")

    def download_youtube_video(self, url):
        """Download YouTube video using yt-dlp with ultra-robust multi-strategy fallback."""
        output_dir = PROJECT_ROOT / "downloads"
        output_dir.mkdir(exist_ok=True)

        if not shutil.which('ffmpeg'):
            print("[DOWNLOAD] WARNING: FFmpeg not found. Video+audio merge may fail.")

        aria2_path = shutil.which('aria2c')
        if aria2_path:
            print("[DOWNLOAD] Aria2c detected - using for fast download.")
        
        cookie_path = _get_cookie_path(self.parent)
        if cookie_path:
            print(f"[DOWNLOAD] Using cookies: {Path(cookie_path).name} ({Path(cookie_path).stat().st_size} bytes)")

        progress_hooks = []
        if self.parent is not None and hasattr(self.parent, 'download_progress_hook'):
            progress_hooks = [self.parent.download_progress_hook]

        base_opts = {
            'outtmpl': str(output_dir / '%(title)s.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
            'logger': YDL_Logger(),
            'progress_hooks': progress_hooks,
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
            
        if aria2_path:
            base_opts['external_downloader'] = 'aria2c'
            base_opts['external_downloader_args'] = [
                '--quiet', '-x16', '-s16', '-k1M', '--file-allocation=none',
            ]
            
        fmt_720_1080 = 'bestvideo[height<=1080][height>=720]+bestaudio/best[height<=1080][height>=720]/bestvideo+bestaudio/best'
        fmt_720 = 'bestvideo[height>=720]+bestaudio/best[height>=720]/bestvideo+bestaudio/best'
        fmt_any = 'bestvideo+bestaudio/best'

        ydl_opts_tv = base_opts.copy()
        ydl_opts_tv['cookiefile'] = None
        ydl_opts_tv['extractor_args'] = {'youtube': {'player_client': ['tv', 'web_embedded']}}
        ydl_opts_tv['format_sort'] = ['res:1080', 'res:720', 'quality', 'codec:h264', 'size']
        ydl_opts_tv['format'] = fmt_720_1080

        ydl_opts_mobile = base_opts.copy()
        ydl_opts_mobile['cookiefile'] = None
        ydl_opts_mobile['extractor_args'] = {'youtube': {'player_client': ['ios', 'android', 'mweb']}}
        ydl_opts_mobile['format_sort'] = ['res:1080', 'res:720']
        ydl_opts_mobile['format'] = fmt_720_1080

        ydl_opts_creator = base_opts.copy()
        ydl_opts_creator['cookiefile'] = None
        ydl_opts_creator['extractor_args'] = {'youtube': {'player_client': ['android_creator', 'android']}}
        ydl_opts_creator['format_sort'] = ['res:1080', 'res:720']
        ydl_opts_creator['format'] = fmt_720_1080

        ydl_opts_web = base_opts.copy()
        ydl_opts_web['extractor_args'] = {'youtube': {'player_client': ['web']}}
        ydl_opts_web['format_sort'] = ['res:1080', 'res:720']
        ydl_opts_web['format'] = fmt_720_1080

        ydl_opts_android = base_opts.copy()
        ydl_opts_android['cookiefile'] = None
        ydl_opts_android['extractor_args'] = {'youtube': {'player_client': ['android', 'mweb']}}
        ydl_opts_android['format_sort'] = ['res:1080', 'res:720']
        ydl_opts_android['format'] = fmt_720_1080

        ydl_opts_safe = base_opts.copy()
        ydl_opts_safe['cookiefile'] = None
        ydl_opts_safe['format'] = fmt_720
        ydl_opts_safe['extractor_args'] = {'youtube': {'player_client': ['web', 'android', 'ios']}}

        ydl_opts_browser = base_opts.copy()
        ydl_opts_browser['cookiesfrombrowser'] = ('chrome',)
        ydl_opts_browser['format'] = fmt_720_1080

        ydl_opts_fallback_720 = base_opts.copy()
        ydl_opts_fallback_720['format'] = fmt_720

        ydl_opts_anon = base_opts.copy()
        ydl_opts_anon['cookiefile'] = None
        ydl_opts_anon['format'] = fmt_720_1080

        ydl_opts_ipv4 = base_opts.copy()
        ydl_opts_ipv4['force_ipv4'] = True
        
        ydl_opts_simple_best = base_opts.copy()
        ydl_opts_simple_best['format'] = 'best[height>=720]/best'

        ydl_opts_any = base_opts.copy()
        ydl_opts_any['format'] = fmt_any

        ydl_opts_any_anon = base_opts.copy()
        ydl_opts_any_anon['format'] = fmt_any
        ydl_opts_any_anon['cookiefile'] = None

        attempts = []
        has_cookies = cookie_path is not None

        if has_cookies:
            # Age-restricted videos: browser session often works when exported .txt does not.
            # Try Chrome cookies first (user must be logged in & age-confirmed in Chrome).
            attempts.append(("Cookies dari Chrome (browser)", ydl_opts_browser))

            ydl_opts_simple = base_opts.copy()
            ydl_opts_simple['cookiefile'] = cookie_path
            if 'extractor_args' in ydl_opts_simple:
                del ydl_opts_simple['extractor_args']
            ydl_opts_simple['format'] = fmt_720_1080

            ydl_opts_cookie_first = base_opts.copy()
            ydl_opts_cookie_first['cookiefile'] = cookie_path
            ydl_opts_cookie_first['format'] = fmt_720_1080

            ydl_opts_cookie_android = base_opts.copy()
            ydl_opts_cookie_android['cookiefile'] = cookie_path
            ydl_opts_cookie_android['extractor_args'] = {'youtube': {'player_client': ['android']}}
            ydl_opts_cookie_android['format'] = fmt_720_1080

            ydl_opts_cookie_any = base_opts.copy()
            ydl_opts_cookie_any['cookiefile'] = cookie_path
            ydl_opts_cookie_any['format'] = fmt_any

            # Permissive format — avoids "Requested format is not available" when only low/merged formats exist
            ydl_opts_cookie_best = base_opts.copy()
            ydl_opts_cookie_best['cookiefile'] = cookie_path
            ydl_opts_cookie_best['format'] = 'bestvideo+bestaudio/best'
            ydl_opts_cookie_best.pop('format_sort', None)

            # web_embedded client sometimes returns streams for age-gated content when file cookies are used
            ydl_opts_cookie_embedded = base_opts.copy()
            ydl_opts_cookie_embedded['cookiefile'] = cookie_path
            ydl_opts_cookie_embedded['extractor_args'] = {'youtube': {'player_client': ['web_embedded', 'web', 'android']}}
            ydl_opts_cookie_embedded['format'] = 'bestvideo+bestaudio/best'
            ydl_opts_cookie_embedded.pop('format_sort', None)

            attempts.extend([
                ("Cookies Simple", ydl_opts_simple),
                ("Cookies Priority", ydl_opts_cookie_first),
                ("Cookies + Android", ydl_opts_cookie_android),
                ("Cookies + Any Resolution", ydl_opts_cookie_any),
                ("Cookies + Best Any", ydl_opts_cookie_best),
                ("Cookies + Web Embedded", ydl_opts_cookie_embedded),
            ])

        # Avoid duplicate Browser attempt if already tried at top with cookies
        if not has_cookies:
            attempts.append(("Browser Cookies (Chrome)", ydl_opts_browser))

        attempts.extend([
            ("Anonymous Fallback", ydl_opts_anon),
            ("Universal Safety", ydl_opts_safe),
            ("Force IPv4", ydl_opts_ipv4),
            ("Mobile Bypass", ydl_opts_mobile),
            ("Creator Bypass", ydl_opts_creator),
            ("Android Legacy", ydl_opts_android),
            ("Web Authenticated", ydl_opts_web),
            ("Simple Best 720p", ydl_opts_simple_best),
            ("Emergency 720p", ydl_opts_fallback_720),
            ("Any Resolution", ydl_opts_any_anon),
        ])
        if has_cookies:
            attempts.append(("Any Resolution + Cookies", ydl_opts_any))
        
        max_ops_retries = 3
        last_error = ""
        current_try = 0
        
        while current_try < max_ops_retries:
            current_try += 1
            print(f"[DOWNLOAD] Attempt {current_try}/{max_ops_retries} via yt-dlp")
            
            for i, (mode_name, opts) in enumerate(attempts, 1):
                print(f"[DOWNLOAD] Trying strategy {i}: {mode_name}")
                existing_files = set()
                if output_dir.exists():
                    existing_files = set(output_dir.glob('*'))
                
                try:
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
                    
                    time.sleep(0.5)
                    
                    if output_dir.exists():
                        new_files = set(output_dir.glob('*')) - existing_files
                        video_extensions = {'.mp4', '.webm', '.mkv', '.avi', '.m4a', '.flv'}
                        
                        for new_file in new_files:
                            if new_file.suffix.lower() in video_extensions:
                                print(f"[DOWNLOAD] Success: {new_file.name}")
                                if self.parent is not None:
                                    self.download_youtube_subtitles(url, str(new_file))
                                return str(new_file)
                    
                    filename = ydl.prepare_filename(info)
                    if os.path.exists(filename) and not filename.endswith(('.vtt', '.srt', '.jpg', '.png', '.webp')):
                        print(f"[DOWNLOAD] Success with strategy {i}: {filename}")
                        if self.parent is not None:
                            self.download_youtube_subtitles(url, filename)
                        return filename
                                
                except Exception as e:
                    last_error = str(e)
                    print(f"[DOWNLOAD] Strategy {mode_name} failed: {e}")
                    continue
            
            print("[DOWNLOAD] All strategies failed this attempt. Waiting...")
            time.sleep(2 * current_try)

        cookie_hint = "3. Add 'www.youtube.com_cookies.txt' to project folder.\n" if not cookie_path else ""
        age_hint = ""
        err_lower = (last_error or "").lower()
        if "age" in err_lower or "login" in err_lower or "confirm" in err_lower or "inappropriate" in err_lower:
            age_hint = (
                "4. Video TERBATAS UMUR: buka link di Chrome, login & konfirmasi umur, lalu:\n"
                "   - Upload cookies baru di Settings > Cookies YouTube, atau\n"
                "   - Tutup Chrome lalu jalankan aplikasi lagi (strategi 'Cookies dari Chrome').\n"
                "5. Perbarui yt-dlp: pip install -U yt-dlp\n"
            )
        error_msg = (
            f"Download failed after {len(attempts)} strategies: {last_error}\n\n"
            "Troubleshooting:\n"
            "1. Video may be 480p-only - retry.\n"
            "2. YouTube may be blocking - wait 5-10 min.\n"
            f"{cookie_hint}"
            f"{age_hint}"
            f"\nDetail: {last_error}"
        )
        print(f"[DOWNLOAD] ERROR: {error_msg}")
        raise Exception(error_msg)

    def download_youtube_audio(self, url):
        """Download YouTube audio with multi-pass fallback."""
        output_dir = PROJECT_ROOT / "downloads"
        output_dir.mkdir(exist_ok=True)
        
        cookie_path = _get_cookie_path(self.parent)
        if cookie_path:
            print(f"[DOWNLOAD] Audio: using cookies ({Path(cookie_path).name})")
        
        base_opts = {
            'outtmpl': str(output_dir / '%(title)s_audio.%(ext)s'),
            'quiet': True,
            'no_warnings': True,
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
        
        attempts = [
            ("M4A", {**base_opts, 'format': 'bestaudio[ext=m4a]/bestaudio/best'}),
            ("Standard", {**base_opts, 'format': 'bestaudio/best'}),
            ("Mobile Web", {**base_opts, 'format': 'bestaudio/best', 'extractor_args': {'youtube': {'player_client': ['mweb']}}}),
            ("iOS", {**base_opts, 'format': 'bestaudio/best', 'extractor_args': {'youtube': {'player_client': ['ios']}}}),
            ("iOS No Cookie", {**base_opts, 'format': 'bestaudio/best', 'cookiefile': None, 'extractor_args': {'youtube': {'player_client': ['ios']}}}),
            ("Android No Cookie", {**base_opts, 'format': 'bestaudio/best', 'cookiefile': None, 'extractor_args': {'youtube': {'player_client': ['android']}}}),
        ]
        
        for name, opts in attempts:
            try:
                print(f"[DOWNLOAD] Audio: trying {name}...")
                with yt_dlp.YoutubeDL(opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    filename = ydl.prepare_filename(info)
                    
                    if os.path.exists(filename):
                        print(f"[DOWNLOAD] Audio success: {filename}")
                        return filename
                    
                    base_name = Path(filename).stem
                    for ext in ['.m4a', '.webm', '.opus', '.mp3']:
                        potential_file = output_dir / f"{base_name}{ext}"
                        if potential_file.exists():
                            return str(potential_file)
            except Exception as e:
                print(f"[DOWNLOAD] Audio {name} failed: {e}")
                continue
        
        print("[DOWNLOAD] All audio methods failed.")
        return None

    def download_subtitles_only(self, url, video_path):
        """Download subtitles only (competitor strategy). Requires parent with _parse_json3, parse_vtt, etc."""
        if self.parent is None:
            print("[DOWNLOAD] download_subtitles_only requires parent context. Skipping.")
            return
            
        print("[DOWNLOAD] Getting transcript (Competitor Strategy)...")
        try:
            import re
            import requests
            
            video_id = None
            if 'youtube.com' in url or 'youtu.be' in url:
                if 'v=' in url:
                    try:
                        video_id = url.split('v=')[1].split('&')[0]
                    except Exception:
                        pass
                elif 'youtu.be/' in url:
                    try:
                        video_id = url.split('youtu.be/')[1].split('?')[0]
                    except Exception:
                        pass
            
            if not video_id:
                print("[DOWNLOAD] Could not extract video ID")
                return
            
            output_dir = Path(video_path).parent
            base_filename = os.path.splitext(video_path)[0]
            
            ydl_opts = {
                'skip_download': True,
                'listsubtitles': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'quiet': True,
                'no_warnings': True,
            }
            cookie_path = _get_cookie_path(self.parent)
            if cookie_path:
                ydl_opts['cookiefile'] = cookie_path
            
            try:
                import io
                import contextlib
                
                captured_stdout = io.StringIO()
                with contextlib.redirect_stdout(captured_stdout):
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info_dict = ydl.extract_info(url, download=False)
                
                output_log = captured_stdout.getvalue()
                for line in output_log.splitlines():
                    if re.match(r'^\s*[a-z-]{2,10}\s+[A-Z]', line) and ('id ' in line or 'Indonesian' in line or 'id-' in line):
                        print(line)
                
                video_id = info_dict.get('id', video_id)
                subtitles = info_dict.get('subtitles', {})
                auto_captions = info_dict.get('automatic_captions', {})
                selected_lang_code = None
                is_auto = False
                
                for lang in ['id', 'en']:
                    if lang in subtitles:
                        selected_lang_code = lang
                        break
                if not selected_lang_code:
                    for lang in ['id', 'en']:
                        if lang in auto_captions:
                            selected_lang_code = lang
                            is_auto = True
                            break
                if not selected_lang_code:
                    if subtitles:
                        selected_lang_code = list(subtitles.keys())[0]
                    elif auto_captions:
                        selected_lang_code = list(auto_captions.keys())[0]
                        is_auto = True
                
                if not selected_lang_code:
                    print(f"[DOWNLOAD] No transcript for {video_id}")
                    return
                
                cap_type = "Auto" if is_auto else "Manual"
                print(f"[DOWNLOAD] Transcript found ({cap_type}, {selected_lang_code})")
                
                subs_list = auto_captions.get(selected_lang_code) if is_auto else subtitles.get(selected_lang_code)
                json3_url = None
                if subs_list:
                    for fmt in subs_list:
                        if fmt.get('ext') == 'json3':
                            json3_url = fmt.get('url')
                            break
                
                if json3_url and hasattr(self.parent, '_parse_json3'):
                    print("[DOWNLOAD] Downloading JSON3 subtitle...")
                    resp = requests.get(json3_url, timeout=20)
                    if resp.status_code == 200:
                        data_json = resp.json()
                        data = self.parent._parse_json3(data_json)
                        if data and hasattr(self.parent, '_fix_sub_overlaps'):
                            data = self.parent._fix_sub_overlaps(data)
                            json_path = base_filename + ".words.json"
                            srt_path = base_filename + ".srt"
                            with open(json_path, 'w', encoding='utf-8') as f:
                                json.dump(data, f, indent=4)
                                f.flush()
                                os.fsync(f.fileno())
                            if hasattr(self.parent, '_write_srt_from_data'):
                                self.parent._write_srt_from_data(data, srt_path)
                            if hasattr(self.parent, 'sub_transcriptions'):
                                self.parent.sub_transcriptions = {}
                                for i, item in enumerate(data):
                                    if not isinstance(item, dict):
                                        continue
                                    s = float(item.get('start', 0))
                                    e = float(item.get('end', 0))
                                    if s > 1000:
                                        s, e = s / 1000.0, e / 1000.0
                                    self.parent.sub_transcriptions[i] = {'start': s, 'end': e, 'text': item.get('text', '')}
                            time.sleep(0.1)
                            print(f"[DOWNLOAD] JSON3 transcript success ({len(data)} lines)")
                            return
                
                print("[DOWNLOAD] Falling back to SRT/VTT...")
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
                if cookie_path:
                    dl_opts['cookiefile'] = cookie_path
                
                with yt_dlp.YoutubeDL(dl_opts) as ydl:
                    ydl.download([url])
                
                for ext in ['srt', 'vtt']:
                    sub_file = output_dir / f"{video_id}.{selected_lang_code}.{ext}"
                    if sub_file.exists():
                        print(f"[DOWNLOAD] Subtitle downloaded: {sub_file.name}")
                        target_srt = base_filename + ".srt"
                        if ext == 'srt':
                            shutil.copy2(sub_file, target_srt)
                        elif ext == 'vtt' and hasattr(self.parent, 'parse_vtt') and hasattr(self.parent, '_write_srt_from_segments'):
                            segments = self.parent.parse_vtt(str(sub_file))
                            if segments:
                                self.parent._write_srt_from_segments(segments, target_srt)
                                if hasattr(self.parent, 'sub_transcriptions'):
                                    self.parent.sub_transcriptions = {i: {'start': float(s.get('start', 0)), 'end': float(s.get('end', 0)), 'text': s.get('text', '')} for i, s in enumerate(segments)}
                        print("[DOWNLOAD] Subtitle ready")
                        return
                
                print("[DOWNLOAD] Subtitle download failed")
                    
            except Exception as e:
                print(f"[DOWNLOAD] Subtitle error: {e}")
                import traceback
                traceback.print_exc()
                
        except Exception as e:
            print(f"[DOWNLOAD] Error: {e}")

    def download_with_idm(self, url):
        """Use IDM for download (Windows). Backend-safe: no messagebox, no root.update."""
        output_dir = PROJECT_ROOT / "downloads"
        output_dir.mkdir(exist_ok=True)
        
        print("[DOWNLOAD] IDM: Starting...")
        idm_path = r"C:\Program Files (x86)\Internet Download Manager\IDMan.exe"
        if not os.path.exists(idm_path):
            idm_path = r"C:\Program Files\Internet Download Manager\IDMan.exe"
            
        if not os.path.exists(idm_path):
            print("[DOWNLOAD] IDM ERROR: IDMan.exe not found.")
            return None
            
        try:
            cookie_path = _get_cookie_path(self.parent)
            if cookie_path:
                print(f"[DOWNLOAD] IDM: Using cookies")
            
            ydl_opts = {
                'format': 'best[height<=1080][height>=720]/best',
                'quiet': True,
                'no_warnings': True,
                'cookiefile': cookie_path,
                'noplaylist': True
            }
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                stream_url = info.get('url')
                title = info.get('title', 'video').replace('|', '').replace('/', '_')
                ext = info.get('ext', 'mp4')
                filename = f"{title}.{ext}"
                
            if not stream_url:
                raise Exception("Failed to get stream URL")
                
            abs_path = str(output_dir.resolve())
            print(f"[DOWNLOAD] IDM: Sending to IDM: {filename}")
            
            subprocess.run([idm_path, '/d', stream_url, '/p', abs_path, '/f', filename, '/n', '/a'], check=True, creationflags=0x08000000)
            subprocess.run([idm_path, '/s'], check=True, creationflags=0x08000000)
            
            print("[DOWNLOAD] IDM: Waiting (timeout 10 min)...")
            target_file = output_dir / filename
            start_time = time.time()
            
            while True:
                if target_file.exists():
                    initial_size = target_file.stat().st_size
                    time.sleep(2)
                    if target_file.stat().st_size == initial_size and initial_size > 0:
                        print("[DOWNLOAD] IDM: Complete")
                        return str(target_file)
                
                if time.time() - start_time > 600:
                    raise Exception("IDM Download Timeout")
                    
                time.sleep(2)
                
        except Exception as e:
            print(f"[DOWNLOAD] IDM ERROR: {e}")
            return None

    def update_cookies(self):
        """Placeholder for GUI cookie update. No-op in headless mode."""
        if self.parent is None:
            return
        print("[DOWNLOAD] update_cookies: Use web upload or copy www.youtube.com_cookies.txt")

    def check_cookie_status(self):
        """Placeholder for GUI cookie status. No-op in headless mode."""
        if self.parent is None:
            return
        cookie_file = PROJECT_ROOT / "www.youtube.com_cookies.txt"
        if _get_cookie_path(self.parent):
            print(f"[DOWNLOAD] Cookies: active ({cookie_file.stat().st_size} bytes)")
        else:
            print("[DOWNLOAD] Cookies: none")

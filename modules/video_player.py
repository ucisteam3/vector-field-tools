"""
Video Player Module
Built-in video player with seek controls, smooth playback, and audio via ffplay.
"""

import tkinter as tk
from tkinter import ttk
import cv2
from PIL import Image, ImageTk
import threading
import time
import subprocess
import os
from pathlib import Path


class VideoPlayer:
    """Built-in video player with seek controls and keyboard shortcuts"""
    
    def __init__(self, video_path, start_time, end_time, title):
        """
        Initialize video player
        
        Args:
            video_path: Path to video file
            start_time: Start time in seconds
            end_time: End time in seconds
            title: Window title
        """
        self.video_path = video_path
        self.start_time = start_time
        self.end_time = end_time
        self.title = title
        
        self.is_playing = False
        self.is_closed = False
        self.current_position = start_time
        self.duration = end_time - start_time
        
        # Video capture
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise Exception("Cannot open video file")
        
        self.fps = self.cap.get(cv2.CAP_PROP_FPS) or 25.0
        if self.fps <= 0 or self.fps > 120:
            self.fps = 25.0
        self.total_frames = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.frame_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.frame_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Calculate display size (max 1280x720)
        max_width = 1280
        max_height = 720
        aspect_ratio = self.frame_width / self.frame_height
        
        if self.frame_width > max_width or self.frame_height > max_height:
            if aspect_ratio > max_width / max_height:
                self.display_width = max_width
                self.display_height = int(max_width / aspect_ratio)
            else:
                self.display_height = max_height
                self.display_width = int(max_height * aspect_ratio)
        else:
            self.display_width = self.frame_width
            self.display_height = self.frame_height
        
        # UI components (will be created in show())
        self.window = None
        self.canvas = None
        self.play_btn = None
        self.seek_slider = None
        self.time_label = None
        self.photo = None
        self._slider_updating = False  # avoid recursive seek when playback updates slider
        self._canvas_image_id = None  # update in place to reduce flicker
        self._play_start_wall = None  # wall-clock time when play started (for real-time sync)
        self._play_start_pos = None   # position when play started
        self._audio_process = None    # ffplay subprocess for audio
        # Update UI hanya dari main thread (hilangkan glitch/blink)
        self._pending_frame = None
        self._pending_position = None
        self._paint_scheduled = False
        self._timeline_update_counter = 0
        # Smooth display: buffer dari playback thread, main thread gambar pakai timer 30 fps
        self._display_frame = None
        self._display_position = None
        self._display_timer_id = None
        self._display_interval_ms = 33  # ~30 fps
        self.AUDIO_START_DELAY = 0.03  # detik: delay start audio agar sinkron dengan video
        
    def show(self):
        """Show the video player window"""
        # Create window
        self.window = tk.Toplevel()
        self.window.title(f"Preview: {self.title[:60]}")
        self.window.geometry(f"{self.display_width}x{self.display_height + 70}")
        self.window.resizable(True, True)
        self.window.minsize(400, 300)
        self.window.configure(bg='#0a0c10')
        
        # Video canvas (satu image item, update in-place untuk kurangi blink)
        self.canvas = tk.Canvas(self.window, width=self.display_width, height=self.display_height, bg='#000', highlightthickness=0)
        self.canvas.pack()
        self._canvas_image_id = self.canvas.create_image(0, 0, anchor='nw')
        
        # Timeline / waveform strip (visual progress bar, click to seek)
        self.timeline_height = 24
        self.timeline = tk.Canvas(self.window, width=self.display_width, height=self.timeline_height, bg='#161b22', highlightthickness=0)
        self.timeline.pack(fill='x', pady=(2, 0))
        def on_timeline_click(event):
            if self.duration <= 0:
                return
            x = event.x
            w = self.timeline.winfo_width() or self.display_width
            frac = max(0, min(1, x / w))
            self.seek_to(frac * self.duration)
        self.timeline.bind('<Button-1>', on_timeline_click)
        self._timeline_bar_bg = None
        self._timeline_bar_fill = None
        self._timeline_playhead = None
        
        # Control frame (dark theme to match app)
        control_frame = tk.Frame(self.window, bg='#0a0c10', height=70)
        control_frame.pack(fill='x')
        control_frame.pack_propagate(False)
        
        # Play/Pause button
        self.play_btn = tk.Button(control_frame, text="> Play", command=self.toggle_play,
                                   bg='#00d2ff', fg='#050608', font=('Segoe UI', 10, 'bold'),
                                   width=10, relief='flat', cursor='hand2',
                                   activebackground='#33e0ff', activeforeground='#050608')
        self.play_btn.pack(side='left', padx=10, pady=10)
        
        # Time label (current / total)
        self.time_label = tk.Label(control_frame, text=f"{self.format_time(0)} / {self.format_time(self.duration)}", 
                                   bg='#0a0c10', fg='#8b949e', font=('Consolas', 10))
        self.time_label.pack(side='left', padx=5)
        
        # Seek slider
        slider_frame = tk.Frame(control_frame, bg='#0a0c10')
        slider_frame.pack(side='left', fill='x', expand=True, padx=10)
        
        self.seek_slider = ttk.Scale(slider_frame, from_=0, to=max(self.duration, 0.1),
                                     orient='horizontal', command=self.on_seek, length=300)
        self.seek_slider.pack(fill='x')
        
        # Duration label (right)
        self.duration_label = tk.Label(control_frame, text=self.format_time(self.duration),
                                       bg='#0a0c10', fg='#8b949e', font=('Consolas', 10))
        self.duration_label.pack(side='right', padx=10)
        
        # Keyboard shortcuts
        self.window.bind('<space>', lambda e: self.toggle_play())
        self.window.bind('<Left>', lambda e: self.seek_relative(-5))
        self.window.bind('<Right>', lambda e: self.seek_relative(5))
        self.window.bind('<Escape>', lambda e: self.close())
        
        # Handle window close
        self.window.protocol("WM_DELETE_WINDOW", self.close)
        
        # Seek to start position
        self.seek_to(0)
        
        # Show first frame
        self.update_frame()
        
        # Auto-play: video tunggu AUDIO_START_DELAY lalu audio start = sinkron
        self.is_playing = True
        delay = self.AUDIO_START_DELAY
        self._play_start_wall = time.perf_counter() + delay
        self._play_start_pos = 0
        self.play_btn.config(text="|| Pause", bg='#f0883e')
        self._start_display_timer()
        threading.Thread(target=self.playback_loop, daemon=True).start()
        self.window.after(int(delay * 1000), self._start_audio)
        
    def _start_audio(self):
        """Jalankan audio segment dengan ffplay (tanpa jendela)."""
        self._stop_audio()
        try:
            elapsed = self.current_position - self.start_time
            left = self.duration - elapsed
            if left <= 0:
                return
            cmd = [
                'ffplay', '-nodisp', '-autoexit', '-loglevel', 'quiet',
                '-ss', str(self.current_position), '-t', str(left),
                '-i', str(self.video_path)
            ]
            creationflags = 0x08000000 if os.name == 'nt' else 0
            self._audio_process = subprocess.Popen(cmd, creationflags=creationflags, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            self._audio_process = None

    def _stop_audio(self):
        """Hentikan proses audio."""
        if getattr(self, '_audio_process', None):
            try:
                self._audio_process.terminate()
                self._audio_process.wait(timeout=1)
            except Exception:
                try:
                    self._audio_process.kill()
                except Exception:
                    pass
            self._audio_process = None

    def toggle_play(self):
        """Toggle play/pause"""
        self.is_playing = not self.is_playing
        if self.is_playing:
            self.play_btn.config(text="|| Pause", bg='#f0883e')
            delay = self.AUDIO_START_DELAY
            self._play_start_wall = time.perf_counter() + delay
            self._play_start_pos = self.current_position - self.start_time
            self._start_display_timer()
            if self.window and self.window.winfo_exists():
                self.window.after(int(delay * 1000), self._start_audio)
        else:
            self.play_btn.config(text="> Play", bg='#00d2ff')
            self._stop_display_timer()
            self._stop_audio()
    
    def seek_relative(self, seconds):
        """Seek relative to current position"""
        new_pos = self.current_position - self.start_time + seconds
        new_pos = max(0, min(new_pos, self.duration))
        self.seek_to(new_pos)
    
    def seek_to(self, position):
        """Seek to absolute position (relative to segment start). Slider di-update lewat paint di main thread."""
        self.current_position = self.start_time + position
        frame_number = int(self.current_position * self.fps)
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        self.update_frame()
        if self.is_playing:
            self._play_start_wall = time.perf_counter()
            self._play_start_pos = position
            self._start_audio()
    
    def on_seek(self, value):
        """Handle slider seek - jump to position and update frame"""
        if self._slider_updating:
            return
        try:
            position = float(value)
        except (TypeError, ValueError):
            return
        self.current_position = self.start_time + position
        frame_number = int(self.current_position * self.fps)
        self.cap.set(cv2.CAP_PROP_POS_FRAMES, frame_number)
        self.update_frame()
    
    def _set_play_btn_play(self):
        """Main thread only: set tombol ke state Play."""
        try:
            if not self.is_closed and self.play_btn and self.play_btn.winfo_exists():
                self.play_btn.config(text="> Play", bg='#00d2ff')
        except tk.TclError:
            pass

    def _widgets_ok(self):
        """True jika jendela/canvas masih ada (jangan akses Tk setelah window ditutup)."""
        if self.is_closed:
            return False
        try:
            return self.window is not None and self.window.winfo_exists() and self.canvas is not None and self.canvas.winfo_exists()
        except tk.TclError:
            return False

    def _paint_frame_impl(self, frame, pos):
        """Gambar satu frame + UI (hanya dipanggil dari main thread). pos = current_position untuk frame ini."""
        if frame is None or not self._widgets_ok():
            return
        try:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frame = cv2.resize(frame, (self.display_width, self.display_height))
            img = Image.fromarray(frame)
            self.photo = ImageTk.PhotoImage(image=img)
            if not self._widgets_ok():
                return
            if self.canvas and self._canvas_image_id is not None:
                self.canvas.itemconfig(self._canvas_image_id, image=self.photo)
            if pos is not None and self.time_label and hasattr(self, 'duration'):
                elapsed = pos - self.start_time
                self.time_label.config(text=f"{self.format_time(elapsed)} / {self.format_time(self.duration)}")
            if pos is not None and self.seek_slider and not self._slider_updating:
                try:
                    self._slider_updating = True
                    self.seek_slider.set(pos - self.start_time)
                except tk.TclError:
                    pass
                finally:
                    self._slider_updating = False
            self._timeline_update_counter += 1
            if self.timeline and self.duration > 0 and self._timeline_update_counter % 3 == 0:
                if self.timeline.winfo_exists():
                    w = self.timeline.winfo_width() or 400
                    h = self.timeline_height
                    elapsed = (pos or self.current_position) - self.start_time
                    frac = min(1, max(0, elapsed / self.duration))
                    self.timeline.delete("all")
                    self.timeline.create_rectangle(0, 2, w, h - 2, fill='#30363d', outline='')
                    self.timeline.create_rectangle(0, 2, int(w * frac), h - 2, fill='#00d2ff', outline='')
                    px = int(w * frac)
                    self.timeline.create_line(px, 0, px, h, fill='#f0f6fc', width=2)
        except (tk.TclError, Exception):
            pass

    def _paint_frame_on_main_thread(self):
        """Dipanggil dari main thread (via after(0)): gambar frame dari _pending_* (seek / one-off)."""
        self._paint_scheduled = False
        if self.is_closed or not self._widgets_ok():
            return
        frame = self._pending_frame
        pos = self._pending_position
        self._pending_frame = None
        self._pending_position = None
        if frame is not None:
            self._paint_frame_impl(frame, pos)

    def _schedule_paint(self, frame, position):
        """Antre satu frame untuk digambar di main thread (seek / one-off)."""
        self._pending_frame = frame.copy() if hasattr(frame, 'copy') else frame
        self._pending_position = position
        if not self._paint_scheduled and self.window and self.window.winfo_exists():
            self._paint_scheduled = True
            self.window.after(0, self._paint_frame_on_main_thread)

    def _display_tick(self):
        """Timer main thread (~30 fps): gambar frame terbaru dari buffer playback."""
        if self._display_timer_id is None:
            return
        if self.is_closed or not self._widgets_ok():
            return
        if self.is_playing and self._display_frame is not None:
            frame = self._display_frame
            pos = self._display_position
            self._paint_frame_impl(frame, pos)
        if self.window and self.window.winfo_exists() and not self.is_closed:
            self._display_timer_id = self.window.after(self._display_interval_ms, self._display_tick)

    def _start_display_timer(self):
        self._stop_display_timer()
        if self.window and self.window.winfo_exists():
            self._display_timer_id = self.window.after(self._display_interval_ms, self._display_tick)

    def _stop_display_timer(self):
        if self._display_timer_id and self.window and self.window.winfo_exists():
            try:
                self.window.after_cancel(self._display_timer_id)
            except tk.TclError:
                pass
        self._display_timer_id = None

    def update_frame(self, frame=None):
        """Update canvas. Selalu jadwalkan paint di main thread (hindari Tk dari thread = no glitch)."""
        if self.is_closed or not self._widgets_ok():
            return
        if frame is None:
            try:
                ret, frame = self.cap.read()
            except Exception:
                return
            if not ret or frame is None:
                return
        self._schedule_paint(frame, self.current_position)

    def playback_loop(self):
        """Playback dengan baca frame berurutan (tanpa seek tiap frame) agar video lancar, sinkron ke waktu nyata."""
        frame_delay = 1.0 / self.fps

        while not self.is_closed and self._widgets_ok():
            if self.is_playing:
                if self.current_position >= self.end_time:
                    self.is_playing = False
                    if self.window and self.window.winfo_exists():
                        self.window.after(0, self._set_play_btn_play)
                    self._stop_audio()
                    if self._widgets_ok():
                        self.seek_to(0)
                        delay = self.AUDIO_START_DELAY
                        self._play_start_wall = time.perf_counter() + delay
                        self._play_start_pos = 0
                        self.is_playing = True
                        if self.window and self.window.winfo_exists():
                            self.window.after(int(delay * 1000), self._start_audio)
                    continue

                # Baca frame; posisi frame ini = current_position (sebelum advance)
                try:
                    ret, frame = self.cap.read()
                except Exception:
                    ret = False
                if not ret or frame is None:
                    self.current_position = self.end_time
                    continue

                # Buffer untuk main-thread timer (smooth 30 fps); posisi = waktu frame ini
                self._display_frame = frame.copy() if hasattr(frame, 'copy') else frame
                self._display_position = self.current_position
                self.current_position += frame_delay

                # Sinkron ke waktu nyata (tidur sampai waktu tampil frame berikutnya)
                if self._play_start_wall is not None:
                    target_wall = self._play_start_wall + (self.current_position - self.start_time)
                    sleep_time = target_wall - time.perf_counter()
                    if sleep_time > 0.005:
                        time.sleep(sleep_time)
                else:
                    time.sleep(frame_delay)
            else:
                time.sleep(0.05)
    
    def format_time(self, seconds):
        """Format seconds as MM:SS"""
        minutes = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{minutes:02d}:{secs:02d}"
    
    def close(self):
        """Close the player and release resources"""
        self.is_closed = True
        self.is_playing = False
        self._stop_display_timer()
        self._stop_audio()
        if self.cap:
            self.cap.release()
        if self.window:
            try:
                self.window.destroy()
            except:
                pass


def play_video_segment(video_path, start_time, end_time, title="Video Preview"):
    """
    Convenience function to play a video segment
    
    Args:
        video_path: Path to video file
        start_time: Start time in seconds
        end_time: End time in seconds
        title: Window title
    """
    try:
        player = VideoPlayer(video_path, start_time, end_time, title)
        player.show()
    except Exception as e:
        print(f"[VIDEO PLAYER ERROR] {e}")
        import traceback
        traceback.print_exc()

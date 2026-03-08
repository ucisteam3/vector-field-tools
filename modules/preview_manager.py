"""
Preview Manager Module
Handles video segment preview functionality
"""

import threading
import subprocess
import cv2
import os


class PreviewManager:
    """Manages video segment preview operations"""
    
    def __init__(self, parent):
        """Initialize Preview Manager"""
        self.parent = parent
    
    def preview_selected_segment(self):
        """Play the selected segment in an OpenCV window"""
        selection = self.parent.results_tree.selection()
        if not selection:
            messagebox.showwarning("Peringatan", "Pilih salah satu baris di tabel untuk diputar.")
            return
            
        if not self.parent.video_path or not os.path.exists(self.parent.video_path):
            messagebox.showerror("Kesalahan", "File video tidak ditemukan. Silakan analisis video terlebih dahulu.")
            return
            
        item = self.parent.results_tree.item(selection[0])
        start_str = item['values'][1]
        
        matching_result = None
        for result in self.parent.analysis_results:
            if self.parent.format_time(result['start']) == start_str:
                matching_result = result
                break
        
        if not matching_result:
            return
            
        # Play in background thread to keep UI alive
        threading.Thread(target=self.parent._preview_worker, args=(matching_result,), daemon=True).start()

    def _preview_worker(self, result):
        """Worker thread to play video segment using built-in player"""
        try:
            from modules.video_player import VideoPlayer
            from tkinter import messagebox
            
            start_time = result['start']
            end_time = result['end']
            title = result['topic'][:60]
            
            print(f"  [PREVIEW] Opening built-in player for: {title}")
            
            # Use built-in video player
            try:
                player = VideoPlayer(
                    video_path=self.parent.video_path,
                    start_time=start_time,
                    end_time=end_time,
                    title=title
                )
                player.show()
                return
                
            except Exception as e:
                print(f"  [ERROR] Built-in player failed: {e}")
                import traceback
                traceback.print_exc()
                
                # Fallback: Create temp clip and use system player
                print("  [FALLBACK] Using system player...")
                from pathlib import Path
                import subprocess
                import tempfile
                
                temp_dir = Path("temp") / "previews"
                temp_dir.mkdir(parents=True, exist_ok=True)
                
                # Clean old previews
                for f in temp_dir.glob("*.mp4"):
                    try:
                        f.unlink()
                    except: pass
                
                # Use a very safe filename
                import time
                temp_preview_path = temp_dir / f"preview_{int(time.time())}.mp4"
                
                duration = end_time - start_time
                
                # Encoder configuration (ultrafast for quick preview)
                cmd = [
                    'ffmpeg', '-y',
                    '-ss', f"{start_time:.3f}",
                    '-t', f"{duration:.3f}",
                    '-i', self.parent.video_path,
                    '-c:v', 'libx264',
                    '-preset', 'ultrafast',
                    '-crf', '23',
                    '-c:a', 'aac',
                    '-b:a', '128k',
                    str(temp_preview_path)
                ]
                
                print(f"  [PREVIEW] Generating preview clip...")
                # Run ffmpeg (hide window)
                subprocess.run(cmd, creationflags=0x08000000, check=True)
                
                # Open with system default player
                if os.path.exists(temp_preview_path):
                    print(f"  [SUCCESS] Opening with system player: {temp_preview_path}")
                    os.startfile(temp_preview_path)
                else:
                    raise Exception("Output file not generated")
                
        except Exception as e:
            print(f"Preview error: {e}")
            import traceback
            traceback.print_exc()

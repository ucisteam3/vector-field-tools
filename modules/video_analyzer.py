"""
Video Analyzer Module
Handles video heatmap analysis, duration extraction, and parallel transcription
"""

import os
import cv2
import numpy as np
import subprocess
import tempfile
from pydub import AudioSegment
from concurrent.futures import ThreadPoolExecutor
import time

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False

try:
    from modules.transcription_engine import WHISPER_AVAILABLE
except ImportError:
    WHISPER_AVAILABLE = False


class VideoAnalyzer:
    """Manages video analysis operations including heatmap detection and transcription.
    Backend-safe: works with WebAppContext via safe guards on parent methods."""
    
    def __init__(self, parent):
        """
        Initialize Video Analyzer
        
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
    
    def detect_high_engagement_face(self, frame):
        """Advanced visual analysis using MediaPipe to detect laughter/excitement"""
        if not MEDIAPIPE_AVAILABLE:
            return 0
        if not self.parent or not getattr(self.parent, "advanced_ai_enabled", None):
            return 0
        if not self.parent.advanced_ai_enabled.get():
            return 0
            
        try:
            # MediaPipe is heavy, so we don't run it every frame (handled in loop)
            # This is a simplified heuristic: look for wide mouth open + squinted eyes
            face_mesh = getattr(self.parent, "face_mesh", None)
            if face_mesh is None:
                return 0
            results = face_mesh.process(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            
            if results.multi_face_landmarks:
                # Basic engagement score based on facial landmarks
                # (Pseudo-code for laughter/excitement detection)
                return 0.5 # Return a boost score
        except:
            pass
        return 0

    def analyze_video_heatmap(self, video_path):
        """Analyze video to detect heatmap segments (high activity/engagement areas)"""
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise Exception("Could not open video file")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = total_frames / fps if fps > 0 else 0
        
        frame_activity = []
        prev_frame = None
        
        frame_count = 0
        # Optimize: sample every 1 second instead of 0.5 for faster processing
        sample_rate = max(1, int(fps))  # Sample every 1 second
        
        if self.parent and getattr(self.parent, "advanced_ai_enabled", None) and self.parent.advanced_ai_enabled.get() and MEDIAPIPE_AVAILABLE:
            mp_face_mesh = mp.solutions.face_mesh
            self.parent.face_mesh = mp_face_mesh.FaceMesh(
                static_image_mode=False,
                max_num_faces=1,
                min_detection_confidence=0.5
            )

        while True:
            # Skip frames using grab() for speed
            for _ in range(sample_rate - 1):
                if not cap.grab():
                    break
            
            ret, frame = cap.read()
            if not ret:
                break
            
            # Optimization: Resize frame to very low resolution for activity detection
            small_frame = cv2.resize(frame, (160, 90))
            gray = cv2.cvtColor(small_frame, cv2.COLOR_BGR2GRAY)
            
            # Calculate engagement boost from MediaPipe (Sultan/Mantap mode)
            engagement_boost = 0
            if self.parent and getattr(self.parent, "advanced_ai_enabled", None) and self.parent.advanced_ai_enabled.get() and MEDIAPIPE_AVAILABLE and frame_count % 3 == 0:
                if hasattr(self.parent, "detect_high_engagement_face"):
                    engagement_boost = self.parent.detect_high_engagement_face(frame)
            
            # Calculate frame difference (activity level)
            if prev_frame is not None:
                diff = cv2.absdiff(gray, prev_frame)
                activity = np.mean(diff) + (engagement_boost * 10) # Apply boost
                timestamp = (frame_count * sample_rate) / fps
                frame_activity.append((timestamp, activity))
            
            prev_frame = gray
            
            # Update progress
            frame_count += 1
            if frame_count % 10 == 0:
                progress = min(99, (frame_count * sample_rate / total_frames) * 100)
                if self.parent and hasattr(self.parent, "progress_var"):
                    self.parent.progress_var.set(f"Mencari Golden Moment... {progress:.1f}%")
                if self.parent and hasattr(self.parent, "root"):
                    self.parent.root.update()
        
        cap.release()
        
        print(f"  Total frames analyzed: {len(frame_activity)}")
        
        if not frame_activity:
            print("  WARNING: No frame activity detected!")
            return []
        
        # Normalize activity scores
        activities = [a[1] for a in frame_activity]
        if not activities:
            print("  WARNING: No activities calculated!")
            return []
        
        mean_activity = np.mean(activities)
        std_activity = np.std(activities)
        median_activity = np.median(activities)
        max_activity = np.max(activities)
        min_activity = np.min(activities)
        
        print(f"  Activity stats:")
        print(f"    Mean: {mean_activity:.2f}")
        print(f"    Median: {median_activity:.2f}")
        print(f"    Std: {std_activity:.2f}")
        print(f"    Min: {min_activity:.2f}")
        print(f"    Max: {max_activity:.2f}")
        
        # Use multiple threshold strategies for better detection
        # Strategy 1: Use median as base (more robust to outliers)
        threshold1 = median_activity + (std_activity * 0.1)
        # Strategy 2: Use percentile (top 40% of activities)
        threshold2 = np.percentile(activities, 60)
        # Strategy 3: Use mean with very low multiplier
        threshold3 = mean_activity + (std_activity * 0.05)
        
        # Use the lowest threshold to catch more segments
        threshold = min(threshold1, threshold2, threshold3)
        
        # If threshold is too low, use at least median
        if threshold < median_activity:
            threshold = median_activity
        
        print(f"  Using threshold: {threshold:.2f}")
        
        # Find segments with high activity
        segments = []
        in_segment = False
        segment_start = None
        above_threshold_count = 0
        
        for timestamp, activity in frame_activity:
            if activity > threshold:
                above_threshold_count += 1
                if not in_segment:
                    segment_start = timestamp
                    in_segment = True
            else:
                if in_segment:
                    segment_end = timestamp
                    duration = segment_end - segment_start
                    # Durasi natural: min 10s, max 180s (3 menit)
                    if duration >= 10.0:
                        if duration > 180.0:
                            segment_end = segment_start + 180.0
                        
                        segment_activities = [a for t, a in frame_activity 
                                            if segment_start <= t <= segment_end]
                        segments.append({
                            'start': segment_start,
                            'end': segment_end,
                            'avg_activity': np.mean(segment_activities) if segment_activities else 0
                        })
                    in_segment = False
        
        print(f"  Frames above threshold: {above_threshold_count}/{len(frame_activity)}")
        print(f"  Initial segments found: {len(segments)}")
        
        # Close last segment if still open
        if in_segment and segment_start:
            segment_end = frame_activity[-1][0]
            duration = segment_end - segment_start
            # Durasi natural: min 10s, max 180s
            if duration >= 10.0:
                if duration > 180.0:
                    duration = random.uniform(60.0, 180.0)
                    segment_end = segment_start + duration
                
                segment_activities = [a for t, a in frame_activity 
                                    if segment_start <= t <= segment_end]
                segments.append({
                    'start': segment_start,
                    'end': segment_end,
                    'avg_activity': np.mean(segment_activities) if segment_activities else 0
                })
        
        # If no segments found, use alternative method: create segments from video timeline
        if len(segments) == 0:
            print("  WARNING: No segments found with threshold method!")
            print("  Using alternative method: creating segments from video timeline...")
            
            video_duration = frame_activity[-1][0] if frame_activity else duration
            print(f"  Video duration: {video_duration:.2f} seconds")
            
            # Ensure results are varied with random durations
            overlap = 10.0  # 10 second overlap
            current_start = 0
            while current_start < video_duration - 10:
                # Segment length bervariasi: 10s - 180s (natural)
                segment_length = random.uniform(10.0, 180.0)
                end_time = min(current_start + segment_length, video_duration)
                
                if end_time - current_start >= 10.0:
                    # Calculate average activity for this segment
                    segment_activities = [a for t, a in frame_activity 
                                        if current_start <= t <= end_time]
                    avg_activity = np.mean(segment_activities) if segment_activities else mean_activity
                    
                    segments.append({
                        'start': current_start,
                        'end': end_time,
                        'avg_activity': avg_activity
                    })
                
                current_start += (segment_length - 5.0) # Small overlap for continuity
            
            print(f"  Created {len(segments)} segments using timeline method")
        
        # Get video duration for reference
        video_duration = frame_activity[-1][0] if frame_activity else duration
        
        # Process segments: durasi natural (10s - 180s). Hanya split jika > 3 menit.
        processed_segments = []
        MAX_CLIP = 180.0  # 3 menit
        for segment in segments:
            duration = segment['end'] - segment['start']
            
            # 1. Jika > 180s, split jadi beberapa klip (maks 180s per klip)
            if duration > MAX_CLIP:
                t = segment['start']
                while t < segment['end']:
                    split_end = min(t + MAX_CLIP, segment['end'])
                    if split_end - t >= 10.0:
                        segment_activities = [a for ti, a in frame_activity if t <= ti <= split_end]
                        processed_segments.append({
                            'start': t,
                            'end': split_end,
                            'avg_activity': np.mean(segment_activities) if segment_activities else segment['avg_activity']
                        })
                    t = split_end
            # 2. Durasi 10s - 180s: terima apa adanya (natural)
            elif duration >= 10.0:
                processed_segments.append(segment)
            # 3. Kurang dari 10s: perpanjang sedikit jika bisa (tetap cap 180s)
            elif duration < 10.0 and duration > 0:
                extended_start = max(0, segment['start'] - (10.0 - duration) / 2)
                extended_end = min(video_duration, segment['end'] + (10.0 - duration) / 2)
                if extended_end - extended_start <= MAX_CLIP:
                    segment_activities = [a for t, a in frame_activity if extended_start <= t <= extended_end]
                    processed_segments.append({
                        'start': extended_start,
                        'end': extended_end,
                        'avg_activity': np.mean(segment_activities) if segment_activities else segment['avg_activity']
                    })
        
        # Sort segments by activity (highest first) for better clipper results
        processed_segments.sort(key=lambda x: x['avg_activity'], reverse=True)
        
        # [LIMIT] User request: Maximum 40 segments for high-volume detection
        if len(processed_segments) > 40:
            print(f"  [LIMIT] Clipping segments from {len(processed_segments)} to 40 (Best list)")
            processed_segments = processed_segments[:40]
        
        print(f"  Final processed segments: {len(processed_segments)}")
        
        # [SMART BOUNDARY] Refine segment boundaries using subtitle data
        try:
            from modules.smart_segmentation import refine_all_segments
            
            # Try to find subtitle file
            subtitle_path = None
            if self.parent and hasattr(self.parent, 'current_video_path') and self.parent.current_video_path:
                base_path = os.path.splitext(self.parent.current_video_path)[0]
                potential_subs = [
                    base_path + ".id.vtt",
                    base_path + ".en.vtt",
                    base_path + ".vtt",
                    self.parent.current_video_path + ".vtt"
                ]
                for sub_path in potential_subs:
                    if os.path.exists(sub_path):
                        subtitle_path = sub_path
                        break
            
            if subtitle_path and processed_segments:
                refined_list, stats = refine_all_segments(processed_segments, subtitle_path,
                                                         min_duration=15.0, max_duration=60.0)
                processed_segments = refined_list
        except Exception as e:
            print(f"  [WARNING] Smart boundary refinement failed: {e}")
            # Continue with original segments
        
        return processed_segments

    def get_video_duration(self, video_path):
        """Get video duration using ffprobe (much faster than pydub)"""
        try:
            cmd = [
                'ffprobe', '-v', 'error', '-show_entries', 'format=duration',
                '-of', 'default=noprint_wrappers=1:nokey=1', video_path
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, creationflags=0x08000000)
            return float(result.stdout.strip())
        except:
            return 0

    def extract_audio_and_transcribe(self, video_path):
        """Transcribe audio using parallel processing (Whisper / Google Speech)."""
        if not self.parent or not hasattr(self.parent, "_run_parallel_transcription"):
            return {}
        transcriptions = self.parent._run_parallel_transcription(video_path)
        if not transcriptions or (len(transcriptions) < 2 and WHISPER_AVAILABLE):
            print("  [TRANSCRIPTION] Menggunakan Local Whisper (Akurasi Tinggi)...")
            text = None
            if hasattr(self.parent, "transcribe_video_with_whisper"):
                text = self.parent.transcribe_video_with_whisper(video_path)
            if text:
                return {0: {'start': 0, 'end': 0, 'text': text}}
        return transcriptions

    def transcribe_audio_file(self, audio_path):
        """Transcribe audio using parallel processing."""
        if not self.parent or not hasattr(self.parent, "_run_parallel_transcription"):
            return {}
        return self.parent._run_parallel_transcription(audio_path)

    def _run_parallel_transcription(self, input_path, use_groq=False):
        if not os.path.exists(input_path):
            return {}
        if not self.parent or not hasattr(self.parent, "get_video_duration"):
            return {}

        transcriptions = {}
        try:
            duration = self.parent.get_video_duration(input_path)
            if duration <= 0:
                # Fallback to pydub for duration if ffprobe fails
                try:
                    audio = AudioSegment.from_file(input_path)
                    duration = len(audio) / 1000.0
                except:
                    return {0: {'start': 0, 'end': 0, 'text': '[Gagal mendeteksi durasi audio]'}}
            
            chunk_length = 60  # 60 seconds
            chunks = []
            for start in range(0, int(duration), chunk_length):
                end = min(start + chunk_length, duration)
                chunks.append((start, end, len(chunks)))
            
            r = sr.Recognizer()
            
            def process_chunk(chunk_info):
                start, end, chunk_idx = chunk_info
                actual_duration = end - start
                
                from pathlib import Path
                chunk_wav = Path("temp") / f"chunk_{chunk_idx}_{int(time.time())}.wav"
                
                try:
                    # Direct FFmpeg slicing (extremely fast)
                    cmd = [
                        'ffmpeg', '-y', '-ss', str(start), '-t', str(actual_duration),
                        '-i', input_path, '-vn', '-acodec', 'pcm_s16le', '-ar', '16000', '-ac', '1',
                        chunk_wav
                    ]
                    subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=0x08000000)
                    
                    text = ""
                    if WHISPER_AVAILABLE:
                        try:
                            with sr.AudioFile(chunk_wav) as source:
                                audio_data = r.record(source)
                            text = r.recognize_google(audio_data, language='id')
                        except Exception:
                            text = "[Audio tidak dapat ditranskripsi]"
                    else:
                        with sr.AudioFile(chunk_wav) as source:
                            audio_data = r.record(source)
                        try:
                            text = r.recognize_google(audio_data, language='id')
                        except Exception:
                            text = "[Audio tidak dapat ditranskripsi]"
                    
                    return chunk_idx, {'start': start, 'end': end, 'text': text}
                except Exception as e:
                    return chunk_idx, {'start': start, 'end': end, 'text': f"[Error: {str(e)}]"}
                finally:
                    try:
                        os.unlink(chunk_wav)
                    except:
                        pass

            cpu_cores = os.cpu_count() or 1
            max_workers = min(len(chunks), cpu_cores * 2, 20)
            
            print(f"  [INFO] Hardware Terdeteksi: {cpu_cores} Cores. Menggunakan {max_workers} worker threads.")
            print(f"  [INFO] Transkripsi paralel dimulai...")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                results = list(executor.map(process_chunk, chunks))
            
            # Sort results by index to ensure order
            for idx, data in sorted(results, key=lambda x: x[0]):
                transcriptions[idx] = data
                
        except Exception as e:
            print(f"Transcription error: {e}")
            return {0: {'start': 0, 'end': 0, 'text': f'[Error: {str(e)}]'}}
        
        return transcriptions


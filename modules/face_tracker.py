"""
Face Tracking Module for Smart 9:16 Crop Export
Uses MediaPipe to detect faces and create dynamic crop following face positions
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict

try:
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False
    print("[FACE_TRACKER] MediaPipe not available - face tracking disabled")


class FaceTracker:
    """
    Tracks faces in video frames and calculates optimal 9:16 crop positions
    """
    
    def __init__(self, min_detection_confidence=0.5, smoothing_window=30):
        """
        Initialize face tracker
        
        Args:
            min_detection_confidence: Minimum confidence for face detection (0.0-1.0)
            smoothing_window: Number of frames to smooth tracking (reduces jitter)
        """
        self.smoothing_window = smoothing_window
        self.face_detector = None
        
        if MEDIAPIPE_AVAILABLE:
            try:
                # MediaPipe 0.10.x uses tasks API
                from mediapipe.tasks import python
                from mediapipe.tasks.python import vision
                import os
                
                # Get model path
                model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'blaze_face_short_range.tflite')
                model_path = os.path.abspath(model_path)
                
                # Download model if not exists
                if not os.path.exists(model_path):
                    print(f"[FACE_TRACKER] Downloading face detection model...")
                    os.makedirs(os.path.dirname(model_path), exist_ok=True)
                    import urllib.request
                    urllib.request.urlretrieve(
                        'https://storage.googleapis.com/mediapipe-models/face_detector/blaze_face_short_range/float16/1/blaze_face_short_range.tflite',
                        model_path
                    )
                    print(f"[FACE_TRACKER] Model downloaded to {model_path}")
                
                # Create FaceDetector options
                base_options = python.BaseOptions(model_asset_path=model_path)
                options = vision.FaceDetectorOptions(
                    base_options=base_options,
                    min_detection_confidence=min_detection_confidence
                )
                
                self.face_detector = vision.FaceDetector.create_from_options(options)
                self.detector_type = "tasks"  # New API
                print(f"[FACE_TRACKER] Initialized with model: {model_path}")
            except Exception as e:
                print(f"[FACE_TRACKER] Could not initialize MediaPipe tasks API: {e}")
                self.face_detector = None
    
    def detect_faces_in_frame(self, frame: np.ndarray) -> List[Dict]:
        """
        Detect faces in a single frame
        
        Args:
            frame: BGR image from cv2
            
        Returns:
            List of face dictionaries with 'bbox' and 'confidence' keys
        """
        if not MEDIAPIPE_AVAILABLE or self.face_detector is None:
            return []
        
        try:
            # Convert BGR to RGB for MediaPipe
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Create MediaPipe Image
            from mediapipe import Image, ImageFormat
            mp_image = Image(image_format=ImageFormat.SRGB, data=rgb_frame)
            
            # Detect faces
            detection_result = self.face_detector.detect(mp_image)
            
            if not detection_result.detections:
                return []
            
            faces = []
            h, w = frame.shape[:2]
            
            for detection in detection_result.detections:
                # Get bounding box
                bbox = detection.bounding_box
                
                # Convert to absolute pixels
                x = bbox.origin_x
                y = bbox.origin_y
                width = bbox.width
                height = bbox.height
                
                # Calculate center point
                center_x = x + width // 2
                center_y = y + height // 2
                
                # Get confidence score
                confidence = detection.categories[0].score if detection.categories else 0.5
                
                faces.append({
                    'bbox': (x, y, width, height),
                    'center': (center_x, center_y),
                    'confidence': confidence,
                    'size': width * height  # For prioritizing larger faces
                })
            
            return faces
        except Exception as e:
            print(f"[FACE_TRACKER] Detection error: {e}")
            return []
    
    def calculate_crop_center(self, faces: List[Dict], frame_width: int, frame_height: int) -> int:
        """
        Calculate optimal horizontal center for 9:16 crop based on detected faces
        
        Args:
            faces: List of face dictionaries from detect_faces_in_frame
            frame_width: Width of the video frame
            frame_height: Height of the video frame
            
        Returns:
            X-coordinate for crop center (horizontal position)
        """
        if not faces:
            # No faces detected - return center
            return frame_width // 2
        
        # If multiple faces, prioritize by size and confidence
        # Weight: 70% size, 30% confidence
        weighted_centers = []
        total_weight = 0
        
        for face in faces:
            weight = (face['size'] * 0.7) + (face['confidence'] * 1000 * 0.3)
            weighted_centers.append((face['center'][0], weight))
            total_weight += weight
        
        # Calculate weighted average center
        if total_weight > 0:
            weighted_x = sum(x * w for x, w in weighted_centers) / total_weight
            return int(weighted_x)
        
        return frame_width // 2
    
    def smooth_tracking(self, positions: List[int], window_size: Optional[int] = None) -> List[int]:
        """
        Apply temporal smoothing to tracking positions to reduce jitter
        
        Args:
            positions: List of X-coordinates over time
            window_size: Size of smoothing window (default: self.smoothing_window)
            
        Returns:
            Smoothed list of positions
        """
        if window_size is None:
            window_size = self.smoothing_window
        
        if len(positions) < 2:
            return positions
        
        smoothed = []
        for i in range(len(positions)):
            # Get window around current position
            start = max(0, i - window_size // 2)
            end = min(len(positions), i + window_size // 2 + 1)
            window = positions[start:end]
            
            # Use median for robustness against outliers
            smoothed.append(int(np.median(window)))
        
        return smoothed
    
    def get_crop_box(self, center_x: int, frame_width: int, frame_height: int) -> Tuple[int, int, int, int]:
        """
        Calculate 9:16 crop box coordinates given a center X position
        
        Args:
            center_x: Desired horizontal center of crop
            frame_width: Width of the video frame
            frame_height: Height of the video frame
            
        Returns:
            Tuple of (x, y, width, height) for crop box
        """
        # Calculate 9:16 crop dimensions
        crop_height = frame_height
        crop_width = int(crop_height * 9 / 16)
        
        # Ensure crop width doesn't exceed frame width
        if crop_width > frame_width:
            crop_width = frame_width
            crop_height = int(crop_width * 16 / 9)
        
        # Calculate X position (centered on center_x)
        crop_x = center_x - crop_width // 2
        
        # Clamp to frame boundaries
        crop_x = max(0, min(crop_x, frame_width - crop_width))
        crop_y = (frame_height - crop_height) // 2  # Vertically centered
        
        return (crop_x, crop_y, crop_width, crop_height)
    
    def analyze_video_for_faces(self, video_path: str, sample_rate: int = 30, start_time: float = 0, duration: float = None) -> List[int]:
        """
        Analyze video segment and return smoothed crop center positions for each frame
        
        Args:
            video_path: Path to video file
            sample_rate: Analyze every Nth frame for speed (default: 30 = 1 FPS for 30fps video)
            start_time: Start time in seconds (default: 0 = beginning of video)
            duration: Duration in seconds to analyze (default: None = entire video)
            
        Returns:
            List of X-coordinates for crop center at each frame
        """
        if not MEDIAPIPE_AVAILABLE:
            print("[FACE_TRACKER] MediaPipe not available - using center crop")
            cap = cv2.VideoCapture(video_path)
            
            # Calculate frame count for the segment
            fps = cap.get(cv2.CAP_PROP_FPS)
            if duration:
                frame_count = int(duration * fps)
            else:
                frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            cap.release()
            return [width // 2] * frame_count
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        frame_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        
        # Calculate segment boundaries
        start_frame = int(start_time * fps)
        if duration:
            end_frame = int((start_time + duration) * fps)
            frame_count = end_frame - start_frame
        else:
            end_frame = total_frames
            frame_count = total_frames - start_frame
        
        print(f"[FACE_TRACKER] Analyzing segment: {start_time:.1f}s - {start_time + (duration or 0):.1f}s")
        print(f"[FACE_TRACKER] Frames {start_frame} - {end_frame} ({frame_count} frames, {frame_width}x{frame_height})")
        
        # Seek to start position
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)
        
        # Sample frames and detect faces
        raw_positions = []
        last_known_position = frame_width // 2
        
        frame_idx = 0
        while frame_idx < frame_count:
            ret, frame = cap.read()
            if not ret:
                break
            
            # Only analyze every Nth frame
            if frame_idx % sample_rate == 0:
                # Resize frame for faster processing
                small_frame = cv2.resize(frame, (640, 360))
                faces = self.detect_faces_in_frame(small_frame)
                
                # Scale back to original resolution
                scale_x = frame_width / 640
                for face in faces:
                    face['center'] = (int(face['center'][0] * scale_x), face['center'][1])
                    face['size'] = int(face['size'] * scale_x * scale_x)
                
                if faces:
                    center_x = self.calculate_crop_center(faces, frame_width, frame_height)
                    last_known_position = center_x
                else:
                    # No face detected - use last known position
                    center_x = last_known_position
                
                raw_positions.append(center_x)
            
            frame_idx += 1
            
            # Progress indicator
            if frame_idx % 300 == 0:
                progress = (frame_idx / frame_count) * 100
                print(f"  Progress: {progress:.1f}%")
        
        cap.release()
        
        # Interpolate positions for all frames
        full_positions = self._interpolate_positions(raw_positions, frame_count, sample_rate)
        
        # Apply smoothing
        smoothed_positions = self.smooth_tracking(full_positions)
        
        print(f"[FACE_TRACKER] Analysis complete - {len(smoothed_positions)} positions generated")
        return smoothed_positions
    
    def _interpolate_positions(self, sampled_positions: List[int], total_frames: int, sample_rate: int) -> List[int]:
        """
        Interpolate positions for frames that weren't sampled
        
        Args:
            sampled_positions: Positions from sampled frames
            total_frames: Total number of frames in video
            sample_rate: How many frames between samples
            
        Returns:
            List of positions for all frames
        """
        if not sampled_positions:
            return [0] * total_frames
        
        full_positions = []
        for i in range(total_frames):
            sample_idx = i // sample_rate
            
            if sample_idx >= len(sampled_positions):
                # Beyond last sample - use last position
                full_positions.append(sampled_positions[-1])
            elif i % sample_rate == 0:
                # Exact sample point
                full_positions.append(sampled_positions[sample_idx])
            else:
                # Interpolate between samples
                if sample_idx + 1 < len(sampled_positions):
                    pos1 = sampled_positions[sample_idx]
                    pos2 = sampled_positions[sample_idx + 1]
                    ratio = (i % sample_rate) / sample_rate
                    interpolated = int(pos1 + (pos2 - pos1) * ratio)
                    full_positions.append(interpolated)
                else:
                    full_positions.append(sampled_positions[sample_idx])
        
        return full_positions
    
    def close(self):
        """Clean up resources"""
        if self.face_detector:
            self.face_detector.close()

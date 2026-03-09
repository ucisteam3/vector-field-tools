"""
Podcast Smart Tracker - Active speaker detection for 9:16 vertical podcast export.
When two speakers are left/right, the camera dynamically focuses on the person speaking.
Uses face detection + motion (mouth movement proxy) to determine active speaker.
"""

import cv2
import numpy as np
from typing import List, Tuple, Optional, Dict
from pathlib import Path

try:
    from modules.face_tracker import FaceTracker
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False


def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation. t=0.15 for smooth camera movement."""
    return a + (b - a) * t


class PodcastSmartTracker:
    """
    Tracks faces in podcast layout (left/right) and crops around active speaker.
    - Face detection via MediaPipe (FaceTracker)
    - Active speaker = face with higher motion (mouth movement proxy via frame diff)
    - Smooth camera: lerp(prev_x, target_x, 0.15)
    - Safe face margin: padding around face
    - Double speaker: zoom out to include both faces
    """

    def __init__(
        self,
        smoothing_factor: float = 0.15,
        face_margin: float = 1.4,
        motion_threshold: float = 8.0,
        both_speak_ratio: float = 0.6,
    ):
        """
        Args:
            smoothing_factor: lerp factor (0.15 = smooth camera)
            face_margin: padding multiplier around face (1.4 = 40% extra space)
            motion_threshold: min motion to consider "speaking"
            both_speak_ratio: when motion ratio between faces > this, zoom out
        """
        self.smoothing_factor = smoothing_factor
        self.face_margin = face_margin
        self.motion_threshold = motion_threshold
        self.both_speak_ratio = both_speak_ratio
        self.face_tracker: Optional[FaceTracker] = None
        if MEDIAPIPE_AVAILABLE:
            try:
                self.face_tracker = FaceTracker(smoothing_window=15)
            except Exception as e:
                print(f"[PODCAST_SMART] FaceTracker init: {e}")

    def detect_faces(self, frame: np.ndarray) -> List[Dict]:
        """Detect faces in frame. Returns list of {bbox, center, confidence, size}."""
        if not self.face_tracker:
            return []
        return self.face_tracker.detect_faces_in_frame(frame)

    def _compute_face_motion(
        self,
        frame: np.ndarray,
        prev_frame: np.ndarray,
        faces: List[Dict],
    ) -> List[float]:
        """Compute motion (mean abs diff) in each face region. Proxy for mouth movement."""
        if prev_frame is None or frame is None:
            return [0.0] * len(faces)

        motions = []
        h, w = frame.shape[:2]
        for face in faces:
            x, y, fw, fh = face["bbox"]
            # Clamp to frame
            x = max(0, min(int(x), w - 2))
            y = max(0, min(int(y), h - 2))
            fw = max(2, min(int(fw), w - x))
            fh = max(2, min(int(fh), h - y))
            roi_curr = frame[y : y + fh, x : x + fw]
            roi_prev = prev_frame[y : y + fh, x : x + fw]
            if roi_curr.size and roi_prev.size and roi_curr.shape == roi_prev.shape:
                diff = cv2.absdiff(roi_curr, roi_prev)
                motions.append(float(np.mean(diff)))
            else:
                motions.append(0.0)
        return motions

    def _get_target_crop(
        self,
        faces: List[Dict],
        motions: List[float],
        frame_width: int,
        frame_height: int,
    ) -> Tuple[float, float, float, float]:
        """
        Compute target crop (x, y, w, h) for current frame.
        - Single active speaker: crop around that face with margin
        - Both speaking: zoom out to include both faces
        - No faces: center crop
        """
        crop_height = frame_height
        crop_width = int(crop_height * 9 / 16)
        if crop_width > frame_width:
            crop_width = frame_width
            crop_height = int(crop_width * 16 / 9)

        # Safe center crop when no faces — never return (0,0)
        if not faces:
            cx = frame_width / 2
            cy = frame_height / 2
            crop_x = max(0, min(cx - crop_width / 2, frame_width - crop_width))
            crop_y = max(0, min(cy - crop_height / 2, frame_height - crop_height))
            return (crop_x, crop_y, crop_width, crop_height)

        # Determine active speaker(s)
        if len(faces) == 1:
            f = faces[0]
            cx, cy = f["center"]
            # Apply face margin: expand bbox
            _, _, fw, fh = f["bbox"]
            pad_w = fw * (self.face_margin - 1) / 2
            pad_h = fh * (self.face_margin - 1) / 2
            # Target: center crop on face with room around
            target_cx = cx
            target_cy = cy
        else:
            # Two (or more) faces - check if both speaking
            m0 = motions[0] if len(motions) > 0 else 0
            m1 = motions[1] if len(motions) > 1 else 0
            total = m0 + m1
            if total < self.motion_threshold:
                # Neither speaking - safe center crop (never (0,0))
                cx = frame_width / 2
                cy = frame_height / 2
                crop_x = max(0, min(cx - crop_width / 2, frame_width - crop_width))
                crop_y = max(0, min(cy - crop_height / 2, frame_height - crop_height))
                return (crop_x, crop_y, crop_width, crop_height)
            ratio = min(m0, m1) / max(m0, m1) if max(m0, m1) > 0 else 0
            if ratio >= self.both_speak_ratio:
                # Both speaking - zoom out: crop to include both faces
                xs = [f["center"][0] for f in faces[:2]]
                ys = [f["center"][1] for f in faces[:2]]
                xmin = min(xs[0] - faces[0]["bbox"][2] * self.face_margin / 2,
                          xs[1] - faces[1]["bbox"][2] * self.face_margin / 2)
                xmax = max(xs[0] + faces[0]["bbox"][2] * self.face_margin / 2,
                          xs[1] + faces[1]["bbox"][2] * self.face_margin / 2)
                span = xmax - xmin
                # Ensure crop width encompasses both with margin
                crop_w_needed = max(crop_width, span * 1.2)
                if crop_w_needed > frame_width:
                    crop_w_needed = frame_width
                crop_h_needed = int(crop_w_needed * 16 / 9)
                if crop_h_needed > frame_height:
                    crop_h_needed = frame_height
                    crop_w_needed = int(crop_h_needed * 9 / 16)
                target_cx = (min(xs) + max(xs)) / 2
                target_cy = frame_height / 2
                crop_width = int(crop_w_needed)
                crop_height = crop_h_needed
            else:
                # Single speaker - focus on face with more motion
                idx = 0 if m0 >= m1 else 1
                f = faces[idx]
                target_cx = f["center"][0]
                target_cy = f["center"][1]

        crop_x = target_cx - crop_width / 2
        crop_y = (frame_height - crop_height) / 2
        crop_x = max(0, min(crop_x, frame_width - crop_width))
        crop_y = max(0, min(crop_y, frame_height - crop_height))
        return (crop_x, crop_y, crop_width, crop_height)

    def analyze_video(
        self,
        video_path: str,
        start_time: float = 0,
        duration: Optional[float] = None,
        sample_rate: int = 5,
    ) -> List[Tuple[int, int, int, int]]:
        """
        Lightweight 1 FPS analysis: sample one frame per second, detect faces, build crop
        timeline, interpolate to per-frame, smooth, return crop boxes. No full-frame scan.
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        dur = duration if duration and duration > 0 else 30.0
        start_frame = int(start_time * fps)
        total_frames = int(dur * fps)
        frames_per_sec = max(1, int(fps))

        crop_height = h
        crop_width = min(w, int(h * 9 / 16))
        if crop_width >= w:
            crop_width = w
            crop_height = int(crop_width * 16 / 9)
        center_y = (h - crop_height) // 2

        def center_x_to_box(cx: float) -> Tuple[int, int, int, int]:
            cx_int = int(cx)
            x = max(0, min(cx_int - crop_width // 2, w - crop_width))
            y = max(0, min(center_y, h - crop_height))
            return (x, y, crop_width, crop_height)

        # Fallback: static center crop (no MediaPipe or on failure)
        if not self.face_tracker:
            cap.release()
            cx = w // 2
            box = center_x_to_box(cx)
            return [box] * total_frames

        # ~sample_rate FPS sampling: sample_interval = fps / sample_rate (e.g. 5 FPS when sample_rate=5)
        sample_interval = max(1, int(fps / sample_rate))
        n_samples = max(1, (total_frames + sample_interval - 1) // sample_interval)
        timeline: List[float] = []
        last_center_x = float(w // 2)
        prev_frame = None

        for i in range(n_samples):
            frame_pos = min(start_frame + i * sample_interval, start_frame + total_frames - 1)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
            ret, frame = cap.read()
            if not ret:
                timeline.append(last_center_x)
                continue
            small = cv2.resize(frame, (640, 360))
            scale_x = w / 640
            scale_y = h / 360
            faces = self.detect_faces(small)
            # Motion uses small frame and small bbox
            motions = self._compute_face_motion(small, prev_frame, faces) if prev_frame is not None else []
            for f in faces:
                f["center"] = (f["center"][0] * scale_x, f["center"][1] * scale_y)
                f["bbox"] = (
                    f["bbox"][0] * scale_x,
                    f["bbox"][1] * scale_y,
                    f["bbox"][2] * scale_x,
                    f["bbox"][3] * scale_y,
                )
                f["size"] = f["bbox"][2] * f["bbox"][3]
            if faces:
                # Choose active speaker by motion; fallback to largest face
                if motions and len(motions) == len(faces):
                    idx = int(np.argmax(motions))
                    speaker = faces[idx]
                else:
                    faces.sort(key=lambda f: f["size"], reverse=True)
                    speaker = faces[0]
                center_x = speaker["center"][0]
                last_center_x = center_x
            else:
                center_x = last_center_x
            timeline.append(center_x)
            prev_frame = small.copy()

        cap.release()

        # Step 5: Interpolate sampled positions to per-frame (repeat each value sample_interval times)
        positions: List[float] = []
        for i in range(n_samples):
            idx = min(i, len(timeline) - 1)
            val = timeline[idx]
            for _ in range(sample_interval):
                positions.append(val)
        positions = positions[:total_frames]
        if len(positions) < total_frames:
            last = positions[-1] if positions else (w // 2)
            positions.extend([last] * (total_frames - len(positions)))

        # Step 6: Smoothing via _lerp(prev, curr, smoothing_factor)
        smoothed: List[float] = []
        for i in range(len(positions)):
            if i == 0:
                smoothed.append(positions[0])
            else:
                s = _lerp(smoothed[i - 1], positions[i], self.smoothing_factor)
                smoothed.append(s)

        # Step 7: Return crop boxes (x, y, w, h) per frame
        crop_boxes = [center_x_to_box(s) for s in smoothed]
        print(f"  [PODCAST_SMART] ~{sample_rate} FPS analysis done: {n_samples} samples -> {len(crop_boxes)} frames")
        return crop_boxes

    def close(self):
        if self.face_tracker and hasattr(self.face_tracker, "close"):
            self.face_tracker.close()

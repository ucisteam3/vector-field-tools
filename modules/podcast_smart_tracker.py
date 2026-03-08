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

        if not faces:
            cx = frame_width / 2
            cy = frame_height / 2
            return (cx - crop_width / 2, cy - crop_height / 2, crop_width, crop_height)

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
                # Neither speaking - use last or center
                return (0, 0, crop_width, crop_height)
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
        Analyze video and return per-frame crop boxes (x, y, w, h).
        Uses frame differencing for active speaker, lerp for smoothing.
        """
        if not self.face_tracker:
            cap = cv2.VideoCapture(video_path)
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = cap.get(cv2.CAP_PROP_FPS)
            cap.release()
            crop_w = min(w, int(h * 9 / 16))
            crop_h = int(crop_w * 16 / 9)
            cx = w // 2
            cy = h // 2
            x = max(0, cx - crop_w // 2)
            y = max(0, cy - crop_h // 2)
            n = int((duration or 30) * fps)
            return [(x, y, crop_w, crop_h)] * n

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        start_frame = int(start_time * fps)
        end_frame = int((start_time + (duration or 999999)) * fps) if duration else int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        crop_height = h
        crop_width = min(w, int(h * 9 / 16))
        if crop_width == w:
            crop_height = int(crop_width * 16 / 9)

        sampled: List[Tuple[int, int, int, int]] = []
        prev_frame = None
        prev_crop = (max(0, (w - crop_width) // 2), (h - crop_height) // 2, crop_width, crop_height)
        n_total = end_frame - start_frame
        frame_idx = 0

        while frame_idx < n_total:
            ret, frame = cap.read()
            if not ret:
                break

            target_crop = prev_crop
            if frame_idx % sample_rate == 0:
                small = cv2.resize(frame, (640, 360))
                scale_x = w / 640
                scale_y = h / 360

                faces = self.detect_faces(small)
                for f in faces:
                    f["center"] = (int(f["center"][0] * scale_x), int(f["center"][1] * scale_y))
                    f["bbox"] = (
                        int(f["bbox"][0] * scale_x),
                        int(f["bbox"][1] * scale_y),
                        int(f["bbox"][2] * scale_x),
                        int(f["bbox"][3] * scale_y),
                    )
                    f["size"] = f["bbox"][2] * f["bbox"][3]

                motions = self._compute_face_motion(frame, prev_frame or frame, faces)
                tx, ty, tw, th = self._get_target_crop(faces, motions, w, h)
                prev_x, prev_y, _, _ = prev_crop
                t = self.smoothing_factor
                crop_x = int(_lerp(prev_x, tx, t))
                crop_y = int(_lerp(prev_y, ty, t))
                crop_x = max(0, min(crop_x, w - crop_width))
                crop_y = max(0, min(crop_y, h - crop_height))
                target_crop = (crop_x, crop_y, crop_width, crop_height)
                prev_crop = target_crop
                prev_frame = frame.copy()

            sampled.append(prev_crop)
            frame_idx += 1

            if frame_idx % 150 == 0:
                print(f"  [PODCAST_SMART] Frame {frame_idx}/{n_total}")

        cap.release()
        return sampled

    def close(self):
        if self.face_tracker and hasattr(self.face_tracker, "close"):
            self.face_tracker.close()

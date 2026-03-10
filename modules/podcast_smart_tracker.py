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
        emotion_threshold: float = 18.0,
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
        self.emotion_threshold = emotion_threshold
        self.face_tracker: Optional[FaceTracker] = None
        if MEDIAPIPE_AVAILABLE:
            try:
                self.face_tracker = FaceTracker(smoothing_window=15)
            except Exception as e:
                print(f"[PODCAST_SMART] FaceTracker init: {e}")

        # Laughter markers (optional transcript-based zoom)
        self.laughter_keywords = ["haha", "wkwk", "tertawa", "(laugh)", "[laugh]"]

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
        """
        Compute active-speaker motion score per face.
        Enhanced: motion_score = (mouth_motion * 1.6) + (face_motion * 0.4)
        where mouth_motion is computed on the lower part of the face box.
        """
        if prev_frame is None or frame is None:
            return [0.0] * len(faces)

        motions: List[float] = []
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
            if not (roi_curr.size and roi_prev.size and roi_curr.shape == roi_prev.shape):
                motions.append(0.0)
                continue

            # Face motion (overall)
            diff_face = cv2.absdiff(roi_curr, roi_prev)
            face_motion = float(np.mean(diff_face))

            # Mouth motion (lower region of face) - stronger indicator of speaking
            mouth_y0 = int(fh * 0.62)
            mouth_y0 = max(0, min(mouth_y0, fh - 2))
            mouth_curr = roi_curr[mouth_y0:fh, :]
            mouth_prev = roi_prev[mouth_y0:fh, :]
            if mouth_curr.size and mouth_prev.size and mouth_curr.shape == mouth_prev.shape:
                diff_mouth = cv2.absdiff(mouth_curr, mouth_prev)
                mouth_motion = float(np.mean(diff_mouth))
            else:
                mouth_motion = 0.0

            motion_score = (mouth_motion * 1.6) + (face_motion * 0.4)
            motions.append(motion_score)
        return motions

    def _get_target_crop(
        self,
        faces: List[Dict],
        motions: List[float],
        frame_width: int,
        frame_height: int,
        *,
        emotion_score: float = 0.0,
        laugh_active: bool = False,
    ) -> Tuple[float, float, float, float]:
        """
        Compute target crop (x, y, w, h) for current frame.
        - Single active speaker: crop around that face with margin
        - Both speaking: zoom out to include both faces
        - No faces: center crop
        """
        # STEP 1 — ALWAYS CROP BASED ON VIDEO HEIGHT (perfect 9:16 region)
        crop_height = frame_height
        crop_width = int(frame_height * 9 / 16)
        crop_width = max(2, min(crop_width, frame_width))

        # Safe center crop when no faces — never return (0,0)
        if not faces:
            center_x = frame_width / 2
            crop_x = max(0, min(center_x - crop_width / 2, frame_width - crop_width))
            return (crop_x, 0.0, crop_width, crop_height)

        # Determine active speaker(s)
        if len(faces) == 1:
            f = faces[0]
            fx, fy, fw, fh = f["bbox"]
            face_center = fx + (fw / 2.0)
            target_cx = face_center
        else:
            # Two (or more) faces - check if both speaking
            m0 = motions[0] if len(motions) > 0 else 0
            m1 = motions[1] if len(motions) > 1 else 0
            total = m0 + m1
            if total < self.motion_threshold:
                # Neither speaking - safe center crop
                center_x = frame_width / 2
                crop_x = max(0, min(center_x - crop_width / 2, frame_width - crop_width))
                return (crop_x, 0.0, crop_width, crop_height)
            # Dual speaker mode when both motion scores are similar
            denom = max(m0, m1) if max(m0, m1) > 0 else 1.0
            similar = abs(m0 - m1) / denom < 0.35
            if similar:
                # STEP 4 — DUAL SPEAKER MODE: include both faces, but keep fixed 9:16 width
                f1, f2 = faces[0], faces[1]
                x1, y1, w1, h1 = f1["bbox"]
                x2, y2, w2, h2 = f2["bbox"]
                min_x = min(x1, x2)
                max_x = max(x1 + w1, x2 + w2)
                center_x = (min_x + max_x) / 2.0
                target_cx = center_x
            else:
                # Single speaker - focus on face with more motion
                # Face priority: size * 0.6 + motion_score * 0.4
                scores = []
                for i in range(2):
                    f = faces[i]
                    size = float(f.get("size") or (f["bbox"][2] * f["bbox"][3]))
                    mot = float(motions[i]) if i < len(motions) else 0.0
                    scores.append((size * 0.6 + mot * 0.4, i))
                idx = max(scores, key=lambda t: t[0])[1] if scores else (0 if m0 >= m1 else 1)
                f = faces[idx]
                fx, fy, fw, fh = f["bbox"]
                face_center = fx + (fw / 2.0)
                target_cx = face_center

        # STEP 6 — CLAMP CROP AREA, y always 0 for full-height vertical crop
        crop_x = target_cx - crop_width / 2
        crop_x = max(0, min(crop_x, frame_width - crop_width))
        return (crop_x, 0.0, crop_width, crop_height)

    def analyze_video(
        self,
        video_path: str,
        start_time: float = 0,
        duration: Optional[float] = None,
        sample_rate: int = 5,
        transcript_text: Optional[str] = None,
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

        # Faster sampling for responsiveness: ~5 samples per second
        sample_interval = max(1, int(fps / 5))
        n_samples = max(1, (total_frames + sample_interval - 1) // sample_interval)
        timeline: List[Tuple[float, float, float, float]] = []
        # Default: safe center crop box
        last_box = (float((w - crop_width) // 2), float(center_y), float(crop_width), float(crop_height))
        prev_frame = None
        # Laughter zoom window (2 seconds)
        laugh_zoom_frames = 0
        if transcript_text:
            tt = (transcript_text or "").lower()
            if any(k in tt for k in self.laughter_keywords):
                laugh_zoom_frames = int(max(1.0, fps) * 2)

        for i in range(n_samples):
            frame_pos = min(start_frame + i * sample_interval, start_frame + total_frames - 1)
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_pos)
            ret, frame = cap.read()
            if not ret:
                timeline.append(last_box)
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
            # Visual motion (frame intensity) for emotion-aware zoom
            visual_motion = 0.0
            if prev_frame is not None and prev_frame.shape == small.shape and prev_frame.size and small.size:
                try:
                    visual_motion = float(np.mean(cv2.absdiff(small, prev_frame)))
                except Exception:
                    visual_motion = 0.0
            speech_motion = float(max(motions) if motions else 0.0)
            emotion_score = (speech_motion * 0.7) + (visual_motion * 0.3)
            laugh_active = laugh_zoom_frames > 0

            # Target crop from enhanced active-speaker + dual-speaker logic; safe center crop if none
            target = self._get_target_crop(
                faces,
                motions,
                w,
                h,
                emotion_score=emotion_score,
                laugh_active=laugh_active,
            )
            last_box = target
            timeline.append(target)
            prev_frame = small.copy()
            if laugh_zoom_frames > 0:
                laugh_zoom_frames -= sample_interval

        cap.release()

        # Step 5: Interpolate sampled boxes to per-frame (repeat each value sample_interval times)
        positions: List[Tuple[float, float, float, float]] = []
        for i in range(n_samples):
            idx = min(i, len(timeline) - 1)
            val = timeline[idx]
            for _ in range(sample_interval):
                positions.append(val)
        positions = positions[:total_frames]
        if len(positions) < total_frames:
            last = positions[-1] if positions else last_box
            positions.extend([last] * (total_frames - len(positions)))

        # Step 6: Smoothing (x only) + jump-cut reduction
        smoothed_x: List[float] = []
        for i, (x, _y, _cw, _ch) in enumerate(positions):
            if i == 0:
                smoothed_x.append(float(x))
                continue
            px = smoothed_x[i - 1]
            sx = _lerp(px, float(x), self.smoothing_factor)
            # Jump cut reduction: clamp movement if it changes too fast
            if abs(sx - px) > w * 0.25:
                sx = px + (w * 0.15 if sx > px else -w * 0.15)
            smoothed_x.append(sx)

        # Step 7: Return crop boxes (x, y, w, h) per frame (always full-height 9:16)
        crop_boxes: List[Tuple[int, int, int, int]] = []
        crop_w = int(h * 9 / 16)
        crop_h = h
        # SAFE CROP VALIDATION
        if crop_w <= 0 or crop_h <= 0:
            crop_w = int(h * 9 / 16)
            crop_h = h
        crop_w = max(2, min(crop_w, w))
        for x in smoothed_x:
            x_i = int(x)
            x_i = max(0, min(x_i, w - crop_w))
            crop_boxes.append((x_i, 0, crop_w, crop_h))
        print(f"  [PODCAST_SMART] ~{sample_rate} FPS analysis done: {n_samples} samples -> {len(crop_boxes)} frames")
        return crop_boxes

    def close(self):
        if self.face_tracker and hasattr(self.face_tracker, "close"):
            self.face_tracker.close()

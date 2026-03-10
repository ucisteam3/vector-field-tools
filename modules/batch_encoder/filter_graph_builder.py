from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple


def _q(path: str) -> str:
    """Escape for FFmpeg filter args (Windows friendly)."""
    if not path:
        return path
    p = path.replace("\\", "/")
    p = p.replace(":", r"\:")
    return p


@dataclass
class BatchClipSpec:
    start: float
    end: float
    output: str
    crop: Optional[Tuple[int, int, int, int]] = None  # (w,h,x,y)
    scale: Optional[Tuple[int, int]] = None  # (w,h)
    subtitles_ass: Optional[str] = None
    fonts_dir: Optional[str] = None


class FilterGraphBuilder:
    """
    Build a filter_complex graph that renders N clips from one input:
      - split video into N streams
      - trim video/audio per clip
      - apply crop->scale->subtitles per clip
    """

    def build(self, clips: List[BatchClipSpec]) -> str:
        if not clips:
            raise ValueError("No clips to build filtergraph")

        n = len(clips)
        parts: List[str] = []

        # Split video
        v_splits = "".join([f"[v{i}]" for i in range(n)])
        parts.append(f"[0:v]split={n}{v_splits}")

        # Split audio if present (best-effort). If input has no audio, mapping will fail unless handled by caller.
        a_splits = "".join([f"[a{i}]" for i in range(n)])
        parts.append(f"[0:a]asplit={n}{a_splits}")

        for i, c in enumerate(clips):
            start = max(0.0, float(c.start))
            end = max(start, float(c.end))

            chain: List[str] = []
            chain.append(f"trim=start={start:.3f}:end={end:.3f}")
            chain.append("setpts=PTS-STARTPTS")
            if c.crop:
                cw, ch, cx, cy = c.crop
                chain.append(f"crop={int(cw)}:{int(ch)}:{int(cx)}:{int(cy)}")
            if c.scale:
                sw, sh = c.scale
                chain.append(f"scale={int(sw)}:{int(sh)}:flags=lanczos")
            if c.subtitles_ass:
                p = _q(c.subtitles_ass)
                if c.fonts_dir:
                    fd = _q(c.fonts_dir)
                    chain.append(f"subtitles='{p}':fontsdir='{fd}'")
                else:
                    chain.append(f"subtitles='{p}'")

            parts.append(f"[v{i}]{','.join(chain)}[v{i}out]")

            # Audio trim
            parts.append(f"[a{i}]atrim=start={start:.3f}:end={end:.3f},asetpts=PTS-STARTPTS[a{i}out]")

        return ";".join(parts)


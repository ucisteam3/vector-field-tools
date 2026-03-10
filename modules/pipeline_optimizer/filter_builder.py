from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Tuple
import os


def _q(path: str) -> str:
    # FFmpeg filter args need escaping for backslashes/colons on Windows.
    # Use forward slashes to reduce escaping pain.
    if not path:
        return path
    p = path.replace("\\", "/")
    # Escape ':' for filter args like subtitles=...
    p = p.replace(":", r"\:")
    return p


@dataclass
class FilterBuilder:
    """
    Builds FFmpeg video filter chain in required order:
      crop -> scale -> subtitles -> watermark -> overlay

    Output: filter string for -vf or inside -filter_complex.
    """

    filters: List[str] = field(default_factory=list)

    def add_crop(self, w: int, h: int, x: int, y: int) -> "FilterBuilder":
        self.filters.append(f"crop={int(w)}:{int(h)}:{int(x)}:{int(y)}")
        return self

    def add_scale(self, w: int, h: int, *, flags: str = "lanczos") -> "FilterBuilder":
        self.filters.append(f"scale={int(w)}:{int(h)}:flags={flags}")
        return self

    def add_subtitles(self, ass_path: str, *, fonts_dir: Optional[str] = None) -> "FilterBuilder":
        # Prefer subtitles=path:fontsdir=... for portability
        if not ass_path:
            return self
        p = _q(ass_path)
        if fonts_dir:
            fd = _q(fonts_dir)
            self.filters.append(f"subtitles='{p}':fontsdir='{fd}'")
        else:
            self.filters.append(f"subtitles='{p}'")
        return self

    def add_watermark(
        self,
        *,
        text: Optional[str] = None,
        image_path: Optional[str] = None,
        x: int = 0,
        y: int = 0,
        opacity: float = 1.0,
        font: str = "Arial",
        fontsize: int = 48,
        fontcolor: str = "white",
    ) -> "FilterBuilder":
        """
        Watermark stage. For image watermark, it must be applied via overlay in filter_complex.
        Here we only support text watermark via drawtext as a pure filter.
        """
        if text:
            safe_text = text.replace(":", r"\:").replace("'", r"\'")
            alpha = max(0.0, min(1.0, float(opacity)))
            self.filters.append(
                f"drawtext=text='{safe_text}':x={int(x)}:y={int(y)}:font='{font}':fontsize={int(fontsize)}:fontcolor={fontcolor}@{alpha:.3f}"
            )
        # image watermark handled by PipelineBuilder as overlay with second input
        return self

    def add_overlay(self, *args, **kwargs) -> "FilterBuilder":
        """
        Overlay stage is typically handled in -filter_complex with extra inputs.
        Kept for API completeness; PipelineBuilder handles actual overlay graph.
        """
        return self

    def build(self) -> str:
        return ",".join([f for f in self.filters if f])


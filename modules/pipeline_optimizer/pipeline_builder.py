from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import os
import subprocess

from modules.runtime_paths import ffmpeg_cmd
from modules.processing_engine.engine import get_best_processing_config
from modules.pipeline_optimizer.filter_builder import FilterBuilder


def _exists(p: str) -> bool:
    try:
        return bool(p) and Path(p).exists()
    except Exception:
        return False


def _ensure_parent_dir(file_path: str) -> None:
    p = Path(file_path)
    p.parent.mkdir(parents=True, exist_ok=True)


@dataclass
class PipelineJob:
    """
    Minimal job schema for building one-FFmpeg clip render.
    """

    input_file: str
    output_file: str
    start_time: float
    end_time: float
    # Crop box (optional)
    crop: Optional[Tuple[int, int, int, int]] = None  # (w,h,x,y)
    scale: Optional[Tuple[int, int]] = None  # (w,h)
    subtitles_ass: Optional[str] = None
    fonts_dir: Optional[str] = None
    watermark_text: Optional[str] = None
    watermark_x: int = 0
    watermark_y: int = 0
    watermark_opacity: float = 1.0
    watermark_font: str = "Arial"
    watermark_fontsize: int = 48
    watermark_fontcolor: str = "white"
    # Overlay image (optional, drawn after watermark stage)
    overlay_image: Optional[str] = None
    overlay_x: int = 0
    overlay_y: int = 0
    # Processing override: auto|cpu|nvidia|amd
    processing_override: str = "auto"


class PipelineBuilder:
    """
    Builds efficient single-FFmpeg command:
      trim + filter chain + encode -> output_file

    Filter order enforced:
      crop, scale, subtitles, watermark, overlay
    """

    def __init__(self) -> None:
        self._encoder_cache: Dict[str, bool] = {}

    def _ffmpeg_has_encoder(self, encoder: str) -> bool:
        enc = (encoder or "").strip().lower()
        if not enc:
            return False
        if enc in self._encoder_cache:
            return self._encoder_cache[enc]
        try:
            r = subprocess.run(
                [ffmpeg_cmd(), "-hide_banner", "-encoders"],
                capture_output=True,
                text=True,
                timeout=8,
                creationflags=0x08000000 if os.name == "nt" else 0,
            )
            out = (r.stdout or "") + (r.stderr or "")
            ok = enc in out.lower()
            self._encoder_cache[enc] = ok
            return ok
        except Exception:
            self._encoder_cache[enc] = False
            return False

    def validate(self, job: PipelineJob) -> None:
        if not _exists(job.input_file):
            raise FileNotFoundError(f"Input file missing: {job.input_file}")
        _ensure_parent_dir(job.output_file)
        if job.subtitles_ass and not _exists(job.subtitles_ass):
            raise FileNotFoundError(f"Subtitle file missing: {job.subtitles_ass}")
        if job.overlay_image and not _exists(job.overlay_image):
            raise FileNotFoundError(f"Overlay image missing: {job.overlay_image}")

        proc = get_best_processing_config(override=job.processing_override)
        enc = str(proc.get("encoder") or "")
        if enc and not self._ffmpeg_has_encoder(enc):
            # Fallback to libx264
            if not self._ffmpeg_has_encoder("libx264"):
                raise RuntimeError("No usable encoder found in FFmpeg build")

    def build_filtergraph(self, job: PipelineJob) -> Dict[str, Any]:
        """
        Returns dict with:
          - filter_complex (str|None)
          - map (list[str]) mapping args
          - inputs (list[str]) extra inputs after main -i
        """
        fb = FilterBuilder()
        if job.crop:
            cw, ch, cx, cy = job.crop
            fb.add_crop(cw, ch, cx, cy)
        if job.scale:
            sw, sh = job.scale
            fb.add_scale(sw, sh)
        if job.subtitles_ass:
            fb.add_subtitles(job.subtitles_ass, fonts_dir=job.fonts_dir)
        if job.watermark_text:
            fb.add_watermark(
                text=job.watermark_text,
                x=job.watermark_x,
                y=job.watermark_y,
                opacity=job.watermark_opacity,
                font=job.watermark_font,
                fontsize=job.watermark_fontsize,
                fontcolor=job.watermark_fontcolor,
            )

        base_chain = fb.build()

        # Overlay image needs a second input and overlay filter. Must be after watermark stage.
        if job.overlay_image:
            # Use filter_complex:
            # [0:v] <base_chain> [v0]; [1:v] scale/format? [ov]; [v0][ov]overlay=x:y[v]
            overlay_in = job.overlay_image
            chain0 = base_chain if base_chain else "null"
            fc = (
                f"[0:v]{chain0}[v0];"
                f"[1:v]format=rgba[ov];"
                f"[v0][ov]overlay={int(job.overlay_x)}:{int(job.overlay_y)}[v]"
            )
            return {
                "filter_complex": fc,
                "map": ["-map", "[v]"],
                "extra_inputs": ["-i", str(overlay_in)],
            }

        # No overlay -> can use -vf directly (but we return as filter string)
        return {
            "filter_complex": None,
            "vf": base_chain,
            "map": [],
            "extra_inputs": [],
        }

    def build_command(self, job: PipelineJob) -> List[str]:
        """
        Build a single-process FFmpeg command.
        Smart trim:
          -ss before -i for fast seek
          -to after input for accurate end
        """
        self.validate(job)
        proc = get_best_processing_config(override=job.processing_override)
        enc = str(proc.get("encoder") or "libx264")
        enc_args = list(proc.get("ffmpeg_args") or [])
        if enc != "libx264" and not self._ffmpeg_has_encoder(enc):
            # fallback
            proc = get_best_processing_config(override="cpu")
            enc_args = list(proc.get("ffmpeg_args") or ["-c:v", "libx264", "-preset", "fast", "-crf", "23"])

        start = max(0.0, float(job.start_time))
        end = max(start, float(job.end_time))
        dur = max(0.01, end - start)

        fg = self.build_filtergraph(job)

        cmd: List[str] = [
            ffmpeg_cmd(),
            "-y",
            "-hide_banner",
            "-loglevel",
            "warning",
            # fast seek
            "-ss",
            f"{start:.3f}",
            "-i",
            str(job.input_file),
        ]
        cmd += fg.get("extra_inputs") or []

        # Accurate end: duration after input
        cmd += ["-t", f"{dur:.3f}"]

        if fg.get("filter_complex"):
            cmd += ["-filter_complex", str(fg["filter_complex"])]
            cmd += fg.get("map") or []
        else:
            vf = str(fg.get("vf") or "").strip()
            if vf:
                cmd += ["-vf", vf]

        # Encoder args from processing engine plugin
        cmd += enc_args

        # Audio: keep simple default (copy if possible), can be tuned later.
        cmd += ["-c:a", "aac", "-b:a", "128k"]

        cmd += [str(job.output_file)]
        return cmd


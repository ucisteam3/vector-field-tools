"""
Video filter graph builder — produces valid FFmpeg filter segments.
Order: base mode -> zoom -> flip -> subtitles -> watermark -> overlay -> source_credit -> [v_out].
Never end the full graph with a semicolon.
"""

import os
from pathlib import Path
from typing import Tuple, List, Optional, Any


def finalize_filter_graph(fc: str) -> str:
    """Never end a filter graph with a semicolon. Use before running FFmpeg."""
    return (fc.strip().rstrip(";") if fc else fc) or ""


def append_filter(fc: str, chain: str) -> str:
    """Safe builder: ignores empty chains, prevents double semicolons."""
    if not chain or not chain.strip():
        return fc.strip() if fc else ""
    if not fc or not fc.strip():
        return chain.strip()
    return fc.strip().rstrip(";") + ";" + chain.strip().lstrip(";")


# --- Base mode segments (output [v_mixed]) ---


def landscape_fit() -> str:
    """Landscape -> 9:16 vertical (1080x1920) via blurred background (no stretch). Output label: [v_mixed]."""
    return (
        "[0:v]split=2[bg][fg];"
        "[bg]scale=1080:1920,boxblur=20:10[bg_blur];"
        "[fg]scale=1080:1920:force_original_aspect_ratio=decrease[fg_scaled];"
        "[bg_blur][fg_scaled]overlay=(W-w)/2:(H-h)/2,scale=1080:1920,setsar=1[v_mixed]"
    )


def portrait_crop() -> str:
    """Center crop 9:16. Output label: [v_mixed]."""
    return "[0:v]setsar=1,crop=ih*9/16:ih:(iw-(ih*9/16))/2:0,scale=1080:1920[v_mixed]"


def podcast_passthrough(use_gpu: bool = False) -> str:
    """Preprocessed 1080x1920: setsar or scale_cuda. Output label: [v_mixed]."""
    if use_gpu:
        return "[0:v]scale_cuda=1080:1920[v_mixed]"
    return "[0:v]setsar=1[v_mixed]"


# --- Optional stages (input_label -> output_label) ---


def apply_zoom(input_label: str, strength: float = 1.55, speed: float = 0.0032) -> str:
    """Output label: [v_zoom]. zoom never drops below 1.0."""
    strength = max(1.1, min(2.0, strength))
    speed = max(0.0015, min(0.008, speed))
    return f"{input_label}zoompan=z='min(max(zoom,1.0)+{speed:.4f},{strength:.2f})':d=1:s=1080x1920[v_zoom]"


def apply_flip(input_label: str) -> str:
    """Output label: [v_flipped]."""
    return f"{input_label}hflip[v_flipped]"


def apply_subtitles(input_label: str, ass_path: str, fonts_dir: str) -> str:
    """Output label: [v_sub]."""
    safe_ass = str(ass_path).replace("\\", "/").replace(":", "\\:")
    safe_fonts = str(fonts_dir).replace("\\", "/").replace(":", "\\:")
    return f"{input_label}subtitles='{safe_ass}':fontsdir='{safe_fonts}'[v_sub]"


def _resolve_font(settings: dict, key: str, default_ttf: str = "Arial") -> str:
    """Resolve font path from settings (watermark_font, overlay_font, etc.)."""
    font_name = settings.get(key, default_ttf)
    try:
        from modules.font_manager import VIRAL_FONTS
        if font_name in VIRAL_FONTS:
            local = f"assets/fonts/{VIRAL_FONTS[font_name][1]}"
            if os.path.exists(local):
                return os.path.abspath(local).replace("\\", "/").replace(":", "\\:").replace("'", "")
    except Exception:
        pass
    for candidate in [f"assets/fonts/{font_name}.ttf", "assets/fonts/Roboto-Bold.ttf", "arial.ttf"]:
        if os.path.exists(candidate):
            return os.path.abspath(candidate).replace("\\", "/").replace(":", "\\:").replace("'", "")
    try:
        import glob
        found = glob.glob("assets/fonts/*.ttf")
        if found:
            return os.path.abspath(found[0]).replace("\\", "/").replace(":", "\\:").replace("'", "")
    except Exception:
        pass
    return "arial.ttf"


def apply_watermark(
    input_label: str,
    settings: dict,
    *,
    wm_idx: int = -1,
) -> Tuple[str, List[str]]:
    """
    Text or image watermark. Returns (filter_segment, extra_inputs e.g. ['-i', path]).
    Output label: [v_wm].
    """
    extra: List[str] = []
    wm_type = settings.get("watermark_type", "text")
    if wm_type == "text":
        wm_text = settings.get("watermark_text", "Watermark")
        if not wm_text:
            return "", []
        size = int(settings.get("watermark_size", 48) * 10)
        font_abs = _resolve_font(settings, "watermark_font", "Arial")
        col = settings.get("watermark_color", "#FFFFFF").replace("#", "0x")
        op = settings.get("watermark_opacity", 80) / 100.0
        out_w = settings.get("watermark_outline_width", 2)
        out_col = settings.get("watermark_outline_color", "#000000").replace("#", "0x")
        x_pct = settings.get("watermark_pos_x", 50)
        y_margin = settings.get("watermark_pos_y", 50)
        safe_text = wm_text.replace(":", "\\:").replace("'", "")
        x_expr = f"(W*{x_pct}/100)-(text_w/2)"
        y_expr = f"H-text_h-{y_margin}"
        seg = f"{input_label}drawtext=text='{safe_text}':fontfile='{font_abs}':fontsize={size}:fontcolor={col}@{op}:borderw={out_w}:bordercolor={out_col}@{op}:x={x_expr}:y={y_expr}[v_wm]"
        return seg, extra
    elif wm_type == "image":
        wm_path = settings.get("watermark_image_path", "")
        if wm_path and os.path.exists(wm_path):
            extra = ["-i", wm_path]
            idx = wm_idx if wm_idx >= 0 else 1
            scale_pct = settings.get("watermark_image_scale", 50) / 100.0
            op = settings.get("watermark_image_opacity", 100) / 100.0
            x_pct = settings.get("watermark_pos_x", 50)
            y_margin = settings.get("watermark_pos_y", 50)
            seg = f"[{idx}:v]format=rgba,scale=iw*{scale_pct}:-1,colorchannelmixer=aa={op}[wm_proc];{input_label}[wm_proc]overlay=x='(W*{x_pct}/100)-(w/2)':y='H-h-{y_margin}'[v_wm]"
            return seg, extra
    return "", []


def apply_overlay(
    input_label: str,
    settings: dict,
    *,
    ov_idx: int = -1,
) -> Tuple[str, List[str]]:
    """Second overlay (text/image). Returns (segment, extra_inputs). Output label: [v_ov]."""
    extra: List[str] = []
    ov_type = settings.get("overlay_type", "text")
    if ov_type == "text":
        ov_text = settings.get("overlay_text", "Overlay")
        if not ov_text:
            return "", []
        size = int(settings.get("overlay_size", 48) * 10)
        font_abs = _resolve_font(settings, "overlay_font", "Arial")
        col = settings.get("overlay_color", "#FFFFFF").replace("#", "0x")
        op = settings.get("overlay_opacity", 80) / 100.0
        out_w = settings.get("overlay_outline_width", 2)
        out_col = settings.get("overlay_outline_color", "#000000").replace("#", "0x")
        x_pct = settings.get("overlay_pos_x", 50)
        y_margin = settings.get("overlay_pos_y", 200)
        safe_text = ov_text.replace(":", "\\:").replace("'", "")
        x_expr = f"(W*{x_pct}/100)-(text_w/2)"
        y_expr = f"H-text_h-{y_margin}"
        seg = f"{input_label}drawtext=text='{safe_text}':fontfile='{font_abs}':fontsize={size}:fontcolor={col}@{op}:borderw={out_w}:bordercolor={out_col}@{op}:x={x_expr}:y={y_expr}[v_ov]"
        return seg, extra
    elif ov_type == "image":
        ov_path = settings.get("overlay_image_path", "")
        if ov_path and os.path.exists(ov_path):
            extra = ["-i", ov_path]
            idx = ov_idx if ov_idx >= 0 else 1
            scale_pct = settings.get("overlay_image_scale", 50) / 100.0
            op = settings.get("overlay_image_opacity", 100) / 100.0
            x_pct = settings.get("overlay_pos_x", 50)
            y_margin = settings.get("overlay_pos_y", 200)
            seg = f"[{idx}:v]format=rgba,scale=iw*{scale_pct}:-1,colorchannelmixer=aa={op}[ov_proc];{input_label}[ov_proc]overlay=x='(W*{x_pct}/100)-(w/2)':y='H-h-{y_margin}'[v_ov]"
            return seg, extra
    return "", []


def apply_source_credit(
    input_label: str,
    settings: dict,
    parent: Optional[Any] = None,
) -> str:
    """Source credit drawtext. Output label: [v_credit]."""
    channel_name = getattr(parent, "channel_name", None) if parent else None
    if not channel_name or channel_name == "Unknown Channel":
        if parent and hasattr(parent, "channel_name_label"):
            try:
                channel_name = parent.channel_name_label.cget("text")
            except Exception:
                pass
    if not channel_name or channel_name == "Unknown Channel":
        if parent and getattr(parent, "video_path", None):
            stem = Path(parent.video_path).stem
            if " - " in stem:
                channel_name = stem.split(" - ")[0].split("[")[0].strip()
    if not channel_name:
        channel_name = "Unknown Channel"
    credit_text = f"Source: {channel_name}"
    safe_text = credit_text.replace(":", "\\:").replace("'", "")
    size = int(settings.get("source_credit_fontsize", 17) * 10)
    font_abs = _resolve_font(settings, "source_credit_font", "Arial")
    col = settings.get("source_credit_color", "#FFFFFF").replace("#", "0x")
    op = settings.get("source_credit_opacity", 80) / 100.0
    pos = settings.get("source_credit_position", "bottom-right")
    ox = settings.get("source_credit_pos_x", 50)
    oy = settings.get("source_credit_pos_y", 100)
    if pos == "top-left":
        x_expr, y_expr = str(ox), str(oy)
    elif pos == "top-right":
        x_expr, y_expr = f"W-text_w-{ox}", str(oy)
    elif pos == "bottom-left":
        x_expr, y_expr = str(ox), f"H-text_h-{oy}"
    else:
        x_expr, y_expr = f"W-text_w-{ox}", f"H-text_h-{oy}"
    return f"{input_label}drawtext=text='{safe_text}':fontfile='{font_abs}':fontsize={size}:fontcolor={col}@{op}:x={x_expr}:y={y_expr}[v_credit]"


def chain_to_v_out(last_label: str) -> str:
    """Append valid final stage: last_label -> null -> [v_out]. Prevents invalid [v_wm][v_out] graph."""
    return f"{last_label}null[v_out]"

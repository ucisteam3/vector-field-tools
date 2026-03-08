"""
Clip Service - Export clips using existing clip_exporter, serve clip files.
Supports custom export settings (subtitle, watermark, BGM, effects, etc.)
"""

import os
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Default export settings (from settings_manager)
DEFAULT_EXPORT_SETTINGS = {
    "export_mode": "landscape_fit",
    "dynamic_zoom_enabled": False,
    "video_flip_enabled": False,
    "audio_pitch_enabled": False,
    "subtitle_enabled": False,
    "subtitle_font": "Arial",
    "subtitle_fontsize": 24,
    "subtitle_text_color": "#FFFFFF",
    "subtitle_outline_color": "#000000",
    "subtitle_outline_width": 2,
    "subtitle_highlight_color": "#FFFF00",
    "subtitle_position_y": 50,
    "watermark_enabled": False,
    "watermark_type": "text",
    "watermark_text": "Watermark",
    "watermark_font": "Arial",
    "watermark_size": 48,
    "watermark_opacity": 80,
    "watermark_pos_x": 50,
    "watermark_pos_y": 50,
    "watermark_image_path": "",
    "watermark_image_scale": 50,
    "watermark_image_opacity": 100,
    "watermark_outline_width": 2,
    "watermark_outline_color": "#000000",
    "bgm_enabled": False,
    "bgm_file_path": "",
}


def _apply_settings(ctx, settings: dict):
    """Apply export settings to WebAppContext."""
    if not settings:
        return
    ctx.custom_settings.update(settings)
    if "subtitle_enabled" in settings:
        ctx.subtitle_enabled_var.set(bool(settings["subtitle_enabled"]))


def export_clip(project_id: str, clip_index: int, settings: Optional[dict] = None) -> str | None:
    """
    Export a single clip for the project. Returns the clip filename or None.
    Uses existing ClipExporter via WebAppContext.
    settings: optional dict to override export options (subtitle, watermark, BGM, etc.)
    """
    import sys
    sys.path.insert(0, str(PROJECT_ROOT))
    os.chdir(PROJECT_ROOT)

    from backend.project_manager import get_project, get_project_dir, update_project

    meta = get_project(project_id)
    if not meta or not meta.get("clips"):
        return None

    clips = meta["clips"]
    if clip_index < 0 or clip_index >= len(clips):
        return None

    project_dir = get_project_dir(project_id)
    video_path = project_dir / (meta.get("video_path") or "video.mp4")
    if not video_path.exists():
        return None

    clip_info = clips[clip_index]
    # Build full result dict expected by clip_exporter
    result = {
        "start": clip_info["start"],
        "end": clip_info["end"],
        "duration": clip_info["end"] - clip_info["start"],
        "topic": clip_info.get("title", "Clip"),
        "activity": 0.95,
        "viral_score": clip_info.get("score", 0),
        "hook_score": 0,
        "final_score": clip_info.get("score", 0),
        "clickbait_title": clip_info.get("title", "Clip"),
        "hook_text": "",
        "hook_script": "",
    }

    clips_dir = project_dir / "clips"
    clips_dir.mkdir(exist_ok=True)

    from backend.web_context import WebAppContext

    ctx = WebAppContext(project_dir)
    ctx.video_path = str(video_path)
    ctx.current_video_path = str(video_path)

    # Apply export settings (defaults: no subtitle, no watermark unless overridden)
    merged = DEFAULT_EXPORT_SETTINGS.copy()
    if settings:
        s = dict(settings)
        # Resolve relative paths for uploaded files
        for key in ("bgm_file_path", "watermark_image_path"):
            if s.get(key):
                p = Path(s[key])
                if not p.is_absolute():
                    p = PROJECT_ROOT / p
                s[key] = str(p) if p.exists() else ""
        merged.update({k: v for k, v in s.items() if v is not None})
    _apply_settings(ctx, merged)

    # Create mock vars for clip_exporter
    class MockTkVar:
        def get(self): return False
        def set(self, v): pass
    ctx.use_voiceover_var = MockTkVar()
    ctx.gpu_var = MockTkVar()
    ctx.gpu_var.get = lambda: True
    ctx.channel_name = meta.get("channel_name", "Unknown")

    try:
        from modules.clip_exporter import ClipExporter
        exporter = ClipExporter(ctx)
        # ClipExporter.download_clip uses self.parent (ctx)
        success = exporter.download_clip(result, clips_dir, clip_index + 1)
        if success:
            # Find the generated filename
            safe_topic = "".join(c for c in result["topic"][:50] if c.isalnum() or c in (" ", "-", "_")).strip()
            if not safe_topic:
                safe_topic = f"clip_{clip_index + 1}"
            filename = f"{safe_topic}.mp4"
            if (clips_dir / filename).exists():
                clips[clip_index]["clip_path"] = f"clips/{filename}"
                update_project(project_id, clips=clips)
                return filename
    except Exception as e:
        print(f"[CLIP SERVICE] Export error: {e}")
        import traceback
        traceback.print_exc()
    return None


def export_all_clips(project_id: str) -> list[str]:
    """Export all clips for a project. Returns list of clip filenames."""
    from backend.project_manager import get_project
    meta = get_project(project_id)
    if not meta or not meta.get("clips"):
        return []
    exported = []
    for i in range(len(meta["clips"])):
        fn = export_clip(project_id, i)
        if fn:
            exported.append(fn)
    return exported

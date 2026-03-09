"""
Export pipeline — build filter graphs, run FFmpeg, handle GPU/CPU and fallbacks.
Orchestrates video_filters, audio_filters, ffmpeg_runner.
"""

import os
from pathlib import Path
from typing import Optional, List, Tuple, Any, Callable

from modules.video_filters import (
    finalize_filter_graph,
    append_filter,
    landscape_fit,
    portrait_crop,
    podcast_passthrough,
    apply_zoom,
    apply_flip,
    apply_subtitles,
    apply_watermark,
    apply_overlay,
    apply_source_credit,
    chain_to_v_out,
)
from modules.audio_filters import build_audio_filter as build_audio_filter_impl
from modules.ffmpeg_runner import (
    run_ffmpeg,
    get_video_info,
    gpu_available,
    ffmpeg_has_filters,
)


# --- Constants (portrait 9:16 safe fallbacks) ---
PORTRAIT_SAFE_FC = "[0:v]setsar=1,crop=ih*9/16:ih:(iw-(ih*9/16))/2:0,scale=1080:1920[v_out]"
MINIMAL_VIDEO_FC = PORTRAIT_SAFE_FC
ULTRA_MINIMAL_VIDEO_FC = PORTRAIT_SAFE_FC
MINIMAL_VIDEO_FC_GPU = "[0:v]scale_cuda=1080:1920[v_out]"


def build_video_filter(
    mode: str,
    settings: dict,
    *,
    ass_path: Optional[str] = None,
    use_gpu: bool = False,
    podcast_preprocessed: bool = False,
    has_zoom: bool = False,
    has_flip: bool = False,
    has_subtitles: bool = False,
    has_watermark: bool = False,
    has_overlay: bool = False,
    has_source_credit: bool = False,
    parent: Optional[Any] = None,
    num_inputs: int = 1,
) -> Tuple[str, str, List[str]]:
    """
    Build video filter graph. Order: base -> zoom -> flip -> subtitles -> watermark -> overlay -> source_credit -> [v_out].
    Returns (fc_video_only, last_v_label, extra_inputs). num_inputs = number of -i before any watermark/overlay image.
    """
    _has = ffmpeg_has_filters("subtitles", "drawtext", "zoompan", "hflip")
    extra_inputs: List[str] = []

    # Base mode
    if mode == "podcast_smart":
        fc = podcast_passthrough(use_gpu=use_gpu)
        last = "[v_mixed]"
    elif mode == "face_tracking":
        fc = portrait_crop()
        last = "[v_mixed]"
    elif mode == "landscape_fit":
        fc = landscape_fit()
        last = "[v_mixed]"
    else:
        fc = portrait_crop()
        last = "[v_mixed]"

    # Zoom
    if has_zoom and _has.get("zoompan", True):
        strength = max(1.1, min(2.0, float(settings.get("dynamic_zoom_strength", 1.55))))
        speed = max(0.0015, min(0.008, float(settings.get("dynamic_zoom_speed", 0.0032))))
        fc = append_filter(fc, apply_zoom(last, strength, speed))
        last = "[v_zoom]"

    # Flip
    if has_flip and _has.get("hflip", True):
        fc = append_filter(fc, apply_flip(last))
        last = "[v_flipped]"

    # Subtitles
    if has_subtitles and ass_path and _has.get("subtitles", True):
        fonts_dir = str(Path("assets/fonts").resolve())
        fc = append_filter(fc, apply_subtitles(last, ass_path, fonts_dir))
        last = "[v_sub]"

    # Watermark (image index = num_inputs + existing extra inputs)
    if has_watermark and _has.get("drawtext", True):
        wm_idx = num_inputs + len(extra_inputs)
        seg, ext = apply_watermark(last, settings, wm_idx=wm_idx)
        if seg:
            fc = append_filter(fc, seg)
            extra_inputs.extend(ext)
            last = "[v_wm]"

    # Overlay (image index = num_inputs + number of extra inputs so far)
    if has_overlay and _has.get("drawtext", True):
        ov_idx = num_inputs + (len(extra_inputs) // 2)
        seg, ext = apply_overlay(last, settings, ov_idx=ov_idx)
        if seg:
            fc = append_filter(fc, seg)
            extra_inputs.extend(ext)
            last = "[v_ov]"

    # Source credit
    if has_source_credit and _has.get("drawtext", True):
        seg = apply_source_credit(last, settings, parent)
        if seg:
            fc = append_filter(fc, seg)
            last = "[v_credit]"

    # Final output
    fc = append_filter(fc, chain_to_v_out(last))
    return finalize_filter_graph(fc), last, extra_inputs


def build_audio_filter(
    settings: dict,
    voiceover_path: Optional[str] = None,
    bgm_file_path: Optional[str] = None,
) -> Tuple[str, List[str]]:
    """Build audio filter and extra inputs."""
    pitch = float(settings.get("audio_pitch_semitones", 0))
    pitch = max(-4, min(4, pitch))
    return build_audio_filter_impl(
        voiceover_path=voiceover_path,
        bgm_file_path=bgm_file_path,
        audio_pitch_semitones=pitch,
    )


def export_clip(
    input_video: str,
    output_video: str,
    start: float,
    duration: float,
    mode: str,
    *,
    subtitles: Optional[str] = None,
    voiceover_path: Optional[str] = None,
    bgm_file_path: Optional[str] = None,
    custom_settings: Optional[dict] = None,
    parent: Optional[Any] = None,
    effective_video_path: Optional[str] = None,
    effective_start: Optional[float] = None,
    effective_duration: Optional[float] = None,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    clip_num: Optional[int] = None,
    output_filename: Optional[str] = None,
    safe_messagebox: Optional[Callable[[str, str, str], None]] = None,
) -> bool:
    """
    Build filter graph, run FFmpeg, handle GPU/CPU and minimal/ultra fallback.
    Returns True on success.
    """
    settings = custom_settings or {}
    effective_video_path = effective_video_path or input_video
    effective_start = effective_start if effective_start is not None else start
    effective_duration = effective_duration if effective_duration is not None else duration
    pad_start = max(0, effective_start - 0.2)
    pad_duration = effective_duration + 0.4 if effective_video_path == input_video else effective_duration

    # Normalize mode
    if mode in ("portrait", "face_tracking", "9:16", "portrait_9_16"):
        mode = "face_tracking"
    elif mode != "landscape_fit" and mode != "podcast_smart":
        mode = "landscape_fit"

    # Input args: video + optional voiceover + optional bgm
    input_args: List[str] = ["-i", effective_video_path]
    if voiceover_path:
        input_args.extend(["-i", voiceover_path])
    if bgm_file_path:
        input_args.extend(["-i", bgm_file_path])

    # Audio filter and extra inputs (voiceover/bgm already in input_args)
    audio_fc, _ = build_audio_filter(settings, voiceover_path, bgm_file_path)

    # Heavy filters -> CPU path, audio via -map 0:a
    has_heavy = (
        settings.get("dynamic_zoom_enabled", False)
        or bool(subtitles)
        or settings.get("watermark_enabled", False)
        or settings.get("overlay_enabled", False)
        or settings.get("source_credit_enabled", False)
    )
    use_gpu_possible = gpu_available() and (getattr(parent, "gpu_var", None) and parent.gpu_var.get() if parent else False)
    podcast_preprocessed = mode == "podcast_smart" and effective_video_path != input_video
    base_supports_gpu = mode == "podcast_smart" and podcast_preprocessed
    use_pure_gpu = use_gpu_possible and not has_heavy and base_supports_gpu
    use_cpu = not use_pure_gpu
    use_video_only_minimal = use_cpu  # CPU path uses -map 0:a

    # Number of inputs before watermark/overlay (for correct [1:v] etc.)
    n_in = len(input_args) // 2
    fc_video, last_v_label, extra = build_video_filter(
        mode,
        settings,
        ass_path=subtitles,
        use_gpu=use_gpu_possible and not has_heavy,
        podcast_preprocessed=podcast_preprocessed,
        has_zoom=settings.get("dynamic_zoom_enabled", False),
        has_flip=settings.get("video_flip_enabled", False),
        has_subtitles=bool(subtitles),
        has_watermark=settings.get("watermark_enabled", False),
        has_overlay=settings.get("overlay_enabled", False),
        has_source_credit=settings.get("source_credit_enabled", False),
        parent=parent,
        num_inputs=n_in,
    )
    input_args.extend(extra)

    # Full filter: video only for CPU (audio -map 0:a), or video+audio for GPU
    if use_video_only_minimal:
        filter_complex = fc_video
        map_a = "0:a"
    else:
        filter_complex = append_filter(fc_video, audio_fc)
        filter_complex = finalize_filter_graph(filter_complex)
        map_a = "[a_out]"

    filter_complex_cpu = fc_video  # for NVENC fallback
    use_gpu_encode = use_pure_gpu

    # Hybrid GPU: hwdownload -> fc -> hwupload
    if use_gpu_possible and not has_heavy and not base_supports_gpu and not use_pure_gpu:
        # Not podcast preprocessed; use CPU filters with GPU decode/encode
        filter_complex_cpu = fc_video
        filter_complex = "[0:v]hwdownload,format=nv12[v0];" + fc_video.replace("[0:v]", "[v0]")
        filter_complex = filter_complex.replace(f"{last_v_label}[v_out]", f"{last_v_label}hwupload_cuda[v_out]")
        filter_complex = finalize_filter_graph(filter_complex)
        use_gpu_encode = True
        use_video_only_minimal = False
        map_a = "[a_out]"
        filter_complex = append_filter(filter_complex, audio_fc)
        filter_complex = finalize_filter_graph(filter_complex)

    def make_cmd(force_cpu: bool = False, fc_override: Optional[str] = None) -> List[str]:
        fc = fc_override if fc_override is not None else (filter_complex_cpu if force_cpu else filter_complex)
        # Prefer GPU minimal (scale_cuda + nvenc) when GPU available and using minimal fallback
        if fc_override in (MINIMAL_VIDEO_FC, ULTRA_MINIMAL_VIDEO_FC) and not force_cpu and gpu_available():
            fc = MINIMAL_VIDEO_FC_GPU
        fc = finalize_filter_graph(fc)
        map_audio = "0:a" if (fc_override in (MINIMAL_VIDEO_FC, ULTRA_MINIMAL_VIDEO_FC) or fc == MINIMAL_VIDEO_FC_GPU) else map_a
        use_gpu_this = (use_gpu_encode and not force_cpu and fc_override is None) or (fc == MINIMAL_VIDEO_FC_GPU and not force_cpu)
        hwaccel = ["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"] if use_gpu_this else []
        cmd = [
            "ffmpeg", "-y", "-fflags", "+genpts", "-avoid_negative_ts", "make_zero",
            "-ss", str(pad_start), "-t", str(pad_duration),
            *hwaccel, *input_args,
            "-filter_complex", fc,
            "-map", "[v_out]", "-map", map_audio,
            "-max_muxing_queue_size", "1024",
        ]
        if use_gpu_this:
            cmd.extend([
                "-c:v", "h264_nvenc", "-preset", "p5", "-tune", "hq",
                "-rc:v", "vbr", "-cq:v", "19", "-b:v", "6M", "-maxrate", "10M", "-bufsize", "12M",
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                output_video,
            ])
        else:
            cmd.extend([
                "-c:v", "libx264", "-preset", "fast", "-crf", "23",
                "-maxrate", "8M", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                output_video,
            ])
        return cmd

    def progress(pct: int, msg: str):
        if progress_callback:
            try:
                progress_callback(pct, msg)
            except Exception:
                pass

    def msg_ok(title: str, msg: str):
        if safe_messagebox:
            try:
                safe_messagebox("info", title, msg)
            except Exception:
                print(f"  [{title}] {msg}")
        else:
            print(f"  [{title}] {msg}")

    def msg_err(title: str, msg: str):
        if safe_messagebox:
            try:
                safe_messagebox("error", title, msg)
            except Exception:
                print(f"  [{title}] {msg}")
        else:
            print(f"  [{title}] {msg}")

    encode_dur = pad_duration
    out_name = output_filename or os.path.basename(output_video)

    # GPU try
    if use_gpu_encode:
        progress(50, "Mengode video (NVENC)...")
        ret = run_ffmpeg(make_cmd(), progress_callback=progress, encode_duration=encode_dur)
        if ret == 0:
            progress(100, "Selesai (NVENC)")
            msg_ok("Berhasil", f"Klip berhasil diekspor (GPU):\n{out_name}")
            return True
        progress(45, "Fallback CPU encoding...")
        ret = run_ffmpeg(make_cmd(force_cpu=True), progress_callback=progress, encode_duration=encode_dur)
        if ret == 0:
            progress(100, "Selesai (CPU)")
            msg_ok("Berhasil", f"Klip berhasil diekspor (CPU):\n{out_name}")
            return True
        msg_err("Kesalahan", "NVENC gagal dan fallback CPU tidak tersedia. Cek log konsol.")
        return False

    # CPU
    progress(50, "Mengode video...")
    ret = run_ffmpeg(make_cmd(), progress_callback=progress, encode_duration=encode_dur)
    if ret == 0:
        progress(100, "Selesai")
        msg_ok("Berhasil", f"Klip berhasil diekspor:\n{out_name}")
        return True

    # Minimal fallback
    progress(50, "Mencoba export minimal...")
    ret = run_ffmpeg(make_cmd(fc_override=MINIMAL_VIDEO_FC), progress_callback=progress, encode_duration=encode_dur)
    if ret == 0:
        progress(100, "Selesai (minimal)")
        msg_ok("Berhasil", f"Klip berhasil diekspor (minimal):\n{out_name}")
        return True

    # Ultra minimal: portrait-safe filter_complex (BUG 9+10: finalize, keep 9:16)
    progress(50, "Mencoba ultra-minimal...")
    fc_ultra = finalize_filter_graph(PORTRAIT_SAFE_FC)
    cmd = [
        "ffmpeg", "-y", "-fflags", "+genpts", "-avoid_negative_ts", "make_zero",
        "-ss", str(pad_start), "-t", str(pad_duration),
        "-i", effective_video_path,
        "-filter_complex", fc_ultra,
        "-map", "[v_out]", "-map", "0:a",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-maxrate", "8M", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
        "-max_muxing_queue_size", "1024",
        output_video,
    ]
    ret = run_ffmpeg(cmd, progress_callback=progress, encode_duration=encode_dur)
    if ret == 0:
        progress(100, "Selesai (ultra-minimal)")
        msg_ok("Berhasil", f"Klip berhasil diekspor (ultra-minimal):\n{out_name}")
        return True

    msg_err("Kesalahan", "Gagal mengekspor klip. Cek log konsol.")
    return False

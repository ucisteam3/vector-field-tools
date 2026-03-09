"""
Audio filter graph builder — produces [a_out] for FFmpeg.
"""

from typing import List, Tuple, Optional


def passthrough_audio() -> Tuple[str, List[str]]:
    """Passthrough: [0:a] -> aresample -> [a_out]. Extra inputs: []."""
    # Keep audio in sync with video
    return "[0:a]aresample=async=1:first_pts=0[a_out]", []


def mix_voiceover(voiceover_path: str) -> Tuple[str, List[str]]:
    """Original + voiceover. Input 0 = video (audio), 1 = voiceover. Output [a_out]."""
    extra = ["-i", voiceover_path]
    # Original 1.0, VOX 1.5, duration=first
    filt = "[1:a]volume=1.5[vox];[0:a]volume=1.0[bg];[bg][vox]amix=inputs=2:duration=first:dropout_transition=2[a_out]"
    return filt, extra


def mix_bgm(bgm_file_path: str) -> Tuple[str, List[str]]:
    """Original + BGM (-10dB). Input 0 = video, 1 = BGM. Output [a_out]. BGM looped."""
    extra = ["-i", bgm_file_path]
    # BGM at 0.316 (~-10dB), loop
    filt = "[0:a]volume=1.0[orig];[1:a]volume=0.316,aloop=loop=-1:size=2e+09[bgm];[orig][bgm]amix=inputs=2:duration=first:dropout_transition=2[a_out]"
    return filt, extra


def mix_voiceover_bgm(voiceover_path: str, bgm_file_path: str) -> Tuple[str, List[str]]:
    """Original + voiceover + BGM. Input 0=video, 1=voiceover, 2=bgm. Output [a_out]."""
    extra = ["-i", voiceover_path, "-i", bgm_file_path]
    filt = (
        "[1:a]volume=1.5[vox];"
        "[0:a]volume=1.0[bg];"
        "[2:a]volume=0.316,aloop=loop=-1:size=2e+09[bgm];"
        "[bg][vox]amix=inputs=2:duration=first[mix1];"
        "[mix1][bgm]amix=inputs=2:duration=first:dropout_transition=2[a_out]"
    )
    return filt, extra


def build_audio_filter(
    voiceover_path: Optional[str] = None,
    bgm_file_path: Optional[str] = None,
    *,
    audio_pitch_semitones: float = 0,
) -> Tuple[str, List[str]]:
    """
    Build full audio filter string and extra input list.
    Returns (filter_string, extra_inputs).
    If pitch non-zero, wraps in asetrate/aresample.
    """
    if voiceover_path and bgm_file_path:
        filt, extra = mix_voiceover_bgm(voiceover_path, bgm_file_path)
    elif voiceover_path:
        filt, extra = mix_voiceover(voiceover_path)
    elif bgm_file_path:
        filt, extra = mix_bgm(bgm_file_path)
    else:
        filt, extra = passthrough_audio()

    if audio_pitch_semitones != 0:
        # Wrap: [0:a] or mixed -> asetrate -> aresample=48000 -> async [a_out]
        import math
        rate_in = 48000 * (2 ** (audio_pitch_semitones / 12.0))
        rate_in = max(24000, min(96000, rate_in))
        # We need to replace [a_out] with pitch chain; passthrough is [0:a]...[a_out]
        # For passthrough: "[0:a]asetrate=...,aresample=48000,aresample=async=1:first_pts=0[a_out]"
        # For mix: the mix output is something like [a_out]; we need [mix_out]asetrate...[a_out]
        if "[a_out]" in filt:
            inner = filt.replace("[a_out]", "[a_pitch_in]")
            filt = inner + ";[a_pitch_in]asetrate=" + f"{rate_in:.0f}" + ",aresample=48000,aresample=async=1:first_pts=0[a_out]"
    return filt, extra

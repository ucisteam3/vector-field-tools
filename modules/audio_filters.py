"""
Audio filter graph builder — produces [a_out] for FFmpeg.
"""

from typing import List, Tuple, Optional


def passthrough_audio() -> Tuple[str, List[str]]:
    """Passthrough: [0:a] +3dB -> [a_sync]. Extra inputs: []. build_audio_filter adds tail."""
    return "[0:a]volume=1.4125[a_sync]", []  # +3 dB


def mix_voiceover(voiceover_path: str) -> Tuple[str, List[str]]:
    """Original + voiceover. Input 0 = video (audio) +3dB, 1 = voiceover. Output [a_sync]."""
    extra = ["-i", voiceover_path]
    filt = "[1:a]volume=1.5[vox];[0:a]volume=1.4125[bg];[bg][vox]amix=inputs=2:duration=first:dropout_transition=2[a_sync]"  # orig +3 dB
    return filt, extra


def mix_bgm(bgm_file_path: str) -> Tuple[str, List[str]]:
    """Original +3 dB + BGM -15 dB. Input 0 = video, 1 = BGM. Output [a_sync]. BGM looped."""
    extra = ["-i", bgm_file_path]
    filt = "[0:a]volume=1.4125[orig];[1:a]volume=0.178,aloop=loop=-1:size=2e+09[bgm];[orig][bgm]amix=inputs=2:duration=first:dropout_transition=2[a_sync]"  # orig +3dB, BGM -15dB
    return filt, extra


def mix_voiceover_bgm(voiceover_path: str, bgm_file_path: str) -> Tuple[str, List[str]]:
    """Original +3 dB + voiceover + BGM -15 dB. Input 0=video, 1=voiceover, 2=bgm. Output [a_sync]."""
    extra = ["-i", voiceover_path, "-i", bgm_file_path]
    filt = (
        "[1:a]volume=1.5[vox];"
        "[0:a]volume=1.4125[bg];"  # orig +3 dB
        "[2:a]volume=0.178,aloop=loop=-1:size=2e+09[bgm];"  # BGM -15 dB
        "[bg][vox]amix=inputs=2:duration=first[mix1];"
        "[mix1][bgm]amix=inputs=2:duration=first:dropout_transition=2[a_sync]"
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
    Returns (filter_string, extra_inputs). Output label always [a_out].
    """
    if voiceover_path and bgm_file_path:
        filt, extra = mix_voiceover_bgm(voiceover_path, bgm_file_path)
    elif voiceover_path:
        filt, extra = mix_voiceover(voiceover_path)
    elif bgm_file_path:
        filt, extra = mix_bgm(bgm_file_path)
    else:
        filt, extra = passthrough_audio()

    # Tail: [a_sync] -> (optional pitch) -> [a_out]
    if audio_pitch_semitones != 0:
        rate_in = 48000 * (2 ** (audio_pitch_semitones / 12.0))
        rate_in = max(24000, min(96000, rate_in))
        tail = f";[a_sync]asetrate={rate_in:.0f},aresample=48000,aresample=async=1:first_pts=0[a_out]"
    else:
        tail = ";[a_sync]aresample=async=1:first_pts=0[a_out]"
    return filt + tail, extra

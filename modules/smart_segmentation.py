"""
Smart Segmentation Module
Provides intelligent boundary detection for video clips based on subtitle/dialogue analysis.
Prevents cutting in the middle of sentences or dialogues.
"""

import re
from typing import List, Dict, Tuple, Optional


class SubtitleCue:
    """Represents a single subtitle cue with timing and text"""
    def __init__(self, start: float, end: float, text: str):
        self.start = start
        self.end = end
        self.text = text.strip()
        self.duration = end - start
    
    def __repr__(self):
        return f"Cue({self.start:.1f}-{self.end:.1f}: '{self.text[:30]}...')"


def flexible_time_to_seconds(t_str: str) -> float:
    """
    Convert VTT timestamp to seconds (handles HH:MM:SS.mmm or MM:SS.mmm)
    """
    if not t_str:
        return 0.0
    t_str = t_str.replace(',', '.')
    parts = t_str.split(':')
    try:
        if len(parts) == 3:  # H:M:S
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
        elif len(parts) == 2:  # M:S
            return int(parts[0]) * 60 + float(parts[1])
        else:
            return float(parts[0])
    except:
        return 0.0


def load_subtitle_cues(vtt_path: str) -> List[SubtitleCue]:
    """
    Parse VTT file into structured subtitle cues
    Returns list of SubtitleCue objects
    """
    try:
        with open(vtt_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except:
        return []
    
    cues = []
    time_pat = re.compile(r'([\d:.,]+)\s*-->\s*([\d:.,]+)')
    
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        match = time_pat.search(line)
        
        if match:
            start_str, end_str = match.groups()
            start_sec = flexible_time_to_seconds(start_str)
            end_sec = flexible_time_to_seconds(end_str)
            
            # Get text from next line(s)
            text_lines = []
            i += 1
            while i < len(lines) and lines[i].strip() and not time_pat.search(lines[i]):
                text = lines[i].strip()
                # Remove VTT tags like <c.color> or <b>
                text = re.sub(r'<[^>]+>', '', text)
                if text:
                    text_lines.append(text)
                i += 1
            
            if text_lines:
                full_text = ' '.join(text_lines)
                cues.append(SubtitleCue(start_sec, end_sec, full_text))
        else:
            i += 1
    
    return cues


def find_sentence_boundaries(cues: List[SubtitleCue]) -> List[Tuple[float, str]]:
    """
    Find all sentence ending points in subtitle cues
    Returns list of (timestamp, punctuation) tuples
    """
    boundaries = []
    sentence_endings = re.compile(r'[.!?]+\s*$')
    
    for cue in cues:
        if sentence_endings.search(cue.text):
            boundaries.append((cue.end, cue.text[-1]))
    
    return boundaries


def calculate_pause_durations(cues: List[SubtitleCue]) -> List[Tuple[float, float]]:
    """
    Calculate gaps/pauses between consecutive subtitle cues
    Returns list of (timestamp, pause_duration) tuples
    """
    pauses = []
    
    for i in range(len(cues) - 1):
        gap = cues[i + 1].start - cues[i].end
        if gap > PAUSE_THRESHOLD_SEC:  # Only consider pauses >0.4s
            pauses.append((cues[i].end, gap))
    
    return pauses


def is_sentence_ending(text: str) -> bool:
    """Check if text ends with sentence-ending punctuation"""
    return bool(re.search(r'[.!?]+\s*$', text))


def get_pause_after(cue: SubtitleCue, all_cues: List[SubtitleCue]) -> float:
    """Get pause duration after a specific cue"""
    cue_idx = all_cues.index(cue) if cue in all_cues else -1
    if cue_idx == -1 or cue_idx >= len(all_cues) - 1:
        return 0.0
    
    next_cue = all_cues[cue_idx + 1]
    return max(0.0, next_cue.start - cue.end)


def find_nearest_cue(timestamp: float, cues: List[SubtitleCue], max_distance: float = 3.0) -> Optional[SubtitleCue]:
    """
    Find the subtitle cue nearest to a given timestamp
    Returns None if no cue within max_distance
    """
    if not cues:
        return None
    
    best_cue = None
    best_distance = float('inf')
    
    for cue in cues:
        # Distance to cue (prefer end points for natural breaks)
        distance = min(abs(timestamp - cue.start), abs(timestamp - cue.end))
        
        if distance < best_distance and distance <= max_distance:
            best_distance = distance
            best_cue = cue
    
    return best_cue


def find_sentence_start_before(timestamp: float, cues: List[SubtitleCue], max_lookback: float = 10.0) -> float:
    """
    Find the start of the sentence that contains or precedes the given timestamp.
    Never start mid-sentence: return the cue start of the sentence that contains this time.
    """
    if not cues:
        return timestamp
    min_start = max(0.0, timestamp - max_lookback)
    # Find cue that contains timestamp or is the last one ending before timestamp
    best_cue = None
    for cue in cues:
        if cue.end < min_start:
            continue
        if cue.start > timestamp + 1.0:
            break
        if cue.start <= timestamp <= cue.end:
            best_cue = cue
            break
        if cue.end >= timestamp and (best_cue is None or cue.start < best_cue.start):
            best_cue = cue
        if cue.start <= timestamp and cue.end >= timestamp - 0.5:
            best_cue = cue
    if best_cue is None:
        for cue in reversed(cues):
            if cue.end <= timestamp:
                best_cue = cue
                break
    if best_cue is None:
        return timestamp
    # Return start of this sentence (beginning of cue)
    return best_cue.start


def refine_segment_start_hook_first(hook_timestamp: float, segment_end: float, cues: List[SubtitleCue],
                                    pre_roll_sec: float = 2.0, max_shift: float = REFINE_START_MAX_SHIFT_SEC) -> float:
    """
    Hook-first clip start: start slightly before the hook (e.g. hook - 2s).
    If that falls mid-sentence, shift start to the beginning of that sentence.
    Then skip any leading filler sentences.
    """
    if not cues:
        return max(0.0, hook_timestamp - pre_roll_sec)
    candidate_start = max(0.0, hook_timestamp - pre_roll_sec)
    # Snap to sentence boundary (never start mid-sentence)
    sentence_start = find_sentence_start_before(candidate_start, cues, max_lookback=8.0)
    new_start = min(sentence_start, candidate_start + max_shift)
    new_start = max(0.0, new_start)
    # Skip filler at the beginning
    new_start = refine_segment_start(new_start, segment_end, cues, max_shift=max_shift)
    return new_start


def score_boundary_quality(timestamp: float, cues: List[SubtitleCue], is_start: bool = False) -> float:
    """
    Score how good a timestamp is as a clip boundary
    Higher score = better cut point
    
    Args:
        timestamp: The time to evaluate
        cues: All subtitle cues
        is_start: True if evaluating start boundary, False for end
    
    Returns:
        Quality score (0-20 range typically)
    """
    score = 0.0
    nearest = find_nearest_cue(timestamp, cues, max_distance=2.0)
    
    if not nearest:
        return 0.0
    
    # Distance penalty (prefer exact alignment)
    distance = min(abs(timestamp - nearest.start), abs(timestamp - nearest.end))
    score -= distance * 2  # -2 points per second of misalignment
    
    # Check if at sentence end (STRONG preference for end boundaries)
    if is_sentence_ending(nearest.text):
        score += 12 if not is_start else 5
    
    # Check pause after this cue
    pause = get_pause_after(nearest, cues)
    if pause > 1.5:
        score += 10
    elif pause > 1.0:
        score += 6
    elif pause > 0.5:
        score += 3
    
    # For start boundaries, prefer beginning of cue
    if is_start:
        if abs(timestamp - nearest.start) < 0.5:
            score += 5
    else:
        # For end boundaries, prefer end of cue
        if abs(timestamp - nearest.end) < 0.5:
            score += 5
    
    # Penalty for cutting mid-cue (very bad)
    if nearest.start < timestamp < nearest.end:
        score -= 20
    
    return score


# Safe extension limit: do not extend boundaries by more than this (seconds)
MAX_BOUNDARY_EXTENSION_SEC = 8.0
# Subtitle continuity: if next cue starts within this many seconds, treat as same sentence
SUBTITLE_CONTINUITY_SEC = 0.6
# Pause threshold: gap between subtitles > this = natural pause (good cut point)
PAUSE_THRESHOLD_SEC = 0.4
# Natural clip end: extend until end of sentence OR pause >= this (600ms)
PAUSE_NATURAL_END_SEC = 0.6
# Stop context continuation when pause > 1s or duration > 60s
PAUSE_TOPIC_CHANGE_SEC = 1.0
MAX_CLIP_DURATION_SEC = 60.0
# Max shift for start refinement: skip intro/filler, shift to first meaningful moment
REFINE_START_MAX_SHIFT_SEC = 6.0
REFINE_END_MAX_EXTENSION_SEC = 6.0
# Pre-roll buffer: include conversation setup before clip (max 4 sec)
PRE_ROLL_BUFFER_SEC = 4.0
# Sentence completion: max extension at end to finish sentence (user limit)
SENTENCE_END_MAX_EXTENSION_SEC = 5.0

# Filler/intro phrases (Indonesian) to skip at segment start - lowercase for matching
# Order matters: longer phrases first
FILLER_PHRASES = [
    "sebelum kita bahas",
    "sebelum kita membahas",
    "kita bahas dulu",
    "kita membahas dulu",
    "oke kita bahas",
    "oke kita membahas",
    "sekarang kita bahas",
    "sekarang kita membahas",
    "pertama kita bahas",
    "topik kita hari ini",
    "kita akan bahas",
    "kita akan membahas",
    "jadi sebenarnya",
    "kalau kita lihat",
    "menurut saya",
    "seperti biasa",
    "yang menarik adalah",
    "nah",
    "jadi",
]

# If content after filler phrase is longer than this, cue has meaningful content - don't skip
MIN_MEANINGFUL_LEN = 15


def _is_filler_sentence(text: str) -> bool:
    """
    Check if text is predominantly a filler sentence.
    A cue is filler if it starts with a filler phrase AND the remainder is short.
    E.g. 'nah sebelum kita bahas wasit' = filler; 'kita akan bahas gol beckham yang cantik' = has meaningful content
    """
    if not text or not text.strip():
        return True
    t = text.strip().lower()
    for phrase in FILLER_PHRASES:
        if t.startswith(phrase):
            remainder = t[len(phrase):].strip().lstrip(" ,.:;")
            # If substantial content remains, this cue has meaningful part - not pure filler
            if len(remainder) >= MIN_MEANINGFUL_LEN:
                return False
            return True
    return False


def refine_segment_start(segment_start: float, segment_end: float, cues: List[SubtitleCue],
                         max_shift: float = REFINE_START_MAX_SHIFT_SEC) -> float:
    """
    Refine segment start by skipping filler sentences at the beginning.
    
    Example: "nah sebelum kita membahas wasit, kita akan membahas gol beckham yang terlalu cantik"
    -> Clip should start from "gol beckham yang terlalu cantik"
    
    Rules:
    - Maximum shift: +max_shift seconds (default 6)
    - Must remain inside segment [segment_start, segment_end]
    
    Args:
        segment_start: Original segment start time
        segment_end: Segment end time
        cues: Subtitle cues (from VTT/transcript)
        max_shift: Maximum seconds to advance the start
    
    Returns:
        Refined start time
    """
    if not cues:
        return segment_start
    
    latest_allowed_start = min(segment_end - 1.0, segment_start + max_shift)
    if latest_allowed_start <= segment_start:
        return segment_start
    
    # Get cues within the segment
    segment_cues = [c for c in cues if c.start < segment_end and c.end > segment_start]
    segment_cues.sort(key=lambda c: c.start)
    
    for cue in segment_cues:
        if cue.start > latest_allowed_start:
            break
        if _is_filler_sentence(cue.text):
            # Skip this filler cue - move start to after this cue
            candidate_start = cue.end
            if candidate_start <= latest_allowed_start and candidate_start < segment_end:
                segment_start = candidate_start
        else:
            # First meaningful sentence - start at beginning of this cue
            return max(segment_start, min(cue.start, latest_allowed_start))
    
    return segment_start


def refine_segment_end(segment_end: float, cues: List[SubtitleCue],
                       max_extension: float = REFINE_END_MAX_EXTENSION_SEC) -> float:
    """
    Refine segment end so the clip never cuts mid-sentence.
    
    If the sentence at segment_end does not end with . ! ?, extend until it completes.
    
    Rules:
    - Maximum extension: +max_extension seconds (default 6)
    - Prefer extending to natural pause (gap > 0.4s between subtitle cues)
    
    Args:
        segment_end: Original segment end time
        cues: Subtitle cues
        max_extension: Maximum seconds to extend
    
    Returns:
        Refined end time
    """
    if not cues:
        return segment_end
    
    cap = segment_end + max_extension
    
    # Find cue containing segment_end or nearest after
    idx = -1
    for i, cue in enumerate(cues):
        if cue.start <= segment_end <= cue.end:
            idx = i
            break
        if segment_end < cue.start:
            if i > 0 and cues[i - 1].end >= segment_end - 0.5:
                idx = i - 1
            else:
                idx = i
            break
    
    if idx < 0:
        if segment_end < cues[0].start:
            return segment_end
        idx = len(cues) - 1
    
    best_end = segment_end
    for j in range(idx, len(cues)):
        c = cues[j]
        if c.start > cap:
            break
        if c.end > best_end:
            best_end = c.end
        
        # Sentence complete?
        if is_sentence_ending(c.text):
            # Natural clip end: prefer end of sentence when pause >= 600ms
            pause = get_pause_after(c, cues)
            if pause >= PAUSE_NATURAL_END_SEC:
                return min(best_end, cap)
            # Sentence ended, no strong pause - still a valid end
            return min(best_end, cap)
        
        # No sentence end - check if next cue has pause (acceptable cut point at 600ms+)
        if j + 1 < len(cues):
            next_c = cues[j + 1]
            gap = next_c.start - c.end
            if gap > PAUSE_NATURAL_END_SEC:
                # Natural pause before next cue - acceptable cut point
                return min(best_end, cap)
            # Stop context continuation when pause > 1s (topic change)
            if gap > PAUSE_TOPIC_CHANGE_SEC:
                return min(best_end, cap)
        else:
            break
    
    return min(best_end, cap)


def extend_end_to_complete_sentence(segment_end: float, cues: List[SubtitleCue], 
                                    max_extension: float = MAX_BOUNDARY_EXTENSION_SEC) -> float:
    """
    Extend segment_end so the clip never ends mid-sentence or mid-subtitle.
    - End at cue boundary; prefer sentence endings (., ?, !).
    - If next cue starts within 0.6s (SUBTITLE_CONTINUITY_SEC), treat as same sentence and extend.
    - Total extension capped at max_extension (8s).
    """
    if not cues:
        return segment_end
    cap = segment_end + max_extension
    # Find index of cue that contains segment_end or that we're past
    idx = -1
    for i, cue in enumerate(cues):
        if cue.start <= segment_end <= cue.end:
            idx = i
            break
        if segment_end < cue.start:
            if i > 0 and segment_end < cues[i - 1].end:
                idx = i - 1
            break
    if idx < 0:
        if segment_end < cues[0].start:
            return min(segment_end, cap)
        idx = len(cues) - 1
    # Start from current cue; extend through following cues if gap <= 0.6s until sentence end or cap
    best_end = segment_end
    for j in range(idx, len(cues)):
        c = cues[j]
        if c.start > cap:
            break
        if c.end > best_end:
            best_end = c.end
        if is_sentence_ending(c.text):
            return min(best_end, cap)
        if j + 1 < len(cues) and cues[j + 1].start - c.end > SUBTITLE_CONTINUITY_SEC:
            break
    return min(best_end, cap)


def find_best_boundary_near(target_time: float, cues: List[SubtitleCue], 
                            search_window: float = 5.0, is_start: bool = False,
                            min_end_time: Optional[float] = None) -> float:
    """
    Find the best boundary point near a target timestamp.
    If is_start=False and min_end_time is set, only consider candidates >= min_end_time
    (agar klip tidak terpotong sebelum kalimat selesai).
    """
    if not cues:
        return target_time
    
    candidates = []
    start_search = max(0, target_time - search_window)
    end_search = target_time + search_window
    
    for cue in cues:
        if start_search <= cue.start <= end_search:
            candidates.append(cue.start)
        if start_search <= cue.end <= end_search:
            candidates.append(cue.end)
    candidates.append(target_time)
    
    if min_end_time is not None and not is_start:
        candidates = [c for c in candidates if c >= min_end_time - 0.3]
        if not candidates:
            return max(target_time, min_end_time)
        target_time = max(target_time, min_end_time)
    
    if not candidates:
        return target_time
    
    best_time = target_time
    best_score = score_boundary_quality(target_time, cues, is_start)
    
    for candidate in candidates:
        score = score_boundary_quality(candidate, cues, is_start)
        if score > best_score:
            best_score = score
            best_time = candidate
    
    return best_time


def refine_segment_boundaries(segment: Dict, cues: List[SubtitleCue],
                              min_duration: float = 15.0, max_duration: float = 60.0) -> Dict:
    """
    Refine a segment's start/end times to align with subtitle boundaries.
    - Start: pre-roll buffer (max 4s) to include conversation setup, then skip filler
    - End: extend until sentence completes (max +5s), prefer punctuation at cue boundary
    """
    if not cues:
        return segment
    
    original_start = segment['start']
    original_end = segment['end']
    original_duration = original_end - original_start
    
    # [PART 1] Pre-roll buffer, then skip filler intro (move start to first meaningful sentence)
    buffer_start = max(0.0, original_start - PRE_ROLL_BUFFER_SEC)
    new_start = find_best_boundary_near(buffer_start, cues, search_window=2.0, is_start=True)
    new_start = refine_segment_start(new_start, original_end, cues, max_shift=REFINE_START_MAX_SHIFT_SEC)
    
    # [PART 2 & 3] Refine end: extend until sentence complete (max +5s), never cut mid-sentence
    min_end = refine_segment_end(original_end, cues, max_extension=SENTENCE_END_MAX_EXTENSION_SEC)
    
    new_end = find_best_boundary_near(
        max(original_end, min_end), cues, search_window=3.0, is_start=False,
        min_end_time=min_end
    )
    
    new_duration = new_end - new_start
    
    # Validate duration constraints
    if new_duration < min_duration:
        # Try extending end first
        new_end = new_start + min_duration
        new_end = find_best_boundary_near(new_end, cues, search_window=3.0, is_start=False)
        new_duration = new_end - new_start
        
        # If still too short, revert to original
        if new_duration < min_duration:
            return segment
    
    if new_duration > max_duration:
        # Try trimming from end
        new_end = new_start + max_duration
        new_end = find_best_boundary_near(new_end, cues, search_window=3.0, is_start=False)
        new_duration = new_end - new_start
        
        # If still too long, revert to original
        if new_duration > max_duration:
            return segment
    
    # Create refined segment
    refined = segment.copy()
    refined['start'] = new_start
    refined['end'] = new_end
    refined['_refined'] = True
    refined['_original_start'] = original_start
    refined['_original_end'] = original_end
    
    return refined


def refine_all_segments(segments: List[Dict], vtt_path: str,
                       min_duration: float = 15.0, max_duration: float = 60.0) -> Tuple[List[Dict], Dict]:
    """
    Refine all segments using subtitle data
    
    Returns:
        (refined_segments, stats_dict)
    """
    cues = load_subtitle_cues(vtt_path)
    
    stats = {
        'total_segments': len(segments),
        'refined_count': 0,
        'avg_adjustment': 0.0,
        'subtitle_cues_found': len(cues)
    }
    
    if not cues:
        print("  [SMART SEGMENT] Subtitle tidak tersedia, menggunakan batas waktu standar")
        return segments, stats
    
    print(f"  [SMART SEGMENT] Menemukan {len(cues)} subtitle cues, menyesuaikan batas klip...")
    
    refined_segments = []
    total_adjustment = 0.0
    
    for segment in segments:
        refined = refine_segment_boundaries(segment, cues, min_duration, max_duration)
        
        if refined.get('_refined'):
            stats['refined_count'] += 1
            adjustment = abs(refined['start'] - segment['start']) + abs(refined['end'] - segment['end'])
            total_adjustment += adjustment
        
        refined_segments.append(refined)
    
    if stats['refined_count'] > 0:
        stats['avg_adjustment'] = total_adjustment / stats['refined_count']
        print(f"  [SMART SEGMENT] OK Berhasil menyesuaikan {stats['refined_count']} dari {stats['total_segments']} klip")
        print(f"  [SMART SEGMENT] Rata-rata penyesuaian: {stats['avg_adjustment']:.1f} detik")
    
    return refined_segments, stats

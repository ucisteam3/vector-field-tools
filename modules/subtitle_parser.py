"""
Subtitle Parser Module
Handles parsing of various subtitle formats (VTT, SRT, JSON3) and caption file management
Backend-safe: works with WebAppContext or parent=None via safe_parent_call.
"""

import os
import re
import json
from pathlib import Path
from glob import glob
from datetime import timedelta


class SubtitleParser:
    """Manages all subtitle parsing and caption file operations"""
    
    def __init__(self, parent):
        """
        Initialize Subtitle Parser
        
        Args:
            parent: Reference to YouTubeHeatmapAnalyzer or WebAppContext (can be None)
        """
        self.parent = parent

    def safe_parent_call(self, method, *args, **kwargs):
        """Safely call a parent method if it exists. Returns None if parent=None or method missing."""
        if self.parent is None:
            return None
        if hasattr(self.parent, method):
            return getattr(self.parent, method)(*args, **kwargs)
        return None

    def _format_time(self, seconds):
        """Format seconds for SRT. Uses parent.format_time if available, else local fallback."""
        result = self.safe_parent_call("format_time", seconds)
        if result is not None:
            return str(result)
        return str(timedelta(seconds=int(seconds)))
    
    def parse_manual_transcript(self, raw_text):
        """Parse raw text with timestamps and merge into meaningful segments (30s - 180s)"""
        import re
        
        # [ROBUST] Regex for timestamp line (Handles optional hours or minutes-only)
        # Matches: 00:00.000, 00:00:00.000, 00:00:00,000, etc.
        time_pat = re.compile(r'([\d:.,]+)\s*--\>\s*([\d:.,]+)')
        # Pattern to match timestamps: MM:SS or HH:MM:SS (optional brackets)
        time_pattern = r'\[?(\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\]?[:\s-]*'
        
        # Split by timestamp while keeping timestamps
        parts = re.split(time_pattern, raw_text)
        
        found_data = []
        for i in range(1, len(parts), 2):
            time_str = parts[i].strip()
            content = parts[i+1].strip() if i+1 < len(parts) else ""
            
            # Convert timestamp to seconds
            t_parts = time_str.split(':')
            try:
                if len(t_parts) == 2: # MM:SS
                    seconds = int(t_parts[0]) * 60 + int(t_parts[1])
                elif len(t_parts) == 3: # HH:MM:SS
                    seconds = int(t_parts[0]) * 3600 + int(t_parts[1]) * 60 + int(t_parts[2])
                else:
                    continue
            except ValueError:
                continue
                
            found_data.append({'start': float(seconds), 'text': content})
            
        if not found_data:
            return {}
            
        # Sort by start time
        found_data.sort(key=lambda x: x['start'])
        
        if not found_data:
            return {}
            
        # Sort by start time
        found_data.sort(key=lambda x: x['start'])
        
        # Smart Merge Logic (Variable Duration)
        merged_transcriptions = {}
        
        MIN_DURATION = 6.0    # Minimum duration to consider splitting
        MAX_DURATION = 35.0   # Max duration - produces many candidates for viral detection
        
        current_chunk_start = found_data[0]['start']
        current_chunk_text = []
        chunk_idx = 0
        
        for i in range(len(found_data)):
            item = found_data[i]
            next_start = found_data[i+1]['start'] if i < len(found_data) - 1 else item['start'] + 5.0
            
            # Add text
            if item['text']:
                current_chunk_text.append(item['text'])
            
            # Duration check
            current_duration = next_start - current_chunk_start
            
            # Punctuation check (Split on sentence endings if we have enough duration)
            has_punctuation = item['text'] and item['text'].strip()[-1] in ['.', '?', '!']
            
            # Logic:
            # 1. MUST split if > MAX_DURATION
            # 2. CAN split if > MIN_DURATION AND has_punctuation (Natural break)
            # 3. MUST split if last item
            
            should_forced_split = current_duration >= MAX_DURATION
            can_natural_split = current_duration >= MIN_DURATION and has_punctuation
            is_last_item = (i == len(found_data) - 1)
            
            if should_forced_split or can_natural_split or is_last_item:
                duration = next_start - current_chunk_start
                
                # Check minimum duration (6s minimum)
                if duration < 6.0:
                    if is_last_item:
                         # Merge with previous if possible
                        if chunk_idx > 0:
                            prev_chunk = merged_transcriptions[chunk_idx-1]
                            prev_chunk['end'] = next_start
                            prev_chunk['text'] += " " + " ".join(current_chunk_text)
                    else:
                        # Not last item, keep accumulating
                        continue
                else:
                    # Duration OK!
                    merged_transcriptions[chunk_idx] = {
                        'start': current_chunk_start,
                        'end': next_start,
                        'text': " ".join(current_chunk_text),
                        'hook_script': ""
                    }
                    chunk_idx += 1
                    
                # Reset for next chunk
                current_chunk_start = next_start
                current_chunk_text = []
                
        # Limit candidate segments only if exceeding max (target: 120–180 per hour)
        total_segments = len(merged_transcriptions)
        MAX_CANDIDATES = 180

        if total_segments > MAX_CANDIDATES:
            print(f"  [LIMIT] Ditemukan {total_segments} segmen. Mengambil sampel {MAX_CANDIDATES} (kronologis).")
            # Downsample: pick evenly distributed indices to preserve chronological order
            step = total_segments / MAX_CANDIDATES
            selected_indices = [int(i * step) for i in range(MAX_CANDIDATES)]
            
            new_transcriptions = {}
            for new_idx, old_idx in enumerate(selected_indices):
                if old_idx in merged_transcriptions:
                    new_transcriptions[new_idx] = merged_transcriptions[old_idx]
            
            return new_transcriptions
            
        return merged_transcriptions

    def parse_vtt(self, vtt_path):
        """Parse VTT subtitle file into internal transcription format"""
        if not os.path.exists(vtt_path):
            return {}
            
        transcriptions = {}
        idx = 0
        
        try:
            with open(vtt_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Remove header and styles
            content = re.sub(r'^WEBVTT.*?(\n\n|$)', '', content, flags=re.DOTALL)
            content = re.sub(r'STYLE.*?-->', '', content, flags=re.DOTALL)
            
            blocks = content.strip().split('\n\n')
            for block in blocks:
                lines = block.strip().split('\n')
                if len(lines) < 2: continue
                
                timestamp_line = None
                text_lines = []
                for line in lines:
                    if '-->' in line:
                        timestamp_line = line
                    elif line and not line.isdigit():
                        text_lines.append(line)
                        
                if not timestamp_line or not text_lines: continue
                
                # Parse timestamps
                timestamp_line = re.sub(r'align:.*|position:.*', '', timestamp_line).strip()
                times = timestamp_line.split('-->')
                start_str = times[0].strip()
                end_str = times[1].strip()
                
                def time_to_sec(t_str):
                    t_str = t_str.strip()
                    parts = t_str.split(':')
                    if len(parts) == 3:
                        return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2].replace(',', '.'))
                    elif len(parts) == 2:
                        return int(parts[0]) * 60 + float(parts[1].replace(',', '.'))
                    return float(parts[0].replace(',', '.'))

                start = time_to_sec(start_str)
                end = time_to_sec(end_str)
                text = ' '.join(text_lines)
                text = re.sub(r'<[^>]+>', '', text).strip()
                
                if text:
                    transcriptions[idx] = {
                        'start': start,
                        'end': end,
                        'text': text
                    }
                    idx += 1
        except Exception as e:
            print(f"  [ERROR] Gagal parse VTT: {e}")
            
        return transcriptions

    def _caption_safe_key(self, s):
        """Sanitize caption key for filename matching."""
        if not s: return ''
        s = s.strip()
        s = re.sub(r'[^A-Za-z0-9\-_]+', '_', s)
        s = re.sub(r'_+', '_', s)
        return s.strip('_')

    def derive_caption_keys(self, video_path, video_id=None):
        """Return a priority-ordered list of possible caption keys."""
        keys = []
        if video_id:
            keys.append(self._caption_safe_key(video_id))
            keys.append(f"{self._caption_safe_key(video_id)}_source")
        
        if video_path:
            base = os.path.splitext(os.path.basename(video_path))[0]
            base = self._caption_safe_key(base)
            if base:
                keys.append(base)
                if base.endswith('_source'):
                    keys.append(base[:-7])
        
        seen = set()
        out = []
        for k in keys:
            if k and k not in seen:
                seen.add(k)
                out.append(k)
        return out

    def find_sidecar_caption(self, video_path, video_id=None):
        """Try to find a sidecar caption file for a given video."""
        search_dirs = []
        if video_path:
            # Use absolute path to ensure we have a valid directory
            vdir = os.path.dirname(os.path.abspath(video_path))
            if vdir: search_dirs.append(vdir)
        
        # Fallback to current working directory if somehow empty
        if not search_dirs:
            search_dirs.append(os.getcwd())
        
        # PRIORITY 1: Try exact basename match (without sanitization)
        # CHANGED: Prioritize .srt first since it's more reliable to parse
        if video_path:
            exact_base = os.path.splitext(os.path.basename(video_path))[0]
            for d in search_dirs:
                for ext in ['.srt', '.vtt', '.words.json']:  # SRT first!
                    cand = os.path.join(d, f"{exact_base}{ext}")
                    if os.path.exists(cand) and os.path.getsize(cand) > 0:
                        kind = ext.replace('.', '').replace('json', 'words_json')
                        return {'found': True, 'path': cand, 'kind': kind}
        
        # PRIORITY 2: Try sanitized keys (for backward compatibility)
        keys = self.derive_caption_keys(video_path, video_id=video_id)
        
        for d in search_dirs:
            for k in keys:
                for ext in ['.srt', '.vtt', '.words.json']:  # SRT first!
                    cand = os.path.join(d, f"{k}{ext}")
                    if os.path.exists(cand) and os.path.getsize(cand) > 0:
                        kind = ext.replace('.', '').replace('json', 'words_json')
                        return {'found': True, 'path': cand, 'kind': kind}
        
        return {'found': False}

    def parse_structured_segments(self, text):
        """
        Parse manual/external-AI segment list text into structured segments.
        Accepted line examples:
          - 01:45-03:30
          - 01:45 - 03.30 | optional title
          - 00:01:10-00:03:00 | Title
        """
        segs = {}
        if not text:
            return segs
        
        raw_lines = str(text).splitlines()
        idx = 0
        for raw in raw_lines:
            if not raw: continue
            line = raw.strip()
            if not line: continue
            if line.startswith('#'): continue
            
            title = 'Viral Moment'
            if '|' in line:
                parts = line.split('|')
                line = parts[0].strip()
                title = parts[1].strip()
            
            # Replace unicode dashes with standard dash
            line = line.replace('–', '-').replace('—', '-')
            
            m = re.match(r'^\s*(.+?)\s*-\s*(.+?)\s*$', line)
            if not m:
                continue
                
            def time_to_sec(t_str):
                t_str = t_str.strip().replace('.', ':')
                parts = t_str.split(':')
                try:
                    if len(parts) == 3: # HH:MM:SS
                        return int(parts[0])*3600 + int(parts[1])*60 + float(parts[2])
                    elif len(parts) == 2: # MM:SS
                        return int(parts[0])*60 + float(parts[2])
                    elif len(parts) == 1: # SS
                        return float(parts[0])
                except:
                    return None
                return None

            a = time_to_sec(m.group(1))
            b = time_to_sec(m.group(2))
            
            if a is None or b is None:
                continue
                
            if b <= a:
                continue
                
            segs[idx] = {
                'start': float(a),
                'end': float(b),
                'text': title,
                'hook_script': ""
            }
            idx += 1
            
        return segs

    def _parse_json3(self, data):
        """Convert YouTube JSON3 format to internal transcription format."""
        transcriptions = {}
        idx = 0
        events = data.get('events', [])
        
        for event in events:
            segs = event.get('segs', [])
            if not segs: continue
            
            start_ms = float(event.get('tStartMs', 0))
            duration_ms = float(event.get('dDurationMs', 0))
            
            # Combine segments into a single line for this event
            text = "".join([s.get('utf8', '') for s in segs]).strip()
            if not text or text == '\n': continue
            
            transcriptions[idx] = {
                'start': start_ms / 1000.0,
                'end': (start_ms + duration_ms) / 1000.0,
                'text': text
            }
            idx += 1
        return transcriptions

    def _fix_sub_overlaps(self, subs):
        """Remove cumulative 'rolling' text from YouTube auto-subtitles."""
        if not subs: return subs
        
        # Sort by start time just in case
        sorted_keys = sorted(subs.keys(), key=lambda k: subs[k]['start'])
        out = {}
        last_text = ""
        
        for k in sorted_keys:
            curr = subs[k]
            text = curr['text'].strip()
            
            # [CRITICAL] Handle Rolling/Cumulative Text
            # If current text is just the last text + a little bit more,
            # we only want that "little bit more".
            if last_text and text.startswith(last_text):
                new_part = text[len(last_text):].strip()
                if new_part:
                    out[k] = {
                        'start': curr['start'],
                        'end': curr['end'],
                        'text': new_part
                    }
                    last_text = text
                else:
                    # It's an exact duplicate or empty addition, skip
                    continue
            else:
                out[k] = curr
                last_text = text
                
        return out

    def _write_srt_from_data(self, data, out_path, max_words=8):
        """Save transcription data to SRT with grouping for better AI readability."""
        try:
            with open(out_path, 'w', encoding='utf-8') as f:
                idx = 1
                current_group = []
                group_start = None
                group_end = None
                
                # data is usually a dict of {idx: {start, end, text}}
                sorted_items = sorted(data.values(), key=lambda x: x['start'])
                
                for item in sorted_items:
                    if group_start is None:
                        group_start = item['start']
                    
                    current_group.append(item['text'])
                    group_end = item['end']
                    
                    # Split into chunks of max_words or if text is long
                    words_in_group = " ".join(current_group).split()
                    if len(words_in_group) >= max_words:
                        # Flush
                        t0 = self._format_time(group_start)
                        t1 = self._format_time(group_end)
                        f.write(f"{idx}\n{t0.replace('.', ',')} --> {t1.replace('.', ',')}\n{' '.join(current_group)}\n\n")
                        
                        idx += 1
                        current_group = []
                        group_start = None
                
                # Final flush
                if current_group:
                    t0 = self._format_time(group_start)
                    t1 = self._format_time(group_end)
                    f.write(f"{idx}\n{t0.replace('.', ',')} --> {t1.replace('.', ',')}\n{' '.join(current_group)}\n\n")
                
                # Ensure file is written
                f.flush()
                os.fsync(f.fileno())
                    
        except Exception as e:
            print(f"  [ERROR] Gagal menulis SRT: {e}")

    def _write_srt_from_segments(self, segments, out_path):
        """Convert segment list to SRT format (from competitor's approach)"""
        try:
            with open(out_path, 'w', encoding='utf-8') as f:
                for idx, seg in enumerate(segments, 1):
                    start_time = self._format_time(seg['start']).replace('.', ',')
                    end_time = self._format_time(seg['end']).replace('.', ',')
                    text = seg['text']
                    f.write(f"{idx}\n{start_time} --> {end_time}\n{text}\n\n")
        except Exception as e:
            print(f"  [ERROR] Gagal menulis SRT dari segments: {e}")


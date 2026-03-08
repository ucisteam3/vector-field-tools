import os
from datetime import timedelta
try:
    import whisper
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False

def seconds_to_ass_time(seconds):
    """Convert seconds to ASS format H:MM:SS.cs"""
    td = timedelta(seconds=seconds)
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    centiseconds = int((seconds - total_seconds) * 100)
    return f"{hours}:{minutes:02d}:{secs:02d}.{centiseconds:02d}"

def ass_time_to_seconds(ass_time):
    """Convert ASS/VTT time (H:MM:SS.cs or MM:SS.cs) to seconds"""
    try:
        parts = ass_time.replace('.', ':').split(':')
        if len(parts) == 4: # H:MM:SS.cs
            h, m, s, cs = map(int, parts)
            return h*3600 + m*60 + s + cs/1000.0
        elif len(parts) == 3: # MM:SS.cs (VTT often) or H:MM:SS
            # VTT usually HH:MM:SS.mmm
            # We need to handle flexible parsing
            pass
    except: pass
    
    # Robust string check
    import re
    # Match HH:MM:SS.mmm or MM:SS.mmm
    match = re.search(r'(\d{1,2}):(\d{2}):(\d{2})[\.,](\d{2,3})', ass_time)
    if match:
         h, m, s, ms = map(int, match.groups())
         ms_val = ms / 1000.0 if len(str(ms)) == 3 else ms / 100.0
         return h*3600 + m*60 + s + ms_val
    
    # Try MM:SS.mmm
    match = re.search(r'(\d{1,2}):(\d{2})[\.,](\d{2,3})', ass_time)
    if match:
         m, s, ms = map(int, match.groups())
         ms_val = ms / 1000.0 if len(str(ms)) == 3 else ms / 100.0
         return m*60 + s + ms_val
         
    return 0.0
def flexible_time_to_seconds(t_str):
    """
    Robust time converter for MM:SS.mmm, HH:MM:SS.mmm, or HH:MM:SS,mmm
    """
    if not t_str: return 0.0
    # Normalize separator
    t_str = t_str.replace(',', '.')
    parts = t_str.split(':')
    try:
        if len(parts) == 3: # H:M:S
            return int(parts[0])*3600 + int(parts[1])*60 + float(parts[2])
        elif len(parts) == 2: # M:S
            return int(parts[0])*60 + float(parts[1])
        else:
            return float(parts[0])
    except:
        return 0.0

def generate_ass_from_vtt(vtt_path, clip_start_offset, output_ass_path, settings):
    """
    Parse existing WebVTT file, extract relevant lines for the clip (based on offset),
    and generate ASS with 'Fake Karaoke' (distributing word timing evenly).
    """
    import re
    
    events = []
    
    # Read VTT
    with open(vtt_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    # Simple VTT Parser
    # 00:00:00.000 --> 00:00:04.160
    # Text
    
    # [ROBUST] Regex for timestamp line (Handles optional hours or minutes-only)
    # Matches: 00:00.000, 00:00:00.000, 00:00:00,000, etc.
    time_pat = re.compile(r'([\d:.,]+)\s*--\>\s*([\d:.,]+)')
    
    current_start = 0.0
    current_end = 0.0
    
    collected_events = []
    
    last_text = ""
    last_end = 0.0
    for i, line in enumerate(lines):
        line = line.strip()
        match = time_pat.search(line)
        if match:
            s_str, e_str = match.groups()
            s_sec = flexible_time_to_seconds(s_str)
            e_sec = flexible_time_to_seconds(e_str)
            
            # Check content in next line
            if i + 1 < len(lines):
                text = lines[i+1].strip()
                # Remove tags
                text = re.sub(r'<[^>]+>', '', text)
                
                # [FIX] De-duplicate: YouTube VTT often repeats lines in sequential cues
                if text == last_text:
                    continue
                last_text = text
                
                # Check intersection with Clip
                # Clip Range: [clip_start_offset, clip_start_offset + 120 (max)]
                # Warning: We don't verify Clip End here, usually the clip audio cut determines duration.
                # But we should shift timestamps.
                
                # We want events that start AFTER clip_start, relative to it.
                # Or start overlapping.
                
                # Shifted Times (Adjusted earlier by 1.1s to feel more snappy/in-sync)
                sync_adj = -1.1
                rel_start = s_sec - clip_start_offset + sync_adj
                rel_end = e_sec - clip_start_offset + sync_adj
                
                # Filter: Keep if relative start >= -1.0 (allow small overlap)
                # And usually clip is max 90s, so discard if rel_start > 120
                if rel_end > 0 and rel_start < 120:
                     # [FIX] Prevent Overlap Stacking (libass Alignment 2)
                     final_start = max(last_end, max(0.0, rel_start))
                     if rel_end > final_start + 0.1: # At least 0.1s duration
                         collected_events.append({
                             'start': final_start,
                             'end': rel_end,
                             'text': text
                         })
                         last_end = rel_end
                     
    # Generate ASS Content
    font = settings.get("subtitle_font", "Arial")
    # [FIX] Scale font size for 1080p resolution
    # Increased to 6x for better visibility in 9:16 vertical videos
    size = int(settings.get("subtitle_fontsize", 24) * 6)
    
    def hex_to_ass_color(hex_color):
        if not hex_color or not hex_color.startswith("#"): return "&H00FFFFFF"
        r = hex_color[1:3]
        g = hex_color[3:5]
        b = hex_color[5:7]
        return f"&H00{b}{g}{r}"
        
    primary = hex_to_ass_color(settings.get("subtitle_text_color", "#FFFFFF"))
    outline_color = hex_to_ass_color(settings.get("subtitle_outline_color", "#000000"))
    highlight = hex_to_ass_color(settings.get("subtitle_highlight_color", "#FFFF00"))
    margin_v = int(settings.get('subtitle_position_y', 50))
    
    from modules.font_manager import FONT_NAME_MAP
    font_name_ass = FONT_NAME_MAP.get(font, font)

    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name_ass},{size},{primary},{primary},{outline_color},&H80000000,-1,0,0,0,100,100,0,0,1,{settings.get('subtitle_outline_width', 2)},0,2,10,10,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    
    ass_events = []
    
    # Process "Fake Karaoke" (Word Splitting)
    # We enforce the Max 4 words / Max 3 lines rule too?
    # Actually, YouTube CC is usually already segmented well (1-2 lines).
    # But for "Viral Format" we might want to respect the user's "Max 4 words" preference if possible.
    # Splitting YouTube lines is harder because we don't know exact word times.
    # Approach: Just use the YouTube lines as is, but apply Karaoke Effect by splitting duration uniformly.
    
    for item in collected_events:
        words = item['text'].split()
        if not words: continue
        
        start_t = item['start']
        end_t = item['end']
        duration = end_t - start_t
        
        # Max 4 words per line, Max 2 lines per screen = Group into chunks of 8
        chunks = []
        for i in range(0, len(words), 8):
            chunks.append(words[i:i+8])
            
        # Distribute duration among chunks (roughly)
        chunk_duration = duration / len(chunks)
        
        for k, chunk in enumerate(chunks):
            # Calculate chunk specific timeline
            c_start = start_t + (k * chunk_duration)
            c_end = start_t + ((k+1) * chunk_duration)
            
            # Words in this chunk (Max 8 words)
            # Split this chunk into 2 lines of 4 words each if needed
            line_str = ""
            for w_idx, word in enumerate(chunk):
                # Fake timestamps for animation
                # Relative to Line Start (c_start)
                word_duration = chunk_duration / len(chunk)
                t_rel_start = int((w_idx * word_duration) * 1000)
                t_rel_end = int(((w_idx+1) * word_duration) * 1000)
                
                # Add Line Break (\N) after 4 words
                if w_idx == 4:
                    line_str += "\\N"
                
                # Active Highlight with Zoom Animation (100% -> 120% -> 100%)
                line_str += f"{{\\1c{primary}\\fscx100\\fscy100\\t({t_rel_start},{t_rel_start+20},\\1c{highlight}\\fscx120\\fscy120)\\t({t_rel_end},{t_rel_end+20},\\1c{primary}\\fscx100\\fscy100)}}{word} "
            
            # Output Event
            start_str = seconds_to_ass_time(c_start)
            end_str = seconds_to_ass_time(c_end)
            
            ass_events.append(f"Dialogue: 0,{start_str},{end_str},Default,,0,0,0,,{line_str}")

    with open(output_ass_path, "w", encoding='utf-8') as f:
        f.write(header)
        f.write("\n".join(ass_events))
        
    return True

def generate_karaoke_ass(audio_path, output_ass_path, settings):
    """
    Generate ASS subtitle file with Karaoke effects (\\k) using Whisper word-level timestamps.
    """
    if not WHISPER_AVAILABLE:
        print("[SUBTITLE] Whisper library not found.")
        # But if mode is youtube_cc, we don't need Whisper!
        if settings.get("whisper_model") != "youtube_cc":
            return False
            
    try:
        # [NEW LOGIC] Check for YouTube CC Mode
        if settings.get("whisper_model") == "youtube_cc":
            vtt_path = settings.get("video_vtt_path")
            clip_start = settings.get("clip_start_time", 0.0)
            
            if vtt_path and os.path.exists(vtt_path):
                print(f"[SUBTITLE] Generating from YouTube CC: {vtt_path} (Offset: {clip_start}s)")
                return generate_ass_from_vtt(vtt_path, clip_start, output_ass_path, settings)
            else:
                print(f"[SUBTITLE] YouTube CC mode selected but VTT not found. Fallback to Whisper Small?")
                # Fallback to Whisper to ensure output
                model_name = "small"
        else:
            # [UPGRADE] User selection for trade-off between Size vs Accuracy.
            model_name = settings.get("whisper_model", "small")
            
        print(f"[SUBTITLE] Loading '{model_name}' model (based on user Settings)...")
        # Ensure models are saved locally in the project (portable)
        models_root = os.path.join(os.getcwd(), "assets", "models")
        os.makedirs(models_root, exist_ok=True)
        
        # [FIX] Detect GPU for massive speedup (prevents 'mentok' / hang on CPU)
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
        if device == "cuda":
            print(f"[SUBTITLE] GPU DETECTED! Using NVIDIA CUDA for ultra-fast transcription.")
        else:
            print(f"[SUBTITLE] WARNING: No GPU detected or Torch-CUDA not installed. Using CPU (Will be SLOW for 'medium' model).")

        from modules.transcription_engine import get_cached_whisper_model
        model = get_cached_whisper_model(model_name, device, download_root=models_root)
        
        print(f"[SUBTITLE] Transcribing {audio_path} for karaoke...")
        result = model.transcribe(
            str(audio_path), word_timestamps=True, beam_size=5, fp16=(device == "cuda")
        )
        
        # Prepare ASS Header
        font = settings.get("subtitle_font", "Arial")
        # [FIX] Scale font size for 1080p resolution
        # Increased to 6x for better visibility in 9:16 vertical videos
        # Preview uses: base * (canvas_h / 480) * 1.5 to match export 6x scale
        size = int(settings.get("subtitle_fontsize", 24) * 6)
        
        # Colors are hex strings e.g. "#FFFFFF". ASS needs &HBBGGRR
        def hex_to_ass_color(hex_color):
            if not hex_color or not hex_color.startswith("#"): return "&H00FFFFFF"
            # #RRGGBB -> &H00BBGGRR
            r = hex_color[1:3]
            g = hex_color[3:5]
            b = hex_color[5:7]
            return f"&H00{b}{g}{r}"
            
        primary = hex_to_ass_color(settings.get("subtitle_text_color", "#FFFFFF"))
        outline_color = hex_to_ass_color(settings.get("subtitle_outline_color", "#000000"))
        highlight = hex_to_ass_color(settings.get("subtitle_highlight_color", "#FFFF00")) 
        
        # [FIX] For "Active Word Only" highlight (Bouncing Ball style):
        # We want Base Color -> Highlight -> Base Color.
        # So Primary and Secondary should both be the Base Color in the style.
        # We will use \t tags to animate the color change.
        
        
        # [FIX] Font Matching:
        # libass often fails to match "Luckiest Guy" to "LuckiestGuy-Regular.ttf".
        # We must try to use the EXACT Font Name stored in the file.
        # We now have a mapping in font_manager.
        from modules.font_manager import FONT_NAME_MAP
        
        user_font = settings.get("subtitle_font", "Arial")
        # Lookup real name or fallback to user_font (filename base)
        font_name_ass = FONT_NAME_MAP.get(user_font, user_font)
        
        # [FIX] Position Scaling:
        # User slider is 0-1200. PlayResY is 1920.
        # We now use 1:1 pixel mapping (unified with Preview and Watermark).
        margin_v = int(settings.get('subtitle_position_y', 50))

        header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,{font_name_ass},{size},{primary},{primary},{outline_color},&H80000000,-1,0,0,0,100,100,0,0,1,{settings.get('subtitle_outline_width', 2)},0,2,10,10,{margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
        
        events = []
        
        # [FIX] Max 4 Words per Line, Max 2 Lines per Screen
        # 4 words * 2 lines = 8 words per "Event" (Screen clear)
        MAX_WORDS_PER_LINE = 4
        MAX_LINES = 2
        WORDS_PER_EVENT = MAX_WORDS_PER_LINE * MAX_LINES
        
        last_end_sec = 0.0
        for segment in result["segments"]:
            words = segment.get("words", [])
            if not words:
                # Fallback for no-word-timestamp segments
                start_time = seconds_to_ass_time(segment["start"])
                end_time = seconds_to_ass_time(segment["end"])
                events.append(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{segment['text']}")
                continue

            # Process words in Chunks of 12 (Max screen capacity)
            num_words = len(words)
            for i in range(0, num_words, WORDS_PER_EVENT):
                event_chunk = words[i : i + WORDS_PER_EVENT]
                if not event_chunk: continue
                
                # Event timing
                c_start_sec = max(last_end_sec, event_chunk[0]["start"])
                c_end_sec = event_chunk[-1]["end"]
                last_end_sec = c_end_sec
                
                start_time = seconds_to_ass_time(c_start_sec)
                end_time = seconds_to_ass_time(c_end_sec)
                
                text_content = ""
                
                # Iterate words in this event to add Line Breaks
                for j, word in enumerate(event_chunk):
                    w_start = word["start"]
                    w_end = word["end"]
                    word_text = word["word"].strip()
                    
                    # Relative time calculation
                    t_start = int((w_start - c_start_sec) * 1000)
                    t_end = int((w_end - c_start_sec) * 1000)
                    
                    # Add Line Break (\N) every 4 words, but not at the very start
                    if j > 0 and j % MAX_WORDS_PER_LINE == 0:
                        text_content += "\\N" 
                        
                    # Add Karaoke Word with Zoom Animation (100% -> 120% -> 100%)
                    text_content += f"{{\\1c{primary}\\fscx100\\fscy100\\t({t_start},{t_start+20},\\1c{highlight}\\fscx120\\fscy120)\\t({t_end},{t_end+20},\\1c{primary}\\fscx100\\fscy100)}}{word_text} "
                
                events.append(f"Dialogue: 0,{start_time},{end_time},Default,,0,0,0,,{text_content}")
            
        with open(output_ass_path, "w", encoding='utf-8') as f:
            f.write(header)
            f.write("\n".join(events))
            
        print(f"[SUBTITLE] ASS file generated: {output_ass_path}")
        return True
        
    except Exception as e:
        print(f"[SUBTITLE] Error generating ASS: {e}")
        return False

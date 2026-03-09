"""
AI Engine Module for YouTube Heatmap Analyzer
Handles all AI-related functionality including:
- Title generation and validation
- Clip category detection
- Viral segment analysis
- API interactions with Gemini and OpenAI (OpenAI is primary for clip detection, titles, hooks)
"""

import os
import re
import json
import time
from google import genai

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OpenAI = None
    OPENAI_AVAILABLE = False


def load_openai_key():
    """Load OpenAI API key from openai.txt. Tries project root then current dir. Do not hardcode keys."""
    candidates = [
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "openai.txt"),
        "openai.txt",
        os.path.join(os.getcwd(), "openai.txt"),
    ]
    for path in candidates:
        try:
            if os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as f:
                    key = f.read().strip()
                    if key:
                        print(f"[OPENAI] API key loaded from {path}")
                        return key
        except Exception as e:
            print(f"[OPENAI] Failed to read {path}: {e}")
            continue
    print("[OPENAI] No API key - openai.txt missing or invalid. OpenAI will be skipped.")
    return None


def _title_from_transcript(segment_text):
    """Fallback hanya jika API gagal: judul dari isi percakapan (bukan teks generik)."""
    if not (segment_text or "").strip():
        return "Klip"
    s = (segment_text or "").strip()
    if len(s) <= 55:
        return s
    return s[:52].rstrip() + "..."


# [TITLE GENERATION] Viral Title Examples by Category
VIRAL_TITLE_EXAMPLES = {
    "informatif": [
        "Cara Cepat Kaya dari Nol Tanpa Modal",
        "Rahasia Bumbu Nasi Goreng Abang-Abang",
        "Tips Lolos Interview Kerja 100% Berhasil"
    ],
    "lucu": [
        "Momen Kocak Pas Kepedesan Level 10",
        "Reaksi Kocak Kalah 10x Beruntun di Game",
        "Kucing Pinter Banget Buka Pintu Sendiri"
    ],
    "kontroversial": [
        "Hot Take Kontroversial Soal Sistem Pendidikan",
        "Statement Berani Tentang Politik Hari Ini",
        "Fakta Mengejutkan di Balik Layar Industri"
    ],
    "emosional": [
        "Kisah Haru Pertemuan Setelah 10 Tahun",
        "Detik-detik Kecelakaan yang Bikin Nangis",
        "Momen Paling Emosional Tahun Ini"
    ]
}


class AIEngine:
    """Handles all AI operations for the YouTube Heatmap Analyzer"""
    
    def __init__(self, parent):
        """
        Initialize AI Engine
        
        Args:
            parent: Reference to main YouTubeHeatmapAnalyzer instance
        """
        self.parent = parent
        self._openai_client = None

        # Respect preferred provider from WebAppContext (dropdown on dashboard)
        preferred = None
        try:
            preferred = getattr(parent, "preferred_ai_provider", None)
        except Exception:
            preferred = None
        preferred = (preferred or "").strip().lower() or None

        # Only initialize OpenAI client when either explicitly selected or no preference
        api_key = None
        if preferred in (None, "", "openai"):
            try:
                # Prefer keys from WebAppContext/settings (multi-key rotation)
                if parent and hasattr(parent, "get_openai_key"):
                    api_key = parent.get_openai_key()
            except Exception:
                api_key = None
            if not api_key:
                api_key = load_openai_key()
            if OPENAI_AVAILABLE and api_key:
                try:
                    self._openai_client = OpenAI(api_key=api_key)
                    self.openai_available = True
                    print("[OPENAI] Client initialized - GPT-4o will be used for ranking, titles, and hook refinement.")
                except Exception as e:
                    self.openai_available = False
                    print(f"[OPENAI] Client init failed: {e}. OpenAI will be skipped.")
            else:
                self.openai_available = False
                if not OPENAI_AVAILABLE:
                    print("[OPENAI] Package 'openai' not installed. Run: pip install openai")
        else:
            # User chose non-OpenAI provider: disable OpenAI for this run
            self.openai_available = False

    def _maybe_rotate_openai_on_error(self, err: Exception) -> bool:
        """Rotate OpenAI key only when the current key errors/unusable."""
        if not self.parent or not hasattr(self.parent, "rotate_openai_api_key"):
            return False
        # Only rotate for auth/quota/rate-limit style failures
        msg = str(err).lower()
        if any(k in msg for k in ["401", "invalid api key", "incorrect api key", "quota", "rate limit", "429", "insufficient_quota"]):
            try:
                if hasattr(self.parent, "rotate_on_error") and not self.parent.rotate_on_error.get("openai", True):
                    return False
            except Exception:
                pass
            try:
                rotated = self.parent.rotate_openai_api_key()
                if rotated:
                    # Re-init client with new key
                    try:
                        api_key = self.parent.get_openai_key() if hasattr(self.parent, "get_openai_key") else None
                        if api_key and OPENAI_AVAILABLE:
                            self._openai_client = OpenAI(api_key=api_key)
                            self.openai_available = True
                    except Exception:
                        pass
                return rotated
            except Exception:
                return False
        return False
    
    def clean_viral_title(self, title):
        """Hard filter to strip forbidden repetitive words (Gila, Parah, etc)"""
        if not title:
            return ""
        
        # List of words to strip (case insensitive)
        forbidden = [
            r'Gila!?', r'Parah!?', r'Mengerikan!?', r'Sadis!?', 
            r'Bikin Gila', r'Bikin Parah', r'Jadi Gila', r'Gokil!?'
        ]
        
        cleaned = title
        for word in forbidden:
            # Replace at start of string or anywhere else
            cleaned = re.sub(rf"(?i)^{word}\s*:?\s*", "", cleaned)  # Strip from start
            cleaned = re.sub(rf"(?i)\s+{word}", "", cleaned)  # Strip from middle/end
            
        # Clean up any leftover double spaces, punctuation, or QUOTES
        cleaned = cleaned.strip().strip("!").strip('"').strip("'").strip()
        
        # If empty after cleaning (rare), provide a safe fallback
        if not cleaned:
            return "Momen Menarik"
        
        return cleaned
    
    def validate_title_quality(self, title):
        """
        Validate title quality based on cari-judul.md standards.
        
        Returns:
            (bool, str, int): (is_valid, error_message, quality_score)
        """
        if not title:
            return False, "Judul kosong", 0
        
        score = 0
        errors = []
        
        # 1. Length check (40-60 ideal)
        length = len(title)
        if length < 20:
            errors.append("Terlalu pendek (min 40 karakter)")
        elif 40 <= length <= 60:
            score += 30  # Perfect length
        elif 20 <= length < 40:
            score += 15  # Acceptable but short
        elif length > 75:
            errors.append("Terlalu panjang (max 75 karakter)")
        else:
            score += 20  # OK length
        
        # 2. Emoji check (should have 1-2)
        emoji_pattern = re.compile("["
            u"\U0001F600-\U0001F64F"  # emoticons
            u"\U0001F300-\U0001F5FF"  # symbols & pictographs
            u"\U0001F680-\U0001F6FF"  # transport & map
            u"\U0001F1E0-\U0001F1FF"  # flags
            "]+", flags=re.UNICODE)
        
        emojis = emoji_pattern.findall(title)
        if len(emojis) == 1 or len(emojis) == 2:
            score += 20
        elif len(emojis) == 0:
            errors.append("Tidak ada emoji")
        
        # 3. Forbidden patterns (generic titles)
        generic_patterns = [
            r'^(Viral|Menarik|Lucu|Kocak)\s*$',
            r'^(Video|Klip|Momen)\s+(Viral|Menarik)$',
            r'^(Bagian|Segment)\s+\d+$',
        ]
        
        for pattern in generic_patterns:
            if re.match(pattern, title, re.IGNORECASE):
                errors.append(f"Judul terlalu generic: {title}")
                score -= 30
        
        # 4. Word count (should be 4+ words for context)
        words = title.split()
        text_words = [w for w in words if not emoji_pattern.match(w)]
        
        if len(text_words) >= 5:
            score += 20  # Good context
        elif len(text_words) >= 3:
            score += 10  # Acceptable
        else:
            errors.append("Terlalu sedikit kata (min 4 kata)")
        
        # 5. Check for quotes (forbidden)
        if '"' in title or "'" in title or '`' in title:
            errors.append("Mengandung tanda kutip (dilarang)")
            score -= 20
        
        # 6. Check for specificity keywords
        good_keywords = [
            'cara', 'tips', 'rahasia', 'fakta', 'alasan', 
            'momen', 'reaksi', 'kisah', 'detik', 'ternyata',
            'hot take', 'statement', 'begini', 'beginilah'
        ]
        
        has_good_keyword = any(kw in title.lower() for kw in good_keywords)
        if has_good_keyword:
            score += 20
        
        # Final validation
        is_valid = score >= 50 and len(errors) == 0
        error_msg = "; ".join(errors) if errors else ""
        
        return is_valid, error_msg, min(100, max(0, score))
    
    def detect_clip_category(self, transcript_text):
        """Detect clip category from transcript for better title generation"""
        text_lower = transcript_text.lower()
        
        if any(kw in text_lower for kw in ['cara', 'tips', 'rahasia', 'tutorial', 'belajar']):
            return 'informatif'
        elif any(kw in text_lower for kw in ['lucu', 'kocak', 'ngakak', 'ketawa', 'humor']):
            return 'lucu'
        elif any(kw in text_lower for kw in ['kontroversial', 'hot take', 'statement', 'shocking']):
            return 'kontroversial'
        elif any(kw in text_lower for kw in ['sedih', 'haru', 'nangis', 'emosi', 'terharu']):
            return 'emosional'
        else:
            return 'informatif'  # default
    
    def _use_gemini_for_ai(self):
        """True when user selected Gemini (or non-OpenAI) and Gemini is available."""
        return (
            getattr(self.parent, "gemini_available", False)
            and (not self._openai_client or not self.openai_available)
        )

    def _generate_title_gemini(self, segment_text, existing_titles=None, strict_content=False):
        """Generate clickbait title using Gemini. Used when API selected is Gemini."""
        if not segment_text or not getattr(self.parent, "gemini_client", None):
            return _title_from_transcript(segment_text)
        try:
            prompt = """Kamu ahli YouTube Shorts untuk penonton Indonesia.
Dari percakapan/transkrip berikut, buat SATU judul clickbait yang menarik (bukan generic).
Aturan: BAHASA INDONESIA, maks 60 karakter, awali 1 emoji. Jangan pakai kata Gila/Parah.
Judul harus mencerminkan isi klip. Jawab HANYA judul (tanpa tanda kutip).

Percakapan:
"""
            prompt += (segment_text[:2000] if segment_text else "").strip()
            response = self.parent.gemini_client.models.generate_content(
                model="gemini-2.0-flash", contents=prompt
            )
            title = (response.text or "").strip().strip('"').strip("'")
            title = self.clean_viral_title(title) if title else ""
            if title and len(title) >= 8 and len(title) <= 80:
                return title[:60]
        except Exception as e:
            print(f"[GEMINI] Title generation failed: {e}")
        return _title_from_transcript(segment_text)

    def _refine_hook_gemini(self, hook_text):
        """Refine hook using Gemini. Returns (refined_hook, score)."""
        if not (hook_text or "").strip() or not getattr(self.parent, "gemini_client", None):
            return (hook_text or "").strip(), 50
        try:
            prompt = f"""Perbaiki kalimat hook berikut agar lebih menarik dan singkat (max 10 kata). Bahasa Indonesia. Jawab HANYA kalimat hook saja, tanpa penjelasan.

Hook: {hook_text[:500]}"""
            response = self.parent.gemini_client.models.generate_content(
                model="gemini-2.0-flash", contents=prompt
            )
            refined = (response.text or "").strip().strip('"').strip("'")
            if refined:
                return refined[:120], 65
        except Exception as e:
            print(f"[GEMINI] Hook refine failed: {e}")
        return (hook_text or "").strip(), 50

    def analyze_with_gemini(self, text, start_time, end_time, retry_count=0):
        """Use Gemini API with rotation support to analyze and summarize content"""
        if not self.parent.gemini_available or not text or text.startswith("["):
            return text
        
        try:
            prompt = f"""Kamu adalah ahli konten viral YouTube Shorts & TikTok. Tugasmu adalah membuat JUDUL VIRAL yang sangat "hooky" berdasarkan transkrip berikut.
            
Target Audiens: Gen Z & Milenial
Genre: {self.parent.current_genre.get()}
Tone: {self.parent.current_style.get()}

Transkrip: "{text}"

Tugas:
Buat 1 Judul MENARIK tapi NATURAL (Jangan pakai kata 'Gila' atau 'Parah').
Gunakan formula: [Variasi Hook] + [Emosi] -> Contoh: "Ternyata... Begini Caranya"

Tugas Tambahan:
Buat 1 kalimat "HOOK" sangat pendek (max 10 kata) untuk diucapkan AI di awal video agar penonton penasaran.

Output Format (JSON):
{{"title": "Judul Viral", "hook": "Kalimat pembuka AI"}}
"""
            
            response = self.parent.gemini_client.models.generate_content(
                model='gemini-2.0-flash',
                contents=prompt
            )
            
            # Parse JSON response
            response_data = json.loads(response.text.strip())
            summary = self.parent.clean_viral_title(response_data.get('title', '').replace('"', '').strip())
            hook_script = response_data.get('hook', '').replace('"', '').strip()

            # Clean up response
            if len(summary) > 150:
                summary = summary[:150] + "..."
            
            return {"title": summary, "hook_script": hook_script}
        except Exception as e:
            error_str = str(e).lower()
            if ("429" in error_str or "quota" in error_str or "limit" in error_str) and retry_count < len(self.parent.gemini_keys):
                print(f"\n  [RATE LIMIT] Rotating API Key (Retry {retry_count + 1})...")
                if self.parent.rotate_gemini_api_key():
                    return self.parent.analyze_with_gemini(text, start_time, end_time, retry_count + 1)
            
            print(f"Gemini API error: {e}")
            return {"title": text, "hook_script": ""}
    
    def auto_shorten_title(self, long_title):
        """Shorten long titles (no external API)."""
        if not long_title or len(long_title) <= 75:
            return long_title or ""
        return long_title[:75]

    def _contains_english(self, text):
        """Return True if text contains common English words (judul/hook harus Indonesia)."""
        if not text:
            return False
        t = text.lower()
        english_words = [
            "storming", "outrage", "field", "global", "game changer", "face recognition",
            "protest", "stands", "anguish", "sanctions", "unleashed", "recognition", "solution",
            "problem", "the", "and", "for", "with", "this", "that", "from", "have", "has",
            "what", "when", "where", "why", "how", "best", "top", "new", "first", "big",
            "real", "true", "full", "live", "breaking", "exclusive", "versus", "vs",
            "star", "stars", "world", "moment", "moments", "story", "stories",
        ]
        words = re.findall(r"[a-z]+", t)
        if not words:
            return False
        for w in english_words:
            if w in t or (len(w) > 4 and w in " ".join(words)):
                return True
        return False

    def generate_clickbait_title(self, segment_text, existing_titles=None, max_attempts=5, strict_content=False, _retry=0):
        """
        Selalu minta OpenAI buat judul clickbait dari percakapan/transkrip.
        Judul harus dari OpenAI; jika respons Inggris, minta terjemah ke Indonesia.
        Fallback hanya jika API gagal: potongan transkrip (bukan teks generik).
        strict_content: judul harus STRICT mencerminkan isi, 8–12 kata, tidak berlebihan.
        """
        existing_titles = existing_titles or []
        if not segment_text:
            return _title_from_transcript(segment_text)
        if self._use_gemini_for_ai():
            print("[GEMINI] Generating clickbait title")
            return self._generate_title_gemini(segment_text, existing_titles, strict_content)
        if not self._openai_client or not self.openai_available:
            print("[OPENAI] API key not found, skipping clickbait title")
            return _title_from_transcript(segment_text)
        print("[OPENAI] Generating clickbait title")

        if strict_content:
            prompt = """Kamu ahli YouTube Shorts untuk penonton Indonesia.
Dari percakapan/transkrip berikut, buat SATU judul yang menarik.

ATURAN PENTING:
* Judul HARUS STRICT mencerminkan isi klip. Jangan melebih-lebihkan atau mengarang informasi yang tidak ada di transkrip.
* BAHASA INDONESIA saja
* 8–12 kata
* Awali dengan 1 emoji
* Jangan pakai: Climax, YT Shorts

Percakapan:
{segment_text}

Jawab HANYA judulnya.""".format(segment_text=(segment_text[:2000] if segment_text else ""))
        else:
            prompt = """Kamu ahli YouTube Shorts untuk penonton Indonesia.
Dari percakapan/transkrip berikut, buat SATU judul clickbait yang bikin penasaran.

Aturan:
* BAHASA INDONESIA saja, maksimal 60 karakter
* Awali dengan 1 emoji
* Jangan pakai: Climax, YT Shorts
* Judul harus mencerminkan isi klip, jangan melebih-lebihkan

Percakapan:
{segment_text}

Jawab HANYA judulnya.""".format(segment_text=(segment_text[:2000] if segment_text else ""))

        emoji_pattern = re.compile(
            "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]+",
            flags=re.UNICODE,
        )
        forbidden_words = ["climax", "yt shorts", "yt short"]
        def _reject_title(t):
            if not t or len(t) < 8:
                return True
            if len(t) > 80:
                return True
            wc = len(t.split())
            if strict_content and (wc < 7 or wc > 14):
                return True
            if not emoji_pattern.search(t):
                return True
            if any(fw in (t or "").lower() for fw in forbidden_words):
                return True
            if self._contains_english(t):
                return True
            if t in existing_titles:
                return True
            return False

        last_raw = ""
        for attempt in range(max_attempts):
            try:
                response = self._openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.8,
                    max_tokens=80,
                )
                title = (response.choices[0].message.content or "").strip().strip('"').strip("'")
                if not title:
                    continue
                title = self.clean_viral_title(title)
                last_raw = title
                if _reject_title(title):
                    continue
                return title[:60]
            except Exception as e:
                if self._maybe_rotate_openai_on_error(e) and _retry < 1:
                    return self.generate_clickbait_title(segment_text, existing_titles, max_attempts, strict_content, _retry=_retry + 1)
                if attempt < max_attempts - 1:
                    continue
                print(f"[OPENAI] Clickbait title failed: {e}")
                return _title_from_transcript(segment_text)
        if last_raw and self._contains_english(last_raw):
            try:
                r = self._openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[{"role": "user", "content": "Ubah judul ini ke Bahasa Indonesia saja, tetap clickbait, max 60 karakter, awali emoji. Jawab hanya judul.\n\n" + last_raw}],
                    temperature=0.3,
                    max_tokens=80,
                )
                tr = (r.choices[0].message.content or "").strip().strip('"').strip("'")
                if tr and len(tr) >= 8:
                    return tr[:60]
            except Exception:
                pass
        if last_raw and not self._contains_english(last_raw):
            return last_raw[:60]
        try:
            r = self._openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": "Dari percakapan ini buat 1 judul clickbait YouTube Shorts. Bahasa Indonesia, max 60 karakter, 1 emoji di depan. Jawab hanya judul.\n\n" + (segment_text[:1500] or "")}],
                temperature=0.7,
                max_tokens=80,
            )
            t = (r.choices[0].message.content or "").strip().strip('"').strip("'")
            if t and len(t) >= 8:
                return t[:60]
        except Exception:
            pass
        return _title_from_transcript(segment_text)

    def _time_str_to_sec(self, t_str):
        """Convert MM:SS or HH:MM:SS to seconds."""
        t_str = (t_str or "").strip()
        parts = t_str.replace(",", ".").split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(float(parts[1]))
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(float(parts[2]))
        try:
            return int(float(t_str))
        except ValueError:
            return 0

    def detect_viral_segments_with_gemini(self, transcript):
        """
        Use Gemini to detect viral moments from full transcript. Same output format as OpenAI.
        """
        if not (transcript or "").strip() or not getattr(self.parent, "gemini_client", None):
            return []
        print("[GEMINI] Detecting viral segments")
        prompt = """You are an expert video highlight editor. Find GOLDEN MOMENTS—exciting moments, NOT setup/intro.

PRIORITIZE: Conflict, controversy, debate, surprising events, strong emotions, key incidents, hot takes, dramatic reveals ("ternyata", "justru", "masalahnya").
AVOID: Topic introductions, setup sentences, "Jadi seperti biasa", "Kita akan bahas", "Pertama kita bahas".

OUTPUT: One line per clip:
START_TIME - END_TIME | VIRAL_SCORE | HOOK
Use transcript timestamps. VIRAL_SCORE 0-100. HOOK max 12 words. Min 10s, max 60s per clip. Up to 15 clips.

Transcript:
"""
        prompt += (transcript[:80000] if transcript else "").strip()
        try:
            response = self.parent.gemini_client.models.generate_content(
                model="gemini-2.0-flash", contents=prompt
            )
            result = (response.text or "").strip()
            segments = self._parse_viral_segments_response(result)
            return segments[:15]
        except Exception as e:
            print(f"[GEMINI] Detect viral segments failed: {e}")
            return []

    def detect_viral_segments_with_openai(self, transcript, _retry=0):
        """
        Use selected AI (OpenAI or Gemini) to detect viral moments from full transcript.
        Returns list of dicts: [{"start": sec, "end": sec, "viral_score": 0-100, "hook": str}, ...]
        """
        if not (transcript or "").strip():
            return []
        if self._use_gemini_for_ai():
            return self.detect_viral_segments_with_gemini(transcript)
        if not self._openai_client or not self.openai_available:
            print("[OPENAI] API key not found, skipping viral segment detection")
            return []
        print("[OPENAI] Detecting viral segments")
        prompt = """You are an expert video highlight editor. Your goal is to find GOLDEN MOMENTS—the actual exciting moments where something interesting happens, NOT the setup or introduction.

PRIORITIZE (Golden Moments):
* Conflict, controversy, or debate
* Surprising events or revelations
* Strong emotional reactions
* Key incidents: goals, fouls, referee decisions, fights, arguments
* Strong opinions or hot takes
* Dramatic reveals ("ternyata", "justru", "masalahnya")

AVOID (Do NOT select these):
* Topic introductions ("Jadi seperti biasa...", "Kita akan bahas...")
* Setup sentences or general explanations
* Long background context before the actual moment
* "Pertama kita bahas", "Topik kita hari ini", "Sebelum kita bahas"
* Segments that only introduce what will be discussed

HIGHLIGHT SIGNALS (prefer segments containing or starting with):
- "tapi", "namun", "ternyata", "justru" -> often introduces the real moment
- "masalahnya", "keputusan wasit", "gol", "kontroversi", "aneh", "tidak masuk akal"
- "yang menarik" -> usually precedes the actual interesting point

INTRO PHRASES (avoid as clip start—these are discussion setup):
- "jadi", "seperti biasa", "kita akan bahas", "sekarang kita bahas"
- "pertama kita bahas", "topik kita hari ini", "sebelum kita bahas"

RULE: The clip should feel like the viewer jumps DIRECTLY into the exciting moment. If a segment starts with introduction and the real moment appears later, prefer selecting the segment that contains the real moment, or a later timestamp where the interesting part begins.

CLIP LENGTH:
Minimum: 10 seconds. Maximum: 60 seconds.

OUTPUT FORMAT:
One line per clip:
START_TIME - END_TIME | VIRAL_SCORE | HOOK

Use timestamps from the transcript. VIRAL_SCORE 0-100 (higher = more viral potential). HOOK: max 12 words, same language as transcript.

Return up to 15 clips.

Transcript:
"""
        prompt += (transcript[:80000] if transcript else "").strip()
        try:
            response = self._openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.4,
                max_tokens=8000,
            )
            result = (response.choices[0].message.content or "").strip()
        except Exception as e:
            if self._maybe_rotate_openai_on_error(e) and _retry < 1:
                return self.detect_viral_segments_with_openai(transcript, _retry=_retry + 1)
            print(f"[OPENAI] Detect viral segments failed: {e}")
            return []
        segments = self._parse_viral_segments_response(result)
        return segments[:15]

    def _parse_viral_segments_response(self, result):
        """Parse AI response: either block format (with HOOK/TITLE/CAPTION/KEYWORDS/HASHTAGS) or legacy one-line format."""
        time_range_re = re.compile(
            r"(\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\s*-\s*(\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)"
        )
        legacy_re = re.compile(
            r"(\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\s*-\s*(\d{1,2}:\d{2}(?::\d{2})?(?:\.\d+)?)\s*\|\s*(\d+)\s*\|\s*(.*)",
            re.IGNORECASE,
        )
        segments = []
        lines = [ln.strip() for ln in result.split("\n")]

        # Try legacy one-line format first (any line matching "START - END | SCORE | HOOK")
        for line in lines:
            if not line or line.startswith("#"):
                continue
            m = legacy_re.search(line)
            if m:
                start_sec = self._time_str_to_sec(m.group(1))
                end_sec = self._time_str_to_sec(m.group(2))
                score = min(100, max(0, int(m.group(3))))
                hook = (m.group(4) or "").strip().strip('"').strip("'")
                if end_sec > start_sec and (end_sec - start_sec) >= 10:
                    segments.append({
                        "start": float(start_sec), "end": float(end_sec),
                        "viral_score": score, "hook": hook,
                        "title": "", "caption": "", "keywords": [], "hashtags": [],
                    })
        if segments:
            return segments

        # Block format: find lines that start a new segment (time range)
        i = 0
        while i < len(lines):
            line = lines[i]
            m = time_range_re.search(line)
            if not m:
                i += 1
                continue
            start_sec = self._time_str_to_sec(m.group(1))
            end_sec = self._time_str_to_sec(m.group(2))
            if end_sec <= start_sec or (end_sec - start_sec) < 10:
                i += 1
                continue
            score = 0
            hook = title = caption = ""
            keywords = []
            hashtags = []
            i += 1
            while i < len(lines):
                cur = lines[i]
                if time_range_re.search(cur):
                    break
                # Viral score: accept "85", "85 (0-100)", "VIRAL_SCORE: 85", "Score: 85", or line with single number 0-100
                try:
                    if re.match(r"^\d+\s*$", cur) or re.match(r"^\d+\s*\(0-100\)", cur, re.I):
                        score = min(100, max(0, int(re.sub(r"\D", "", cur))))
                    elif re.search(r"(?i)(?:viral|score)", cur):
                        num_match = re.search(r"\b(\d{1,2}|100)\b", cur)
                        if num_match:
                            score = min(100, max(0, int(num_match.group(1))))
                    elif re.match(r"^\s*(\d{1,2}|100)\s*$", cur) and ":" not in cur:
                        score = min(100, max(0, int(cur.strip())))
                except (ValueError, TypeError):
                    pass
                if cur.upper().startswith("HOOK:"):
                    hook = cur[5:].strip().strip('"').strip("'")
                elif cur.upper().startswith("TITLE:"):
                    title = cur[6:].strip().strip('"').strip("'")
                elif cur.upper().startswith("CAPTION:"):
                    caption = cur[8:].strip().strip('"').strip("'")
                elif cur.upper().startswith("KEYWORDS:"):
                    raw = cur[9:].strip()
                    keywords = [k.strip() for k in re.split(r"[,;]+", raw) if k.strip()][:8]
                    if not keywords:
                        keywords = [k.strip() for k in raw.split() if k.strip() and not k.startswith("#")][:8]
                elif cur.upper().startswith("HASHTAGS:"):
                    raw = cur[9:].strip()
                    hashtags = [h.strip().lstrip("#") for h in re.split(r"[,;\s]+", raw) if h.strip()][:8]
                i += 1
            segments.append({
                "start": float(start_sec), "end": float(end_sec),
                "viral_score": score, "hook": hook,
                "title": title, "caption": caption,
                "keywords": keywords, "hashtags": hashtags,
            })
        return segments

    def _build_segment_prompt(self, segments):
        """Build prompt text listing segments for GPT-4o ranking (format: 1. MM:SS - MM:SS)."""
        lines = []
        for i, seg in enumerate(segments):
            start = seg.get("start", seg.get("start_str", 0))
            end = seg.get("end", seg.get("end_str", 0))
            if isinstance(start, (int, float)):
                start = f"{int(start // 60):02d}:{int(start % 60):02d}"
            if isinstance(end, (int, float)):
                end = f"{int(end // 60):02d}:{int(end % 60):02d}"
            text = (seg.get("text") or seg.get("segment_text") or seg.get("full_topic") or "")[:300]
            lines.append(f"{i + 1}. {start} - {end}\n   {text}")
        return "\n".join(lines) if lines else "(no segments)"

    def _parse_ranked_segments(self, result_text, segments):
        """Parse GPT-4o ranking response into reordered segment list. Falls back to original order."""
        if not result_text or not segments:
            return segments
        order = []
        seen = set()
        for line in result_text.strip().split("\n"):
            line = line.strip()
            for part in line.replace(",", " ").split():
                try:
                    idx = int(part)
                    if 0 <= idx < len(segments) and idx not in seen:
                        order.append(idx)
                        seen.add(idx)
                except ValueError:
                    continue
        for i in range(len(segments)):
            if i not in seen:
                order.append(i)
        return [segments[i] for i in order] if order else segments

    def rank_segments_with_gemini(self, segments):
        """Use Gemini to rank segments by virality. Returns segments in ranked order."""
        if not segments or not getattr(self.parent, "gemini_client", None):
            return segments
        print("[GEMINI] Ranking segments")
        try:
            prompt_body = self._build_segment_prompt(segments)
            prompt = f"""Segments:

{prompt_body}

You are an expert short-form video editor. Select the most viral moments (shocking statements, emotional reactions, controversy, surprising stories). Return the top 10 clips ranked by virality. Reply with segment numbers only, one per line (e.g. 3, 1, 0, 5, 2, ...). Use the segment index (1-based) from the list above."""
            response = self.parent.gemini_client.models.generate_content(
                model="gemini-2.0-flash", contents=prompt
            )
            result = (response.text or "").strip()
            order, seen = [], set()
            for line in result.strip().split("\n"):
                for part in line.replace(",", " ").split():
                    try:
                        num = int(part)
                        idx = num - 1
                        if 0 <= idx < len(segments) and idx not in seen:
                            order.append(idx)
                            seen.add(idx)
                    except ValueError:
                        continue
            for i in range(len(segments)):
                if i not in seen:
                    order.append(i)
            return [segments[i] for i in order] if order else segments
        except Exception as e:
            print(f"[GEMINI] Ranking failed: {e}, using original order")
            return segments

    def rank_segments_with_openai(self, segments, _retry=0):
        """
        Use selected AI (OpenAI or Gemini) to rank the most viral segments.
        Returns segments in ranked order.
        """
        if not segments:
            return segments
        if self._use_gemini_for_ai():
            return self.rank_segments_with_gemini(segments)
        if not self._openai_client or not self.openai_available:
            print("[OPENAI] API key not found, skipping ranking")
            return segments
        print("[OPENAI] Ranking segments")
        try:
            prompt_body = self._build_segment_prompt(segments)
            user_content = """Segments:

""" + prompt_body + """

You are an expert short-form video editor.
Select the most viral moments from this list.

Criteria:
* shocking statements
* emotional reactions
* controversy
* surprising stories

Return the top 10 clips ranked by virality. Reply with segment numbers only, one per line (e.g. 3, 1, 0, 5, 2, ...). Use the segment index (1-based) from the list above."""
            response = self._openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": "You are an expert short-form video editor. Select the most viral moments. Reply only with segment numbers in ranked order (best first), one number per line."},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.3,
                max_tokens=500,
            )
            result = (response.choices[0].message.content or "").strip()
            # Parse 1-based numbers from response; convert to 0-based indices
            order = []
            seen = set()
            for line in result.strip().split("\n"):
                for part in line.replace(",", " ").split():
                    try:
                        num = int(part)
                        idx = num - 1  # 1-based in prompt
                        if 0 <= idx < len(segments) and idx not in seen:
                            order.append(idx)
                            seen.add(idx)
                    except ValueError:
                        continue
            for i in range(len(segments)):
                if i not in seen:
                    order.append(i)
            return [segments[i] for i in order] if order else segments
        except Exception as e:
            if self._maybe_rotate_openai_on_error(e) and _retry < 1:
                return self.rank_segments_with_openai(segments, _retry=_retry + 1)
            print(f"[OPENAI] Ranking failed: {e}, using original order")
            return segments

    def rank_and_score_segments_openai(self, candidates):
        """
        Use OpenAI GPT-4o to assign viral scores to candidate segments.
        candidates: list of dicts with at least 'start', 'end', 'text' or transcript snippet.
        Returns list of dicts with added: shock_score, emotion_score, humor_score, story_score,
        controversy_score, curiosity_score, viral_score. Returns all segments; caller ranks and selects top N.
        """
        if not self._openai_client or not self.openai_available or not candidates:
            return candidates
        print("[OPENAI] Ranking segments")

        viral_weights = {
            "shock_score": 0.25,
            "emotion_score": 0.20,
            "humor_score": 0.15,
            "story_score": 0.20,
            "controversy_score": 0.10,
            "curiosity_score": 0.10,
        }

        prompt = """You are a viral content analyst. For each segment, assign integer scores 0-100 for:
- shock_score: how surprising/shocking
- emotion_score: emotional impact
- humor_score: how funny/entertaining
- story_score: narrative strength
- controversy_score: debate/controversy potential
- curiosity_score: curiosity hook

Return a JSON array of objects, one per segment, in the same order. Each object must have exactly:
{"shock_score": N, "emotion_score": N, "humor_score": N, "story_score": N, "controversy_score": N, "curiosity_score": N}
No other text. Only the JSON array."""

        texts = []
        for c in candidates:
            t = c.get("text") or c.get("segment_text") or c.get("full_topic") or ""
            if isinstance(t, str) and len(t) > 500:
                t = t[:500] + "..."
            texts.append(t or "(no text)")

        try:
            response = self._openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "user", "content": prompt + "\n\nSegments (one per line, same order as output):\n" + "\n---\n".join(texts)}
                ],
                temperature=0.3,
                max_tokens=2000,
            )
            raw = (response.choices[0].message.content or "").strip()
            if "```" in raw:
                raw = raw.split("```")[1].replace("```", "").strip()
            if raw.startswith("["):
                arr = json.loads(raw)
            else:
                return candidates
        except Exception as e:
            print(f"[OPENAI] Scoring failed: {e}, using original candidates")
            return candidates

        scored = []
        for i, c in enumerate(candidates):
            copy = dict(c)
            if i < len(arr) and isinstance(arr[i], dict):
                s = arr[i]
                copy["shock_score"] = min(100, max(0, int(s.get("shock_score", 0))))
                copy["emotion_score"] = min(100, max(0, int(s.get("emotion_score", 0))))
                copy["humor_score"] = min(100, max(0, int(s.get("humor_score", 0))))
                copy["story_score"] = min(100, max(0, int(s.get("story_score", 0))))
                copy["controversy_score"] = min(100, max(0, int(s.get("controversy_score", 0))))
                copy["curiosity_score"] = min(100, max(0, int(s.get("curiosity_score", 0))))
                viral = (
                    copy["shock_score"] * 0.25
                    + copy["emotion_score"] * 0.20
                    + copy["humor_score"] * 0.15
                    + copy["story_score"] * 0.20
                    + copy["controversy_score"] * 0.10
                    + copy["curiosity_score"] * 0.10
                )
                copy["viral_score"] = round(viral)
                scored.append(copy)
            else:
                copy["viral_score"] = copy.get("virality_score", 0)
                scored.append(copy)
        return scored

    def refine_hook_with_openai(self, hook_text):
        """
        Refine hook text using OpenAI GPT-4o. Safe fallback: returns original if no client or on failure.
        """
        if not self._openai_client or not self.openai_available:
            print("[OPENAI] API key not found, skipping hook refinement")
            return (hook_text or "").strip()
        if not (hook_text or "").strip():
            return ""
        print("[OPENAI] Refining hook text")
        system_msg = (
            "Kamu editor thumbnail YouTube Shorts/TikTok. Buat hook yang catchy, bikin penasaran, dan viral. "
            "HANYA Bahasa Indonesia, tanpa kata Inggris. Jangan kalimat deskriptif biasa—buat seperti headline yang bikin orang ingin klik. "
            "Contoh gaya: pakai pertanyaan, angka, atau pernyataan tegas; hindari kalimat datar seperti 'X perlu Y' tanpa daya tarik."
        )
        user_msg = (
            "Ubah hook ini jadi lebih engaging untuk thumbnail (maks 12 kata). Jawab HANYA hook baru, tanpa penjelasan.\n\n"
            "Hook sekarang: " + (hook_text or "").strip() + "\n\nHook baru:"
        )
        try:
            response = self._openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {"role": "system", "content": system_msg},
                    {"role": "user", "content": user_msg},
                ],
                temperature=0.7,
                max_tokens=80,
            )
            out = (response.choices[0].message.content or "").strip().strip('"').strip("'")
            if out and self._contains_english(out):
                out = ""
            if out:
                return out
            raw = (hook_text or "").strip()
            if raw and self._contains_english(raw):
                try:
                    r = self._openai_client.chat.completions.create(
                        model="gpt-4o",
                        messages=[{"role": "user", "content": "Terjemahkan ke Bahasa Indonesia saja, tetap menarik, max 12 kata. Jawab hanya terjemahannya.\n\n" + raw}],
                        temperature=0.3,
                        max_tokens=60,
                    )
                    tr = (r.choices[0].message.content or "").strip().strip('"').strip("'")
                    if tr and not self._contains_english(tr):
                        return tr
                except Exception:
                    pass
            return raw
        except Exception as e:
            print(f"[OPENAI] Hook refinement failed: {e}")
            return (hook_text or "").strip()

    def refine_hook_openai(self, hook_text):
        """
        Use OpenAI GPT-4o to refine hook for first 3 seconds of a YouTube Shorts video.
        Returns improved hook (max 12 words, attention-grabbing, curiosity-driven).
        Delegates to refine_hook_with_openai with safe fallback.
        """
        if not (hook_text or "").strip():
            return (hook_text or "").strip()
        return self.refine_hook_with_openai(hook_text)

    def score_hook_openai(self, hook_text):
        """
        Score hook quality: curiosity_score, emotion_score, shock_score, clarity_score (0-100 each).
        hook_score = curiosity*0.35 + emotion*0.25 + shock*0.25 + clarity*0.15.
        Returns (hook_score, scores_dict) or (0, {}) on failure.
        """
        if not self._openai_client or not self.openai_available or not (hook_text or "").strip():
            return 0, {}

        prompt = """You are a viral hook analyst. Score this hook for a YouTube Shorts opening (0-100 each):
- curiosity_score: how much it makes viewers curious
- emotion_score: emotional pull
- shock_score: surprise/attention grab
- clarity_score: clear and easy to understand

Return ONLY a JSON object with exactly: {"curiosity_score": N, "emotion_score": N, "shock_score": N, "clarity_score": N}
Hook: """ + (hook_text or "").strip()[:300]

        try:
            response = self._openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=150,
            )
            raw = (response.choices[0].message.content or "").strip()
            if "```" in raw:
                raw = raw.split("```")[1].replace("```", "").strip()
            obj = json.loads(raw)
            c = min(100, max(0, int(obj.get("curiosity_score", 0))))
            e = min(100, max(0, int(obj.get("emotion_score", 0))))
            s = min(100, max(0, int(obj.get("shock_score", 0))))
            cl = min(100, max(0, int(obj.get("clarity_score", 0))))
            hook_score = round(c * 0.35 + e * 0.25 + s * 0.25 + cl * 0.15)
            return hook_score, {"curiosity_score": c, "emotion_score": e, "shock_score": s, "clarity_score": cl}
        except Exception:
            return 0, {}

    def refine_and_score_hook_openai(self, hook_text, max_attempts=2, _retry=0):
        """
        Refine hook with selected AI (OpenAI or Gemini), then score it.
        Returns (refined_hook_text, hook_score).
        """
        if not (hook_text or "").strip():
            return "", 0
        if self._use_gemini_for_ai():
            return self._refine_hook_gemini(hook_text)
        best_hook = (hook_text or "").strip()
        best_score = 0
        for _ in range(max_attempts):
            try:
                refined = self.refine_hook_openai(best_hook)
            except Exception as e:
                if self._maybe_rotate_openai_on_error(e) and _retry < 1:
                    return self.refine_and_score_hook_openai(hook_text, max_attempts=max_attempts, _retry=_retry + 1)
                refined = best_hook
            if not refined:
                refined = best_hook
            score, _ = self.score_hook_openai(refined)
            if score >= 50:
                return refined, score
            if score > best_score:
                best_score = score
                best_hook = refined
        return best_hook, best_score

    def apply_hook_trigger_boost(self, hook_text, hook_score):
        """
        Boost hook_score if hook contains curiosity/emotional trigger words.
        Stronger hooks get +12 (capped at 100).
        """
        if hook_text is None or hook_score is None:
            return hook_score or 0
        t = (hook_text or "").strip().lower()
        if not t:
            return hook_score
        triggers = [
            "kenapa", "ternyata", "ini dia", "kamu gak bakal percaya",
            "gila", "serius", "tunggu dulu"
        ]
        for w in triggers:
            if w in t:
                return min(100, int(hook_score) + 12)
        return int(hook_score)

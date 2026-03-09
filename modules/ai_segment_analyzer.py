"""
AI Segment Analyzer Module
Handles AI-powered viral segment detection and title generation
"""

import os
import re
import json
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor

from modules.smart_segmentation import find_sentence_boundaries

# Optional: embedding + emotion models (lazy-loaded, skip if unavailable)
_EMBEDDING_MODEL = None
_EMOTION_MODEL = None
_EMOTION_TOKENIZER = None



class AISegmentAnalyzer:
    """Manages AI-powered segment analysis and title generation"""
    
    HOOK_MAX_WORDS = 12
    HOOK_FILLER_REMOVE = ["ee", "eh", "jadi", "ya", "gitu kan"]
    HOOK_STRONG_VERBS = ["akan", "ternyata", "justru", "bikin", "masalahnya", "bisa", "harus", "memang"]
    HOOK_SURPRISE = ["ternyata", "justru", "masalahnya", "anehnya", "padahal"]

    def __init__(self, parent):
        """
        Initialize AI Segment Analyzer
        
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

    # [MOMENT-FIRST] Window scanning for short viral moments
    WINDOW_SIZE_SEC = 18
    WINDOW_OVERLAP_SEC = 4
    TOP_CANDIDATES_FOR_OPENAI = 250  # 120–250 candidate moments per hour
    TARGET_CLIPS_PER_HOUR = 20
    CLIP_MIN_DURATION_SEC = 10
    CLIP_MAX_DURATION_SEC = 60

    # [OPUS-STYLE] Multi-clip pipeline: sliding window for 10-30 clips per video
    OPUS_WINDOW_SIZE = 25
    OPUS_STEP_SIZE = 10
    OPUS_CLIP_MIN = 10
    OPUS_CLIP_MAX = 60
    OPUS_TOP_CLIPS = 20
    OPUS_OVERLAP_THRESHOLD = 0.60
    HOOK_PRE_ROLL_SEC = 2  # Start clip 2s before hook moment
    HOOK_POST_ROLL_MIN = 30
    HOOK_POST_ROLL_MAX = 45
    # Natural end behavior (speech boundaries)
    NATURAL_PAUSE_END_SEC = 0.6
    TOPIC_SHIFT_PAUSE_SEC = 1.0
    ABS_MIN_CLIP_SEC = 8
    ABS_MAX_CLIP_SEC = 60

    # [HOOK DETECTION] Phrases that mark viral statement moments (strong opening in first 3s)
    HOOK_MOMENT_PATTERNS = [
        "yang paling penting", "masalahnya adalah", "kenapa", "yang menarik adalah",
        "yang mengejutkan", "faktanya", "menurut saya", "masalahnya", "yang menarik",
        "bukan mustahil", "justru", "ternyata", "anehnya", "padahal", "saya pikir",
        "ini masalah", "yang bikin", "yang jadi masalah", "ini yang bikin", "ini yang menarik",
    ]

    # [INTRO/FILLER] Skip these at clip start — move to first meaningful sentence
    FILLER_PHRASES = [
        "jadi", "nah", "seperti biasa", "kita bahas dulu", "sebelum kita bahas",
        "topik kita hari ini", "oke kita bahas", "kalau kita lihat",
    ]

    # [ARGUMENT] Debate/disagreement — highly viral in podcasts
    ARGUMENT_PATTERNS = [
        "menurut saya", "tidak setuju", "sebenarnya", "masalahnya", "argumen",
        "tapi", "namun", "justru", "saya tidak setuju", "sebaliknya", "padahal",
    ]

    # [STRONG STATEMENT] Opinion / prediction / controversy
    STRONG_STATEMENTS = [
        "prediksi", "menurut saya", "tidak masuk akal", "aneh", "kontroversi",
        "masalahnya", "yang menarik",
    ]

    # [PRE-FILTER] Viral category keywords - rule-based detection before AI
    VIRAL_CATEGORY_KEYWORDS = {
        "controversy": [
            "kontroversi", "aneh", "tidak masuk akal", "keputusan wasit", "dipertanyakan",
            "debat", "argumen", "keputusan", "protes wasit", "kesalahan wasit",
        ],
        "funny_relatable": [
            "lucu", "ngakak", "kocak", "pernah ngalamin", "gak masuk akal",
            "bikin ketawa", "kelucuan", "lebay", "lebay banget",
        ],
        "emotional": [
            "sedih", "terharu", "menangis", "menyentuh", "haru",
            "pilu", "emosi", "haru biru", "air mata",
        ],
        "surprising": [
            "ternyata", "tidak disangka", "baru diketahui", "tahu gak",
            "fakta mengejutkan", "tak terduga", "luar biasa", "bikin kaget",
        ],
        "anger_injustice": [
            "marah", "kesal", "tidak adil", "protes", "kecewa",
            "zalim", "aniaya", "ketidakadilan", "bikin emosi",
        ],
        "inspirational": [
            "bangkit", "perjuangan", "jangan menyerah", "semangat",
            "pantang menyerah", "bangkit dari keterpurukan", "motivasi",
        ],
        "personal_story": [
            "saya pernah", "pengalaman saya", "waktu itu", "dulu saya",
            "cerita saya", "pengalamanku", "kejadian waktu",
        ],
        "secrets_hidden": [
            "rahasia", "fakta", "dibalik", "yang jarang diketahui",
            "tahu gak", "fakta tersembunyi", "rahasia besar",
        ],
    }
    # [EMOTION] Indonesian emotion indicators (PART 4)
    EMOTION_KEYWORDS = [
        "marah", "lucu", "heboh", "serius", "ketat", "krisis", "mengejutkan",
        "sedih", "terharu", "menangis", "menyentuh", "pilu", "emosi",
    ]

    # Dramatic connector words - often indicate important moments
    CONNECTOR_WORDS = [
        "tapi", "namun", "justru", "tiba tiba", "yang menarik",
        "masalahnya", "ternyata", "padahal", "sementara", "di satu sisi",
    ]
    # [MULTI-SIGNAL] Viral detection patterns (includes HOOK_MOMENT_PATTERNS)
    HOOK_PATTERNS = [
        " itu ", " itu.", " itu?", " itu!",
        "ini masalah besar", "ini yang bikin", "ini bikin",
        "itu masalah", "itu yang", "kan itu",
    ]
    HUMOR_MARKERS = ["[tertawa]", "(tertawa)", "haha", "hehe", "wkwk", "wkwkwk"]
    ARGUMENT_SIGNALS = ["tapi", "namun", "justru", "saya tidak setuju", "masalahnya", "sebaliknya", "padahal"]
    SURPRISE_PATTERNS = ["ternyata", "bahkan", "tidak disangka", "yang bikin kaget", "anehnya"]
    # Strong verbs / action markers (golden moment signal)
    STRONG_VERB_MARKERS = [
        "bikin", "mengubah", "menghancurkan", "mengagetkan", "menyelamatkan",
        "meledak", "bongkar", "buktinya", "terbukti", "kalah", "menang",
        "hancur", "viral", "trending",
    ]

    # Emotional/dramatic keywords - boost score for viral moment prioritization (post-AI)
    HIGHLIGHT_KEYWORDS = [
        "tapi", "namun", "justru", "ternyata", "yang menarik",
        "aneh", "kontroversi", "luar biasa", "masalahnya",
        "keputusan wasit", "gol", "tidak masuk akal",
        "keputusan", "debat", "argumen", "kejadian",
    ]
    # Intro phrases at segment start = discussion setup, penalize heavily (-6)
    INTRO_PHRASES = [
        "jadi", "nah", "seperti biasa", "kita bahas dulu", "sebelum kita bahas",
        "topik kita hari ini", "oke kita bahas", "kalau kita lihat",
        "kita akan bahas", "sekarang kita bahas", "pertama kita bahas",
    ]
    # Greeting patterns in first 120 chars = strong penalty (avoid "halo bang sehat?" etc.)
    GREETING_PATTERNS = [
        "halo", "hai", "apa kabar", "sehat", "selamat datang",
        "terima kasih sudah datang", "kita kedatangan", "host kita hari ini",
        "gimana kabarnya",
    ]
    # Filler words to remove before sending to AI (improve semantic clarity)
    FILLER_WORDS = [
        "ee", "uh", "um", "apa namanya", "gitu kan", "jadi ya", "eee",
    ]

    def _get_all_viral_keywords(self):
        """Lazy-build flat list of all viral keywords for fast lookup."""
        if not hasattr(self, '_cached_viral_keywords') or self._cached_viral_keywords is None:
            flat = []
            for kws in self.VIRAL_CATEGORY_KEYWORDS.values():
                flat.extend(kw.lower() for kw in kws)
            self._cached_viral_keywords = list(set(flat))
        return self._cached_viral_keywords

    def _clean_filler_words(self, text: str) -> str:
        """Remove filler words from text to improve AI semantic clarity."""
        if not text or not text.strip():
            return text or ""
        t = text
        for f in self.FILLER_WORDS:
            # Match filler as whole word/phrase (case-insensitive)
            pat = r'(?<!\w)' + re.escape(f) + r'(?!\w)'
            t = re.sub(pat, ' ', t, flags=re.IGNORECASE)
        t = re.sub(r'\s+', ' ', t).strip()
        return t

    def _is_filler_heavy(self, text: str) -> bool:
        """True if segment has mostly filler words or very low information density."""
        if not text or not text.strip():
            return True
        cleaned = self._clean_filler_words(text)
        if len(cleaned.strip()) < 25:
            return True
        words = cleaned.split()
        if len(words) < 4:
            return True
        return False

    def _title_segment_similarity(self, title: str, segment_text: str) -> float:
        """Cosine similarity between title and segment. Returns 0.0–1.0. Uses embeddings if available."""
        if not title or not segment_text:
            return 0.0
        model = self._get_embedding_model()
        if not model:
            return 0.5
        try:
            emb = model.encode([title[:512], segment_text[:512]], show_progress_bar=False)
            return float(self._cosine_similarity(emb[0], emb[1]))
        except Exception:
            return 0.5

    # --- Optional ML models (embedding + emotion) ---
    def _get_device(self):
        """Return 'cuda' if available, else 'cpu'."""
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"

    def _get_embedding_model(self):
        """Lazy-load sentence-transformers model. Returns None if unavailable."""
        global _EMBEDDING_MODEL
        if _EMBEDDING_MODEL is None:
            try:
                from sentence_transformers import SentenceTransformer
                device = self._get_device()
                _EMBEDDING_MODEL = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2", device=device)
            except Exception:
                _EMBEDDING_MODEL = False  # mark as attempted
        return _EMBEDDING_MODEL if _EMBEDDING_MODEL else None

    def _get_emotion_model(self):
        """Lazy-load emotion classifier. Returns (model, tokenizer) or (None, None) if unavailable."""
        global _EMOTION_MODEL, _EMOTION_TOKENIZER
        if _EMOTION_MODEL is None:
            try:
                from transformers import AutoModelForSequenceClassification, AutoTokenizer
                device = self._get_device()
                _EMOTION_TOKENIZER = AutoTokenizer.from_pretrained(
                    "cardiffnlp/twitter-roberta-base-emotion"
                )
                _EMOTION_MODEL = AutoModelForSequenceClassification.from_pretrained(
                    "cardiffnlp/twitter-roberta-base-emotion"
                )
                try:
                    import torch
                    _EMOTION_MODEL = _EMOTION_MODEL.to(device)
                except Exception:
                    pass
            except Exception:
                _EMOTION_MODEL = False
                _EMOTION_TOKENIZER = False
        m = _EMOTION_MODEL if _EMOTION_MODEL else None
        t = _EMOTION_TOKENIZER if _EMOTION_TOKENIZER else None
        return (m, t) if (m and t) else (None, None)

    def _compute_embeddings_batch(self, texts: list) -> list:
        """Compute embeddings for a batch of texts. Returns list of vectors or empty list on failure."""
        model = self._get_embedding_model()
        if not model:
            return []
        try:
            # Truncate long texts to avoid OOM (model max ~512 tokens)
            truncated = [t[:2000] if t else "" for t in texts]
            emb = model.encode(truncated, show_progress_bar=False)
            return list(emb)
        except Exception:
            return []

    def _cosine_similarity(self, a, b) -> float:
        """Cosine similarity between two vectors."""
        try:
            import numpy as np
            a, b = np.asarray(a), np.asarray(b)
            n = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9)
            return float(n)
        except Exception:
            return 0.0

    def _semantic_uniqueness_score(self, embeddings: list, idx: int) -> int:
        """
        Score +3 if segment has large semantic change vs neighbors (topic shift / important moment).
        """
        if not embeddings or idx < 0 or idx >= len(embeddings):
            return 0
        sim_prev = self._cosine_similarity(embeddings[idx], embeddings[idx - 1]) if idx > 0 else 1.0
        sim_next = self._cosine_similarity(embeddings[idx], embeddings[idx + 1]) if idx < len(embeddings) - 1 else 1.0
        # Low similarity = high semantic change
        min_sim = min(sim_prev, sim_next) if idx > 0 and idx < len(embeddings) - 1 else min(sim_prev, sim_next)
        if min_sim < 0.6:
            return 3
        return 0

    def _emotion_score_for_text(self, text: str) -> int:
        """Score +3 if emotional content detected (anger, joy, excitement, etc.)."""
        model, tokenizer = self._get_emotion_model()
        if not model or not tokenizer or not text:
            return 0
        try:
            import torch
            device = self._get_device()
            inputs = tokenizer(text[:512], return_tensors="pt", truncation=True, padding=True)
            inputs = {k: v.to(device) for k, v in inputs.items()}
            with torch.no_grad():
                out = model(**inputs)
            # Labels: anger, joy, optimism, sadness
            logits = out.logits[0]
            pred_idx = int(logits.argmax())
            # Any strong emotion (not neutral) = viral potential
            if pred_idx >= 0 and logits[pred_idx] > 0.5:
                return 3
        except Exception:
            pass
        return 0

    def _emotion_scores_batch(self, texts: list) -> list:
        """Batch emotion scores. Returns list of 0 or 3. Processes in chunks to avoid OOM."""
        model, tokenizer = self._get_emotion_model()
        if not model or not tokenizer:
            return [0] * len(texts)
        scores = [0] * len(texts)
        chunk = 16
        try:
            import torch
            device = self._get_device()
            for i in range(0, len(texts), chunk):
                batch = texts[i:i + chunk]
                truncated = [t[:512] if t else "" for t in batch]
                inputs = tokenizer(truncated, return_tensors="pt", truncation=True, padding=True)
                inputs = {k: v.to(device) for k, v in inputs.items()}
                with torch.no_grad():
                    out = model(**inputs)
                logits = out.logits
                preds = logits.argmax(dim=1)
                for j, idx in enumerate(range(i, min(i + chunk, len(texts)))):
                    if logits[j][preds[j]] > 0.5:
                        scores[idx] = 3
        except Exception:
            pass
        return scores

    def _compute_hook_score(self, text: str, first_3s_text: str = None) -> float:
        """Hook score 0-100: phrases in first 3s = strong hook (PART 3)."""
        if not text or not text.strip():
            return 0.0
        t = text.lower().strip()
        score = 0.0
        # Boost if hook phrases in first 3 seconds (~50 chars)
        opening = (first_3s_text or t)[:80].lower()
        strong_hooks = ["yang paling penting", "masalahnya adalah", "kenapa", "yang menarik adalah",
                        "yang mengejutkan", "faktanya", "ternyata", "justru", "menurut saya"]
        for p in strong_hooks:
            if p in opening:
                score += 25.0
                break
        # Rhetorical question / emotional emphasis
        if "?" in opening and len(opening) < 60:
            score += 15.0
        for p in self.HOOK_MOMENT_PATTERNS + self.HOOK_PATTERNS + self.HOOK_STRONG_VERBS:
            if p in t:
                score += 18.0
        for m in self.HUMOR_MARKERS:
            if m in t:
                score += 15.0
        for s in self.SURPRISE_PATTERNS:
            if s in t:
                score += 12.0
        for sent in re.split(r'[.!?]+', t):
            w = len(sent.split())
            if 5 <= w <= 12:
                score += 10.0
                break
        return min(100.0, score)

    def _compute_emotion_score(self, text: str) -> float:
        """Emotion score 0-100: emotional content detection (PART 4 - marah, lucu, heboh, etc)."""
        if not text or not text.strip():
            return 0.0
        t = text.lower()
        score = 0.0
        for kw in self.EMOTION_KEYWORDS:
            if kw in t:
                score += 18.0
        for kw in self.VIRAL_CATEGORY_KEYWORDS.get("emotional", []):
            if kw in t:
                score += 25.0
        for kw in self.VIRAL_CATEGORY_KEYWORDS.get("anger_injustice", []):
            if kw in t:
                score += 20.0
        for kw in self.VIRAL_CATEGORY_KEYWORDS.get("inspirational", []):
            if kw in t:
                score += 18.0
        emo_raw = self._emotion_score_for_text(text)
        score += emo_raw * 15.0
        return min(100.0, score)

    def _compute_argument_score(self, text: str) -> float:
        """Argument score 0-100: debate-style dialogue (PART 5 - menurut saya, tidak setuju, etc)."""
        if not text or not text.strip():
            return 0.0
        t = text.lower()
        score = 0.0
        for p in self.ARGUMENT_PATTERNS:
            if p in t:
                score += 22.0
        return min(100.0, score)

    def _compute_controversy_score(self, text: str) -> float:
        """Controversy score 0-100: debate, disagreement, strong opinions (distinct from argument)."""
        if not text or not text.strip():
            return 0.0
        t = text.lower()
        score = 0.0
        for s in self.STRONG_STATEMENTS:
            if s in t:
                score += 20.0
        for kw in self.VIRAL_CATEGORY_KEYWORDS.get("controversy", []):
            if kw in t:
                score += 22.0
        for kw in self.VIRAL_CATEGORY_KEYWORDS.get("surprising", []):
            if kw in t:
                score += 12.0
        return min(100.0, score)

    def _compute_information_density_score(self, text: str) -> float:
        """Information density 0-100: substantial content, not filler."""
        if not text or not text.strip():
            return 0.0
        cleaned = self._clean_filler_words(text)
        words = cleaned.split()
        if len(words) < 5:
            return 0.0
        unique = len(set(w.lower() for w in words))
        density = unique / max(1, len(words)) * 100
        if len(text) > 200:
            density = min(100, density + 15)
        if self._is_filler_heavy(text):
            density *= 0.3
        return min(100.0, max(0.0, density))

    def _compute_local_viral_score(self, window_text: str) -> int:
        """
        Multi-signal viral scoring (0–100).
        +3 hook, +3 humor, +3 emotion, +2 argument, +2 surprise, +2 strong statement, +1 long
        -8 greeting, -6 intro filler, -4 low info
        """
        if not window_text:
            return 0
        t = window_text.strip()
        t_lower = t.lower()
        score = 0

        # HOOK MOMENT: phrases that mark viral statements (+3)
        for p in self.HOOK_MOMENT_PATTERNS + self.HOOK_PATTERNS:
            if p in t_lower:
                score += 3
                break

        # HUMOR: laughter markers (+3)
        for m in self.HUMOR_MARKERS:
            if m in t_lower:
                score += 3
                break

        # ARGUMENT: debate/disagreement (+2)
        for s in self.ARGUMENT_PATTERNS:
            if s in t_lower:
                score += 2
                break

        # SURPRISE: reveal / unexpected (+2)
        for s in self.SURPRISE_PATTERNS:
            if s in t_lower:
                score += 2
                break

        # STRONG STATEMENT: opinion/prediction/controversy (+2 or +3)
        for s in self.STRONG_STATEMENTS:
            if s in t_lower:
                score += 3
                break

        # SHORT STRONG STATEMENT: 5–12 words = possible hook (+2)
        for sent in re.split(r'[.!?]+', t):
            w = len(sent.split())
            if 5 <= w <= 12:
                score += 2
                break

        # LONG EXPLANATION: substantial dialogue (+1)
        if len(t) > 200:
            score += 1

        # GREETING PENALTY (-8)
        first_120 = (t[:120] or "").lower()
        for g in self.GREETING_PATTERNS:
            if g in first_120:
                score -= 8
                break

        # INTRO FILLER PENALTY (-6)
        for phrase in self.FILLER_PHRASES:
            if t_lower.startswith(phrase) or t_lower.startswith(phrase + " "):
                score -= 6
                break

        # LOW INFORMATION: very short or generic (-4)
        if len(t.strip()) < 40 or t_lower.count(" ") < 3:
            score -= 4

        return max(0, min(100, score))

    def _passes_viral_filter(self, window_text: str) -> bool:
        """Minimal gate: only reject empty or very short windows. Used for backwards compat."""
        if not window_text:
            return False
        return len(window_text.strip()) >= 25

    def _score_window_for_ranking(self, window_text: str) -> int:
        """Score for ranking. Uses same logic as _compute_local_viral_score."""
        return self._compute_local_viral_score(window_text)

    def _adjust_viral_score_by_content(self, viral_score: int, seg_text: str) -> int:
        """
        Adjust viral_score based on segment content:
        - Boost if contains highlight keywords (actual moment)
        - Penalize if starts with intro phrases (topic setup)
        - Penalize if greeting in first 120 chars
        """
        if not seg_text or not seg_text.strip():
            return viral_score
        t = seg_text.strip().lower()
        score = viral_score
        # Boost: segment contains emotional/dramatic moment signals
        for kw in self.HIGHLIGHT_KEYWORDS:
            if kw in t:
                score = min(100, score + 12)
                break
        # Penalty: segment starts with intro/setup
        for phrase in self.INTRO_PHRASES:
            if t.startswith(phrase) or t.startswith(phrase + " "):
                score = max(0, score - 15)
                break
        # Penalty: greeting in first 120 chars
        first_120 = t[:120]
        for g in self.GREETING_PATTERNS:
            if g in first_120:
                score = max(0, score - 8)
                break
        return score

    def _time_str_to_sec(self, t_str):
        """Convert MM:SS or HH:MM:SS to seconds."""
        parts = t_str.strip().split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return 0

    def _slice_transcript_by_time(self, formatted_transcript, start_sec, end_sec):
        """Return transcript text for lines whose timestamp falls in [start_sec, end_sec]. Supports [MM:SS] or H:MM:SS."""
        if not formatted_transcript:
            return ""
        lines = []
        for line in formatted_transcript.split("\n"):
            line = line.strip()
            if not line:
                continue
            t_sec = None
            match = re.match(r"\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]", line)
            if match:
                g = match.groups()
                if len(g) == 3 and g[2] is not None:
                    t_sec = int(g[0]) * 3600 + int(g[1]) * 60 + int(g[2])
                else:
                    t_sec = int(g[0]) * 60 + int(g[1])
            else:
                match2 = re.match(r"^(\d+):(\d{2}):(\d{2})\s", line)
                if match2:
                    h, m, s = match2.groups()
                    t_sec = int(h) * 3600 + int(m) * 60 + int(s)
                else:
                    match3 = re.match(r"^(\d{1,2}):(\d{2})\s", line)
                    if match3:
                        m, s = match3.groups()
                        t_sec = int(m) * 60 + int(s)
            if t_sec is not None and start_sec <= t_sec <= end_sec:
                lines.append(line)
        return "\n".join(lines) if lines else ""

    def _get_timestamped_sentences(self):
        """
        [MOMENT-FIRST] Build list of (start_sec, end_sec, text) from sub_transcriptions.
        Each item is a cue/sentence with timestamps for hook detection.
        """
        cues = getattr(self.parent, "sub_transcriptions", None)
        if not cues or not isinstance(cues, dict):
            return []
        out = []
        for _, c in sorted(cues.items(), key=lambda x: x[1].get("start", 0)):
            if not isinstance(c, dict):
                continue
            s = self._normalize_cue_time(c.get("start") or c.get("s"))
            e = self._normalize_cue_time(c.get("end") or c.get("e")) if (c.get("end") or c.get("e")) is not None else s + 5.0
            t = (c.get("text") or c.get("t") or "").strip()
            if t:
                out.append((s, e, t))
        return out

    def _is_hook_sentence(self, text: str) -> bool:
        """True if sentence contains hook pattern or is strong short statement (5–12 words)."""
        if not text or len(text.strip()) < 10:
            return False
        t_lower = text.lower().strip()
        for p in self.HOOK_MOMENT_PATTERNS:
            if p in t_lower:
                return True
        words = text.split()
        if 5 <= len(words) <= 12:
            for s in self.STRONG_STATEMENTS + self.ARGUMENT_PATTERNS:
                if s in t_lower:
                    return True
        return False

    def _detect_hook_moments(self):
        """
        [MOMENT-FIRST] Detect hook moments from timestamped sentences.
        Returns list of (hook_start_sec, hook_end_sec, text, base_score).
        """
        sentences = self._get_timestamped_sentences()
        moments = []
        for start_sec, end_sec, text in sentences:
            if not self._is_hook_sentence(text):
                continue
            score = self._compute_local_viral_score(text)
            moments.append((start_sec, end_sec, text, score))
        return moments

    def _detect_golden_moments(self, cues, *, max_moments: int = 24, min_separation_sec: float = 10.0) -> list[dict]:
        """
        [GOLDEN MOMENT] Detect timestamps where multiple strong signals co-occur.
        Returns list of dicts: {t, score, text, signals}.

        Signals & weights (requested):
        - hook phrase: +4
        - surprise phrase: +4
        - argument marker: +3
        - emotional keyword: +3
        - humor marker: +2
        - strong verb: +2
        """
        sentences = self._get_timestamped_sentences()
        if not sentences:
            return []

        def score_text(text: str) -> tuple[float, list[str]]:
            t = (text or "").lower()
            if not t.strip():
                return 0.0, []
            s = 0.0
            sig = []
            # hook phrase (existing hook patterns)
            if any(p in t for p in (self.HOOK_MOMENT_PATTERNS or [])):
                s += 4
                sig.append("hook")
            # surprise
            if any(p in t for p in (self.SURPRISE_PATTERNS or [])):
                s += 4
                sig.append("surprise")
            # argument
            if any(p in t for p in (self.ARGUMENT_SIGNALS or [])):
                s += 3
                sig.append("argument")
            # emotion
            if any(p in t for p in (self.EMOTION_KEYWORDS or [])):
                s += 3
                sig.append("emotion")
            # humor
            if any(p in t for p in (self.HUMOR_MARKERS or [])):
                s += 2
                sig.append("humor")
            # strong verbs
            if any(p in t for p in (self.STRONG_VERB_MARKERS or [])):
                s += 2
                sig.append("verb")
            return s, sig

        raw = []
        for start_sec, end_sec, text in sentences:
            base, sig = score_text(text)
            if base <= 0:
                continue
            # small boosters for dramatic connectors + highlight keywords
            tl = (text or "").lower()
            if any(w in tl for w in (self.CONNECTOR_WORDS or [])):
                base += 1.5
            if any(w in tl for w in (self.HIGHLIGHT_KEYWORDS or [])):
                base += 1.0
            # penalize greetings / pure intro lines
            if any(g in tl[:140] for g in (self.GREETING_PATTERNS or [])):
                base -= 4.0
            if self._is_filler_heavy(text):
                base -= 2.0
            if base >= 5.0:
                raw.append({"t": float(start_sec), "score": float(base), "text": (text or "").strip(), "signals": sig})

        raw.sort(key=lambda m: m["score"], reverse=True)
        picked: list[dict] = []
        for m in raw:
            if len(picked) >= max_moments:
                break
            if any(abs(m["t"] - p["t"]) < min_separation_sec for p in picked):
                continue
            picked.append(m)
        picked.sort(key=lambda m: m["t"])
        return picked

    def _dedupe_by_text_similarity(self, segments: list[dict], *, sim_threshold: float = 0.86) -> list[dict]:
        """
        [DIVERSITY] Remove near-identical transcript content.
        Keeps higher-scoring segment when similarity is high.
        """
        if not segments:
            return []
        try:
            from modules.smart_segmentation import sentence_similarity
        except Exception:
            return segments

        out: list[dict] = []
        for seg in sorted(segments, key=lambda s: s.get("final_score", s.get("viral_score", 0)), reverse=True):
            t = (seg.get("transcript") or seg.get("hook") or "").strip()
            if not t:
                out.append(seg)
                continue
            dup = False
            for kept in out:
                kt = (kept.get("transcript") or kept.get("hook") or "").strip()
                if not kt:
                    continue
                if sentence_similarity(t[:420], kt[:420]) >= sim_threshold:
                    dup = True
                    break
            if not dup:
                out.append(seg)
        # preserve chronological order for downstream refiners; caller can re-sort
        out.sort(key=lambda s: s.get("start", 0))
        return out

    def _compute_hook_strength(self, full_text: str, first_3s_text: str) -> float:
        """
        [HOOK STRENGTH] Emphasize hooks in first ~3 seconds plus dramatic connectors.
        Returns 0..100-ish.
        """
        t0 = (first_3s_text or "").lower()
        t = (full_text or "").lower()
        strength = 0.0
        if any(p in t0 for p in (self.HOOK_MOMENT_PATTERNS or [])):
            strength += 45
        if any(p in t0 for p in (self.SURPRISE_PATTERNS or [])):
            strength += 25
        if any(p in t0 for p in (self.ARGUMENT_SIGNALS or [])):
            strength += 18
        if any(p in t0 for p in (self.EMOTION_KEYWORDS or [])):
            strength += 18
        if any(p in t0 for p in (self.CONNECTOR_WORDS or [])):
            strength += 12
        # light boost if the whole clip contains multiple signals
        sig_count = 0
        for group in (self.HOOK_MOMENT_PATTERNS, self.SURPRISE_PATTERNS, self.ARGUMENT_SIGNALS, self.EMOTION_KEYWORDS, self.HUMOR_MARKERS):
            try:
                if any(p in t for p in (group or [])):
                    sig_count += 1
            except Exception:
                pass
        strength += sig_count * 5
        return float(max(0.0, min(100.0, strength)))

    def _build_subtitle_cues_from_parent(self):
        """
        Build SubtitleCue list from self.parent.sub_transcriptions (dict of {start,end,text}).
        Uses smart_segmentation.SubtitleCue so we can reuse pause + sentence helpers.
        """
        cues_dict = getattr(self.parent, "sub_transcriptions", None)
        if not cues_dict or not isinstance(cues_dict, dict):
            return []
        try:
            from modules.smart_segmentation import SubtitleCue
        except Exception:
            return []
        cues = []
        for _, c in sorted(cues_dict.items(), key=lambda x: (x[1].get("start", 0) if isinstance(x[1], dict) else 0)):
            if not isinstance(c, dict):
                continue
            s = self._normalize_cue_time(c.get("start") or c.get("s") or 0)
            e = self._normalize_cue_time(c.get("end") or c.get("e") or (s + 3.0))
            t = (c.get("text") or c.get("t") or "").strip()
            if t:
                cues.append(SubtitleCue(float(s), float(e), t))
        cues.sort(key=lambda c: c.start)
        return cues

    def _find_hook_time_in_range(self, start_sec: float, end_sec: float, cues) -> float | None:
        """
        Find first hook-ish cue start within [start_sec, end_sec]. Returns cue.start or None.
        """
        if not cues:
            return None
        for cue in cues:
            if cue.end < start_sec:
                continue
            if cue.start > end_sec:
                break
            if self._is_hook_sentence(getattr(cue, "text", "")):
                return float(cue.start)
        return None

    def _adaptive_duration_bounds_from_scores(self, hook_score: float, argument_score: float, info_density: float) -> tuple[float, float]:
        """
        Variable duration based on signals (rough heuristic):
        - Strong hook -> 8-15s
        - Argument/discussion -> 15-40s
        - High info density -> 40-60s
        """
        if hook_score >= 60:
            return 8.0, 15.0
        if info_density >= 60:
            return 40.0, 60.0
        if argument_score >= 55:
            return 25.0, 40.0
        return 15.0, 25.0

    def _natural_clip_window(self, *, base_start: float, base_end: float, hook_time: float | None, cues, min_dur: float, max_dur: float) -> tuple[float, float, float | None]:
        """
        Hook-first + subtitle boundaries:
        - start near hook (hook-2s) snapped to cue.start and skip filler introductions
        - end at sentence punctuation OR pause>=0.6s, allow continuation until pause>1s/topic shift, cap 60s
        Returns (clip_start, clip_end, hook_time_used)
        """
        if not cues:
            # Fallback: keep within caps
            s = max(0.0, (hook_time - self.HOOK_PRE_ROLL_SEC) if hook_time is not None else base_start)
            e = min(max(s + min_dur, base_end), s + max_dur)
            return s, e, hook_time

        try:
            from modules.smart_segmentation import refine_segment_start_hook_first, find_best_boundary_near, refine_segment_end, is_sentence_ending, get_pause_after
            from modules.smart_segmentation import is_topic_shift
        except Exception:
            s = max(0.0, (hook_time - self.HOOK_PRE_ROLL_SEC) if hook_time is not None else base_start)
            e = min(max(s + min_dur, base_end), s + max_dur)
            return s, e, hook_time

        # --- start ---
        if hook_time is not None:
            start = refine_segment_start_hook_first(float(hook_time), float(base_end), cues, pre_roll_sec=self.HOOK_PRE_ROLL_SEC)
        else:
            start = find_best_boundary_near(float(base_start), cues, search_window=2.0, is_start=True)

        # --- end ---
        cap_end = min(float(start) + max_dur, float(start) + self.ABS_MAX_CLIP_SEC)
        desired_min_end = float(start) + min_dur
        # Ensure we don't cut mid-sentence at the original end
        min_end = refine_segment_end(float(base_end), cues, max_extension=min(6.0, max(2.0, cap_end - float(base_end))))
        end_target = max(desired_min_end, float(base_end), float(min_end))
        end = find_best_boundary_near(end_target, cues, search_window=3.0, is_start=False, min_end_time=min_end)
        end = min(float(end), cap_end)

        # Extend naturally forward from the chosen end while keeping bounds (context continuation)
        # Walk forward cue-by-cue until punctuation or pause>=0.6s and min_dur satisfied; stop at pause>1s or cap.
        best = float(end)
        prev_cue = None
        for i, cue in enumerate(cues):
            if cue.end < best - 0.2:
                continue
            if cue.start > cap_end:
                break
            best = max(best, float(cue.end))
            dur_now = best - float(start)
            pause = get_pause_after(cue, cues)
            if pause > self.TOPIC_SHIFT_PAUSE_SEC:
                break
            if prev_cue is not None:
                try:
                    if is_topic_shift(prev_cue.text, cue.text) and dur_now >= min_dur:
                        break
                except Exception:
                    pass
            if dur_now >= min_dur and (is_sentence_ending(cue.text) or pause >= self.NATURAL_PAUSE_END_SEC):
                break
            prev_cue = cue
        end = min(best, cap_end)

        if end - float(start) < self.ABS_MIN_CLIP_SEC:
            end = min(float(start) + self.ABS_MIN_CLIP_SEC, cap_end)
            end = find_best_boundary_near(end, cues, search_window=3.0, is_start=False)
        return float(start), float(end), hook_time

    def _build_clip_around_hook(self, hook_start: float, hook_end: float, duration_sec: float, cues=None) -> tuple:
        """
        Build clip around hook with duration diversity + sentence safety:
        start = hook - 2s
        end = start + random target duration (then snap to sentence boundary if possible)
        Clamped to CLIP_MIN/MAX and video duration.
        """
        start_time = max(0.0, hook_start - self.HOOK_PRE_ROLL_SEC)

        # STEP 3 — Random target duration (avoid uniform clips)
        target_duration = random.randint(12, 45)
        clip_end = start_time + float(target_duration)

        # STEP 4 — Align with sentence end (never cut speech)
        try:
            if cues:
                sentence_boundaries = find_sentence_boundaries(cues)
                for boundary_time, _ in sentence_boundaries:
                    if boundary_time > clip_end:
                        clip_end = float(boundary_time)
                        break
        except Exception:
            pass

        # STEP 5 — Safety limits
        clip_end = min(float(clip_end), float(duration_sec))
        clip_duration = float(clip_end) - float(start_time)
        if clip_duration < 10.0:
            clip_end = min(float(duration_sec), float(start_time) + 10.0)
        if (float(clip_end) - float(start_time)) > 60.0:
            clip_end = min(float(duration_sec), float(start_time) + 60.0)

        return (float(start_time), float(clip_end))

    def _merge_overlapping_clips(self, segments: list, overlap_threshold: float = 0.7) -> list:
        """
        If two clips overlap >70%, merge them instead of deleting.
        Keeps higher-scoring segment's timing, extends to cover both.
        """
        if len(segments) <= 1:
            return segments
        segs = sorted(segments, key=lambda x: x.get("start", 0))
        merged = []
        i = 0
        while i < len(segs):
            curr = segs[i]
            cs, ce = curr.get("start", 0), curr.get("end", 0)
            curr_dur = ce - cs
            j = i + 1
            while j < len(segs):
                next_s = segs[j]
                ns, ne = next_s.get("start", 0), next_s.get("end", 0)
                ov = max(0, min(ce, ne) - max(cs, ns))
                dur_min = min(curr_dur, ne - ns)
                if dur_min > 0 and (ov / dur_min) > overlap_threshold:
                    ce = max(ce, ne)
                    curr_dur = ce - cs
                    curr["end"] = ce
                    if curr.get("viral_score", 0) < next_s.get("viral_score", 0):
                        curr["viral_score"] = next_s.get("viral_score", 0)
                    j += 1
                else:
                    break
            merged.append(curr)
            i = j
        return merged

    def _normalize_cue_time(self, val) -> float:
        """Convert to seconds; if value > 10000 assume milliseconds."""
        try:
            v = float(val)
            if v > 10000:
                return v / 1000.0
            return v
        except (TypeError, ValueError):
            return 0.0

    def _get_transcript_for_range_from_cues(self, start_sec: float, end_sec: float) -> str:
        """Extract transcript from sub_transcriptions for [start_sec, end_sec]. For sliding window."""
        cues = getattr(self.parent, "sub_transcriptions", None)
        return self._get_transcript_for_clip_range(start_sec, end_sec, cues) if cues else ""

    def _get_transcript_for_clip_range(self, clip_start: float, clip_end: float, cues: dict) -> str:
        """
        Extract transcript from subtitle cues that OVERLAP the clip window.
        Include cue if: cue.end >= clip_start AND cue.start <= clip_end.
        Handles milliseconds (values > 10000). Returns text in chronological order.
        """
        if not cues or not isinstance(cues, dict):
            return ""
        entries = []
        for _, c in cues.items():
            if not isinstance(c, dict):
                continue
            s = c.get("start") or c.get("s")
            e = c.get("end") or c.get("e")
            t = (c.get("text") or c.get("t") or "").strip()
            if not t or s is None:
                continue
            start = self._normalize_cue_time(s)
            end = self._normalize_cue_time(e) if e is not None else start + 5.0
            if end >= clip_start and start <= clip_end:
                entries.append((start, t))
        entries.sort(key=lambda x: x[0])
        return " ".join(txt for _, txt in entries).strip() if entries else ""

    def get_transcript_for_clip_from_vtt(self, clip_start: float, clip_end: float, vtt_path: str) -> str:
        """Extract transcript from VTT file for clip range. Uses same source as clip export."""
        if not vtt_path or not os.path.exists(vtt_path):
            return ""
        try:
            cues = self.safe_parent_call("parse_vtt", vtt_path)
            if cues is None:
                return ""
            return self._get_transcript_for_clip_range(clip_start, clip_end, cues)
        except Exception:
            return ""

    def _get_transcript_duration_sec(self, formatted_transcript):
        """Return approximate duration in seconds from last timestamp in transcript."""
        max_sec = 0
        for line in formatted_transcript.split("\n"):
            match = re.search(r"\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]", line)
            if match:
                g = match.groups()
                if len(g) == 3 and g[2] is not None:
                    t_sec = int(g[0]) * 3600 + int(g[1]) * 60 + int(g[2])
                else:
                    t_sec = int(g[0]) * 60 + int(g[1])
                max_sec = max(max_sec, t_sec)
        return max_sec

    def _process_raw_hook_to_tts(self, raw_text: str) -> str:
        """
        Convert raw transcript to TTS-ready hook (8-12 words, first sentence or first 10 words).
        - Remove timestamps [MM:SS], brackets, trim
        - Split by . ? ! -> use first sentence
        - Strip leading intro phrases (e.g. "Nah sebelum kita bahas...")
        - If no punctuation: take first 10 words
        - Cap at HOOK_MAX_WORDS
        """
        if not raw_text or not raw_text.strip():
            return ""
        t = raw_text.strip()
        # Remove timestamps [00:12] or [0:12] or [1:23:45]
        t = re.sub(r'\[\d{1,2}:\d{2}(?::\d{2})?\]', '', t)
        # Remove brackets and excess whitespace
        t = re.sub(r'\[|\]', '', t)
        t = re.sub(r'\s+', ' ', t).strip()
        if not t:
            return ""
        # Split by sentence punctuation . ? !
        sentences = re.split(r'[.?!]+', t)
        first = (sentences[0] or "").strip()
        if not first:
            first = t
        # Strip leading intro/filler phrases to get the punch (e.g. "Nah sebelum kita bahas wasit kita bahas dulu gol Beckham..." -> "gol Beckham...")
        first_lower = first.lower()
        lead_ins = ["nah ", "oke ", "jadi ", "karena ", "karena itu ", "lalu ", "terus ", "kita bahas dulu ", "wasit kita bahas ", "wasit kita bahas dulu "]
        for _ in range(8):  # Multiple passes to strip stacked intro phrases
            changed = False
            for lead in lead_ins + list(self.INTRO_PHRASES):
                if first_lower.startswith(lead):
                    first_lower = first_lower[len(lead):].strip()
                    first = first[len(lead):].strip()
                    changed = True
                    break
            if not changed:
                break
        words = first.split()
        if not words:
            words = t.split()
        # Cap at HOOK_MAX_WORDS (8-12), fallback first 10 if no punctuation
        if len(sentences) > 1:
            hook_words = words[:self.HOOK_MAX_WORDS]
        else:
            hook_words = words[:10]  # No punctuation: first 10 words
        return " ".join(hook_words).strip()

    def _remove_hook_fillers(self, text: str) -> str:
        """Remove filler words before scoring sentences."""
        if not text:
            return ""
        t = text
        for f in self.HOOK_FILLER_REMOVE:
            pat = r'(?<!\w)' + re.escape(f) + r'(?!\w)'
            t = re.sub(pat, ' ', t, flags=re.IGNORECASE)
        return re.sub(r'\s+', ' ', t).strip()

    def _score_sentence_for_hook(self, sentence: str) -> float:
        """Score sentence: names (cap), strong verbs, surprise = higher score."""
        cleaned = self._remove_hook_fillers(sentence)
        if len(cleaned.split()) < 3:
            return 0.0
        t = cleaned.lower()
        score = 0.0
        for w in cleaned.split():
            if len(w) >= 4 and w[0].isupper():
                score += 2.0
        for v in self.HOOK_STRONG_VERBS:
            if v in t:
                score += 1.5
                break
        for s in self.HOOK_SURPRISE:
            if s in t:
                score += 2.0
                break
        return score

    def _score_phrase_for_hook(self, phrase: str) -> float:
        """Score a phrase (may be sub-sentence). Reuse same heuristics."""
        return self._score_sentence_for_hook(phrase)

    def _extract_core_hook_from_text(self, full_text: str) -> str:
        """
        Extract strongest statement from full segment (not first seconds).
        Prefer names, strong verbs (akan, ternyata, justru), surprise. Max 12 words.
        For run-on transcripts: slide window to find best phrase.
        """
        if not full_text or not full_text.strip():
            return ""
        t = full_text.strip()
        t = re.sub(r'\[\d{1,2}:\d{2}(?::\d{2})?\]', '', t)
        t = re.sub(r'\[|\]', '', t)
        t = re.sub(r'\s+', ' ', t).strip()
        if not t:
            return ""
        sentences = re.split(r'[.?!]+', t)
        best_phrase, best_score = "", -1.0
        for s in sentences:
            s = s.strip()
            if not s or len(s.split()) < 2:
                continue
            words = s.split()
            if len(words) <= self.HOOK_MAX_WORDS:
                score = self._score_phrase_for_hook(s)
                if score > best_score:
                    best_score = score
                    best_phrase = s
            else:
                # Run-on: slide window (4..12 words) to find strongest phrase
                for size in range(self.HOOK_MAX_WORDS, 3, -1):
                    for i in range(len(words) - size + 1):
                        window = " ".join(words[i : i + size])
                        score = self._score_phrase_for_hook(window)
                        if score > best_score:
                            best_score = score
                            best_phrase = window
        if not best_phrase:
            words = t.split()
            return " ".join(words[:self.HOOK_MAX_WORDS]).strip()
        return " ".join(best_phrase.split()[:self.HOOK_MAX_WORDS]).strip()

    def extract_hook_from_segment(self, segment_start_sec, transcriptions):
        """
        Extract core hook from full segment transcript (strongest statement, not first seconds).
        """
        if not transcriptions:
            return ""
        parts = []
        for _, item in sorted(transcriptions.items(), key=lambda x: x[1].get('start', 0)):
            text = (item.get('text') or "").strip()
            if text:
                parts.append(text)
        full = " ".join(parts).strip()
        return self._extract_core_hook_from_text(full) if full else ""

    def _get_viral_segments_opus_style(self, formatted_transcript: str, duration_sec: float) -> list:
        """
        [OPUS-STYLE] Sliding window: 25s window, 10s step (0-25, 10-35, 20-45...).
        Multi-signal scoring: viral = 0.35*hook + 0.25*emotion + 0.20*argument + 0.10*controversy + 0.10*info_density.
        Returns top 20 clips (15-45s), deduplicated if overlap >60%.
        """
        window_size = self.OPUS_WINDOW_SIZE
        step_size = self.OPUS_STEP_SIZE
        min_dur = self.OPUS_CLIP_MIN
        max_dur = self.OPUS_CLIP_MAX
        top_n = self.OPUS_TOP_CLIPS
        has_cues = bool(getattr(self.parent, "sub_transcriptions", None))
        cues = self._build_subtitle_cues_from_parent() if has_cues else []

        def get_window_text(s, e):
            if has_cues:
                return self._get_transcript_for_range_from_cues(s, e)
            return self._slice_transcript_by_time(formatted_transcript, s, e)

        candidates = []

        # [GOLDEN MOMENT] Anchor-first candidates before sliding windows
        if cues:
            target = max(10, min(40, int((duration_sec / 3600.0) * self.TARGET_CLIPS_PER_HOUR) + 8))
            golden = self._detect_golden_moments(cues, max_moments=target, min_separation_sec=10.0)
            for m in golden:
                t0 = float(m["t"])
                base_start = max(0.0, t0 - self.HOOK_PRE_ROLL_SEC)
                base_end = min(duration_sec, t0 + 35.0)
                window_text = get_window_text(base_start, base_end)
                if len(window_text.strip()) < 30 or self._is_filler_heavy(window_text):
                    continue
                first_3s_text = get_window_text(base_start, min(base_end, base_start + 3.5))
                hook = self._compute_hook_score(window_text, first_3s_text)
                emotion = self._compute_emotion_score(window_text)
                argument = self._compute_argument_score(window_text)
                controversy = self._compute_controversy_score(window_text)
                info_density = self._compute_information_density_score(window_text)
                viral = (
                    0.35 * hook + 0.25 * emotion + 0.20 * argument
                    + 0.10 * controversy + 0.10 * info_density
                )
                if viral < 1.5:
                    continue
                min_d, max_d = self._adaptive_duration_bounds_from_scores(hook, argument, info_density)
                clip_start, clip_end, hook_used = self._natural_clip_window(
                    base_start=base_start,
                    base_end=base_end,
                    hook_time=t0,
                    cues=cues,
                    min_dur=min_d,
                    max_dur=max_d,
                )
                if (clip_end - clip_start) < float(self.ABS_MIN_CLIP_SEC):
                    continue

                hook_strength = self._compute_hook_strength(window_text, first_3s_text)
                moment_score = float(m.get("score", 0.0))
                hs = 1.0 + (hook_strength / 100.0)
                em = 1.0 + (emotion / 100.0)
                ar = 1.0 + (argument / 100.0)
                eng = 1.0 + (min(100.0, max(0.0, viral)) / 120.0)
                golden_final = (moment_score * 2.0) * hs * em * ar * eng

                candidates.append({
                    "start": clip_start,
                    "end": clip_end,
                    "viral_score": round(float(viral), 1),
                    "hook_score": hook,
                    "hook_strength": round(hook_strength, 1),
                    "emotion_score": emotion,
                    "argument_score": argument,
                    "controversy_score": controversy,
                    "info_density_score": info_density,
                    "moment_score": round(moment_score, 2),
                    "final_score": round(float(golden_final), 2),
                    "hook": (m.get("text") or window_text[:80] or "").strip(),
                    "transcript": window_text.strip(),
                    "_hook_time": hook_used if hook_used is not None else t0,
                    "_golden_anchor": True,
                    "_signals": m.get("signals") or [],
                })
        start = 0
        while start + min_dur <= duration_sec:
            end = min(start + window_size, duration_sec)
            dur = end - start
            if dur < min_dur:
                start += step_size
                continue

            window_text = get_window_text(start, end)
            if len(window_text.strip()) < 30:
                start += step_size
                continue

            if self._is_filler_heavy(window_text):
                start += step_size
                continue

            first_3s_text = get_window_text(start, min(end, start + 3.5))
            hook = self._compute_hook_score(window_text, first_3s_text)
            emotion = self._compute_emotion_score(window_text)
            argument = self._compute_argument_score(window_text)
            controversy = self._compute_controversy_score(window_text)
            info_density = self._compute_information_density_score(window_text)
            viral = (
                0.35 * hook + 0.25 * emotion + 0.20 * argument
                + 0.10 * controversy + 0.10 * info_density
            )
            if viral < 2.0:
                start += step_size
                continue

            # Hook-first + subtitle-boundary clip with variable duration
            hook_time = self._find_hook_time_in_range(start, end, cues) if cues else start
            min_d, max_d = self._adaptive_duration_bounds_from_scores(hook, argument, info_density)
            clip_start, clip_end, hook_used = self._natural_clip_window(
                base_start=start,
                base_end=end,
                hook_time=hook_time,
                cues=cues,
                min_dur=min_d,
                max_dur=max_d,
            )
            clip_dur = clip_end - clip_start
            # Avoid uniform durations: small jitter target (still bound to sentence/pause)
            if clip_dur >= max(self.ABS_MIN_CLIP_SEC, min_dur) and clip_dur <= self.ABS_MAX_CLIP_SEC:
                hook_strength = self._compute_hook_strength(window_text, first_3s_text)
                candidates.append({
                    "start": clip_start,
                    "end": clip_end,
                    "viral_score": round(viral, 1),
                    "hook_score": hook,
                    "hook_strength": round(hook_strength, 1),
                    "emotion_score": emotion,
                    "argument_score": argument,
                    "controversy_score": controversy,
                    "info_density_score": info_density,
                    "hook": window_text[:80].strip(),
                    "transcript": window_text.strip(),
                    "_hook_time": hook_used if hook_used is not None else start,
                })
            start += step_size

        # Prefer golden anchors (final_score) when available, otherwise viral_score
        candidates.sort(key=lambda x: (x.get("final_score", 0), x.get("viral_score", 0)), reverse=True)
        deduped = []
        for seg in candidates:
            overlap_any = False
            for kept in deduped:
                ov = max(0, min(seg["end"], kept["end"]) - max(seg["start"], kept["start"]))
                dur_min = min(seg["end"] - seg["start"], kept["end"] - kept["start"])
                if dur_min > 0 and (ov / dur_min) > self.OPUS_OVERLAP_THRESHOLD:
                    overlap_any = True
                    break
            if not overlap_any:
                deduped.append(seg)
            if len(deduped) >= top_n:
                break
        deduped = deduped[:top_n]

        # [DIVERSITY] Remove near-duplicate transcript content after overlap dedupe
        deduped = self._dedupe_by_text_similarity(deduped, sim_threshold=0.86)

        # [DURATION DIVERSITY] Nudge ends slightly to avoid uniform lengths (only when cues exist)
        if cues and len(deduped) > 1:
            try:
                from modules.smart_segmentation import find_best_boundary_near
            except Exception:
                find_best_boundary_near = None
            if find_best_boundary_near:
                seen_bucket: dict[int, int] = {}
                for seg in deduped:
                    dur_s = float(seg["end"] - seg["start"])
                    bucket = int(round(dur_s / 5.0) * 5)
                    seen_bucket[bucket] = seen_bucket.get(bucket, 0) + 1
                    if seen_bucket[bucket] <= 2:
                        continue
                    target_end = float(seg["end"]) + (1.6 if (seen_bucket[bucket] % 2 == 0) else -1.2)
                    target_end = max(float(seg["start"]) + float(self.ABS_MIN_CLIP_SEC), min(float(seg["start"]) + float(self.ABS_MAX_CLIP_SEC), target_end))
                    nudged = float(find_best_boundary_near(target_end, cues, search_window=2.5, is_start=False))
                    if nudged > float(seg["start"]) + float(self.ABS_MIN_CLIP_SEC):
                        seg["end"] = nudged

        deduped.sort(key=lambda x: (x.get("final_score", 0), x.get("viral_score", 0)), reverse=True)
        return deduped[:top_n]

    def get_viral_segments_from_ai(self, raw_transcript, keyword=None):
        """
        [OPUS-STYLE] Sliding window 25s/10s for 10-30 clips. Multi-signal viral scoring.
        [MOMENT-FIRST] Fallback: hook moments -> expand -> score.
        """
        if not raw_transcript:
            return None

        cues = getattr(self.parent, "sub_transcriptions", None) or {}
        formatted_transcript = ""
        duration_sec = 60.0
        if cues and isinstance(cues, dict):
            entries = sorted(cues.items(), key=lambda x: (x[1].get("start", 0) if isinstance(x[1], dict) else 0))
            for _, entry in entries:
                if not isinstance(entry, dict):
                    continue
                start = self._normalize_cue_time(entry.get("start") or entry.get("s", 0))
                end = self._normalize_cue_time(entry.get("end") or entry.get("e") or start + 5)
                duration_sec = max(duration_sec, end)
                ts = f"[{int(start // 60):02d}:{int(start % 60):02d}]"
                formatted_transcript += f"{ts} {entry.get('text', entry.get('t', ''))}\n"
        elif isinstance(raw_transcript, dict):
            for i in sorted(raw_transcript.keys()):
                entry = raw_transcript[i]
                start = entry.get('start', 0)
                ts = f"[{int(start // 60):02d}:{int(start % 60):02d}]"
                formatted_transcript += f"{ts} {entry.get('text', '')}\n"
            duration_sec = max(self._get_transcript_duration_sec(formatted_transcript), 60)
        else:
            formatted_transcript = raw_transcript if isinstance(raw_transcript, str) else ""
            duration_sec = max(self._get_transcript_duration_sec(formatted_transcript), 60)

        # [OPUS-STYLE] Primary path: sliding window for many clips (10-30 per video)
        openai_segments = []
        if getattr(self.parent, "sub_transcriptions", None) and self.parent.sub_transcriptions:
            opus_segments = self._get_viral_segments_opus_style(formatted_transcript, duration_sec)
            if opus_segments:
                print(f"  [OPUS] Sliding window: {len(opus_segments)} clips (15-45s)")
                openai_segments = opus_segments

        # [MOMENT-FIRST] Fallback when Opus returns none
        if not openai_segments and getattr(self.parent, "sub_transcriptions", None) and self.parent.sub_transcriptions:
            moments = self._detect_hook_moments()
            print(f"  [MOMENT] Detected {len(moments)} hook moments")

            for hook_start, hook_end, text, base_score in moments:
                clip_start, clip_end = self._build_clip_around_hook(hook_start, hook_end, duration_sec)
                dur = clip_end - clip_start
                if dur < self.CLIP_MIN_DURATION_SEC:
                    continue
                openai_segments.append({
                    "start": clip_start, "end": clip_end,
                    "viral_score": base_score, "hook": text[:80],
                    "_hook_time": hook_start,
                })

            # Window scanning for more candidates (18s, 4s overlap)
            step_sec = self.WINDOW_SIZE_SEC - self.WINDOW_OVERLAP_SEC
            raw_windows = []
            for start_sec in range(0, int(duration_sec), step_sec):
                end_sec = min(start_sec + self.WINDOW_SIZE_SEC, int(duration_sec) + 1)
                if end_sec - start_sec < 12:
                    continue
                window_text = self._slice_transcript_by_time(formatted_transcript, start_sec, end_sec)
                if len(window_text.strip()) < 40:
                    continue
                raw_windows.append((start_sec, end_sec, window_text))

            texts = [w[2] for w in raw_windows]
            embeddings = self._compute_embeddings_batch(texts)
            emotion_scores = self._emotion_scores_batch(texts)

            for i, (start_sec, end_sec, window_text) in enumerate(raw_windows):
                rule_score = self._compute_local_viral_score(window_text)
                sem_score = self._semantic_uniqueness_score(embeddings, i) if embeddings else 0
                emo_score = emotion_scores[i] if emotion_scores else 0
                viral_score = min(100, rule_score + sem_score + emo_score)
                if viral_score < 3:
                    continue
                clip_start, clip_end = self._build_clip_around_hook(start_sec, end_sec, duration_sec)
                dur = clip_end - clip_start
                if dur >= self.CLIP_MIN_DURATION_SEC:
                    openai_segments.append({
                        "start": clip_start, "end": clip_end,
                        "viral_score": viral_score, "hook": (window_text[:80] or "").strip(),
                        "_hook_time": start_sec,
                    })

            openai_segments.sort(key=lambda x: x.get("viral_score", 0), reverse=True)
            seen_ranges = []
            deduped = []
            for seg in openai_segments:
                s, e = seg["start"], seg["end"]
                too_close = any(abs(s - rs) < 8 and abs(e - re) < 8 for rs, re in seen_ranges)
                if not too_close:
                    seen_ranges.append((s, e))
                    deduped.append(seg)

            openai_segments = self._merge_overlapping_clips(deduped, overlap_threshold=0.7)
            for seg in openai_segments:
                s, e = seg["start"], seg["end"]
                if e - s > self.CLIP_MAX_DURATION_SEC:
                    seg["end"] = s + self.CLIP_MAX_DURATION_SEC
                elif e - s < self.CLIP_MIN_DURATION_SEC:
                    seg["end"] = s + self.CLIP_MIN_DURATION_SEC

            target_clips = max(15, min(30, int(duration_sec / 3600 * self.TARGET_CLIPS_PER_HOUR)))
            openai_segments = openai_segments[:max(target_clips, 40)]
            print(f"  [MOMENT] Candidates: {len(deduped)} -> final pool: {len(openai_segments)}")

        # [FALLBACK] No sub_transcriptions: use GPT
        if not openai_segments and getattr(self.parent, "openai_available", False):
            transcript_for_ai = formatted_transcript.strip()[:120000]
            openai_segments = self.safe_parent_call("detect_viral_segments_with_openai", transcript_for_ai)
            if openai_segments:
                for seg in openai_segments:
                    s, e = float(seg.get("start", 0)), float(seg.get("end", 0))
                    if e - s > self.CLIP_MAX_DURATION_SEC:
                        seg["end"] = s + self.CLIP_MAX_DURATION_SEC
                    if e - s < self.CLIP_MIN_DURATION_SEC:
                        seg["end"] = s + self.CLIP_MIN_DURATION_SEC

        if not openai_segments:
            print("  [WARN] No viral segments. Ensure transcript has timestamps (VTT/sub_transcriptions).")
            return None

        openai_segments.sort(key=lambda x: x.get("viral_score", 0), reverse=True)
        target_clips = max(15, min(30, int(duration_sec / 3600 * self.TARGET_CLIPS_PER_HOUR)))
        openai_segments = openai_segments[:target_clips]

        print(f"  [OPENAI] Processing {len(openai_segments)} clips for titles and hooks")

        viral_segments = {}
        PADDING_SEC = 5
        for i, item in enumerate(openai_segments):
            start_sec = float(item.get("start", 0))
            end_sec = float(item.get("end", 0))
            if end_sec <= start_sec:
                continue
            duration = end_sec - start_sec
            if duration < self.CLIP_MIN_DURATION_SEC:
                continue
            if duration > self.CLIP_MAX_DURATION_SEC:
                end_sec = start_sec + self.CLIP_MAX_DURATION_SEC

            # Build segment transcript early (needed for hook fallback)
            seg_text_parts = []
            if getattr(self.parent, "sub_transcriptions", None):
                for sub_item in (getattr(self.parent, "sub_transcriptions", None) or {}).values():
                    sub_start = sub_item["start"]
                    sub_end = sub_item["end"]
                    if (sub_start >= start_sec - PADDING_SEC and sub_start <= end_sec + PADDING_SEC) or (
                        sub_end >= start_sec - PADDING_SEC and sub_end <= end_sec + PADDING_SEC
                    ):
                        seg_text_parts.append(sub_item.get("text", ""))
            full_seg_text = " ".join(seg_text_parts)

            # Clip relevance: skip filler-heavy / low-information segments
            if self._is_filler_heavy(full_seg_text):
                continue

            hook_script = (item.get("hook") or "").strip()
            if not hook_script and full_seg_text:
                hook_script = self._extract_core_hook_from_text(full_seg_text)
            if not hook_script:
                hook_script = " ".join(full_seg_text.split()[:10]).strip() if full_seg_text else ""

            hook_text = hook_script
            hook_score_val = 50
            if hook_script:
                try:
                    refined_hook, hook_score_val = self.safe_parent_call("refine_and_score_hook_openai", hook_script, max_attempts=1) or (hook_script, 0.5)
                    if refined_hook:
                        hook_text = refined_hook
                    boosted = self.safe_parent_call("apply_hook_trigger_boost", hook_text, hook_score_val)
                    if boosted is not None:
                        hook_score_val = boosted
                except Exception:
                    pass

            # Content-based adjustment: boost emotional/dramatic moments, penalize intro-only segments
            viral_score_val = int(item.get("viral_score", 0))
            viral_score_val = self._adjust_viral_score_by_content(viral_score_val, full_seg_text)
            # STEP 9 — final_score combines: viral (emotion, argument, keyword, emphasis), hook, activity
            activity_score = 75
            final_score_val = round(
                viral_score_val * 0.5 + hook_score_val * 0.3 + activity_score * 0.2
            )
            title = (item.get("title") or "").strip()
            if not title and full_seg_text:
                existing = [v.get("text") for v in viral_segments.values() if v.get("text")]
                cleaned_seg = self._clean_filler_words(full_seg_text)
                clickbait = self.safe_parent_call(
                    "generate_clickbait_title",
                    cleaned_seg or full_seg_text, existing_titles=existing, max_attempts=5, strict_content=True
                )
                if clickbait:
                    # Title semantic validation: regenerate if title does not match content
                    sim = self._title_segment_similarity(clickbait, full_seg_text)
                    if sim < 0.35:
                        clickbait = self.safe_parent_call(
                            "generate_clickbait_title",
                            cleaned_seg or full_seg_text, existing_titles=existing, max_attempts=3, strict_content=True
                        ) or clickbait
                    title = self.safe_parent_call("clean_viral_title", clickbait) if clickbait else ""
            if not title:
                title = (full_seg_text or "").strip()
                title = (title[:52].rstrip() + "...") if len(title) > 55 else title
            if not title:
                title = "Klip"
            # Ensure hook is never empty (TTS intro) — fallback to title
            if not hook_text or not hook_text.strip():
                hook_text = title
                hook_script = title
            caption = (item.get("caption") or "").strip()
            keywords = item.get("keywords") or []
            hashtags = item.get("hashtags") or []
            if isinstance(keywords, str):
                keywords = [k.strip() for k in keywords.replace(",", " ").split() if k.strip()]
            if isinstance(hashtags, str):
                hashtags = [h.strip().lstrip("#") for h in hashtags.replace(",", " ").split() if h.strip()]
            viral_segments[i] = {
                "start": float(start_sec),
                "end": float(end_sec),
                "text": title,
                "segment_transcript": full_seg_text,
                "hook_script": hook_text,
                "hook_text": hook_text,
                "clickbait_title": title,
                "viral_score": viral_score_val,
                "hook_score": hook_score_val,
                "final_score": final_score_val,
                "caption": caption,
                "keywords": keywords,
                "hashtags": hashtags,
                "_hook_time": item.get("_hook_time"),
            }

        # Dedupe by >60% overlap, keep higher final_score; remove low quality (STEP 10)
        if viral_segments:
            seg_list = list(viral_segments.items())
            seg_list.sort(key=lambda x: x[1].get("final_score", 0), reverse=True)
            keep_ids = []
            for idx, (kid, seg) in enumerate(seg_list):
                overlap_any = False
                for kept_id in keep_ids:
                    kept = viral_segments[kept_id]
                    ov = max(0, min(seg["end"], kept["end"]) - max(seg["start"], kept["start"]))
                    dur_min = min(seg["end"] - seg["start"], kept["end"] - kept["start"])
                    if dur_min > 0 and (ov / dur_min) > 0.6:
                        overlap_any = True
                        break
                if not overlap_any:
                    dur = seg["end"] - seg["start"]
                    if dur >= 8.0 and seg.get("final_score", 0) >= 5:
                        keep_ids.append(kid)
            viral_segments = {k: viral_segments[k] for k in keep_ids if k in viral_segments}

        if viral_segments:
            print(f"  [SUCCESS] Berhasil menemukan {len(viral_segments)} Golden Moment via AI!")

            # [SMART BOUNDARY] Refine segment boundaries (pre-roll + sentence completion)
            try:
                from modules.smart_segmentation import refine_all_segments
                
                # Try to find subtitle file (for Smart Start + Sentence Completion refinement)
                subtitle_path = None
                vid = getattr(self.parent, 'video_path', None) or getattr(self.parent, 'current_video_path', None)
                if vid:
                    base_path = os.path.splitext(vid)[0]
                    for ext in [".id.vtt", ".en.vtt", ".vtt", ".srt"]:
                        p = base_path + ext
                        if os.path.exists(p):
                            subtitle_path = p
                            break
                if not subtitle_path and getattr(self.parent, 'current_transcript_path', None):
                    tp = self.parent.current_transcript_path
                    if tp and os.path.exists(tp):
                        subtitle_path = tp
                
                if subtitle_path:
                    print(f"  [SMART] Refining boundaries using subtitles: {os.path.basename(subtitle_path)}")
                    # Convert dict to list for refinement (pass _hook_time for hook-first start)
                    segments_list = [
                        {'start': v['start'], 'end': v['end'], 'text': v['text'],
                         'segment_transcript': v.get('segment_transcript', ''),
                         'hook_script': v.get('hook_script', ''), 'hook_text': v.get('hook_text', ''),
                         'viral_score': v.get('viral_score', 0), 'hook_score': v.get('hook_score', 0),
                         'final_score': v.get('final_score', 0), 'clickbait_title': v.get('clickbait_title', ''),
                         'caption': v.get('caption', ''), 'keywords': v.get('keywords', []), 'hashtags': v.get('hashtags', []),
                         '_id': k, '_hook_time': v.get('_hook_time')}
                        for k, v in viral_segments.items()
                    ]
                    refined_list, stats = refine_all_segments(segments_list, subtitle_path,
                                                             min_duration=8.0,
                                                             max_duration=60.0)
                    by_id = {s['_id']: s for s in segments_list}
                    # [STEP 10] Remove low quality: incomplete sentence, very low score, < 8s
                    MIN_CLIP_DURATION_SEC = 8.0
                    MIN_FINAL_SCORE = 5
                    refined_list = [
                        seg for seg in refined_list
                        if (seg['end'] - seg['start']) >= MIN_CLIP_DURATION_SEC
                        and seg.get('final_score', 0) >= MIN_FINAL_SCORE
                        and not seg.get('_incomplete_sentence', False)
                    ]
                    # [STEP 8] Sort by final_score descending (highest first)
                    refined_list.sort(key=lambda s: (s.get('final_score', 0), -(s['end'] - s['start'])), reverse=True)
                    viral_segments = {}
                    for seg in refined_list:
                        orig = by_id.get(seg['_id'], {})
                        viral_segments[seg['_id']] = {
                            'start': seg['start'],
                            'end': seg['end'],
                            'text': orig.get('text', seg.get('text', '')),
                            'segment_transcript': orig.get('segment_transcript', ''),
                            'hook_script': orig.get('hook_script', ''),
                            'hook_text': orig.get('hook_text', ''),
                            'viral_score': orig.get('viral_score', 0),
                            'hook_score': orig.get('hook_score', 0),
                            'final_score': orig.get('final_score', 0),
                            'clickbait_title': orig.get('clickbait_title', ''),
                            'caption': orig.get('caption', ''),
                            'keywords': orig.get('keywords', []),
                            'hashtags': orig.get('hashtags', []),
                        }
                else:
                    # No subtitle file: apply pre-roll buffer only (max 4 sec)
                    for k, v in viral_segments.items():
                        v["start"] = max(0.0, float(v.get("start", 0)) - 4.0)
            except Exception as e:
                print(f"  [WARNING] Smart boundary refinement failed: {e}")
            return viral_segments
        print("  [WARNING] AI tidak menghasilkan segmen viral yang valid")
        return None

    def generate_segment_titles_parallel(self):
        """Generate titles with OpenAI only (no Groq). Used when segments came from heatmap, not from OpenAI detection."""
        analysis_results = getattr(self.parent, "analysis_results", None) or []
        valid_segments = [
            res for res in analysis_results
            if (res.get("full_topic") or res.get("topic")) and not (res.get("full_topic") or "").startswith("[")
        ]
        if not valid_segments:
            return
        if not getattr(self.parent, "openai_available", False):
            return
        total = len(valid_segments)
        for i, segment in enumerate(valid_segments):
            text = (segment.get("full_topic") or segment.get("topic") or "").strip()[:2000]
            if not text:
                continue
            cleaned = self._clean_filler_words(text)
            existing = [r.get("topic") or r.get("clickbait_title") for r in analysis_results[:i]]
            title = self.safe_parent_call("generate_clickbait_title", cleaned or text, existing_titles=existing, max_attempts=2, strict_content=True)
            if title and title != "Untitled Clip":
                segment["topic"] = title
                segment["clickbait_title"] = title
            if self.parent and hasattr(self.parent, "progress_var"):
                self.parent.progress_var.set(f"Generating titles... ({i+1}/{total})")
            if self.parent and getattr(self.parent, "root", None):
                self.parent.root.update()

    def match_segments_with_content(self, segments, transcriptions):
        """Match heatmap segments with transcribed content"""
        # [SMART FIX] If "segments" is already a dictionary from AI (viral_segments), 
        # it means we already have the perfect cuts and titles.
        # So we just convert it to the list format expected by UI.
        if isinstance(transcriptions, dict) and transcriptions and isinstance(segments, list) == False:
             # This happens when we skipped heatmap and used AI segments directly
             # Actually, in analyze_video logic:
             # if ai_viral_segments: transcriptions = ai_viral_segments
             # then heatmap_segments is created from it.
             pass

        results = []
        
        # [ROBUST CHECK] Check if we are in Smart Mode (AI-curated segments)
        # Standard Whisper transcripts don't have 'hook_script'
        is_smart_mode = False
        if transcriptions and isinstance(transcriptions, dict):
            first_key = next(iter(transcriptions))
            if isinstance(transcriptions[first_key], dict) and 'hook_script' in transcriptions[first_key]:
                is_smart_mode = True
                print(f"  [DEBUG] Entering Smart Mode Matching (AI-Curated)")
        
        print(f"  [DEBUG] Segment matching: {len(segments)} segments, {len(transcriptions)} transcription chunks, SmartMode: {is_smart_mode}")

        # Raw subtitle cues for transcript extraction (log content must match clip time range)
        raw_cues = getattr(self.parent, "sub_transcriptions", None) or transcriptions

        for segment in segments:
            topic = "Topik tidak ditemukan"
            full_text = ""
            hook_script = ""

            # LOG FIX: Always extract transcript from cues overlapping clip window
            clip_start, clip_end = segment["start"], segment["end"]
            full_text = self._get_transcript_for_clip_range(clip_start, clip_end, raw_cues)

            if is_smart_mode:
                found = False
                for _, trans in transcriptions.items():
                    if abs(trans["start"] - segment["start"]) < 0.1:
                        topic = trans.get("clickbait_title", trans.get("text", ""))
                        hook_script = trans.get("hook_script", trans.get("hook_text", ""))
                        viral_score = trans.get("viral_score", 0)
                        hook_score = trans.get("hook_score", 0)
                        final_score = trans.get("final_score", 0)
                        clickbait_title = trans.get("clickbait_title", trans.get("text", ""))
                        found = True
                        if not full_text:
                            full_text = trans.get("segment_transcript", trans.get("text", ""))
                        break
                if not found:
                    continue
            else:
                if not full_text:
                    full_text = "[Tidak ada transkripsi tersedia]"
                topic = full_text if len(full_text) < 100 else full_text[:100] + "..."
                if full_text and full_text != "[Tidak ada transkripsi tersedia]":
                    hook_script = self._extract_core_hook_from_text(full_text) or " ".join(full_text.split()[:10]).strip()
                if not hook_script:
                    hook_script = topic
            
            # [BUG FIX] Validate segment duration - AI sometimes returns wrong timestamps
            calculated_duration = segment['end'] - segment['start']

            if calculated_duration > 300.0:
                # Bug detected: AI returned wrong timestamps
                # Recalculate duration from transcription chunk instead
                print(f"  [BUG FIX] Invalid duration detected: {calculated_duration:.1f}s for segment at {segment['start']:.1f}s")
                
                # Find matching transcription to get correct timestamps
                if is_smart_mode and transcriptions:
                    for trans in transcriptions.values():
                        if abs(trans['start'] - segment['start']) < 0.1:
                            # Use transcription timestamps instead
                            segment['start'] = trans['start']
                            segment['end'] = trans['end']
                            calculated_duration = segment['end'] - segment['start']
                            print(f"  [BUG FIX] Corrected to: {calculated_duration:.1f}s using transcription timestamps")
                            break
                
                # If still invalid, skip this segment
                if calculated_duration > 300.0:
                    print(f"  [BUG FIX] Skipping segment - could not fix duration")
                    continue
            
            # Clip duration: 12–35 seconds
            if calculated_duration > self.CLIP_MAX_DURATION_SEC:
                segment['end'] = segment['start'] + self.CLIP_MAX_DURATION_SEC
                calculated_duration = float(self.CLIP_MAX_DURATION_SEC)

            # Ensure hook never empty (TTS intro) — fallback to topic
            if not hook_script or not hook_script.strip():
                hook_script = topic or "Klip"
            
            r = {
                'start': segment['start'],
                'end': segment['end'],
                'duration': calculated_duration,
                'topic': topic,
                'full_topic': full_text,
                'hook_script': hook_script,
                'hook_text': hook_script,
                'activity': segment['avg_activity'],
            }
            if is_smart_mode and found:
                r['viral_score'] = viral_score
                r['hook_score'] = hook_score
                r['final_score'] = final_score
                r['clickbait_title'] = clickbait_title
            else:
                r['viral_score'] = segment.get('viral_score', 0)
                r['hook_score'] = segment.get('hook_score', 0)
                act = segment.get('avg_activity', 0.75)
                act_score = (act * 100) if act <= 1 else min(100, act)
                r['final_score'] = round(
                    r['viral_score'] * 0.5 + r['hook_score'] * 0.3 + act_score * 0.2
                )
                r['clickbait_title'] = topic or ''
            results.append(r)
        
        final_results = []
        min_d = float(self.CLIP_MIN_DURATION_SEC)
        max_d = float(self.CLIP_MAX_DURATION_SEC)
        print(f"  [FILTER] Duration Rule: {min_d:.0f}s - {max_d:.0f}s")

        for r in results:
            if r['duration'] >= min_d and r['duration'] <= (max_d + 5.0):
                final_results.append(r)
            else:
                print(f"  [FILTER] Klip dihapus (Durasi: {r['duration']:.1f}s) - {r['topic']}")

        # Rank by score (no threshold), take top 15-25
        final_results.sort(key=lambda x: x.get('final_score') or x.get('viral_score', 0), reverse=True)
        max_clips = 25
        if len(final_results) > max_clips:
            print(f"  [LIMIT] Selecting top {max_clips} by score from {len(final_results)}")
            final_results = final_results[:max_clips]

        if not final_results and results:
            print(f"  [WARN] Semua klip dihapus karena durasi tidak valid (<{min_d}s atau >{max_d}s).")

        # Sort chronologically for UI display
        final_results.sort(key=lambda x: x['start'])
        
        return final_results

    def generate_titles_for_selected(self):
        """Generate clickbait titles with OpenAI for selected (checked) clips."""
        if not self.parent.analysis_results:
            messagebox.showwarning("Peringatan", "Tidak ada segmen untuk diproses")
            return
        if not getattr(self.parent, "openai_available", False):
            messagebox.showwarning("Peringatan", "OpenAI tidak tersedia (tambahkan openai.txt)")
            return

        checked_segments = []
        for item_id in self.parent.results_tree.get_children():
            values = self.parent.results_tree.item(item_id)['values']
            if values and values[0] == '[X]':
                for result in self.parent.analysis_results:
                    if (f"{int(result['start']//60):02d}:{int(result['start']%60):02d}" == values[1] and
                        f"{int(result['end']//60):02d}:{int(result['end']%60):02d}" == values[2]):
                        checked_segments.append(result)
                        break
        if not checked_segments:
            messagebox.showwarning("Peringatan", "Silakan pilih setidaknya satu segmen")
            return
        if not messagebox.askyesno("Konfirmasi", f"Generate judul OpenAI untuk {len(checked_segments)} klip terpilih?"):
            return

        def task():
            total = len(checked_segments)
            existing = []
            for i, segment in enumerate(checked_segments):
                self.parent.progress_var.set(f"Generating title {i+1}/{total}...")
                self.parent.root.after(0, self.parent.root.update_idletasks)
                text = (segment.get('full_topic') or segment.get('topic') or '').strip()[:2000]
                if text:
                    cleaned = self._clean_filler_words(text)
                    title = self.parent.generate_clickbait_title(cleaned or text, existing_titles=existing, max_attempts=2, strict_content=True)
                    if title and title != "Untitled Clip":
                        segment['topic'] = title
                        segment['clickbait_title'] = title
                        existing.append(title)
            self.parent.progress_var.set("Selesai.")
            self.parent.root.after(0, self.parent.update_results_ui)
            self.parent.root.after(0, lambda: messagebox.showinfo("Berhasil", f"{total} judul berhasil di-generate."))
        import threading
        threading.Thread(target=task, daemon=True).start()


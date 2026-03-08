# Why OpenAI Is Not Being Used — Diagnosis

## 1. Where the pipeline runs

- **Smart path (OpenAI is supposed to run):**  
  `analysis_orchestrator` → `get_viral_segments_from_ai(transcript)` → inside that:  
  `rank_segments_with_openai(top_20)` → `rank_and_score_segments_openai(ordered)` → per-segment `generate_clickbait_title()`.

- **Fallback path (what you see in logs):**  
  When `get_viral_segments_from_ai` returns **None**, the orchestrator uses heatmap + `match_segments_with_content`, then runs **Step 5**:  
  `"Generating titles with AI in parallel (Fallback/Enhancement)"` → **only Groq/Gemini** (`generate_segment_titles_parallel`).  
  OpenAI is never called in this path.

So you see fallback logs when either:
- The **smart path** is never entered (e.g. no transcript / Groq returns no segments), or  
- The **smart path** is entered but **OpenAI client is not initialized**, so ranking and title functions return early and never call the API (and you may see "API key not found" instead of "Ranking segments with GPT-4o").

---

## 2. Condition that prevents OpenAI from being used

### 2.1 Client not initialized (`ai_engine.py`)

In `AIEngine.__init__`:

- `api_key = load_openai_key()`  
  If the key file is missing, unreadable, or empty, `api_key` is `None`.
- `if OPENAI_AVAILABLE and api_key:`  
  If the `openai` package is not installed, or `api_key` is `None`, we do **not** create the client.
- Then: `self._openai_client = None` and `self.openai_available = False`.

Every OpenAI function then does:

```python
if not self._openai_client or not self.openai_available:
    print("[OPENAI] API key not found, skipping ...")
    return ...
```

So **the condition that disables OpenAI is:**  
`not self._openai_client or not self.openai_available`  
(i.e. key not loaded or client not created).

### 2.2 Functions that are never actually calling the API

When the client is not initialized, these are **never** calling the OpenAI API (they return before the `create` call):

- **`rank_segments_with_openai`** — `ai_engine.py` ~491–493: returns `segments` unchanged, no API call.
- **`rank_and_score_segments_openai`** — ~521–523: returns `candidates` unchanged, no API call.
- **`generate_clickbait_title`** — ~382–385: returns `"Untitled Clip"`, no API call.
- **`refine_hook_with_openai`** — ~605–607: returns original hook, no API call.

So the **line of code that forces “no OpenAI”** in each case is the early return right after the check, e.g.:

- `ai_engine.py` line ~491–493:  
  `if not self._openai_client or not self.openai_available: ... return segments`
- Same pattern in the other three functions above.

### 2.3 Fallback path never uses OpenAI

In **`analysis_orchestrator.py`** line 311–314:

```python
if should_run_title_gen and (self.parent.gemini_available or self.parent.groq_available) and self.parent.analysis_results:
    print("\n[STEP 5] Generating titles with AI in parallel (Fallback/Enhancement)...")
    self.parent.generate_segment_titles_parallel()
```

- **`generate_segment_titles_parallel`** (in `ai_segment_analyzer.py`) uses only **Groq or Gemini**, not OpenAI.
- So the line that **forces fallback mode to never use OpenAI** is this one: we only call `generate_segment_titles_parallel()`, which does not call any OpenAI API.

`should_run_title_gen` is set to `False` only when `get_viral_segments_from_ai` returns segments (titles “already embedded”). So whenever you end up in Step 5, you are in “Fallback/Enhancement” and titles are generated only with Groq/Gemini.

---

## 3. Why you see “[FALLBACK LIMIT]” and “Fallback/Enhancement”

- **`[FALLBACK LIMIT]`** comes from **`subtitle_parser.py`** (segment limiting), not from the OpenAI vs Groq choice.
- **“Generating titles with AI in parallel (Fallback/Enhancement)”** is printed in **`analysis_orchestrator.py`** when:
  - `should_run_title_gen` is **True** (i.e. `get_viral_segments_from_ai` did **not** return segments, so we did not get “titles already embedded”), and  
  - Step 5 runs and calls **`generate_segment_titles_parallel`** (Groq/Gemini only).

So the pipeline is in “fallback” mode and **never** uses OpenAI for ranking or titles in that path.

---

## 4. Summary

| What | Why OpenAI is not used |
|------|-------------------------|
| **Condition that disables OpenAI** | `not self._openai_client or not self.openai_available` in `ai_engine.py` (key not loaded or client not created). |
| **Function that is never really used** | The **API call** inside `rank_segments_with_openai`, `rank_and_score_segments_openai`, `generate_clickbait_title`, `refine_hook_with_openai` is never executed when the client is None. |
| **Line that forces “no OpenAI”** | In each of those functions, the early `return` right after the `if not self._openai_client or not self.openai_available` check. |
| **Fallback path** | Step 5 only calls `generate_segment_titles_parallel()` (Groq/Gemini); there is no branch that uses OpenAI for titles in fallback mode. |

---

## 5. Required code changes (high level)

1. **Ensure `openai.txt` is read and client is created**  
   - More robust `load_openai_key()` (e.g. try project root and cwd).  
   - **Startup logs** so we can see: key loaded vs not, client created vs not.

2. **Always log when OpenAI is used**  
   - Keep/add:  
     - `print("[OPENAI] Ranking segments with GPT-4o")`  
     - `print("[OPENAI] Generating clickbait title")`  
   in the code paths that **actually** call the API (after the client check).

3. **Use OpenAI in fallback mode for titles**  
   - When `should_run_title_gen` is True, if `openai_available`: generate titles with OpenAI (e.g. loop and call `generate_clickbait_title`); else keep using `generate_segment_titles_parallel` (Groq/Gemini).

4. **Optional**  
   - In `get_viral_segments_from_ai`, if the client is None, log once that OpenAI is skipped so it’s clear why no `[OPENAI]` logs appear.

These changes ensure:  
- We can see from logs whether the key is loaded and the client is used.  
- Segment ranking, hook refinement, and clickbait title generation use OpenAI when the client is available, including in the fallback path.

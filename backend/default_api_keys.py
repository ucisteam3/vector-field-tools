"""
Default API (Groq) keys loaded from Pastebin - built-in, no user config.
Used when no other API keys are configured; displayed as "Default API" in UI.
"""
import urllib.request
import time

_DEFAULT_API_URL = "https://pastebin.com/raw/YRXAcAPP"
_cached_keys: list[str] | None = None
_cached_at: float = 0
_CACHE_SEC = 300  # 5 minutes


def get_default_api_keys() -> list[str]:
    """Fetch Groq API keys from Pastebin. Cached for 5 minutes. Returns list of non-empty lines."""
    global _cached_keys, _cached_at
    now = time.time()
    if _cached_keys is not None and (now - _cached_at) < _CACHE_SEC:
        return _cached_keys
    try:
        req = urllib.request.Request(_DEFAULT_API_URL, headers={"User-Agent": "HeatmapAnalyzer/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        keys = [line.strip() for line in raw.splitlines() if line.strip() and line.strip().startswith("gsk_")]
        _cached_keys = keys
        _cached_at = now
        return keys
    except Exception as e:
        if _cached_keys is not None:
            return _cached_keys
        print(f"[DEFAULT_API] Failed to fetch keys from Pastebin: {e}")
        return []


def is_default_api_available() -> bool:
    return len(get_default_api_keys()) > 0

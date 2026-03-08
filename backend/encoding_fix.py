"""Windows encoding fix - run early to prevent charmap errors.
Import and call apply() at process/thread start."""
import sys

_REPLACE = (
    ("\u2192", "->"),
    ("\u27a1", "->"),
    ("\u2713", "OK"),
    ("\u2714", "OK"),
    ("\u2717", "X"),
    ("\u26a0", "!"),
)


def _safe(s: str) -> str:
    for old, new in _REPLACE:
        s = s.replace(old, new)
    return s


class _SafeStream:
    def __init__(self, stream):
        self._stream = stream

    def write(self, s):
        if isinstance(s, str):
            s = _safe(s)
            try:
                self._stream.write(s)
            except UnicodeEncodeError:
                self._stream.write(s.encode("ascii", errors="replace").decode("ascii"))
        else:
            self._stream.write(s)

    def flush(self):
        self._stream.flush()

    def __getattr__(self, k):
        return getattr(self._stream, k)


def apply():
    """Apply safe stream wrapper. Idempotent - skips if already wrapped."""
    if hasattr(sys.stdout, "_stream"):
        return  # already wrapped
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            if sys.stderr is not sys.stdout:
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    try:
        sys.stdout = _SafeStream(sys.stdout)
        if sys.stderr is not sys.stdout:
            sys.stderr = _SafeStream(sys.stderr)
    except Exception:
        pass

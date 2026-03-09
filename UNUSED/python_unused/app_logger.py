"""
App Logger Module
Buffers log output and provides export to file for analysis log.
Web/headless: no GUI; export is no-op or can be done via API.
"""

import os
from datetime import datetime

END = "end"


def export_log_from_widget(text_widget, parent_window=None):
    """Export current log content from ScrolledText widget to a file. No-op when headless (no widget)."""
    if not text_widget:
        return
    try:
        exists = getattr(text_widget, "winfo_exists", lambda: False)()
    except Exception:
        exists = False
    if not exists:
        return
    try:
        content = text_widget.get("1.0", END).strip()
    except Exception:
        return
    if not content:
        return
    # Headless: no filedialog. Caller can write to a path from API.
    default_name = f"heatmap_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    # Optional: write to cwd if you want headless export
    # path = os.path.join(os.getcwd(), default_name)
    # with open(path, "w", encoding="utf-8") as f: f.write(content)
    return

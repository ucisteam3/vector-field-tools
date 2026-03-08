"""
App Logger Module
Buffers log output and provides export to file for analysis log.
"""

import tkinter as tk
from tkinter import filedialog, messagebox
import os
from datetime import datetime


def export_log_from_widget(text_widget, parent_window=None):
    """Export current log content from ScrolledText widget to a file."""
    if not text_widget or not text_widget.winfo_exists():
        messagebox.showwarning("Export Log", "Log tidak tersedia.")
        return
    content = text_widget.get("1.0", tk.END).strip()
    if not content:
        messagebox.showinfo("Export Log", "Log kosong. Jalankan analisis terlebih dahulu.")
        return
    default_name = f"heatmap_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    path = filedialog.asksaveasfilename(
        defaultextension=".txt",
        filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        initialfile=default_name,
        title="Simpan Log Analisis"
    )
    if path:
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            messagebox.showinfo("Berhasil", f"Log disimpan ke:\n{path}")
            if os.path.exists(path) and parent_window:
                try:
                    os.startfile(os.path.dirname(path))
                except Exception:
                    pass
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyimpan log: {e}")

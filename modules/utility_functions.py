"""
Utility Functions Module
Miscellaneous utility functions. Web/headless: no GUI dialogs.
"""

import os
import time

# Headless stubs (no messagebox/filedialog).
def _noop(*a, **k): pass
def _noop_filedialog(*a, **k): return None
messagebox = type("MB", (), {"showwarning": _noop, "showinfo": _noop, "showerror": _noop})()
filedialog = type("FD", (), {"askdirectory": lambda *a, **k: None})()
END = "end"


class UtilityFunctions:
    """Miscellaneous utility functions"""
    
    def __init__(self, parent):
        """Initialize Utility Functions"""
        self.parent = parent
    
    def export_ai_package(self):
        """Export current transcript and AI prompt to a folder. No-op when headless (no dialog)."""
        if not self.parent.analysis_results and not self.parent.video_path:
            messagebox.showwarning("Export Failed", "Lakukan analisis video terlebih dahulu!")
            return
        manual_box = getattr(self.parent, "manual_transcript_text", None)
        manual_text = manual_box.get("1.0", END).strip() if manual_box else ""
        try:
             if not manual_text:
                 messagebox.showwarning("Export Failed", "Transkrip kosong. Pastikan transkrip sudah dimuat/dihasilkan.")
                 return
                 
             # Choose a directory
             output_dir = filedialog.askdirectory(title="Pilih Folder untuk AI Package")
             if not output_dir:
                 return
                 
             video_id = "video_" + str(int(time.time()))
             if self.parent.video_path:
                 video_id = os.path.splitext(os.path.basename(self.parent.video_path))[0]
                 
             pkg_dir = os.path.join(output_dir, f"AI_PACKAGE_{self.parent._caption_safe_key(video_id)}")
             os.makedirs(pkg_dir, exist_ok=True)
             
             # Save transcript as SRT (Convert manual text if it's timestamps)
             # For simplicity, we just save the raw text as TRANSCRIPT.txt and also try to format as SRT
             with open(os.path.join(pkg_dir, "TRANSCRIPT.txt"), 'w', encoding='utf-8') as f:
                 f.write(manual_text)
                 
             # AI Prompt
             prompt = f"""Kamu adalah Viral Content Editor Pro. Tugasmu mencari "Golden Moments" (momen seru) dari transkrip video ini.

KRITERIA WAJIB:
- DURASI: Harus antara 30-90 detik.
- JUDUL: Buat judul deskriptif, menarik, dan SEO-friendly.
- KONTEKS: Ambil momen lucu, informatif, perdebatan, atau kejadian mendadak.

Format Output (WAJIB):
MM:SS - MM:SS | JUDUL KLIP | ALASAN

Transkrip:
{manual_text[:10000]}... (selebihnya dalam file)
"""
             with open(os.path.join(pkg_dir, "PROMPT_GPT_GEMINI.txt"), 'w', encoding='utf-8') as f:
                 f.write(prompt)
                 
             # README
             readme = """CARA PAKAI:
1. Upload file TRANSCRIPT.txt ke ChatGPT (GPT-4o) atau Gemini 1.5 Pro.
2. Copy isi file PROMPT_GPT_GEMINI.txt dan kirim ke AI.
3. Tunggu AI menghasilkan segmen.
4. Copy hasil dari AI (format MM:SS - MM:SS | Judul).
5. Paste ke kotak 'Manual Transcript' di aplikasi AutoClipper Heatmap.
6. Klik 'GAS!' untuk memproses klip tersebut.
"""
             with open(os.path.join(pkg_dir, "README.txt"), 'w', encoding='utf-8') as f:
                 f.write(readme)
                 
             print(f"  [SUCCESS] AI Package exported to: {pkg_dir}")
             messagebox.showinfo("Export Berhasil", f"Folder AI Package dibuat di:\n{pkg_dir}")
             if os.path.exists(pkg_dir):
                 os.startfile(pkg_dir)
             
        except Exception as e:
             messagebox.showerror("Error", f"Gagal mengekspor AI Package: {e}")

    def clear_results(self):
        """Clear all results"""
        for item in self.parent.results_tree.get_children():
            self.parent.results_tree.delete(item)
        self.parent.analysis_results = []
        self.parent.video_path = None
        self.parent.progress_var.set("Siap")


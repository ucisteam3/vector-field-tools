"""
Results Manager Module
Handles results UI updates, export, and clip download management
"""

import tkinter as tk
from tkinter import messagebox, filedialog
import json
import os
import threading


class ResultsManager:
    """Manages results display, export, and clip download operations"""
    
    def __init__(self, parent):
        """
        Initialize Results Manager
        
        Args:
            parent: Reference to YouTubeHeatmapAnalyzer instance
        """
        self.parent = parent
    
    
    def update_results_ui(self):
        """Update the results treeview with analysis results, statistik, dan rekomendasi"""
        # Clear existing items
        for item in self.parent.results_tree.get_children():
            self.parent.results_tree.delete(item)
        
        results = self.parent.analysis_results
        if not results:
            if getattr(self.parent, 'stats_total_label', None):
                self.parent.stats_total_label.config(text="Total: 0 klip")
            if getattr(self.parent, 'stats_avg_label', None):
                self.parent.stats_avg_label.config(text="Rata-rata: -")
            if getattr(self.parent, 'stats_recommended_label', None):
                self.parent.stats_recommended_label.config(text="")
            return
        
        # Urutkan sesuai pilihan (Skor / Durasi / Mulai) — default: viral score descending
        sort_by = getattr(self.parent, 'results_sort_var', None)
        sort_val = sort_by.get() if sort_by else "Skor"
        if sort_val == "Durasi":
            results = sorted(results, key=lambda r: r['duration'])
        elif sort_val == "Mulai":
            results = sorted(results, key=lambda r: r['start'])
        else:
            # Default: sort by final_score (or viral_score) descending — most viral first
            results = sorted(
                results,
                key=lambda r: r.get('final_score') if r.get('final_score') is not None else r.get('viral_score', r.get('virality_score', 0)),
                reverse=True
            )
        
        # Statistik
        total = len(results)
        durations = [r['duration'] for r in results]
        avg_d = sum(durations) / len(durations) if durations else 0
        min_d = min(durations) if durations else 0
        max_d = max(durations) if durations else 0
        
        if getattr(self.parent, 'stats_total_label', None):
            self.parent.stats_total_label.config(text=f"Total: {total} klip")
        if getattr(self.parent, 'stats_avg_label', None):
            self.parent.stats_avg_label.config(text=f"Rata-rata: {avg_d:.1f}s (min {min_d:.0f}s - max {max_d:.0f}s)")
        
        # Rekomendasi: urutkan berdasarkan activity (tinggi = rekomendasi)
        sorted_by_activity = sorted(results, key=lambda r: r.get('activity', 0), reverse=True)
        top3_starts = {self.parent.format_time(sorted_by_activity[i]['start']) for i in range(min(3, len(sorted_by_activity)))}
        if getattr(self.parent, 'stats_recommended_label', None):
            self.parent.stats_recommended_label.config(text="Top 3 Rekomendasi (by aktivitas)" if top3_starts else "")
        
        # Titles from OpenAI only; no legacy prefixes (Climax | YT Shorts | Hook)
        for result in results:
            start_str = self.parent.format_time(result['start'])
            end_str = self.parent.format_time(result['end'])
            duration_str = f"{result['duration']:.1f}s"
            hook_str = (result.get('hook_text') or result.get('hook_script') or '').strip()
            if len(hook_str) > 80:
                hook_str = hook_str[:77] + "..."
            title = (result.get('clickbait_title') or result.get('topic') or '').strip()
            # Prefer final_score (viral + hook combined); fallback to viral_score
            score_val = result.get('final_score')
            if score_val is None:
                score_val = result.get('viral_score', result.get('virality_score', 0))
            score_str = str(int(score_val)) if isinstance(score_val, (int, float)) else '0'
            self.parent.results_tree.insert("", tk.END, values=(
                "☐",
                start_str,
                end_str,
                duration_str,
                hook_str,
                title,
                score_str
            ))


    def on_tree_click(self, event):
        """Handle clicks on the treeview, specifically for the checkbox column"""
        region = self.parent.results_tree.identify_region(event.x, event.y)
        if region == "heading":
            column = self.parent.results_tree.identify_column(event.x)
            if column == "#1":  # Select column header
                # Toggle all based on current state of first item
                items = self.parent.results_tree.get_children()
                if not items: return
                
                first_val = self.parent.results_tree.item(items[0])['values'][0]
                new_val = "☐" if first_val == "☑" else "☑"
                
                for item in items:
                    vals = list(self.parent.results_tree.item(item)['values'])
                    vals[0] = new_val
                    self.parent.results_tree.item(item, values=vals)
        
        elif region == "cell":
            column = self.parent.results_tree.identify_column(event.x)
            item = self.parent.results_tree.identify_row(event.y)
            
            if column == "#1":  # Select column
                vals = list(self.parent.results_tree.item(item)['values'])
                vals[0] = "☑" if vals[0] == "☐" else "☐"
                self.parent.results_tree.item(item, values=vals)


    def select_all_segments(self):
        """Check all items in the treeview"""
        for item in self.parent.results_tree.get_children():
            vals = list(self.parent.results_tree.item(item)['values'])
            vals[0] = "☑"
            self.parent.results_tree.item(item, values=vals)


    def deselect_all_segments(self):
        """Uncheck all items in the treeview"""
        for item in self.parent.results_tree.get_children():
            vals = list(self.parent.results_tree.item(item)['values'])
            vals[0] = "☐"
            self.parent.results_tree.item(item, values=vals)

    
    def on_segment_select(self, event):
        """Handle segment selection to show details"""
        selection = self.parent.results_tree.selection()
        if not selection:
            return
        
        item = self.parent.results_tree.item(selection[0])
        values = item['values']
        
        # Find corresponding result
        start_str = values[1]  # Start index shifted by 1 due to checkbox column
        for result in self.parent.analysis_results:
            if self.parent.format_time(result['start']) == start_str:
                # Content: use SAME transcript source as clip export (VTT file first, then sub_transcriptions)
                content_text = ""
                analyzer = getattr(self.parent, "ai_segment_analyzer", None)
                if analyzer:
                    clip_start, clip_end = result["start"], result["end"]
                    # 1. Try VTT file (same source as clip export overlay) - ensures exact match
                    vtt_path = None
                    vid_path = getattr(self.parent, "video_path", None) or getattr(self.parent, "current_video_path", None)
                    if vid_path:
                        base = os.path.splitext(vid_path)[0]
                        for ext in [".id.vtt", ".vtt", ".en.vtt"]:
                            cand = base + ext
                            if os.path.exists(cand):
                                vtt_path = cand
                                break
                    if vtt_path:
                        content_text = analyzer.get_transcript_for_clip_from_vtt(clip_start, clip_end, vtt_path)
                    # 2. Fallback: sub_transcriptions (from parse_vtt, parse_manual_transcript, or JSON3)
                    if not content_text:
                        raw_cues = getattr(self.parent, "sub_transcriptions", None) or {}
                        content_text = analyzer._get_transcript_for_clip_range(clip_start, clip_end, raw_cues)
                if not content_text:
                    content_text = result.get("full_topic", "")

                details = f"Start Time: {self.parent.format_time(result['start'])}\n"
                details += f"End Time: {self.parent.format_time(result['end'])}\n"
                details += f"Duration: {result['duration']:.2f} seconds\n"
                details += f"Viral Score: {result.get('viral_score', 0)} | Hook Score: {result.get('hook_score', 0)} | Final: {result.get('final_score', 0)}\n"
                details += f"Activity Level: {result['activity']:.2f}\n\n"
                hook_3s = (result.get('hook_text') or result.get('hook_script', '')).strip()
                if hook_3s:
                    details += f"Hook (3 detik pertama):\n{hook_3s}\n\n"
                details += f"Content:\n{content_text}"

                self.parent.details_text.delete(1.0, tk.END)
                self.parent.details_text.insert(1.0, details)
                break

    
    def export_results(self):
        """Export results to JSON file"""
        if not self.parent.analysis_results:
            messagebox.showwarning("Peringatan", "Tidak ada hasil untuk diekspor")
            return
        
        filename = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Simpan Hasil Analisis"
        )
        
        if filename:
            try:
                export_data = {
                    'video_path': self.parent.video_path,
                    'segments': [
                        {
                            'start': r['start'],
                            'end': r['end'],
                            'duration': r['duration'],
                            'topic': r['full_topic'],
                            'activity': r['activity'],
                            'viral_score': r.get('viral_score', 0),
                            'hook_score': r.get('hook_score', 0),
                            'final_score': r.get('final_score', 0),
                            'clickbait_title': r.get('clickbait_title', r.get('topic', '')),
                            'hook_text': r.get('hook_text', r.get('hook_script', '')),
                        }
                        for r in self.parent.analysis_results
                    ]
                }
                
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
                
                messagebox.showinfo("Berhasil", f"Hasil berhasil diekspor ke {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Gagal mengekspor hasil: {str(e)}")

    
    def download_selected_clips(self):
        """Download clips for all checked segments in a background thread"""
        checked_segments = []
        for item_id in self.parent.results_tree.get_children():
            item = self.parent.results_tree.item(item_id)
            if item['values'][0] == "☑":
                start_str = item['values'][1]
                for result in self.parent.analysis_results:
                    if self.parent.format_time(result['start']) == start_str:
                        checked_segments.append(result)
                        break
        
        if not checked_segments:
            messagebox.showwarning("Peringatan", "Silakan pilih setidaknya satu segmen untuk diunduh")
            return
        
        if not self.parent.video_path or not os.path.exists(self.parent.video_path):
            messagebox.showerror("Kesalahan", "File video tidak ditemukan")
            return

        if len(checked_segments) > 1:
            if not messagebox.askyesno("Konfirmasi", f"Unduh {len(checked_segments)} klip terpilih?"):
                return

        # Use threading to prevent "Not Responding"
        self.parent.download_btn.config(state=tk.DISABLED)
        threading.Thread(target=self.parent._download_worker, args=(checked_segments,), daemon=True).start()


    def download_all_clips(self):
        """Download all clips in a background thread"""
        if not self.parent.analysis_results:
            messagebox.showwarning("Peringatan", "Tidak ada segmen untuk diunduh")
            return
        
        if not self.parent.video_path or not os.path.exists(self.parent.video_path):
            messagebox.showerror("Kesalahan", "File video tidak ditemukan")
            return
        
        if not messagebox.askyesno("Konfirmasi", f"Unduh semua {len(self.parent.analysis_results)} klip?"):
            return
            
        self.parent.download_btn.config(state=tk.DISABLED)
        threading.Thread(target=self.parent._download_worker, args=(self.parent.analysis_results,), daemon=True).start()


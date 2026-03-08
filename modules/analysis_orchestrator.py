"""
Analysis Orchestrator Module
Handles the main video analysis workflow orchestration
"""

import os
import tkinter as tk
from tkinter import messagebox
import json
import traceback

try:
    from modules.transcription_engine import WHISPER_AVAILABLE
except ImportError:
    WHISPER_AVAILABLE = False


class AnalysisOrchestrator:
    """Orchestrates the complete video analysis workflow"""
    
    def __init__(self, parent):
        """
        Initialize Analysis Orchestrator
        
        Args:
            parent: Reference to YouTubeHeatmapAnalyzer instance
        """
        self.parent = parent
    
    def start_analysis(self, url, genre="Auto-Detect", style="Auto-Detect", use_gpu=False, use_voiceover=False):
        import traceback # FIX UnboundLocalError
        self.parent.sub_transcriptions = {} # [FIX] Clear stale subtitle data from previous runs
        self.parent.is_analyzing = True
        self.parent.download_btn.config(state='disabled')
        self.parent.progress_bar.start()
        
        # [INFO] Store params for reference
        print(f"[ORCHESTRATOR] Starting analysis: {genre} | {style} | GPU: {use_gpu}")

        # Clear previous results automatically
        self.parent.root.after(0, self.parent.clear_results)
        
        try:
            print("\n" + "="*60)
            print("Starting Video Analysis")
            print("="*60)
            print(f"URL: {url}\n")
            
            # Step 1: Check Mode (Local vs URL)
            if self.parent.local_video_mode:
                print(f"[STEP 1] Menggunakan File Lokal: {url}")
                self.parent.progress_var.set("Mode Lokal: Menggunakan video dari disk...")
                video_path = url # Input is already the file path
                
                # Validation
                if not os.path.exists(video_path):
                    raise Exception("File video tidak ditemukan!")
                self.parent.video_path = video_path
                self.parent.current_video_path = video_path

                # Warn if manual transcript is missing in local mode
                manual_text = self.parent.manual_transcript_text.get("1.0", tk.END).strip()
                if not manual_text:
                    # If Whisper is available, don't scare user, just proceed to fallback
                    if WHISPER_AVAILABLE:
                        print("  [INFO] Transkrip kosong, akan menggunakan Whisper Otomatis.")
                    else:
                        if not messagebox.askyesno("Peringatan Transkrip", "Mode File Lokal butuh Transkrip Manual!\nKotak transkrip kosong dan Whisper tidak terinstall.\nLanjut tanpa teks (Cuma Visual)?"):
                            self.parent.is_analyzing = False
                            self.parent.download_btn.config(state='normal')
                            self.parent.progress_bar.stop()
                            return
            else:
                # Step 1: Download video (URL Mode)
                print("[STEP 1] Mengunduh video...")
                self.parent.progress_var.set("Sedang mengunduh video dari YouTube...")
                video_path = self.parent.download_youtube_video(url)
            
            if not video_path:
                raise Exception("Gagal mengunduh video")
            
            print(f"[SUCCESS] Video diunduh: {video_path}")
            self.parent.video_path = video_path
            self.parent.current_video_path = video_path

            # Download subtitles separately (if enabled)
            if not self.parent.local_video_mode:
                self.parent.download_subtitles_only(url, video_path)
            
            # Step 2 & 3: FAST MODE Check (Prioritize Manual Transcript)
            transcriptions = {}
            manual_text = self.parent.manual_transcript_text.get("1.0", tk.END).strip()

            # [MODE] Structured Segments Check
            if manual_text and ("|" in manual_text or "-" in manual_text):
                 guessed_segments = self.parent.parse_structured_segments(manual_text)
                 if guessed_segments and len(guessed_segments) > 0:
                     print(f"  [MODE] Segment Terstruktur Terdeteksi ({len(guessed_segments)} klip). Bypass Heatmap!")
                     self.parent.analysis_results = guessed_segments
                     # Need to populate Treeview and cleanup
                     self.parent.root.after(0, self.parent.update_results_ui)
                     self.parent.progress_var.set("Berhasil memuat segmen manual.")
                     self.parent.is_analyzing = False
                     self.parent.download_btn.config(state='normal')
                     self.parent.progress_bar.stop()
                     return 
            
            
            # [SMART] Sidecar Caching (Start) - Optimized Discovery
            # ALWAYS check for sidecar after download_subtitles_only
            if not manual_text:
                print("  [SMART] Mencari sidecar captions (SRT/VTT/Words)...")
                sidecar = self.parent.find_sidecar_caption(video_path)
                if sidecar['found']:
                    print(f"  [SUCCESS] Sidecar ditemukan: {os.path.basename(sidecar['path'])}")
                    
                    sub_transcriptions = None
                    
                    # Handle different sidecar types
                    if sidecar['kind'] == 'words_json':
                        # Load words.json and convert to transcription format
                        import traceback
                        try:
                            print(f"  [DEBUG] Loading JSON from: {sidecar['path']}")
                            with open(sidecar['path'], 'r', encoding='utf-8') as f:
                                words_data = json.load(f)
                            
                            print(f"  [DEBUG] JSON loaded, type: {type(words_data)}, has 'words' key: {'words' in words_data if isinstance(words_data, dict) else False}")
                            
                            sub_transcriptions = {}
                            
                            # Handle competitor format: {"version": 1, "words": [...]}
                            if isinstance(words_data, dict) and 'words' in words_data:
                                print(f"  [DEBUG] Using competitor format (words array)")
                                for idx, w in enumerate(words_data['words']):
                                    sub_transcriptions[idx] = {
                                        'start': w.get('s') or w.get('start'),
                                        'end': w.get('e') or w.get('end'),
                                        'text': w.get('t') or w.get('text')
                                    }
                            # Handle our format: {"0": {"start": ..., "end": ..., "text": ...}, ...}
                            elif isinstance(words_data, dict):
                                print(f"  [DEBUG] Using our format (dict with string keys)")
                                for k, v in words_data.items():
                                    try:
                                        int_key = int(k)
                                        sub_transcriptions[int_key] = v
                                    except (ValueError, TypeError):
                                        # If key is not convertible, use as-is
                                        sub_transcriptions[k] = v
                            
                            print(f"  [INFO] Loaded {len(sub_transcriptions)} entries from words.json")
                        except Exception as e:
                            print(f"  [ERROR] Gagal load words.json: {e}")
                            traceback.print_exc()
                    else:
                        # For SRT/VTT files
                        sub_transcriptions = self.parent.parse_vtt(sidecar['path'])
                    
                    # FALLBACK: If words.json failed, try .srt file
                    if not sub_transcriptions or len(sub_transcriptions) == 0:
                        if sidecar['kind'] == 'words_json':
                            print(f"  [WARN] words.json parsing failed, trying .srt fallback...")
                            srt_path = sidecar['path'].replace('.words.json', '.srt')
                            if os.path.exists(srt_path):
                                print(f"  [INFO] Found SRT fallback: {os.path.basename(srt_path)}")
                                sub_transcriptions = self.parent.parse_vtt(srt_path)
                    
                    if sub_transcriptions and len(sub_transcriptions) > 0:
                        self.parent.sub_transcriptions = sub_transcriptions
                        print(f"  [DEBUG] sub_transcriptions has {len(sub_transcriptions)} entries")
                        # Populate the box for visibility
                        formatted_text = ""
                        try:
                            for _, data in sorted(sub_transcriptions.items()):
                                if isinstance(data, dict) and 'start' in data and 'text' in data:
                                    time_str = self.parent.format_time(data['start'])
                                    formatted_text += f"{time_str} {data['text']}\n"
                            
                            print(f"  [DEBUG] formatted_text length: {len(formatted_text)}")
                            
                            if formatted_text:
                                def _update_ui(t):
                                    self.parent.manual_transcript_text.delete("1.0", tk.END)
                                    self.parent.manual_transcript_text.insert(tk.END, t)
                                
                                self.parent.root.after(0, lambda: _update_ui(formatted_text))
                                manual_text = formatted_text
                                print(f"  [INFO] Berhasil memuat {len(sub_transcriptions)} baris subtitle dari sidecar.")
                            else:
                                print(f"  [WARN] formatted_text is empty after processing")
                        except Exception as e:
                            print(f"  [ERROR] Error formatting subtitle text: {e}")
                            import traceback
                            traceback.print_exc()
                    else:
                        print(f"  [WARN] sub_transcriptions is empty or None")
            
            # [AUTOCLIP STYLE] Sidecar Caching (Start)
            # Check for [video].srt or .words.json before transcribing

            # [WHISPER FALLBACK] DISABLED - User requested to completely disable Whisper
            # if not manual_text:
            #     print("[SMART] Transkrip manual kosong. Mencoba Whisper Offline...")
            #     whisper_text = self.parent.transcribe_video_with_whisper(video_path)
            #     if whisper_text:
            #         manual_text = whisper_text
            #         print("[WHISPER SUCCESS] Menggunakan hasil transkripsi AI Offline.")
            #         
            #         # [SMART] Update UI box with Whisper result
            #         def _update_ui_whisper(t):
            #             self.parent.manual_transcript_text.delete("1.0", tk.END)
            #             self.parent.manual_transcript_text.insert(tk.END, t)
            #         self.parent.root.after(0, lambda: _update_ui_whisper(manual_text))
            #         
            #         # [AUTOCLIP STYLE] Sidecar Saving (Immediate Dump)
            #         try:
            #             base_filename = os.path.splitext(video_path)[0]
            #             sidecar_srt = base_filename + ".srt"
            #             sidecar_json = base_filename + ".words.json"
            #             
            #             print(f"  > Saving SRT & JSON sidecars...")
            #             with open(sidecar_srt, 'w', encoding='utf-8') as f:
            #                 f.write(manual_text) 
            #             
            #             with open(sidecar_json, 'w', encoding='utf-8') as f:
            #                 json.dump([{'word': w} for w in manual_text.split()], f)
            #                 
            #         except Exception as e:
            #             print(f"  [WARN] Gagal simpan sidecar: {e}")
            
            # Fallback flag: If True, we must generate titles in Step 5
            should_run_title_gen = True

            if manual_text:
                print("\n[FAST MODE] Transkrip manual/AI terdeteksi! Melewati scanning visual...")
                self.parent.progress_var.set("Mode Cepat: Memproses transkrip manual...")
                
                # [HOOK 3s] Jika belum ada sub_transcriptions (no sidecar), coba parse manual untuk deteksi hook
                if not getattr(self.parent, 'sub_transcriptions', None) or not self.parent.sub_transcriptions:
                    parsed_chunks = self.parent.parse_manual_transcript(manual_text)
                    if parsed_chunks:
                        self.parent.sub_transcriptions = parsed_chunks
                        print(f"  [HOOK 3s] Memakai {len(parsed_chunks)} chunk transkrip untuk deteksi hook 3 detik pertama.")
                
                # Try AI Viral Segmentation first (dengan keyword/trend jika diisi)
                keyword = getattr(self.parent, 'trend_keyword_var', None)
                kw_val = keyword.get().strip() if keyword else ""
                ai_viral_segments = self.parent.get_viral_segments_from_ai(manual_text, keyword=kw_val if kw_val else None)
                
                if ai_viral_segments:
                    transcriptions = ai_viral_segments
                    print(f"[SMART MODE] AI Editor menemukan {len(transcriptions)} segmen viral.")
                    should_run_title_gen = False # Titles are already embedded!
                else:
                    # Silence fallback message
                    transcriptions = self.parent.parse_manual_transcript(manual_text)
                
                # Generate heatmap segments from whatever transcription we have
                heatmap_segments = []
                for _, t in transcriptions.items():
                    heatmap_segments.append({
                        'start': t['start'],
                        'end': t['end'],
                        'avg_activity': 0.95 
                    })
                print(f"[SUCCESS] {len(heatmap_segments)} segmen analisis siap.")
                
            else:
                # [AI-FIRST GATEKEEPER MODE]
                # Competitor Logic: Transcript -> AI -> Segments (Skip Visual Heatmap)
                print("\n[STEP 2] AI-First Analysis (Gatekeeper Mode)...")
                
                # A. Get Transcription First
                print("  [INFO] Extracting full transcript for AI analysis...")
                self.parent.progress_var.set("Mengekstrak audio dan transkripsi AI...")
                
                # Try download/extract
                audio_path = self.parent.download_youtube_audio(url)
                if audio_path and os.path.exists(audio_path):
                    transcriptions = self.parent.transcribe_audio_file(audio_path)
                else:
                    transcriptions = self.parent.extract_audio_and_transcribe(video_path)
                
                # [HOOK 3s] Simpan transkrip untuk deteksi hook 3 detik pertama di tiap klip
                if transcriptions:
                    self.parent.sub_transcriptions = transcriptions
                
                # B. OpenAI-only: detect viral segments (clip selection)
                if transcriptions and getattr(self.parent, "openai_available", False):
                    print("  [AI START] Mengirim transkrip ke OpenAI (GPT-4o)...")
                    self.parent.progress_var.set("OpenAI sedang mendeteksi momen viral...")
                    kw_val = (self.parent.trend_keyword_var.get() or "").strip() if getattr(self.parent, "trend_keyword_var", None) else ""
                    ai_segments = self.parent.get_viral_segments_from_ai(transcriptions, keyword=kw_val or None)
                    if ai_segments:
                        print(f"[AI SUCCESS] OpenAI menemukan {len(ai_segments)} Golden Moments!")
                        heatmap_segments = []
                        for _, t in ai_segments.items():
                            heatmap_segments.append({
                                "start": t["start"],
                                "end": t["end"],
                                "avg_activity": 0.99,
                            })
                        transcriptions = ai_segments
                        should_run_title_gen = False
                    else:
                        print("[AI FAIL] OpenAI tidak mengembalikan segmen. Fallback ke Visual Heatmap.")
                        heatmap_segments = self.parent.analyze_video_heatmap(video_path)
                else:
                    if not transcriptions:
                        print("[INFO] Transkripsi kosong/gagal. Fallback ke Visual Heatmap.")
                    else:
                        print("[INFO] OpenAI tidak tersedia (openai.txt). Fallback ke Visual Heatmap.")
                    heatmap_segments = self.parent.analyze_video_heatmap(video_path)

            self.parent.analysis_results = self.parent.match_segments_with_content(heatmap_segments, transcriptions)
            print(f"[SUCCESS] Matched {len(self.parent.analysis_results)} segments")
            
            # Step 5: Title generation (OpenAI only)
            if should_run_title_gen and self.parent.analysis_results:
                if getattr(self.parent, "openai_available", False):
                    print("\n[STEP 5] [OPENAI] Generating titles...")
                    self.parent.generate_segment_titles_parallel()
                    print("[OPENAI] Generating titles complete")
                else:
                    print("\n[STEP 5] No OpenAI key (openai.txt). Skip title generation.")
            else:
                print("\n[STEP 5] Titles already from OpenAI pipeline.")
            
            # Step 6: Update UI
            print("\n[STEP 6] Updating UI...")
            self.parent.root.after(0, self.parent.update_results_ui)
            self.parent.progress_var.set("Analysis complete!")
            print("\n" + "="*60)
            print("Analysis Complete!")
            print("="*60 + "\n")
            
        except Exception as e:
            error_msg = str(e)
            print("\n" + "="*60)
            print("ERROR OCCURRED!")
            print("="*60)
            print(f"Error Message: {error_msg}")
            print("\nFull Traceback:")
            traceback.print_exc()
            print("="*60 + "\n")
            
            self.parent.root.after(0, lambda msg=error_msg: messagebox.showerror("Error", f"Analysis failed: {msg}"))
            self.parent.progress_var.set(f"Error: {error_msg}")
        finally:
            self.parent.is_analyzing = False
            self.parent.download_btn.config(state='normal')
            self.parent.progress_bar.stop()


"""
UI Setup Module
Handles setup of all UI tabs (Analysis, Settings, Customize)
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog, colorchooser
import os

from modules.preview_engine import render_subtitle_preview
from modules.ui_components import ModernButton
from modules.font_manager import load_fonts_from_folder
from modules.accordion_widget import AccordionSection


class UISetup:
    """Manages UI setup for all application tabs"""
    
    def __init__(self, parent):
        """
        Initialize UI Setup
        
        Args:
            parent: Reference to YouTubeHeatmapAnalyzer instance for accessing widgets and settings
        """
        self.parent = parent
    
    def setup_analysis_tab(self):
        # Configure weights for the tab frame itself
        self.parent.analysis_tab.columnconfigure(0, weight=1)
        self.parent.analysis_tab.rowconfigure(0, weight=1)
        
        # Container for analysis tab
        main_frame = ttk.Frame(self.parent.analysis_tab, style='Dark.TFrame', padding="20")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configure weights for the main container
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1) # Results section expands
        main_frame.rowconfigure(0, weight=0) # Top stays compact
        main_frame.rowconfigure(1, weight=0) # Progress stays compact
        
        # Middle Section: Two Columns for URL and Manual Transcript
        middle_container = ttk.Frame(main_frame, style='Dark.TFrame')
        middle_container.grid(row=0, column=0, columnspan=2, sticky="nsew", pady=5)
        middle_container.columnconfigure(0, weight=1)
        middle_container.columnconfigure(1, weight=1)

        # URL Input Section (Column 0)
        url_frame = ttk.LabelFrame(middle_container, text=" URL Video YouTube ", style='Dark.TLabelframe', padding="15")
        url_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        url_frame.columnconfigure(0, weight=1)

        # Row 0: URL + Browse
        input_row = ttk.Frame(url_frame, style='Dark.TFrame')
        input_row.grid(row=0, column=0, sticky="ew", pady=5)
        input_row.columnconfigure(0, weight=1)
        
        self.parent.url_entry = ttk.Entry(input_row, style='Dark.TEntry')
        self.parent.url_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        ModernButton(input_row, text="📂 Browse", 
                    command=self.parent.browse_local_file, width=100, radius=12,
                    bg_color="#444444", hover_color="#666666").grid(row=0, column=1, padx=5)
        
        self.parent.download_btn = ModernButton(input_row, text="GAS!", 
                    command=lambda: self.parent.start_analysis_thread(), width=100,
                    bg_color=self.parent.accent_blue, hover_color="#2980b9")
        self.parent.download_btn.grid(row=0, column=2, padx=(5, 0))
        
        # Video Info Section (Metadata)
        info_frame = ttk.Frame(url_frame, style='Dark.TFrame')
        info_frame.grid(row=1, column=0, sticky="w", pady=(5, 10))
        
        # Title Label
        title_container = ttk.Frame(info_frame, style='Dark.TFrame')
        title_container.pack(anchor="w", pady=2)
        ttk.Label(title_container, text="Judul  :", style='Dark.TLabel', width=10).pack(side=tk.LEFT)
        self.parent.video_title_label = ttk.Label(title_container, text="-", style='Highlight.TLabel', font=('Segoe UI', 10, 'bold'))
        self.parent.video_title_label.pack(side=tk.LEFT)
        
        # Channel Label
        channel_container = ttk.Frame(info_frame, style='Dark.TFrame')
        channel_container.pack(anchor="w", pady=2)
        ttk.Label(channel_container, text="Channel :", style='Dark.TLabel', width=10).pack(side=tk.LEFT)
        self.parent.channel_name_label = ttk.Label(channel_container, text="-", style='Highlight.TLabel')
        self.parent.channel_name_label.pack(side=tk.LEFT)

        # Row 2: Checkboxes (Moved inside)
        checks_row = ttk.Frame(url_frame, style='Dark.TFrame')
        checks_row.grid(row=2, column=0, sticky="w", pady=(0, 5))
        
        encoder_label = getattr(self.parent, 'best_encoder_name', "Detecting...")
        ttk.Checkbutton(checks_row, text=f"Hardware Acc ({encoder_label})", style='Dark.TCheckbutton', 
                        variable=self.parent.gpu_var).pack(side=tk.LEFT, padx=(0, 10))

        self.parent.voiceover_btn = ttk.Checkbutton(checks_row, text="AI Voice Over Hook", style='Dark.TCheckbutton', 
                                            variable=self.parent.use_voiceover_var)
        self.parent.voiceover_btn.pack(side=tk.LEFT, padx=10)

        # Trend / Keyword (opsional - bias AI ke niche)
        keyword_row = ttk.Frame(url_frame, style='Dark.TFrame')
        keyword_row.grid(row=3, column=0, sticky="ew", pady=(5, 0))
        keyword_row.columnconfigure(1, weight=1)
        ttk.Label(keyword_row, text="Trend/Keyword:", style='Dark.TLabel', width=12).grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self.parent.trend_keyword_entry = ttk.Entry(keyword_row, style='Dark.TEntry', textvariable=self.parent.trend_keyword_var, width=30)
        self.parent.trend_keyword_entry.grid(row=0, column=1, sticky="ew", padx=5)
        ttk.Label(keyword_row, text="(opsional, contoh: investasi, komedi)", style='Dark.TLabel').grid(row=0, column=2, sticky=tk.W)

        # Manual Transcript Section (Column 1)
        manual_frame = ttk.LabelFrame(middle_container, text=" Transkrip Manual (Opsional) ", 
                                     style='Dark.TLabelframe', padding="15")
        manual_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        self.parent.manual_transcript_text = scrolledtext.ScrolledText(manual_frame, wrap=tk.WORD, height=6,
                                                            bg=self.parent.bg_darker, fg=self.parent.fg_light,
                                                            insertbackground=self.parent.fg_light,
                                                            font=('Segoe UI', 9), borderwidth=0)
        self.parent.manual_transcript_text.pack(expand=True, fill='both', pady=(0, 10))
        
        # Manual Action Buttons
        manual_btn_frame = ttk.Frame(manual_frame, style='Dark.TFrame')
        manual_btn_frame.pack(anchor=tk.E)

        ModernButton(manual_btn_frame, text="📦 Export AI Package", width=180, radius=15,
                    bg_color="#7928ca", hover_color="#904ce0", fg_color="white",
                    command=self.parent.export_ai_package).pack(side=tk.LEFT, padx=5)

        ModernButton(manual_btn_frame, text=" Hapus Transkrip", width=160, radius=15,
                    bg_color="#cc0000", hover_color="#ff3333", fg_color="white",
                    command=lambda: self.parent.manual_transcript_text.delete("1.0", tk.END)).pack(side=tk.LEFT, padx=5)

        # Progress Section (Row 1 - Compact)
        progress_frame = ttk.Frame(main_frame, style='Dark.TFrame')
        progress_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)
        
        self.parent.progress_var = tk.StringVar(value="Siap dijalankan")
        ttk.Label(progress_frame, textvariable=self.parent.progress_var, style='Dark.TLabel').pack(side=tk.LEFT, padx=5)
        
        self.parent.progress_bar = ttk.Progressbar(progress_frame, mode='indeterminate', 
                                           style='Modern.Horizontal.TProgressbar')
        self.parent.progress_bar.pack(side=tk.LEFT, expand=True, fill='x', padx=10)

        # Results Section (Row 2 - Expanding)
        results_frame = ttk.LabelFrame(main_frame, text=" Hasil Analisis Video ", style='Dark.TLabelframe', padding="15")
        results_frame.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=5)
        
        # Left side - Heatmap segments
        left_frame = ttk.Frame(results_frame, style='Dark.TFrame')
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 10))
        
        # Right side - Details
        right_frame = ttk.Frame(results_frame, style='Dark.TFrame')
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(10, 0))
        
        # Pengaturan Export di depan (Mode + toggles cepat)
        export_toggles_frame = ttk.LabelFrame(right_frame, text=" Pengaturan Export ", style='Dark.TFrame', padding=8)
        export_toggles_frame.pack(fill='x', pady=(0, 8))
        # Mode: Landscape Fit / Face Tracking (paling atas)
        export_mode_display = ["Landscape Fit (Blur Background)", "Face Tracking (9:16 Crop)"]
        export_mode_internal = {"Landscape Fit (Blur Background)": "landscape_fit", "Face Tracking (9:16 Crop)": "face_tracking"}
        export_mode_reverse = {v: k for k, v in export_mode_internal.items()}
        mode_row = ttk.Frame(export_toggles_frame, style='Dark.TFrame')
        mode_row.pack(fill='x', pady=(0, 6))
        ttk.Label(mode_row, text="Mode:", style='Dark.TLabel', width=6).pack(side=tk.LEFT)
        current_export = self.parent.export_mode_var.get()
        mode_display_var = tk.StringVar(value=export_mode_reverse.get(current_export, export_mode_display[0]))
        mode_combo = ttk.Combobox(mode_row, textvariable=mode_display_var, values=export_mode_display,
                                  state='readonly', style='Dark.TCombobox', width=28)
        mode_combo.pack(side=tk.LEFT, fill='x', expand=True, padx=(4, 0))
        def _on_export_mode_change(event=None):
            val = export_mode_internal.get(mode_display_var.get(), "landscape_fit")
            self.parent.export_mode_var.set(val)
            self.parent.save_custom_settings()
        mode_combo.bind('<<ComboboxSelected>>', _on_export_mode_change)
        tk.Checkbutton(export_toggles_frame, text="Dynamic Zoom", variable=self.parent.dynamic_zoom_var,
                       command=self.parent.save_custom_settings, bg='#2b2b2b', fg='white', selectcolor='#2b2b2b',
                       activebackground='#2b2b2b', activeforeground='white', font=('Segoe UI', 9), cursor='hand2').pack(anchor=tk.W)
        tk.Checkbutton(export_toggles_frame, text="Audio Pitch", variable=self.parent.audio_pitch_var,
                       command=self.parent.save_custom_settings, bg='#2b2b2b', fg='white', selectcolor='#2b2b2b',
                       activebackground='#2b2b2b', activeforeground='white', font=('Segoe UI', 9), cursor='hand2').pack(anchor=tk.W)
        tk.Checkbutton(export_toggles_frame, text="Flip Video (Mirror)", variable=self.parent.video_flip_var,
                       command=self.parent.save_custom_settings, bg='#2b2b2b', fg='white', selectcolor='#2b2b2b',
                       activebackground='#2b2b2b', activeforeground='white', font=('Segoe UI', 9), cursor='hand2').pack(anchor=tk.W)
        
        log_header = ttk.Frame(right_frame, style='Dark.TFrame')
        log_header.pack(anchor=tk.W, fill='x', pady=(0, 8))
        ttk.Label(log_header, text="Log Sistem & Detail Analisis:", style='Title.TLabel').pack(side=tk.LEFT)
        from modules.app_logger import export_log_from_widget
        ModernButton(log_header, text="Export Log", width=110, height=28, radius=10,
                    bg_color=self.parent.bg_lighter, hover_color="#30363d", fg_color=self.parent.fg_light,
                    command=lambda: export_log_from_widget(self.parent.details_text, self.parent.root)).pack(side=tk.RIGHT, padx=5)
        
        self.parent.details_text = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, width=45, height=20,
                                                   bg=self.parent.bg_darker, fg=self.parent.fg_light,
                                                   insertbackground=self.parent.fg_light,
                                                   font=('Segoe UI', 10), borderwidth=0)
        self.parent.details_text.pack(expand=True, fill='both')
        
        # Configure results_frame weights to split space
        results_frame.columnconfigure(0, weight=3) # Table gets more space
        results_frame.columnconfigure(1, weight=2) # Details gets less
        
        # Statistik & Rekomendasi
        stats_frame = ttk.Frame(left_frame, style='Dark.TFrame')
        stats_frame.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        stats_frame.columnconfigure(1, weight=1)
        self.parent.stats_total_label = ttk.Label(stats_frame, text="Total: 0 klip", style='Dark.TLabel')
        self.parent.stats_total_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 15))
        self.parent.stats_avg_label = ttk.Label(stats_frame, text="Rata-rata: -", style='Dark.TLabel')
        self.parent.stats_avg_label.grid(row=0, column=1, sticky=tk.W, padx=(0, 15))
        self.parent.stats_recommended_label = ttk.Label(stats_frame, text="", style='Title.TLabel')
        self.parent.stats_recommended_label.grid(row=0, column=2, sticky=tk.W)
        
        header_row = ttk.Frame(left_frame, style='Dark.TFrame')
        header_row.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        header_row.columnconfigure(0, weight=1)
        ttk.Label(header_row, text="Golden Moment Terdeteksi:", style='Title.TLabel').pack(side=tk.LEFT)
        
        # Add Select All / Deselect All at the top of treeview
        tree_btns_frame = tk.Frame(header_row, bg=self.parent.bg_dark)
        tree_btns_frame.pack(side=tk.RIGHT)
        ttk.Label(tree_btns_frame, text="Urut:", style='Dark.TLabel').pack(side=tk.LEFT, padx=(0, 4))
        sort_combo = ttk.Combobox(tree_btns_frame, textvariable=self.parent.results_sort_var,
                                 values=["Skor", "Durasi", "Mulai"], state="readonly", width=10, style='Dark.TCombobox')
        sort_combo.pack(side=tk.LEFT, padx=(0, 8))
        def on_sort_change(*args):
            if getattr(self.parent, 'results_manager', None):
                self.parent.results_manager.update_results_ui()
        self.parent.results_sort_var.trace_add("write", on_sort_change)
        ModernButton(tree_btns_frame, text="Centang Semua", 
                    command=self.parent.select_all_segments, width=140, height=30, radius=15).pack(side=tk.LEFT, padx=5)
        ModernButton(tree_btns_frame, text="Hapus Centang", 
                    command=self.parent.deselect_all_segments, width=140, height=30, radius=15).pack(side=tk.LEFT, padx=5)
        ModernButton(tree_btns_frame, text="Bersihkan", 
                    command=self.parent.clear_results, width=140, height=30, radius=15, bg_color="#cc0000", hover_color="#ff3333", fg_color="white").pack(side=tk.LEFT, padx=5)

        # Treeview for results: START | END | HOOK | TITLE | SCORE
        columns = ("Select", "Start", "End", "Duration", "Hook", "Title", "Score")
        self.parent.results_tree = ttk.Treeview(left_frame, columns=columns, show="headings",
                                        style='Dark.Treeview', height=15)
        self.parent.results_tree.heading("Select", text="☑")
        self.parent.results_tree.heading("Start", text="MULAI")
        self.parent.results_tree.heading("End", text="SELESAI")
        self.parent.results_tree.heading("Duration", text="DURASI")
        self.parent.results_tree.heading("Hook", text="HOOK")
        self.parent.results_tree.heading("Title", text="TITLE")
        self.parent.results_tree.heading("Score", text="SCORE")
        self.parent.results_tree.column("Select", width=40, anchor=tk.CENTER)
        self.parent.results_tree.column("Start", width=80, anchor=tk.CENTER)
        self.parent.results_tree.column("End", width=80, anchor=tk.CENTER)
        self.parent.results_tree.column("Duration", width=70, anchor=tk.CENTER)
        self.parent.results_tree.column("Hook", width=280)
        self.parent.results_tree.column("Title", width=320)
        self.parent.results_tree.column("Score", width=55, anchor=tk.CENTER)

        # Ensure treeview fills space correctly
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(2, weight=1)
        results_frame.rowconfigure(0, weight=1)
        
        scrollbar_y = ttk.Scrollbar(left_frame, orient=tk.VERTICAL, 
                                   style='Dark.Vertical.TScrollbar',
                                   command=self.parent.results_tree.yview)
        scrollbar_y.grid(row=2, column=1, sticky=(tk.N, tk.S))
        self.parent.results_tree.configure(yscrollcommand=scrollbar_y.set)
        
        self.parent.results_tree.grid(row=2, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Bind double click for preview
        self.parent.results_tree.bind("<Double-1>", lambda e: self.parent.preview_selected_segment())
        self.parent.results_tree.bind("<<TreeviewSelect>>", self.parent.on_segment_select)
        self.parent.results_tree.bind("<Button-1>", self.parent.on_tree_click)
        
        # Action Buttons at the bottom
        actions_frame = tk.Frame(left_frame, bg=self.parent.bg_dark)
        actions_frame.grid(row=3, column=0, columnspan=2, pady=(15, 0), sticky=tk.W)
        
        self.parent.preview_btn = ModernButton(actions_frame, text="▶ Putar Video", 
                                      command=self.parent.preview_selected_segment, width=160, height=45)
        self.parent.preview_btn.pack(side=tk.LEFT, padx=(0, 15))
        ModernButton(actions_frame, text="🖼 Thumbnail", width=120, height=45,
                    command=self.parent.save_thumbnail_for_segment,
                    bg_color=self.parent.bg_lighter, hover_color="#30363d", fg_color=self.parent.fg_light).pack(side=tk.LEFT, padx=(0, 15))
        
        self.parent.download_selected_btn = ModernButton(actions_frame, text="📥 Download Terpilih", 
                                                command=self.parent.download_selected_clips, width=180, height=45,
                                                bg_color=self.parent.accent_green, hover_color="#4fd160")
        self.parent.download_selected_btn.pack(side=tk.LEFT, padx=15)
        
        self.parent.download_all_btn = ModernButton(actions_frame, text="📦 Download Semua", 
                                           command=self.parent.download_all_clips, width=180, height=45,
                                           bg_color="#7928ca", hover_color="#904ce0")
        self.parent.download_all_btn.pack(side=tk.LEFT, padx=15)
        
        def open_clips_folder():
            if not os.path.exists("clips"):
                os.makedirs("clips", exist_ok=True)
            os.startfile("clips")
        ModernButton(actions_frame, text="📁 Buka Folder", 
                    command=open_clips_folder,
                    width=150, height=45, bg_color=self.parent.bg_lighter, hover_color="#30363d", fg_color=self.parent.fg_light).pack(side=tk.LEFT, padx=15)

    def setup_settings_tab(self):
        # Container for settings tab
        settings_frame = ttk.Frame(self.parent.settings_tab, style='Dark.TFrame', padding="30")
        settings_frame.pack(expand=True, fill='both')
        
        # Tema & Aksesibilitas
        theme_group = ttk.LabelFrame(settings_frame, text=" Tema & Aksesibilitas ", style='Dark.TLabelframe', padding="15")
        theme_group.pack(fill='x', pady=(0, 15))
        theme_row = ttk.Frame(theme_group, style='Dark.TFrame')
        theme_row.pack(fill='x')
        ttk.Label(theme_row, text="Tema:", style='Dark.TLabel', width=12).pack(side=tk.LEFT, padx=(0, 10))
        self.parent.theme_combo = ttk.Combobox(theme_row, values=["Dark", "Light"], state="readonly", width=12, style='Dark.TCombobox')
        self.parent.theme_combo.set("Dark" if (getattr(self.parent, 'theme_mode_var', None) and self.parent.theme_mode_var.get() == "dark") else "Light")
        self.parent.theme_combo.pack(side=tk.LEFT, padx=5)
        ttk.Label(theme_row, text="Ukuran font log (8-14):", style='Dark.TLabel').pack(side=tk.LEFT, padx=(20, 5))
        self.parent.font_size_spin = ttk.Spinbox(theme_row, from_=8, to=14, width=5, textvariable=self.parent.font_size_var)
        self.parent.font_size_spin.pack(side=tk.LEFT, padx=5)
        def on_theme_change(*args):
            mode = "light" if self.parent.theme_combo.get() == "Light" else "dark"
            try:
                fs = int(self.parent.font_size_var.get())
            except Exception:
                fs = 10
            self.parent.custom_settings["theme_mode"] = mode
            self.parent.custom_settings["ui_font_size"] = fs
            from modules.settings_manager import save_settings
            save_settings(self.parent.custom_settings)
            self.parent.theme_manager.apply_theme(mode, fs)
        self.parent.theme_combo.bind("<<ComboboxSelected>>", lambda e: on_theme_change())
        tk.Button(theme_row, text="Terapkan", command=on_theme_change, bg=self.parent.accent_blue, fg="#050608", font=("Segoe UI", 9), relief="flat", cursor="hand2").pack(side=tk.LEFT, padx=10)
        
        # API Management Section with Sub-Tabs
        api_group = ttk.LabelFrame(settings_frame, text=" Manajemen API AI ", style='Dark.TLabelframe', padding="10")
        api_group.pack(fill='x', pady=(0, 20))
        
        self.parent.api_notebook = ttk.Notebook(api_group, style='Dark.TNotebook')
        self.parent.api_notebook.pack(expand=True, fill='both', padx=5, pady=5)
        
        # --- Gemini Tab ---
        gemini_tab = ttk.Frame(self.parent.api_notebook, style='Dark.TFrame', padding=15)
        self.parent.api_notebook.add(gemini_tab, text=" Google Gemini ")
        
        ttk.Label(gemini_tab, text="Google Gemini API Keys:", style='Title.TLabel').pack(anchor=tk.W, pady=(0, 10))
        
        self.parent.gemini_listbox = tk.Listbox(gemini_tab, bg=self.parent.bg_darker, fg=self.parent.fg_light, 
                                       selectbackground=self.parent.accent_blue, font=('Consolas', 9), height=4)
        self.parent.gemini_listbox.pack(fill='x', pady=(0, 10))
        
        tk.Label(gemini_tab, text="Masukkan Key (Satu per baris):", 
                 bg=self.parent.bg_dark, fg=self.parent.accent_blue, 
                 font=('Segoe UI', 10, 'bold')).pack(anchor=tk.W, pady=(5, 2))
        self.parent.gemini_entry = tk.Text(gemini_tab, bg=self.parent.bg_darker, fg=self.parent.fg_light, 
                                   insertbackground=self.parent.fg_light, height=3, font=('Consolas', 10),
                                   borderwidth=1, highlightthickness=1, highlightbackground=self.parent.border_color)
        self.parent.gemini_entry.pack(fill='x', pady=(0, 10))
        
        gemini_btns = ttk.Frame(gemini_tab, style='Dark.TFrame')
        gemini_btns.pack(fill='x')
        
        ModernButton(gemini_btns, text="+ Tambah", command=self.parent.add_gemini_key, width=120, height=35, radius=10).pack(side=tk.LEFT, padx=(0, 10))
        ModernButton(gemini_btns, text="- Hapus Terpilih", command=self.parent.remove_gemini_key, width=130, height=35, radius=10, bg_color="#cc3300", hover_color="#ff4400").pack(side=tk.LEFT, padx=10)
        ModernButton(gemini_btns, text="🗑 Hapus Semua", command=self.parent.clear_all_gemini_keys, width=130, height=35, radius=10, bg_color="#555555", hover_color="#777777").pack(side=tk.LEFT, padx=10)
        ModernButton(gemini_btns, text="⚡ Test Semua Key", command=self.parent.test_all_gemini_keys, width=150, height=35, radius=10, bg_color="#ffcc00", hover_color="#ffd633", fg_color="black").pack(side=tk.LEFT, padx=10)
        
        ttk.Checkbutton(gemini_tab, text="Otomatis Ganti Key (Rotate) jika Limit", style='Dark.TCheckbutton', variable=self.parent.rotate_gemini).pack(anchor=tk.W, pady=(10, 0))
        
        # --- Cookie & Other Settings ---
        other_frame = ttk.LabelFrame(settings_frame, text=" Pengaturan YouTube & Sistem ", style='Dark.TLabelframe', padding="20")
        other_frame.pack(fill='x')
        
        cookie_row = ttk.Frame(other_frame, style='Dark.TFrame')
        cookie_row.pack(fill='x', pady=(0, 10))
        
        self.parent.cookie_status_label = ttk.Label(cookie_row, text="Status Cookies: Mengecek...", style='Dark.TLabel')
        self.parent.cookie_status_label.pack(side=tk.LEFT, padx=(0, 20))
        
        # System Spec Info
        spec_frame = ttk.LabelFrame(settings_frame, text=" Status Sistem & AI Pintar (Auto-Spec) ", style='Dark.TLabelframe', padding="20")
        spec_frame.pack(fill='x', pady=20)
        
        spec_info = f"Spek Terdeteksi: {self.parent.ram_gb}GB RAM | {self.parent.cpu_cores} Cores | NVIDIA: {'AKTIF' if self.parent.has_nvidia else 'TIDAK'}"
        ttk.Label(spec_frame, text=spec_info, style='Dark.TLabel').pack(anchor=tk.W)
        
        status_color = self.parent.accent_blue if "Sultan" in self.parent.pc_level or "Mantap" in self.parent.pc_level else self.parent.accent_orange
        status_label = ttk.Label(spec_frame, text=f"Level PC: {self.parent.pc_level}", font=('Segoe UI', 11, 'bold'), foreground=status_color, background=self.parent.bg_dark)
        status_label.pack(anchor=tk.W, pady=5)
        
        self.parent.advanced_check = ttk.Checkbutton(
            spec_frame,
            text="Aktifkan Advanced AI (MediaPipe & Local Whisper) - Otomatis jika PC Dewa",
            style='Dark.TCheckbutton',
            variable=self.parent.advanced_ai_enabled
        )
        self.parent.advanced_check.pack(anchor=tk.W, pady=5)
        
        self.parent.update_cookie_btn = ModernButton(cookie_row, text="Perbarui File Cookies (.txt)", 
                                           command=self.parent.update_cookies, width=180, height=35, radius=15,
                                           bg_color=self.parent.accent_orange, hover_color="#ffb366")
        self.parent.update_cookie_btn.pack(side=tk.LEFT)
        
        gpu_row = ttk.Frame(other_frame, style='Dark.TFrame')
        gpu_row.pack(fill='x')
        
        self.parent.gpu_check = ttk.Checkbutton(
            gpu_row,
            text="Gunakan Akselerasi GPU NVIDIA (NVENC) untuk Export Video",
            style='Dark.TCheckbutton',
            variable=self.parent.gpu_var
        )
        self.parent.gpu_check.pack(side=tk.LEFT)
        
        # Load initial keys into listboxes
        self.parent.update_api_listboxes()
        self.parent.check_cookie_status()

    def setup_customize_tab(self):
        """Setup modern layout for the Customize tab including Live Preview"""
        # Split into Left (Controls) and Right (Preview)
        # Use a Grid with 2 columns
        self.parent.customize_tab.columnconfigure(0, weight=6) # Controls
        self.parent.customize_tab.columnconfigure(1, weight=4) # Preview
        self.parent.customize_tab.rowconfigure(0, weight=1)

        # === RIGHT PANEL: PREVIEW (Create First for Canvas Reference) ===
        preview_panel = ttk.Frame(self.parent.customize_tab, style='Dark.TFrame', padding=20)
        preview_panel.grid(row=0, column=1, sticky="nsew") # Right side
        
        # Center container
        center_preview = ttk.Frame(preview_panel, style='Dark.TFrame')
        center_preview.pack(expand=True)

        ttk.Label(center_preview, text="LIVE PREVIEW", style='Title.TLabel').pack(pady=(0, 10))
        
        # Phone Frame (Border)
        phone_frame = tk.Frame(center_preview, bg="#111", padx=10, pady=20)
        phone_frame.pack()
        
        # The Canvas (9:16 aspect ratio)
        self.parent.preview_canvas = tk.Canvas(phone_frame, width=270, height=480, bg="#000", highlightthickness=0)
        self.parent.preview_canvas.pack()
        
        # Store path to layout-baru.png for preview_engine to use
        self.parent.preview_base_image_path = os.path.join("assets", "img", "layout-baru.png")

        # === LEFT PANEL: CONTROLS ===
        controls_panel = ttk.Frame(self.parent.customize_tab, style='Dark.TFrame', padding=20)
        controls_panel.grid(row=0, column=0, sticky="nsew")


        # Title
        ttk.Label(controls_panel, text="Kustomisasi Tampilan", style='Title.TLabel').pack(anchor=tk.W, pady=(0, 5))

        # [NEW] Scrollable Cards Container (Single Column with Accordion)
        # Create canvas with scrollbar
        canvas_frame = ttk.Frame(controls_panel, style='Dark.TFrame')
        canvas_frame.pack(fill='both', expand=True)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(canvas_frame, orient='vertical')
        scrollbar.pack(side=tk.RIGHT, fill='y')
        
        # Canvas
        cards_canvas = tk.Canvas(canvas_frame, bg='#2b2b2b', highlightthickness=0, yscrollcommand=scrollbar.set)
        cards_canvas.pack(side=tk.LEFT, fill='both', expand=True)
        
        scrollbar.config(command=cards_canvas.yview)
        
        # Container frame inside canvas
        cards_container = ttk.Frame(cards_canvas, style='Dark.TFrame')
        canvas_window = cards_canvas.create_window((0, 0), window=cards_container, anchor='nw')
        
        # Update scroll region when container size changes
        def on_frame_configure(event=None):
            cards_canvas.configure(scrollregion=cards_canvas.bbox('all'))
            # Also update canvas window width to match canvas width
            cards_canvas.itemconfig(canvas_window, width=cards_canvas.winfo_width())
        
        cards_container.bind('<Configure>', on_frame_configure)
        cards_canvas.bind('<Configure>', lambda e: cards_canvas.itemconfig(canvas_window, width=e.width))
        
        # Mouse wheel scrolling
        def on_mousewheel(event):
            cards_canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        cards_canvas.bind_all("<MouseWheel>", on_mousewheel)

        # === ACCORDION SECTIONS ===
        
        # 1. Subtitle Accordion
        subtitle_accordion = AccordionSection(cards_container, "📝 Karaoke Subtitle", accent_color=self.parent.accent_blue)
        subtitle_accordion.pack(fill='x', pady=(0, 2))
        subtitle_accordion.open()  # Open by default
        sub_card = subtitle_accordion.get_content_frame()

        # Enable Switch
        ttk.Checkbutton(sub_card, text="Aktifkan Karaoke Subtitle", style='Dark.TCheckbutton', 
                        variable=self.parent.subtitle_enabled_var, command=self.parent.update_preview).pack(anchor=tk.W, pady=(0, 5))

        # Model Selector (New)
        model_frame = ttk.Frame(sub_card, style='Dark.TFrame')
        model_frame.pack(fill='x', pady=2)
        ttk.Label(model_frame, text="Model AI:", style='Dark.TLabel', width=10).pack(side=tk.LEFT)
        self.parent.whisper_model_var = tk.StringVar(value=self.parent.custom_settings.get("whisper_model", "small"))
        
        # Helper to map options
        # [AUTO] = Try YouTube CC first -> Fallback to Small (Best for users)
        model_names = ["Otomatis (Cerdas & Ringan)", "Manual: AI Small (Cepat)", "Manual: AI Medium (Akurasi)"]
        
        def get_model_display():
            v = self.parent.whisper_model_var.get()
            if v == "medium": return model_names[2]
            if v == "small": return model_names[1]
            return model_names[0] # Default Auto
            
        self.parent.model_combo = ttk.Combobox(model_frame, values=model_names, state="readonly", width=30, style='Dark.TCombobox')
        self.parent.model_combo.set(get_model_display())
        self.parent.model_combo.pack(side=tk.LEFT, fill='x', expand=True)
        
        def on_model_change(event):
            val = self.parent.model_combo.get()
            if "Medium" in val:
                self.parent.whisper_model_var.set("medium")
                messagebox.showinfo("Info Model", "Mode Manual: AI Medium (~1.5GB).\nAkan didownload & digunakan selalu.")
            elif "Small" in val:
                self.parent.whisper_model_var.set("small")
                messagebox.showinfo("Info Model", "Mode Manual: AI Small (~240MB).\nMemaksa penggunaan AI meskipun ada subtitle YouTube.")
            else:
                self.parent.whisper_model_var.set("auto")
                # Auto is silent, best UX
                
            self.parent.save_custom_settings(silent=True)
            
        self.parent.model_combo.bind("<<ComboboxSelected>>", on_model_change)

        # --- Font Section ---
        font_frame = ttk.Frame(sub_card, style='Dark.TFrame')
        font_frame.pack(fill='x', pady=2)
        
        ttk.Label(font_frame, text="Font:", style='Dark.TLabel', width=10).pack(side=tk.LEFT)
        
        # Load fonts dynamically
        available_fonts = load_fonts_from_folder()
        self.parent.font_combo = ttk.Combobox(font_frame, textvariable=self.parent.sub_font_var, values=available_fonts, 
                                     state="readonly", width=25, style='Dark.TCombobox')
        self.parent.font_combo.pack(side=tk.LEFT, fill='x', expand=True)
        self.parent.font_combo.bind("<<ComboboxSelected>>", self.parent.update_preview)

        # --- SLIDER GRID SECTION (2 Columns) ---
        slider_grid = ttk.Frame(sub_card, style='Dark.TFrame')
        slider_grid.pack(fill='x', pady=5)
        
        # Configure Grid Weights
        slider_grid.columnconfigure(1, weight=1) # Slider 1
        slider_grid.columnconfigure(3, weight=0) # Spacer
        slider_grid.columnconfigure(5, weight=1) # Slider 2
        
        # Ensure variable init
        if not hasattr(self, 'sub_stroke_width_var'):
             self.parent.sub_stroke_width_var = tk.IntVar(value=self.parent.custom_settings.get("subtitle_outline_width", 2))

        # Row 1: Ukuran | Posisi Y
        # Col 0: Label
        ttk.Label(slider_grid, text="Ukuran:", style='Dark.TLabel', width=10).grid(row=0, column=0, sticky='w')
        # Col 1: Slider
        ttk.Scale(slider_grid, from_=10, to=100, variable=self.parent.sub_size_var, 
                 orient='horizontal', command=lambda x: self.parent.update_preview()).grid(row=0, column=1, sticky='ew', padx=2)
        # Col 2: Value
        ttk.Label(slider_grid, textvariable=self.parent.sub_size_var, style='Dark.TLabel', width=4).grid(row=0, column=2, sticky='e')
        
        # Col 3: Spacer
        ttk.Frame(slider_grid, width=15, style='Dark.TFrame').grid(row=0, column=3)
        
        # Col 4: Label
        ttk.Label(slider_grid, text="Posisi Y:", style='Dark.TLabel', width=10).grid(row=0, column=4, sticky='w')
        # Col 5: Slider (Range 0-1200 to match Watermark logic)
        ttk.Scale(slider_grid, from_=0, to=1200, variable=self.parent.sub_pos_var,
                 orient='horizontal', command=lambda x: self.parent.update_preview()).grid(row=0, column=5, sticky='ew', padx=2)
        # Col 6: Value
        ttk.Label(slider_grid, textvariable=self.parent.sub_pos_var, style='Dark.TLabel', width=4).grid(row=0, column=6, sticky='e')
        
        # Row 2: Outline Width | (Empty/Future)
        ttk.Label(slider_grid, text="Outline:", style='Dark.TLabel', width=10).grid(row=1, column=0, sticky='w', pady=5)
        ttk.Scale(slider_grid, from_=0, to=10, variable=self.parent.sub_stroke_width_var,
                 orient='horizontal', command=lambda x: self.parent.update_preview()).grid(row=1, column=1, sticky='ew', padx=2, pady=5)
        ttk.Label(slider_grid, textvariable=self.parent.sub_stroke_width_var, style='Dark.TLabel', width=4).grid(row=1, column=2, sticky='e', pady=5)


        # --- Colors Grid ---
        color_frame = ttk.Frame(sub_card, style='Dark.TFrame')
        color_frame.pack(fill='x', pady=15)
        
        # Helper for color button
        def create_color_btn(parent, text, var):
            container = ttk.Frame(parent, style='Dark.TFrame')
            container.pack(side=tk.LEFT, expand=True)
            
            lbl = ttk.Label(container, text=text, style='Dark.TLabel', font=('Segoe UI', 9))
            lbl.pack(anchor='center', pady=(0, 5))
            
            # Canvas circle
            canvas = tk.Canvas(container, width=40, height=40, bg=self.parent.bg_dark, highlightthickness=0)
            canvas.pack()
            
            # Draw initial circle
            circle = canvas.create_oval(5, 5, 35, 35, fill=var.get(), outline='#555')
            
            def pick(event=None):
                from tkinter import colorchooser
                c = colorchooser.askcolor(color=var.get(), title=f"Pilih {text}", parent=self.parent.root)[1]
                if c:
                    var.set(c)
                    canvas.itemconfig(circle, fill=c)
                    self.parent.update_preview()
            
            canvas.bind('<Button-1>', pick)
            return canvas, circle

        self.parent.color_widgets = {}
        self.parent.color_widgets['text'] = create_color_btn(color_frame, "Teks Utama", self.parent.sub_color_var)
        self.parent.color_widgets['outline'] = create_color_btn(color_frame, "Outline", self.parent.sub_outline_color_var)
        self.parent.color_widgets['highlight'] = create_color_btn(color_frame, "Highlight", self.parent.sub_highlight_color_var)

        # 3. Live Update Bindings
        # Any change to variables triggers preview?
        # Sliders use 'command', Combo uses binding.
        # Button uses internal callback.
        # We should also ensure 'trace' if needed, but 'command' on sliders is usually enough.
        
        # Re-render immediately
        self.parent.root.after(100, self.parent.update_preview)

        # 2. Watermark Accordion
        watermark_accordion = AccordionSection(cards_container, "🏷️ Watermark", accent_color=self.parent.accent_blue)
        watermark_accordion.pack(fill='x', pady=(0, 2))
        wm_card = watermark_accordion.get_content_frame()

        # Enable Switch
        ttk.Checkbutton(wm_card, text="Aktifkan Watermark", style='Dark.TCheckbutton', 
                        variable=self.parent.watermark_enabled_var, command=self.parent.update_preview).pack(anchor=tk.W, pady=(0, 10))

        # Type Selection
        type_frame = ttk.Frame(wm_card, style='Dark.TFrame')
        type_frame.pack(fill='x', pady=5)
        ttk.Label(type_frame, text="Tipe:", style='Dark.TLabel', width=10).pack(side=tk.LEFT)
        wm_type_combo = ttk.Combobox(type_frame, textvariable=self.parent.watermark_type_var, values=["text", "image"], 
                                     state="readonly", width=15, style='Dark.TCombobox')
        wm_type_combo.pack(side=tk.LEFT, fill='x', expand=True)
        wm_type_combo.bind("<<ComboboxSelected>>", lambda e: self.parent.toggle_watermark_ui())

        # [FIX] Dedicated Content Frame for switching Text/Image settings safely
        self.parent.wm_content_frame = ttk.Frame(wm_card, style='Dark.TFrame')
        self.parent.wm_content_frame.pack(fill='x', pady=5)

        # --- TEXT SETTINGS FRAME ---
        # Parent is now wm_content_frame
        self.parent.wm_text_frame = ttk.Frame(self.parent.wm_content_frame, style='Dark.TFrame')
        # self.parent.wm_text_frame.pack(fill='x', pady=5) # Managed by toggle
        
        # Text Input
        ttk.Label(self.parent.wm_text_frame, text="Teks:", style='Dark.TLabel').pack(anchor=tk.W)
        wm_entry = ttk.Entry(self.parent.wm_text_frame, textvariable=self.parent.watermark_text_var, style='Dark.TEntry')
        wm_entry.pack(fill='x', pady=(0, 5))
        wm_entry.bind('<KeyRelease>', lambda e: self.parent.update_preview())

        # Font
        font_frame_wm = ttk.Frame(self.parent.wm_text_frame, style='Dark.TFrame')
        font_frame_wm.pack(fill='x', pady=2)
        ttk.Label(font_frame_wm, text="Font:", style='Dark.TLabel', width=10).pack(side=tk.LEFT)
        wm_font_combo = ttk.Combobox(font_frame_wm, textvariable=self.parent.watermark_font_var, values=available_fonts, 
                                     state="readonly", width=15, style='Dark.TCombobox')
        wm_font_combo.pack(side=tk.LEFT, fill='x', expand=True)
        wm_font_combo.bind("<<ComboboxSelected>>", self.parent.update_preview)

        # Size & Opacity (Text)
        wm_size_frame = ttk.Frame(self.parent.wm_text_frame, style='Dark.TFrame')
        wm_size_frame.pack(fill='x', pady=2)
        ttk.Label(wm_size_frame, text="Size:", style='Dark.TLabel', width=8).pack(side=tk.LEFT)
        ttk.Scale(wm_size_frame, from_=8, to=96, variable=self.parent.watermark_size_var, command=lambda x: self.parent.update_preview()).pack(side=tk.LEFT, fill='x', expand=True)
        ttk.Label(wm_size_frame, textvariable=self.parent.watermark_size_var, style='Dark.TLabel', width=4).pack(side=tk.LEFT, padx=(5,0))
        
        wm_op_frame = ttk.Frame(self.parent.wm_text_frame, style='Dark.TFrame')
        wm_op_frame.pack(fill='x', pady=2)
        ttk.Label(wm_op_frame, text="Opacity:", style='Dark.TLabel', width=8).pack(side=tk.LEFT)
        ttk.Scale(wm_op_frame, from_=0, to=100, variable=self.parent.watermark_opacity_var, command=lambda x: self.parent.update_preview()).pack(side=tk.LEFT, fill='x', expand=True)
        ttk.Label(wm_op_frame, textvariable=self.parent.watermark_opacity_var, style='Dark.TLabel', width=4).pack(side=tk.LEFT, padx=(5,0))

        # Colors
        wm_col_frame = ttk.Frame(self.parent.wm_text_frame, style='Dark.TFrame')
        wm_col_frame.pack(fill='x', pady=5)
        self.parent.color_widgets['wm_text'] = create_color_btn(wm_col_frame, "Warna", self.parent.watermark_color_var)
        self.parent.color_widgets['wm_outline'] = create_color_btn(wm_col_frame, "Outline", self.parent.watermark_outline_var)

        # Outline Width
        wm_outline_w_frame = ttk.Frame(self.parent.wm_text_frame, style='Dark.TFrame')
        wm_outline_w_frame.pack(fill='x', pady=2)
        ttk.Label(wm_outline_w_frame, text="Tebal Garis:", style='Dark.TLabel', width=12).pack(side=tk.LEFT)
        ttk.Scale(wm_outline_w_frame, from_=0, to=5, variable=self.parent.watermark_outline_width_var, command=lambda x: self.parent.update_preview()).pack(side=tk.LEFT, fill='x', expand=True)
        ttk.Label(wm_outline_w_frame, textvariable=self.parent.watermark_outline_width_var, style='Dark.TLabel', width=4).pack(side=tk.LEFT, padx=(5,0))

        # --- IMAGE SETTINGS FRAME ---
        # Parent is now wm_content_frame
        self.parent.wm_image_frame = ttk.Frame(self.parent.wm_content_frame, style='Dark.TFrame')
        # Initially hidden if text is selected
        
        # Image Upload
        img_up_frame = ttk.Frame(self.parent.wm_image_frame, style='Dark.TFrame')
        img_up_frame.pack(fill='x', pady=5)
        wm_img_entry = ttk.Entry(img_up_frame, textvariable=self.parent.watermark_image_path_var, style='Dark.TEntry', width=30)
        wm_img_entry.pack(side=tk.LEFT, fill='x', expand=True, padx=(0,5))
        def browse_wm_image():
            f = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg")])
            if f:
                self.parent.watermark_image_path_var.set(f)
                self.parent.update_preview()
        ModernButton(img_up_frame, text="📂 Browse", command=browse_wm_image, width=80, bg_color=self.parent.accent_blue).pack(side=tk.LEFT)

        # Scale & Opacity (Image)
        wm_img_scale_frame = ttk.Frame(self.parent.wm_image_frame, style='Dark.TFrame')
        wm_img_scale_frame.pack(fill='x', pady=2)
        ttk.Label(wm_img_scale_frame, text="Scale %:", style='Dark.TLabel', width=10).pack(side=tk.LEFT)
        ttk.Scale(wm_img_scale_frame, from_=1, to=100, variable=self.parent.watermark_scale_var, command=lambda x: self.parent.update_preview()).pack(side=tk.LEFT, fill='x', expand=True)
        ttk.Label(wm_img_scale_frame, textvariable=self.parent.watermark_scale_var, style='Dark.TLabel', width=4).pack(side=tk.LEFT, padx=(5,0))

        wm_img_op_frame = ttk.Frame(self.parent.wm_image_frame, style='Dark.TFrame')
        wm_img_op_frame.pack(fill='x', pady=2)
        ttk.Label(wm_img_op_frame, text="Opacity:", style='Dark.TLabel', width=10).pack(side=tk.LEFT)
        ttk.Scale(wm_img_op_frame, from_=0, to=100, variable=self.parent.watermark_img_opacity_var, command=lambda x: self.parent.update_preview()).pack(side=tk.LEFT, fill='x', expand=True)
        ttk.Label(wm_img_op_frame, textvariable=self.parent.watermark_img_opacity_var, style='Dark.TLabel', width=4).pack(side=tk.LEFT, padx=(5,0))

        # --- POSITION SECTION ---
        pos_card = ttk.Frame(wm_card, style='Dark.TFrame')
        pos_card.pack(fill='x', pady=10)
        ttk.Label(pos_card, text="Posisi:", style='Dark.TLabel').pack(anchor=tk.W)
        
        # Simple Sliders (Bottom Margin Logic)
        fine_frame = ttk.Frame(pos_card, style='Dark.TFrame')
        fine_frame.pack(fill='x', pady=5)
        
        wm_pos_grid = ttk.Frame(fine_frame, style='Dark.TFrame')
        wm_pos_grid.pack(fill='x')
        wm_pos_grid.columnconfigure(1, weight=1)
        wm_pos_grid.columnconfigure(3, weight=0)
        wm_pos_grid.columnconfigure(5, weight=1)
        
        # Row 1: X (%) | Y (Bottom Margin)
        ttk.Label(wm_pos_grid, text="Posisi X (%):", style='Dark.TLabel', width=12).grid(row=0, column=0, sticky='w')
        ttk.Scale(wm_pos_grid, from_=0, to=100, variable=self.parent.watermark_pos_x_var, 
                 orient='horizontal', command=lambda x: self.parent.update_preview()).grid(row=0, column=1, sticky='ew', padx=2)
        ttk.Label(wm_pos_grid, textvariable=self.parent.watermark_pos_x_var, style='Dark.TLabel', width=4).grid(row=0, column=2, sticky='e')
        
        # Spacer
        ttk.Frame(wm_pos_grid, width=15, style='Dark.TFrame').grid(row=0, column=3)
        
        ttk.Label(wm_pos_grid, text="Margin Bawah:", style='Dark.TLabel', width=12).grid(row=0, column=4, sticky='w')
        ttk.Scale(wm_pos_grid, from_=0, to=2000, variable=self.parent.watermark_pos_y_var, 
                 orient='horizontal', command=lambda x: self.parent.update_preview()).grid(row=0, column=5, sticky='ew', padx=2)
        ttk.Label(wm_pos_grid, textvariable=self.parent.watermark_pos_y_var, style='Dark.TLabel', width=4).grid(row=0, column=6, sticky='e')


        # Initialize Toggle
        self.parent.toggle_watermark_ui()

        # 3. BGM Accordion
        bgm_accordion = AccordionSection(cards_container, "🎵 Background Music", accent_color=self.parent.accent_blue)
        bgm_accordion.pack(fill='x', pady=(0, 2))
        bgm_card = bgm_accordion.get_content_frame()
        
        # Enable BGM Checkbox
        ttk.Checkbutton(bgm_card, text="Aktifkan BGM", style='Dark.TCheckbutton', 
                        variable=self.parent.bgm_enabled_var, command=self.parent.save_custom_settings).pack(anchor=tk.W, pady=(0, 10))
        
        # File Browser Section
        bgm_file_frame = ttk.Frame(bgm_card, style='Dark.TFrame')
        bgm_file_frame.pack(fill='x', pady=5)
        
        ttk.Label(bgm_file_frame, text="File Audio:", style='Dark.TLabel', width=10).pack(side=tk.LEFT)
        
        # Entry to display selected file
        self.parent.bgm_file_entry = ttk.Entry(bgm_file_frame, textvariable=self.parent.bgm_file_path_var, 
                                               style='Dark.TEntry', state='readonly')
        self.parent.bgm_file_entry.pack(side=tk.LEFT, fill='x', expand=True, padx=(5, 5))
        
        # Browse button
        def browse_bgm_file():
            from tkinter import filedialog
            f = filedialog.askopenfilename(
                title="Pilih File BGM",
                filetypes=[
                    ("Audio Files", "*.mp3;*.wav"),
                    ("MP3 Files", "*.mp3"),
                    ("WAV Files", "*.wav"),
                    ("All Files", "*.*")
                ]
            )
            if f:
                self.parent.bgm_file_path_var.set(f)
                self.parent.save_custom_settings()
                print(f"[BGM] File selected: {f}")
        
        ModernButton(bgm_file_frame, text="📂 Browse", command=browse_bgm_file, 
                    width=100, bg_color=self.parent.accent_blue, hover_color="#2980b9").pack(side=tk.LEFT)
        
        # Info label
        info_label = ttk.Label(bgm_card, text="💡 BGM akan di-mix dengan volume -10dB saat export", 
                              style='Dark.TLabel', font=('Segoe UI', 8, 'italic'))
        info_label.pack(anchor=tk.W, pady=(5, 0))
        
        
        # 3.5. Overlay Accordion (Second Watermark)
        overlay_accordion = AccordionSection(cards_container, "🎨 Overlay", accent_color=self.parent.accent_blue)
        overlay_accordion.pack(fill='x', pady=(0, 2))
        ov_card = overlay_accordion.get_content_frame()

        # Enable Switch
        ttk.Checkbutton(ov_card, text="Aktifkan Overlay", style='Dark.TCheckbutton', 
                        variable=self.parent.overlay_enabled_var, command=self.parent.update_preview).pack(anchor=tk.W, pady=(0, 10))

        # Type Selection
        type_frame_ov = ttk.Frame(ov_card, style='Dark.TFrame')
        type_frame_ov.pack(fill='x', pady=5)
        ttk.Label(type_frame_ov, text="Tipe:", style='Dark.TLabel', width=10).pack(side=tk.LEFT)
        ov_type_combo = ttk.Combobox(type_frame_ov, textvariable=self.parent.overlay_type_var, values=["text", "image"], 
                                     state="readonly", width=15, style='Dark.TCombobox')
        ov_type_combo.pack(side=tk.LEFT, fill='x', expand=True)
        ov_type_combo.bind("<<ComboboxSelected>>", lambda e: self.parent.toggle_overlay_ui())

        # Content Frame for switching Text/Image settings
        self.parent.ov_content_frame = ttk.Frame(ov_card, style='Dark.TFrame')
        self.parent.ov_content_frame.pack(fill='x', pady=5)

        # --- TEXT SETTINGS FRAME ---
        self.parent.ov_text_frame = ttk.Frame(self.parent.ov_content_frame, style='Dark.TFrame')
        
        # Text Input
        ttk.Label(self.parent.ov_text_frame, text="Teks:", style='Dark.TLabel').pack(anchor=tk.W)
        ov_entry = ttk.Entry(self.parent.ov_text_frame, textvariable=self.parent.overlay_text_var, style='Dark.TEntry')
        ov_entry.pack(fill='x', pady=(0, 5))
        ov_entry.bind('<KeyRelease>', lambda e: self.parent.update_preview())

        # Font
        font_frame_ov = ttk.Frame(self.parent.ov_text_frame, style='Dark.TFrame')
        font_frame_ov.pack(fill='x', pady=2)
        ttk.Label(font_frame_ov, text="Font:", style='Dark.TLabel', width=10).pack(side=tk.LEFT)
        ov_font_combo = ttk.Combobox(font_frame_ov, textvariable=self.parent.overlay_font_var, values=available_fonts, 
                                     state="readonly", width=15, style='Dark.TCombobox')
        ov_font_combo.pack(side=tk.LEFT, fill='x', expand=True)
        ov_font_combo.bind("<<ComboboxSelected>>", self.parent.update_preview)

        # Size & Opacity (Text)
        ov_size_frame = ttk.Frame(self.parent.ov_text_frame, style='Dark.TFrame')
        ov_size_frame.pack(fill='x', pady=2)
        ttk.Label(ov_size_frame, text="Size:", style='Dark.TLabel', width=8).pack(side=tk.LEFT)
        ttk.Scale(ov_size_frame, from_=8, to=96, variable=self.parent.overlay_size_var, command=lambda x: self.parent.update_preview()).pack(side=tk.LEFT, fill='x', expand=True)
        ttk.Label(ov_size_frame, textvariable=self.parent.overlay_size_var, style='Dark.TLabel', width=4).pack(side=tk.LEFT, padx=(5,0))
        
        ov_op_frame = ttk.Frame(self.parent.ov_text_frame, style='Dark.TFrame')
        ov_op_frame.pack(fill='x', pady=2)
        ttk.Label(ov_op_frame, text="Opacity:", style='Dark.TLabel', width=8).pack(side=tk.LEFT)
        ttk.Scale(ov_op_frame, from_=0, to=100, variable=self.parent.overlay_opacity_var, command=lambda x: self.parent.update_preview()).pack(side=tk.LEFT, fill='x', expand=True)
        ttk.Label(ov_op_frame, textvariable=self.parent.overlay_opacity_var, style='Dark.TLabel', width=4).pack(side=tk.LEFT, padx=(5,0))

        # Colors
        ov_col_frame = ttk.Frame(self.parent.ov_text_frame, style='Dark.TFrame')
        ov_col_frame.pack(fill='x', pady=5)
        self.parent.color_widgets['ov_text'] = create_color_btn(ov_col_frame, "Warna", self.parent.overlay_color_var)
        self.parent.color_widgets['ov_outline'] = create_color_btn(ov_col_frame, "Outline", self.parent.overlay_outline_var)

        # Outline Width
        ov_outline_w_frame = ttk.Frame(self.parent.ov_text_frame, style='Dark.TFrame')
        ov_outline_w_frame.pack(fill='x', pady=2)
        ttk.Label(ov_outline_w_frame, text="Tebal Garis:", style='Dark.TLabel', width=12).pack(side=tk.LEFT)
        ttk.Scale(ov_outline_w_frame, from_=0, to=5, variable=self.parent.overlay_outline_width_var, command=lambda x: self.parent.update_preview()).pack(side=tk.LEFT, fill='x', expand=True)
        ttk.Label(ov_outline_w_frame, textvariable=self.parent.overlay_outline_width_var, style='Dark.TLabel', width=4).pack(side=tk.LEFT, padx=(5,0))

        # --- IMAGE SETTINGS FRAME ---
        self.parent.ov_image_frame = ttk.Frame(self.parent.ov_content_frame, style='Dark.TFrame')
        
        # Image Upload
        img_up_frame_ov = ttk.Frame(self.parent.ov_image_frame, style='Dark.TFrame')
        img_up_frame_ov.pack(fill='x', pady=5)
        ov_img_entry = ttk.Entry(img_up_frame_ov, textvariable=self.parent.overlay_image_path_var, style='Dark.TEntry', width=30)
        ov_img_entry.pack(side=tk.LEFT, fill='x', expand=True, padx=(0,5))
        def browse_ov_image():
            f = filedialog.askopenfilename(filetypes=[("Images", "*.png;*.jpg;*.jpeg")])
            if f:
                self.parent.overlay_image_path_var.set(f)
                self.parent.update_preview()
        ModernButton(img_up_frame_ov, text="📂 Browse", command=browse_ov_image, width=80, bg_color=self.parent.accent_blue).pack(side=tk.LEFT)

        # Scale & Opacity (Image)
        ov_img_scale_frame = ttk.Frame(self.parent.ov_image_frame, style='Dark.TFrame')
        ov_img_scale_frame.pack(fill='x', pady=2)
        ttk.Label(ov_img_scale_frame, text="Scale %:", style='Dark.TLabel', width=10).pack(side=tk.LEFT)
        ttk.Scale(ov_img_scale_frame, from_=1, to=100, variable=self.parent.overlay_scale_var, command=lambda x: self.parent.update_preview()).pack(side=tk.LEFT, fill='x', expand=True)
        ttk.Label(ov_img_scale_frame, textvariable=self.parent.overlay_scale_var, style='Dark.TLabel', width=4).pack(side=tk.LEFT, padx=(5,0))

        ov_img_op_frame = ttk.Frame(self.parent.ov_image_frame, style='Dark.TFrame')
        ov_img_op_frame.pack(fill='x', pady=2)
        ttk.Label(ov_img_op_frame, text="Opacity:", style='Dark.TLabel', width=10).pack(side=tk.LEFT)
        ttk.Scale(ov_img_op_frame, from_=0, to=100, variable=self.parent.overlay_img_opacity_var, command=lambda x: self.parent.update_preview()).pack(side=tk.LEFT, fill='x', expand=True)
        ttk.Label(ov_img_op_frame, textvariable=self.parent.overlay_img_opacity_var, style='Dark.TLabel', width=4).pack(side=tk.LEFT, padx=(5,0))

        # --- POSITION SECTION ---
        pos_card_ov = ttk.Frame(ov_card, style='Dark.TFrame')
        pos_card_ov.pack(fill='x', pady=10)
        ttk.Label(pos_card_ov, text="Posisi:", style='Dark.TLabel').pack(anchor=tk.W)
        
        # Simple Sliders (Bottom Margin Logic)
        fine_frame_ov = ttk.Frame(pos_card_ov, style='Dark.TFrame')
        fine_frame_ov.pack(fill='x', pady=5)
        
        ov_pos_grid = ttk.Frame(fine_frame_ov, style='Dark.TFrame')
        ov_pos_grid.pack(fill='x')
        ov_pos_grid.columnconfigure(1, weight=1)
        ov_pos_grid.columnconfigure(3, weight=0)
        ov_pos_grid.columnconfigure(5, weight=1)
        
        # Row 1: X (%) | Y (Bottom Margin)
        ttk.Label(ov_pos_grid, text="Posisi X (%):", style='Dark.TLabel', width=12).grid(row=0, column=0, sticky='w')
        ttk.Scale(ov_pos_grid, from_=0, to=100, variable=self.parent.overlay_pos_x_var, 
                 orient='horizontal', command=lambda x: self.parent.update_preview()).grid(row=0, column=1, sticky='ew', padx=2)
        ttk.Label(ov_pos_grid, textvariable=self.parent.overlay_pos_x_var, style='Dark.TLabel', width=4).grid(row=0, column=2, sticky='e')
        
        # Spacer
        ttk.Frame(ov_pos_grid, width=15, style='Dark.TFrame').grid(row=0, column=3)
        
        ttk.Label(ov_pos_grid, text="Margin Bawah:", style='Dark.TLabel', width=12).grid(row=0, column=4, sticky='w')
        ttk.Scale(ov_pos_grid, from_=0, to=2000, variable=self.parent.overlay_pos_y_var, 
                 orient='horizontal', command=lambda x: self.parent.update_preview()).grid(row=0, column=5, sticky='ew', padx=2)
        ttk.Label(ov_pos_grid, textvariable=self.parent.overlay_pos_y_var, style='Dark.TLabel', width=4).grid(row=0, column=6, sticky='e')

        # Initialize Toggle
        self.parent.toggle_overlay_ui()

        
        # 4. Source Credit Accordion
        source_accordion = AccordionSection(cards_container, "📺 Source Credit", accent_color=self.parent.accent_blue)
        source_accordion.pack(fill='x', pady=(0, 2))
        source_card = source_accordion.get_content_frame()
        
        # Enable Source Credit Checkbox
        tk.Checkbutton(
            source_card, 
            text="📺 Tampilkan Source Credit", 
            variable=self.parent.source_credit_enabled_var,
            command=self.parent.update_preview,  # Changed from save_custom_settings to update_preview
            bg='#2b2b2b',
            fg='white',
            selectcolor='#2b2b2b',
            activebackground='#2b2b2b',
            activeforeground='white',
            font=('Segoe UI', 9),
            cursor='hand2'
        ).pack(anchor=tk.W, pady=(0, 10))
        
        # Info Label (Text will be auto-generated)
        info_frame = ttk.Frame(source_card, style='Dark.TFrame')
        info_frame.pack(fill='x', pady=(0, 10))
        ttk.Label(info_frame, text="💡 Text akan otomatis: 'Source: [Nama Channel]'", 
                 style='Dark.TLabel', font=('Segoe UI', 9, 'italic')).pack(anchor=tk.W)
        
        # Font & Size
        font_frame = ttk.Frame(source_card, style='Dark.TFrame')
        font_frame.pack(fill='x', pady=5)
        
        ttk.Label(font_frame, text="Font:", style='Dark.TLabel', width=10).pack(side=tk.LEFT)
        font_combo = ttk.Combobox(font_frame, textvariable=self.parent.source_credit_font_var,
                                 values=available_fonts,
                                 state='readonly', style='Dark.TCombobox', width=12)
        font_combo.pack(side=tk.LEFT, padx=(5, 10))
        font_combo.bind('<<ComboboxSelected>>', lambda e: self.parent.update_preview())
        
        ttk.Label(font_frame, text="Size:", style='Dark.TLabel').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Scale(font_frame, from_=5, to=72, variable=self.parent.source_credit_fontsize_var,
                 command=lambda x: self.parent.update_preview()).pack(side=tk.LEFT, fill='x', expand=True)
        ttk.Label(font_frame, textvariable=self.parent.source_credit_fontsize_var, 
                 style='Dark.TLabel', width=3).pack(side=tk.LEFT, padx=(5, 0))
        
        # Color & Opacity
        color_frame = ttk.Frame(source_card, style='Dark.TFrame')
        color_frame.pack(fill='x', pady=5)
        
        ttk.Label(color_frame, text="Color:", style='Dark.TLabel', width=10).pack(side=tk.LEFT)
        
        def pick_source_color():
            from tkinter import colorchooser
            color = colorchooser.askcolor(initialcolor=self.parent.source_credit_color_var.get())
            if color[1]:
                self.parent.source_credit_color_var.set(color[1])
                self.parent.update_preview()
        
        ModernButton(color_frame, text="🎨 Pick Color", command=pick_source_color,
                    width=100, bg_color=self.parent.accent_blue, hover_color="#2980b9").pack(side=tk.LEFT, padx=(5, 10))
        
        ttk.Label(color_frame, text="Opacity:", style='Dark.TLabel').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Scale(color_frame, from_=0, to=100, variable=self.parent.source_credit_opacity_var,
                 command=lambda x: self.parent.update_preview()).pack(side=tk.LEFT, fill='x', expand=True)
        ttk.Label(color_frame, textvariable=self.parent.source_credit_opacity_var, 
                 style='Dark.TLabel', width=3).pack(side=tk.LEFT, padx=(5, 0))
        ttk.Label(color_frame, text="%", style='Dark.TLabel').pack(side=tk.LEFT)
        
        # Position Preset
        pos_frame = ttk.Frame(source_card, style='Dark.TFrame')
        pos_frame.pack(fill='x', pady=5)
        
        ttk.Label(pos_frame, text="Position:", style='Dark.TLabel', width=10).pack(side=tk.LEFT)
        pos_combo = ttk.Combobox(pos_frame, textvariable=self.parent.source_credit_position_var,
                                values=["top-left", "top-right", "bottom-left", "bottom-right"],
                                state='readonly', style='Dark.TCombobox')
        pos_combo.pack(side=tk.LEFT, fill='x', expand=True, padx=(5, 0))
        pos_combo.bind('<<ComboboxSelected>>', lambda e: self.parent.update_preview())
        
        # X/Y Offset
        offset_frame = ttk.Frame(source_card, style='Dark.TFrame')
        offset_frame.pack(fill='x', pady=5)
        
        ttk.Label(offset_frame, text="Offset X:", style='Dark.TLabel', width=10).pack(side=tk.LEFT)
        ttk.Scale(offset_frame, from_=0, to=500, variable=self.parent.source_credit_pos_x_var,
                 command=lambda x: self.parent.update_preview()).pack(side=tk.LEFT, fill='x', expand=True)
        ttk.Label(offset_frame, textvariable=self.parent.source_credit_pos_x_var, 
                 style='Dark.TLabel', width=4).pack(side=tk.LEFT, padx=(5, 10))
        
        ttk.Label(offset_frame, text="Y:", style='Dark.TLabel').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Scale(offset_frame, from_=0, to=500, variable=self.parent.source_credit_pos_y_var,
                 command=lambda x: self.parent.update_preview()).pack(side=tk.LEFT, fill='x', expand=True)
        ttk.Label(offset_frame, textvariable=self.parent.source_credit_pos_y_var, 
                 style='Dark.TLabel', width=4).pack(side=tk.LEFT, padx=(5, 0))
        
        # Info label
        source_info = ttk.Label(source_card, text="💡 Menampilkan credit channel asli di video export", 
                               style='Dark.TLabel', font=('Segoe UI', 8, 'italic'))
        source_info.pack(anchor=tk.W, pady=(5, 0))
        
        
        # 5. Export Mode Accordion
        export_accordion = AccordionSection(cards_container, "🎬 Mode Export", accent_color=self.parent.accent_blue)
        export_accordion.pack(fill='x', pady=(0, 2))
        export_card = export_accordion.get_content_frame()
        
        # Export Mode Dropdown
        mode_frame = ttk.Frame(export_card, style='Dark.TFrame')
        mode_frame.pack(fill='x', pady=5)
        ttk.Label(mode_frame, text="Mode:", style='Dark.TLabel', width=15).pack(side=tk.LEFT)
        
        export_modes = [
            "Landscape Fit (Blur Background)",
            "Face Tracking (9:16 Crop)"
        ]
        
        # Map display names to internal values
        mode_map = {
            "Landscape Fit (Blur Background)": "landscape_fit",
            "Face Tracking (9:16 Crop)": "face_tracking"
        }
        reverse_mode_map = {v: k for k, v in mode_map.items()}
        
        # Get current display value
        current_mode = self.parent.export_mode_var.get()
        current_display = reverse_mode_map.get(current_mode, export_modes[0])
        
        mode_dropdown_var = tk.StringVar(value=current_display)
        
        def on_mode_change(*args):
            display_value = mode_dropdown_var.get()
            internal_value = mode_map.get(display_value, "landscape_fit")
            self.parent.export_mode_var.set(internal_value)
            self.parent.save_custom_settings()
            # Show/hide face tracking settings
            if internal_value == "face_tracking":
                face_tracking_frame.pack(fill='x', pady=5)
            else:
                face_tracking_frame.pack_forget()
        
        mode_dropdown = ttk.Combobox(mode_frame, textvariable=mode_dropdown_var, 
                                     values=export_modes, state='readonly', style='Dark.TCombobox')
        mode_dropdown.pack(side=tk.LEFT, fill='x', expand=True, padx=(5, 0))
        mode_dropdown.bind('<<ComboboxSelected>>', on_mode_change)
        
        # Flip Video, Dynamic Zoom, Audio Pitch — di depan (langsung di bawah Mode)
        flip_frame = ttk.Frame(export_card, style='Dark.TFrame')
        flip_frame.pack(fill='x', pady=(10, 0))
        tk.Checkbutton(
            flip_frame, 
            text="🔄 Flip Video Horizontal (Anti-Copyright Detection)", 
            variable=self.parent.video_flip_var,
            command=self.parent.save_custom_settings,
            bg='#2b2b2b', fg='white', selectcolor='#2b2b2b',
            activebackground='#2b2b2b', activeforeground='white',
            font=('Segoe UI', 9), cursor='hand2'
        ).pack(anchor=tk.W)
        flip_info = ttk.Label(
            flip_frame, 
            text="Video di-mirror horizontal untuk hindari deteksi copyright",
            style='Dark.TLabel', font=('Segoe UI', 8, 'italic')
        )
        flip_info.pack(anchor=tk.W, pady=(2, 0))

        zoom_frame = ttk.Frame(export_card, style='Dark.TFrame')
        zoom_frame.pack(fill='x', pady=(10, 0))
        tk.Checkbutton(
            zoom_frame,
            text="Dynamic Zoom (Ken Burns)",
            variable=self.parent.dynamic_zoom_var,
            command=self.parent.save_custom_settings,
            bg='#2b2b2b', fg='white', selectcolor='#2b2b2b',
            activebackground='#2b2b2b', activeforeground='white',
            font=('Segoe UI', 9), cursor='hand2'
        ).pack(anchor=tk.W)
        zoom_opts = ttk.Frame(zoom_frame, style='Dark.TFrame')
        zoom_opts.pack(fill='x', pady=(4, 0))
        ttk.Label(zoom_opts, text="Kekuatan:", style='Dark.TLabel', width=10).pack(side=tk.LEFT)
        ttk.Scale(zoom_opts, from_=1.1, to=1.9, variable=self.parent.dynamic_zoom_strength_var,
                  command=lambda x: self.parent.save_custom_settings()).pack(side=tk.LEFT, fill='x', expand=True, padx=4)
        ttk.Label(zoom_opts, text="Kecepatan:", style='Dark.TLabel', width=10).pack(side=tk.LEFT, padx=(10,0))
        ttk.Scale(zoom_opts, from_=0.0015, to=0.0065, variable=self.parent.dynamic_zoom_speed_var,
                  command=lambda x: self.parent.save_custom_settings()).pack(side=tk.LEFT, fill='x', expand=True, padx=4)
        ttk.Label(zoom_opts, text="(kanan=lebih terasa)", style='Dark.TLabel', font=('Segoe UI', 8, 'italic')).pack(side=tk.LEFT, padx=(4,0))

        pitch_frame = ttk.Frame(export_card, style='Dark.TFrame')
        pitch_frame.pack(fill='x', pady=(10, 0))
        tk.Checkbutton(
            pitch_frame,
            text="Audio Pitch (naik/turun nada)",
            variable=self.parent.audio_pitch_var,
            command=self.parent.save_custom_settings,
            bg='#2b2b2b', fg='white', selectcolor='#2b2b2b',
            activebackground='#2b2b2b', activeforeground='white',
            font=('Segoe UI', 9), cursor='hand2'
        ).pack(anchor=tk.W)
        pitch_opts = ttk.Frame(pitch_frame, style='Dark.TFrame')
        pitch_opts.pack(fill='x', pady=(4, 0))
        ttk.Label(pitch_opts, text="Semitone (-4 s/d +4):", style='Dark.TLabel', width=18).pack(side=tk.LEFT)
        ttk.Scale(pitch_opts, from_=-4, to=4, variable=self.parent.audio_pitch_semitones_var,
                  command=lambda x: self.parent.save_custom_settings()).pack(side=tk.LEFT, fill='x', expand=True, padx=4)
        
        # Face Tracking Settings (conditionally shown)
        face_tracking_frame = ttk.Frame(export_card, style='Dark.TFrame')
        smooth_frame = ttk.Frame(face_tracking_frame, style='Dark.TFrame')
        smooth_frame.pack(fill='x', pady=2)
        ttk.Label(smooth_frame, text="Smoothing:", style='Dark.TLabel', width=15).pack(side=tk.LEFT)
        ttk.Scale(smooth_frame, from_=1, to=60, variable=self.parent.face_tracking_smoothing_var,
                 command=lambda x: self.parent.save_custom_settings()).pack(side=tk.LEFT, fill='x', expand=True)
        ttk.Label(smooth_frame, textvariable=self.parent.face_tracking_smoothing_var, 
                 style='Dark.TLabel', width=4).pack(side=tk.LEFT, padx=(5,0))
        ttk.Label(smooth_frame, text="frames", style='Dark.TLabel').pack(side=tk.LEFT, padx=(2,0))
        if self.parent.export_mode_var.get() == "face_tracking":
            face_tracking_frame.pack(fill='x', pady=5)

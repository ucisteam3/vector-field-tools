"""
Theme Manager Module
Handles dark theme configuration for the application.
Web/headless: no tkinter; setup_dark_theme is no-op.
"""

try:
    import tkinter as tk
    from tkinter import ttk
    _tk_available = True
except ImportError:
    tk = None
    ttk = None
    _tk_available = False


class ThemeManager:
    """Manages application theme and styling (desktop only; no-op when headless)."""

    def __init__(self, parent):
        self.parent = parent

    def setup_dark_theme(self):
        """Configure modern dark theme. No-op when headless or tk not available."""
        if not _tk_available or getattr(self.parent, "root", None) is None:
            return
        style = ttk.Style()
        self.parent.root.configure(bg=self.parent.bg_dark)
        
        # Configure ttk styles
        style.theme_use('clam')
        
        # Frame style
        style.configure('Dark.TFrame', 
                       background=self.parent.bg_dark,
                       borderwidth=0)
        
        style.configure('Card.TFrame',
                       background=self.parent.bg_lighter,
                       borderwidth=1,
                       relief='flat')
        
        # LabelFrame style
        style.configure('Dark.TLabelframe',
                       background=self.parent.bg_dark,
                       foreground=self.parent.fg_light,
                       borderwidth=1,
                       bordercolor=self.parent.border_color)
        
        style.configure('Dark.TLabelframe.Label',
                       background=self.parent.bg_dark,
                       foreground=self.parent.fg_light,
                       font=('Segoe UI', 10, 'bold'))
        
        # Label style
        style.configure('Dark.TLabel',
                       background=self.parent.bg_dark,
                       foreground=self.parent.fg_light,
                       font=('Segoe UI', 10))
        
        style.configure('Title.TLabel',
                       background=self.parent.bg_dark,
                       foreground=self.parent.accent_blue,
                       font=('Segoe UI', 12, 'bold'))
        
        # Button style - Vibrant Light Blue
        style.configure('Modern.TButton',
                       background=self.parent.accent_blue,
                       foreground='#050608',
                       borderwidth=0,
                       focuscolor='none',
                       font=('Segoe UI', 10, 'bold'),
                       padding=(20, 10))
        
        style.map('Modern.TButton',
                 background=[('active', self.parent.accent_blue_hover),
                           ('pressed', self.parent.accent_blue_active)],
                 foreground=[('active', '#050608'),
                           ('pressed', '#050608')])
        
        # Secondary button
        style.configure('Secondary.TButton',
                       background=self.parent.bg_lighter,
                       foreground=self.parent.fg_light,
                       borderwidth=1,
                       bordercolor=self.parent.border_color,
                       focuscolor='none',
                       font=('Segoe UI', 9),
                       padding=(15, 8))
        
        style.map('Secondary.TButton',
                 background=[('active', '#3a3a3a'),
                           ('pressed', '#2a2a2a')],
                 foreground=[('active', self.parent.fg_light),
                           ('pressed', self.parent.fg_light)])
        
        # Entry style
        style.configure('Dark.TEntry',
                       fieldbackground=self.parent.bg_lighter,
                       foreground=self.parent.fg_light,
                       borderwidth=1,
                       bordercolor=self.parent.border_color,
                       insertcolor=self.parent.fg_light,
                       font=('Segoe UI', 10),
                       padding=8)
        
        # Checkbutton style
        style.configure('Dark.TCheckbutton',
                       background=self.parent.bg_dark,
                       foreground=self.parent.fg_light,
                       focuscolor='none',
                       font=('Segoe UI', 9))
        
        # Progressbar style
        style.configure('Modern.Horizontal.TProgressbar',
                       background=self.parent.accent_blue,
                       troughcolor=self.parent.bg_lighter,
                       borderwidth=0,
                       lightcolor=self.parent.accent_blue,
                       darkcolor=self.parent.accent_blue)
        
        # Treeview style
        style.configure('Dark.Treeview',
                       background=self.parent.bg_lighter,
                       foreground=self.parent.fg_light,
                       fieldbackground=self.parent.bg_lighter,
                       borderwidth=0,
                       font=('Segoe UI', 9))
        
        style.configure('Dark.Treeview.Heading',
                       background=self.parent.bg_darker,
                       foreground=self.parent.fg_light,
                       borderwidth=1,
                       bordercolor=self.parent.border_color,
                       font=('Segoe UI', 9, 'bold'))
        
        style.map('Dark.Treeview',
                 background=[('selected', self.parent.accent_blue)],
                 foreground=[('selected', 'white')])
        
        # Scrollbar style
        style.configure('Dark.Vertical.TScrollbar',
                       background=self.parent.bg_lighter,
                       troughcolor=self.parent.bg_dark,
                       borderwidth=0,
                       arrowcolor=self.parent.fg_muted,
                       darkcolor=self.parent.bg_lighter,
                       lightcolor=self.parent.bg_lighter)
        
        style.map('Dark.Vertical.TScrollbar',
                 background=[('active', self.parent.bg_lighter)],
                 arrowcolor=[('active', self.parent.fg_light)])
        
        # Combobox style
        style.configure('Dark.TCombobox',
                       fieldbackground=self.parent.bg_darker,
                       background=self.parent.bg_darker,
                       foreground=self.parent.fg_light,
                       arrowcolor=self.parent.accent_blue,
                       bordercolor=self.parent.border_color,
                       darkcolor=self.parent.bg_darker,
                       lightcolor=self.parent.bg_darker,
                       font=('Segoe UI', 10),
                       padding=5)
        
        style.map('Dark.TCombobox',
                 fieldbackground=[('readonly', self.parent.bg_darker)],
                 foreground=[('readonly', self.parent.fg_light)],
                 selectbackground=[('readonly', self.parent.accent_blue)],
                 selectforeground=[('readonly', 'white')])
        
        # Notebook style
        style.configure('Dark.TNotebook', 
                       background=self.parent.bg_dark,
                       borderwidth=0,
                       padding=0)
        style.configure('Dark.TNotebook.Tab',
                       background=self.parent.bg_lighter,
                       foreground=self.parent.fg_muted,
                       padding=[20, 10],
                       font=('Segoe UI', 10, 'bold'),
                       borderwidth=0)
        style.map('Dark.TNotebook.Tab',
                 background=[('selected', self.parent.accent_blue), ('!selected', self.parent.bg_lighter)],
                 foreground=[('selected', 'white'), ('!selected', self.parent.fg_muted)],
                 padding=[('selected', [22, 12]), ('!selected', [20, 10])],
                 expand=[('selected', [1, 1, 1, 0]), ('!selected', [0, 0, 0, 0])])
        
        # Override Combobox dropdown (requires popdown style)
        self.parent.root.option_add('*TCombobox*Listbox.background', self.parent.bg_lighter)
        self.parent.root.option_add('*TCombobox*Listbox.foreground', self.parent.fg_light)
        self.parent.root.option_add('*TCombobox*Listbox.selectBackground', self.parent.accent_blue)
        self.parent.root.option_add('*TCombobox*Listbox.selectForeground', 'white')
        self.parent.root.option_add('*TCombobox*Listbox.font', ('Segoe UI', 10))

    def apply_theme(self, mode="dark", font_size=None):
        """Apply dark or light theme. font_size: 8-14 for aksesibilitas."""
        if mode == "light":
            self.parent.bg_dark = "#f0f2f5"
            self.parent.bg_darker = "#e4e6eb"
            self.parent.bg_lighter = "#ffffff"
            self.parent.fg_light = "#050608"
            self.parent.fg_muted = "#65676b"
            self.parent.border_color = "#dddfe2"
            self.parent.accent_blue = "#0084ff"
            self.parent.accent_blue_hover = "#2d9bf0"
            self.parent.accent_blue_active = "#0066cc"
        else:
            self.parent.bg_dark = "#0a0c10"
            self.parent.bg_darker = "#050608"
            self.parent.bg_lighter = "#161b22"
            self.parent.fg_light = "#f0f6fc"
            self.parent.fg_muted = "#8b949e"
            self.parent.border_color = "#30363d"
            self.parent.accent_blue = "#00d2ff"
            self.parent.accent_blue_hover = "#33e0ff"
            self.parent.accent_blue_active = "#00b8e6"
        self.setup_dark_theme()
        if font_size is not None and 8 <= font_size <= 14:
            self.parent.font_size_var.set(font_size)
            if getattr(self.parent, 'details_text', None) and self.parent.details_text.winfo_exists():
                self.parent.details_text.config(font=('Segoe UI', font_size))
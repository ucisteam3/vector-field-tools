"""
UI Components Module
Custom UI widgets for the YouTube Heatmap Analyzer application
"""

import tkinter as tk
from tkinter import Canvas
import sys



class CustomLogger:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.stdout = sys.stdout
        self.stderr = sys.stderr
        self.replacing = False # Track if next write should overwrite

    def write(self, message):
        self.stdout.write(message)
        if self.text_widget and self.text_widget.winfo_exists():
            self.text_widget.after(0, lambda: self._handle_write(message))

    def _handle_write(self, message):
        if not message: return
        try:
            # Handle carriage returns and newlines by ensuring each part is on its own line
            # This fulfills the user's request for "per baris saja" (per line)
            
            # 1. First, handle carriage returns by converting them to newlines for the UI
            clean_message = message.replace('\r', '\n')
            
            # 2. Split into lines to filter out empty ones and keep it tidy
            lines = [line.strip() for line in clean_message.split('\n') if line.strip()]
            
            for line in lines:
                # Add a prefix if it's a progress update but lacks a bracket (rare for yt-dlp)
                # Ensure each line ends with a newline in the widget
                self.text_widget.insert(tk.END, line + '\n')
            
            # Always scroll to bottom
            self.text_widget.see(tk.END)
        except:
            pass

    def flush(self):
        self.stdout.flush()
        self.stderr.flush()


class ModernButton(tk.Canvas):
    def __init__(self, parent, text, command=None, width=150, height=40, radius=20, bg_color="#00d2ff", hover_color="#33e0ff", fg_color="#050608"):
        # Safely get parent background to blend in
        try:
            bg_val = parent["bg"]
        except:
            try:
                bg_val = parent.cget("background")
            except:
                bg_val = "#0a0c10" # Default app dark
        
        super().__init__(parent, width=width, height=height, bg=bg_val, highlightthickness=0)
        self.command = command
        self.width = width
        self.height = height
        self.radius = radius
        self.bg_color = bg_color
        self.hover_color = hover_color
        self.fg_color = fg_color
        
        self.rect = self._draw_rounded_rect(0, 0, width, height, radius, bg_color)
        self.text = self.create_text(width/2, height/2, text=text, fill=fg_color, font=("Segoe UI", 10, "bold"))
        
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)
        self.bind("<Button-1>", self._on_click)
        
    def _draw_rounded_rect(self, x1, y1, x2, y2, r, color):
        points = [x1+r, y1, x1+r, y1, x2-r, y1, x2-r, y1, x2, y1, x2, y1+r, x2, y1+r, x2, y2-r, x2, y2-r, x2, y2, x2-r, y2, x2-r, y2, x1+r, y2, x1+r, y2, x1, y2, x1, y2-r, x1, y2-r, x1, y1+r, x1, y1+r, x1, y1]
        return self.create_polygon(points, fill=color, smooth=True)

    def _on_enter(self, event):
        self.itemconfig(self.rect, fill=self.hover_color)
        self.config(cursor="hand2")

    def _on_leave(self, event):
        self.itemconfig(self.rect, fill=self.bg_color)

    def _on_click(self, event):
        if self.command:
            self.command()

"""
Accordion Widget for Collapsible Sections
"""
import tkinter as tk
from tkinter import ttk

class AccordionSection:
    """A collapsible section widget"""
    
    def __init__(self, parent, title, bg_color='#2b2b2b', fg_color='white', accent_color='#3498db'):
        self.parent = parent
        self.title = title
        self.bg_color = bg_color
        self.fg_color = fg_color
        self.accent_color = accent_color
        self.is_open = False
        
        # Main container
        self.container = tk.Frame(parent, bg=bg_color)
        
        # Header (clickable)
        self.header = tk.Frame(self.container, bg=bg_color, cursor='hand2')
        self.header.pack(fill='x', pady=(0, 1))
        
        # Arrow indicator
        self.arrow_label = tk.Label(
            self.header, 
            text=">", 
            bg=bg_color, 
            fg=accent_color,
            font=('Segoe UI', 10, 'bold'),
            width=2
        )
        self.arrow_label.pack(side=tk.LEFT, padx=(5, 0))
        
        # Title label
        self.title_label = tk.Label(
            self.header,
            text=title,
            bg=bg_color,
            fg=fg_color,
            font=('Segoe UI', 10, 'bold'),
            anchor='w'
        )
        self.title_label.pack(side=tk.LEFT, fill='x', expand=True, padx=5, pady=8)
        
        # Content frame (collapsible)
        self.content_frame = tk.Frame(self.container, bg='#1e1e1e')
        
        # Bind click events
        self.header.bind('<Button-1>', self.toggle)
        self.arrow_label.bind('<Button-1>', self.toggle)
        self.title_label.bind('<Button-1>', self.toggle)
        
    def toggle(self, event=None):
        """Toggle section open/close"""
        if self.is_open:
            self.close()
        else:
            self.open()
    
    def open(self):
        """Open the section"""
        self.is_open = True
        self.arrow_label.config(text="v")
        self.content_frame.pack(fill='both', expand=True, padx=5, pady=(0, 5))
    
    def close(self):
        """Close the section"""
        self.is_open = False
        self.arrow_label.config(text=">")
        self.content_frame.pack_forget()
    
    def get_content_frame(self):
        """Get the content frame to add widgets to"""
        return self.content_frame
    
    def pack(self, **kwargs):
        """Pack the container"""
        self.container.pack(**kwargs)
    
    def grid(self, **kwargs):
        """Grid the container"""
        self.container.grid(**kwargs)

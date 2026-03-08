"""
API Manager Module
Handles API key management for Gemini (OpenAI is configured via openai.txt)
"""

import tkinter as tk
from tkinter import messagebox
import threading

try:
    from google import genai
except ImportError:
    genai = None


class APIManager:
    """Manages API keys and initialization for AI services"""
    
    def __init__(self, parent):
        """
        Initialize API Manager
        
        Args:
            parent: Reference to YouTubeHeatmapAnalyzer instance
        """
        self.parent = parent
    
    def initialize_gemini_api(self):
        """Initialize Gemini API with the current user-provided key"""
        if not self.parent.user_gemini_keys:
            self.parent.gemini_available = False
            return False
            
        try:
            key = self.parent.user_gemini_keys[self.parent.current_gemini_idx]
            self.parent.gemini_client = genai.Client(api_key=key)
            self.parent.gemini_available = True
            print(f"  [SUCCESS] Gemini API {self.parent.current_gemini_idx + 1}/{len(self.parent.user_gemini_keys)} aktif.")
            return True
        except Exception as e:
            print(f"  [ERROR] Gemini API config failed (Key {self.parent.current_gemini_idx + 1}): {e}")
            if self.parent.rotate_gemini.get() and len(self.parent.user_gemini_keys) > 1:
                return self.rotate_gemini_api_key()
            self.parent.gemini_available = False
            return False

    def on_api_save(self):
        """Save API keys and re-initialize"""
        self.parent.save_config()
        self.initialize_gemini_api()

    def rotate_gemini_api_key(self):
        """Rotate to the next Gemini API key in the user list"""
        if not self.parent.user_gemini_keys or not self.parent.rotate_gemini.get():
            self.parent.gemini_available = False
            return False
            
        # Track initial index to prevent infinite loop
        if not hasattr(self, '_rotation_start_idx'):
            self._rotation_start_idx = self.parent.current_gemini_idx
        
        self.parent.current_gemini_idx = (self.parent.current_gemini_idx + 1) % len(self.parent.user_gemini_keys)
        
        # If we've come full circle, all keys have failed
        if self.parent.current_gemini_idx == self._rotation_start_idx:
            print("  [ERROR] Semua Gemini API key telah dicoba dan gagal.")
            self.parent.gemini_available = False
            delattr(self, '_rotation_start_idx')  # Clean up
            return False
            
        print(f"  [RATE LIMIT] Berputar ke Gemini API Key {self.parent.current_gemini_idx + 1}/{len(self.parent.user_gemini_keys)}...")
        result = self.initialize_gemini_api()
        
        # If successful, clean up tracking
        if result and hasattr(self, '_rotation_start_idx'):
            delattr(self, '_rotation_start_idx')
            
        return result

    def update_api_listboxes(self):
        self.parent.gemini_listbox.delete(0, tk.END)
        for i, key in enumerate(self.parent.user_gemini_keys):
            masked_key = key[:4] + "*" * (len(key)-8) + key[-4:] if len(key) > 8 else "****"
            status = self.parent.gemini_key_statuses.get(key, "")
            display_text = f"{masked_key} {status}"
            self.parent.gemini_listbox.insert(tk.END, display_text)
            # Apply color based on status
            if "[AKTIF]" in status: self.parent.gemini_listbox.itemconfig(i, fg="#00ff00")
            elif "[LIMIT]" in status: self.parent.gemini_listbox.itemconfig(i, fg="#ffcc00")
            elif "[ERROR]" in status: self.parent.gemini_listbox.itemconfig(i, fg="#ff4400")
            
        if getattr(self.parent, 'groq_listbox', None):
            self.parent.groq_listbox.delete(0, tk.END)
        self.parent.root.update_idletasks()

    def add_gemini_key(self):
        raw_text = self.parent.gemini_entry.get("1.0", tk.END).strip()
        if not raw_text:
            messagebox.showwarning("Peringatan", "Masukkan minimal satu API Key Gemini!")
            return
            
        keys = [k.strip() for k in raw_text.split('\n') if k.strip()]
        added = 0
        existed = 0
        for key in keys:
            if key not in self.parent.user_gemini_keys:
                self.parent.user_gemini_keys.append(key)
                added += 1
            else:
                existed += 1
                
        if added > 0:
            self.parent.gemini_entry.delete("1.0", tk.END)
            self.parent.update_api_listboxes()
            self.parent.save_config()
            self.parent.current_gemini_idx = 0 
            self.initialize_gemini_api()
            msg = f"{added} API Key Gemini berhasil ditambahkan!"
            if existed > 0:
                msg += f"\n({existed} key lainnya sudah terdaftar)"
            messagebox.showinfo("Berhasil", msg)
        else:
            messagebox.showinfo("Informasi", f"Semua key ({existed}) sudah terdaftar dalam sistem.")

    def test_all_gemini_keys(self):
        """Test all Gemini keys in a background thread"""
        if not self.parent.user_gemini_keys:
            messagebox.showwarning("Peringatan", "Tidak ada API Key Gemini untuk ditest!")
            return

        def task():
            total = len(self.parent.user_gemini_keys)
            for i, key in enumerate(self.parent.user_gemini_keys):
                self.parent.progress_var.set(f"Testing Gemini Key {i+1}/{total}...")
                self.parent.gemini_key_statuses[key] = "[TESTING...]"
                self.parent.root.after(0, self.parent.update_api_listboxes)
                
                try:
                    test_client = genai.Client(api_key=key)
                    # Minimal test call
                    test_client.models.generate_content(
                        model='gemini-2.0-flash',
                        contents="hi"
                    )
                    self.parent.gemini_key_statuses[key] = "[AKTIF]"
                except Exception as e:
                    err = str(e).lower()
                    if "429" in err or "quota" in err or "limit" in err:
                        self.parent.gemini_key_statuses[key] = "[LIMIT]"
                    else:
                        print(f"Test Key Error ({key[:5]}...): {e}")
                        self.parent.gemini_key_statuses[key] = "[ERROR]"
                
                self.parent.root.after(0, self.parent.update_api_listboxes)

            self.parent.progress_var.set(f"Selesai mengetes {total} API Key Gemini.")
            self.parent.root.after(0, lambda: messagebox.showinfo("Selesai", f"Selesai mengetes {total} API Key Gemini.\nCek tabel untuk status masing-masing key."))
            
        import threading
        threading.Thread(target=task, daemon=True).start()

    def remove_gemini_key(self):
        selected = self.parent.gemini_listbox.curselection()
        if selected:
            idx = selected[0]
            self.parent.user_gemini_keys.pop(idx)
            self.parent.current_gemini_idx = 0 # Reset to safety
            self.parent.update_api_listboxes()
            self.parent.save_config()
            self.initialize_gemini_api()
        else:
            messagebox.showwarning("Peringatan", "Pilih key yang ingin dihapus terlebih dahulu!")

    def clear_all_gemini_keys(self):
        if not self.parent.user_gemini_keys: return
        if messagebox.askyesno("Konfirmasi", "Apakah Anda yakin ingin menghapus SEMUA Google Gemini API keys?"):
            self.parent.user_gemini_keys.clear()
            self.parent.current_gemini_idx = 0
            self.parent.update_api_listboxes()
            self.parent.save_config()
            self.initialize_gemini_api()
            messagebox.showinfo("Berhasil", "Semua Gemini API Keys berhasil dihapus.")

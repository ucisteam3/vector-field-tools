"""
System Manager Module
Handles system specs detection and encoder probing
"""

import subprocess
import platform
import psutil


class SystemManager:
    """Manages system specifications and encoder detection"""
    
    def __init__(self, parent):
        """Initialize System Manager"""
        self.parent = parent

    def probe_encoders(self):
        """
        [AUTOCLIP STYLE] Detect best FFmpeg hardware encoder
        Mimics the robust probing seen in other advanced tools.
        """
        print("\n" + "="*50)
        print("[HARDWARE PROBE] Mendeteksi Encoder Video Terbaik...")
        print("="*50)
        
        # 1. Check list of encoders
        try:
            res = subprocess.run(['ffmpeg', '-encoders'], capture_output=True, text=True, creationflags=0x08000000)
            output = res.stdout
            print(f"  [INFO] FFmpeg -encoders check: OK")
        except FileNotFoundError:
            print(f"  [ERROR] FFmpeg tidak ditemukan! Fallback ke CPU.")
            return 'libx264'
            
        # Priority list (NVIDIA > AMD > INTEL > MAC > CPU)
        candidates = [
            ('h264_nvenc', 'NVIDIA NVENC (Cepat & Tajam)'),
            ('h264_amf', 'AMD AMF (Radeon)'),
            ('h264_qsv', 'Intel QuickSync (iGPU)'),
            ('h264_videotoolbox', 'Apple M1/M2 VideoToolbox'),
        ]
        
        found_encoder = None
        
        for enc_id, friendly_name in candidates:
            if enc_id in output:
                print(f"  [INFO] Probe encoder: {friendly_name} ({enc_id}) ...")
                
                # 2. DUMMY CONVERSION TEST
                # Just seeing it in list isn't enough (phantom drivers). We must test it.
                dummy_test_cmd = [
                    'ffmpeg', '-y', '-f', 'lavfi', '-i', 'color=c=black:s=1280x720:d=1',
                    '-c:v', enc_id, '-f', 'null', '-'
                ]
                
                try:
                    # Run silent test

                    if test_res.returncode == 0:
                        print(f"  [SUCCESS] Probe BERHASIL! Menggunakan: {friendly_name}")
                        found_encoder = enc_id
                        self.parent.best_encoder_name = friendly_name
                        break
                    else:
                        print(f"  [WARN] Probe GAGAL: {enc_id} ada di list, tapi error saat tes.")
                        # print(f"  -> Error details: {test_res.stderr[:200]}") # Debug allowed
                except Exception as e:
                    print(f"  [WARN] Probe Error: {e}")
            else:
                pass # print(f"  [INFO] Skip: {friendly_name} tidak tersedia.")
        
        if not found_encoder:
            print(f"  [INFO] Tidak ada hardware encoder yang lolos probe. Fallback ke 'libx264' (CPU).")
            self.parent.best_encoder_name = "CPU (libx264)"
            return 'libx264'
            
        return found_encoder

    def check_system_specs(self):
        """Smart detection of PC specs (Sultan vs Kentang)"""
        try:
            # Detect RAM on Windows - Using powershell for better reliability with large RAM
            cmd = "powershell (Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory"
            res = subprocess.run(cmd, shell=True, capture_output=True, text=True, creationflags=0x08000000)
            if res.returncode == 0 and res.stdout.strip():
                mem_bytes = int(res.stdout.strip())
                self.parent.ram_gb = round(mem_bytes / (1024**3))
            
            # Fallback if powershell fails
            if self.parent.ram_gb == 0:
                cmd = "wmic computersystem get totalphysicalmemory"
                res = subprocess.run(cmd, shell=True, capture_output=True, text=True, creationflags=0x08000000)
                lines = [l.strip() for l in res.stdout.split('\n') if l.strip()]
                if len(lines) > 1:
                    self.parent.ram_gb = round(int(lines[1]) / (1024**3))
            
            # Detect NVIDIA GPU
            try:
                nvidia_check = subprocess.run(['nvidia-smi'], capture_output=True, text=True, creationflags=0x08000000)
                self.parent.has_nvidia = (nvidia_check.returncode == 0)
            except:
                self.parent.has_nvidia = False
            
            # CPU cores
            self.parent.cpu_cores = psutil.cpu_count(logical=False) or 4
            
            # Determine PC tier
            if self.parent.ram_gb >= 32 and self.parent.has_nvidia:
                self.parent.pc_tier = "sultan"
                self.parent.pc_level = "🔥 Sultan (Dewa)"
            elif self.parent.ram_gb >= 16:
                self.parent.pc_tier = "mantap"
                self.parent.pc_level = "💪 Mantap (Bagus)"
            else:
                self.parent.pc_tier = "kentang"
                self.parent.pc_level = "🥔 Kentang (Standar)"
            
            print(f"  [SYSTEM] Specs: {self.parent.ram_gb}GB RAM, {self.parent.cpu_cores} Cores, NVIDIA: {self.parent.has_nvidia}")
            print(f"  [TIER] PC Level: {self.parent.pc_level}")
            
        except Exception as e:
            print(f"  [ERROR] Gagal mendeteksi spek: {e}")
            self.parent.ram_gb = 8
            self.parent.cpu_cores = 4
            self.parent.has_nvidia = False
            self.parent.pc_tier = "kentang"
            self.parent.pc_level = "🥔 Kentang (Standar)"

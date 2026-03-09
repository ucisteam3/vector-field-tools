@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo Mematikan proses Node yang berjalan (jika ada)...
taskkill /F /IM node.exe 2>nul
if errorlevel 1 (echo Tidak ada proses Node.) else (echo Node berhasil dimatikan.)
echo.

echo Mematikan backend lama di port 8001 (jika ada)...
python -c "import subprocess,re; out=subprocess.check_output(['netstat','-ano'],text=True,errors='ignore'); pids=set(re.findall(r':8001\\s+[^\\s]+\\s+[^\\s]+\\s+LISTENING\\s+(\\d+)',out)); print('PIDs',sorted(pids)); [subprocess.run(['taskkill','/F','/PID',pid],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL) for pid in pids]"
timeout /t 1 /nobreak >nul
python -c "import subprocess,re; out=subprocess.check_output(['netstat','-ano'],text=True,errors='ignore'); pids=set(re.findall(r':8001\\s+[^\\s]+\\s+[^\\s]+\\s+LISTENING\\s+(\\d+)',out)); print('[WARNING] Port 8001 masih dipakai oleh PID '+', '.join(sorted(pids)) if pids else 'Port 8001 kosong')"
echo.

echo Menjalankan Backend (API)...
start "Backend - API" cmd /k "cd /d ""%~dp0"" && python server.py"

timeout /t 3 /nobreak >nul
echo Menjalankan Frontend...
start "Frontend - Web" cmd /k "cd /d ""%~dp0frontend"" && npm run dev"

echo.
echo Backend dan Frontend berjalan di jendela terpisah.
echo Buka browser: http://localhost:3000
echo.
pause
endlocal

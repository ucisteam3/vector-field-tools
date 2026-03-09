@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo Mematikan proses Node yang berjalan (jika ada)...
taskkill /F /IM node.exe 2>nul
if errorlevel 1 (echo Tidak ada proses Node.) else (echo Node berhasil dimatikan.)
echo.

echo Mematikan backend lama di port 8001 (jika ada)...
python "scripts\\kill_port.py" 8001 5
if errorlevel 1 (
  echo.
  echo GAGAL mematikan proses backend di port 8001. Tutup semua jendela backend lama lalu jalankan lagi.
  pause
  exit /b 1
)
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

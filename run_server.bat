@echo off
cd /d "%~dp0"

echo Mematikan proses Node yang berjalan (jika ada)...
taskkill /F /IM node.exe 2>nul
if %errorlevel% equ 0 (echo Node berhasil dimatikan.) else (echo Tidak ada proses Node.)
echo.

echo Menjalankan Backend (API)...
start "Backend - API" cmd /k "cd /d "%~dp0" && python server.py"

timeout /t 3 /nobreak >nul
echo Menjalankan Frontend...
start "Frontend - Web" cmd /k "cd /d "%~dp0frontend" && npm run dev"

echo.
echo Backend dan Frontend berjalan di jendela terpisah.
echo Buka browser: http://localhost:3000
echo.
pause

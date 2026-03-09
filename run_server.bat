@echo off
setlocal EnableExtensions EnableDelayedExpansion
cd /d "%~dp0"

echo Mematikan proses Node yang berjalan (jika ada)...
taskkill /F /IM node.exe 2>nul
if errorlevel 1 (echo Tidak ada proses Node.) else (echo Node berhasil dimatikan.)
echo.

echo Mematikan backend lama di port 8001 (jika ada)...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8001" ^| findstr "LISTENING"') do (
  echo Kill PID %%a (port 8001)...
  taskkill /F /PID %%a >nul 2>nul
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

@echo off
echo Mematikan proses Node yang berjalan (jika ada)...
taskkill /F /IM node.exe 2>nul
if %errorlevel% equ 0 (echo Node berhasil dimatikan.) else (echo Tidak ada proses Node.)
echo.

echo Menjalankan backend server...
python server.py
pause

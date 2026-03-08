@echo off
chcp 65001 >nul
title Install Dependencies - YouTube Heatmap Analyzer
color 0B

echo ========================================
echo   Install Dependencies
echo   YouTube Heatmap Analyzer
echo ========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python tidak ditemukan!
    echo Silakan install Python dari https://www.python.org/
    echo Pastikan Python ditambahkan ke PATH saat instalasi.
    pause
    exit /b 1
)

echo [INFO] Python ditemukan
python --version
echo.

echo [INFO] Mengupgrade pip...
python -m pip install --upgrade pip
echo.

echo [INFO] Menginstall dependencies dari requirements.txt...
echo.
python -m pip install opencv-python numpy yt-dlp pydub SpeechRecognition matplotlib google-generativeai

if errorlevel 1 (
    echo.
    echo [ERROR] Gagal menginstall beberapa dependencies!
    pause
    exit /b 1
)

echo.
echo [INFO] Mencoba install pyaudio (opsional - bisa dilewati jika error)...
echo [INFO] Jika Visual Studio sudah terinstall, PyAudio akan bisa di-compile...
python -m pip install pyaudio >nul 2>&1
if errorlevel 1 (
    echo [INFO] pyaudio gagal diinstall - TIDAK MASALAH!
    echo [INFO] pyaudio hanya diperlukan untuk microphone input
    echo [INFO] Aplikasi tetap bisa berjalan tanpa pyaudio
    echo.
    echo [CATATAN] Jika Visual Studio sudah terinstall tapi masih error:
    echo   1. Pastikan "Desktop development with C++" workload terinstall
    echo   2. Atau download wheel file dari: https://www.lfd.uci.edu/~gohlke/pythonlibs/#pyaudio
    echo   3. Atau jalankan: install_pyaudio_now.bat untuk install manual
) else (
    echo [SUCCESS] pyaudio berhasil diinstall!
)

echo.
echo ========================================
echo   Installasi selesai!
echo ========================================
echo.
echo Jalankan aplikasi dengan: run.bat
echo.
pause

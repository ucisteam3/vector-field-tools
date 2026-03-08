@echo off
chcp 65001 >nul
title YouTube Heatmap Analyzer
color 0A
REM Force UTF-8 output (avoid 'charmap' emoji errors)
set PYTHONUTF8=1
set PYTHONIOENCODING=utf-8

echo ========================================
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
echo [INFO] Memeriksa dependencies...

REM Check if required packages are installed (pyaudio is optional)
python -c "import cv2, numpy, yt_dlp, pydub, speech_recognition, matplotlib, groq; from google import genai; from PIL import Image" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] Beberapa dependencies belum terinstall
    echo [INFO] Menginstall dependencies...
    echo.
    python -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [ERROR] Gagal menginstall dependencies!
        echo Silakan jalankan: python -m pip install -r requirements.txt
        pause
        exit /b 1
    )
    echo.
    echo [SUCCESS] Dependencies berhasil diinstall!
    echo.
) else (
    echo [SUCCESS] Semua dependencies sudah terinstall
    echo.
)

echo [INFO] Menjalankan aplikasi...
echo.
python main.py

if errorlevel 1 (
    echo.
    echo [ERROR] Aplikasi mengalami error!
    pause
    exit /b 1
)

pause

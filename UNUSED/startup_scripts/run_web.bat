@echo off
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo AI Video Clipper - Web Application
echo.
echo Starting backend API on http://localhost:8000
echo Frontend will run on http://localhost:3000
echo.
echo Open TWO terminals:
echo   Terminal 1: python backend\server.py
echo   Terminal 2: cd frontend ^&^& npm run dev
echo.
echo Then open http://localhost:3000 in your browser
echo.

cd /d "%~dp0"
python backend\server.py

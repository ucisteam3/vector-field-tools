@echo off
echo AI Video Clipper - Web Application
echo.
echo Starting backend API on http://localhost:8000
echo Frontend will run on http://localhost:3000
echo.
echo Open TWO terminals:
echo   Terminal 1: python server.py
echo   Terminal 2: cd frontend ^&^& npm run dev
echo.
echo Then open http://localhost:3000 in your browser
echo.

REM Start backend in current window
python server.py

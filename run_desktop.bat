@echo off
setlocal enabledelayedexpansion

REM Run HEATMAP5 Electron Desktop
REM - Auto installs npm deps if missing
REM - Then launches Electron (npm start)

cd /d "%~dp0"

echo.
echo =========================================
echo HEATMAP5 Desktop - Electron Launcher
echo Project: %cd%
echo =========================================
echo.

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] npm not found. Please install Node.js LTS first.
  echo         https://nodejs.org/
  pause
  exit /b 1
)

if not exist "package.json" (
  echo [ERROR] package.json not found in this folder.
  pause
  exit /b 1
)

if not exist "node_modules" (
  echo [INFO] node_modules not found. Installing dependencies...
  call npm install
  if errorlevel 1 (
    echo [ERROR] npm install failed.
    pause
    exit /b 1
  )
)

echo [INFO] Starting Electron...
call npm start

echo.
echo [INFO] Electron exited.
pause
exit /b 0


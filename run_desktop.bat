@echo off
setlocal enabledelayedexpansion

REM Run HEATMAP5 Electron Desktop
REM - Auto installs npm deps if missing
REM - Kills existing backend/frontend ports
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

echo [INFO] Stopping any existing backend/frontend...
REM Kill processes holding ports 8001 (backend) and 3000 (frontend)
for %%P in (8001 3000) do (
  for /f "tokens=5" %%A in ('netstat -aon ^| findstr ":%%P" ^| findstr LISTENING') do (
    echo [INFO] Killing PID %%A on port %%P
    taskkill /F /PID %%A >nul 2>nul
  )
)

echo [INFO] Starting Electron...
call npm start

echo.
echo [INFO] Electron exited.
pause
exit /b 0


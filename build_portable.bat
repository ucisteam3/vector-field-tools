@echo off
setlocal enabledelayedexpansion

REM Build 100% portable desktop folder (no Python/Node required at runtime)
REM Output: dist-portable\win-unpacked\HEATMAP5.exe (folder)

cd /d "%~dp0"

echo.
echo =========================================
echo HEATMAP5 - Build Portable Desktop
echo =========================================
echo.

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] npm not found. Install Node.js LTS for BUILD step only.
  pause
  exit /b 1
)

where py >nul 2>nul
if errorlevel 1 (
  echo [ERROR] Python launcher (py) not found. Install Python for BUILD step only.
  pause
  exit /b 1
)

echo [1/5] Install root deps...
call npm install
if errorlevel 1 exit /b 1

echo [2/5] Build frontend (Next standalone)...
pushd "frontend"
call npm install
if errorlevel 1 popd & exit /b 1
call npm run build
if errorlevel 1 popd & exit /b 1
popd

echo [3/5] Build backend EXE (PyInstaller)...
py -3 -m pip install -U pyinstaller >nul
if errorlevel 1 exit /b 1

REM Build into portable-resources\backend
if exist "portable-resources\backend" rmdir /s /q "portable-resources\backend"
mkdir "portable-resources\backend"

py -3 -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --onedir ^
  --name "heatmap5_backend" ^
  --distpath "portable-resources\backend" ^
  --workpath "portable-resources\_pyi_work" ^
  --specpath "portable-resources\_pyi_spec" ^
  "desktop_backend_entry.py"
if errorlevel 1 exit /b 1

echo [4/5] Assemble frontend resources...
if exist "portable-resources\frontend" rmdir /s /q "portable-resources\frontend"
mkdir "portable-resources\frontend"

REM Next standalone server.js lives here:
REM frontend\.next\standalone\server.js
xcopy /e /i /y "frontend\.next\standalone\*" "portable-resources\frontend\" >nul

REM Copy static + public into expected locations:
mkdir "portable-resources\frontend\.next" >nul 2>nul
xcopy /e /i /y "frontend\.next\static" "portable-resources\frontend\.next\static" >nul
xcopy /e /i /y "frontend\public" "portable-resources\frontend\public" >nul

echo [5/5] Build Electron portable folder...
call npm run build:portable
if errorlevel 1 exit /b 1

echo.
echo DONE.
echo Output folder:
echo   %cd%\dist-portable\
echo.
pause
exit /b 0


@echo off
setlocal

REM ============================================================
REM Clarion Operator Launcher (Primary Entry Point)
REM - Starts backend using existing backend\start.bat convention
REM - Opens Command Center at http://localhost:5000/dashboard
REM ============================================================

cd /d "%~dp0"

echo [clarion] Starting backend service...
start "Clarion Backend" cmd /k "cd /d "%~dp0backend" && start.bat"

REM Give Flask a few seconds to boot before opening the command center.
timeout /t 5 /nobreak >nul

echo [clarion] Opening Command Center...
start "" "http://localhost:5000/dashboard"

echo.
echo [clarion] Done. If login is required, sign in to continue.
endlocal

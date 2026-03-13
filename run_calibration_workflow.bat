@echo off
:: Clarion Calibration Workflow — Windows double-click launcher
:: Place this file at the repo root and double-click to run.

title Clarion Calibration Workflow

echo.
echo ============================================================
echo   CLARION CALIBRATION WORKFLOW
echo ============================================================
echo.

:: Ask for CSV path (supports drag-and-drop into the prompt window)
set /p CSV_PATH="Drag your reviews CSV here (or type path): "

:: Strip surrounding quotes if dragged in
set CSV_PATH=%CSV_PATH:"=%

if "%CSV_PATH%"=="" (
    echo.
    echo ERROR: No CSV path provided. Exiting.
    pause
    exit /b 1
)

:: Move to repo root (same folder as this .bat)
cd /d "%~dp0"

echo.
echo Running workflow with:
echo   CSV: %CSV_PATH%
echo.

python automation\calibration\run_calibration_workflow.py --csv "%CSV_PATH%"

echo.
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Workflow failed. See output above.
) else (
    echo Workflow complete. Results are in data\calibration\runs\
)

echo.
pause

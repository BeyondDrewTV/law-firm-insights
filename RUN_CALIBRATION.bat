@echo off
setlocal

REM ============================================================
REM Clarion Calibration Launcher
REM Uses backend venv312 interpreter when available.
REM Usage:
REM   RUN_CALIBRATION.bat
REM   RUN_CALIBRATION.bat "data\calibration\inputs\real_reviews.csv"
REM ============================================================

cd /d "%~dp0"

set "PY_EXE=%~dp0backend\venv312\Scripts\python.exe"
if exist "%PY_EXE%" goto run

set "PY_EXE=python"
echo [clarion] WARNING: backend venv312 python not found; falling back to system python.

:run
if "%~1"=="" (
  "%PY_EXE%" automation\calibration\run_calibration_workflow.py
) else (
  "%PY_EXE%" automation\calibration\run_calibration_workflow.py --csv "%~1"
)

if errorlevel 1 (
  echo.
  echo [clarion] Calibration workflow failed.
) else (
  echo.
  echo [clarion] Calibration workflow complete. Review data\calibration\runs\
)

pause
endlocal

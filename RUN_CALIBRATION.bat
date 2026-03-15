@echo off
setlocal

REM ============================================================
REM  Clarion Calibration — One-Click Runner
REM
REM  Prerequisites:
REM    1. Backend must be running (START_CLARION.bat)
REM    2. Add your real Google Maps reviews to:
REM         data\calibration\inputs\real_reviews.csv
REM       Columns: review_text, rating, owner_response
REM
REM  What this does:
REM    1. Runs deterministic + AI benchmark on your reviews
REM    2. Writes per-chunk results to data\calibration\runs\<timestamp>\
REM    3. Analyzes disagreements and suggests phrases to add
REM    4. Writes disagreement_report.md to the run folder
REM ============================================================

cd /d "%~dp0"

set "PYTHON=%~dp0backend\venv312\Scripts\python.exe"
set "REVIEWS=%~dp0data\calibration\inputs\real_reviews.csv"

if not exist "%PYTHON%" (
    echo [ERROR] venv312 not found. Run backend\start.bat first.
    pause & exit /b 1
)

if not exist "%REVIEWS%" (
    echo [ERROR] No reviews file found at:
    echo   %REVIEWS%
    echo.
    echo Create that CSV with columns: review_text,rating,owner_response
    echo Then re-run this bat.
    pause & exit /b 1
)

echo.
echo [clarion] Running calibration workflow...
echo [clarion] Reviews: %REVIEWS%
echo.

"%PYTHON%" automation\calibration\run_calibration_workflow.py --csv "%REVIEWS%"

if errorlevel 1 (
    echo.
    echo [clarion] Calibration workflow failed. Check output above.
    pause & exit /b 1
)

echo.
echo [clarion] Analyzing disagreements...
echo.

"%PYTHON%" automation\calibration\analyze_disagreements.py

if errorlevel 1 (
    echo [clarion] Disagreement analysis failed. Run manually:
    echo   python automation\calibration\analyze_disagreements.py
)

echo.
echo [clarion] Done. Check data\calibration\runs\ for results.
echo [clarion] Open disagreement_report.md in the latest run folder to see phrase suggestions.
echo.
pause
endlocal

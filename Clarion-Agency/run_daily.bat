@echo off
cd /d "%~dp0"
echo.
echo ============================================================
echo   Clarion Daily Run
echo   Conversation Discovery + Competitive Intel + Comms
echo ============================================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo   ERROR: Python not found.
    echo   Install Python 3.10+ and make sure it is on your PATH.
    echo.
    pause
    exit /b 1
)

echo   Starting daily agents...
echo   This takes 1-3 minutes.
echo.

python run_daily.py

if errorlevel 1 (
    echo.
    echo ============================================================
    echo   Something went wrong. Check the output above.
    echo   If the API key is missing, check Clarion-Agency\.env
    echo ============================================================
) else (
    echo.
    echo ============================================================
    echo   Done. Reports written to:
    echo     reports\market\
    echo     reports\comms\
    echo.
    echo   Run run_clarion_agent_office.bat on Fridays for the
    echo   full weekly brief with executive synthesis.
    echo ============================================================
)

echo.
pause

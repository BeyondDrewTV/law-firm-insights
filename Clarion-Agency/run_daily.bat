@echo off
cd /d "%~dp0"
echo.
echo ============================================================
echo   Clarion LEAN Office Run  (daily)
echo   Prospect Intel -> Outbound -> Content -> Execution
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

echo   Starting lean office run...
echo   This takes 3-6 minutes (prospect discovery + outbound drafting + content).
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
    echo     reports\sales\       (prospect intel + outreach drafts)
    echo     reports\growth\      (content artifacts)
    echo     data\publish_ready\ (content ready to post)
    echo     memory\outbound_email_log.md  (send results)
    echo.
    echo   For the full weekly synthesis (Chief of Staff, market intel):
    echo     run_clarion_agent_office.bat --full-office
    echo ============================================================
)

echo.
pause

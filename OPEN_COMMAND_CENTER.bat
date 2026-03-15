@echo off
setlocal

REM Opens Clarion internal command center without starting services.
start "" "http://localhost:5000/internal/command-center/"

endlocal

@echo off
setlocal

REM Opens internal tools launcher route (requires running backend + admin/dev access).
start "" "http://localhost:5000/internal/tools/"

endlocal

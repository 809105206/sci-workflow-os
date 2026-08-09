@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 scripts\serve-console.py
) else (
  python scripts\serve-console.py
)
pause

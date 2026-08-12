@echo off
setlocal
cd /d "%~dp0"
if exist "console\dist\index.html" (
  where py >nul 2>nul
  if not errorlevel 1 (
    py -3 scripts\serve-console.py
  ) else (
    python scripts\serve-console.py
  )
  pause
  exit /b %errorlevel%
)
if exist "SCI-WORKFLOW-CONSOLE.html" (
  start "" "%CD%\SCI-WORKFLOW-CONSOLE.html"
  exit /b 0
)
echo Built console not found. Run scripts\start-console first.
pause

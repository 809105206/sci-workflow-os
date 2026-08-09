@echo off
setlocal
cd /d "%~dp0"
echo Trusted setup may install missing user-level tools and project dependencies.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup-codex.ps1" -Trusted
if errorlevel 1 (
  echo.
  echo Trusted setup did not finish. Keep this window open and copy the error message.
  pause
  exit /b 1
)
pause

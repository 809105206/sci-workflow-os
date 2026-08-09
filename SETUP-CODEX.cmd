@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\setup-codex.ps1"
if errorlevel 1 (
  echo.
  echo Setup stopped. Review the message above or run SETUP-CODEX-TRUSTED.cmd.
  pause
  exit /b 1
)
pause

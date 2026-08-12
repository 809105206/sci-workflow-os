@echo off
setlocal
cd /d "%~dp0"
where uv >nul 2>nul
if errorlevel 1 (
  echo uv not found. Run SETUP-CODEX.cmd first.
  pause
  exit /b 1
)
uv run --frozen sciops credentials export
if errorlevel 1 (
  pause
  exit /b 1
)
explorer /select,"%CD%\.sciops-credentials.local.json"
echo Private credential JSON exported. Never upload or share this file.
pause

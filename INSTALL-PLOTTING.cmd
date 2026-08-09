@echo off
setlocal
cd /d "%~dp0"
echo SCI Workflow OS - open-source plotting setup
echo This installs uv, Python 3.12, Matplotlib and Plotly for the current user.
echo.
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\install-plotting.ps1"
if errorlevel 1 (
  echo.
  echo Installation did not finish. Keep this window open and copy the error message.
  pause
  exit /b 1
)
echo.
echo Plotting environment is ready.
pause

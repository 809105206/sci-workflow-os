@echo off
setlocal
cd /d "%~dp0"
set "CG=%CD%\.tools\codegraph\node_modules\.bin\codegraph.cmd"
if exist "%CG%" (
  call "%CG%" sync .
) else (
  where codegraph >nul 2>nul
  if errorlevel 1 (
    echo CodeGraph is not installed. Run SETUP-CODEX.cmd first.
  ) else (
    codegraph sync .
  )
)
uv run sciops codex resume
pause

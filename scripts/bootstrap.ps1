$ErrorActionPreference = "Stop"

$ProjectDir = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $ProjectDir

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    winget install --id astral-sh.uv --exact --source winget
}

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    winget install --id GitHub.cli --exact --source winget
}

if (-not (Get-Command quarto -ErrorAction SilentlyContinue)) {
    winget install --id Posit.Quarto --exact --source winget
}

uv sync --extra data --group dev
uv run sciops audit templates/project
uv run pytest

Write-Host "SCI Workflow OS is ready. Run: uv run sciops doctor"

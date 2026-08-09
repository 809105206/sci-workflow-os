param(
    [switch]$Trusted
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$ProjectDir = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectDir

function Refresh-Path {
    $machine = [Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
}

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    if (-not $Trusted) {
        throw "uv is missing. Run SETUP-CODEX-TRUSTED.cmd for a one-time trusted setup."
    }
    if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
        throw "Windows Package Manager is required to install uv automatically."
    }
    & winget install --id astral-sh.uv --exact --source winget --accept-package-agreements --accept-source-agreements
    if ($LASTEXITCODE -ne 0) { throw "uv installation failed." }
    Refresh-Path
}

Write-Host "Installing the isolated SCI Workflow OS environment..."
& uv sync --extra data --extra figures --group dev
if ($LASTEXITCODE -ne 0) { throw "Project dependency installation failed." }

$CodeGraph = $null
$Npm = Get-Command npm -ErrorAction SilentlyContinue
if ($null -ne $Npm) {
    Write-Host "Installing project-local CodeGraph 1.5.0..."
    & npm install --prefix .tools/codegraph --no-save @colbymchenry/codegraph@1.5.0
    if ($LASTEXITCODE -ne 0) { throw "CodeGraph installation failed." }
    $CodeGraph = Join-Path $ProjectDir ".tools\codegraph\node_modules\.bin\codegraph.cmd"
}
else {
    $Existing = Get-Command codegraph -ErrorAction SilentlyContinue
    if ($null -ne $Existing) {
        $CodeGraph = $Existing.Source
    }
    elseif ($Trusted) {
        Write-Host "Installing the pinned standalone CodeGraph build in this project..."
        $Installer = Join-Path $ProjectDir "scripts\install-codegraph.ps1"
        $CodeGraph = & $Installer -ProjectDir $ProjectDir
    }
    else {
        Write-Warning "CodeGraph skipped because npm is missing. Core research workflow remains available."
    }
}

if ($null -ne $CodeGraph) {
    if (Test-Path ".codegraph") {
        & $CodeGraph sync .
    }
    else {
        & $CodeGraph init .
    }
    if ($LASTEXITCODE -ne 0) { throw "CodeGraph indexing failed." }
}

if ($Trusted) {
    & uv run sciops codex trust --yes
    if ($LASTEXITCODE -ne 0) { throw "Trusted mode configuration failed." }
}

& uv run sciops doctor
& uv run sciops codex resume
Write-Host "Codex takeover environment is ready. Open this repository in Codex and state the research direction." -ForegroundColor Green

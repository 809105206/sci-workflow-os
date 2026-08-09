$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest

$projectDir = Split-Path -Parent $PSScriptRoot
Set-Location $projectDir

function Find-Uv {
    $command = Get-Command uv -ErrorAction SilentlyContinue
    if ($null -ne $command) {
        return $command.Source
    }

    $candidates = @(
        (Join-Path $env:USERPROFILE ".local\bin\uv.exe"),
        (Join-Path $env:LOCALAPPDATA "Microsoft\WinGet\Links\uv.exe"),
        (Join-Path $env:USERPROFILE ".cargo\bin\uv.exe")
    )
    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            return $candidate
        }
    }
    return $null
}

$uv = Find-Uv
if ($null -eq $uv) {
    $winget = Get-Command winget -ErrorAction SilentlyContinue
    if ($null -ne $winget) {
        Write-Host "Installing uv through Windows Package Manager..."
        & winget install --id astral-sh.uv --exact --source winget --accept-package-agreements --accept-source-agreements
        if ($LASTEXITCODE -ne 0) {
            throw "Windows Package Manager could not install uv."
        }
    }
    else {
        Write-Host "Installing uv from the official Astral installer..."
        Invoke-RestMethod https://astral.sh/uv/install.ps1 | Invoke-Expression
    }
    $uv = Find-Uv
}

if ($null -eq $uv) {
    throw "uv was installed but could not be found. Reopen this folder and run INSTALL-PLOTTING.cmd again."
}

Write-Host "Installing managed Python 3.12..."
& $uv python install 3.12
if ($LASTEXITCODE -ne 0) { throw "Python installation failed." }

Write-Host "Installing Matplotlib and Plotly in the project environment..."
& $uv sync --extra figures
if ($LASTEXITCODE -ne 0) { throw "Plotting dependency installation failed." }

Write-Host "Checking plotting backends..."
& $uv run sciops figure doctor
if ($LASTEXITCODE -ne 0) { throw "Plotting backend check failed." }

Write-Host "Setup complete. No OriginPro or MATLAB installation is required." -ForegroundColor Green

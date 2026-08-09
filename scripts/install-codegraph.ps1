param(
    [string]$ProjectDir = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$Version = "v1.5.0"
$Architecture = if (
    [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture -eq "Arm64"
) { "arm64" } else { "x64" }
$Target = "win32-$Architecture"
$Asset = "codegraph-$Target.zip"
$Expected = if ($Architecture -eq "arm64") {
    "de125e792b5eed7dee8def2ab9bd7e762f372012f75f595e59d3b0c8714b0d55"
} else {
    "d6798622b4f44ee6757c94335f437ee27a9ff7d3537b554cb6a2b3baf11bc4a1"
}
$Destination = Join-Path $ProjectDir ".tools\codegraph-standalone\$Version"
$Executable = Join-Path $Destination "codegraph-$Target\bin\codegraph.cmd"
if (Test-Path $Executable) {
    Write-Host "CodeGraph $Version is already installed at $Executable"
    return $Executable
}

$Temporary = Join-Path ([System.IO.Path]::GetTempPath()) ("sciops-codegraph-" + [guid]::NewGuid())
New-Item -ItemType Directory -Path $Temporary | Out-Null
try {
    $Archive = Join-Path $Temporary $Asset
    $Url = "https://github.com/colbymchenry/codegraph/releases/download/$Version/$Asset"
    Invoke-WebRequest -Uri $Url -OutFile $Archive
    $Actual = (Get-FileHash -Path $Archive -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($Actual -ne $Expected) { throw "CodeGraph checksum verification failed." }
    if (Test-Path $Destination) { Remove-Item -Recurse -Force $Destination }
    New-Item -ItemType Directory -Force -Path $Destination | Out-Null
    Expand-Archive -Path $Archive -DestinationPath $Destination -Force
}
finally {
    if (Test-Path $Temporary) { Remove-Item -Recurse -Force $Temporary }
}

if (-not (Test-Path $Executable)) {
    throw "CodeGraph executable is missing after extraction."
}
Write-Host "Installed verified CodeGraph $Version at $Executable"
return $Executable

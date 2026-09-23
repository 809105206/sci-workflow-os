param(
    [string]$ProjectDir = (Split-Path -Parent $PSScriptRoot)
)

$ErrorActionPreference = "Stop"
Set-StrictMode -Version Latest
$Version = "v1.6.0"
$Architecture = if (
    [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture -eq "Arm64"
) { "arm64" } else { "x64" }
$Target = "win32-$Architecture"
$Asset = "codegraph-$Target.zip"
$Expected = if ($Architecture -eq "arm64") {
    "3ca980010bd718a6b5e75be1145806ae6491afb1a59a2cec6cee4bf5c39f1b3a"
} else {
    "cd76c3c3391f2d40abef12b142151950b6d77abc2d8429e648f89eaa90f5b68a"
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

<#
.SYNOPSIS
    Build Keylight into one file.

.DESCRIPTION
    Runs PyInstaller over keylight.spec and leaves the app in
    dist\Keylight\Keylight.exe. The folder beside it holds nothing the
    app needs: the front end is inside the file.

    The build needs a virtual environment with the app's requirements
    in it. If there is no .venv here, one is made and the requirements
    are put in it.

.PARAMETER Clean
    Throw away the work PyInstaller did last time before building.
#>
[CmdletBinding()]
param(
    [switch]$Clean
)

$ErrorActionPreference = 'Stop'
$here = Split-Path -Parent $MyInvocation.MyCommand.Path
Push-Location $here

try {
    $python = Join-Path $here '.venv\Scripts\python.exe'
    if (-not (Test-Path $python)) {
        Write-Host 'No virtual environment here; making one.'
        python -m venv .venv
        $python = Join-Path $here '.venv\Scripts\python.exe'
        & $python -m pip install --upgrade pip
        & $python -m pip install -e ".[dev]"
    }

    Write-Host 'Checking the packer is there.'
    & $python -m PyInstaller --version | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw 'PyInstaller is not installed. Run: .venv\Scripts\python.exe -m pip install pyinstaller'
    }

    $arguments = @('--noconfirm')
    if ($Clean) { $arguments += '--clean' }
    $arguments += 'keylight.spec'

    Write-Host 'Building.'
    & $python -m PyInstaller @arguments
    if ($LASTEXITCODE -ne 0) {
        throw 'The build failed.'
    }

    $exe = Join-Path $here 'dist\Keylight.exe'
    if (-not (Test-Path $exe)) {
        throw "The build finished but $exe is not there."
    }

    $size = [math]::Round((Get-Item $exe).Length / 1MB, 1)

    # A zip to hand to someone. It holds the one file and a short guide.
    $zip = Join-Path $here 'dist\Keylight.zip'
    if (Test-Path $zip) { Remove-Item -Force $zip }
    Compress-Archive -Path $exe -DestinationPath $zip
    $guide = Join-Path $here '..\docs\user-guide.md'
    if (Test-Path $guide) {
        Compress-Archive -Path $guide -DestinationPath $zip -Update
    }

    Write-Host ''
    Write-Host 'Keylight is built.'
    Write-Host "  $exe  ($size MB)"
    Write-Host "  $zip  (the exe and the guide, zipped)"
    Write-Host 'Unzip the zip on another computer and run Keylight.exe.'
}
finally {
    Pop-Location
}

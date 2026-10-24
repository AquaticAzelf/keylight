<#
.SYNOPSIS
    Build Keylight into one portable folder.

.DESCRIPTION
    Runs PyInstaller over keylight.spec and leaves the app in
    dist\Keylight\: Keylight.exe beside the _internal folder it needs.
    The folder is the app: copy it anywhere (a USB stick included) and
    run Keylight.exe. Everything the app writes - profiles, macros,
    settings, the log - lands in that same folder, so deleting it
    deletes the whole app.

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

    $app = Join-Path $here 'dist\Keylight'
    $exe = Join-Path $app 'Keylight.exe'
    if (-not (Test-Path $exe)) {
        throw "The build finished but $exe is not there."
    }

    # The guide travels inside the folder, next to the exe.
    $guide = Join-Path $here '..\docs\user-guide.md'
    if (Test-Path $guide) {
        Copy-Item $guide (Join-Path $app 'user-guide.md') -Force
    }

    # A zip to hand to someone. Unzipping it gives one Keylight folder.
    $zip = Join-Path $here 'dist\Keylight.zip'
    if (Test-Path $zip) { Remove-Item -Force $zip }
    Compress-Archive -Path $app -DestinationPath $zip

    $size = [math]::Round((Get-ChildItem $app -Recurse -File | Measure-Object Length -Sum).Sum / 1MB, 1)

    Write-Host ''
    Write-Host 'Keylight is built.'
    Write-Host "  $app  ($size MB, the portable folder)"
    Write-Host "  $zip  (the same folder, zipped)"
    Write-Host 'Copy the folder anywhere and run Keylight.exe.'
}
finally {
    Pop-Location
}

# build.ps1 — Local PyInstaller build for Windows
# Run from the repo root: .\scripts\build.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path $PSScriptRoot -Parent

# Activate venv if present
$VenvActivate = Join-Path $RepoRoot "venv\Scripts\Activate.ps1"
if (Test-Path $VenvActivate) {
    Write-Host "Activating virtual environment..."
    & $VenvActivate
}

# Generate icon assets if missing
$IconPath = Join-Path $RepoRoot "assets\icon.ico"
if (-not (Test-Path $IconPath)) {
    Write-Host "Generating icon assets..."
    python (Join-Path $RepoRoot "scripts\generate_icon.py")
}

# Check client_secrets.json exists
$SecretsPath = Join-Path $RepoRoot "client_secrets.json"
if (-not (Test-Path $SecretsPath)) {
    Write-Error "client_secrets.json not found at $SecretsPath`nSee docs/02-google-oauth-setup.md"
}

# Run PyInstaller
Write-Host "Building TextForge.exe..."
Set-Location $RepoRoot

pyinstaller `
    --onefile `
    --noconsole `
    --icon=assets\icon.ico `
    --name TextForge `
    "--add-data=client_secrets.json;." `
    --hidden-import=pystray._win32 `
    --hidden-import=keyboard._winkeyboard `
    --collect-all=customtkinter `
    --collect-all=googleapiclient `
    src\textforge\__main__.py

if ($LASTEXITCODE -ne 0) {
    Write-Error "PyInstaller build failed."
}

Write-Host ""
Write-Host "Build complete: dist\TextForge.exe" -ForegroundColor Green

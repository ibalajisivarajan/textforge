# install-startup.ps1 — Add TextForge.exe to Windows Startup folder
# Run from the repo root after building: .\scripts\install-startup.ps1

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path $PSScriptRoot -Parent
$ExePath   = Join-Path $RepoRoot "dist\TextForge.exe"
$StartupDir = [System.Environment]::GetFolderPath("Startup")
$ShortcutPath = Join-Path $StartupDir "TextForge.lnk"

if (-not (Test-Path $ExePath)) {
    Write-Error "TextForge.exe not found at $ExePath`nRun .\scripts\build.ps1 first."
}

# Create a shortcut in the Startup folder
$WshShell   = New-Object -ComObject WScript.Shell
$Shortcut   = $WshShell.CreateShortcut($ShortcutPath)
$Shortcut.TargetPath       = $ExePath
$Shortcut.WorkingDirectory = Split-Path $ExePath -Parent
$Shortcut.Description      = "TextForge — System-wide text expander"
$Shortcut.Save()

Write-Host ""
Write-Host "TextForge will now start with Windows." -ForegroundColor Green
Write-Host "Shortcut created at: $ShortcutPath"

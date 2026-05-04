# Auto-Start TextForge with Windows

TextForge needs to be running in the background (system tray) to expand snippets. Set it to start automatically with Windows so you never have to think about it.

## Option 1 — PowerShell Script (Recommended)

After building `dist\TextForge.exe`, run from the repo root:

```powershell
.\scripts\install-startup.ps1
```

This creates a shortcut to `TextForge.exe` in your Windows Startup folder. TextForge will launch automatically every time you log in.

## Option 2 — Manual (No Build Required)

1. Press `Win + R` → type `shell:startup` → press Enter
2. The Startup folder opens in File Explorer
3. Copy `TextForge.exe` into this folder (or create a shortcut to it)

TextForge will now start with Windows.

## Verify It's Working

1. Restart your PC (or log out and back in)
2. Check the system tray — the TextForge icon should appear
3. Try typing a snippet shortcut in any app

## Remove from Startup

1. Press `Win + R` → type `shell:startup` → Enter
2. Delete `TextForge.exe` or `TextForge.lnk` from the folder

TextForge will no longer start automatically (it won't affect your saved snippets).

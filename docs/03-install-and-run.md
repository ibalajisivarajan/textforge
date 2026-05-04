# Install and Run TextForge

## Download

Go to the [latest release](https://github.com/ibalajisivarajan/textforge/releases/latest) and download `TextForge.exe`.

No Python installation required — it's a single self-contained executable.

## First Run

1. Double-click `TextForge.exe`
2. Windows may show a SmartScreen warning — click **More info** → **Run anyway**
   (this happens because the app isn't code-signed yet)
3. TextForge appears in the **system tray** (bottom-right taskbar area)

## Sign In

1. Right-click (or left-click) the tray icon
2. Click **Sign In**
3. Your browser opens to a Google login page
4. Sign in with your Google account and grant the requested permissions
5. The browser shows "Authentication successful" — you can close it
6. Your snippets from Drive sync automatically

## Managing Snippets

1. Click the tray icon → **Manage Snippets**
2. The snippet manager window opens
3. Click **+ Add** to create a new shortcut → expansion pair
4. Type the shortcut in any app, followed by a space or punctuation, to expand it

## Transferring to a New Machine

1. Download `TextForge.exe` on the new machine
2. Run it and sign in with the same Google account
3. Your snippets appear immediately — they sync from Google Drive

## Uninstall

1. Click tray icon → **Quit**
2. Delete `TextForge.exe`
3. Optionally delete `%APPDATA%\TextForge\` (contains local snippet cache and token)

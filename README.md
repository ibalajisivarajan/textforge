# TextForge

A free, self-built, Google-synced system-wide text expander for Windows.

Type `bs` anywhere on Windows → it expands to `Balaji Sivarajan`. Type a shortcut, get the full expansion — synced across all your Windows machines via Google Drive.

## How it works

1. Add shortcut + expansion pairs via the native Windows UI (e.g. `bs` → `Balaji Sivarajan`)
2. A background Python agent runs in the system tray and hooks into all keyboard input globally
3. Type your shortcut followed by a word-ending character (space, period, comma, etc.) in **any** app — TextForge backspaces the trigger and types the expansion
4. Snippets sync to Google Drive (`appDataFolder` — hidden, app-scoped, only TextForge can see it)
5. On a new machine: install TextForge, sign in with Google, snippets appear

## Installation

Download `TextForge.exe` from [Releases](https://github.com/ibalajisivarajan/textforge/releases/latest) and run it. No Python installation required.

## First-time setup

1. Run `TextForge.exe` — it appears in the system tray
2. Click the tray icon → **Sign In** → complete the Google OAuth flow in your browser
3. Your snippets sync automatically

## Adding snippets

- Click the system tray icon → **Manage Snippets**
- Click **+ Add** to create a new shortcut → expansion pair
- The keyboard hook picks up changes immediately

## Building from source

See [`docs/04-build-exe.md`](docs/04-build-exe.md) for the full build process.

You will need to set up a Google Cloud project first — see [`docs/02-google-oauth-setup.md`](docs/02-google-oauth-setup.md).

## Auto-start with Windows

Run `scripts/install-startup.ps1` in PowerShell (as administrator) after building. See [`docs/05-auto-start-windows.md`](docs/05-auto-start-windows.md).

## License

MIT — see [LICENSE](LICENSE)

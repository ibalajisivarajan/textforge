# CLAUDE.md — TextForge Build Handover

This file is the single source of truth for building TextForge.
All decisions are locked. Read this fully before writing a single line of code.

-----

## Who You Are Building For

**Balaji Sivarajan** — Senior TPM, vibe coder, no formal coding background.

- Primary dev device: Microsoft Surface Pro (Windows 11)
- Primary usage device: Mobile (uses claude.ai to direct builds)
- GitHub: ibalajisivarajan
- Build philosophy: MVP first, full replacement files always, no partial diffs

-----

## What TextForge Is

A free, self-built, Google-synced system-wide text expander for Windows.

A free, self-built, Google-synced text expander for Windows. Type `omw` and it expands to `On my way!`
anywhere on Windows. TextForge does this system-wide, with Google Drive as the sync backend.

**Core loop:**

1. User adds a shortcut + expansion pair via a native Windows UI (e.g. `bs` → `Balaji Sivarajan`)
1. A background Python agent runs in the system tray and hooks into all keyboard input globally
1. Whenever the user types `bs` (or `BS` or `Bs`) followed by a word-ending character
   (space, tab, period, comma, semicolon, colon, exclamation, question mark, enter)
   in **any** Windows app — the agent backspaces the trigger and types the expansion
1. Snippets are saved locally and synced to Google Drive (`appDataFolder` — hidden, app-scoped)
1. On a new machine: install TextForge, sign in with Google, snippets appear

-----

## Architecture — All Decisions Locked

### Stack

- **Language:** Python 3.11+
- **Keyboard hook:** `keyboard` library (global, low-level Windows hook)
- **System tray:** `pystray`
- **Management UI:** `customtkinter` (modern-looking Tkinter; native Windows window)
- **Google Auth:** `google-auth-oauthlib` (OAuth 2.0 desktop flow, loopback redirect)
- **Google Drive API:** `google-api-python-client`
- **Distribution:** PyInstaller `--onefile --noconsole` → `TextForge.exe`
- **Build pipeline:** GitHub Actions (Windows runner) → GitHub Releases
- **No web backend. No database. No server. Google Drive is the backend.**

### Data Storage

Two locations, always in sync:

**Local mirror (hot path):**

```
%APPDATA%\TextForge\snippets.json
```

The keyboard hook reads only from here. Zero network calls in the expansion hot path.

**Source of truth (cloud):**

```
Google Drive → appDataFolder → snippets.json
```

Hidden from Drive UI. App-scoped. Only TextForge can read/write it.

**snippets.json schema:**

```json
{
  "version": 1,
  "user_email": "user@gmail.com",
  "updated_at": "2026-05-04T10:30:00Z",
  "snippets": [
    {
      "id": "uuid4-string",
      "shortcut": "bs",
      "expansion": "Balaji Sivarajan",
      "created_at": "2026-05-04T10:00:00Z",
      "updated_at": "2026-05-04T10:00:00Z"
    }
  ]
}
```

### Auth Model

- OAuth 2.0 desktop app flow with loopback redirect (`http://127.0.0.1:PORT/callback`)
- Scopes: `drive.appdata` + `userinfo.email` ONLY
- Tokens stored at: `%APPDATA%\TextForge\token.json`
- `client_secrets.json` must be bundled into the PyInstaller binary (never committed to git)

### Trigger Matching Rules

- **No prefix character** — type the shortcut directly, like any standard text expander
- **Word-boundary fire:** expansion triggers when a word-ending character follows the shortcut
  - Word-ending chars: `space tab . , ; : ! ? \n \r`
- **Case-insensitive, same-order:** `bs` / `BS` / `Bs` / `bS` all match `bs`. `sb` does NOT match.
- **Backspace count:** erase (len(shortcut) + 1) characters — the shortcut plus the word-ending char,
  then retype the expansion followed by the word-ending char

### MVP Scope (v1.0) — DO NOT EXCEED

- Static shortcut → static text expansion only
- Add / Edit / Delete snippets via native UI
- Google Sign-In (one-time browser flow)
- Auto-start with Windows
- Cross-device sync via Drive

**Explicitly NOT in v1.0:**

- Variables (`{date}`, `{clipboard}`, `{cursor}`)
- Fill-in forms
- Picker UI (Ctrl+Space search)
- Folders / tags
- Import / export
- Per-app rules
- Token encryption at rest (plaintext token.json is acceptable for personal use v1)

-----

## ADR Summary — All Locked

|#  |Decision                                    |Rationale                                                  |
|---|--------------------------------------------|-----------------------------------------------------------|
|001|Native Windows window (customtkinter) for UI|Single codebase, no web hosting complexity                 |
|002|Google Drive appDataFolder as only backend  |100% free, no deployment, data in user’s own Drive         |
|003|Python + PyInstaller .exe                   |Clean OAuth libs, single binary, no Python needed on target|
|004|drive.appdata scope only                    |Minimal privacy surface; app cannot see other Drive files  |
|005|L1 static expansion only for MVP            |Validate daily use before layering complexity              |
|006|No-prefix trigger + word-boundary detection |Low friction; type shortcut directly like any standard text expander|
|007|Case-insensitive, same-order matching       |User preference; bs/BS/Bs/bS all match                     |
|008|Local cache for expansion hot path          |Zero network latency; offline support                      |
|009|PyInstaller –onefile distribution           |Single .exe, no Python required on target machine          |

-----

## Repo Structure — Build to This Exactly

```
textforge/
├── CLAUDE.md                          ← this file
├── README.md
├── LICENSE                            ← MIT
├── .gitignore
├── requirements.txt
├── pyproject.toml
├── .github/
│   └── workflows/
│       └── build.yml                  ← GitHub Actions: build .exe on push to main
├── docs/
│   ├── 00-charter.md
│   ├── 01-architecture.md
│   ├── 02-google-oauth-setup.md
│   ├── 03-install-and-run.md
│   ├── 04-build-exe.md
│   ├── 05-auto-start-windows.md
│   └── adr/
│       ├── 001-native-windows-ui.md
│       ├── 002-drive-as-backend.md
│       ├── 003-python-agent.md
│       ├── 004-drive-appdata-scope.md
│       ├── 005-mvp-l1-scope.md
│       ├── 006-no-prefix-triggers.md
│       ├── 007-case-insensitive.md
│       ├── 008-local-cache.md
│       └── 009-pyinstaller-distribution.md
├── src/
│   └── textforge/
│       ├── __init__.py
│       ├── __main__.py                ← entry: python -m textforge
│       ├── app.py                     ← main loop, wires all components
│       ├── config.py                  ← paths, constants, version
│       ├── auth.py                    ← Google OAuth desktop flow
│       ├── drive_sync.py              ← Drive API: push/pull snippets.json
│       ├── storage.py                 ← local JSON read/write
│       ├── keyboard_hook.py           ← global hook, rolling buffer, word-end detection
│       ├── expander.py                ← match + backspace + type logic
│       ├── tray.py                    ← pystray icon and menu
│       └── ui/
│           ├── __init__.py
│           ├── main_window.py         ← snippet list, Add/Edit/Delete buttons
│           └── snippet_dialog.py      ← modal dialog for add/edit
├── assets/
│   ├── icon.ico                       ← generate a simple 'TF' icon, 256x256
│   └── icon.png
├── scripts/
│   ├── build.ps1                      ← local PyInstaller build (Windows PowerShell)
│   └── install-startup.ps1            ← add TextForge.exe to Windows Startup folder
└── tests/
    ├── __init__.py
    ├── test_expander.py
    └── test_storage.py
```

**Note:** `client_secrets.json` is in `.gitignore`. It must be obtained separately from
Google Cloud Console and placed in the repo root before building (locally or in Actions secrets).

-----

## Build Plan — File by File, In Order

Build strictly in this sequence. Each file must be complete and functional before moving to the next.
Never deliver partial files. Always deliver the complete file ready to write.

### Step 1 — Project scaffolding

**Files to create:**

- `.gitignore`
- `LICENSE` (MIT, owner: Balaji Sivarajan)
- `requirements.txt`
- `pyproject.toml`
- `README.md`
- `src/textforge/__init__.py` (empty, just version string)

**requirements.txt must pin these:**

```
keyboard==0.13.5
pystray==0.19.5
customtkinter==5.2.2
google-auth==2.29.0
google-auth-oauthlib==1.2.0
google-api-python-client==2.127.0
Pillow==10.3.0
pyperclip==1.8.2
```

### Step 2 — config.py

Constants and paths only. No logic.

```python
# Key constants to define:
APP_NAME = "TextForge"
VERSION = "1.0.0"
APPDATA_DIR = Path(os.environ["APPDATA"]) / "TextForge"
SNIPPETS_FILE = APPDATA_DIR / "snippets.json"
TOKEN_FILE = APPDATA_DIR / "token.json"
CLIENT_SECRETS_FILE = Path(__file__).parent.parent.parent / "client_secrets.json"
# For PyInstaller bundled builds:
# CLIENT_SECRETS_FILE = Path(sys._MEIPASS) / "client_secrets.json"  (handle both)
DRIVE_FILE_NAME = "snippets.json"
DRIVE_FOLDER = "appDataFolder"
SCOPES = [
    "https://www.googleapis.com/auth/drive.appdata",
    "https://www.googleapis.com/auth/userinfo.email",
]
WORD_END_CHARS = set(" \t.,;:!?\n\r")
SYNC_INTERVAL_SECONDS = 300  # sync every 5 minutes
```

### Step 3 — storage.py

Local JSON read/write. No network. No auth. Standalone testable.

```python
# Functions to implement:
def load_snippets() -> list[dict]:
    """Load snippets from local cache. Returns [] if file missing or corrupt."""

def save_snippets(snippets: list[dict]) -> None:
    """Atomically write snippets to local cache. Create APPDATA_DIR if needed."""

def add_snippet(shortcut: str, expansion: str) -> dict:
    """Create snippet dict with uuid4 id and timestamps. Save. Return snippet."""

def update_snippet(id: str, shortcut: str, expansion: str) -> bool:
    """Update existing snippet by id. Return True if found and updated."""

def delete_snippet(id: str) -> bool:
    """Delete snippet by id. Return True if found and deleted."""

def get_all_shortcuts() -> dict[str, str]:
    """Return {lowercase_shortcut: expansion} for fast O(1) lookup in expander."""
```

### Step 4 — expander.py

Core matching and expansion logic. No keyboard library here — pure logic, fully testable.

```python
# Functions to implement:
def match_shortcut(buffer: str, shortcuts: dict[str, str]) -> tuple[str, str] | None:
    """
    Given the rolling character buffer and the shortcuts lookup dict,
    return (shortcut, expansion) if the buffer ends with a known shortcut
    followed by a word-ending character. Return None if no match.

    Rules:
    - Compare buffer suffix case-insensitively
    - Word-ending character is the LAST character in buffer
    - The shortcut must be immediately before the word-ending char
    - If buffer ends with space+shortcut+space, only fire on the LAST occurrence
    """

def build_replacement_keystrokes(shortcut: str, expansion: str, word_end_char: str) -> list:
    """
    Return list of keyboard actions:
    1. (len(shortcut) + 1) backspaces to erase shortcut + word-end char
    2. Type expansion
    3. Type word_end_char
    """
```

**Tests to write in tests/test_expander.py:**

```python
# test cases must cover:
# "bs " → matches shortcut "bs"
# "BS " → matches shortcut "bs" (case insensitive)
# "xbs " → does NOT match (not at word boundary start)
# "sb " → does NOT match (different order)
# "bs" (no word-end char) → does NOT match
# "bs." → matches (period is word-end char)
# empty buffer → does NOT match
```

### Step 5 — auth.py

Google OAuth 2.0 desktop flow. Stores and refreshes tokens.

```python
# Functions to implement:
def get_credentials() -> google.oauth2.credentials.Credentials | None:
    """
    Load credentials from TOKEN_FILE if they exist.
    Refresh if expired. Return None if no token file exists.
    """

def run_oauth_flow() -> google.oauth2.credentials.Credentials:
    """
    Start local HTTP server on random port.
    Open browser to OAuth consent URL.
    Wait for redirect callback with code.
    Exchange code for tokens.
    Save to TOKEN_FILE.
    Return credentials.
    """

def get_user_email(credentials) -> str:
    """Call userinfo API. Return email string."""

def sign_out() -> None:
    """Delete TOKEN_FILE. Revoke token from Google if possible."""

def is_signed_in() -> bool:
    """Return True if TOKEN_FILE exists and has a refresh token."""
```

**Important implementation notes:**

- Use `google_auth_oauthlib.flow.InstalledAppFlow` — it handles the loopback redirect natively
- Call `flow.run_local_server(port=0)` — port=0 picks a random available port
- Handle `FileNotFoundError` if `client_secrets.json` is missing with a clear error message
- Handle expired tokens by calling `credentials.refresh(Request())`

### Step 6 — drive_sync.py

Google Drive API wrapper. Push/pull snippets.json.

```python
# Functions to implement:
def get_drive_service(credentials):
    """Return authenticated Drive API service object."""

def find_snippets_file(service) -> str | None:
    """
    List files in appDataFolder with name == DRIVE_FILE_NAME.
    Return file ID if found, None otherwise.
    """

def download_snippets(service, file_id: str) -> dict:
    """Download and parse snippets.json from Drive. Return parsed dict."""

def upload_snippets(service, file_id: str | None, data: dict) -> str:
    """
    If file_id is None: create new file in appDataFolder.
    If file_id exists: update file content.
    Return file_id.
    """

def sync_from_drive(credentials) -> bool:
    """
    Pull snippets from Drive → overwrite local cache.
    Return True on success, False on error.
    """

def sync_to_drive(credentials) -> bool:
    """
    Push local cache → Drive.
    Return True on success, False on error.
    """
```

**Important:** All Drive operations must be wrapped in try/except. Network failures must
be logged silently — never crash the agent because Drive is unreachable.

### Step 7 — keyboard_hook.py

Global keyboard hook. Maintains rolling buffer. Fires expander on word-end chars.

```python
class KeyboardHook:
    """
    Lifecycle:
    - __init__: set up buffer, load shortcuts from storage
    - start(): register keyboard.on_press callback, start listening
    - stop(): unhook all
    - reload_shortcuts(): re-read from storage (called after snippet add/edit/delete)

    Buffer management:
    - Keep last 50 characters (enough for any reasonable shortcut)
    - On word-end char: call expander.match_shortcut(buffer, shortcuts)
    - If match: call expander.build_replacement_keystrokes and fire them
    - On any other printable char: append to buffer
    - On backspace: remove last char from buffer
    - On escape: clear buffer

    Threading:
    - keyboard.on_press fires on a background thread
    - Expansion (keyboard.send) must NOT be called from within the on_press callback
      (causes deadlock on some systems)
    - Use threading.Timer(0, ...) or queue to fire expansions asynchronously
    """
```

**Critical implementation detail on expansion:**

```python
# WRONG — deadlocks:
def on_key(event):
    if match:
        keyboard.send(...)  # called from hook thread

# CORRECT — defer to next tick:
def on_key(event):
    if match:
        threading.Timer(0, lambda: keyboard.send(...)).start()
```

### Step 8 — tray.py

System tray icon and menu using pystray.

```python
# Menu items:
# ✓ TextForge v1.0.0            (title, disabled)
# ─────────────────────
# Signed in as: user@gmail.com  (or "Not signed in")
# ─────────────────────
# Manage Snippets               → open main_window
# Sign In                       → run_oauth_flow (shown when signed out)
# Sign Out                      → sign_out (shown when signed in)
# Sync Now                      → sync_to_drive + sync_from_drive
# ─────────────────────
# Pause Expansion               → toggle hook on/off (checkable)
# ─────────────────────
# Quit                          → stop everything, exit

# Icon:
# Load from assets/icon.ico
# Fall back to a programmatically generated PIL image if icon file not found
# (draw "TF" text on a dark background — ensures tray always has an icon)
```

### Step 9 — ui/main_window.py and ui/snippet_dialog.py

Native Windows management UI using customtkinter.

**main_window.py — the snippet manager:**

```
Layout:
┌─────────────────────────────────────────┐
│  TextForge                    [x]        │
├─────────────────────────────────────────┤
│  🔍 [Search snippets...              ]   │
├───────────────┬─────────────────────────┤
│  SHORTCUT     │  EXPANSION              │
├───────────────┼─────────────────────────┤
│  bs           │  Balaji Sivarajan       │
│  addr         │  123 Main St Surrey BC  │
│  ...          │  ...                    │
├───────────────┴─────────────────────────┤
│  [+ Add]          [✏ Edit]  [🗑 Delete] │
│                        Synced ✓ 10:30am │
└─────────────────────────────────────────┘

Behaviour:
- Window size: 600x450, resizable
- Snippet list: CTkScrollableFrame with rows
- Clicking a row selects it (highlights it)
- Double-click a row → opens edit dialog
- Add button → opens add dialog
- Edit button → opens edit dialog for selected row (disabled if nothing selected)
- Delete button → confirm dialog, then delete (disabled if nothing selected)
- Search bar filters list in real-time (client-side, no re-query)
- Sync status shown bottom right: "Synced ✓ HH:MM" or "Syncing..." or "Offline"
- On close: hide window (do not quit agent), agent stays in tray
```

**snippet_dialog.py — add/edit modal:**

```
Layout:
┌──────────────────────────────┐
│  Add Snippet          [x]    │
├──────────────────────────────┤
│  Shortcut                    │
│  [bs                      ]  │
│                              │
│  Expansion                   │
│  [Balaji Sivarajan        ]  │
│  (multiline text box)        │
│                              │
│  [Cancel]          [Save]    │
└──────────────────────────────┘

Validation:
- Shortcut: required, no spaces, lowercase enforced on save, max 20 chars
- Expansion: required, max 500 chars
- Duplicate shortcut check: warn but allow (user may be editing)
- Save calls storage.add_snippet or storage.update_snippet
- Then calls keyboard_hook.reload_shortcuts()
- Then triggers drive_sync.sync_to_drive() in background thread
```

### Step 10 — app.py and **main**.py

The main entry point that wires everything together.

**app.py:**

```python
class TextForgeApp:
    def __init__(self):
        # 1. Ensure APPDATA_DIR exists
        # 2. Load local snippets
        # 3. Try to restore credentials from token.json
        # 4. If credentials exist: sync from Drive on startup (background thread)
        # 5. Start keyboard hook
        # 6. Start background sync timer (every SYNC_INTERVAL_SECONDS)
        # 7. Start tray (blocking call — runs until Quit)

    def start(self):
        """Full startup sequence."""

    def quit(self):
        """Clean shutdown: stop hook, cancel timers, remove tray icon, sys.exit(0)"""
```

****main**.py:**

```python
# Single-instance guard: check for a lockfile in APPDATA_DIR
# If already running: show a message and exit
# Else: write lockfile, run TextForgeApp().start(), delete lockfile on exit
```

### Step 11 — GitHub Actions build.yml

**File path:** `.github/workflows/build.yml`

```yaml
# Trigger: push to main branch
# Runner: windows-latest
# Steps:
# 1. Checkout repo
# 2. Set up Python 3.11
# 3. pip install -r requirements.txt
# 4. pip install pyinstaller
# 5. Write client_secrets.json from GitHub Secret CLIENT_SECRETS_JSON
#    (echo $env:CLIENT_SECRETS_JSON > client_secrets.json)
# 6. Run PyInstaller:
#    pyinstaller --onefile --noconsole --icon=assets/icon.ico
#                --name TextForge
#                --add-data "client_secrets.json;."
#                src/textforge/__main__.py
# 7. Upload dist/TextForge.exe as artifact
# 8. Create GitHub Release with tag v{VERSION} and attach TextForge.exe
#    (use softprops/action-gh-release)
#
# GitHub Secret required:
# CLIENT_SECRETS_JSON — paste the full content of client_secrets.json from Google Cloud Console
```

### Step 12 — scripts/

**build.ps1** — for local builds on Surface Pro (optional, fallback):

```powershell
# Activate venv
# Run same PyInstaller command as Actions workflow
# Echo: "Build complete: dist\TextForge.exe"
```

**install-startup.ps1** — add to Windows Startup:

```powershell
# Copy dist\TextForge.exe to %APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\
# Or create a shortcut there pointing to the .exe
# Echo: "TextForge will now start with Windows"
```

### Step 13 — docs/

Write these markdown docs. Keep each one short and practical:

- `docs/02-google-oauth-setup.md` — step by step Google Cloud Console setup
  (this is the one manual step Bala must do before the first build works)
- `docs/03-install-and-run.md` — how to install TextForge.exe on a new machine
- `docs/04-build-exe.md` — how GitHub Actions builds the .exe, how to trigger a new build
- `docs/05-auto-start-windows.md` — running install-startup.ps1 or manual Startup folder method

-----

## What Bala Must Do Manually (Before First Build)

Claude Code cannot do these — they require a browser:

### 1. Google Cloud Console (~10 minutes)

1. Go to `console.cloud.google.com`
1. New Project → name: “TextForge”
1. APIs & Services → Library → search “Google Drive API” → **Enable**
1. APIs & Services → OAuth consent screen
- User Type: **External**
- App name: `TextForge`
- Support email: your Gmail
- Developer contact: your Gmail
- Save and Continue
1. Scopes → Add scopes:
- `https://www.googleapis.com/auth/drive.appdata`
- `https://www.googleapis.com/auth/userinfo.email`
- Update → Save and Continue
1. Test users → Add your Gmail address → Save and Continue
1. Credentials → **Create Credentials** → OAuth client ID
- Application type: **Desktop app**
- Name: `TextForge Desktop`
- Create
1. Download JSON → rename to `client_secrets.json`

### 2. GitHub Secret

1. Go to `github.com/ibalajisivarajan/textforge` → Settings → Secrets and variables → Actions
1. New repository secret
1. Name: `CLIENT_SECRETS_JSON`
1. Value: paste the **entire contents** of `client_secrets.json`
1. Save

Once these two steps are done, every push to `main` will automatically build `TextForge.exe`
and publish it to GitHub Releases. Bala downloads from:
`https://github.com/ibalajisivarajan/textforge/releases/latest`

-----

## Icon

Generate a simple `icon.ico` and `icon.png` programmatically using Pillow.
Do not depend on an external asset. Write a `scripts/generate_icon.py` that:

- Creates a 256x256 dark background (color: `#1a1a2e`)
- Draws “TF” in white with a clean sans-serif font
- Saves as both `assets/icon.ico` (multi-size: 16, 32, 48, 64, 128, 256) and `assets/icon.png`

Run this script as part of the build if `assets/icon.ico` doesn’t exist.

-----

## Testing

Write tests for the two pure-logic modules:

**tests/test_expander.py** — cover all matching rules:

- Exact match (bs + space)
- Case variants (BS, Bs, bS)
- Non-match: wrong order (sb)
- Non-match: embedded (xbs — not at start of word)
- Non-match: no word-end char
- All word-end chars trigger
- Empty buffer
- Shortcut longer than buffer

**tests/test_storage.py** — cover CRUD:

- Load from missing file returns []
- Add snippet creates file with correct schema
- Update snippet changes fields
- Delete snippet removes correctly
- get_all_shortcuts returns lowercase keys

Run with: `python -m pytest tests/ -v`

-----

## Build Sequence Summary

```
Step 1  → scaffolding (gitignore, requirements, pyproject, README)
Step 2  → config.py
Step 3  → storage.py + tests/test_storage.py
Step 4  → expander.py + tests/test_expander.py
Step 5  → auth.py
Step 6  → drive_sync.py
Step 7  → keyboard_hook.py
Step 8  → tray.py
Step 9  → ui/main_window.py + ui/snippet_dialog.py
Step 10 → app.py + __main__.py
Step 11 → .github/workflows/build.yml
Step 12 → scripts/build.ps1 + install-startup.ps1 + generate_icon.py
Step 13 → docs/
```

After Step 10: run `python -m textforge` locally to verify the full app works.
After Step 11: push to main, verify GitHub Actions builds successfully, download .exe from Releases.

-----

## Phase 2 Backlog (DO NOT BUILD IN v1.0)

1. Variables — `{date}`, `{time}`, `{clipboard}`, `{cursor}`
1. Export / Import JSON
1. Picker UI — Ctrl+Shift+Space fuzzy search
1. Usage statistics
1. Fill-in forms
1. Folders / tags
1. Web management UI (Cloudflare Pages reading same Drive file)
1. Token encryption (Windows DPAPI)
1. Per-app disable rules

-----

## Constraints — Never Violate These

- **Full files always.** Never deliver partial diffs or code snippets. Every file is complete and ready to write.
- **No backend.** No server, no database, no Cloudflare, no Firebase. Google Drive only.
- **No scope creep.** L1 static expansion only. Do not add Phase 2 features.
- **Windows only.** All paths use `%APPDATA%`, PowerShell scripts, Windows startup folder. No cross-platform abstractions.
- **Single process.** Everything runs in one Python process. No subprocesses except PyInstaller build.
- **Graceful degradation.** Drive sync failures must never crash the agent. Log and continue.
- **client_secrets.json is never committed to git.** It is in .gitignore. It enters the build only via GitHub Secret.

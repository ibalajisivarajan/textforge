import os
import sys
from pathlib import Path

APP_NAME = "TextForge"
VERSION = "1.0.6"

APPDATA_DIR = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming")) / "TextForge"
SNIPPETS_FILE = APPDATA_DIR / "snippets.json"
TOKEN_FILE = APPDATA_DIR / "token.json"
LOCK_FILE = APPDATA_DIR / "textforge.lock"

# Support both dev (repo root) and PyInstaller bundled builds
if getattr(sys, "frozen", False):
    CLIENT_SECRETS_FILE = Path(sys._MEIPASS) / "client_secrets.json"
else:
    CLIENT_SECRETS_FILE = Path(__file__).parent.parent.parent / "client_secrets.json"

DRIVE_FILE_NAME = "snippets.json"
DRIVE_FOLDER = "appDataFolder"

SCOPES = [
    "https://www.googleapis.com/auth/drive.appdata",
    "https://www.googleapis.com/auth/userinfo.email",
]

WORD_END_CHARS = set(" \t.,;:!?\n\r")

SYNC_INTERVAL_SECONDS = 300

BUFFER_MAX_LEN = 50
SHORTCUT_MAX_LEN = 20
EXPANSION_MAX_LEN = 500

import json
import uuid
import logging
import tempfile
import os
from datetime import datetime, timezone
from pathlib import Path

from .config import APPDATA_DIR, SNIPPETS_FILE

log = logging.getLogger(__name__)

SCHEMA_VERSION = 1


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _load_raw() -> dict:
    try:
        with open(SNIPPETS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, OSError) as e:
        log.warning("Failed to load snippets file: %s", e)
        return {}


def _save_raw(data: dict) -> None:
    APPDATA_DIR.mkdir(parents=True, exist_ok=True)
    # Atomic write via temp file in same directory
    fd, tmp_path = tempfile.mkstemp(dir=APPDATA_DIR, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        os.replace(tmp_path, SNIPPETS_FILE)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def load_snippets() -> list[dict]:
    """Load snippets from local cache. Returns [] if file missing or corrupt."""
    data = _load_raw()
    return data.get("snippets", [])


def save_snippets(snippets: list[dict]) -> None:
    """Atomically write snippets to local cache. Creates APPDATA_DIR if needed."""
    existing = _load_raw()
    data = {
        "version": SCHEMA_VERSION,
        "user_email": existing.get("user_email", ""),
        "updated_at": _now_iso(),
        "snippets": snippets,
    }
    _save_raw(data)


def add_snippet(shortcut: str, expansion: str) -> dict:
    """Create snippet dict with uuid4 id and timestamps. Save. Return snippet."""
    snippets = load_snippets()
    now = _now_iso()
    snippet = {
        "id": str(uuid.uuid4()),
        "shortcut": shortcut.lower().strip(),
        "expansion": expansion,
        "created_at": now,
        "updated_at": now,
    }
    snippets.append(snippet)
    save_snippets(snippets)
    return snippet


def update_snippet(id: str, shortcut: str, expansion: str) -> bool:
    """Update existing snippet by id. Return True if found and updated."""
    snippets = load_snippets()
    for s in snippets:
        if s["id"] == id:
            s["shortcut"] = shortcut.lower().strip()
            s["expansion"] = expansion
            s["updated_at"] = _now_iso()
            save_snippets(snippets)
            return True
    return False


def delete_snippet(id: str) -> bool:
    """Delete snippet by id. Return True if found and deleted."""
    snippets = load_snippets()
    new_snippets = [s for s in snippets if s["id"] != id]
    if len(new_snippets) == len(snippets):
        return False
    save_snippets(new_snippets)
    return True


def get_all_shortcuts() -> dict[str, str]:
    """Return {lowercase_shortcut: expansion} for fast O(1) lookup in expander."""
    snippets = load_snippets()
    return {s["shortcut"].lower(): s["expansion"] for s in snippets}


def set_user_email(email: str) -> None:
    """Persist the signed-in user's email in snippets.json."""
    data = _load_raw()
    data["user_email"] = email
    if "version" not in data:
        data["version"] = SCHEMA_VERSION
    if "snippets" not in data:
        data["snippets"] = []
    data["updated_at"] = _now_iso()
    _save_raw(data)

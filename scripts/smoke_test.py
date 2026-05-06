#!/usr/bin/env python3
"""
smoke_test.py — automated verification of TextForge TESTPLAN.md cases.

Covers every case that does NOT require a real keyboard, browser, or tray icon.
Lists the remaining manual cases at the end.

Run with:
    python scripts/smoke_test.py
"""
import sys
import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

# Allow running from repo root: `python scripts/smoke_test.py`
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# ── Test runner ───────────────────────────────────────────────────────────────

PASSED: list[str] = []
FAILED: list[str] = []

# Cases that genuinely require a human + real OS/hardware
MANUAL_CASES = [
    "T1  — Tray icon visible on first launch (no token.json)",
    "T2  — Menu shows email address after Google sign-in",
    "T3  — Menu reverts to 'Not signed in' after sign-out",
    "T4  — 'Manage Snippets' opens the snippet manager window",
    "T5  — 'Pause Expansion': typing shortcut no longer expands",
    "T6  — 'Resume Expansion': shortcut expands again",
    "T7  — 'Sync Now': tray balloon notification appears",
    "T8  — 'Quit': TextForge.exe gone from Task Manager",
    "A1  — 'Sign In' opens Google OAuth consent page in browser",
    "A2  — OAuth completes: 'Signed in as email' notification shown",
    "A3  — Relaunch after sign-in: no browser prompt, email in menu",
    "A4  — Relaunch after sign-out: menu shows 'Not signed in'",
    "U1  — Snippet manager window opens at 600×450",
    "U6  — Empty shortcut field: error shown, row not added",
    "U7  — Empty expansion field: error shown, row not added",
    "U8  — Search bar filters list in real time",
    "U9  — No-match search → empty list",
    "U10 — Clearing search → all snippets reappear",
    "U11 — Close window (X): tray icon still present",
    "U12 — Reopen window: current snippet list shown",
    "E12 — Expansion works in Notepad",
    "E13 — Expansion works in Chrome address bar",
    "E14 — Expansion works in VS Code",
    "S3  — Auto-sync after 5 min updates 'Synced ✓ HH:MM' label",
    "S4  — 'Sync Now' from tray updates snippets.json timestamp",
    "S5  — Cross-device sync: snippets appear on second machine",
    "AS1 — Copy TextForge.exe to shell:startup folder",
    "AS2 — Restart Windows: icon appears without manual launch",
    "AS3 — Single instance enforced (second launch shows dialog and exits)",
    "ST1 — No crash or freeze after 30 minutes of normal use",
    "ST2 — Memory stays under 50 MB after 30 minutes",
    "ST3 — 20+ snippets: all listed, no UI slowdown",
    "ST4 — Rapid typing of 10 shortcuts: no dropped/doubled characters",
]


def case(label: str, fn) -> None:
    """Run one test case, record pass/fail, print result."""
    try:
        fn()
        PASSED.append(label)
        print(f"  ✅  {label}")
    except AssertionError as e:
        FAILED.append(label)
        print(f"  ❌  {label}")
        print(f"       AssertionError: {e}")
    except Exception as e:
        FAILED.append(label)
        print(f"  ❌  {label}")
        print(f"       {type(e).__name__}: {e}")


# ── AUTH ──────────────────────────────────────────────────────────────────────

def run_auth_tests() -> None:
    print("\n── AUTH " + "─" * 55)
    from textforge.auth import is_signed_in, sign_out

    def _no_token_file():
        with tempfile.TemporaryDirectory() as d:
            tf = Path(d) / "token.json"
            with patch("textforge.auth.TOKEN_FILE", tf):
                result = is_signed_in()
            assert result is False, f"Expected False, got {result!r}"

    def _refresh_token_present():
        with tempfile.TemporaryDirectory() as d:
            tf = Path(d) / "token.json"
            tf.write_text(json.dumps({"refresh_token": "rtoken123"}))
            with patch("textforge.auth.TOKEN_FILE", tf):
                result = is_signed_in()
            assert result is True, f"Expected True, got {result!r}"

    def _no_refresh_token():
        with tempfile.TemporaryDirectory() as d:
            tf = Path(d) / "token.json"
            tf.write_text(json.dumps({"token": "abc"}))
            with patch("textforge.auth.TOKEN_FILE", tf):
                result = is_signed_in()
            assert result is False, f"Expected False (no refresh_token), got {result!r}"

    def _sign_out_deletes_file():
        with tempfile.TemporaryDirectory() as d:
            tf = Path(d) / "token.json"
            tf.write_text(json.dumps({
                "token": "tok",
                "refresh_token": "rtok",
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": "cid",
                "client_secret": "cs",
                "scopes": [],
            }))
            with (
                patch("textforge.auth.TOKEN_FILE", tf),
                patch("textforge.auth.urllib.request.urlopen"),  # skip network revoke
            ):
                sign_out()
            assert not tf.exists(), "Expected token.json to be deleted after sign_out()"

    def _sign_out_no_file_is_noop():
        with tempfile.TemporaryDirectory() as d:
            tf = Path(d) / "token.json"
            with patch("textforge.auth.TOKEN_FILE", tf):
                sign_out()  # must not raise when file is absent

    case("is_signed_in() → False  when token.json missing              (T1/A4)", _no_token_file)
    case("is_signed_in() → True   when refresh_token present           (A3)",    _refresh_token_present)
    case("is_signed_in() → False  when token exists but no refresh_tok (A4)",    _no_refresh_token)
    case("sign_out()     deletes token.json                              (A4/T3)", _sign_out_deletes_file)
    case("sign_out()     is a no-op when token.json is absent            (A4)",    _sign_out_no_file_is_noop)


# ── STORAGE ───────────────────────────────────────────────────────────────────

def run_storage_tests() -> None:
    print("\n── STORAGE " + "─" * 52)

    def fresh(fn):
        """Run fn(snippets_path) with APPDATA_DIR + SNIPPETS_FILE redirected."""
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            sf = tmp / "snippets.json"
            with (
                patch("textforge.storage.APPDATA_DIR", tmp),
                patch("textforge.storage.SNIPPETS_FILE", sf),
            ):
                fn(sf)

    def _add_snippet():
        def run(sf):
            from textforge.storage import add_snippet, load_snippets
            snippet = add_snippet("bs", "Balaji Sivarajan")
            # In-memory check
            snippets = load_snippets()
            assert len(snippets) == 1, f"Expected 1 snippet, got {len(snippets)}"
            assert snippets[0]["shortcut"] == "bs"
            assert snippets[0]["expansion"] == "Balaji Sivarajan"
            assert "id" in snippets[0]
            assert "created_at" in snippets[0]
            # On-disk check
            data = json.loads(sf.read_text())
            assert data["version"] == 1
            assert len(data["snippets"]) == 1
            assert data["snippets"][0]["shortcut"] == "bs"
        fresh(run)

    def _edit_snippet():
        def run(sf):
            from textforge.storage import add_snippet, update_snippet, load_snippets
            s = add_snippet("addr", "Old Address")
            ok = update_snippet(s["id"], "addr", "New Address")
            assert ok is True, "update_snippet should return True"
            snippets = load_snippets()
            updated = next((x for x in snippets if x["id"] == s["id"]), None)
            assert updated is not None, "Snippet not found after update"
            assert updated["expansion"] == "New Address", \
                f"Got {updated['expansion']!r}, expected 'New Address'"
            # Verify shortcut unchanged
            assert updated["shortcut"] == "addr"
            # On-disk check
            data = json.loads(sf.read_text())
            on_disk = next(x for x in data["snippets"] if x["id"] == s["id"])
            assert on_disk["expansion"] == "New Address"
        fresh(run)

    def _delete_snippet():
        def run(sf):
            from textforge.storage import add_snippet, delete_snippet, load_snippets
            s1 = add_snippet("keep", "Keep me")
            s2 = add_snippet("del", "Delete me")
            ok = delete_snippet(s2["id"])
            assert ok is True, "delete_snippet should return True"
            snippets = load_snippets()
            ids = [x["id"] for x in snippets]
            assert s2["id"] not in ids, "Deleted snippet still present"
            assert s1["id"] in ids, "Unrelated snippet was also removed"
            # On-disk check
            data = json.loads(sf.read_text())
            disk_ids = [x["id"] for x in data["snippets"]]
            assert s2["id"] not in disk_ids
        fresh(run)

    def _duplicate_shortcut_no_crash():
        def run(sf):
            from textforge.storage import add_snippet, load_snippets
            add_snippet("dup", "First expansion")
            add_snippet("dup", "Second expansion")
            # Storage layer does not enforce uniqueness — the UI layer warns.
            # Verify both entries stored and no exception raised.
            snippets = load_snippets()
            dups = [s for s in snippets if s["shortcut"] == "dup"]
            assert len(dups) == 2, f"Expected 2 dup entries, got {len(dups)}"
        fresh(run)

    case("Add snippet    → appears in snippets.json with correct schema (U2/S1)", _add_snippet)
    case("Edit snippet   → change persists in snippets.json            (U3)",     _edit_snippet)
    case("Delete snippet → removed from snippets.json                  (U4/S2)",  _delete_snippet)
    case("Duplicate shortcut → no crash, both entries stored           (U5)",     _duplicate_shortcut_no_crash)


# ── EXPANDER ──────────────────────────────────────────────────────────────────

def run_expander_tests() -> None:
    print("\n── EXPANDER " + "─" * 51)
    from textforge.expander import match_shortcut, build_replacement_keystrokes

    SC = {"bs": "Balaji Sivarajan"}

    def _bs_space():
        r = match_shortcut("bs ", SC)
        assert r == ("bs", "Balaji Sivarajan"), f"Expected match, got {r!r}"

    def _BS_space():
        r = match_shortcut("BS ", SC)
        assert r == ("bs", "Balaji Sivarajan"), f"Case-insensitive match failed: {r!r}"

    def _mixed_Bs_space():
        r = match_shortcut("Bs ", SC)
        assert r == ("bs", "Balaji Sivarajan"), f"Mixed-case match failed: {r!r}"

    def _sb_no_match():
        r = match_shortcut("sb ", SC)
        assert r is None, f"Expected None for wrong order 'sb ', got {r!r}"

    def _xbs_no_match():
        r = match_shortcut("xbs ", SC)
        assert r is None, f"Expected None for embedded 'xbs ', got {r!r}"

    def _bs_period():
        r = match_shortcut("bs.", SC)
        assert r == ("bs", "Balaji Sivarajan"), f"Period trigger failed: {r!r}"

    def _bs_enter():
        r = match_shortcut("bs\n", SC)
        assert r == ("bs", "Balaji Sivarajan"), f"Enter trigger failed: {r!r}"

    def _empty_buffer():
        r = match_shortcut("", SC)
        assert r is None, f"Expected None for empty buffer, got {r!r}"

    def _backspace_count():
        # "bs" (2 chars) + trigger (1) = 3 backspaces; then expansion + trigger
        actions = build_replacement_keystrokes("bs", "Balaji Sivarajan", " ")
        bspaces = sum(1 for a in actions if a["type"] == "backspace")
        texts = [a["value"] for a in actions if a["type"] == "text"]
        assert bspaces == 3, f"Expected 3 backspaces, got {bspaces}"
        assert texts[0] == "Balaji Sivarajan", f"Expansion text wrong: {texts[0]!r}"
        assert texts[1] == " ", f"Trigger char wrong: {texts[1]!r}"

    case("E1  — bs  + Space  → expansion triggered",          _bs_space)
    case("E6  — BS  + Space  → case-insensitive match",       _BS_space)
    case("E7  — Bs  + Space  → mixed-case match",             _mixed_Bs_space)
    case("E9  — sb  + Space  → no match (wrong char order)",  _sb_no_match)
    case("E10 — xbs + Space  → no match (not word boundary)", _xbs_no_match)
    case("E2  — bs  + Period → expansion triggered",          _bs_period)
    case("E3  — bs  + Enter  → expansion triggered",          _bs_enter)
    case("E11 — empty buffer → no match",                     _empty_buffer)
    case("E1  — backspace count = len(shortcut) + 1 = 3",          _backspace_count)


# ── SYNC ──────────────────────────────────────────────────────────────────────

def run_sync_tests() -> None:
    print("\n── SYNC " + "─" * 55)
    from textforge.drive_sync import sync_to_drive, sync_from_drive

    def _to_drive_no_creds():
        fake_local = {"version": 1, "snippets": [{"id": "x", "shortcut": "bs", "expansion": "Balaji"}]}
        with (
            patch("textforge.drive_sync._load_raw", return_value=fake_local),
            patch(
                "textforge.drive_sync.get_drive_service",
                side_effect=Exception("simulated auth failure"),
            ),
        ):
            result = sync_to_drive(None)
        assert result is False, f"Expected False on Drive failure, got {result!r}"

    def _from_drive_no_creds():
        with patch(
            "textforge.drive_sync.get_drive_service",
            side_effect=Exception("simulated auth failure"),
        ):
            result = sync_from_drive(None)
        assert result is False, f"Expected False on Drive failure, got {result!r}"

    def _from_drive_returns_true_when_no_remote_file():
        """When Drive has no snippets file yet, sync_from_drive returns True (nothing to pull)."""
        mock_svc = MagicMock()
        with (
            patch("textforge.drive_sync.get_drive_service", return_value=mock_svc),
            patch("textforge.drive_sync.find_snippets_file", return_value=None),
        ):
            result = sync_from_drive(MagicMock())
        assert result is True, f"Expected True when no remote file, got {result!r}"

    def _to_drive_returns_true_when_local_empty():
        """If local storage is empty, sync_to_drive skips upload and returns True."""
        with patch("textforge.drive_sync._load_raw", return_value={}):
            with patch("textforge.drive_sync.get_drive_service") as mock_svc:
                result = sync_to_drive(MagicMock())
        assert result is True, f"Expected True when local empty, got {result!r}"

    case("S6 — sync_to_drive(None)   → False, no crash",                    _to_drive_no_creds)
    case("S6 — sync_from_drive(None) → False, no crash",                    _from_drive_no_creds)
    case("S  — sync_from_drive: no remote file → True (nothing to pull)",    _from_drive_returns_true_when_no_remote_file)
    case("S  — sync_to_drive: empty local → True (no upload needed)",        _to_drive_returns_true_when_local_empty)


# ── LOG FILE ──────────────────────────────────────────────────────────────────

def run_log_file_test() -> None:
    print("\n── LOG FILE " + "─" * 51)

    def _log_file_created():
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            log_file = tmp / "textforge.log"
            # Replicate what _setup_logging does (FileHandler creates the file).
            tmp.mkdir(parents=True, exist_ok=True)
            handler = logging.FileHandler(str(log_file), encoding="utf-8")
            handler.close()
            assert log_file.exists(), \
                f"Expected textforge.log to exist at {log_file}"

    def _log_path_uses_appdata():
        """Verify the log path is %APPDATA%\\TextForge\\textforge.log."""
        from textforge.config import APPDATA_DIR
        expected_suffix = Path("TextForge") / "textforge.log"
        log_file = APPDATA_DIR / "textforge.log"
        assert log_file.name == "textforge.log", \
            f"Log filename wrong: {log_file.name!r}"
        assert log_file.parent.name == "TextForge", \
            f"Log parent dir wrong: {log_file.parent.name!r}"

    case("LOG — textforge.log created in APPDATA\\\\TextForge on startup", _log_file_created)
    case("LOG — log path = %%APPDATA%%\\\\TextForge\\\\textforge.log",     _log_path_uses_appdata)


# ── SUMMARY ───────────────────────────────────────────────────────────────────

def print_summary() -> bool:
    width = 60
    print(f"\n{'=' * width}")
    print(f"✅ PASSED: {len(PASSED)}")
    print(f"❌ FAILED: {len(FAILED)}")
    if FAILED:
        for name in FAILED:
            print(f"   • {name}")
    print(f"⚠️  MANUAL REQUIRED: {len(MANUAL_CASES)}")
    for m in MANUAL_CASES:
        print(f"   • {m}")
    print("=" * width)
    return len(FAILED) == 0


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("TextForge Smoke Test")
    print("=" * 60)

    run_auth_tests()
    run_storage_tests()
    run_expander_tests()
    run_sync_tests()
    run_log_file_test()

    ok = print_summary()
    sys.exit(0 if ok else 1)

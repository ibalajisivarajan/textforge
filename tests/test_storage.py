import json
import pytest
from pathlib import Path
from unittest.mock import patch


@pytest.fixture(autouse=True)
def isolated_storage(tmp_path):
    """Redirect APPDATA_DIR and SNIPPETS_FILE to a temp directory for each test."""
    snippets_file = tmp_path / "snippets.json"
    with (
        patch("textforge.storage.APPDATA_DIR", tmp_path),
        patch("textforge.storage.SNIPPETS_FILE", snippets_file),
        patch("textforge.config.APPDATA_DIR", tmp_path),
        patch("textforge.config.SNIPPETS_FILE", snippets_file),
    ):
        yield tmp_path, snippets_file


def test_load_missing_file_returns_empty(isolated_storage):
    from textforge.storage import load_snippets
    result = load_snippets()
    assert result == []


def test_add_snippet_creates_file_with_correct_schema(isolated_storage):
    tmp_path, snippets_file = isolated_storage
    from textforge.storage import add_snippet

    snippet = add_snippet("bs", "Balaji Sivarajan")

    assert snippets_file.exists()
    data = json.loads(snippets_file.read_text())
    assert data["version"] == 1
    assert len(data["snippets"]) == 1
    assert data["snippets"][0]["shortcut"] == "bs"
    assert data["snippets"][0]["expansion"] == "Balaji Sivarajan"
    assert "id" in data["snippets"][0]
    assert "created_at" in data["snippets"][0]
    assert "updated_at" in data["snippets"][0]
    assert snippet["shortcut"] == "bs"


def test_add_snippet_lowercases_shortcut(isolated_storage):
    from textforge.storage import add_snippet
    snippet = add_snippet("BS", "Balaji Sivarajan")
    assert snippet["shortcut"] == "bs"


def test_update_snippet_changes_fields(isolated_storage):
    from textforge.storage import add_snippet, update_snippet, load_snippets

    snippet = add_snippet("bs", "Balaji Sivarajan")
    result = update_snippet(snippet["id"], "bsi", "Balaji S Iyer")

    assert result is True
    snippets = load_snippets()
    assert snippets[0]["shortcut"] == "bsi"
    assert snippets[0]["expansion"] == "Balaji S Iyer"


def test_update_nonexistent_snippet_returns_false(isolated_storage):
    from textforge.storage import update_snippet
    result = update_snippet("no-such-id", "x", "y")
    assert result is False


def test_delete_snippet_removes_correctly(isolated_storage):
    from textforge.storage import add_snippet, delete_snippet, load_snippets

    s1 = add_snippet("bs", "Balaji Sivarajan")
    s2 = add_snippet("addr", "123 Main St")

    result = delete_snippet(s1["id"])
    assert result is True

    remaining = load_snippets()
    assert len(remaining) == 1
    assert remaining[0]["id"] == s2["id"]


def test_delete_nonexistent_snippet_returns_false(isolated_storage):
    from textforge.storage import delete_snippet
    result = delete_snippet("no-such-id")
    assert result is False


def test_get_all_shortcuts_returns_lowercase_keys(isolated_storage):
    from textforge.storage import add_snippet, get_all_shortcuts

    add_snippet("BS", "Balaji Sivarajan")
    add_snippet("ADDR", "123 Main St")

    shortcuts = get_all_shortcuts()
    assert "bs" in shortcuts
    assert "addr" in shortcuts
    assert shortcuts["bs"] == "Balaji Sivarajan"
    assert shortcuts["addr"] == "123 Main St"


def test_save_and_reload_multiple_snippets(isolated_storage):
    from textforge.storage import add_snippet, load_snippets

    add_snippet("a", "Alpha")
    add_snippet("b", "Beta")
    add_snippet("c", "Gamma")

    snippets = load_snippets()
    assert len(snippets) == 3
    shortcuts = {s["shortcut"] for s in snippets}
    assert shortcuts == {"a", "b", "c"}


def test_corrupt_file_returns_empty(isolated_storage):
    tmp_path, snippets_file = isolated_storage
    snippets_file.write_text("not valid json")

    from textforge.storage import load_snippets
    result = load_snippets()
    assert result == []

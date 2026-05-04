import pytest
from textforge.expander import match_shortcut, build_replacement_keystrokes


SHORTCUTS = {"bs": "Balaji Sivarajan", "addr": "123 Main St Surrey BC"}


# --- match_shortcut ---

def test_exact_match_with_space():
    result = match_shortcut("bs ", SHORTCUTS)
    assert result == ("bs", "Balaji Sivarajan")


def test_case_insensitive_uppercase():
    assert match_shortcut("BS ", SHORTCUTS) == ("bs", "Balaji Sivarajan")


def test_case_insensitive_mixed_1():
    assert match_shortcut("Bs ", SHORTCUTS) == ("bs", "Balaji Sivarajan")


def test_case_insensitive_mixed_2():
    assert match_shortcut("bS ", SHORTCUTS) == ("bs", "Balaji Sivarajan")


def test_no_match_wrong_order():
    assert match_shortcut("sb ", SHORTCUTS) is None


def test_no_match_embedded_mid_word():
    # "xbs " — 'bs' is not at a word boundary
    assert match_shortcut("xbs ", SHORTCUTS) is None


def test_no_match_no_word_end_char():
    assert match_shortcut("bs", SHORTCUTS) is None


def test_match_with_period():
    assert match_shortcut("bs.", SHORTCUTS) == ("bs", "Balaji Sivarajan")


def test_match_with_comma():
    assert match_shortcut("bs,", SHORTCUTS) == ("bs", "Balaji Sivarajan")


def test_match_with_tab():
    assert match_shortcut("bs\t", SHORTCUTS) == ("bs", "Balaji Sivarajan")


def test_match_with_newline():
    assert match_shortcut("bs\n", SHORTCUTS) == ("bs", "Balaji Sivarajan")


def test_match_with_exclamation():
    assert match_shortcut("bs!", SHORTCUTS) == ("bs", "Balaji Sivarajan")


def test_match_with_question_mark():
    assert match_shortcut("bs?", SHORTCUTS) == ("bs", "Balaji Sivarajan")


def test_match_with_semicolon():
    assert match_shortcut("bs;", SHORTCUTS) == ("bs", "Balaji Sivarajan")


def test_match_with_colon():
    assert match_shortcut("bs:", SHORTCUTS) == ("bs", "Balaji Sivarajan")


def test_empty_buffer():
    assert match_shortcut("", SHORTCUTS) is None


def test_shortcut_longer_than_buffer():
    assert match_shortcut("b ", SHORTCUTS) is None


def test_no_match_empty_shortcuts():
    assert match_shortcut("bs ", {}) is None


def test_match_after_word_end_prefix():
    # " bs " — shortcut preceded by space (word boundary), should match
    result = match_shortcut(" bs ", SHORTCUTS)
    assert result == ("bs", "Balaji Sivarajan")


def test_no_match_only_word_end_chars():
    assert match_shortcut("   ", SHORTCUTS) is None


def test_longer_shortcut_match():
    result = match_shortcut("addr ", SHORTCUTS)
    assert result == ("addr", "123 Main St Surrey BC")


def test_longer_shortcut_no_match_embedded():
    assert match_shortcut("xaddr ", SHORTCUTS) is None


# --- build_replacement_keystrokes ---

def test_build_replacement_keystrokes_structure():
    actions = build_replacement_keystrokes("bs", "Balaji Sivarajan", " ")
    # 2 (shortcut) + 1 (word-end) = 3 backspaces
    backspaces = [a for a in actions if a["type"] == "backspace"]
    texts = [a for a in actions if a["type"] == "text"]
    assert len(backspaces) == 3
    assert texts[0]["value"] == "Balaji Sivarajan"
    assert texts[1]["value"] == " "


def test_build_replacement_preserves_word_end_char():
    actions = build_replacement_keystrokes("addr", "123 Main St", ".")
    texts = [a for a in actions if a["type"] == "text"]
    assert texts[-1]["value"] == "."


def test_build_replacement_backspace_count():
    actions = build_replacement_keystrokes("hello", "World", "\n")
    backspaces = [a for a in actions if a["type"] == "backspace"]
    # len("hello") + 1 = 6
    assert len(backspaces) == 6

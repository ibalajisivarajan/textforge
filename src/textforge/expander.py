from .config import WORD_END_CHARS


def match_shortcut(buffer: str, shortcuts: dict[str, str]) -> tuple[str, str] | None:
    """
    Given the rolling character buffer and the shortcuts lookup dict,
    return (shortcut, expansion) if the buffer ends with a known shortcut
    followed by a word-ending character. Return None if no match.

    Rules:
    - The last character in the buffer must be a word-ending character
    - The shortcut must appear immediately before the word-ending char
    - The shortcut must be at the start of the buffer OR preceded by a word-ending char
      (i.e. it must be at a word boundary — cannot be embedded mid-word)
    - Matching is case-insensitive
    """
    if not buffer:
        return None

    last_char = buffer[-1]
    if last_char not in WORD_END_CHARS:
        return None

    # The part before the word-end char
    before_end = buffer[:-1]
    if not before_end:
        return None

    lower_before = before_end.lower()

    for shortcut, expansion in shortcuts.items():
        sc_lower = shortcut.lower()
        sc_len = len(sc_lower)

        if len(lower_before) < sc_len:
            continue

        # Check that the buffer ends with this shortcut
        if lower_before[-sc_len:] != sc_lower:
            continue

        # Check word-boundary: character before the shortcut must be word-ending or absent
        pos = len(lower_before) - sc_len
        if pos > 0 and lower_before[pos - 1] not in WORD_END_CHARS:
            continue

        return (shortcut, expansion)

    return None


def build_replacement_keystrokes(shortcut: str, expansion: str, word_end_char: str) -> list:
    """
    Return list of keyboard actions:
    1. (len(shortcut) + 1) backspaces to erase shortcut + word-end char
    2. Type expansion
    3. Type word_end_char

    Each action is a dict: {"type": "backspace"} or {"type": "text", "value": str}
    """
    actions = []
    erase_count = len(shortcut) + 1
    for _ in range(erase_count):
        actions.append({"type": "backspace"})
    actions.append({"type": "text", "value": expansion})
    actions.append({"type": "text", "value": word_end_char})
    return actions

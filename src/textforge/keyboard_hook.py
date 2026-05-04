import logging
import threading
from collections import deque

from .config import WORD_END_CHARS, BUFFER_MAX_LEN
from .expander import match_shortcut, build_replacement_keystrokes
from .storage import get_all_shortcuts

log = logging.getLogger(__name__)


class KeyboardHook:
    """
    Global keyboard hook. Maintains a rolling character buffer.
    Fires text expansion when a word-ending character completes a known shortcut.

    Lifecycle:
      hook = KeyboardHook()
      hook.start()
      ...
      hook.reload_shortcuts()   # call after snippet add/edit/delete
      ...
      hook.stop()
    """

    def __init__(self):
        self._buffer: deque[str] = deque(maxlen=BUFFER_MAX_LEN)
        self._shortcuts: dict[str, str] = {}
        self._paused: bool = False
        self._lock = threading.Lock()
        self._hook_ref = None
        self.reload_shortcuts()

    def start(self) -> None:
        """Register the global keyboard hook."""
        try:
            import keyboard
            self._hook_ref = keyboard.on_press(self._on_key_event, suppress=False)
            log.info("Keyboard hook started.")
        except Exception as e:
            log.error("Failed to start keyboard hook: %s", e)

    def stop(self) -> None:
        """Unregister the global keyboard hook."""
        try:
            import keyboard
            keyboard.unhook_all()
            log.info("Keyboard hook stopped.")
        except Exception as e:
            log.warning("Error stopping keyboard hook: %s", e)

    def reload_shortcuts(self) -> None:
        """Re-read shortcuts from storage (call after any snippet mutation)."""
        with self._lock:
            self._shortcuts = get_all_shortcuts()
        log.debug("Shortcuts reloaded: %d entries.", len(self._shortcuts))

    def pause(self) -> None:
        self._paused = True

    def resume(self) -> None:
        self._paused = False

    @property
    def is_paused(self) -> bool:
        return self._paused

    def _on_key_event(self, event) -> None:
        if self._paused:
            return

        name = event.name

        if name == "backspace":
            with self._lock:
                if self._buffer:
                    self._buffer.pop()
            return

        if name == "esc" or name == "escape":
            with self._lock:
                self._buffer.clear()
            return

        # Map keyboard library key names to their character
        char = _key_name_to_char(name)
        if char is None:
            return

        with self._lock:
            self._buffer.append(char)
            buffer_str = "".join(self._buffer)
            shortcuts_snapshot = dict(self._shortcuts)

        if char in WORD_END_CHARS:
            match = match_shortcut(buffer_str, shortcuts_snapshot)
            if match:
                shortcut, expansion = match
                word_end_char = char
                actions = build_replacement_keystrokes(shortcut, expansion, word_end_char)
                # Defer expansion to avoid deadlock on the hook thread
                threading.Timer(0, lambda: self._fire_expansion(actions)).start()
                # Clear buffer after scheduling expansion
                with self._lock:
                    self._buffer.clear()

    def _fire_expansion(self, actions: list) -> None:
        try:
            import keyboard
            for action in actions:
                if action["type"] == "backspace":
                    keyboard.send("backspace")
                elif action["type"] == "text":
                    keyboard.write(action["value"], delay=0)
        except Exception as e:
            log.warning("Expansion failed: %s", e)


def _key_name_to_char(name: str) -> str | None:
    """Convert keyboard library key name to printable character, or None."""
    if name is None:
        return None

    # Single printable character
    if len(name) == 1:
        return name

    # Named keys mapped to their characters
    _named = {
        "space": " ",
        "tab": "\t",
        "enter": "\n",
        "return": "\r",
        "period": ".",
        "comma": ",",
        "semicolon": ";",
        "colon": ":",
        "exclamation": "!",
        "question": "?",
    }
    return _named.get(name)

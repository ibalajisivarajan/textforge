import logging
import threading
import time
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
      hook.start()              # called after a startup delay (see app.py)
      ...
      hook.reload_shortcuts()   # call after snippet add/edit/delete
      hook.pause()              # unregisters hook — no events processed
      hook.resume()             # re-registers hook
      hook.stop()               # permanent stop (called by app.quit)

    Watchdog:
      A daemon thread started in __init__ checks every 15 s whether the
      hook is still active and whether it has seen a keypress recently.
      This self-heals the rare case where start() failed (e.g. OS not
      ready), the hook was silently unregistered, or Windows invalidated
      the low-level hook across sleep/wake while our state still looked
      active.
    """

    def __init__(self):
        self._buffer: deque[str] = deque(maxlen=BUFFER_MAX_LEN)
        self._shortcuts: dict[str, str] = {}
        self._paused: bool = False
        self._hook_active: bool = False
        self._last_key_time: float = time.time()
        self._lock = threading.Lock()
        # Used only to wake the watchdog early on app shutdown (daemon=True
        # handles the rest — no need to set this explicitly).
        self._stop_event = threading.Event()
        self.reload_shortcuts()

        threading.Thread(target=self._watchdog, daemon=True, name="tf-hook-watchdog").start()

    def start(self) -> None:
        """Register the global keyboard hook."""
        if self._hook_active:
            log.debug("Keyboard hook start requested, but hook is already marked active.")
            return
        try:
            import keyboard
            keyboard.on_press(self._on_key_event, suppress=False)
            self._last_key_time = time.time()
            self._hook_active = True
            log.info("Keyboard hook started.")
        except Exception as e:
            self._hook_active = False
            log.error("Failed to start keyboard hook: %s", e)

    def stop(self) -> None:
        """Unregister the global keyboard hook."""
        self._hook_active = False
        try:
            import keyboard
            keyboard.unhook_all()
            log.info("Keyboard hook stopped.")
        except Exception as e:
            log.warning("Error stopping keyboard hook: %s", e)

    def pause(self) -> None:
        """Stop listening and clear the buffer."""
        self._paused = True
        with self._lock:
            self._buffer.clear()
        self.stop()
        log.info("Expansion paused.")

    def resume(self) -> None:
        """Re-register the hook and resume expansion."""
        self._paused = False
        self.start()
        log.info("Expansion resumed.")

    def reload_shortcuts(self) -> None:
        """Re-read shortcuts from storage (call after any snippet mutation)."""
        with self._lock:
            self._shortcuts = get_all_shortcuts()
        log.debug("Shortcuts reloaded: %d entries.", len(self._shortcuts))

    @property
    def is_paused(self) -> bool:
        return self._paused

    def _is_hook_active(self) -> bool:
        """Return whether the hook appears to be registered.

        `_hook_active` is still useful for detecting failed starts and explicit
        stops, but Windows can invalidate a low-level keyboard hook during
        sleep/wake without notifying the `keyboard` package.  The watchdog
        therefore combines this flag with a recent-keypress check instead of
        trusting the flag by itself.
        """
        return self._hook_active

    def _watchdog(self) -> None:
        """
        Every 15 s: restart the hook if it is inactive or may be stale.

        The stale check is intentionally conservative: a user may simply have
        been idle for 45+ seconds, but restarting an active hook is cheap and
        is safer than leaving TextForge broken after Windows sleep/wake.
        """
        while not self._stop_event.wait(15):
            if self.is_paused:
                continue

            if not self._is_hook_active():
                log.warning("Keyboard hook not active — restarting.")
                self.start()
                continue

            idle_seconds = time.time() - self._last_key_time
            if idle_seconds > 45:
                log.warning(
                    "Hook may be stale — restarting after %.1f seconds without keypress.",
                    idle_seconds,
                )
                self.stop()
                self.start()

    def _on_key_event(self, event) -> None:
        self._last_key_time = time.time()

        if self._paused:
            return

        name = event.name

        if name == "backspace":
            with self._lock:
                if self._buffer:
                    self._buffer.pop()
            return

        if name in ("esc", "escape"):
            with self._lock:
                self._buffer.clear()
            return

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
                actions = build_replacement_keystrokes(shortcut, expansion, char)
                # Defer to next tick — firing keyboard events from inside a
                # keyboard hook callback causes a deadlock on Windows.
                threading.Timer(0, lambda: self._fire_expansion(actions)).start()
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
    if len(name) == 1:
        return name
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

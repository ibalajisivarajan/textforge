import logging
import threading
from typing import Optional

from .config import APPDATA_DIR, SYNC_INTERVAL_SECONDS

log = logging.getLogger(__name__)


class TextForgeApp:
    """
    Main application class. Wires all components together.
    Call start() to launch. Blocks until quit() is called.
    """

    def __init__(self):
        self.credentials = None
        self.user_email: Optional[str] = None
        self.keyboard_hook = None
        self._tray_icon = None
        self._main_window = None
        self._sync_timer: Optional[threading.Timer] = None

    def start(self):
        """Full startup sequence. Blocks on tray.run()."""
        # 1. Ensure APPDATA_DIR exists
        APPDATA_DIR.mkdir(parents=True, exist_ok=True)

        # 2. Load local snippets (storage does this lazily; just ensure dir exists)
        from .storage import load_snippets
        snippets = load_snippets()
        log.info("Loaded %d local snippets.", len(snippets))

        # 3. Try to restore credentials from token.json
        from .auth import get_credentials, get_user_email
        self.credentials = get_credentials()
        if self.credentials:
            self.user_email = get_user_email(self.credentials)
            log.info("Signed in as %s.", self.user_email)
            # 4. Sync from Drive on startup in background
            threading.Thread(target=self._startup_sync, daemon=True).start()

        # 5. Start keyboard hook
        from .keyboard_hook import KeyboardHook
        self.keyboard_hook = KeyboardHook()
        self.keyboard_hook.start()

        # 6. Start periodic sync timer
        self._schedule_sync()

        # 7. Build and run tray (blocking)
        from .tray import build_tray_icon
        self._tray_icon = build_tray_icon(self)
        log.info("TextForge started. Running in system tray.")
        self._tray_icon.run()

    def _startup_sync(self):
        from .drive_sync import sync_from_drive
        ok = sync_from_drive(self.credentials)
        if ok:
            log.info("Startup sync from Drive complete.")
            if self.keyboard_hook:
                self.keyboard_hook.reload_shortcuts()

    def _schedule_sync(self):
        self._sync_timer = threading.Timer(SYNC_INTERVAL_SECONDS, self._periodic_sync)
        self._sync_timer.daemon = True
        self._sync_timer.start()

    def _periodic_sync(self):
        if self.credentials:
            from .drive_sync import sync_to_drive, sync_from_drive
            sync_to_drive(self.credentials)
            sync_from_drive(self.credentials)
            if self.keyboard_hook:
                self.keyboard_hook.reload_shortcuts()
            if self._main_window:
                try:
                    from datetime import datetime
                    ts = datetime.now().strftime("%I:%M %p").lstrip("0")
                    self._main_window.set_sync_status(f"Synced ✓ {ts}")
                except Exception:
                    pass
        self._schedule_sync()

    # --- Actions callable from tray menu ---

    def open_main_window(self):
        """Open or focus the snippet manager window."""
        if self._main_window is None:
            from .ui.main_window import MainWindow
            self._main_window = MainWindow(self)
        else:
            self._main_window.show()
        self._main_window.mainloop()

    def sign_in(self):
        """Run OAuth flow and update state."""
        from .auth import run_oauth_flow, get_user_email
        from .drive_sync import sync_from_drive
        try:
            self.credentials = run_oauth_flow()
            self.user_email = get_user_email(self.credentials)
            log.info("Signed in as %s.", self.user_email)
            if self._tray_icon:
                self._tray_icon.update_menu()
            threading.Thread(
                target=lambda: sync_from_drive(self.credentials), daemon=True
            ).start()
        except Exception as e:
            log.error("Sign in failed: %s", e)

    def sign_out(self):
        """Sign out and clear state."""
        from .auth import sign_out as auth_sign_out
        auth_sign_out()
        self.credentials = None
        self.user_email = None
        log.info("Signed out.")
        if self._tray_icon:
            self._tray_icon.update_menu()

    def sync_now(self):
        """Manual sync from tray menu."""
        if not self.credentials:
            log.info("Sync skipped — not signed in.")
            return
        from .drive_sync import sync_to_drive, sync_from_drive
        sync_to_drive(self.credentials)
        sync_from_drive(self.credentials)
        if self.keyboard_hook:
            self.keyboard_hook.reload_shortcuts()
        if self._main_window:
            from datetime import datetime
            ts = datetime.now().strftime("%I:%M %p").lstrip("0")
            self._main_window.set_sync_status(f"Synced ✓ {ts}")

    def toggle_pause(self):
        """Pause or resume the keyboard hook."""
        if self.keyboard_hook:
            if self.keyboard_hook.is_paused:
                self.keyboard_hook.resume()
                log.info("Expansion resumed.")
            else:
                self.keyboard_hook.pause()
                log.info("Expansion paused.")

    def quit(self):
        """Clean shutdown."""
        if self._sync_timer:
            self._sync_timer.cancel()
        if self.keyboard_hook:
            self.keyboard_hook.stop()
        if self._tray_icon:
            self._tray_icon.stop()
        import sys
        sys.exit(0)

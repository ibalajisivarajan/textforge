import logging
import threading
from datetime import datetime
from typing import Optional

from .config import APPDATA_DIR, SYNC_INTERVAL_SECONDS, APP_NAME

log = logging.getLogger(__name__)


class TextForgeApp:
    """
    Main application class. Wires all components together.

    Threading model:
      - Main thread: customtkinter mainloop (MainWindow is the CTk root)
      - Background thread: pystray (run_detached)
      - Background threads: Drive sync, keyboard expansion, sign-in flow
      - All cross-thread UI calls must go through self._main_window.after(0, fn)
    """

    def __init__(self):
        self.credentials = None
        self.user_email: Optional[str] = None
        self.keyboard_hook = None
        self._tray_icon = None
        self._main_window = None
        self._sync_timer: Optional[threading.Timer] = None

    def start(self):
        """Full startup sequence. Blocks on tkinter mainloop."""
        APPDATA_DIR.mkdir(parents=True, exist_ok=True)

        from .storage import load_snippets
        log.info("Loaded %d local snippets.", len(load_snippets()))

        from .auth import get_credentials, get_user_email
        self.credentials = get_credentials()
        if self.credentials:
            self.user_email = get_user_email(self.credentials)
            log.info("Signed in as %s.", self.user_email)
            threading.Thread(target=self._startup_sync, daemon=True).start()

        from .keyboard_hook import KeyboardHook
        self.keyboard_hook = KeyboardHook()
        self.keyboard_hook.start()

        self._schedule_sync()

        # MainWindow IS the CTk root — create it hidden, run mainloop on it.
        from .ui.main_window import MainWindow
        self._main_window = MainWindow(self)
        self._main_window.withdraw()

        # pystray runs in background so main thread stays free for tkinter.
        from .tray import build_tray_icon
        self._tray_icon = build_tray_icon(self)
        self._tray_icon.run_detached()

        log.info("TextForge started. Running in system tray.")
        self._main_window.mainloop()  # blocks until quit() destroys the root

    # --- Sync helpers ---

    def _startup_sync(self):
        from .drive_sync import sync_from_drive
        ok = sync_from_drive(self.credentials)
        if ok and self.keyboard_hook:
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
            self._update_sync_label()
        self._schedule_sync()

    def _update_sync_label(self):
        if self._main_window:
            ts = datetime.now().strftime("%I:%M %p").lstrip("0")
            self._main_window.after(
                0, lambda: self._main_window.set_sync_status(f"Synced ✓ {ts}")
            )

    def _notify(self, message: str):
        """Show a tray balloon notification (non-fatal if unsupported)."""
        try:
            if self._tray_icon:
                self._tray_icon.notify(message, APP_NAME)
        except Exception as e:
            log.debug("Tray notify failed (non-fatal): %s", e)

    # --- Actions callable from tray menu (called on pystray thread) ---

    def open_main_window(self):
        """Schedule show on the tkinter thread."""
        if self._main_window:
            self._main_window.after(0, self._main_window.show)

    def sign_in(self):
        from .auth import run_oauth_flow, get_user_email
        from .drive_sync import sync_from_drive
        try:
            self.credentials = run_oauth_flow()
            self.user_email = get_user_email(self.credentials)
            log.info("Signed in as %s.", self.user_email)
            self._notify(f"Signed in as {self.user_email}")
            threading.Thread(
                target=lambda: sync_from_drive(self.credentials), daemon=True
            ).start()
        except Exception as e:
            log.error("Sign in failed: %s", e)

    def sign_out(self):
        from .auth import sign_out as auth_sign_out
        auth_sign_out()
        self.credentials = None
        self.user_email = None
        log.info("Signed out.")
        self._notify("Signed out of TextForge.")

    def sync_now(self):
        """Manual sync triggered from tray. Notifies on completion."""
        if not self.credentials:
            self._notify("Sign in first to sync snippets.")
            return
        from .drive_sync import sync_to_drive, sync_from_drive
        push_ok = sync_to_drive(self.credentials)
        pull_ok = sync_from_drive(self.credentials)
        if self.keyboard_hook:
            self.keyboard_hook.reload_shortcuts()
        self._update_sync_label()
        if push_ok and pull_ok:
            self._notify("Snippets synced successfully.")
        else:
            self._notify("Sync completed with errors — check your connection.")

    def sync_after_save(self):
        """Push snippets to Drive after a snippet add/edit/delete."""
        if not self.credentials:
            return
        from .drive_sync import sync_to_drive
        threading.Thread(
            target=lambda: self._do_sync_after_save(), daemon=True
        ).start()

    def _do_sync_after_save(self):
        from .drive_sync import sync_to_drive
        sync_to_drive(self.credentials)
        self._update_sync_label()

    def toggle_pause(self):
        if self.keyboard_hook:
            if self.keyboard_hook.is_paused:
                self.keyboard_hook.resume()
                self._notify("Text expansion resumed.")
            else:
                self.keyboard_hook.pause()
                self._notify("Text expansion paused.")

    def quit(self):
        if self._sync_timer:
            self._sync_timer.cancel()
        if self.keyboard_hook:
            self.keyboard_hook.stop()
        if self._tray_icon:
            self._tray_icon.stop()
        if self._main_window:
            self._main_window.after(0, self._main_window.destroy)

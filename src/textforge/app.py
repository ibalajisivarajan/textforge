import logging
import sys
import threading
import time
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
        self._hook_restart_lock = threading.Lock()
        self._power_monitor_thread: Optional[threading.Thread] = None
        self._power_monitor_hwnd = None
        self._power_monitor_wndproc = None

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
        # Do NOT start the hook immediately — on Windows startup the low-level
        # hook infrastructure may not be ready yet.  A 5-second delay after the
        # tray is visible avoids silent registration failures.

        self._schedule_sync()

        # MainWindow IS the CTk root — create it hidden, run mainloop on it.
        from .ui.main_window import MainWindow
        self._main_window = MainWindow(self)
        self._main_window.withdraw()

        # pystray runs in background so main thread stays free for tkinter.
        from .tray import build_tray_icon
        self._tray_icon = build_tray_icon(self)
        self._tray_icon.run_detached()

        # Start the keyboard hook after a short delay so the OS hook
        # infrastructure is fully initialised before we register.
        threading.Thread(
            target=self._delayed_hook_start, daemon=True, name="tf-hook-delay"
        ).start()

        self._start_power_monitor()

        log.info("TextForge started. Running in system tray.")
        self._main_window.mainloop()  # blocks until quit() destroys the root

    # --- Startup helpers ---

    def _delayed_hook_start(self):
        time.sleep(5)
        if self.keyboard_hook:
            self.keyboard_hook.start()

    def _start_power_monitor(self):
        """Listen for Windows sleep/wake events and restart the hook on wake."""
        if sys.platform != "win32":
            log.debug("Windows power monitor skipped on non-Windows platform.")
            return

        if self._power_monitor_thread and self._power_monitor_thread.is_alive():
            log.debug("Windows power monitor already running.")
            return

        def monitor():
            import ctypes
            import ctypes.wintypes

            HWND_MESSAGE = -3
            WM_POWERBROADCAST = 0x0218
            PBT_APMRESUMEAUTOMATIC = 0x0012
            PBT_APMRESUMESUSPEND = 0x0007

            LRESULT = ctypes.c_ssize_t
            WNDPROC = ctypes.WINFUNCTYPE(
                LRESULT,
                ctypes.wintypes.HWND,
                ctypes.wintypes.UINT,
                ctypes.wintypes.WPARAM,
                ctypes.wintypes.LPARAM,
            )

            class WNDCLASSW(ctypes.Structure):
                _fields_ = [
                    ("style", ctypes.wintypes.UINT),
                    ("lpfnWndProc", WNDPROC),
                    ("cbClsExtra", ctypes.c_int),
                    ("cbWndExtra", ctypes.c_int),
                    ("hInstance", ctypes.wintypes.HINSTANCE),
                    ("hIcon", ctypes.wintypes.HICON),
                    ("hCursor", ctypes.wintypes.HCURSOR),
                    ("hbrBackground", ctypes.wintypes.HBRUSH),
                    ("lpszMenuName", ctypes.wintypes.LPCWSTR),
                    ("lpszClassName", ctypes.wintypes.LPCWSTR),
                ]

            user32 = ctypes.WinDLL("user32", use_last_error=True)
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

            kernel32.GetModuleHandleW.argtypes = [ctypes.wintypes.LPCWSTR]
            kernel32.GetModuleHandleW.restype = ctypes.wintypes.HMODULE
            user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
            user32.RegisterClassW.restype = ctypes.wintypes.ATOM
            user32.CreateWindowExW.argtypes = [
                ctypes.wintypes.DWORD,
                ctypes.wintypes.LPCWSTR,
                ctypes.wintypes.LPCWSTR,
                ctypes.wintypes.DWORD,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.c_int,
                ctypes.wintypes.HWND,
                ctypes.wintypes.HMENU,
                ctypes.wintypes.HINSTANCE,
                ctypes.wintypes.LPVOID,
            ]
            user32.CreateWindowExW.restype = ctypes.wintypes.HWND
            user32.DefWindowProcW.argtypes = [
                ctypes.wintypes.HWND,
                ctypes.wintypes.UINT,
                ctypes.wintypes.WPARAM,
                ctypes.wintypes.LPARAM,
            ]
            user32.DefWindowProcW.restype = LRESULT
            user32.GetMessageW.argtypes = [
                ctypes.POINTER(ctypes.wintypes.MSG),
                ctypes.wintypes.HWND,
                ctypes.wintypes.UINT,
                ctypes.wintypes.UINT,
            ]
            user32.GetMessageW.restype = ctypes.wintypes.BOOL
            user32.TranslateMessage.argtypes = [ctypes.POINTER(ctypes.wintypes.MSG)]
            user32.TranslateMessage.restype = ctypes.wintypes.BOOL
            user32.DispatchMessageW.argtypes = [ctypes.POINTER(ctypes.wintypes.MSG)]
            user32.DispatchMessageW.restype = LRESULT

            class_name = "TextForgePowerMonitorWindow"

            def wnd_proc(hwnd, msg, wparam, lparam):
                if msg == WM_POWERBROADCAST:
                    log.debug("Received WM_POWERBROADCAST event: wparam=%s", wparam)
                    if wparam in (PBT_APMRESUMEAUTOMATIC, PBT_APMRESUMESUSPEND):
                        log.info("System resumed from sleep — scheduling hook restart.")
                        timer = threading.Timer(3, self._restart_hook)
                        timer.daemon = True
                        timer.start()
                return user32.DefWindowProcW(hwnd, msg, wparam, lparam)

            try:
                hinstance = kernel32.GetModuleHandleW(None)
                wndproc = WNDPROC(wnd_proc)
                self._power_monitor_wndproc = wndproc

                wndclass = WNDCLASSW()
                wndclass.lpfnWndProc = wndproc
                wndclass.hInstance = hinstance
                wndclass.lpszClassName = class_name

                atom = user32.RegisterClassW(ctypes.byref(wndclass))
                if not atom:
                    error = ctypes.get_last_error()
                    # ERROR_CLASS_ALREADY_EXISTS (1410) is harmless after app reloads.
                    if error != 1410:
                        raise ctypes.WinError(error)
                    log.debug("Power monitor window class already registered.")

                hwnd = user32.CreateWindowExW(
                    0,
                    class_name,
                    "TextForge Power Monitor",
                    0,
                    0,
                    0,
                    0,
                    0,
                    ctypes.wintypes.HWND(HWND_MESSAGE),
                    None,
                    hinstance,
                    None,
                )
                if not hwnd:
                    raise ctypes.WinError(ctypes.get_last_error())

                self._power_monitor_hwnd = hwnd
                log.info("Windows power monitor started.")

                msg = ctypes.wintypes.MSG()
                while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
                    user32.TranslateMessage(ctypes.byref(msg))
                    user32.DispatchMessageW(ctypes.byref(msg))
            except Exception as e:
                log.warning("Windows power monitor failed: %s", e)

        self._power_monitor_thread = threading.Thread(
            target=monitor, daemon=True, name="tf-power-monitor"
        )
        self._power_monitor_thread.start()
        log.debug("Windows power monitor thread launched.")

    def _restart_hook(self):
        """Safely restart the keyboard hook after Windows resumes from sleep."""
        if not self.keyboard_hook:
            log.debug("Hook restart requested, but keyboard hook is not initialised.")
            return

        if self.keyboard_hook.is_paused:
            log.info("Hook restart skipped because expansion is paused.")
            return

        if not self._hook_restart_lock.acquire(blocking=False):
            log.debug("Hook restart already in progress; skipping duplicate request.")
            return

        try:
            log.info("Restarting keyboard hook after sleep/wake.")
            self.keyboard_hook.stop()
            time.sleep(1)
            self.keyboard_hook.start()
            log.info("Hook restarted after sleep/wake.")
        finally:
            self._hook_restart_lock.release()

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
            try:
                ts = datetime.now().strftime("%I:%M %p").lstrip("0")
                self._main_window.after(
                    0, lambda: self._main_window.set_sync_status(f"Synced ✓ {ts}")
                )
            except Exception as e:
                log.debug("Failed to update sync label: %s", e)

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
            if self._tray_icon:
                self._tray_icon.update_menu()
            threading.Thread(
                target=lambda: sync_from_drive(self.credentials), daemon=True
            ).start()
        except Exception as e:
            log.error("Sign in failed: %s", e)
            self._notify(f"Sign in failed: {type(e).__name__}: {e}")

    def sign_out(self):
        from .auth import sign_out as auth_sign_out
        auth_sign_out()
        self.credentials = None
        self.user_email = None
        log.info("Signed out.")
        self._notify("Signed out of TextForge.")
        if self._tray_icon:
            self._tray_icon.update_menu()

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

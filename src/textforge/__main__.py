import logging
import sys
import os

# Support both `python -m textforge` (relative imports) and PyInstaller bundled exe (absolute)
try:
    from .config import APPDATA_DIR, LOCK_FILE, APP_NAME
except ImportError:
    from textforge.config import APPDATA_DIR, LOCK_FILE, APP_NAME


def _setup_logging():
    APPDATA_DIR.mkdir(parents=True, exist_ok=True)
    log_file = APPDATA_DIR / "textforge.log"
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(log_file, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def _is_process_alive(pid: int) -> bool:
    """Windows-compatible check: return True if process with given pid is running."""
    try:
        import ctypes
        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        handle = ctypes.windll.kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if handle:
            ctypes.windll.kernel32.CloseHandle(handle)
            return True
        return False
    except Exception:
        return False


def _acquire_lock() -> bool:
    """Return True if we acquired the lock (no other instance running)."""
    APPDATA_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        try:
            pid = int(LOCK_FILE.read_text().strip())
            if _is_process_alive(pid):
                return False  # Another instance is running
        except (ValueError, OSError):
            pass  # Stale lock file — previous instance crashed
    LOCK_FILE.write_text(str(os.getpid()))
    return True


def _release_lock():
    try:
        LOCK_FILE.unlink()
    except OSError:
        pass


def main():
    _setup_logging()
    log = logging.getLogger(__name__)

    if not _acquire_lock():
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(
                0,
                f"{APP_NAME} is already running.\nCheck the system tray.",
                APP_NAME,
                0x40,  # MB_ICONINFORMATION
            )
        except Exception:
            pass
        sys.exit(0)

    try:
        try:
            from .app import TextForgeApp
        except ImportError:
            from textforge.app import TextForgeApp
        app = TextForgeApp()
        app.start()
    except Exception as e:
        log.exception("Fatal error: %s", e)
        raise
    finally:
        _release_lock()


if __name__ == "__main__":
    main()

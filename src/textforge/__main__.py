import logging
import sys
import os

from .config import APPDATA_DIR, LOCK_FILE, APP_NAME


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


def _acquire_lock() -> bool:
    """Return True if we acquired the lock (no other instance running)."""
    APPDATA_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        try:
            pid = int(LOCK_FILE.read_text().strip())
            os.kill(pid, 0)
            return False  # process alive — another instance running
        except (ValueError, OSError) as e:
            logging.getLogger(__name__).debug("Removing stale lock file (pid check failed: %s).", e)
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
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0,
            f"{APP_NAME} is already running.\nCheck the system tray.",
            APP_NAME,
            0x40,  # MB_ICONINFORMATION
        )
        sys.exit(0)

    try:
        from .app import TextForgeApp
        app = TextForgeApp()
        app.start()
    except Exception as e:
        log.exception("Fatal error: %s", e)
        raise
    finally:
        _release_lock()


if __name__ == "__main__":
    main()

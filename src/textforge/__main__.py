import logging
import sys
import os

# Support both `python -m textforge` (relative imports) and PyInstaller bundled exe (absolute)
try:
    from .config import APPDATA_DIR, LOCK_FILE, APP_NAME
except ImportError:
    from textforge.config import APPDATA_DIR, LOCK_FILE, APP_NAME


def _setup_oauth_env():
    """
    Tell requests_oauthlib not to raise when Google returns extra scopes
    (e.g. 'openid') alongside the ones we requested. Without this, the
    token exchange raises 'Warning: Scope has changed' and sign-in fails.
    """
    os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")


def _setup_ssl():
    """
    Point requests and httplib2 at the bundled certifi CA store.
    Must be called before any HTTPS request — critical in PyInstaller bundles
    where the default certificate path doesn't exist on disk.
    """
    try:
        import certifi
        ca_bundle = certifi.where()
        os.environ.setdefault("SSL_CERT_FILE", ca_bundle)
        os.environ.setdefault("REQUESTS_CA_BUNDLE", ca_bundle)
    except Exception as e:
        logging.getLogger(__name__).debug("certifi not available, using system certs: %s", e)


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
    except Exception as e:
        logging.getLogger(__name__).debug("Process alive check failed: %s", e)
        return False


def _acquire_lock() -> bool:
    """Return True if we acquired the lock (no other instance running)."""
    APPDATA_DIR.mkdir(parents=True, exist_ok=True)
    if LOCK_FILE.exists():
        try:
            pid = int(LOCK_FILE.read_text().strip())
            if _is_process_alive(pid):
                return False  # Another instance is running
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
    _setup_oauth_env()  # must be before any OAuth call
    _setup_ssl()        # must be before any HTTPS call
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

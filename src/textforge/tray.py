import logging
import threading
from pathlib import Path

from .config import APP_NAME, VERSION

log = logging.getLogger(__name__)

# Resolved at runtime to avoid circular imports
_app_ref = None


def _get_icon_image():
    """Load icon from assets/icon.ico or generate a fallback PIL image."""
    from PIL import Image, ImageDraw, ImageFont

    icon_path = Path(__file__).parent.parent.parent / "assets" / "icon.ico"
    if icon_path.exists():
        try:
            return Image.open(str(icon_path))
        except Exception:
            pass

    # Fallback: draw "TF" on a dark background
    img = Image.new("RGBA", (64, 64), color="#1a1a2e")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except Exception:
        font = ImageFont.load_default()
    draw.text((8, 16), "TF", fill="white", font=font)
    return img


def build_tray_icon(app):
    """Build and return a pystray.Icon. Does not start it."""
    import pystray
    from pystray import MenuItem, Menu

    global _app_ref
    _app_ref = app

    def _signed_in_label(item):
        email = getattr(app, "user_email", None)
        return f"Signed in as: {email}" if email else "Not signed in"

    def _on_manage(icon, item):
        threading.Thread(target=app.open_main_window, daemon=True).start()

    def _on_sign_in(icon, item):
        threading.Thread(target=app.sign_in, daemon=True).start()

    def _on_sign_out(icon, item):
        threading.Thread(target=app.sign_out, daemon=True).start()

    def _on_sync_now(icon, item):
        threading.Thread(target=app.sync_now, daemon=True).start()

    def _on_toggle_pause(icon, item):
        app.toggle_pause()
        icon.update_menu()

    def _on_quit(icon, item):
        app.quit()

    def _is_signed_in(item):
        return getattr(app, "user_email", None) is not None

    def _is_signed_out(item):
        return not _is_signed_in(item)

    def _is_paused(item):
        hook = getattr(app, "keyboard_hook", None)
        return hook.is_paused if hook else False

    menu = Menu(
        MenuItem(f"{APP_NAME} v{VERSION}", None, enabled=False),
        Menu.SEPARATOR,
        MenuItem(_signed_in_label, None, enabled=False),
        Menu.SEPARATOR,
        MenuItem("Manage Snippets", _on_manage),
        MenuItem("Sign In", _on_sign_in, visible=_is_signed_out),
        MenuItem("Sign Out", _on_sign_out, visible=_is_signed_in),
        MenuItem("Sync Now", _on_sync_now),
        Menu.SEPARATOR,
        MenuItem("Pause Expansion", _on_toggle_pause, checked=_is_paused),
        Menu.SEPARATOR,
        MenuItem("Quit", _on_quit),
    )

    icon = pystray.Icon(
        name=APP_NAME,
        icon=_get_icon_image(),
        title=APP_NAME,
        menu=menu,
    )
    return icon

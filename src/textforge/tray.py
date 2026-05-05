import logging
import threading
from pathlib import Path

from .config import APP_NAME, VERSION

log = logging.getLogger(__name__)


def _get_icon_image():
    """Load icon.ico or generate a fallback 'TF' image."""
    from PIL import Image, ImageDraw, ImageFont

    icon_path = Path(__file__).parent.parent.parent / "assets" / "icon.ico"
    if icon_path.exists():
        try:
            return Image.open(str(icon_path))
        except Exception:
            pass

    img = Image.new("RGBA", (64, 64), color="#1a1a2e")
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("arial.ttf", 28)
    except Exception:
        font = ImageFont.load_default()
    draw.text((8, 16), "TF", fill="white", font=font)
    return img


def build_tray_icon(app):
    """Build and return a pystray.Icon with a fully dynamic menu."""
    import pystray
    from pystray import MenuItem, Menu

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

    def _on_quit(icon, item):
        app.quit()

    def _menu_items():
        """
        Called fresh every time the menu is opened, so Sign In/Out state,
        account label, and pause state are always current.
        """
        creds = getattr(app, "credentials", None)
        email = getattr(app, "user_email", None)
        signed_in = creds is not None
        hook = getattr(app, "keyboard_hook", None)
        paused = hook.is_paused if hook else False

        if email:
            account_label = f"● {email}"
        elif signed_in:
            account_label = "● Signed in"
        else:
            account_label = "● Not signed in"
        pause_label = "Resume Expansion" if paused else "Pause Expansion"

        items = [
            MenuItem(f"{APP_NAME} v{VERSION}", None, enabled=False),
            Menu.SEPARATOR,
            MenuItem(account_label, None, enabled=False),
            Menu.SEPARATOR,
            MenuItem("Manage Snippets", _on_manage),
        ]

        if signed_in:
            items.append(MenuItem("Sign Out", _on_sign_out))
            items.append(MenuItem("Sync Now", _on_sync_now))
        else:
            items.append(MenuItem("Sign In", _on_sign_in))

        items += [
            Menu.SEPARATOR,
            MenuItem(pause_label, _on_toggle_pause),
            Menu.SEPARATOR,
            MenuItem("Quit", _on_quit),
        ]
        return items

    icon = pystray.Icon(
        name=APP_NAME,
        icon=_get_icon_image(),
        title=APP_NAME,
        menu=Menu(_menu_items),
    )
    return icon

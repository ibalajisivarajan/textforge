import logging
import threading
from datetime import datetime

import customtkinter as ctk

log = logging.getLogger(__name__)

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class MainWindow(ctk.CTk):
    """
    The TextForge snippet manager window. This IS the CTk root window.
    Created hidden at startup; shown/hidden on demand via show() / withdraw().
    Never destroyed until quit() — closing the window only hides it.
    """

    def __init__(self, app_ref):
        super().__init__()
        self._app = app_ref
        self._all_snippets: list[dict] = []
        self._filtered_snippets: list[dict] = []
        self._selected_idx: int | None = None
        self._row_frames: list[ctk.CTkFrame] = []

        self.title("TextForge — Snippets")
        self.geometry("600x450")
        self.resizable(True, True)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_ui()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # Search bar
        self._search_var = ctk.StringVar()
        self._search_var.trace_add("write", lambda *_: self._on_search_change())
        search_entry = ctk.CTkEntry(
            self, textvariable=self._search_var,
            placeholder_text="Search snippets...",
            height=36,
        )
        search_entry.grid(row=0, column=0, padx=12, pady=(12, 4), sticky="ew")

        # Column headers
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.grid(row=1, column=0, padx=12, pady=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)
        header.grid_columnconfigure(1, weight=3)
        ctk.CTkLabel(header, text="SHORTCUT", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="gray").grid(row=0, column=0, sticky="w", padx=4)
        ctk.CTkLabel(header, text="EXPANSION", font=ctk.CTkFont(size=11, weight="bold"),
                     text_color="gray").grid(row=0, column=1, sticky="w", padx=4)

        # Scrollable snippet list
        self._scroll_frame = ctk.CTkScrollableFrame(self)
        self._scroll_frame.grid(row=2, column=0, padx=12, pady=4, sticky="nsew")
        self._scroll_frame.grid_columnconfigure(0, weight=1)
        self._scroll_frame.grid_columnconfigure(1, weight=3)

        # Bottom action bar
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=3, column=0, padx=12, pady=(4, 12), sticky="ew")
        bottom.grid_columnconfigure(2, weight=1)

        self._btn_add = ctk.CTkButton(bottom, text="+ Add", width=80, command=self._on_add)
        self._btn_add.grid(row=0, column=0, padx=(0, 6))

        self._btn_edit = ctk.CTkButton(bottom, text="✏ Edit", width=80,
                                       command=self._on_edit, state="disabled")
        self._btn_edit.grid(row=0, column=1, padx=6)

        self._btn_delete = ctk.CTkButton(bottom, text="🗑 Delete", width=80,
                                         fg_color="#c0392b", hover_color="#96281b",
                                         command=self._on_delete, state="disabled")
        self._btn_delete.grid(row=0, column=2, padx=6, sticky="w")

        self._sync_label = ctk.CTkLabel(bottom, text="", text_color="gray",
                                        font=ctk.CTkFont(size=11))
        self._sync_label.grid(row=0, column=3, padx=(12, 0), sticky="e")

    def _refresh_list(self):
        from textforge.storage import load_snippets
        self._all_snippets = load_snippets()
        self._apply_filter()

    def _apply_filter(self):
        query = self._search_var.get().lower().strip()
        if query:
            self._filtered_snippets = [
                s for s in self._all_snippets
                if query in s["shortcut"].lower() or query in s["expansion"].lower()
            ]
        else:
            self._filtered_snippets = list(self._all_snippets)
        self._selected_idx = None
        self._render_rows()

    def _render_rows(self):
        for frame in self._row_frames:
            frame.destroy()
        self._row_frames = []
        self._update_buttons()

        for idx, snippet in enumerate(self._filtered_snippets):
            row = ctk.CTkFrame(self._scroll_frame, fg_color="transparent", cursor="hand2")
            row.grid(row=idx, column=0, columnspan=2, sticky="ew", pady=1)
            row.grid_columnconfigure(0, weight=1)
            row.grid_columnconfigure(1, weight=3)

            lbl_sc = ctk.CTkLabel(row, text=snippet["shortcut"],
                                  font=ctk.CTkFont(family="Courier New", size=13),
                                  anchor="w")
            lbl_sc.grid(row=0, column=0, sticky="w", padx=8, pady=4)

            lbl_exp = ctk.CTkLabel(row, text=snippet["expansion"],
                                   anchor="w", wraplength=380)
            lbl_exp.grid(row=0, column=1, sticky="w", padx=8, pady=4)

            for widget in (row, lbl_sc, lbl_exp):
                widget.bind("<Button-1>", lambda e, i=idx: self._on_row_click(i))
                widget.bind("<Double-Button-1>", lambda e, i=idx: self._on_row_double_click(i))

            self._row_frames.append(row)

    def _on_row_click(self, idx: int):
        self._selected_idx = idx
        self._highlight_row(idx)
        self._update_buttons()

    def _on_row_double_click(self, idx: int):
        self._selected_idx = idx
        self._on_edit()

    def _highlight_row(self, selected_idx: int):
        for i, frame in enumerate(self._row_frames):
            color = "#2a5caa" if i == selected_idx else "transparent"
            frame.configure(fg_color=color)

    def _update_buttons(self):
        state = "normal" if self._selected_idx is not None else "disabled"
        self._btn_edit.configure(state=state)
        self._btn_delete.configure(state=state)

    def _on_search_change(self):
        self._apply_filter()

    def _on_add(self):
        from .snippet_dialog import SnippetDialog
        dialog = SnippetDialog(self, mode="add", on_save=self._after_save)
        dialog.grab_set()
        self.wait_window(dialog)

    def _on_edit(self):
        if self._selected_idx is None:
            return
        snippet = self._filtered_snippets[self._selected_idx]
        from .snippet_dialog import SnippetDialog
        dialog = SnippetDialog(self, mode="edit", snippet=snippet, on_save=self._after_save)
        dialog.grab_set()
        self.wait_window(dialog)

    def _on_delete(self):
        if self._selected_idx is None:
            return
        snippet = self._filtered_snippets[self._selected_idx]
        confirm = ctk.CTkToplevel(self)
        confirm.title("Confirm Delete")
        confirm.geometry("360x140")
        confirm.resizable(False, False)
        confirm.grab_set()

        ctk.CTkLabel(
            confirm,
            text=f'Delete shortcut "{snippet["shortcut"]}"?',
            wraplength=320,
        ).pack(pady=20)

        btn_row = ctk.CTkFrame(confirm, fg_color="transparent")
        btn_row.pack()

        def do_delete():
            from textforge.storage import delete_snippet
            delete_snippet(snippet["id"])
            self._notify_hook_and_sync()
            self._refresh_list()
            confirm.destroy()

        ctk.CTkButton(btn_row, text="Cancel", width=100, fg_color="gray",
                      command=confirm.destroy).pack(side="left", padx=8)
        ctk.CTkButton(btn_row, text="Delete", width=100, fg_color="#c0392b",
                      hover_color="#96281b", command=do_delete).pack(side="left", padx=8)

        self.wait_window(confirm)

    def _after_save(self):
        self._notify_hook_and_sync()
        self._refresh_list()

    def _notify_hook_and_sync(self):
        hook = getattr(self._app, "keyboard_hook", None)
        if hook:
            hook.reload_shortcuts()
        creds = getattr(self._app, "credentials", None)
        if creds:
            threading.Thread(
                target=lambda: self._sync_and_update_label(creds), daemon=True
            ).start()

    def _sync_and_update_label(self, creds):
        from textforge.drive_sync import sync_to_drive
        ok = sync_to_drive(creds)
        ts = datetime.now().strftime("%I:%M %p").lstrip("0")
        label = f"Synced ✓ {ts}" if ok else "Offline"
        self.after(0, lambda: self._sync_label.configure(text=label))

    def set_sync_status(self, text: str):
        """Thread-safe — call via after(0, ...) from non-tk threads."""
        self._sync_label.configure(text=text)

    def show(self):
        """Show and focus the window. Safe to call from main tk thread."""
        self._refresh_list()
        self.deiconify()
        self.lift()
        self.focus_force()

    def _on_close(self):
        """Hide instead of destroy so the agent stays alive in the tray."""
        self.withdraw()

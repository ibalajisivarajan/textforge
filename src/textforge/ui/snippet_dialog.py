import logging
from typing import Callable

import customtkinter as ctk

log = logging.getLogger(__name__)


class SnippetDialog(ctk.CTkToplevel):
    """
    Modal dialog for adding or editing a snippet.
    mode: "add" | "edit"
    snippet: existing snippet dict (required for "edit")
    on_save: callback invoked after successful save (no arguments)
    """

    def __init__(
        self,
        parent,
        mode: str = "add",
        snippet: dict | None = None,
        on_save: Callable | None = None,
    ):
        super().__init__(parent)
        self._mode = mode
        self._snippet = snippet
        self._on_save = on_save

        title = "Add Snippet" if mode == "add" else "Edit Snippet"
        self.title(title)

        # Hide while building so the user never sees an unsized window.
        self.withdraw()

        self.resizable(True, True)
        self.minsize(450, 350)

        self._build_ui()

        if mode == "edit" and snippet:
            self._shortcut_var.set(snippet["shortcut"])
            self._expansion_text.insert("1.0", snippet["expansion"])

        # Let CustomTkinter and the OS finish geometry calculations before
        # measuring the window — avoids the cut-off-buttons problem on HiDPI.
        self.update_idletasks()
        self._center()
        self.deiconify()
        self.grab_set()
        self._shortcut_entry.focus()

    def _center(self):
        """Center the dialog over the screen using post-layout dimensions."""
        w = self.winfo_reqwidth()
        h = self.winfo_reqheight()
        # Respect minsize floor.
        w = max(w, 450)
        h = max(h, 350)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        x = (sw - w) // 2
        y = (sh - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)  # expansion textbox stretches

        ctk.CTkLabel(self, text="Shortcut", anchor="w").grid(
            row=0, column=0, padx=20, pady=(20, 2), sticky="w"
        )
        self._shortcut_var = ctk.StringVar()
        self._shortcut_entry = ctk.CTkEntry(
            self, textvariable=self._shortcut_var, height=34
        )
        self._shortcut_entry.grid(row=1, column=0, padx=20, pady=(0, 8), sticky="ew")

        ctk.CTkLabel(self, text="Expansion", anchor="w").grid(
            row=2, column=0, padx=20, pady=(4, 2), sticky="w"
        )
        self._expansion_text = ctk.CTkTextbox(self, height=90)
        self._expansion_text.grid(row=3, column=0, padx=20, pady=(0, 4), sticky="nsew")

        self._error_label = ctk.CTkLabel(
            self, text="", text_color="#e74c3c", font=ctk.CTkFont(size=11)
        )
        self._error_label.grid(row=4, column=0, padx=20, pady=(2, 0), sticky="w")

        btn_row = ctk.CTkFrame(self, fg_color="transparent")
        btn_row.grid(row=5, column=0, padx=20, pady=(10, 20), sticky="ew")
        btn_row.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(
            btn_row, text="Cancel", width=100, fg_color="gray", command=self.destroy
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkButton(
            btn_row, text="Save", width=100, command=self._on_save_click
        ).grid(row=0, column=1, sticky="e")

    def _on_save_click(self):
        shortcut = self._shortcut_var.get().strip().lower()
        expansion = self._expansion_text.get("1.0", "end").rstrip("\n")

        if not shortcut:
            self._show_error("Shortcut is required.")
            return
        if " " in shortcut:
            self._show_error("Shortcut must not contain spaces.")
            return
        if len(shortcut) > 20:
            self._show_error("Shortcut must be 20 characters or fewer.")
            return
        if not expansion:
            self._show_error("Expansion is required.")
            return
        if len(expansion) > 500:
            self._show_error("Expansion must be 500 characters or fewer.")
            return

        from textforge.storage import add_snippet, update_snippet, load_snippets

        # Duplicate check — block if another snippet already owns this shortcut.
        existing = {s["shortcut"]: s["id"] for s in load_snippets()}
        own_id = self._snippet["id"] if self._snippet else None
        if shortcut in existing and existing[shortcut] != own_id:
            self._show_error(f'Shortcut "{shortcut}" is already used. Choose another.')
            return

        if self._mode == "add":
            add_snippet(shortcut, expansion)
        else:
            update_snippet(self._snippet["id"], shortcut, expansion)

        if self._on_save:
            self._on_save()
        self.destroy()

    def _show_error(self, msg: str):
        self._error_label.configure(text=msg)

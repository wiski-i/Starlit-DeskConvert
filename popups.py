"""Themed format picker and confirmation dialogs."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk

from i18n import tr
from theme import ACCENT, ACCENT_H, ACCENT_HOVER, BG, BORDER_H, PANEL, SUB, SURFACE, SURFACE_H, TEXT, font


class FormatPicker(ctk.CTkFrame):
    def __init__(self, parent, command):
        super().__init__(parent, fg_color=SURFACE, corner_radius=11)
        self.command = command
        self.values = ["—"]
        self.selected = "—"
        self.state = "normal"
        self._popup = None
        self._button = ctk.CTkButton(
            self, text="—", command=self._open, height=40, anchor="w", corner_radius=11,
            fg_color=SURFACE, hover_color=SURFACE_H, text_color=TEXT, font=font(14, "bold"),
        )
        self._button.pack(side="left", fill="x", expand=True)
        self._arrow = ctk.CTkButton(
            self, text="⌄", command=self._open, width=40, height=40, corner_radius=10,
            fg_color=ACCENT, hover_color=ACCENT_HOVER, font=font(18, "bold"),
        )
        self._arrow.pack(side="right")
        tk.Frame.configure(self, takefocus=1)
        tk.Frame.bind(self, "<Return>", lambda _event: self._open(), add="+")
        tk.Frame.bind(self, "<space>", lambda _event: self._open(), add="+")
        tk.Frame.bind(self, "<FocusIn>", lambda _event: self._button.configure(border_width=1, border_color=ACCENT_H))
        tk.Frame.bind(self, "<FocusOut>", lambda _event: self._button.configure(border_width=0))

    def configure(self, *, values=None, state=None, **kwargs):
        super().configure(**kwargs)
        if values is not None:
            self.values = values
        if state is not None:
            self.state = state
            self._button.configure(state=state)
            self._arrow.configure(state=state)
            if state == "disabled":
                self._dismiss()

    def get(self):
        return self.selected

    def set(self, value):
        self.selected = value
        self._button.configure(text=f"  {value}")

    def _open(self):
        if self.state == "disabled":
            return
        if self._popup:
            self._dismiss()
            return
        popup = ctk.CTkToplevel(self)
        self._popup = popup
        popup.withdraw()
        popup.overrideredirect(True)
        popup.configure(fg_color=BG)
        popup.transient(self.winfo_toplevel())
        shell = ctk.CTkFrame(popup, fg_color=PANEL, border_color=BORDER_H, border_width=1, corner_radius=11)
        shell.pack(fill="both", expand=True)
        items = tk.Listbox(
            shell, height=min(11, len(self.values)), bg=PANEL, fg=TEXT,
            selectbackground=SURFACE_H, selectforeground=TEXT, activestyle="none",
            relief="flat", highlightthickness=0, exportselection=False, font=("Segoe UI", 11),
        )
        if len(self.values) > 11:
            bar = ctk.CTkScrollbar(shell, command=items.yview)
            bar.pack(side="right", fill="y", pady=6)
            items.configure(yscrollcommand=bar.set)
        items.pack(fill="both", expand=True, padx=6, pady=6)
        items.insert("end", *self.values)
        selected = self.values.index(self.selected) if self.selected in self.values else 0
        items.selection_set(selected)
        items.activate(selected)
        items.see(selected)

        def choose(_event=None):
            choice = items.curselection()
            if choice:
                self._choose(self.values[choice[0]])
            return "break"

        items.bind("<ButtonRelease-1>", choose)
        items.bind("<Return>", choose)
        popup.update_idletasks()
        x = self.winfo_rootx()
        y = self.winfo_rooty() + self.winfo_height() + 5
        height = popup.winfo_reqheight()
        if y + height > self.winfo_screenheight() - 40:
            y = self.winfo_rooty() - height - 5
        # The anchor and requested size are already measured in screen pixels.
        tk.Wm.geometry(popup, f"{self.winfo_width()}x{height}{x:+d}{y:+d}")
        popup.bind("<Escape>", lambda _event: self._dismiss())
        popup.bind("<Button-1>", self._outside_click, add="+")
        popup.deiconify()
        popup.wait_visibility()
        popup.grab_set()
        items.focus_set()

    def _outside_click(self, event):
        popup = self._popup
        if popup and not (
            popup.winfo_rootx() <= event.x_root < popup.winfo_rootx() + popup.winfo_width()
            and popup.winfo_rooty() <= event.y_root < popup.winfo_rooty() + popup.winfo_height()
        ):
            self._dismiss()

    def _choose(self, value):
        self.set(value)
        self._dismiss()
        self.command(value)

    def _dismiss(self):
        if self._popup:
            self._popup.destroy()
            self._popup = None
            self.focus_set()


def show_dialog(parent, title: str, message: str, *, confirm: bool = False) -> bool:
    """Show an app-themed notice or a confirmation with a safe keyboard default."""
    dialog = ctk.CTkToplevel(parent)
    dialog.withdraw()
    dialog.overrideredirect(True)
    dialog.configure(fg_color=BG)
    dialog.transient(parent)
    card = ctk.CTkFrame(dialog, fg_color=PANEL, border_width=1, border_color=BORDER_H, corner_radius=19)
    card.pack(fill="both", expand=True)
    ctk.CTkLabel(card, text=title, font=font(19, "bold"), text_color=TEXT, anchor="w").pack(
        fill="x", padx=23, pady=(18, 5)
    )
    ctk.CTkLabel(
        card, text=message, font=font(13), text_color=SUB, anchor="w",
        justify="left", wraplength=365,
    ).pack(fill="x", padx=23, pady=(0, 16))
    bar = ctk.CTkFrame(card, fg_color="transparent")
    bar.pack(fill="x", padx=21, pady=(0, 18))
    accepted = False

    def close(answer=False):
        nonlocal accepted
        accepted = answer
        dialog.destroy()

    ctk.CTkButton(
        bar, text=tr("Convert") if confirm else tr("OK"), command=lambda: close(True),
        height=38, fg_color=ACCENT, hover_color=ACCENT_HOVER, font=font(13, "bold"),
    ).pack(side="right")
    if confirm:
        ctk.CTkButton(
            bar, text=tr("Cancel"), command=close, height=38, width=98,
            fg_color=SURFACE, hover_color=SURFACE_H, font=font(13),
        ).pack(side="right", padx=(0, 8))
    dialog.update_idletasks()
    width, height = 414, dialog.winfo_reqheight()
    x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
    dialog.geometry(f"{width}x{height}{x:+d}{y:+d}")
    dialog.bind("<Escape>", lambda _event: close())
    dialog.bind("<Return>", lambda _event: close(not confirm))
    dialog.protocol("WM_DELETE_WINDOW", close)
    dialog.deiconify()
    dialog.wait_visibility()
    dialog.grab_set()
    dialog.focus_force()
    parent.wait_window(dialog)
    return accepted

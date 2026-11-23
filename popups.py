"""Themed format picker and confirmation dialogs."""

from __future__ import annotations

import tkinter as tk

import customtkinter as ctk
from PIL import Image, ImageDraw

from i18n import tr
from theme import ACCENT, ACCENT_2, ACCENT_H, ACCENT_HOVER, BG, BORDER_H, PANEL, SUB, SURFACE, SURFACE_H, TEXT, font


def _chevron(px: int) -> ctk.CTkImage:
    """White down chevron; the "⌄" glyph sits below the button's center in Segoe UI."""
    scale = 4
    image = Image.new("RGBA", (px * scale, px * scale), (0, 0, 0, 0))
    unit = px * scale / 24
    points = [(6 * unit, 9 * unit), (12 * unit, 15 * unit), (18 * unit, 9 * unit)]
    ImageDraw.Draw(image).line(points, fill="#FFFFFF", width=max(2, round(2 * unit)), joint="curve")
    image = image.resize((px, px), Image.LANCZOS)
    return ctk.CTkImage(light_image=image, dark_image=image, size=(px, px))


class FormatPicker(ctk.CTkComboBox):
    def __init__(self, parent, command, *, height=40, text_font=None):
        self._arrow_icon = _chevron(max(12, height // 2))
        super().__init__(
            parent, width=140, height=height, corner_radius=8, border_width=1,
            fg_color=SURFACE, border_color=BORDER_H, button_color=ACCENT,
            button_hover_color=ACCENT_HOVER, text_color=TEXT, text_color_disabled=SUB,
            font=text_font or font(14, "bold"), values=["—"], state="readonly",
        )
        self.command = command
        self.values = ["—"]
        self.state = "normal"
        self._popup = None
        self._previous_grab = None
        self.set("—")
        # The combobox paints its field, border and arrow on one canvas.
        self._entry.configure(cursor="hand2", takefocus=1)
        for sequence in ("<Button-1>", "<Return>", "<space>"):
            self._entry.bind(sequence, lambda _event: self._open() or "break")
        self._entry.bind("<FocusIn>", lambda _event: self.configure(border_color=ACCENT_H))
        self._entry.bind("<FocusOut>", lambda _event: self.configure(border_color=BORDER_H))

    def _draw(self, no_color_updates=False):
        super()._draw(no_color_updates)
        # Keep the centered vector chevron instead of the font-based glyph.
        self._canvas.itemconfigure("dropdown_arrow", state="hidden")
        self._arrow_photo = self._arrow_icon.create_scaled_photo_image(
            self._get_widget_scaling(), self._get_appearance_mode(),
        )
        if not self._canvas.find_withtag("picker_chevron"):
            self._canvas.create_image(0, 0, image=self._arrow_photo, tags="picker_chevron")
        self._canvas.itemconfigure("picker_chevron", image=self._arrow_photo)
        self._canvas.coords(
            "picker_chevron", self._apply_widget_scaling(self._current_width - self._current_height / 2),
            self._apply_widget_scaling(self._current_height / 2),
        )

    def configure(self, *, values=None, state=None, **kwargs):
        if values is not None:
            self.values = list(values)
            kwargs["values"] = self.values
        if state is not None:
            self.state = state
            kwargs["state"] = "disabled" if state == "disabled" else "readonly"
        super().configure(**kwargs)
        if state == "disabled":
            self._dismiss()

    def _open_dropdown_menu(self):
        self._open()

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
        if popup.tk.call("tk", "windowingsystem") == "win32":
            # Hide the top-level rectangle outside the rounded shell.
            popup.attributes("-transparentcolor", BG)
        popup.transient(self.winfo_toplevel())
        shell = ctk.CTkFrame(popup, fg_color=PANEL, border_color=BORDER_H, border_width=1, corner_radius=11)
        shell.pack(fill="both", expand=True)
        items = tk.Listbox(
            shell, height=min(11, len(self.values)), bg=PANEL, fg=TEXT,
            selectbackground=SURFACE_H, selectforeground=TEXT, activestyle="none",
            relief="flat", borderwidth=0, highlightthickness=0, exportselection=False, font=("Segoe UI", 11),
        )
        if len(self.values) > 11:
            bar = ctk.CTkScrollbar(
                shell, command=items.yview, width=14, fg_color=PANEL,
                button_color=BORDER_H, button_hover_color=ACCENT_2,
            )
            bar.pack(side="right", fill="y", padx=(0, 6), pady=8)
            items.configure(yscrollcommand=bar.set)
        items.pack(fill="both", expand=True, padx=8, pady=8)
        items.insert("end", *self.values)
        selected = self.values.index(self.get()) if self.get() in self.values else 0
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
        # "+-1650" keeps a monitor left of the primary; "-1650" would mean "from the right edge".
        tk.Wm.geometry(popup, f"{self.winfo_width()}x{height}+{x}+{y}")
        popup.bind("<Escape>", lambda _event: self._dismiss())
        popup.bind("<Button-1>", self._outside_click, add="+")
        popup.deiconify()
        popup.wait_visibility()
        # A modal parent (the presets window) holds the grab; hand it back on dismiss.
        self._previous_grab = popup.grab_current()
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
            previous, self._previous_grab = self._previous_grab, None
            if previous is not None and previous.winfo_exists():
                previous.grab_set()
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

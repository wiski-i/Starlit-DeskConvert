"""Edit conversion presets with the existing DeskConvert desktop theme."""
from __future__ import annotations

import tkinter as tk
from dataclasses import replace
from uuid import uuid4

import customtkinter as ctk

from engine import presets
from i18n import tr
from popups import FormatPicker, show_dialog
from theme import (
    ACCENT, ACCENT_2, ACCENT_HOVER, BG, BORDER, BORDER_H, PANEL, SUB, SURFACE, SURFACE_H, TEXT, bind_window_frame, font,
)


class PresetWindow(ctk.CTkToplevel):
    def __init__(self, parent, items, preferences, on_save):
        super().__init__(parent)
        self.title(tr("Manage presets"))
        self.geometry("870x680")
        self.minsize(720, 560)
        self.configure(fg_color=BG)
        self.transient(parent)
        bind_window_frame(self)
        self.items = list(items)
        self.on_save = on_save
        self.current = None
        self.fields = {}
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)

        sidebar = ctk.CTkFrame(self, fg_color=PANEL, border_width=1, border_color=BORDER)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(18, 8), pady=(18, 8))
        ctk.CTkLabel(sidebar, text=tr("Presets"), font=font(17, "bold"), text_color=TEXT).pack(
            anchor="w", padx=12, pady=(12, 7),
        )
        list_frame = tk.Frame(sidebar, bg=PANEL)
        list_frame.pack(fill="both", expand=True, padx=10)
        self.list = tk.Listbox(
            list_frame, width=31, bg=SURFACE, fg=TEXT, selectbackground=ACCENT,
            selectforeground=TEXT, font=("Segoe UI", 10), relief="flat", activestyle="none",
            highlightthickness=1, highlightbackground=BORDER_H, highlightcolor=ACCENT_2, exportselection=False,
        )
        scrollbar = ctk.CTkScrollbar(
            list_frame, command=self.list.yview, width=14, fg_color=PANEL,
            button_color=BORDER_H, button_hover_color=ACCENT_2,
        )
        scrollbar.pack(side="right", fill="y")
        self.list.configure(yscrollcommand=scrollbar.set)
        self.list.pack(fill="both", expand=True)
        self.list.bind("<<ListboxSelect>>", self._selected)
        actions = ctk.CTkFrame(sidebar, fg_color="transparent")
        actions.pack(fill="x", padx=10, pady=8)
        actions.columnconfigure((0, 1, 2), weight=1, uniform="actions")
        for column, (title, command) in enumerate((
            ("New", lambda: self._new(False)), ("Duplicate", lambda: self._new(True)), ("Remove", self._remove),
        )):
            self._button(actions, title, command).grid(
                row=0, column=column, sticky="ew", padx=(0, 6 if column < 2 else 0),
            )
        order = ctk.CTkFrame(sidebar, fg_color="transparent")
        order.pack(fill="x", padx=10, pady=(0, 10))
        order.columnconfigure((0, 1), weight=1, uniform="order")
        self._button(order, "Move up", lambda: self._move(-1)).grid(row=0, column=0, sticky="ew", padx=(0, 6))
        self._button(order, "Move down", lambda: self._move(1)).grid(row=0, column=1, sticky="ew")

        editor = ctk.CTkScrollableFrame(
            self, fg_color=PANEL, border_width=1, border_color=BORDER,
            scrollbar_fg_color=PANEL, scrollbar_button_color=BORDER_H,
            scrollbar_button_hover_color=ACCENT_2,
        )
        editor.grid(row=0, column=1, sticky="nsew", padx=(8, 18), pady=(18, 8))
        editor.columnconfigure((0, 1), weight=1, uniform="fields")
        sections = [
            ("Name", "name", None), ("Menu group", "group", None),
            ("Output format", "target", presets.TARGETS), ("Input extensions", "inputs", None),
            ("Video quality (1–100)", "video_quality", None), ("Audio quality (1–100)", "audio_quality", None),
            ("Image quality (1–100)", "image_quality", None), ("Encoding speed", "speed", presets.SPEEDS),
            ("Scale (%)", "scale", None), ("Height limit (px)", "height", None),
            ("Width limit (px)", "width", None), ("Rotation (°)", "rotate", ("0", "-90", "90", "180")),
            ("Tempo (×)", "tempo", None), ("Pitch (semitones)", "pitch", None),
            ("Frame rate (fps)", "fps", None), ("H.264 encoder", "encoder", presets.ENCODERS),
            ("Audio channels (0 = source)", "channels", ("0", "1", "2", "6", "8")),
            ("Sample rate (Hz)", "sample_rate", ("0", "8000", "16000", "22050", "32000", "44100", "48000", "96000")),
            ("Audio bitrate (kbps)", "bitrate", None),
            ("Audio encoding", "audio_mode", ("", "mp3-vbr", "mp3-cbr", "wav-16", "wav-24", "wav-32", "wav-float")),
            ("Output path template", "template", None), ("After conversion", "action", presets.ACTIONS),
            ("Advanced FFmpeg options", "ffmpeg_options", None),
        ]
        for index, (title, key, choices) in enumerate(sections):
            row, column = divmod(index, 2)
            ctk.CTkLabel(editor, text=tr(title), text_color=SUB, font=font(12)).grid(
                row=row * 2, column=column, sticky="w", padx=8, pady=(7, 1),
            )
            variable = tk.StringVar(self)
            self.fields[key] = variable
            if choices is None:
                field = ctk.CTkEntry(
                    editor, textvariable=variable, width=1, height=32, corner_radius=8,
                    fg_color=SURFACE, border_color=BORDER_H, border_width=1,
                    text_color=TEXT, font=font(13),
                )
            else:
                field = self._picker(editor, choices, variable)
            field.grid(row=row * 2 + 1, column=column, sticky="ew", padx=8)

        checkbox_style = dict(
            fg_color=ACCENT, hover_color=ACCENT_HOVER, border_color=BORDER_H,
            checkmark_color=TEXT, text_color=TEXT, font=font(12),
            checkbox_width=22, checkbox_height=22, corner_radius=6,
        )
        self.switches = {}
        first_switch = 2 * ((len(sections) + 1) // 2)
        for index, (label, key) in enumerate((("Enabled", "enabled"),
                                               ("Include sound", "audio_enabled"),
                                               ("Power-of-two image size", "power_of_two"))):
            row, column = divmod(index, 2)
            variable = tk.BooleanVar(self)
            self.switches[key] = variable
            ctk.CTkCheckBox(editor, text=tr(label), variable=variable, **checkbox_style).grid(
                row=first_switch + row, column=column, sticky="w", padx=8, pady=8,
            )
        ctk.CTkLabel(
            editor, text=tr("Blank quality uses the encoder default. Zero leaves size and frame rate unchanged. "
                            "Example path template: (p)Converted/(f)"),
            text_color=SUB, wraplength=355, justify="left", anchor="w",
        ).grid(row=first_switch + 2, column=0, columnspan=2, sticky="ew", padx=8, pady=(0, 8))

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=1, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 14))
        self._button(footer, "Restore defaults", self._restore).pack(side="left")
        ctk.CTkButton(
            footer, text=tr("Save"), command=self._save, height=32, text_color=TEXT,
            font=font(13), fg_color=ACCENT, hover_color=ACCENT_HOVER,
        ).pack(side="right", padx=(6, 0))
        ctk.CTkButton(
            footer, text=tr("Cancel"), command=self.destroy, height=32, text_color=TEXT,
            font=font(13), fg_color=SURFACE, hover_color=SURFACE_H,
        ).pack(side="right")
        settings = ctk.CTkFrame(self, fg_color=PANEL, border_width=1, border_color=BORDER)
        settings.grid(row=1, column=0, columnspan=2, sticky="ew", padx=18, pady=(0, 8))
        settings.columnconfigure((0, 1), weight=1, uniform="settings")
        footer.grid_configure(row=2)
        parallel_row = ctk.CTkFrame(settings, fg_color="transparent")
        parallel_row.grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(10, 6))
        ctk.CTkLabel(parallel_row, text=tr("Simultaneous conversions"), text_color=SUB, font=font(12)).pack(
            side="left", padx=(0, 10),
        )
        self.parallel = tk.StringVar(self, value=str(preferences.parallel))
        parallel = self._picker(parallel_row, [str(n) for n in range(1, 9)], self.parallel)
        parallel.configure(width=76)
        parallel.pack(side="left")
        self.check_updates = tk.BooleanVar(self, value=preferences.check_updates)
        self.copy_outputs = tk.BooleanVar(self, value=preferences.copy_outputs)
        if parent.tk.call("tk", "windowingsystem") == "win32":
            ctk.CTkCheckBox(settings, text=tr("Copy converted files to clipboard"),
                            variable=self.copy_outputs, **checkbox_style).grid(
                row=1, column=0, sticky="w", padx=12, pady=(0, 10),
            )
        ctk.CTkCheckBox(settings, text=tr("Check GitHub updates at startup"),
                        variable=self.check_updates, **checkbox_style).grid(
            row=1, column=1, sticky="w", padx=12, pady=(0, 10),
        )
        self.bind("<Escape>", lambda _event: self.destroy())
        self._refresh(0)
        self.after_idle(self.grab_set)

    @staticmethod
    def _picker(parent, choices, variable):
        """Themed drop-down bound to a variable; CTkOptionMenu opens the light native menu."""
        picker = FormatPicker(parent, command=variable.set, height=32, text_font=font(13))
        picker.configure(values=list(choices))
        picker.set(variable.get())
        variable.trace_add("write", lambda *_args: picker.set(variable.get()))
        return picker

    def _button(self, parent, title, command):
        return ctk.CTkButton(
            parent, text=tr(title), command=command, width=64, height=32, corner_radius=8,
            fg_color=SURFACE, hover_color=SURFACE_H, text_color=TEXT, font=font(12),
        )

    def _refresh(self, index):
        self.list.delete(0, "end")
        for item in self.items:
            title = f"{item.menu_group} / {item.title}" if item.group else item.title
            self.list.insert("end", title if item.enabled else f"○  {title}")
        self.current = index if self.items else None
        item = self.items[index] if self.items else PresetPlaceholder
        if self.items:
            self.list.selection_set(index)
            self.list.see(index)
        for key, variable in self.fields.items():
            value = getattr(item, key)
            if key == "inputs":
                value = ", ".join(value)
            elif key == "name":
                value = item.title
            elif key == "group":
                value = item.menu_group
            variable.set("" if value is None else str(value))
        for key, variable in self.switches.items():
            variable.set(getattr(item, key))

    def _capture(self):
        if self.current is None:
            return True
        item = self.items[self.current]
        values = {key: variable.get().strip() for key, variable in self.fields.items()}
        try:
            for key in ("scale", "height", "width", "rotate", "fps", "channels", "sample_rate", "bitrate"):
                values[key] = int(values[key])
            for key in ("audio_quality", "video_quality", "image_quality"):
                values[key] = int(values[key]) if values[key] else None
            for key in ("tempo", "pitch"):
                values[key] = float(values[key].replace(",", "."))
            values["inputs"] = tuple(part.lstrip(".").lower() for part in values["inputs"].replace(",", " ").split())
            # Keep translation keys when the displayed stock name/group was left as-is.
            values["name"] = item.name if values["name"] == item.title else values["name"]
            values["group"] = item.group if values["group"] == item.menu_group else values["group"]
            values.update({key: variable.get() for key, variable in self.switches.items()})
            self.items[self.current] = replace(item, **values)
        except ValueError as error:
            show_dialog(self, tr("Manage presets"), str(error))
            return False
        return True

    def _selected(self, _event):
        selected = self.list.curselection()
        if not selected or selected[0] == self.current:
            return
        if self._capture():
            self._refresh(selected[0])
        else:
            self.list.selection_clear(0, "end")
            self.list.selection_set(self.current)

    def _move(self, delta):
        if self.current is None:
            return
        new_index = self.current + delta
        if 0 <= new_index < len(self.items) and self._capture():
            self.items.insert(new_index, self.items.pop(self.current))
            self._refresh(new_index)

    def _new(self, duplicate):
        if not self._capture():
            return
        identifier = uuid4().hex
        if duplicate and self.current is not None:
            item = self.items[self.current]
            item = replace(item, id=identifier, name=tr("{name} (copy)", name=item.title),
                           group=item.menu_group, builtin=False)
        else:
            item = presets.Preset(identifier, tr("New preset"), "mp4")
        self.items.append(item)
        self._refresh(len(self.items) - 1)

    def _remove(self):
        if self.current is not None:
            self.items.pop(self.current)
            self._refresh(max(0, min(self.current, len(self.items) - 1)))

    def _restore(self):
        if show_dialog(self, tr("Restore defaults"), tr("Replace the current preset list with the defaults?"), confirm=True):
            self.items = presets.defaults()
            self._refresh(0)

    def _save(self):
        if self._capture():
            try:
                self.on_save(self.items, presets.Preferences(
                    int(self.parallel.get()), self.copy_outputs.get(), self.check_updates.get(),
                ))
            except (ValueError, OSError) as error:
                show_dialog(self, tr("Manage presets"), str(error))
                return
            self.destroy()


PresetPlaceholder = presets.Preset("placeholder", "—", "mp4", enabled=False)

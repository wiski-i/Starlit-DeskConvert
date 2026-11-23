"""Desktop workspace for previewing and converting local files."""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import threading
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from queue import Empty, SimpleQueue

import customtkinter as ctk
from tkinter import filedialog
from PIL import Image, ImageDraw

import windows_shell
from engine import convert as engine
from engine import presets
from engine.converters import images, media
from i18n import LANGUAGES, Message, get_language, set_language, tr
from popups import FormatPicker, show_dialog
from preset_window import PresetWindow
from preview_window import PreviewWindow
from theme import (
    ACCENT, ACCENT_2, ACCENT_H, ACCENT_HOVER, BG, BORDER, BORDER_H,
    ERR, FAINT, MUTED, OK, PANEL, PANEL_2, SUB, SURFACE, SURFACE_H, TEXT, WARN,
    bind_window_frame, font,
)

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    _DND = True
except Exception:  # pragma: no cover
    _DND = False

ctk.set_appearance_mode("dark")

ASSETS = Path(__file__).with_name("assets")
COPY_LABEL = "Create a copy"
REPLACE_LABEL = "Replace original"

# kategori → (vurgu rengi, kısa ad).  İkon adı = kategori anahtarı.
CAT_COLORS = {
    "image": "#F472B6",
    "audio": "#34D399",
    "video": "#60A5FA",
    "document": "#FBBF24",
    "data": "#A78BFA",
    "archive": "#FB923C",
}


def human_size(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def short_text(text: str, limit: int = 45) -> str:
    if len(text) <= limit:
        return text
    return f"{text[:limit - 12]}…{text[-11:]}"


def thumbnail_board(source: Image.Image) -> Image.Image:
    """Composite transparent pixels onto a subtle checkerboard."""
    board = Image.new("RGBA", source.size, SURFACE)
    draw = ImageDraw.Draw(board)
    tile = 8
    for y in range(0, board.height, tile):
        for x in range((y // tile % 2) * tile, board.width, tile * 2):
            draw.rectangle((x, y, x + tile - 1, y + tile - 1), fill=BORDER)
    return Image.alpha_composite(board, source)


# ════════════════════════════════════════════════════════════════════════
#  VEKTÖR İKON FABRİKASI  (Lucide tarzı — Pillow ile çizilir, emoji yok)
# ════════════════════════════════════════════════════════════════════════
RES = 4          # süper-örnekleme katsayısı (keskinlik)
GRID = 24        # tasarım ızgarası (Lucide ile aynı)


def _draw(name: str, px: int, color: str) -> Image.Image:
    """24x24 ızgarada Lucide tarzı çizgi ikon → keskin RGBA görüntü."""
    c = px * RES
    s = c / GRID
    img = Image.new("RGBA", (c, c), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = max(2, round(2.0 * s))                 # çizgi kalınlığı

    def L(pts, width=w, fill=color):           # çoklu çizgi
        d.line([(x * s, y * s) for x, y in pts], fill=fill, width=width, joint="curve")

    def RR(box, r, width=w, fill=None, outline=color):
        d.rounded_rectangle([v * s for v in box], radius=r * s, outline=outline,
                            width=width, fill=fill)

    def EL(box, width=w, fill=None, outline=color):
        d.ellipse([v * s for v in box], outline=outline, width=width, fill=fill)

    def DOT(cx, cy, r, fill=color):
        d.ellipse([(cx - r) * s, (cy - r) * s, (cx + r) * s, (cy + r) * s], fill=fill)

    if name == "convert":                       # iki yönlü oklar (logo)
        L([(3, 8), (16, 8)]); L([(13, 5), (16, 8), (13, 11)])
        L([(21, 16), (8, 16)]); L([(11, 13), (8, 16), (11, 19)])
    elif name == "upload":
        L([(4, 16), (4, 20), (20, 20), (20, 16)])
        L([(12, 19), (12, 4)]); L([(7, 9), (12, 4), (17, 9)])
    elif name == "image":
        RR((3, 3, 21, 21), 4)
        DOT(9, 9, 1.6)
        L([(4, 18), (10, 12), (14, 16), (17, 13), (20, 16)])
    elif name == "audio":
        L([(9, 18), (9, 5), (20, 3), (20, 16)])
        EL((4, 16, 10, 21), fill=color); EL((15, 14, 21, 19), fill=color)
    elif name == "video":
        RR((2, 6, 15, 18), 3)
        L([(22, 8), (16, 12), (22, 16), (22, 8)])
    elif name == "document":
        L([(6, 3), (6, 21), (18, 21), (18, 8), (13, 3), (6, 3)])
        L([(13, 3), (13, 8), (18, 8)])
        L([(9, 13), (15, 13)]); L([(9, 17), (15, 17)])
    elif name == "data":                        # tablo / ızgara
        RR((3, 4, 21, 20), 3)
        L([(3, 10), (21, 10)]); L([(3, 15), (21, 15)]); L([(11, 4), (11, 20)])
    elif name == "archive":
        RR((3, 4, 21, 9), 1.5)
        L([(5, 9), (5, 20), (19, 20), (19, 9)])
        L([(10, 13), (14, 13)])
    elif name == "folder":
        L([(3, 8), (3, 19), (21, 19), (21, 9), (11, 9), (9, 6), (4, 6), (3, 8)])
    elif name == "x":
        L([(6, 6), (18, 18)]); L([(18, 6), (6, 18)])
    elif name == "arrow":
        L([(4, 12), (19, 12)]); L([(14, 7), (19, 12), (14, 17)])
    elif name == "check":
        L([(5, 13), (10, 18), (19, 6)])
    elif name == "chevron":
        L([(6, 9), (12, 15), (18, 9)])
    elif name == "warn":                         # üçgen + ünlem
        L([(12, 4), (21, 20), (3, 20), (12, 4)])
        L([(12, 10), (12, 15)]); DOT(12, 18, 1.0)
    elif name == "spark":                        # 4-uçlu yıldız (motor/AI)
        L([(12, 3), (14, 10), (21, 12), (14, 14), (12, 21), (10, 14),
           (3, 12), (10, 10), (12, 3)], width=max(2, round(1.6 * s)))
    elif name == "broom":                        # temizle
        L([(4, 20), (10, 14)]); L([(9, 9), (15, 15)])
        L([(13, 3), (21, 11)]); L([(10, 14), (4, 18), (6, 20), (10, 14)])
    return img.resize((px, px), Image.LANCZOS)


@lru_cache(maxsize=512)
def icon(name: str, px: int = 22, color: str = TEXT) -> ctk.CTkImage:
    im = _draw(name, px, color)
    return ctk.CTkImage(light_image=im, dark_image=im, size=(px, px))


@lru_cache(maxsize=16)
def gradient_badge(size: int, radius: int, c1: str, c2: str) -> ctk.CTkImage:
    """Draw the rounded brand mark as a single transparent image."""
    px = size * RES

    def rgb(h):
        h = h.lstrip("#")
        return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))

    a, b = rgb(c1), rgb(c2)
    grad = Image.new("RGB", (px, px))
    gd = grad.load()
    for y in range(px):
        for x in range(px):
            t = (x + y) / (2 * px)
            gd[x, y] = tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))
    mask = Image.new("L", (px, px), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, px - 1, px - 1],
                                           radius=radius * RES, fill=255)
    out = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    out.paste(grad, (0, 0), mask)
    out = out.resize((size, size), Image.LANCZOS)
    symbol_size = round(size * 0.52)
    offset = (size - symbol_size) // 2
    out.alpha_composite(_draw("convert", symbol_size, "#FFFFFF"), (offset, offset))
    return ctk.CTkImage(light_image=out, dark_image=out, size=(size, size))


# ──────────────────────────────────────────────────────────── kök pencere
if _DND:
    class _Root(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self, *a, **k):
            super().__init__(*a, **k)
            self.TkdndVersion = TkinterDnD._require(self)
else:
    _Root = ctk.CTk


def make_card(parent, hover=False, **kw):
    opts = dict(fg_color=PANEL, corner_radius=24, border_width=1, border_color=BORDER)
    opts.update(kw)
    card = ctk.CTkFrame(parent, **opts)
    if hover:
        base = opts["border_color"]
        card.bind("<Enter>", lambda _e: card.configure(border_color=BORDER_H))
        card.bind("<Leave>", lambda _e: card.configure(border_color=base))
    return card


def autohide_scrollbar(frame: ctk.CTkScrollableFrame) -> None:
    """Show the scrollbar only while the content is taller than its viewport."""
    canvas, bar = frame._parent_canvas, frame._scrollbar

    def sync(_event=None):
        if frame.winfo_reqheight() > canvas.winfo_height():
            bar.grid()
        else:
            bar.grid_remove()
            canvas.yview_moveto(0)

    frame.bind("<Configure>", sync, add="+")
    canvas.bind("<Configure>", sync, add="+")


class QuietProgress(ctk.CTkProgressBar):
    """CTk draws a rounded stub at 0%; hide it so an idle bar reads as empty."""

    def __init__(self, *args, progress_color, **kwargs):
        self._fill = progress_color
        super().__init__(*args, progress_color=progress_color, **kwargs)

    def set(self, value, from_variable_callback=False):
        super().set(value, from_variable_callback)
        self._sync_fill()

    def configure(self, require_redraw=False, **kwargs):
        super().configure(require_redraw=require_redraw, **kwargs)
        if "mode" in kwargs:
            self._sync_fill()

    def _sync_fill(self):
        visible = self.get() > 0 or self._mode == "indeterminate"
        super().configure(progress_color=self._fill if visible else self._fg_color)


# ════════════════════════════════════════════════════════════════════════
class App(_Root):
    def __init__(self, paths: list[str] | None = None):
        super().__init__()
        set_language(windows_shell.read_language())
        self.title("DeskConvert")
        self.geometry("980x750")
        self.minsize(820, 700)
        self.configure(fg_color=BG)
        bind_window_frame(self)
        if (ASSETS / "icon.ico").is_file() and sys.platform == "win32":
            self.after(250, self.iconbitmap, str(ASSETS / "icon.ico"))

        self.files: list[dict] = []
        self.primary_cat: str | None = None
        self.target_map: dict[str, dict] = {}
        self.out_dir: str | None = None
        self.busy = False
        self.preview_path: str | None = None
        self.preview_details = None
        self.previews: SimpleQueue = SimpleQueue()
        self.preview_pending: tuple[str, str] | None = None
        self.preview_active = False
        self.results: dict[str, tuple[str | None, str | Exception | None]] = {}
        self.queue_rows: dict[str, tuple[ctk.CTkFrame, ctk.CTkLabel]] = {}
        self.empty_queue = None
        self.stop_requested = threading.Event()
        self.localized_text = []
        self.preset_window = None
        self.presets_error = None
        try:
            self.presets = presets.load()
        except (OSError, ValueError, TypeError) as error:
            self.presets = []
            self.presets_error = error

        try:
            self.preferences = presets.load_preferences()
        except (OSError, ValueError, TypeError) as error:
            self.preferences = presets.Preferences()
            self.presets_error = error

        self._build()
        self.bind("<Control-o>", lambda _event: self.pick_files())
        self.bind("<Control-Return>", lambda _event: self.start_convert())
        self.bind("<F3>", lambda _event: self._open_preview(animate=False))
        self.protocol("WM_DELETE_WINDOW", self._close)
        self.after(60, self._poll_previews)
        if paths:
            self.add_files(paths)
        if not self.files:
            self._refresh()
        if sys.platform == "win32" and not paths and not self.presets_error:
            try:
                windows_shell.upgrade_classic_menu(self.presets)
                self._refresh_shell_button()
            except OSError:
                self.set_status(tr("Could not update the File Explorer context menu."), WARN)
        if self.preferences.check_updates and not paths:
            self.after(800, self._check_updates)

    # ───────────────────────────────────────── iskelet
    def _build(self):
        root = ctk.CTkFrame(self, fg_color="transparent")
        root.pack(fill="both", expand=True, padx=26, pady=22)
        root.columnconfigure(0, weight=1, uniform="main")
        root.columnconfigure(1, weight=1, uniform="main")
        root.rowconfigure(2, weight=1)

        self._header(root)
        self._drop(root)
        self._preview_panel(root)
        self._queue(root)
        self._targets_panel(root)
        self._action(root)

    def _localized(self, widget_type, parent, source, **options):
        widget = widget_type(parent, text=tr(source), **options)
        self.localized_text.append((widget, source))
        return widget

    # ───────────────────────────────────────── başlık
    def _header(self, root):
        head = ctk.CTkFrame(root, fg_color="transparent")
        head.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 16))
        head.columnconfigure(1, weight=1)

        try:
            with Image.open(ASSETS / "logo.png") as logo:
                brand = ctk.CTkImage(dark_image=logo.copy(), size=(54, 54))
        except OSError:
            brand = gradient_badge(54, 16, "#A74269", "#711B36")
        badge = ctk.CTkLabel(head, text="", image=brand)
        badge.grid(row=0, column=0, rowspan=2)
        ctk.CTkLabel(head, text="DeskConvert", font=font(27, "bold"),
                     text_color=TEXT, anchor="w").grid(row=0, column=1, sticky="sw", padx=(16, 0))
        self._localized(
            ctk.CTkLabel, head, "File converter · Images, video, audio, documents and archives",
            font=font(13), text_color=SUB, anchor="w",
        ).grid(
            row=1, column=1, sticky="nw", padx=(16, 0))

        self.language_picker = ctk.CTkSegmentedButton(
            head, values=list(LANGUAGES.values()), height=34, corner_radius=10,
            fg_color=PANEL_2, unselected_color=SURFACE, unselected_hover_color=SURFACE_H,
            selected_color=ACCENT, selected_hover_color=ACCENT_HOVER,
            text_color=TEXT, font=font(12, "bold"),
            command=lambda label: self.after_idle(self._change_language, label),
        )
        self.language_picker.set(LANGUAGES[get_language()])
        self.language_picker.grid(row=0, column=2, rowspan=2, sticky="e", padx=(10, 0))
        if sys.platform == "win32":
            self.shell_button = ctk.CTkButton(
                head, height=40, width=168, corner_radius=11, fg_color=SURFACE,
                hover_color=SURFACE_H, border_width=1, border_color=BORDER,
                image=icon("convert", 16, SUB),
                font=font(13, "bold"), command=self._toggle_shell_menu,
            )
            self.shell_button.grid(row=0, column=3, rowspan=2, sticky="e", padx=(10, 0))
            self._refresh_shell_button()

    def _change_language(self, label):
        previous_language = get_language()
        language = next(code for code, name in LANGUAGES.items() if name == label)
        if self.busy or language == previous_language:
            self.language_picker.set(LANGUAGES[previous_language])
            return
        try:
            windows_shell.save_language(language)
        except OSError:
            self.language_picker.set(LANGUAGES[previous_language])
            show_dialog(self, tr("Language"), tr("Could not save the language preference."))
            return

        save_method = REPLACE_LABEL if self.save_mode.get() == tr(REPLACE_LABEL) else COPY_LABEL
        selected = next((item for item in self.files if item["path"] == self.preview_path), None)
        set_language(language)
        self.language_picker.set(LANGUAGES[language])
        for widget, source in self.localized_text:
            widget.configure(text=tr(source))
        self.save_mode.configure(values=[tr(COPY_LABEL), tr(REPLACE_LABEL)])
        self.save_mode.set(tr(save_method))
        self._save_mode_changed(self.save_mode.get())
        if sys.platform == "win32":
            self._refresh_shell_button()
        self._show_preview(selected)
        self._refresh()

    # ───────────────────────────────────────── bırakma alanı
    def _drop(self, root):
        card = make_card(root, fg_color=PANEL_2, height=215)
        card.grid(row=1, column=0, sticky="nsew", padx=(0, 9), pady=(0, 9))
        self.drop_card = card

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        ring = ctk.CTkFrame(inner, fg_color=SURFACE, corner_radius=19, width=62, height=62,
                             border_width=1, border_color=BORDER_H)
        ring.pack(); ring.pack_propagate(False)
        self.drop_icon = ctk.CTkLabel(ring, text="", image=icon("upload", 29, ACCENT_H))
        self.drop_icon.place(relx=0.5, rely=0.5, anchor="center")

        hint = "Drop files here" if _DND else "Choose files to convert"
        self._localized(ctk.CTkLabel, inner, hint, font=font(16, "bold"), text_color=TEXT).pack(pady=(16, 3))
        self._localized(
            ctk.CTkButton, inner, "Choose files", image=icon("folder", 18, "#FFFFFF"),
            command=self.pick_files, fg_color=ACCENT, hover_color=ACCENT_HOVER,
            height=42, width=154, font=font(14, "bold"), corner_radius=12,
        ).pack(pady=(9, 0))

        if _DND:
            for wdg in (card, inner, ring, self.drop_icon):
                wdg.drop_target_register(DND_FILES)
                wdg.dnd_bind("<<Drop>>", self._on_drop)
                wdg.dnd_bind("<<DropEnter>>", self._drag_enter)
                wdg.dnd_bind("<<DropLeave>>", self._drag_leave)

    def _drag_enter(self, _):
        self.drop_card.configure(border_color=ACCENT_H, border_width=2, fg_color=SURFACE)
        return "copy"

    def _drag_leave(self, _):
        self.drop_card.configure(border_color=BORDER, border_width=1, fg_color=PANEL_2)

    def _preview_panel(self, root):
        card = make_card(root, height=215)
        card.grid(row=1, column=1, sticky="nsew", padx=(9, 0), pady=(0, 9))
        card.pack_propagate(False)
        heading = ctk.CTkFrame(card, fg_color="transparent")
        heading.pack(fill="x", padx=18, pady=(11, 5))
        self._localized(
            ctk.CTkLabel, heading, "Preview", font=font(15, "bold"), text_color=TEXT,
        ).pack(side="left")
        self.expand_preview = self._localized(
            ctk.CTkButton, heading, "Expand", width=70, height=27, corner_radius=8, fg_color=SURFACE,
            hover_color=SURFACE_H, text_color=TEXT, font=font(12), command=self._open_preview,
            state="disabled",
        )
        self.expand_preview.pack(side="right")
        well = ctk.CTkFrame(card, fg_color=PANEL_2, corner_radius=14, height=119)
        well.pack(fill="x", padx=16)
        well.pack_propagate(False)
        self.preview = ctk.CTkLabel(well, text="", image=icon("image", 31, MUTED))
        self.preview.place(relx=0.5, rely=0.5, anchor="center")
        for widget in (well, self.preview):
            widget.bind("<Button-1>", lambda _event: self._open_preview())
        self.preview_caption = ctk.CTkLabel(
            card, text=tr("Choose a file"), font=font(12), text_color=SUB, anchor="w"
        )
        self.preview_caption.pack(fill="x", padx=18, pady=(7, 0))

    def _open_preview(self, *, animate=True):
        if self.busy:
            return
        selected = next((f for f in self.files if f["path"] == self.preview_path), None)
        if selected and os.path.isfile(selected["path"]):
            PreviewWindow(self, selected["path"], selected["info"], animate=animate)

    # ───────────────────────────────────────── kuyruk
    def _queue(self, root):
        card = make_card(root)
        card.grid(row=2, column=0, sticky="nsew", padx=(0, 9), pady=9)
        card.rowconfigure(1, weight=1)
        card.columnconfigure(0, weight=1)

        bar = ctk.CTkFrame(card, fg_color="transparent")
        bar.grid(row=0, column=0, sticky="ew", padx=18, pady=(15, 6))
        bar.columnconfigure(0, weight=1)
        self.queue_title = ctk.CTkLabel(bar, text=tr("Queue"), font=font(15, "bold"),
                                        text_color=TEXT, anchor="w")
        self.queue_title.grid(row=0, column=0, sticky="w")
        self.clear_completed = self._localized(
            ctk.CTkButton, bar, "Clear completed", width=130, height=30,
            corner_radius=9, fg_color=SURFACE, hover_color=SURFACE_H,
            text_color=TEXT, font=font(12), state="disabled", command=self._clear_completed,
        )
        self.clear_completed.grid(row=0, column=1, padx=(6, 8))
        self._localized(
            ctk.CTkButton, bar, "Clear", image=icon("broom", 15, SUB), width=92, height=30,
            corner_radius=9, fg_color="transparent", border_width=1, border_color=BORDER,
            hover_color=SURFACE_H, text_color=SUB, font=font(12), command=self.clear_all,
        ).grid(row=0, column=2, sticky="e")

        self.list = ctk.CTkScrollableFrame(
            card, fg_color="transparent", corner_radius=0, height=145,
            scrollbar_button_color=SURFACE_H, scrollbar_button_hover_color=BORDER_H,
        )
        self.list.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 12))
        autohide_scrollbar(self.list)

    # ───────────────────────────────────────── hedef + akış
    def _targets_panel(self, root):
        card = make_card(root)
        card.grid(row=2, column=1, sticky="nsew", padx=(9, 0), pady=9)

        heading = ctk.CTkFrame(card, fg_color="transparent")
        heading.pack(fill="x", padx=18, pady=(12, 8))
        self._localized(
            ctk.CTkLabel, heading, "Target format", font=font(15, "bold"), text_color=TEXT,
        ).pack(side="left")
        self._localized(
            ctk.CTkButton, heading, "Manage presets", font=font(12), width=108, height=28,
            fg_color=SURFACE, hover_color=SURFACE_H, command=self._manage_presets,
        ).pack(side="right")

        flow = ctk.CTkFrame(card, fg_color="transparent")
        flow.pack(fill="x", padx=18)
        self.src_chip = ctk.CTkFrame(flow, fg_color=SURFACE, corner_radius=10, height=40, width=118)
        self.src_chip.pack(side="left"); self.src_chip.pack_propagate(False)
        self.src_icon = ctk.CTkLabel(self.src_chip, text="", image=icon("data", 18, FAINT))
        self.src_icon.pack(side="left", padx=(12, 6))
        self.src_lbl = ctk.CTkLabel(self.src_chip, text="—", font=font(13, "bold"), text_color=MUTED)
        self.src_lbl.pack(side="left")
        ctk.CTkLabel(flow, text="", image=icon("arrow", 20, ACCENT_2)).pack(side="left", padx=10)
        self.target = FormatPicker(flow, command=self._target_changed, arrow=icon("chevron", 18, "#FFFFFF"))
        self.target.pack(side="left", fill="x", expand=True)

        self.route_detail = ctk.CTkLabel(
            card, text=tr("Compatible formats appear here."), font=font(12),
            text_color=SUB, anchor="w", justify="left", height=44,
        )
        self.route_detail.pack(fill="x", padx=18, pady=(3, 4))
        card.bind("<Configure>", lambda e: self.route_detail.configure(
            wraplength=max(220, e.width - 42)
        ))

        self._localized(
            ctk.CTkLabel, card, "Save method", font=font(14, "bold"), text_color=TEXT,
        ).pack(anchor="w", padx=18)
        self.save_mode = ctk.CTkSegmentedButton(
            card, values=[tr(COPY_LABEL), tr(REPLACE_LABEL)], height=36, corner_radius=10,
            fg_color=PANEL_2, unselected_color=SURFACE, unselected_hover_color=SURFACE_H,
            selected_color=ACCENT, selected_hover_color=ACCENT_HOVER, text_color=TEXT,
            font=font(12, "bold"), command=self._save_mode_changed,
        )
        self.save_mode.set(tr(COPY_LABEL))
        self.save_mode.pack(fill="x", padx=18, pady=(5, 6))

        out = ctk.CTkFrame(card, fg_color="transparent")
        out.pack(fill="x", padx=18, pady=(0, 10))
        self.out_button = self._localized(
            ctk.CTkButton, out, "Choose folder", image=icon("folder", 15, TEXT), height=31, width=110,
            corner_radius=9, fg_color=SURFACE, hover_color=SURFACE_H, text_color=TEXT,
            font=font(12), command=self.pick_out,
        )
        self.out_button.pack(side="right")
        self.out_lbl = ctk.CTkLabel(out, text=tr("Same folder as the source"), font=font(12), text_color=SUB)
        self.out_lbl.pack(side="left", padx=(0, 5))

    # ───────────────────────────────────────── aksiyon
    def _action(self, root):
        card = make_card(root)
        card.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(5, 0))
        card.columnconfigure(0, weight=1)
        self.convert_btn = self._localized(
            ctk.CTkButton, card, "Convert", image=icon("convert", 19, "#FFFFFF"),
            command=self.start_convert, height=44, width=158, font=font(15, "bold"),
            corner_radius=12, fg_color=ACCENT, hover_color=ACCENT_HOVER, state="disabled",
        )
        self.convert_btn.grid(row=0, column=2, rowspan=2, padx=(0, 14), pady=11)
        self.output_action = ctk.CTkButton(
            card, text=tr("Show output"), height=40, width=144, corner_radius=10,
            fg_color=SURFACE, hover_color=SURFACE_H, font=font(12),
            state="disabled", command=self._use_output_action,
        )
        self.output_action.grid(row=0, column=1, rowspan=2, padx=11)
        self.progress = QuietProgress(card, height=5, corner_radius=4,
                                      progress_color=ACCENT_2, fg_color=SURFACE)
        self.progress.set(0)
        self.progress.grid(row=1, column=0, sticky="ew", padx=(17, 4), pady=(0, 12))
        self.status = ctk.CTkLabel(card, text=tr("Waiting for files…"), font=font(12),
                                   text_color=MUTED, anchor="w")
        self.status.grid(row=0, column=0, sticky="ew", padx=(17, 4), pady=(9, 1))

    def _check_updates(self):
        git = shutil.which("git")
        if not git or not (Path(__file__).parent / ".git").exists():
            return

        def check():
            environment = dict(os.environ, GIT_TERMINAL_PROMPT="0", GCM_INTERACTIVE="Never")
            options = dict(cwd=Path(__file__).parent, capture_output=True, text=True, timeout=8,
                           env=environment, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            try:
                local = subprocess.run([git, "rev-parse", "HEAD"], **options, check=True).stdout.strip()
                result = subprocess.run([git, "ls-remote", "origin", "HEAD"], **options)
                if result.returncode and (gh := shutil.which("gh")):
                    result = subprocess.run(
                        [gh, "api", "repos/wiski-i/Starlit-DeskConvert/commits/main", "--jq", ".sha"], **options,
                    )
                remote = result.stdout.split()
                # Only report an update if the remote head is not already in local history.
                if result.returncode == 0 and remote and remote[0] != local:
                    ancestor = subprocess.run([git, "merge-base", "--is-ancestor", remote[0], local], **options)
                    if ancestor.returncode != 0:
                        self.after(0, self._show_update)
            except (OSError, subprocess.SubprocessError, RuntimeError):
                return

        threading.Thread(target=check, daemon=True).start()

    def _show_update(self):
        if not self.busy:
            self.set_status(tr("A newer GitHub revision is available."), OK)

    def _manage_presets(self):
        if self.busy:
            return
        if self.preset_window and self.preset_window.winfo_exists():
            self.preset_window.focus()
            return
        if self.presets_error:
            show_dialog(self, tr("Manage presets"), tr("Could not read the preset file. {reason}", reason=self.presets_error))
            self.presets_error = None
        self.preset_window = PresetWindow(self, self.presets, self.preferences, self._save_presets)

    def _save_presets(self, items, preferences):
        presets.save(items)
        presets.save_preferences(preferences)
        self.presets = items
        self.preferences = preferences
        if sys.platform == "win32":
            windows_shell.refresh_presets(items)
        self._update_targets()

    def run_preset(self, identifier):
        preset = next((item for item in self.presets if item.id == identifier and item.enabled), None)
        if preset is None:
            show_dialog(self, tr("Manage presets"), tr("This preset is missing or disabled."))
            return
        jobs = [file for file in self.files if presets.target_for(preset, file["info"])]
        if not jobs:
            show_dialog(self, preset.title, tr("No compatible files"))
            return
        if len(jobs) < len(self.files):
            show_dialog(self, preset.title, tr("Some selected files cannot use this preset."))
            return
        self._begin_conversion(jobs, {"preset": preset, "label": preset.title}, preset.action, None)

    def _refresh_shell_button(self):
        try:
            location = windows_shell.menu_location()
        except OSError:
            location = None
        titles = {
            "main": tr("Main context menu enabled"),
            "classic": tr("Context menu enabled"),
            None: tr("Add to context menu"),
        }
        self.shell_button.configure(
            text=titles[location],
            image=icon("check" if location else "convert", 16, OK if location else SUB),
        )

    def _toggle_shell_menu(self):
        try:
            enabled = windows_shell.menu_enabled()
            windows_shell.set_menu_enabled(not enabled)
        except OSError as error:
            detail = tr(error) if error.args and isinstance(error.args[0], Message) else (
                tr("Could not update the File Explorer context menu.")
            )
            show_dialog(self, tr("File Explorer context menu"), detail)
            return
        self._refresh_shell_button()
        location = windows_shell.menu_location()
        if enabled:
            message = tr("Context menu command removed.")
        elif location == "main":
            message = tr("Main context menu → {command}", command=tr("Convert File"))
        else:
            message = tr("Show more options → {command}", command=tr("Convert File"))
        self.set_status(message, OK)

    def _on_drop(self, event):
        self._drag_leave(None)
        self.add_files(self.tk.splitlist(event.data))
        return "copy"

    def pick_files(self):
        if self.busy:
            return
        paths = filedialog.askopenfilenames(title=tr("Choose files to convert"))
        if paths:
            self.add_files(list(paths))

    def add_files(self, paths):
        if self.busy:
            return
        added = 0
        known = {os.path.normcase(file["path"]) for file in self.files}
        for p in paths:
            path = os.path.abspath(p)
            if os.path.isfile(path) and os.path.normcase(path) not in known:
                self.files.append({"path": path, "info": engine.analyze(path)})
                known.add(os.path.normcase(path))
                added += 1
        if added:
            self._refresh()

    def clear_all(self):
        if self.busy:
            return
        self.files.clear()
        self.results.clear()
        self.primary_cat = None
        self._refresh()
        self.progress.set(0)
        self.set_status(tr("Queue cleared."), MUTED)

    def _clear_completed(self):
        if self.busy:
            return
        completed = {path for path, (output, warning) in self.results.items() if output and warning is None}
        self.files[:] = [file for file in self.files if file["path"] not in completed]
        for path in completed:
            self.results.pop(path)
        self._refresh()

    def pick_out(self):
        if self.busy or self.save_mode.get() == tr(REPLACE_LABEL):
            return
        d = filedialog.askdirectory(title=tr("Choose an output folder"))
        if d:
            self.out_dir = d
            self._save_mode_changed(self.save_mode.get())

    def _save_mode_changed(self, mode):
        replace = mode == tr(REPLACE_LABEL)
        if replace and sys.platform != "win32":
            self.save_mode.set(tr(COPY_LABEL))
            return
        if replace:
            caption = tr("The original goes to the Recycle Bin")
        elif self.out_dir:
            caption = short_text(os.path.basename(self.out_dir) or self.out_dir, 29)
        else:
            caption = tr("Same folder as the source")
        self.out_lbl.configure(text=caption)
        self.out_button.configure(state="disabled" if replace or self.busy else "normal")

    # ───────────────────────────────────────── liste çizimi
    def _refresh(self):
        queue = tr("Queue")
        self.queue_title.configure(text=f"{queue} · {len(self.files)}" if self.files else queue)
        paths = {file["path"] for file in self.files}
        for path in self.queue_rows.keys() - paths:
            row, _detail = self.queue_rows.pop(path)
            row.destroy()

        selected = next((file for file in self.files if file["path"] == self.preview_path), None)
        if selected is None:
            selected = next(
                (file for file in self.files if file["info"].get("category")),
                self.files[0] if self.files else None,
            )
            self._show_preview(selected)

        if self.empty_queue is not None:
            self.empty_queue.destroy()
            self.empty_queue = None
        if not self.files:
            self.empty_queue = ctk.CTkFrame(self.list, fg_color="transparent")
            self.empty_queue.pack(expand=True, fill="both", pady=34)
            ctk.CTkLabel(self.empty_queue, text="", image=icon("upload", 40, FAINT)).pack()
            ctk.CTkLabel(self.empty_queue, text=tr("No files added yet"), font=font(13),
                         text_color=FAINT).pack(pady=(8, 0))
        for file in self.files:
            if file["path"] not in self.queue_rows:
                self._row(file)
            row, detail = self.queue_rows[file["path"]]
            row.configure(border_width=int(file is selected))
            self._refresh_row_detail(file, detail)
        self._update_targets()
        self._update_output_action()
        self.clear_completed.configure(
            state="normal" if any(output and warning is None for output, warning in self.results.values()) else "disabled",
        )

    def _row(self, f):
        info = f["info"]
        cat = info.get("category")
        color = CAT_COLORS.get(cat, FAINT)

        row = ctk.CTkFrame(
            self.list, fg_color=SURFACE, corner_radius=13,
            border_color=ACCENT_2,
        )
        row.pack(fill="x", pady=4, padx=4)
        row.bind("<Enter>", lambda _e, r=row: r.configure(fg_color=SURFACE_H))
        row.bind("<Leave>", lambda _e, r=row: r.configure(fg_color=SURFACE))

        ctk.CTkFrame(row, fg_color=color if cat else BORDER, width=4, height=42,
                     corner_radius=2).pack(side="left", padx=(8, 0), pady=8)
        chip = ctk.CTkFrame(row, fg_color=PANEL_2, corner_radius=10, width=44, height=44)
        chip.pack(side="left", padx=10, pady=8); chip.pack_propagate(False)
        ctk.CTkLabel(chip, text="", image=icon(cat or "x", 22, color)).place(
            relx=0.5, rely=0.5, anchor="center")

        mid = ctk.CTkFrame(row, fg_color="transparent")
        mid.pack(side="left", fill="x", expand=True, pady=6)
        name = ctk.CTkLabel(mid, text=short_text(info["name"], 35), anchor="w",
                            font=font(13, "bold"), text_color=TEXT)
        name.pack(fill="x")
        detail = ctk.CTkLabel(mid, text="", anchor="w", font=font(11))
        detail.pack(fill="x")
        for widget in (row, chip, mid, name, detail):
            widget.bind("<Button-1>", lambda _event, item=f: self._select_preview(item))

        ctk.CTkButton(row, text="", image=icon("x", 16, FAINT), width=32, height=32,
                      corner_radius=8, fg_color="transparent", hover_color="#2A1C24",
                      command=lambda: self._remove(f["path"])).pack(side="right", padx=8)
        self.queue_rows[f["path"]] = (row, detail)

    def _refresh_row_detail(self, file, detail):
        info = file["info"]
        cat = info.get("category")
        if cat:
            sub = (f"{tr(info['category_label'])}  ·  {(info['format'] or '?').upper()}"
                   f"  ·  {human_size(info['size'])}")
            sc = SUB
            if not info.get("engine_ok"):
                sub += f"  ·  {tr('Not available')}"
                sc = WARN
        else:
            sub, sc = tr("Unsupported format"), ERR
        result = self.results.get(file["path"])
        if result:
            output, warning = result
            if warning:
                sub, sc = short_text(tr(warning), 40), WARN if output else ERR
            elif output:
                sub, sc = short_text(os.path.basename(output), 25), OK
                try:
                    sub += f"  ·  {human_size(os.path.getsize(output))}"
                except OSError:
                    pass
        detail.configure(text=sub, text_color=sc)

    def _remove(self, path):
        if self.busy:
            return
        self.results.pop(path, None)
        self.files[:] = [file for file in self.files if file["path"] != path]
        self._refresh()

    def _select_preview(self, file):
        if not self.busy and self.preview_path != file["path"]:
            previous = self.queue_rows.get(self.preview_path)
            if previous:
                previous[0].configure(border_width=0)
            self._show_preview(file)
            self.queue_rows[file["path"]][0].configure(border_width=1)
            self._update_targets()
            self._update_output_action()

    def _show_preview(self, file):
        self.preview_path = file["path"] if file else None
        self.preview_details = None
        category = file["info"].get("category") if file else None
        caption = short_text(file["info"]["name"]) if file else tr("Choose a file")
        self.preview.configure(image=icon(category or "image", 31, MUTED))
        self.preview_caption.configure(text=caption)
        self.expand_preview.configure(state="normal" if file else "disabled")
        self.preview_pending = (
            (self.preview_path, category) if category in {"image", "video"} and file["info"]["engine_ok"] else None
        )
        self._start_pending_preview()

    def _start_pending_preview(self):
        if not self.preview_active and self.preview_pending:
            request, self.preview_pending = self.preview_pending, None
            self.preview_active = True
            threading.Thread(target=self._load_preview, args=request, daemon=True).start()

    def _load_preview(self, path, category):
        try:
            if category == "image":
                thumbnail, details = images.preview(path, (302, 107))
            else:
                with Image.open(BytesIO(media.preview(path, 310))) as frame:
                    details = None
                    frame.thumbnail((302, 107), Image.Resampling.LANCZOS)
                    thumbnail = frame.convert("RGBA")
            self.previews.put((path, thumbnail_board(thumbnail), details))
        except Exception:
            self.previews.put((path, None, None))

    def _poll_previews(self):
        while True:
            try:
                path, thumbnail, details = self.previews.get_nowait()
            except Empty:
                break
            self.preview_active = False
            if self.preview_pending and self.preview_pending[0] == path:
                self.preview_pending = None
            if path != self.preview_path or thumbnail is None:
                continue
            self.preview_details = details
            image = ctk.CTkImage(dark_image=thumbnail, size=thumbnail.size)
            self.preview.configure(image=image)
            if details:
                (width, height), frames, _depth = details
                caption = f"{short_text(os.path.basename(path), 29)}  ·  {width} × {height}"
                if frames > 1:
                    caption += f"  ·  {tr('{count} frames', count=frames)}"
                self.preview_caption.configure(text=caption)
            self._update_route_detail()
        self._start_pending_preview()
        self.after(60, self._poll_previews)

    def _update_targets(self):
        file = next((f for f in self.files if f["path"] == self.preview_path), None)
        info = file["info"] if file else {}
        if not info.get("targets") or not info.get("engine_ok"):
            self.primary_cat = None
            self.target_map = {}
            self.target.configure(values=["—"], state="disabled")
            self.target.set("—")
            self.src_lbl.configure(text="—", text_color=MUTED)
            self.src_icon.configure(image=icon("data", 18, FAINT))
            self.convert_btn.configure(state="disabled")
            self.route_detail.configure(text=tr("Compatible formats appear here."), text_color=SUB)
            self.set_status(info.get("engine_msg") or tr("Waiting for files…"), WARN if file else MUTED)
            return

        previous_category = self.primary_cat
        previous_target = self.target.get()
        self.primary_cat = info["category"]
        self.target_map = {t["label"]: t for t in info["targets"]}
        for item in self.presets:
            route = presets.target_for(item, info)
            if route:
                title = f"{item.menu_group} / {item.title}" if item.group else item.title
                label = tr("Preset · {name}", name=title)
                while label in self.target_map:
                    label += " ·"
                self.target_map[label] = {**route, "label": label}
        labels = list(self.target_map.keys())
        color = CAT_COLORS[self.primary_cat]
        self.src_icon.configure(image=icon(self.primary_cat, 18, color))
        self.src_lbl.configure(text=info["format"].upper(), text_color=TEXT)
        suggested = {"png": "WEBP", "mp4": "GIF"}.get(info["format"], labels[0])
        if previous_category == self.primary_cat and previous_target in labels:
            suggested = previous_target
        self.target.configure(values=labels, state="normal")
        self.target.set(suggested if suggested in labels else labels[0])
        self._target_changed(self.target.get())

    def _jobs_for(self, target):
        if preset := target.get("preset"):
            return [file for file in self.files if presets.target_for(preset, file["info"])]
        return [
            f for f in self.files
            if f["info"].get("category") == self.primary_cat and f["info"].get("engine_ok")
            and any(option["key"] == target["key"] for option in f["info"]["targets"])
        ]

    def _target_changed(self, label):
        target = self.target_map.get(label)
        if target is None:
            return
        jobs = self._jobs_for(target)
        count = len(jobs)
        ready = tr("{count} files ready", count=count) if count > 1 else tr("1 file ready")
        self.set_status(ready if jobs else tr("No compatible files"), SUB)
        self._update_route_detail()

    def _update_route_detail(self):
        target = self.target_map.get(self.target.get())
        if target is None:
            return
        key = target["key"]
        jobs = self._jobs_for(target)
        frames, depth = self.preview_details[1:] if self.preview_details else (1, None)
        blocked = self.primary_cat == "image" and key == "webp" and (
            (depth or 0) > 8 or (depth is not None and frames > 1)
        )
        color = SUB
        if preset := target.get("preset"):
            detail = tr("Output format · {format}", format=key.upper())
            if preset.action != "keep":
                detail += " · " + tr(f"Source action: {preset.action}")
        elif blocked and (depth or 0) > 8:
            detail, color = tr("WebP cannot preserve the color depth of a 16-bit PNG."), WARN
        elif blocked:
            detail, color = tr("Lossless WebP conversion does not support animated PNGs."), WARN
        elif self.primary_cat == "image" and frames > 1:
            detail, color = tr("Only the first frame or page is included."), WARN
        elif key == "webp" and jobs and all(f["info"]["format"] == "png" for f in jobs):
            detail, color = tr("Lossless WebP · Verifies 8-bit pixels and transparency."), OK
        elif self.primary_cat == "video" and key == "gif":
            detail, color = tr("No audio · 256 colors · 12 fps · Up to 480 px wide."), WARN
        elif self.primary_cat == "video" and key in media.AUDIO_OUTPUTS:
            detail, color = tr("Only the audio track is included."), WARN
        elif self.primary_cat == "video" and key in {"mp4", "mkv", "mov", "webm"}:
            detail = tr("Compatible streams are copied without re-encoding.")
        elif self.primary_cat == "image" and key == "jpg":
            detail, color = tr("JPEG is lossy. Transparent areas get a white background."), WARN
        elif self.primary_cat == "image" and key == "webp":
            detail = tr("PNG inputs use lossless encoding. Other images use high quality.")
        else:
            detail = tr("Output format · {format}", format=target["label"])
        self.route_detail.configure(text=detail, text_color=color)
        self.convert_btn.configure(state="normal" if jobs and not self.busy and not blocked else "disabled")

    def start_convert(self):
        if self.busy or self.convert_btn.cget("state") == "disabled":
            return
        target = self.target_map.get(self.target.get())
        if not target:
            return
        jobs = self._jobs_for(target)
        if not jobs:
            return
        preset = target.get("preset")
        action = "recycle" if self.save_mode.get() == tr(REPLACE_LABEL) else preset.action if preset else "keep"
        self._begin_conversion(jobs, target, action, self.out_dir)

    def _begin_conversion(self, jobs, target, action, out_dir):
        if self.busy:
            return
        if action == "delete" and not show_dialog(
            self, tr("Permanently delete originals"),
            tr("Permanently delete {count} original file(s) after verifying the outputs?", count=len(jobs)),
            confirm=True,
        ):
            return
        if action == "recycle" and not show_dialog(
            self,
            tr(REPLACE_LABEL),
            tr(
                "Convert {count} file(s)? After the output is verified, the original goes to the Recycle Bin.",
                count=len(jobs),
            ),
            confirm=True,
        ):
            return
        self.busy = True
        self.stop_requested.clear()
        self.target.configure(state="disabled")
        self.save_mode.configure(state="disabled")
        self.language_picker.configure(state="disabled")
        self.out_button.configure(state="disabled")
        self.clear_completed.configure(state="disabled")
        self.convert_btn.configure(state="disabled", text=tr("Converting…"))
        self.output_action.configure(
            text=tr("Stop after active files") if len(jobs) > 1 else tr("Show output"),
            state="normal" if len(jobs) > 1 else "disabled",
        )
        self.progress.set(0)
        if len(jobs) == 1:
            self.progress.configure(mode="indeterminate")
            self.progress.start()
        threading.Thread(
            target=self._worker, args=(jobs, target, action, out_dir), daemon=True,
        ).start()

    def _worker(self, jobs, target, action, out_dir):
        total = len(jobs)
        results = {}
        all_outputs = []
        queue = iter(jobs)
        # Office uses application-wide settings during export, so keep that batch serial.
        serial = any(
            (presets.target_for(target["preset"], file["info"]) if "preset" in target else target)
            .get("engine") == "pages" and file["info"]["format"] != "pdf"
            for file in jobs
        )
        workers = 1 if serial else min(self.preferences.parallel, total)
        with ThreadPoolExecutor(max_workers=workers) as pool:
            pending = {}
            while pending or not self.stop_requested.is_set():
                while len(pending) < workers and not self.stop_requested.is_set():
                    file = next(queue, None)
                    if file is None:
                        break
                    name = short_text(file["info"]["name"], 28)
                    count = len(results) + len(pending) + 1
                    self.after(0, self._working_on, f"{count}/{total}  ·  {name} → {target['label']}")
                    task = pool.submit(self._convert_one, file, target, action, out_dir)
                    pending[task] = file["path"]
                if not pending:
                    break
                completed, _ = wait(pending, return_when=FIRST_COMPLETED)
                for task in completed:
                    source = pending.pop(task)
                    try:
                        result, outputs = task.result()
                        results[source] = result
                        all_outputs.extend(outputs)
                    except Exception as error:
                        results[source] = (None, error)
                if total > 1:
                    self.after(0, self.progress.set, len(results) / total)
        self.after(0, self._finish, results, total, all_outputs)

    def _convert_one(self, file, target, action, out_dir):
        source, info = file["path"], file["info"]
        route = presets.target_for(target["preset"], info) if "preset" in target else target
        outputs = []
        warning = None
        if action != "keep":
            remove = {"recycle": windows_shell.recycle, "archive": engine.archive_source, "delete": os.unlink}
            output, warning = engine.replace_source(
                source, info, route, remove[action], out_dir, outputs_out=outputs,
            )
        else:
            output = engine.run(source, info, route, out_dir, verify="preset" in target, outputs_out=outputs)
        return (output, Message("Original kept. {reason}", reason=warning) if warning else None), outputs

    def _working_on(self, status):
        if not self.stop_requested.is_set():
            self.set_status(status, ACCENT_H)

    def _finish(self, results, total, all_outputs):
        self.busy = False
        self.progress.stop()
        self.progress.configure(mode="determinate")
        self.progress.set(len(results) / total)
        self.convert_btn.configure(text=tr("Convert"))
        self.save_mode.configure(state="normal")
        self.language_picker.configure(state="normal")
        self._save_mode_changed(self.save_mode.get())
        self.results.update(results)
        for file in self.files:
            source = file["path"]
            output, warning = results.get(source, (None, None))
            if output and not warning and not os.path.isfile(source):
                file["info"]["engine_ok"] = False
        self._refresh()
        outputs = [path for path, _warning in results.values() if path]
        warnings = [warning for _path, warning in results.values() if warning]
        if all_outputs and self.preferences.copy_outputs and sys.platform == "win32":
            try:
                windows_shell.copy_files(all_outputs, self.winfo_id())
            except (OSError, ImportError) as error:
                show_dialog(self, tr("Copy converted files to clipboard"), str(error))
        if len(results) < total:
            self.set_status(tr("Stopped · {done}/{total} files processed", done=len(results), total=total), WARN)
        elif len(results) == 1 and warnings:
            message = tr("Output saved. The original was kept.") if outputs else tr("Conversion could not be completed.")
            show_dialog(self, message, tr(warnings[0]))
            self.set_status(message, WARN if outputs else ERR)
        elif len(outputs) == 1 and not warnings:
            self.set_status(tr("Saved · {filename}", filename=short_text(os.path.basename(outputs[0]), 31)), OK)
        else:
            message = tr("{done}/{total} files converted", done=len(outputs), total=len(results))
            if warnings:
                count = len(warnings)
                warning = tr("{count} warnings", count=count) if count > 1 else tr("1 warning")
                message += f" · {warning}"
            self.set_status(message, WARN if warnings else OK)

    def _update_output_action(self):
        if self.busy:
            return
        output, warning = self.results.get(self.preview_path, (None, None))
        self.output_action.configure(
            text=tr("Show error") if warning and not output else tr("Show output"),
            state="normal" if warning or (output and sys.platform == "win32") else "disabled",
        )

    def _use_output_action(self):
        if self.busy:
            self.stop_requested.set()
            self.output_action.configure(text=tr("Stopping…"), state="disabled")
            self.set_status(tr("Finishing active files before stopping."), WARN)
            return
        output, warning = self.results.get(self.preview_path, (None, None))
        if output:
            if warning:
                show_dialog(self, tr("Output saved. The original was kept."), tr(warning))
            if sys.platform != "win32":
                return
            try:
                windows_shell.reveal_file(output)
            except OSError:
                show_dialog(self, tr("Show output"), tr("Could not locate the output file."))
        elif warning:
            show_dialog(self, tr("Conversion could not be completed."), tr(warning))

    def _close(self):
        if self.busy:
            self.set_status(tr("Wait for the conversion to finish before closing the window."), WARN)
        else:
            self.destroy()

    def set_status(self, text: str, color: str = MUTED):
        self.status.configure(text=tr(text), text_color=color)


def main():
    if sys.platform == "win32":
        import ctypes

        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("DosyaDonusturucu.Desktop")
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--preset")
    mode.add_argument("--configure-presets", action="store_true")
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args()
    app = App(args.paths)
    if args.preset:
        app.after_idle(app.run_preset, args.preset)
    elif args.configure_presets:
        app.after_idle(app._manage_presets)
    app.mainloop()


if __name__ == "__main__":
    main()

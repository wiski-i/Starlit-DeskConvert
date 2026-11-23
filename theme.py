"""Shared burgundy colors and native desktop typography."""

import ctypes
import sys
from ctypes import wintypes
from pathlib import Path

import customtkinter as ctk

TITLE_BAR = "#1F1F29"
BG = "#120E16"
PANEL = "#211823"
PANEL_2 = "#19121B"
SURFACE = "#30232E"
SURFACE_H = "#432C3D"
BORDER = "#493545"
BORDER_H = "#754B64"
ACCENT = "#88284B"
ACCENT_2 = "#C65B87"
ACCENT_H = "#ED9FBD"
ACCENT_HOVER = "#A73B63"
TEXT = "#FAEFF5"
SUB = "#D7BDCD"
MUTED = "#B59AAB"
FAINT = "#A68B9D"
OK = "#8DE2BC"
WARN = "#F0C07F"
ERR = "#FFA3AD"


def font(size: int = 13, weight: str = "normal") -> ctk.CTkFont:
    return ctk.CTkFont(family="Segoe UI", size=size, weight=weight)


def bind_window_frame(window: ctk.CTk | ctk.CTkToplevel) -> None:
    """Set the app icon and apply the palette when Tk maps the native frame."""
    if sys.platform != "win32":
        return

    icon = Path(__file__).with_name("assets") / "icon.ico"
    if icon.is_file():
        window.iconbitmap(str(icon))

    set_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
    set_attribute.argtypes = (wintypes.HWND, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD)
    border_color, caption_color, text_color = 34, 35, 36
    colors = ((border_color, BORDER), (caption_color, TITLE_BAR), (text_color, TEXT))

    def apply(event):
        if event.widget is not window or _high_contrast_enabled():
            return

        # Tk's outer frame owns the caption and may be recreated on remapping.
        frame = int(window.frame(), 0)
        dark_mode = 20  # DWMWA_USE_IMMERSIVE_DARK_MODE
        dark = wintypes.BOOL(True)
        if set_attribute(frame, dark_mode, ctypes.byref(dark), ctypes.sizeof(dark)):
            set_attribute(frame, 19, ctypes.byref(dark), ctypes.sizeof(dark))
        for attribute, color in colors:
            value = wintypes.DWORD(int.from_bytes(bytes.fromhex(color[1:]), "little"))
            set_attribute(frame, attribute, ctypes.byref(value), ctypes.sizeof(value))

    window.bind("<Map>", apply, add="+")


def _high_contrast_enabled() -> bool:
    class HighContrast(ctypes.Structure):
        _fields_ = (("size", wintypes.UINT), ("flags", wintypes.DWORD), ("scheme", ctypes.c_void_p))

    settings = HighContrast(ctypes.sizeof(HighContrast))
    get_high_contrast, high_contrast_on = 0x0042, 0x0001
    success = ctypes.windll.user32.SystemParametersInfoW(
        get_high_contrast, settings.size, ctypes.byref(settings), 0
    )
    return bool(success and settings.flags & high_contrast_on)


def animations_enabled() -> bool:
    """Respect Windows' animation effects preference."""
    if sys.platform != "win32":
        return False
    enabled = wintypes.BOOL()
    get_client_area_animation = 0x1042
    success = ctypes.windll.user32.SystemParametersInfoW(
        get_client_area_animation, 0, ctypes.byref(enabled), 0
    )
    return bool(success and enabled.value)

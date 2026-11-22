"""Shared burgundy colors and native desktop typography."""

import customtkinter as ctk
import sys

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


def animations_enabled() -> bool:
    """Respect Windows' animation effects preference."""
    if sys.platform != "win32":
        return False
    import ctypes
    from ctypes import wintypes

    enabled = wintypes.BOOL()
    get_client_area_animation = 0x1042
    success = ctypes.windll.user32.SystemParametersInfoW(
        get_client_area_animation, 0, ctypes.byref(enabled), 0
    )
    return bool(success and enabled.value)

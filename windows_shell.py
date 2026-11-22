"""Per-user File Explorer integration and recoverable file removal."""

from __future__ import annotations

import ctypes
import os
import subprocess
import sys
from pathlib import Path
from uuid import UUID

from i18n import DEFAULT_LANGUAGE, LANGUAGES, Message, tr

MENU_KEY = r"Software\Classes\*\shell\DosyaDonusturucu.Convert"
STATE_KEY = r"Software\DosyaDonusturucu"
LANGUAGE_VALUE = "Language"
APP_PATH = Path(__file__).with_name("app.py").resolve()
SHELL_DIR = APP_PATH.parent / "shell"


def read_language() -> str:
    if sys.platform != "win32":
        return DEFAULT_LANGUAGE

    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STATE_KEY) as key:
            language = winreg.QueryValueEx(key, LANGUAGE_VALUE)[0]
            return language if isinstance(language, str) and language in LANGUAGES else DEFAULT_LANGUAGE
    except OSError:
        return DEFAULT_LANGUAGE


def save_language(language: str) -> None:
    if sys.platform != "win32":
        return

    import winreg

    with winreg.CreateKey(winreg.HKEY_CURRENT_USER, STATE_KEY) as key:
        winreg.SetValueEx(key, LANGUAGE_VALUE, 0, winreg.REG_SZ, language)
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, MENU_KEY, access=winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, tr("Convert File", language=language))
    except FileNotFoundError:
        pass
    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)


def _modern_menu_enabled() -> bool:
    import winreg
    from ctypes import wintypes

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STATE_KEY) as key:
            family = winreg.QueryValueEx(key, "ExplorerPackageFamily")[0]
    except FileNotFoundError:
        return False
    packages, length = wintypes.UINT(), wintypes.UINT()
    result = ctypes.windll.kernel32.GetPackagesByPackageFamily(
        family, ctypes.byref(packages), None, ctypes.byref(length), None
    )
    return result in (0, 122) and packages.value > 0


def menu_location() -> str | None:
    import winreg

    if _modern_menu_enabled():
        return "main"
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, MENU_KEY + r"\command") as key:
            return "classic" if winreg.QueryValueEx(key, "")[0] else None
    except FileNotFoundError:
        return None


def menu_enabled() -> bool:
    return menu_location() is not None


def set_menu_enabled(enabled: bool) -> None:
    modern = _modern_menu_enabled()
    signed = (SHELL_DIR / "dist" / "ExplorerMenu.cer").is_file()
    if enabled and signed:
        _manage_modern()
        set_classic_menu_enabled(False)
    elif not enabled and modern:
        _manage_modern(remove=True)
        set_classic_menu_enabled(False)
    else:
        set_classic_menu_enabled(enabled)


def _manage_modern(*, remove: bool = False) -> None:
    powershell = Path(os.environ["WINDIR"]) / "System32/WindowsPowerShell/v1.0/powershell.exe"
    command = [
        str(powershell), "-NoProfile", "-NonInteractive",
        "-File", str(SHELL_DIR / "register.ps1"),
    ]
    if remove:
        command.append("-Remove")
    result = subprocess.run(
        command, creationflags=subprocess.CREATE_NO_WINDOW, capture_output=True, text=True,
        errors="replace",
    )
    if result.returncode:
        raise OSError(Message("Could not register the File Explorer extension."))


def set_classic_menu_enabled(enabled: bool) -> None:
    import winreg

    hive = winreg.HKEY_CURRENT_USER
    command_key = MENU_KEY + r"\command"
    if enabled:
        executable = Path(sys.executable).with_name("pythonw.exe")
        if not executable.is_file():
            raise FileNotFoundError(Message("pythonw.exe was not found."))
        with winreg.CreateKey(hive, MENU_KEY) as key:
            winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, tr("Convert File", language=read_language()))
            winreg.SetValueEx(key, "MultiSelectModel", 0, winreg.REG_SZ, "Single")
            icon = APP_PATH.parent / "assets" / "icon.ico"
            if icon.is_file():
                winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, str(icon))
        with winreg.CreateKey(hive, command_key) as key:
            command = f'"{executable}" "{APP_PATH}" -- "%1"'
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)
    else:
        for name in (command_key, MENU_KEY):
            try:
                winreg.DeleteKey(hive, name)
            except FileNotFoundError:
                pass
    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)


def reveal_file(path: str) -> None:
    """Open the containing folder with the given file selected."""
    if not os.path.isfile(path):
        raise FileNotFoundError(path)
    ole = ctypes.OleDLL("ole32")
    shell = ctypes.OleDLL("shell32")
    item = ctypes.c_void_p()
    ole.CoInitializeEx(None, 2)
    try:
        shell.SHParseDisplayName(ctypes.c_wchar_p(os.path.abspath(path)), None, ctypes.byref(item), 0, None)
        shell.SHOpenFolderAndSelectItems(item, 0, None, 0)
    finally:
        if item:
            ole.CoTaskMemFree(item)
        ole.CoUninitialize()


def recycle(path: str) -> None:
    """Ask Windows to recycle the file, without a permanent-delete fallback."""
    from ctypes import wintypes

    root = Path(path).anchor
    drive_fixed = 3
    if ctypes.windll.kernel32.GetDriveTypeW(root) != drive_fixed:
        raise OSError(Message("Files in this location cannot safely be recycled."))

    ole = ctypes.OleDLL("ole32")
    shell = ctypes.OleDLL("shell32")
    operation = ctypes.c_void_p()
    item = ctypes.c_void_p()
    clsid = (ctypes.c_byte * 16).from_buffer_copy(UUID("3ad05575-8857-4850-9277-11b85bdb8e09").bytes_le)
    operation_iid = (ctypes.c_byte * 16).from_buffer_copy(UUID("947aab5f-0a5c-4c13-b4d6-4bf7836fc9f8").bytes_le)
    item_iid = (ctypes.c_byte * 16).from_buffer_copy(UUID("43826d1e-e718-42ee-bc55-a1e261c37bfe").bytes_le)

    def method(pointer, slot, *argtypes, result=ctypes.HRESULT):
        vtable = ctypes.cast(pointer, ctypes.POINTER(ctypes.POINTER(ctypes.c_void_p))).contents
        return ctypes.WINFUNCTYPE(result, ctypes.c_void_p, *argtypes)(vtable[slot])

    def checked(status):
        if status < 0:
            raise OSError(Message(
                "The Windows file operation failed ({code}).", code=f"0x{status & 0xffffffff:08X}",
            ))

    ole.CoInitializeEx(None, 2)  # COINIT_APARTMENTTHREADED
    try:
        ole.CoCreateInstance(clsid, None, 1, operation_iid, ctypes.byref(operation))
        shell.SHCreateItemFromParsingName(
            ctypes.c_wchar_p(path), None, item_iid, ctypes.byref(item)
        )
        # IFileOperation vtable order follows shobjidl_core.h.
        recycle_on_delete = 0x00080000
        silent_no_error_ui = 0x0404
        early_failure = 0x00100000
        checked(method(operation, 5, wintypes.DWORD)(
            operation, recycle_on_delete | silent_no_error_ui | early_failure
        ))
        checked(method(operation, 18, ctypes.c_void_p, ctypes.c_void_p)(operation, item, None))
        checked(method(operation, 21)(operation))
        aborted = wintypes.BOOL()
        checked(method(operation, 22, ctypes.POINTER(wintypes.BOOL))(operation, ctypes.byref(aborted)))
        if aborted.value or os.path.lexists(path):
            raise OSError(Message("Windows could not move the original file to the Recycle Bin."))
    finally:
        for pointer in (item, operation):
            if pointer:
                method(pointer, 2, result=wintypes.ULONG)(pointer)
        ole.CoUninitialize()

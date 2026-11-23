"""Per-user File Explorer integration and recoverable file removal."""

from __future__ import annotations

import ctypes
import os
import struct
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from uuid import UUID

from i18n import DEFAULT_LANGUAGE, LANGUAGES, Message, tr
from engine import presets

MENU_KEY = r"Software\Classes\*\shell\DosyaDonusturucu.Convert"
STATE_KEY = r"Software\DosyaDonusturucu"
LANGUAGE_VALUE = "Language"
PRESET_MENU_VALUE = "ExplorerPresets"
CLASSIC_EXTENSIONS_VALUE = "ClassicPresetExtensions"
ASSOCIATIONS = r"Software\Classes\SystemFileAssociations"
CLASSIC_VERB = "DeskConvert.Presets"
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
    refresh_presets()


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
    return "classic" if _classic_menu_enabled() else None


def _classic_menu_enabled() -> bool:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, STATE_KEY) as key:
            winreg.QueryValueEx(key, CLASSIC_EXTENSIONS_VALUE)
        return True
    except FileNotFoundError:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, MENU_KEY + r"\command"):
                return True
        except FileNotFoundError:
            return False


def menu_enabled() -> bool:
    return menu_location() is not None


def set_menu_enabled(enabled: bool) -> None:
    modern = _modern_menu_enabled()
    signed = (SHELL_DIR / "dist" / "ExplorerMenu.cer").is_file()
    if not enabled:
        if modern:
            _manage_modern(remove=True)
        set_classic_menu_enabled(False)
    else:
        if signed and not modern:
            try:
                _manage_modern()
            except OSError:
                # The classic menu still works before the package's signer is trusted.
                pass
        set_classic_menu_enabled(True)


def upgrade_classic_menu(items) -> None:
    import winreg

    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, MENU_KEY + r"\command"):
            pass
    except FileNotFoundError:
        return
    set_classic_menu_enabled(True, items=items)


def refresh_presets(items=None) -> None:
    if _classic_menu_enabled():
        set_classic_menu_enabled(True, items=items)
    elif _modern_menu_enabled():
        import winreg

        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, STATE_KEY) as key:
            _write_native_menu(key, items if items is not None else presets.load(), read_language())
        _notify_assoc_changed()


def _notify_assoc_changed() -> None:
    ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)


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


def _rows(items, language):
    for item in items:
        if not item.enabled:
            continue
        extensions = presets.applicable_extensions(item)
        if extensions:
            name = tr(item.name, language=language) if item.builtin else item.name
            group = tr(item.group, language=language) if item.builtin else item.group
            yield item.id, name, group, extensions


def _write_native_menu(key, items, language):
    import winreg

    rows = ["\t".join((identifier, ",".join(exts), f"{group} / {name}" if group else name))
            for identifier, name, group, exts in _rows(items, language)]
    winreg.SetValueEx(key, PRESET_MENU_VALUE, 0, winreg.REG_MULTI_SZ, rows)
    winreg.SetValueEx(key, "ExplorerPython", 0, winreg.REG_SZ,
                      str(Path(sys.executable).with_name("pythonw.exe")))


def _delete_tree(path):
    import winreg

    hive = winreg.HKEY_CURRENT_USER
    try:
        with winreg.OpenKey(hive, path) as key:
            children = [winreg.EnumKey(key, index) for index in range(winreg.QueryInfoKey(key)[0])]
    except FileNotFoundError:
        return
    for child in children:
        _delete_tree(f"{path}\\{child}")
    winreg.DeleteKey(hive, path)


def _write_classic_menu(root, rows, executable, language):
    import winreg

    hive = winreg.HKEY_CURRENT_USER
    icon = APP_PATH.parent / "assets" / "icon.ico"

    def entry(path, label, *, cascade=False, argument=""):
        with winreg.CreateKey(hive, path) as key:
            winreg.SetValueEx(key, "MUIVerb", 0, winreg.REG_SZ, label)
            if cascade:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "")
            else:
                winreg.SetValueEx(key, "MultiSelectModel", 0, winreg.REG_SZ, "Single")
        if not cascade:
            with winreg.CreateKey(hive, path + r"\command") as key:
                command = f'"{executable}" "{APP_PATH}" {argument} -- "%1"'
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, command)

    entry(root, "DeskConvert", cascade=True)
    if icon.is_file():
        with winreg.OpenKey(hive, root, access=winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, str(icon))
    menu = root + r"\ExtendedSubCommandsKey\shell"
    groups = {}
    for index, (identifier, name, group) in enumerate(rows, 1):
        branch = menu
        if group:
            if group not in groups:
                parent = f"{menu}\\{index:04d}-group"
                entry(parent, group, cascade=True)
                groups[group] = parent + r"\ExtendedSubCommandsKey\shell"
            branch = groups[group]
        entry(f"{branch}\\{index:04d}-{identifier}", name, argument=f"--preset {identifier}")
    entry(menu + r"\9998-open", tr("Open DeskConvert", language=language))
    entry(menu + r"\9999-configure", tr("Manage presets", language=language), argument="--configure-presets")


def set_classic_menu_enabled(enabled: bool, *, items=None) -> None:
    import winreg

    hive = winreg.HKEY_CURRENT_USER
    executable = Path(sys.executable).with_name("pythonw.exe")
    if enabled and not executable.is_file():
        raise FileNotFoundError(Message("pythonw.exe was not found."))
    language = read_language()
    items = (presets.load() if items is None else items) if enabled else []
    grouped = defaultdict(list)
    if enabled:
        extension_names = presets.detect.FORMAT_CATEGORY.keys() | presets.detect.ALIASES.keys()
        for extension in extension_names:
            grouped[extension] = []
    for identifier, name, group, extensions in _rows(items, language):
        for extension in extensions:
            grouped[extension].append((identifier, name, group))

    def root(extension):
        return f"{ASSOCIATIONS}\\.{extension}\\shell\\{CLASSIC_VERB}"

    with winreg.CreateKey(hive, STATE_KEY) as state:
        try:
            old = winreg.QueryValueEx(state, CLASSIC_EXTENSIONS_VALUE)[0]
        except FileNotFoundError:
            old = ()
        _delete_tree(MENU_KEY)
        if enabled:
            # Record keys before building so a partially failed registration can be retried or removed.
            tracked = sorted(set(old) | set(grouped))
            winreg.SetValueEx(state, CLASSIC_EXTENSIONS_VALUE, 0, winreg.REG_MULTI_SZ, tracked)
            _write_native_menu(state, items, language)
        for extension in old:
            _delete_tree(root(extension))
        if enabled:
            for extension, rows in grouped.items():
                _write_classic_menu(root(extension), rows, executable, language)
            winreg.SetValueEx(state, CLASSIC_EXTENSIONS_VALUE, 0, winreg.REG_MULTI_SZ, sorted(grouped))
        else:
            for value in (CLASSIC_EXTENSIONS_VALUE, PRESET_MENU_VALUE, "ExplorerPython"):
                try:
                    winreg.DeleteValue(state, value)
                except FileNotFoundError:
                    pass
    _notify_assoc_changed()


def copy_files(paths: list[str], hwnd: int) -> None:
    """Put completed files on the Windows clipboard for normal Explorer paste."""
    import pywintypes
    import win32clipboard
    import win32con

    dropfiles = struct.pack("<IiiII", 20, 0, 0, 0, 1)
    names = ("\0".join(os.path.abspath(path) for path in paths) + "\0\0").encode("utf-16-le")
    try:
        win32clipboard.OpenClipboard(hwnd)
        try:
            win32clipboard.EmptyClipboard()
            win32clipboard.SetClipboardData(win32con.CF_HDROP, dropfiles + names)
        finally:
            win32clipboard.CloseClipboard()
    except pywintypes.error as error:
        raise OSError(str(error)) from error


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

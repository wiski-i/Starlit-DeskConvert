"""Resolve preset output paths and page numbers."""
from __future__ import annotations

import os
import re
from datetime import datetime
from pathlib import Path

_TOKEN = re.compile(r"\((p(?::[dmvp])?|f|i|o|d\d+|n:[ic]|d:[^)]+)\)", re.IGNORECASE)
_DATE = re.compile(r"yyyy|yy|MMMM|MMM|MM|M|dddd|ddd|dd|d|HH|H|hh|h|mm|m|ss|s|tt|'[^']*'|\"[^\"]*\"")
_DATE_PARTS = dict(zip(
    "yyyy yy MMMM MMM MM M dddd ddd dd d HH H hh h mm m ss s tt".split(),
    "%Y %y %B %b %m %-m %A %a %d %-d %H %-H %I %-I %M %-M %S %-S %p".split(),
))


def _date(pattern: str, now: datetime) -> str:
    def part(match):
        token = match[0]
        if token.startswith(("'", '"')):
            return token[1:-1]
        spec = _DATE_PARTS[token]
        value = now.strftime(spec.replace("-", ""))
        return value.lstrip("0") or "0" if "-" in spec else value

    return _DATE.sub(part, pattern)


def _known_folder(folder: str) -> Path:
    fallback = Path.home() / folder
    if os.name != "nt":
        return fallback
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                            r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders") as key:
            name = "Personal" if folder == "Documents" else f"My {folder}"
            return Path(os.path.expandvars(winreg.QueryValueEx(key, name)[0]))
    except OSError:
        return fallback


def destination(
    src: str, ext: str, template: str, out_dir: str | None, page: int, count: int,
    now: datetime | None = None,
) -> Path:
    source = Path(src).absolute()
    folder = Path(out_dir).absolute() if out_dir else source.parent
    stem = source.stem
    if stem.lower().endswith(".tar") and source.suffix.lower() in {".gz", ".bz2", ".xz"}:
        stem = stem[:-4]
    if not template:
        if not out_dir and source.suffix.lower() == ".cda":
            folder = _known_folder("Music") / "CDA Extraction"
        return folder / f"{stem}{f' ({page})' if count > 1 else ''}.{ext}"

    now = now or datetime.now()
    values = {"p": str(folder) + os.sep, "f": stem, "i": source.suffix[1:], "o": ext,
              "n:i": str(page), "n:c": str(count)}
    known = {"p:d": "Documents", "p:m": "Music", "p:v": "Videos", "p:p": "Pictures"}

    def expand(match):
        original = match[1]
        key = original.lower()
        if key.startswith("d:"):
            return _date(original[2:], now)
        if key.startswith("d"):
            index = int(key[1:])
            value = source.parents[index].name if index < len(source.parents) else ""
        elif key in known:
            value = str(_known_folder(known[key])) + os.sep
        else:
            value = values[key]
        return value.upper() if original.isupper() and not key.startswith("p") else value

    rendered = Path(_TOKEN.sub(expand, template))
    name = rendered.name
    if not name or name in {".", ".."}:
        raise ValueError("The output template must produce a file name.")
    if name.lower().endswith(f".{ext.lower()}"):
        name = name[:-(len(ext) + 1)]
    if count > 1 and "(n:i)" not in template.lower():
        name = f"{name} ({page})"
    return folder / rendered.with_name(f"{name}.{ext}")

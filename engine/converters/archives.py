"""Arşiv dönüştürücü.

Kaynağı geçici bir klasöre açıp hedef formata yeniden paketler.
zip, tar, gz(tar.gz), bz2, xz, 7z desteklenir. rar yalnızca okunabilir
(py7zr/rarfile varsa); çıktı olarak rar üretilmez.
"""
from __future__ import annotations

import os
import shutil
import tarfile
import tempfile
import zipfile
from pathlib import Path, PureWindowsPath

from i18n import Message

CATEGORY = "archive"

OUTPUTS = ["zip", "tar", "gztar", "bztar", "xztar", "7z"]

# Kullanıcıya gösterilecek dostça adlar
LABELS = {
    "zip": "zip", "tar": "tar", "gztar": "tar.gz",
    "bztar": "tar.bz2", "xztar": "tar.xz", "7z": "7z",
}


def available():
    return True, ""  # zip/tar stdlib ile her zaman var


def _extract(src: str, fmt: str, dest: str) -> None:
    if fmt == "zip":
        with zipfile.ZipFile(src) as z:
            z.extractall(dest)
    elif fmt == "7z":
        import py7zr
        with py7zr.SevenZipFile(src, "r") as z:
            z.extractall(dest)
    elif fmt == "rar":
        import rarfile
        with rarfile.RarFile(src) as r:
            r.extractall(dest)
    elif fmt in ("tar", "gz", "tgz", "bz2", "xz"):
        _extract_tar(src, dest)
    else:
        raise ValueError(Message("Could not open the {format} archive.", format=fmt))


def _extract_tar(src: str, dest: str) -> None:
    """Accept regular files and folders within the extraction directory."""
    root = Path(dest).resolve()
    with tarfile.open(src) as archive:
        for member in archive:
            name = PureWindowsPath(member.name)
            invalid_part = any(
                part != part.rstrip(" .") or any(char in part for char in '<>:"|?*')
                for part in name.parts
            )
            if name.anchor or invalid_part:
                raise ValueError(Message("The archive contains an unsafe file path."))
            target = root.joinpath(*name.parts)
            if not target.resolve().is_relative_to(root) or target.is_reserved():
                raise ValueError(Message("The archive contains an unsafe file path."))
            if member.isdir():
                target.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                target.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as source, target.open("wb") as output:
                    shutil.copyfileobj(source, output)
            else:
                raise ValueError(Message("TAR links and special files are unsupported."))


def _repack(folder: str, dst: str, fmt: str) -> None:
    base = os.path.splitext(dst)[0]
    # shutil appends the full compound extension.
    if dst.endswith(".tar.gz") or dst.endswith(".tar.bz2") or dst.endswith(".tar.xz"):
        base = dst.rsplit(".tar", 1)[0]

    if fmt == "7z":
        import py7zr
        with py7zr.SevenZipFile(dst, "w") as z:
            for root, _dirs, files in os.walk(folder):
                for f in files:
                    full = os.path.join(root, f)
                    z.write(full, os.path.relpath(full, folder))
        return

    made = shutil.make_archive(base, fmt, folder)
    if os.path.abspath(made) != os.path.abspath(dst):
        if os.path.exists(dst):
            os.remove(dst)
        os.replace(made, dst)


def convert(src: str, dst: str, src_fmt: str, dst_fmt: str) -> None:
    tmp = tempfile.mkdtemp(prefix="donusturucu_")
    try:
        _extract(src, src_fmt, tmp)
        _repack(tmp, dst, dst_fmt)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

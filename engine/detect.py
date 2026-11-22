"""Dosya formatı algılama.

Önce sihirli baytlar (magic bytes), sonra dosya uzantısı kullanılarak
formatın türü ve kategorisi belirlenir. Hiçbir harici servise ihtiyaç yoktur.
"""
from __future__ import annotations

import os
from codecs import getincrementaldecoder
import zipfile

# Uzantı eş anlamlıları -> kanonik (tek) ad
ALIASES = {
    "jpeg": "jpg", "jpe": "jpg", "jfif": "jpg",
    "tif": "tiff",
    "htm": "html",
    "yml": "yaml",
    "mpeg": "mpg",
    "m4v": "mp4",
    "midi": "mid",
    "text": "txt",
    "markdown": "md",
    "aif": "aiff",
    "oga": "ogg",
}

# Kanonik format -> kategori
FORMAT_CATEGORY = {
    # --- Görseller ---
    "png": "image", "jpg": "image", "webp": "image", "bmp": "image",
    "gif": "image", "tiff": "image", "ico": "image", "heic": "image",
    "heif": "image", "avif": "image", "ppm": "image", "pgm": "image",
    "tga": "image", "dib": "image", "jp2": "image", "svg": "image",
    # --- Ses ---
    "mp3": "audio", "wav": "audio", "flac": "audio", "aac": "audio",
    "ogg": "audio", "oga": "audio", "m4a": "audio", "opus": "audio",
    "wma": "audio", "aiff": "audio", "aif": "audio", "amr": "audio",
    "mid": "audio", "ac3": "audio",
    # --- Video ---
    "mp4": "video", "mkv": "video", "avi": "video", "mov": "video",
    "webm": "video", "flv": "video", "wmv": "video", "mpg": "video",
    "3gp": "video", "ts": "video", "ogv": "video",
    # --- Belgeler ---
    "docx": "document", "doc": "document", "odt": "document",
    "rtf": "document", "html": "document", "md": "document",
    "markdown": "document", "txt": "document", "epub": "document",
    "tex": "document", "rst": "document", "org": "document",
    # --- Veri / Tablo ---
    "csv": "data", "tsv": "data", "xlsx": "data", "xls": "data",
    "json": "data", "xml": "data", "yaml": "data", "parquet": "data",
    "ods": "data",
    # --- Arşivler ---
    "zip": "archive", "tar": "archive", "gz": "archive", "tgz": "archive",
    "bz2": "archive", "xz": "archive", "7z": "archive", "rar": "archive",
}

# Sihirli baytlar: (imza, ofset, kanonik format)
_MAGIC = [
    (b"\x89PNG\r\n\x1a\n", 0, "png"),
    (b"\xff\xd8\xff", 0, "jpg"),
    (b"GIF87a", 0, "gif"),
    (b"GIF89a", 0, "gif"),
    (b"BM", 0, "bmp"),
    (b"II+\x00", 0, "tiff"),
    (b"MM\x00+", 0, "tiff"),
    (b"II*\x00", 0, "tiff"),
    (b"MM\x00*", 0, "tiff"),
    (b"\x00\x00\x01\x00", 0, "ico"),
    (b"RIFF", 0, "_riff"),          # wav / webp / avi -> alt türe bakılır
    (b"OggS", 0, "ogg"),
    (b"fLaC", 0, "flac"),
    (b"ID3", 0, "mp3"),
    (b"\xff\xfb", 0, "mp3"),
    (b"\xff\xf3", 0, "mp3"),
    (b"\xff\xf2", 0, "mp3"),
    (b"\x1aE\xdf\xa3", 0, "_matroska"),  # mkv / webm
    (b"\x00\x00\x00", 0, "_isom"),       # mp4/mov/m4a (ftyp ofset 4)
    (b"PK\x03\x04", 0, "_zip"),          # zip/docx/xlsx/odt/epub...
    (b"PK\x05\x06", 0, "_zip"),
    (b"Rar!\x1a\x07", 0, "rar"),
    (b"7z\xbc\xaf\x27\x1c", 0, "7z"),
    (b"BZh", 0, "bz2"),
    (b"PAR1", 0, "parquet"),
    (b"\x1f\x8b", 0, "gz"),
    (b"BZh", 0, "bz2"),
    (b"\xfd7zXZ\x00", 0, "xz"),
    (b"ustar", 257, "tar"),
    (b"%PDF", 0, "pdf"),
    (b"{\\rtf", 0, "rtf"),
]


def _sniff(path: str, extension: str) -> str | None:
    """Identify known binary signatures and extensionless text."""
    try:
        with open(path, "rb") as fh:
            head = fh.read(1024)
    except OSError:
        return None
    if not head:
        return None

    for sig, off, fmt in _MAGIC:
        if head[off:off + len(sig)] == sig:
            if fmt == "bmp" and (len(head) < 26 or head[6:10] != b"\x00\x00\x00\x00"):
                continue
            if fmt == "_riff":
                sub = head[8:12]
                if sub == b"WAVE":
                    return "wav"
                if sub == b"WEBP":
                    return "webp"
                if sub == b"AVI ":
                    return "avi"
                return None
            if fmt == "_matroska":
                return "webm" if b"webm" in head[:64].lower() else "mkv"
            if fmt == "_isom":
                brand = head[4:8]
                if brand != b"ftyp":
                    return None
                major = head[8:12]
                if major in {b"avif", b"avis"}:
                    return "avif"
                if major in {b"heic", b"heix", b"hevc", b"hevx", b"mif1", b"msf1"}:
                    return extension if extension in {"heic", "heif"} else "heic"
                if major[:3] == b"M4A":
                    return "m4a"
                if major[:3] in (b"qt ", b"QT "):
                    return "mov"
                return extension if extension in {"m4a", "3gp"} else "mp4"
            if fmt == "_zip":
                return _zip_kind(path)
            if fmt == "ogg" and b"OpusHead" in head:
                return "opus"
            return fmt
    if not extension:
        try:
            text = getincrementaldecoder("utf-8-sig")().decode(head, final=False)
        except UnicodeError:
            return None
        if text and all(character.isprintable() or character in "\t\n\r" for character in text):
            return "txt"
    return None


def _zip_kind(path: str) -> str:
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            if "word/document.xml" in names:
                return "docx"
            if "xl/workbook.xml" in names:
                return "xlsx"
            if "mimetype" in names:
                with archive.open("mimetype") as stream:
                    kind = stream.read(96).strip()
                return {
                    b"application/epub+zip": "epub",
                    b"application/vnd.oasis.opendocument.text": "odt",
                    b"application/vnd.oasis.opendocument.spreadsheet": "ods",
                }.get(kind, "zip")
    except (OSError, zipfile.BadZipFile, RuntimeError):
        pass
    return "zip"


def canonical(fmt: str) -> str:
    """Uzantıyı kanonik forma indirger (jpeg->jpg gibi)."""
    fmt = fmt.lower().lstrip(".")
    return ALIASES.get(fmt, fmt)


def detect(path: str) -> dict:
    """Dosyayı algılar.

    Döner: {format, category, ext, sniffed, name, size}
    format/category bilinmiyorsa None olabilir.
    """
    name = os.path.basename(path)
    ext = canonical(os.path.splitext(path)[1])
    sniffed = _sniff(path, ext)

    fmt = sniffed or ext

    category = FORMAT_CATEGORY.get(fmt)
    try:
        size = os.path.getsize(path)
    except OSError:
        size = 0

    return {
        "format": fmt or None,
        "category": category,
        "ext": ext or None,
        "sniffed": sniffed,
        "name": name,
        "size": size,
    }

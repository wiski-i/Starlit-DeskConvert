"""Kategori -> dönüştürücü eşlemesi ve olası hedeflerin hesaplanması."""
from __future__ import annotations

from importlib.util import find_spec

from i18n import Message

from .converters import images, media, documents, data, archives, pages

# Category -> (module, English display label).
CATEGORY_INFO = {
    "image": (images, "Image"),
    "audio": (media, "Audio"),
    "video": (media, "Video"),
    "document": (documents, "Document"),
    "data": (data, "Table / Data"),
    "archive": (archives, "Archive"),
}

# Arşiv hedef anahtarı -> dosya uzantısı
_ARCHIVE_EXT = {
    "zip": "zip", "tar": "tar", "gztar": "tar.gz",
    "bztar": "tar.bz2", "xztar": "tar.xz", "7z": "7z",
}
# Kaynak arşiv formatı -> shutil hedef anahtarı (kendini hariç tutmak için)
_ARCHIVE_SELF = {
    "zip": "zip", "tar": "tar", "gz": "gztar", "tgz": "gztar",
    "bz2": "bztar", "xz": "xztar", "7z": "7z",
}


def module_for(category: str):
    info = CATEGORY_INFO.get(category)
    return info[0] if info else None


def label_for(category: str) -> str:
    info = CATEGORY_INFO.get(category)
    return info[1] if info else "Unknown"


def engine_status(category: str):
    """(uygun_mu, mesaj) — gerekli motor kurulu mu?"""
    mod = module_for(category)
    if not mod:
        return False, Message("No converter is available for this format.")
    return mod.available()


_DATA_INPUT_MODULES = {
    "ods": ("odf",), "xls": ("xlrd",), "xlsx": ("openpyxl",),
    "xml": ("lxml",), "yaml": ("yaml",),
}
_DATA_OUTPUT_MODULES = {
    "xlsx": ("openpyxl",), "xml": ("lxml",), "md": ("tabulate",),
}


def _has_parquet() -> bool:
    return any(find_spec(module) is not None for module in ("pyarrow", "fastparquet"))


def source_status(detection: dict) -> tuple[bool, str]:
    """Check per-format readers and their optional dependencies."""
    category, fmt = detection.get("category"), detection.get("format")
    if fmt in pages.INPUTS and (fmt not in documents.INPUTS and category == "document"):
        if pages.available(fmt):
            return True, ""
        if fmt in pages.OFFICE:
            return False, Message("This conversion requires Microsoft {program}.", program=pages.OFFICE[fmt])
        return False, Message("Reading this format requires {module}.", module="pypdfium2")
    if category == "document" and fmt not in documents.INPUTS:
        return False, Message("A reader is unavailable for this document format.")
    if category == "data":
        if fmt in pages.OFFICE and pages.available(fmt):
            return True, ""
        if fmt == "parquet" and not _has_parquet():
            return False, Message("Reading Parquet requires PyArrow or fastparquet.")
        for module in _DATA_INPUT_MODULES.get(fmt, ()):
            if find_spec(module) is None:
                return False, Message("Reading this format requires {module}.", module=module)
    if category == "archive" and fmt in {"7z", "rar"}:
        module = {"7z": "py7zr", "rar": "rarfile"}[fmt]
        if find_spec(module) is None:
            return False, Message("Reading this archive requires {module}.", module=module)
    return True, ""


def targets(detection: dict, *, include_self=False, check_source=True) -> list[dict]:
    """Algılanan dosya için olası hedefleri döndürür.

    Her hedef: {key, label, ext}
    key  -> convert()'e verilecek hedef format anahtarı
    ext  -> oluşturulacak dosya uzantısı
    label-> arayüzde gösterilecek ad
    """
    category = detection.get("category")
    fmt = detection.get("format")
    out: list[dict] = []
    if check_source and not source_status(detection)[0]:
        return out

    if category == "image":
        for k in images.OUTPUTS:
            if k == "webp" and images_webp_blocked(detection):
                continue
            if k != fmt or include_self:
                out.append({"key": k, "label": k.upper(), "ext": k})

        if fmt == "gif":
            for k in media.VIDEO_OUTPUTS:
                if k != "gif":
                    out.append({"key": k, "label": k.upper(), "ext": k, "engine": "media"})

    elif category in ("audio", "video"):
        for k in media.outputs_for(category):
            if k != fmt or include_self:
                out.append({"key": k, "label": k.upper(), "ext": k})

    elif category == "document":
        for k in documents.OUTPUTS if fmt in documents.INPUTS else ():
            if k != fmt or include_self:
                out.append({"key": k, "label": k.upper(), "ext": k})

    elif category == "data":
        data_readable = not any(find_spec(module) is None for module in _DATA_INPUT_MODULES.get(fmt, ()))
        for k in data.OUTPUTS if data_readable else ():
            if k == "parquet" and not _has_parquet():
                continue
            if any(find_spec(module) is None for module in _DATA_OUTPUT_MODULES.get(k, ())):
                continue
            if k != fmt or include_self:
                out.append({"key": k, "label": k.upper(), "ext": k})

    elif category == "archive":
        self_key = _ARCHIVE_SELF.get(fmt)
        for k in archives.OUTPUTS:
            if (k == self_key and not include_self) or (k == "7z" and find_spec("py7zr") is None):
                continue
            out.append({"key": k, "label": archives.LABELS[k], "ext": _ARCHIVE_EXT[k]})

    if fmt in pages.INPUTS and (not check_source or pages.available(fmt)):
        page_targets = list(pages.OUTPUTS) if not check_source or pages.available("pdf") else []
        if fmt != "pdf":
            page_targets.insert(0, "pdf")
        out.extend({"key": k, "label": k.upper(), "ext": k, "engine": "pages"} for k in page_targets)
    return out


def images_webp_blocked(detection: dict) -> bool:
    depth = detection.get("png_depth")
    return depth is not None and (depth > 8 or detection.get("animated", False))

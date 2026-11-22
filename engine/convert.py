"""Üst düzey dönüştürme akışı: algıla -> hedefe çevir."""
from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from pathlib import Path

from i18n import Message

from . import detect as _detect
from . import registry


def analyze(path: str) -> dict:
    """Dosyayı algılar ve olası hedefleri ekler."""
    info = _detect.detect(path)
    info["category_label"] = registry.label_for(info.get("category"))
    if info.get("category"):
        ok, msg = registry.engine_status(info["category"])
        if ok:
            ok, msg = registry.source_status(info)
        if ok and info["category"] == "image":
            from PIL import Image

            try:
                info.update(registry.module_for("image").inspect_source(path))
            except (OSError, ValueError, Image.DecompressionBombError):
                ok, msg = False, Message("This image could not be opened or its format is unsupported.")
        info["engine_ok"] = ok
        info["engine_msg"] = msg
    else:
        info["engine_ok"] = False
        info["engine_msg"] = Message("This file format was not recognized.")
    info["targets"] = registry.targets(info) if info["engine_ok"] else []
    return info


def output_path(src: str, target: dict, out_dir: str | None = None) -> str:
    """Suggest an available output name alongside the source or in a chosen folder."""
    base = os.path.splitext(os.path.basename(src))[0]
    if base.lower().endswith(".tar") and Path(src).suffix.lower() in {".gz", ".bz2", ".xz"}:
        base = base[:-4]
    folder = out_dir or os.path.dirname(src)
    candidate = os.path.join(folder, f"{base}.{target['ext']}")
    n = 1
    while os.path.lexists(candidate):
        candidate = os.path.join(folder, f"{base} ({n}).{target['ext']}")
        n += 1
    return candidate


def run(
    src: str, detection: dict, target: dict, out_dir: str | None = None, *, verify: bool = False
) -> str:
    """Encode to a private staging path and publish without overwriting an existing file."""
    category = detection["category"]
    src_fmt = detection["format"]
    mod = registry.module_for(category)
    if mod is None:
        raise RuntimeError(Message("No converter is available for this format."))

    ok, msg = mod.available()
    if not ok:
        raise RuntimeError(msg or Message("The required conversion engine is missing."))
    if not any(
        route["key"] == target["key"] and route["ext"] == target["ext"]
        for route in registry.targets(detection)
    ):
        raise ValueError(Message("This file cannot be converted to the selected format."))

    folder = out_dir or os.path.dirname(src) or "."
    with tempfile.TemporaryDirectory(prefix=".convert-", dir=folder) as staging:
        staged = os.path.abspath(os.path.join(staging, f"output.{target['ext']}"))
        mod.convert(os.path.abspath(src), staged, src_fmt, target["key"])
        if not os.path.isfile(staged):
            raise OSError(Message("The conversion engine did not create an output file."))
        if verify:
            _verify_output(staged, category, target["key"])
        while True:
            dst = output_path(src, target, out_dir)
            try:
                if os.name == "nt":
                    os.rename(staged, dst)
                else:
                    os.link(staged, dst)
            except FileExistsError:
                continue
            return dst


def _verify_output(path: str, category: str, target: str) -> None:
    """Check that the converted file can be read before removing its source."""
    if category == "image" and target != "pdf":
        from PIL import Image, ImageSequence

        with Image.open(path) as image:
            for frame in ImageSequence.Iterator(image):
                frame.load()
    elif category in {"video", "audio"}:
        registry.module_for(category).verify(path, target)
    elif target in {"zip", "docx", "odt", "epub", "xlsx"}:
        import zipfile

        with zipfile.ZipFile(path) as archive:
            if archive.testzip() is not None:
                raise ValueError(Message("The output archive could not be verified."))
    elif target in {"tar", "gztar", "bztar", "xztar"}:
        import tarfile

        with tarfile.open(path) as archive:
            for member in archive:
                if member.isfile():
                    with archive.extractfile(member) as file:
                        while file.read(1024 * 1024):
                            pass
    elif target == "7z":
        import py7zr

        with py7zr.SevenZipFile(path) as archive:
            if archive.test() is False:
                raise ValueError(Message("The output archive could not be verified."))
    elif target in {"pdf", "parquet"}:
        header = b"%PDF-" if target == "pdf" else b"PAR1"
        with open(path, "rb") as output:
            if output.read(len(header)) != header:
                raise ValueError(Message("The output format could not be verified."))
    else:
        with open(path, encoding="utf-8") as output:
            while output.read(1024 * 1024):
                pass


def _source_signature(path: str) -> tuple[int, int, int, int]:
    stat = os.stat(path, follow_symlinks=False)
    return stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns


def replace_source(
    src: str, detection: dict, target: dict, recycle: Callable[[str], None]
) -> tuple[str, str | None]:
    """Publish a readable copy before asking the shell to recycle the original."""
    if os.path.islink(src):
        raise ValueError(Message("Choose Create a copy when converting a file link."))
    before = _source_signature(src)
    dst = run(src, detection, target, verify=True)
    try:
        if before != _source_signature(src):
            raise OSError(Message("The source file changed during conversion."))
        if not os.path.isfile(dst):
            raise OSError(Message("The converted file could not be found."))
        recycle(os.path.abspath(src))
    except OSError as error:
        reason = error.args[0] if len(error.args) == 1 and isinstance(error.args[0], Message) else str(error)
        return dst, reason
    return dst, None

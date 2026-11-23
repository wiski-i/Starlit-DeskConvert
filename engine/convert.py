"""Üst düzey dönüştürme akışı: algıla -> hedefe çevir."""
from __future__ import annotations

import os
import tempfile
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

from i18n import Message

from . import detect as _detect
from . import registry
from .output_names import destination


def analyze(path: str) -> dict:
    """Dosyayı algılar ve olası hedefleri ekler."""
    info = _detect.detect(path)
    info["category_label"] = registry.label_for(info.get("category"))
    if info.get("category"):
        if info["format"] in registry.pages.INPUTS and info["format"] not in registry.documents.INPUTS:
            ok, msg = registry.source_status(info)
        else:
            ok, msg = registry.engine_status(info["category"])
        if ok:
            ok, msg = registry.source_status(info)
        if ok and info["category"] == "image":
            from PIL import Image

            try:
                info.update(registry.images.inspect_source(path, info["format"]))
            except (OSError, ValueError, ImportError, RuntimeError, Image.DecompressionBombError):
                ok, msg = False, Message("This image could not be opened or its format is unsupported.")
        info["engine_ok"] = ok
        info["engine_msg"] = msg
    else:
        info["engine_ok"] = False
        info["engine_msg"] = Message("This file format was not recognized.")
    info["targets"] = registry.targets(info) if info["engine_ok"] else []
    return info


def output_path(
    src: str, target: dict, out_dir: str | None = None, *, page: int = 1, count: int = 1,
    now: datetime | None = None,
) -> str:
    """Suggest an available output name alongside the source or in a chosen folder."""
    preset = target.get("preset")
    desired = destination(src, target["ext"], preset.template if preset else "", out_dir, page, count, now)
    candidate = desired
    n = 1
    extension = "." + target["ext"]
    stem = desired.name[:-len(extension)]
    while os.path.lexists(candidate):
        candidate = desired.with_name(f"{stem} ({n}){extension}")
        n += 1
    return str(candidate)


def run(
    src: str, detection: dict, target: dict, out_dir: str | None = None, *, verify: bool = False,
    outputs_out: list[str] | None = None,
) -> str:
    """Encode and verify in staging, then publish without overwriting other files."""
    category = detection["category"]
    src_fmt = detection["format"]
    preset = target.get("preset")
    if not any(
        all(route.get(key) == target.get(key) for key in ("key", "ext", "engine"))
        for route in registry.targets(detection, include_self=preset is not None)
    ):
        raise ValueError(Message("This file cannot be converted to the selected format."))

    now = datetime.now()
    folder = Path(output_path(src, target, out_dir, now=now)).parent
    folder.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".convert-", dir=folder) as staging:
        staged = Path(staging) / f"output.{target['ext']}"
        backend = target.get("engine")
        if backend == "pages":
            outputs = registry.pages.convert(os.path.abspath(src), Path(staging), src_fmt, target["key"], preset)
        else:
            mod = registry.media if backend == "media" else registry.module_for(category)
            ok, msg = mod.available()
            if not ok:
                raise RuntimeError(msg or Message("The required conversion engine is missing."))
            args = (os.path.abspath(src), str(staged), src_fmt, target["key"])
            if mod in (registry.media, registry.images):
                mod.convert(*args, preset=preset)
            else:
                mod.convert(*args)
            outputs = [staged]
        if not outputs or any(not item.is_file() or not item.stat().st_size for item in outputs):
            raise OSError(Message("The conversion engine did not create an output file."))
        if verify:
            for item in outputs:
                _verify_output(str(item), "video" if backend == "media" else category, target["key"])
        published = []
        try:
            for index, item in enumerate(outputs, 1):
                while True:
                    dst = output_path(src, target, out_dir, page=index, count=len(outputs), now=now)
                    Path(dst).parent.mkdir(parents=True, exist_ok=True)
                    try:
                        if os.name == "nt":
                            os.rename(item, dst)
                        else:
                            os.link(item, dst)
                    except FileExistsError:
                        continue
                    published.append((dst, _source_signature(dst)))
                    break
        except OSError:
            for dst, signature in published:
                try:
                    if _source_signature(dst) == signature:
                        os.unlink(dst)
                except OSError:
                    pass
            raise
        if outputs_out is not None:
            outputs_out.extend(dst for dst, _signature in published)
        return published[0][0]


def _verify_output(path: str, category: str, target: str) -> None:
    """Check that the converted file can be read before removing its source."""
    if target in registry.images.OUTPUTS and target != "pdf" and category not in {"audio", "video"}:
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
    src: str, detection: dict, target: dict, recycle: Callable[[str], None], out_dir: str | None = None,
    *, outputs_out: list[str] | None = None,
) -> tuple[str, str | None]:
    """Publish a readable copy before asking the shell to recycle the original."""
    if os.path.islink(src):
        raise ValueError(Message("Choose Create a copy when converting a file link."))
    before = _source_signature(src)
    dst = run(src, detection, target, out_dir, verify=True, outputs_out=outputs_out)
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


def archive_source(src: str) -> None:
    """Move a verified source into a sibling archive without replacing an older file."""
    source = Path(src)
    folder = source.parent / "Conversion Archives"
    folder.mkdir(exist_ok=True)
    index = 0
    while True:
        name = f"{source.stem} ({index}){source.suffix}" if index else source.name
        target = folder / name
        try:
            if os.name == "nt":
                source.rename(target)
            else:
                os.link(source, target)
            break
        except FileExistsError:
            index += 1
    if os.name != "nt":
        try:
            source.unlink()
        except OSError:
            target.unlink()
            raise

"""Görsel dönüştürücü (Pillow).

Desteklenen çıktılar görsellerin yanı sıra PDF'i de içerir.
"""
from __future__ import annotations

from functools import cache
from io import BytesIO
from pathlib import Path

from i18n import Message

CATEGORY = "image"

# Bu kategoride üretebileceğimiz çıktı formatları
OUTPUTS = ["png", "jpg", "webp", "bmp", "gif", "tiff", "ico", "tga", "ppm", "pdf", "avif"]

# Pillow'un kaydederken kullandığı format adı (kanonik -> Pillow formatı)
_SAVE_FORMAT = {
    "jpg": "JPEG", "png": "PNG", "webp": "WEBP", "bmp": "BMP",
    "gif": "GIF", "tiff": "TIFF", "ico": "ICO", "tga": "TGA",
    "ppm": "PPM", "pdf": "PDF", "heic": "HEIF", "avif": "AVIF",
}


def available():
    try:
        import PIL  # noqa: F401
        return True, ""
    except ImportError:
        return False, Message("{component} is missing. Install {package}.", component="Pillow", package="Pillow")


@cache
def _register_optional():
    """HEIC/AVIF gibi opsiyonel eklentileri yükle."""
    try:
        import pillow_heif
        pillow_heif.register_heif_opener()
    except Exception:
        pass
    try:
        import pillow_avif  # noqa: F401
    except Exception:
        pass


def png_depth(path: str) -> int | None:
    """Read the channel bit depth from a PNG header."""
    with open(path, "rb") as source:
        header = source.read(25)
    if len(header) == 25 and header[:8] == b"\x89PNG\r\n\x1a\n":
        return header[24]
    return None


_RAW = {"dng", "arw", "cr2", "nef", "raf"}


def _open(path, fmt=None):
    from PIL import Image

    _register_optional()
    fmt = fmt or Path(path).suffix.lower().lstrip(".")
    fmt = "dng" if fmt == "dns" else fmt
    if fmt == "svg":
        import resvg_py
        # No source directory is given to the renderer for linked assets.
        return Image.open(BytesIO(resvg_py.svg_to_bytes(svg_string=Path(path).read_text(encoding="utf-8-sig"))))
    if fmt in _RAW:
        import rawpy
        with rawpy.imread(path) as source:
            return Image.fromarray(source.postprocess())
    if fmt == "exr":
        from . import media
        result = media._run(["-i", path, "-frames:v", "1", "-c:v", "png", "-f", "image2pipe", "pipe:1"], timeout=30)
        media._check(result)
        return Image.open(BytesIO(result.stdout))
    return Image.open(path)


def inspect_source(path: str, fmt: str | None = None) -> dict:
    """Read the decoder header without loading image pixels."""
    with _open(path, fmt) as source:
        return {
            "dimensions": source.size,
            "png_depth": png_depth(path) if source.format == "PNG" else None,
            "animated": getattr(source, "is_animated", False),
        }


def preview(path: str, bounds: tuple[int, int]):
    """Read a thumbnail and the characteristics shown before conversion."""
    from PIL import Image, ImageOps

    with _open(path) as source:
        details = (
            source.size,
            getattr(source, "n_frames", 1),
            png_depth(path) if source.format == "PNG" else None,
        )
        source.thumbnail(bounds, Image.Resampling.LANCZOS)
        return ImageOps.exif_transpose(source).convert("RGBA"), details


def convert(src: str, dst: str, src_fmt: str, dst_fmt: str, *, preset=None) -> None:
    from PIL import Image, ImageChops, ImageSequence

    with _open(src, src_fmt) as source:
        if dst_fmt == "webp" and source.format == "PNG":
            if (png_depth(src) or 0) > 8:
                raise ValueError(Message("WebP cannot preserve the color depth of a 16-bit PNG."))
            if getattr(source, "n_frames", 1) > 1:
                raise ValueError(Message("Lossless WebP conversion does not support animated PNGs."))
            if preset and preset.image_quality is not None:
                save_image(source, dst, dst_fmt, preset)
                return
            pixels = _transform(source.convert("RGBA"), preset)
            metadata = {key: source.info[key] for key in ("icc_profile", "exif", "xmp")
                        if key in source.info}
            pixels.save(dst, format="WEBP", lossless=True, exact=True, **metadata)
            with Image.open(dst) as result:
                if pixels.size != result.size or ImageChops.difference(
                    pixels, result.convert("RGBA")
                ).getbbox(alpha_only=False):
                    raise ValueError(Message("WebP pixel verification failed."))
            return

        if preset and dst_fmt == src_fmt == "gif" and getattr(source, "is_animated", False):
            frames = []
            durations = []
            for frame in ImageSequence.Iterator(source):
                frames.append(_transform(frame.convert("RGBA"), preset))
                durations.append(frame.info.get("duration", 100))
            frames[0].save(dst, format="GIF", save_all=True, append_images=frames[1:],
                           duration=durations, loop=source.info.get("loop", 0), disposal=2)
            return
        save_image(source, dst, dst_fmt, preset)


def _transform(image, preset):
    if not preset:
        return image
    from PIL import Image, ImageOps

    if preset.rotate:
        image = ImageOps.exif_transpose(image).rotate(-preset.rotate, expand=True)
    ratio = preset.scale / 100
    if preset.height:
        ratio = min(ratio, preset.height / image.height)
    if preset.width:
        ratio = min(ratio, preset.width / image.width)
    size = tuple(max(1, round(axis * ratio)) for axis in image.size)
    if preset.power_of_two:
        size = tuple(1 << (axis.bit_length() - 1) for axis in size)
    if size != image.size:
        image = image.resize(size, Image.Resampling.LANCZOS)
    return image


def save_image(img, dst: str, dst_fmt: str, preset=None) -> None:
    from PIL import Image

    save_fmt = _SAVE_FORMAT.get(dst_fmt, dst_fmt.upper())
    params = {}
    img = _transform(img, preset)
    quality = preset.image_quality if preset else None

    if dst_fmt in ("jpg", "bmp", "pdf", "ppm", "tga"):
        # Flatten transparent pixels onto white for these formats.
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg
        else:
            img = img.convert("RGB")

    if dst_fmt in {"jpg", "webp", "avif"}:
        params["quality"] = quality or (85 if dst_fmt == "avif" else 95)
    elif dst_fmt == "png" and quality is not None:
        params["compress_level"] = round(quality * 9 / 100)
    elif dst_fmt == "ico":
        # Include the usual Windows icon dimensions.
        img = img.convert("RGBA")
        sizes = (16, 32, 48, 64, 128, 256)
        side = max(16, min(256, max(img.size)))
        img.thumbnail((side, side), Image.Resampling.LANCZOS)
        canvas = Image.new("RGBA", (side, side))
        canvas.paste(img, ((side - img.width) // 2, (side - img.height) // 2))
        img = canvas
        params["sizes"] = [(size, size) for size in sizes if size <= side]

    img.save(dst, format=save_fmt, **params)

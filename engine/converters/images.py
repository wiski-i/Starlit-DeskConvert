"""Görsel dönüştürücü (Pillow).

Desteklenen çıktılar görsellerin yanı sıra PDF'i de içerir.
"""
from __future__ import annotations

from functools import cache

from i18n import Message

CATEGORY = "image"

# Bu kategoride üretebileceğimiz çıktı formatları
OUTPUTS = ["png", "jpg", "webp", "bmp", "gif", "tiff", "ico", "tga", "ppm", "pdf"]

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


def inspect_source(path: str) -> dict:
    """Read the decoder header without loading image pixels."""
    from PIL import Image

    _register_optional()
    with Image.open(path) as source:
        return {
            "dimensions": source.size,
            "png_depth": png_depth(path) if source.format == "PNG" else None,
            "animated": getattr(source, "is_animated", False),
        }


def preview(path: str, bounds: tuple[int, int]):
    """Read a thumbnail and the characteristics shown before conversion."""
    from PIL import Image, ImageOps

    _register_optional()
    with Image.open(path) as source:
        details = (
            source.size,
            getattr(source, "n_frames", 1),
            png_depth(path) if source.format == "PNG" else None,
        )
        source.thumbnail(bounds, Image.Resampling.LANCZOS)
        return ImageOps.exif_transpose(source).convert("RGBA"), details


def convert(src: str, dst: str, src_fmt: str, dst_fmt: str) -> None:
    from PIL import Image, ImageChops

    _register_optional()
    with Image.open(src) as source:
        if dst_fmt == "webp" and source.format == "PNG":
            if (png_depth(src) or 0) > 8:
                raise ValueError(Message("WebP cannot preserve the color depth of a 16-bit PNG."))
            if getattr(source, "n_frames", 1) > 1:
                raise ValueError(Message("Lossless WebP conversion does not support animated PNGs."))
            pixels = source.convert("RGBA")
            metadata = {key: source.info[key] for key in ("icc_profile", "exif", "xmp")
                        if key in source.info}
            pixels.save(dst, format="WEBP", lossless=True, exact=True, **metadata)
            with Image.open(dst) as result:
                if pixels.size != result.size or ImageChops.difference(
                    pixels, result.convert("RGBA")
                ).getbbox(alpha_only=False):
                    raise ValueError(Message("WebP pixel verification failed."))
            return

        _save_image(source, dst, dst_fmt)


def _save_image(img, dst: str, dst_fmt: str) -> None:
    from PIL import Image

    save_fmt = _SAVE_FORMAT.get(dst_fmt, dst_fmt.upper())
    params = {}

    if dst_fmt in ("jpg", "bmp", "pdf", "ppm", "tga"):
        # Flatten transparent pixels onto white for these formats.
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            bg = Image.new("RGB", img.size, (255, 255, 255))
            bg.paste(img, mask=img.split()[-1])
            img = bg
        else:
            img = img.convert("RGB")

    if dst_fmt == "jpg":
        params["quality"] = 95
    elif dst_fmt == "webp":
        params["quality"] = 95
    elif dst_fmt == "ico":
        # Include the usual Windows icon dimensions.
        img = img.convert("RGBA")
        params["sizes"] = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]

    img.save(dst, format=save_fmt, **params)

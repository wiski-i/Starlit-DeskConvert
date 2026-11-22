"""Belge dönüştürücü (paketlenmiş pandoc).

pypandoc-binary, pandoc'u kendi içinde getirir.
"""
from __future__ import annotations

from codecs import getincrementaldecoder
from string import punctuation

from i18n import Message

CATEGORY = "document"

OUTPUTS = ["docx", "odt", "rtf", "html", "md", "txt", "epub", "rst", "tex"]

# Kanonik format -> pandoc format adı
_PANDOC_IN = {
    "docx": "docx", "odt": "odt", "rtf": "rtf", "html": "html",
    "md": "markdown", "markdown": "markdown", "txt": "markdown",
    "epub": "epub", "tex": "latex", "rst": "rst", "org": "org",
}
_PANDOC_OUT = {
    "docx": "docx", "odt": "odt", "rtf": "rtf", "html": "html",
    "md": "markdown", "markdown": "markdown", "txt": "plain",
    "epub": "epub", "tex": "latex", "rst": "rst",
}
INPUTS = frozenset(_PANDOC_IN)
_PLAIN_ESCAPES = str.maketrans({character: f"\\{character}" for character in punctuation})


def available():
    try:
        import pypandoc
        try:
            pypandoc.get_pandoc_version()
            return True, ""
        except OSError:
            return False, Message("{component} is missing. Install {package}.", component="Pandoc", package="pypandoc-binary")
    except ImportError:
        return False, Message("{component} is missing. Install {package}.", component="pypandoc", package="pypandoc-binary")


def preview(src: str, src_fmt: str) -> str:
    import pypandoc

    return pypandoc.convert_file(src, "plain", format=_PANDOC_IN[src_fmt], extra_args=["--sandbox"])


def read_plain_text(src: str, limit: int = -1) -> str:
    with open(src, "rb") as file:
        raw = file.read(limit)
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", "replace")
    try:
        return getincrementaldecoder("utf-8-sig")().decode(raw, final=limit < 0)
    except UnicodeDecodeError:
        return raw.decode("cp1254", "replace")


def convert(src: str, dst: str, src_fmt: str, dst_fmt: str) -> None:
    import pypandoc
    in_fmt = _PANDOC_IN.get(src_fmt, src_fmt)
    out_fmt = _PANDOC_OUT.get(dst_fmt, dst_fmt)
    extra = ["--sandbox"]
    if dst_fmt in ("docx", "odt", "epub"):
        extra += ["--standalone"]
    if dst_fmt == "html":
        extra += ["--standalone", "--embed-resources"]
    if src_fmt == "txt":
        text = read_plain_text(src).replace("\r\n", "\n").replace("\r", "\n")
        paragraphs = text.split("\n\n")
        escaped = "\n\n".join(
            "\\\n".join(line.translate(_PLAIN_ESCAPES) for line in paragraph.splitlines())
            for paragraph in paragraphs
        )
        pypandoc.convert_text(escaped, out_fmt, format="commonmark", outputfile=dst, extra_args=extra)
    else:
        pypandoc.convert_file(src, out_fmt, format=in_fmt, outputfile=dst, extra_args=extra)

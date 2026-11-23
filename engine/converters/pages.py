"""Render PDF pages and export Office documents through the installed applications."""
from __future__ import annotations

import os
import tempfile
import threading
from functools import cache
from importlib.util import find_spec
from pathlib import Path

from i18n import Message

from . import images

OFFICE = {
    "doc": "Word", "docx": "Word", "odt": "Word",
    "xls": "Excel", "xlsx": "Excel", "ods": "Excel",
    "ppt": "PowerPoint", "pptx": "PowerPoint", "odp": "PowerPoint",
}
INPUTS = OFFICE.keys() | {"pdf"}
OUTPUTS = ("png", "jpg", "ico", "webp", "avif")
_pdf_lock = threading.Lock()


@cache
def available(fmt: str) -> bool:
    if fmt == "pdf":
        return find_spec("pypdfium2") is not None
    if os.name != "nt" or find_spec("win32com") is None:
        return False
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, f"{OFFICE[fmt]}.Application\\CLSID"):
            return True
    except OSError:
        return False


def export_office(src: str, dst: str, fmt: str) -> None:
    import pythoncom
    from win32com.client import DispatchEx

    pythoncom.CoInitialize()
    app = document = None
    program = OFFICE[fmt]
    old_settings = {}
    try:
        app = DispatchEx(f"{program}.Application")
        settings = {"AutomationSecurity": 3}
        if program == "Excel":
            settings.update(DisplayAlerts=False, EnableEvents=False, AskToUpdateLinks=False)
        elif program == "Word":
            settings.update(DisplayAlerts=0)
        for name, value in settings.items():
            old_settings[name] = getattr(app, name)
            setattr(app, name, value)
        if program == "Word":
            document = app.Documents.Open(src, ConfirmConversions=False, ReadOnly=True,
                                          AddToRecentFiles=False, Visible=False, OpenAndRepair=False)
            document.ExportAsFixedFormat(dst, 17)
        elif program == "Excel":
            document = app.Workbooks.Open(src, UpdateLinks=0, ReadOnly=True,
                                          IgnoreReadOnlyRecommended=True, AddToMru=False)
            document.ExportAsFixedFormat(0, dst)
        else:
            document = app.Presentations.Open(src, ReadOnly=-1, Untitled=0, WithWindow=0)
            # SaveAs supports late binding without PowerPoint's complex optional default arguments.
            document.SaveAs(dst, 32)
    finally:
        try:
            if document is not None:
                document.Close() if program == "PowerPoint" else document.Close(False)
        finally:
            try:
                if app is not None:
                    for name, value in old_settings.items():
                        setattr(app, name, value)
                    # PowerPoint can share a running application. Never quit the user's instance.
                    if program != "PowerPoint":
                        app.Quit()
            finally:
                pythoncom.CoUninitialize()


def convert(src: str, staging: Path, src_fmt: str, dst_fmt: str, preset) -> list[Path]:
    with tempfile.TemporaryDirectory() as scratch:
        pdf = src
        if src_fmt != "pdf":
            if not available(src_fmt):
                raise RuntimeError(Message("This conversion requires Microsoft {program}.", program=OFFICE[src_fmt]))
            pdf = str(staging / "output.pdf") if dst_fmt == "pdf" else str(Path(scratch) / "document.pdf")
            export_office(src, pdf, src_fmt)
            if dst_fmt == "pdf":
                return [Path(pdf)]

        import pypdfium2 as pdfium

        outputs = []
        # PDFium's C API is not thread-safe, even across independent documents.
        with _pdf_lock, pdfium.PdfDocument(pdf) as document:
            for index in range(len(document)):
                page = document[index]
                try:
                    bitmap = page.render(scale=2)
                    try:
                        output = staging / f"page-{index + 1}.{dst_fmt}"
                        images.save_image(bitmap.to_pil(), output, dst_fmt, preset)
                        outputs.append(output)
                    finally:
                        bitmap.close()
                finally:
                    page.close()
        return outputs

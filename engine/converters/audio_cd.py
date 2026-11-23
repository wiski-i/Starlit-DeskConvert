"""Read an audio track from the Windows optical drive that owns its CDA shortcut."""
from __future__ import annotations

import ctypes
import os
import struct
import wave
from ctypes import wintypes
from pathlib import Path

from i18n import Message


def _track_sectors(toc: bytes, track: int) -> tuple[int, int]:
    entries = [toc[index:index + 8] for index in range(4, len(toc) - 7, 8)]
    for current, following in zip(entries, entries[1:]):
        if current[2] == track and not current[1] & 4:
            def lba(entry):
                minute, second, frame = entry[5:8]
                return (minute * 60 + second) * 75 + frame - 150

            start, end = lba(current), lba(following)
            if 0 <= start < end:
                return start, end
    raise ValueError(Message("The audio CD track could not be found."))


def extract(src: str, dst: str, *, limit_seconds: int = 0) -> None:
    if os.name != "nt":
        raise OSError(Message("CDA conversion requires a Windows optical drive."))
    root = Path(src).anchor
    if not root or ctypes.windll.kernel32.GetDriveTypeW(root) != 5:
        raise OSError(Message("Open the CDA track directly from the inserted audio CD."))
    with open(src, "rb") as file:
        header = file.read(24)
    if len(header) < 24 or header[:4] != b"RIFF" or header[8:16] != b"CDDAfmt ":
        raise ValueError(Message("The audio CD track could not be found."))
    track = struct.unpack_from("<H", header, 22)[0]

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    create = kernel.CreateFileW
    create.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD, ctypes.c_void_p,
                       wintypes.DWORD, wintypes.DWORD, wintypes.HANDLE)
    create.restype = wintypes.HANDLE
    ioctl = kernel.DeviceIoControl
    ioctl.argtypes = (wintypes.HANDLE, wintypes.DWORD, ctypes.c_void_p, wintypes.DWORD,
                      ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.c_void_p)
    kernel.CloseHandle.argtypes = (wintypes.HANDLE,)
    handle = create("\\\\.\\" + root[:2], 0x80000000, 3, None, 3, 0, None)
    if handle == ctypes.c_void_p(-1).value:
        raise ctypes.WinError(ctypes.get_last_error())

    def read(code, length, request=b""):
        buffer = ctypes.create_string_buffer(length)
        returned = wintypes.DWORD()
        if not ioctl(handle, code, request or None, len(request), buffer, length, ctypes.byref(returned), None):
            raise ctypes.WinError(ctypes.get_last_error())
        return buffer.raw[:returned.value]

    try:
        start, end = _track_sectors(read(0x24000, 804), track)  # IOCTL_CDROM_READ_TOC
        if limit_seconds:
            end = min(end, start + limit_seconds * 75)
        with wave.open(dst, "wb") as output:
            output.setparams((2, 2, 44100, 0, "NONE", "not compressed"))
            for sector in range(start, end, 16):
                count = min(end - sector, 16)
                request = struct.pack("<qII", sector * 2048, count, 2)  # RAW_READ_INFO, CDDA
                data = read(0x2403E, count * 2352, request)  # IOCTL_CDROM_RAW_READ
                if len(data) != count * 2352:
                    raise OSError(Message("The optical drive returned an incomplete audio sector."))
                output.writeframesraw(data)
    finally:
        kernel.CloseHandle(handle)

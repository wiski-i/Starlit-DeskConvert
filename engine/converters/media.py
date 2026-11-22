"""Ses ve video dönüştürücü (paketlenmiş ffmpeg).

imageio-ffmpeg, ffmpeg binary'sini kendi içinde getirir; sistemde
ffmpeg kurulu olmasa bile çalışır.
"""
from __future__ import annotations

import subprocess

from i18n import Message

_NO_CONSOLE = getattr(subprocess, "CREATE_NO_WINDOW", 0)

CATEGORY = "media"  # hem audio hem video

AUDIO_OUTPUTS = ["mp3", "wav", "flac", "aac", "ogg", "m4a", "opus", "aiff", "wma"]
VIDEO_OUTPUTS = ["mp4", "mkv", "avi", "mov", "webm", "gif", "flv"]
# Video kaynaklardan ses çıkarma hedefleri
EXTRACT_AUDIO = ["mp3", "wav", "aac", "flac"]


def ffmpeg_exe():
    import imageio_ffmpeg
    return imageio_ffmpeg.get_ffmpeg_exe()


def available():
    try:
        path = ffmpeg_exe()
        return bool(path), "" if path else Message("FFmpeg was not found.")
    except (ImportError, RuntimeError):
        return False, Message(
            "{component} is missing. Install {package}.", component="FFmpeg", package="imageio-ffmpeg",
        )


def outputs_for(category: str):
    """Kaynağın kategorisine göre olası hedefler."""
    if category == "audio":
        return list(AUDIO_OUTPUTS)
    if category == "video":
        # Video -> başka video + ses çıkarma
        return list(VIDEO_OUTPUTS) + [a for a in EXTRACT_AUDIO]
    return []


# Belirli formatlar için ek/özel kodlama argümanları
_EXTRA = {
    "mp3": ["-codec:a", "libmp3lame", "-q:a", "2"],
    "aac": ["-codec:a", "aac", "-b:a", "192k"],
    "m4a": ["-codec:a", "aac", "-b:a", "192k"],
    "ogg": ["-codec:a", "libvorbis", "-q:a", "5"],
    "opus": ["-codec:a", "libopus", "-b:a", "160k"],
    "flac": ["-codec:a", "flac"],
    "wav": ["-codec:a", "pcm_s16le"],
    "webm": ["-c:v", "libvpx-vp9", "-b:v", "0", "-crf", "32", "-c:a", "libopus"],
    "mp4": ["-c:v", "libx264", "-preset", "medium", "-crf", "23", "-c:a", "aac"],
}

_AUDIO_TARGETS = set(AUDIO_OUTPUTS)
_COPY_TARGETS = {"mp4", "mkv", "mov", "webm"}
_GIF_FILTER = (
    "[0:v:0]fps=12,scale=w='min(480,iw)':h=-1:flags=lanczos,split[first][second];"
    "[first]palettegen=stats_mode=diff[palette];[second][palette]paletteuse=dither=sierra2_4a"
)


def _command(args: list[str]) -> list[str]:
    return [
        ffmpeg_exe(), "-hide_banner", "-loglevel", "error", "-nostdin",
        "-protocol_whitelist", "file,pipe", *args,
    ]


def _run(args: list[str], *, timeout: float | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        _command(args), capture_output=True, creationflags=_NO_CONSOLE, timeout=timeout,
    )


def _check(result: subprocess.CompletedProcess) -> None:
    if result.returncode:
        tail = result.stderr.decode("utf-8", "replace").strip()[-700:]
        raise RuntimeError(f"FFmpeg: {tail}")


def preview(path: str, width: int) -> bytes:
    result = _run([
        "-i", path, "-map", "0:v:0", "-frames:v", "1", "-vf",
        f"scale=w='min({width},iw)':h=-1", "-f", "image2pipe", "-c:v", "png", "pipe:1",
    ], timeout=12)
    _check(result)
    return result.stdout


def preview_video(path: str, width: int, height: int, fps: int) -> subprocess.Popen:
    filter_chain = (
        f"fps={fps},scale={width}:{height}:force_original_aspect_ratio=decrease,"
        f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=0x19121B"
    )
    return subprocess.Popen(
        _command([
            "-i", path, "-t", "60", "-map", "0:v:0", "-vf", filter_chain,
            "-pix_fmt", "rgb24", "-an", "-f", "rawvideo", "pipe:1",
        ]),
        stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, creationflags=_NO_CONSOLE,
    )


def preview_audio(path: str, output: str) -> None:
    _check(_run([
        "-y", "-i", path, "-map", "0:a:0", "-vn", "-t", "45",
        "-c:a", "pcm_s16le", "-ar", "44100", "-ac", "2", output,
    ]))


def verify(path: str, target: str) -> None:
    stream = "0:a:0" if target in _AUDIO_TARGETS else "0:v:0"
    _check(_run(["-xerror", "-i", path, "-map", stream, "-t", "1", "-f", "null", "-"]))


def convert(src: str, dst: str, src_fmt: str, dst_fmt: str, on_progress=None) -> None:
    cmd = ["-y", "-i", src]

    if dst_fmt in _COPY_TARGETS and src_fmt in VIDEO_OUTPUTS + ["wmv", "mpg", "3gp", "ts", "ogv"]:
        if _run([*cmd, "-map", "0", "-c", "copy", dst]).returncode == 0:
            return

    if dst_fmt == "gif":
        cmd += ["-filter_complex", _GIF_FILTER, "-an", "-sn", "-dn", "-loop", "0"]
    elif dst_fmt in _AUDIO_TARGETS:
        # Sadece ses (video kaynaktan ses çıkarma dahil)
        cmd += ["-vn"]
        cmd += _EXTRA.get(dst_fmt, [])
    else:
        cmd += _EXTRA.get(dst_fmt, [])

    _check(_run([*cmd, dst]))

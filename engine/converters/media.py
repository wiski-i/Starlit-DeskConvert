"""Ses ve video dönüştürücü (paketlenmiş ffmpeg).

imageio-ffmpeg, ffmpeg binary'sini kendi içinde getirir; sistemde
ffmpeg kurulu olmasa bile çalışır.
"""
from __future__ import annotations

import shlex
import subprocess
import tempfile
from pathlib import Path

from i18n import Message

_NO_CONSOLE = getattr(subprocess, "CREATE_NO_WINDOW", 0)

CATEGORY = "media"  # hem audio hem video

AUDIO_OUTPUTS = ["mp3", "wav", "flac", "aac", "ogg", "m4a", "opus", "aiff", "wma"]
VIDEO_OUTPUTS = ["mp4", "mkv", "avi", "mov", "webm", "gif", "flv", "ogv"]
# Video kaynaklardan ses çıkarma hedefleri
EXTRACT_AUDIO = ["mp3", "wav", "aac", "flac", "ogg"]


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
    "mkv": ["-c:v", "libx264", "-preset", "medium", "-crf", "23", "-c:a", "aac"],
    "avi": ["-c:v", "mpeg4", "-vtag", "XVID", "-q:v", "4", "-c:a", "libmp3lame"],
    "ogv": ["-c:v", "libtheora", "-q:v", "7", "-c:a", "libvorbis"],
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
    if Path(path).suffix.lower() == ".cda":
        from . import audio_cd
        with tempfile.TemporaryDirectory() as folder:
            wav = str(Path(folder) / "track.wav")
            audio_cd.extract(path, wav, limit_seconds=45)
            preview_audio(wav, output)
        return
    _check(_run([
        "-y", "-i", path, "-map", "0:a:0", "-vn", "-t", "45",
        "-c:a", "pcm_s16le", "-ar", "44100", "-ac", "2", output,
    ]))


def verify(path: str, target: str) -> None:
    stream = "0:a:0" if target in _AUDIO_TARGETS else "0:v:0"
    _check(_run(["-xerror", "-i", path, "-map", stream, "-t", "1", "-f", "null", "-"]))


def convert(src: str, dst: str, src_fmt: str, dst_fmt: str, on_progress=None, *, preset=None) -> None:
    if src_fmt == "cda":
        from . import audio_cd
        with tempfile.TemporaryDirectory() as folder:
            wav = str(Path(folder) / "track.wav")
            audio_cd.extract(src, wav)
            convert(wav, dst, "wav", dst_fmt, on_progress, preset=preset)
        return
    if preset is not None:
        _convert_preset(src, dst, dst_fmt, preset)
        return
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


_ADVANCED_OPTIONS = {
    "-c:a", "-c:v", "-codec:a", "-codec:v", "-b:a", "-b:v", "-q:a", "-q:v", "-crf",
    "-preset", "-profile:v", "-level:v", "-pix_fmt", "-r", "-ar", "-ac", "-t",
    "-movflags", "-maxrate", "-minrate", "-bufsize", "-compression_level", "-threads",
    "-cpu-used", "-g", "-tune", "-sample_fmt", "-metadata", "-map_metadata",
    "-deadline", "-aq-mode", "-quality", "-strict", "-colorspace", "-color_primaries",
    "-color_trc", "-color_range", "-cutoff", "-vbr",
    "-filter:a", "-af", "-filter:v", "-vf",
}
_SAFE_FILTERS = {
    "atempo", "asetrate", "aresample", "volume", "aformat", "highpass", "lowpass",
    "scale", "fps", "format", "crop", "pad", "hflip", "vflip", "transpose", "setsar",
}


def extra_options(text: str) -> list[str]:
    args = shlex.split(text)
    if len(args) % 2:
        raise ValueError("Enter FFmpeg options as option/value pairs.")
    for option, value in zip(args[::2], args[1::2]):
        if option not in _ADVANCED_OPTIONS:
            raise ValueError(f"Unsupported FFmpeg option: {option}")
        if option in {"-vf", "-af", "-filter:a", "-filter:v"}:
            for filter_spec in value.split(","):
                name, _, arguments = filter_spec.partition("=")
                if name not in _SAFE_FILTERS or any(char in arguments for char in ";[]@/\\\\"):
                    raise ValueError(f"Unsupported FFmpeg filter: {filter_spec}")
    return args


def _video_filters(preset) -> list[str]:
    filters = []
    if preset.rotate == -90:
        filters.append("transpose=cclock")
    elif preset.rotate == 90:
        filters.append("transpose=clock")
    elif preset.rotate == 180:
        filters.extend(("hflip", "vflip"))
    if preset.scale != 100:
        scale = preset.scale / 100
        filters.append(f"scale=max(2\\,trunc(iw*{scale}/2)*2):max(2\\,trunc(ih*{scale}/2)*2)")
    if preset.height:
        filters.append(f"scale=-2:max(2\\,trunc(min({preset.height}\\,ih)/2)*2)")
    if preset.width:
        filters.append(f"scale=max(2\\,trunc(min({preset.width}\\,iw)/2)*2):-2")
    if preset.tempo != 1:
        filters.append(f"setpts=PTS/{preset.tempo:.8f}")
    if preset.fps:
        filters.append(f"fps={preset.fps}")
    return filters


def _audio_filters(preset) -> list[str]:
    pitch = 2 ** (preset.pitch / 12)
    tempo = preset.tempo / pitch
    filters = []
    if preset.pitch:
        filters.extend(("aresample=48000", f"asetrate={round(48000 * pitch)}", "aresample=48000"))
    while tempo > 2:
        filters.append("atempo=2")
        tempo /= 2
    while tempo < 0.5:
        filters.append("atempo=0.5")
        tempo *= 2
    if abs(tempo - 1) > 0.000001:
        filters.append(f"atempo={tempo:.8f}")
    return filters


def _set_option(args: list[str], option: str, value: str) -> None:
    if option in args:
        args[args.index(option) + 1] = value
    else:
        args.extend((option, value))


def _convert_preset(src: str, dst: str, fmt: str, preset) -> None:
    cmd = ["-y", "-xerror", "-i", src, "-sn", "-dn"]
    audio = _audio_filters(preset)
    if fmt == "gif":
        filters = _video_filters(preset)
        if not preset.fps:
            filters.append("fps=15")
        if not (preset.scale != 100 or preset.height or preset.width):
            filters.append("scale=w='min(720,iw)':h=-1:flags=lanczos")
        chain = (f"[0:v:0]{','.join(filters)},split[first][second];"
                 "[first]palettegen=stats_mode=diff[p];[second][p]paletteuse=dither=sierra2_4a")
        _check(_run([*cmd, "-filter_complex", chain, "-an", "-loop", "0", dst]))
        return

    options = list(_EXTRA.get(fmt, []))
    if fmt in _AUDIO_TARGETS:
        cmd.extend(("-map", "0:a:0", "-vn"))
    else:
        cmd.extend(("-map", "0:V:0"))
        cmd.extend(("-map", "0:a:0?") if preset.audio_enabled else ("-an",))
        video = _video_filters(preset)
        if fmt in {"mp4", "mkv", "avi", "webm", "ogv", "mov"}:
            video.append("pad=ceil(iw/2)*2:ceil(ih/2)*2")
            _set_option(options, "-pix_fmt", "yuv420p")
        if video:
            cmd.extend(("-vf", ",".join(video)))
    if audio and (fmt in _AUDIO_TARGETS or preset.audio_enabled):
        cmd.extend(("-af", ",".join(audio)))
    if preset.audio_quality is not None:
        quality = preset.audio_quality
        if fmt == "ogg" or fmt == "ogv":
            _set_option(options, "-q:a", str(round(-1 + quality * 11 / 100, 2)))
        elif fmt in {"mp3", "avi"}:
            _set_option(options, "-q:a", str(round(9 - quality * 9 / 100)))
        elif fmt not in {"wav", "flac", "aiff"}:
            _set_option(options, "-b:a", f"{round(48 + 2.4 * quality)}k")
    if fmt in {"mp4", "mkv"}:
        if preset.encoder:
            options = [option for pair in zip(options[::2], options[1::2])
                       if pair[0] not in {"-preset", "-crf"} for option in pair]
            _set_option(options, "-c:v", preset.encoder)
            if preset.video_quality is not None:
                option = {"h264_nvenc": "-cq", "h264_qsv": "-global_quality", "h264_amf": "-qp_i"}
                value = str(round(48 - preset.video_quality * 0.45))
                _set_option(options, option[preset.encoder], value)
                if preset.encoder == "h264_amf":
                    _set_option(options, "-rc", "cqp")
                    _set_option(options, "-qp_p", value)
        else:
            if preset.speed:
                _set_option(options, "-preset", preset.speed)
            if preset.video_quality is not None:
                _set_option(options, "-crf", str(round(48 - preset.video_quality * 0.45)))
    elif preset.video_quality is not None:
        quality = preset.video_quality
        if fmt == "webm":
            _set_option(options, "-crf", str(round(60 - 0.55 * quality)))
        elif fmt in {"avi", "ogv"}:
            _set_option(options, "-q:v", str(round(30 - 0.28 * quality) if fmt == "avi" else round(quality / 10)))
    if preset.channels:
        _set_option(options, "-ac", str(preset.channels))
    if preset.sample_rate:
        _set_option(options, "-ar", str(preset.sample_rate))
    if preset.bitrate and fmt not in {"wav", "flac", "aiff"}:
        if "-q:a" in options:
            del options[options.index("-q:a"):options.index("-q:a") + 2]
        _set_option(options, "-b:a", f"{preset.bitrate}k")
    if fmt == "mp3" and preset.audio_mode == "mp3-vbr":
        if "-b:a" in options:
            del options[options.index("-b:a"):options.index("-b:a") + 2]
        _set_option(options, "-q:a", str(round(9 - (preset.audio_quality or 80) * 9 / 100)))
    elif fmt == "mp3" and preset.audio_mode == "mp3-cbr" and not preset.bitrate:
        if "-q:a" in options:
            del options[options.index("-q:a"):options.index("-q:a") + 2]
        _set_option(options, "-b:a", "192k")
    elif fmt == "wav" and preset.audio_mode.startswith("wav-"):
        codecs = {"wav-16": "pcm_s16le", "wav-24": "pcm_s24le",
                  "wav-32": "pcm_s32le", "wav-float": "pcm_f32le"}
        _set_option(options, "-codec:a", codecs[preset.audio_mode])
    if fmt == "mp4":
        options.extend(("-movflags", "+faststart"))
    options.extend(extra_options(preset.ffmpeg_options))
    _check(_run([*cmd, *options, dst]))

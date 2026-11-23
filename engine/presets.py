"""Shared preset definitions for the desktop app and File Explorer."""
from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from i18n import tr

from . import detect, registry

SETTINGS_DIR = Path(os.getenv("LOCALAPPDATA") or Path.home() / ".config") / "DeskConvert"
PRESET_FILE = SETTINGS_DIR / "presets.json"
PREFERENCES_FILE = SETTINGS_DIR / "preferences.json"


@dataclass(frozen=True)
class Preferences:
    parallel: int = 1
    copy_outputs: bool = False
    check_updates: bool = False

    def __post_init__(self):
        if type(self.parallel) is not int or not 1 <= self.parallel <= 8:
            raise ValueError("Choose between 1 and 8 simultaneous conversions.")
        if type(self.copy_outputs) is not bool or type(self.check_updates) is not bool:
            raise ValueError("Invalid clipboard preference.")

IMAGE_TARGETS = ("png", "jpg", "ico", "webp", "avif")
VIDEO_TARGETS = ("mkv", "mp4", "webm", "ogv", "avi", "gif")
AUDIO_TARGETS = ("ogg", "flac", "wav", "mp3", "aac")
TARGETS = VIDEO_TARGETS + AUDIO_TARGETS + IMAGE_TARGETS + ("pdf", "same")
SPEEDS = ("", "ultrafast", "veryfast", "fast", "medium", "slow", "veryslow")
ENCODERS = ("", "h264_nvenc", "h264_qsv", "h264_amf")
ACTIONS = ("keep", "archive", "recycle", "delete")


@dataclass(frozen=True)
class Preset:
    id: str
    name: str
    target: str
    group: str = ""
    inputs: tuple[str, ...] = ()
    scale: int = 100
    height: int = 0
    rotate: int = 0
    tempo: float = 1
    pitch: float = 0
    video_quality: int | None = None
    audio_quality: int | None = None
    image_quality: int | None = None
    speed: str = ""
    encoder: str = ""
    fps: int = 0
    audio_enabled: bool = True
    channels: int = 0
    sample_rate: int = 0
    bitrate: int = 0
    audio_mode: str = ""
    power_of_two: bool = False
    ffmpeg_options: str = ""
    width: int = 0
    template: str = ""
    action: str = "keep"
    enabled: bool = True
    builtin: bool = False

    def __post_init__(self):
        if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", self.id):
            raise ValueError("Invalid preset identifier.")
        if not 0 < len(self.name.strip()) <= 120 or len(self.group) > 120:
            raise ValueError("Enter a name of up to 120 characters.")
        if any(char in self.name + self.group for char in "\r\n\t\0"):
            raise ValueError("Names cannot contain tabs or line breaks.")
        if self.target not in TARGETS or self.action not in ACTIONS:
            raise ValueError("Invalid output format or source action.")
        if self.speed not in SPEEDS or self.encoder not in ENCODERS:
            raise ValueError("Invalid encoding speed or encoder.")
        if not 1 <= self.scale <= 400 or not 0 <= self.height <= 4320 or not 0 <= self.width <= 7680:
            raise ValueError("Scale must be 1–400%, height 0–4320 and width 0–7680.")
        if self.rotate not in (-90, 0, 90, 180) or not 0.25 <= self.tempo <= 4 or not -24 <= self.pitch <= 24:
            raise ValueError("Invalid rotation, tempo (0.25–4×) or pitch (−24 to +24 semitones).")
        if self.channels not in (0, 1, 2, 6, 8) or not 0 <= self.bitrate <= 1536:
            raise ValueError("Invalid audio channel count or bitrate.")
        if self.sample_rate not in (0, 8000, 16000, 22050, 32000, 44100, 48000, 96000):
            raise ValueError("Invalid audio sample rate.")
        if self.audio_mode not in ("", "mp3-vbr", "mp3-cbr", "wav-16", "wav-24", "wav-32", "wav-float"):
            raise ValueError("Invalid audio encoding mode.")
        if self.ffmpeg_options:
            registry.media.extra_options(self.ffmpeg_options)
        if not 0 <= self.fps <= 120:
            raise ValueError("Frame rate must be 0–120.")
        for quality in (self.video_quality, self.audio_quality, self.image_quality):
            if quality is not None and not 1 <= quality <= 100:
                raise ValueError("Quality must be 1–100.")
        if any(not re.fullmatch(r"[a-z0-9]{1,12}", ext) for ext in self.inputs):
            raise ValueError("Use file extensions separated by spaces or commas.")
        object.__setattr__(self, "inputs", tuple(dict.fromkeys(detect.canonical(ext) for ext in self.inputs)))

    @property
    def title(self):
        return tr(self.name) if self.builtin else self.name

    @property
    def menu_group(self):
        return tr(self.group) if self.builtin and self.group else self.group


def defaults() -> list[Preset]:
    formats = {"jpeg": "JPEG", "jpg": "JPEG"}
    presets = []

    def add(identifier, name, target, **settings):
        presets.append(Preset(identifier, name, target, builtin=True, **settings))

    for output in VIDEO_TARGETS + AUDIO_TARGETS + IMAGE_TARGETS + ("pdf",):
        name = formats.get(output, output.upper())
        add(f"to-{output}", name, output)
        if output == "mp4":
            add("mp4-small", "MP4 · Small file", output, video_quality=45, audio_quality=50)
        elif output == "gif":
            add("gif-small", "GIF · Small file", output, fps=10, scale=75, width=480)

    add("png-pages", "PNG · Numbered pages", "png", group="Document pages",
        inputs=tuple(sorted(registry.pages.INPUTS)), template="(p)(f) (n:i) of (n:c)")
    for extension, group, choices, folder in (
        ("vob", "DVD extraction", ("mp4", "mkv", "flac", "ogg", "mp3"), "DVD Extraction"),
        ("cda", "Audio CD extraction", ("flac", "ogg", "mp3"), "CDA Extraction"),
    ):
        for output in choices:
            location = "v" if output in VIDEO_TARGETS else "m"
            add(f"{extension}-{output}", output.upper(), output, group=group,
                inputs=(extension,), template=f"(p:{location}){folder}/(f)")

    for group_id, label, settings in (
        ("scale-75", "Scale to 75%", {"scale": 75}),
        ("scale-25", "Scale to 25%", {"scale": 25}),
        ("scale-720", "Resize to 720p", {"height": 720}),
        ("scale-1080", "Resize to 1080p", {"height": 1080}),
        ("rotate-left", "Rotate left", {"rotate": -90}),
        ("rotate-right", "Rotate right", {"rotate": 90}),
    ):
        for output in ("same", *VIDEO_TARGETS, *IMAGE_TARGETS):
            name = "Keep format" if output == "same" else formats.get(output, output.upper())
            add(f"{group_id}-{output}", name, output, group=label, **settings)
    for identifier, label, settings in (
        ("slower", "MP3 · Tempo 0.75×", {"tempo": 0.75}),
        ("faster", "MP3 · Tempo 1.25×", {"tempo": 1.25}),
        ("pitch-down", "MP3 · Pitch −1 semitone", {"pitch": -1}),
        ("pitch-up", "MP3 · Pitch +1 semitone", {"pitch": 1}),
    ):
        add(identifier, label, "mp3", group="Tempo and pitch", **settings)
        add(f"{identifier}-same", label.removeprefix("MP3 · "), "same", group="Tempo and pitch", **settings)
    return presets


def load(path: Path = PRESET_FILE) -> list[Preset]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return defaults()
    presets = [Preset(**dict(item, inputs=tuple(item.get("inputs", ())))) for item in data]
    if len({item.id for item in presets}) != len(presets):
        raise ValueError("Preset identifiers must be unique.")
    return presets


def load_preferences(path: Path = PREFERENCES_FILE) -> Preferences:
    try:
        return Preferences(**json.loads(path.read_text(encoding="utf-8")))
    except FileNotFoundError:
        return Preferences()


def save_preferences(preferences: Preferences, path: Path = PREFERENCES_FILE) -> None:
    _write_json(asdict(preferences), path)


def save(presets: list[Preset], path: Path = PRESET_FILE) -> None:
    _write_json([asdict(item) for item in presets], path)


def _write_json(data, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as file:
        temporary = Path(file.name)
        try:
            json.dump(data, file, ensure_ascii=False, indent=2)
            file.write("\n")
            file.close()
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def target_for(preset: Preset, info: dict, *, check_source: bool = True) -> dict | None:
    category, fmt = info.get("category"), info.get("format")
    if (not preset.enabled or not fmt or info.get("engine_ok") is False
            or (preset.inputs and info.get("ext", fmt) not in preset.inputs)):
        return None
    visual = preset.scale != 100 or preset.height or preset.width or preset.rotate or preset.power_of_two
    sound = preset.tempo != 1 or preset.pitch or preset.channels or preset.sample_rate or preset.bitrate
    if preset.group == "Tempo and pitch" and preset.builtin and category not in {"audio", "video"}:
        return None
    if (visual and category not in {"image", "video", "document", "data"}
            or sound and category not in {"audio", "video"}):
        return None
    key = fmt if preset.target == "same" else preset.target
    if (visual and (key in registry.media.AUDIO_OUTPUTS or key == "pdf")
            or sound and key == "gif"):
        return None
    for route in registry.targets(info, include_self=True, check_source=check_source):
        if route["key"] != key:
            continue
        media_route = category in {"audio", "video"} or route.get("engine") == "media"
        if preset.ffmpeg_options and (not media_route or key == "gif"):
            return None
        if preset.power_of_two and media_route:
            return None
        return {**route, "preset": preset}
    return None


def applicable_extensions(preset: Preset) -> tuple[str, ...]:
    extensions = sorted(detect.FORMAT_CATEGORY.keys() | detect.ALIASES.keys())
    return tuple(ext for ext in extensions
                 if target_for(preset, {
                     "format": detect.canonical(ext), "ext": detect.canonical(ext),
                     "category": detect.FORMAT_CATEGORY.get(detect.canonical(ext)),
                 }, check_source=False))

"""Local file previews displayed in a themed child window."""

from __future__ import annotations

import os
import subprocess
import sys
import tarfile
import tempfile
import threading
import zipfile
from io import BytesIO
from itertools import islice
from pathlib import Path
from queue import Empty, Full, Queue, SimpleQueue
from time import perf_counter

import customtkinter as ctk
from PIL import Image, ImageOps

from engine.converters import documents, images, media
from i18n import tr
from theme import (
    ACCENT, ACCENT_HOVER, BG, BORDER_H, PANEL, PANEL_2, SUB, SURFACE, SURFACE_H,
    TEXT, animations_enabled, font,
)

_TEXT_FORMATS = {"txt", "md", "rst", "tex", "html", "rtf", "org", "csv", "tsv", "json", "xml", "yaml", "svg"}
_VIDEO_SIZE = (640, 360)
_VIDEO_RATE = 15


def _text_preview(path: str, fmt: str) -> str:
    if fmt in _TEXT_FORMATS:
        return documents.read_plain_text(path, 24_000)
    if fmt in {"docx", "odt", "epub"}:
        return documents.preview(path, fmt)[:24_000]
    if fmt in {"xlsx", "xls", "ods", "parquet"}:
        from engine.converters.data import preview

        return preview(path, fmt)[:24_000]
    if fmt == "zip":
        with zipfile.ZipFile(path) as archive:
            return "\n".join(islice(archive.namelist(), 250))
    if fmt in {"tar", "tgz", "gz", "bz2", "xz"}:
        with tarfile.open(path) as archive:
            return "\n".join(member.name for member in islice(archive, 250))
    if fmt == "7z":
        import py7zr

        with py7zr.SevenZipFile(path) as archive:
            return "\n".join(islice(archive.getnames(), 250))
    if fmt == "rar":
        import rarfile

        with rarfile.RarFile(path) as archive:
            return "\n".join(islice(archive.namelist(), 250))
    raise ValueError(tr("Preview is unavailable for this file."))


class PreviewWindow(ctk.CTkToplevel):
    def __init__(self, parent, path: str, info: dict, *, animate: bool = True):
        super().__init__(parent)
        self.withdraw()
        self.transient(parent)
        self.overrideredirect(True)
        self.configure(fg_color=BG)
        self.path, self.info = path, info
        self.motion = animate and animations_enabled()
        self.closing = False
        self.playing = False
        self.image_source = None
        self.image_index = 0
        self.video_frames: Queue = Queue(maxsize=3)
        self.loaded: SimpleQueue = SimpleQueue()
        self.stop_video = threading.Event()
        self.video_process: subprocess.Popen | None = None
        self.video_thread: threading.Thread | None = None
        self.audio_folder: tempfile.TemporaryDirectory | None = None
        self.fade_id = None
        self.frame_id = None
        self.poll_id = None
        self.viewport = (650, 360)
        self._build()
        self.bind("<Escape>", lambda _event: self.close(animate=False))
        self.bind("<space>", lambda _event: self._toggle_play())
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.deiconify()
        self.wait_visibility()
        self.grab_set()
        self.focus_force()
        if self.motion:
            self._fade(0.25, 1.0, 175)
        threading.Thread(target=self._load, daemon=True).start()
        self.poll_id = self.after(35, self._poll)

    def _build(self):
        parent = self.master
        width = min(740, parent.winfo_width() - 38)
        height = min(526, parent.winfo_height() - 42)
        self.viewport = (width - 50, height - 125)
        x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
        self.geometry(f"{width}x{height}{x:+d}{y:+d}")
        if self.motion:
            self.attributes("-alpha", 0.25)
        card = ctk.CTkFrame(self, fg_color=PANEL, border_width=1, border_color=BORDER_H, corner_radius=22)
        card.pack(fill="both", expand=True)
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(15, 11))
        ctk.CTkButton(
            header, text=tr("Close"), width=78, height=36, command=self.close,
            fg_color=SURFACE, hover_color=SURFACE_H, font=font(13),
        ).pack(side="right")
        filename = Path(self.path).name
        if len(filename) > 54:
            filename = filename[:38] + "…" + filename[-15:]
        ctk.CTkLabel(header, text=filename, text_color=TEXT, font=font(19, "bold"), anchor="w").pack(
            side="left", fill="x", expand=True
        )
        self.content = ctk.CTkFrame(card, fg_color=PANEL_2, corner_radius=13)
        self.content.pack(fill="both", expand=True, padx=18)
        self.canvas = ctk.CTkLabel(self.content, text=tr("Preparing preview…"), text_color=SUB, font=font(14))
        self.canvas.place(relx=0.5, rely=0.5, anchor="center")
        controls = ctk.CTkFrame(card, fg_color="transparent")
        controls.pack(fill="x", padx=20, pady=(10, 13))
        self.caption = ctk.CTkLabel(
            controls, text=tr(self.info.get("category_label", "Preview")), text_color=SUB, font=font(12),
        )
        self.caption.pack(side="left")
        self.play_button = ctk.CTkButton(
            controls, text=tr("Play"), width=105, height=34, command=self._toggle_play, state="disabled",
            fg_color=ACCENT, hover_color=ACCENT_HOVER, font=font(13, "bold"),
        )
        if self.info.get("category") in {"image", "video", "audio"}:
            self.play_button.pack(side="right")

    def _load(self):
        try:
            category = self.info.get("category")
            if category == "image":
                images.inspect_source(self.path)
                source = Image.open(self.path)
                if self.stop_video.is_set():
                    source.close()
                    return
                self.loaded.put(("image", source))
            elif category == "video":
                with Image.open(BytesIO(media.preview(self.path, self.viewport[0]))) as frame:
                    self.loaded.put(("video", frame.copy()))
            elif category == "audio" and sys.platform == "win32":
                self.loaded.put(("audio", None))
            else:
                self.loaded.put(("text", _text_preview(self.path, self.info.get("format"))))
        except Exception:
            self.loaded.put(("error", tr("Preview is unavailable for this file.")))

    def _poll(self):
        try:
            kind, result = self.loaded.get_nowait()
        except Empty:
            self.poll_id = self.after(35, self._poll)
            return
        self.poll_id = None
        if kind == "image":
            self.image_source = result
            width, height = result.size
            self.caption.configure(text=f"{width} × {height}")
            self._show_image_frame()
            if getattr(result, "is_animated", False):
                self.play_button.configure(state="normal")
                if self.motion:
                    self._toggle_play()
            else:
                self.play_button.pack_forget()
        elif kind == "video":
            self._show_frame(result)
            self.caption.configure(text=tr("Silent video preview · up to 60 sec"))
            self.play_button.configure(state="normal")
        elif kind == "audio":
            self.canvas.configure(text=tr("Audio preview"))
            self.caption.configure(text=tr("First 45 seconds"))
            self.play_button.configure(state="normal")
        elif kind == "text":
            self.canvas.destroy()
            text = ctk.CTkTextbox(
                self.content, fg_color=PANEL_2, text_color=TEXT, corner_radius=13,
                font=font(14), wrap="word", scrollbar_button_color=SURFACE_H,
            )
            text.pack(fill="both", expand=True, padx=5, pady=5)
            text.insert("1.0", result or tr("No content to show."))
            text.configure(state="disabled")
        elif kind == "audio_ready":
            self._play_audio(result)
        else:
            self.canvas.configure(text=result)
            self.play_button.pack_forget()

    def _show_frame(self, frame: Image.Image):
        frame = ImageOps.contain(frame, self.viewport, Image.Resampling.LANCZOS)
        self.canvas.configure(text="", image=ctk.CTkImage(dark_image=frame, size=frame.size))

    def _show_image_frame(self):
        source = self.image_source
        if source is None:
            return
        try:
            source.seek(self.image_index)
        except EOFError:
            self.image_index = 0
            source.seek(0)
        delay = max(20, int(source.info.get("duration", 100)))
        self._show_frame(ImageOps.exif_transpose(source).convert("RGBA"))
        if self.playing:
            self.image_index += 1
            self.frame_id = self.after(delay, self._show_image_frame)

    def _toggle_play(self):
        if self.closing or self.play_button.cget("state") == "disabled":
            return
        category = self.info.get("category")
        self.playing = not self.playing
        self.play_button.configure(text=tr("Pause") if self.playing else tr("Play"))
        if not self.playing:
            if self.frame_id is not None:
                self.after_cancel(self.frame_id)
                self.frame_id = None
            if category == "audio":
                self._stop_audio()
            return
        if category == "image" and self.image_source and self.image_source.is_animated:
            self._show_image_frame()
        elif category == "video":
            if self.video_thread is None or not self.video_thread.is_alive() and self.video_frames.empty():
                self.video_thread = threading.Thread(target=self._read_video, daemon=True)
                self.video_thread.start()
            self._video_tick()
        elif category == "audio":
            self.play_button.configure(state="disabled")
            threading.Thread(target=self._prepare_audio, daemon=True).start()
            self.poll_id = self.after(35, self._poll)

    def _read_video(self):
        process = None
        try:
            process = media.preview_video(self.path, *_VIDEO_SIZE, _VIDEO_RATE)
            self.video_process = process
            size = _VIDEO_SIZE[0] * _VIDEO_SIZE[1] * 3
            while not self.stop_video.is_set():
                frame = process.stdout.read(size)
                if len(frame) != size:
                    break
                if not self._queue_frame(frame):
                    break
            if not self.stop_video.is_set():
                self._queue_frame(None)
        except OSError:
            self._queue_frame(None)
        finally:
            if process:
                if process.poll() is None:
                    process.terminate()
                process.stdout.close()
                process.wait()
            self.video_process = None

    def _queue_frame(self, frame):
        while not self.stop_video.is_set():
            try:
                self.video_frames.put(frame, timeout=0.1)
                return True
            except Full:
                continue
        return False

    def _video_tick(self):
        try:
            frame = self.video_frames.get_nowait()
        except Empty:
            self.frame_id = self.after(18, self._video_tick)
            return
        if frame is None:
            self.frame_id = None
            self.playing = False
            self.play_button.configure(text=tr("Play again"))
            return
        self._show_frame(Image.frombytes("RGB", _VIDEO_SIZE, frame))
        self.frame_id = self.after(round(1000 / _VIDEO_RATE), self._video_tick)

    def _prepare_audio(self):
        try:
            if self.audio_folder is None:
                folder = tempfile.TemporaryDirectory(prefix="converter-audio-")
                path = os.path.join(folder.name, "preview.wav")
                media.preview_audio(self.path, path)
                if self.stop_video.is_set():
                    folder.cleanup()
                    return
                self.audio_folder = folder
            self.loaded.put(("audio_ready", os.path.join(self.audio_folder.name, "preview.wav")))
        except (OSError, RuntimeError):
            self.loaded.put(("error", tr("Could not prepare the audio preview.")))

    def _play_audio(self, path):
        import wave
        import winsound

        with wave.open(path) as audio:
            duration = round(1000 * audio.getnframes() / audio.getframerate())
        winsound.PlaySound(path, winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        self.play_button.configure(state="normal", text=tr("Stop"))
        self.frame_id = self.after(duration, self._audio_finished)

    def _audio_finished(self):
        self.frame_id = None
        self.playing = False
        self.play_button.configure(text=tr("Play again"))

    def _stop_audio(self):
        if sys.platform == "win32":
            import winsound

            winsound.PlaySound(None, 0)

    def _fade(self, start, end, duration, done=None):
        if self.fade_id is not None:
            self.after_cancel(self.fade_id)
        begin = perf_counter()

        def step():
            fraction = min(1.0, (perf_counter() - begin) * 1000 / duration)
            eased = 1 - (1 - fraction) ** 3 if end > start else fraction ** 2
            self.attributes("-alpha", start + (end - start) * eased)
            self.fade_id = self.after(15, step) if fraction < 1.0 else None
            if fraction == 1.0 and done:
                done()

        step()

    def close(self, *, animate=True):
        if self.closing:
            return
        self.closing = True
        self.stop_video.set()
        if self.video_process and self.video_process.poll() is None:
            self.video_process.terminate()
        for timer in (self.frame_id, self.poll_id):
            if timer is not None:
                self.after_cancel(timer)
        if self.image_source:
            self.image_source.close()
        if self.audio_folder:
            self._stop_audio()
            self.audio_folder.cleanup()
        if animate and self.motion:
            self._fade(float(self.attributes("-alpha")), 0.0, 120, self.destroy)
        else:
            self.destroy()

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from engine import convert


class PresetTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.folder = Path(folder.name)

    def test_same_format_preset_resizes_without_overwriting(self):
        from engine.presets import Preset, target_for
        source = self.folder / "sample.png"
        Image.new("RGB", (80, 40), "red").save(source)
        info = convert.analyze(str(source))
        preset = Preset("quarter", "Quarter", "png", scale=25, template="(p)Scaled/(F)")
        result = Path(convert.run(str(source), info, target_for(preset, info), verify=True))
        self.assertEqual(result, self.folder / "Scaled" / "SAMPLE.png")
        with Image.open(result) as output:
            self.assertEqual(output.size, (20, 10))
        with Image.open(source) as original:
            self.assertEqual(original.size, (80, 40))

    def test_preset_round_trip_and_mixed_selection(self):
        from engine.presets import Preset, load, save, target_for
        file = self.folder / "presets.json"
        preset = Preset("small", "Small clip", "mp4", inputs=("mkv",), scale=75, video_quality=40)
        save([preset], file)
        self.assertEqual(load(file), [preset])
        self.assertIsNotNone(target_for(preset, {"category": "video", "format": "mkv"}))
        self.assertIsNone(target_for(preset, {"category": "video", "format": "mp4"}))
        self.assertIsNone(target_for(preset, {"category": "image", "format": "png"}))

    def test_vorbis_video_extraction_and_ogv_detection(self):
        from engine.converters import media
        from engine.detect import detect
        self.assertIn("ogg", media.outputs_for("video"))
        self.assertIn("ogv", media.outputs_for("video"))
        source = self.folder / "movie.ogv"
        source.write_bytes(b"OggS" + bytes(24) + b"\x80theora")
        self.assertEqual(detect(str(source))["format"], "ogv")

    def test_pdf_exports_all_pages(self):
        source = self.folder / "pages.pdf"
        images = [Image.new("RGB", (72, 36), color) for color in ("red", "blue")]
        images[0].save(source, save_all=True, append_images=images[1:])
        info = convert.analyze(str(source))
        target = next(route for route in info["targets"] if route["key"] == "png")
        result = Path(convert.run(str(source), info, target, verify=True))
        self.assertEqual(result, self.folder / "pages (1).png")
        self.assertTrue((self.folder / "pages (2).png").is_file())


    def test_media_presets_encode_real_streams(self):
        from engine.converters import media
        from engine.presets import Preset, target_for

        source = self.folder / "video.mp4"
        media._check(media._run([
            "-f", "lavfi", "-i", "testsrc2=s=96x64:r=15:d=1",
            "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
            "-c:v", "libx264", "-c:a", "aac", "-shortest", str(source),
        ]))
        info = convert.analyze(str(source))
        for preset in (
            Preset("rotate", "Rotated", "mp4", rotate=90, scale=75, audio_enabled=False),
            Preset("webm", "WebM", "webm", height=48, tempo=1.25),
            Preset("ogv", "OGV", "ogv"),
            Preset("avi", "AVI", "avi"),
            Preset("small-gif", "Small GIF", "gif", width=36, fps=8),
            Preset("pitch", "Pitch", "ogg", tempo=0.75, pitch=3, sample_rate=48000, channels=2),
            Preset("wav", "WAV", "wav", audio_mode="wav-24", ffmpeg_options="-ar 48000"),
        ):
            with self.subTest(preset=preset.id):
                result = convert.run(str(source), info, target_for(preset, info), verify=True)
                if preset.id == "rotate":
                    from io import BytesIO
                    with Image.open(BytesIO(media.preview(result, 100))) as frame:
                        self.assertEqual(frame.size, (48, 72))
                    self.assertNotEqual(media._run(["-i", result, "-map", "0:a:0", "-f", "null", "-"]).returncode, 0)
                elif preset.id == "small-gif":
                    with Image.open(result) as image:
                        self.assertLessEqual(image.width, 36)
                        self.assertTrue(image.is_animated)

    def test_svg_to_avif_and_power_of_two(self):
        from engine.presets import Preset, target_for

        source = self.folder / "shape.svg"
        source.write_text('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="75">'
                          '<rect width="100" height="75" fill="red"/></svg>', encoding="utf-8")
        info = convert.analyze(str(source))
        preset = Preset("svg", "AVIF", "avif", power_of_two=True, image_quality=75)
        result = convert.run(str(source), info, target_for(preset, info), verify=True)
        with Image.open(result) as output:
            self.assertEqual(output.format, "AVIF")
            self.assertEqual(output.size, (64, 64))

    def test_advanced_args_cannot_add_input_or_output(self):
        from engine.converters.media import extra_options
        self.assertEqual(extra_options('-af "atempo=1.25" -ar 48000'), ["-af", "atempo=1.25", "-ar", "48000"])
        for value in ('-i another.mp4', '-vf "movie=/tmp/source"', "-b:a 128k second.mp3",
                      "-filter_complex_script unknown.txt"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                extra_options(value)

    def test_archive_uses_unique_name_only_after_verified_output(self):
        from engine.presets import Preset, target_for
        source = self.folder / "archive.png"
        Image.new("RGB", (32, 32), "red").save(source)
        archive = self.folder / "Conversion Archives"
        archive.mkdir()
        existing = archive / source.name
        existing.write_bytes(b"keep")
        info = convert.analyze(str(source))
        route = target_for(Preset("archive", "Archive", "jpg"), info)
        result, warning = convert.replace_source(str(source), info, route, convert.archive_source)
        self.assertIsNone(warning)
        self.assertFalse(source.exists())
        self.assertEqual(existing.read_bytes(), b"keep")
        self.assertTrue((archive / "archive (1).png").is_file())
        self.assertTrue(Path(result).is_file())

    def test_explorer_extensions_and_audio_cd_track_lookup(self):
        from engine.converters.audio_cd import _track_sectors
        from engine.presets import Preset, applicable_extensions
        extensions = applicable_extensions(Preset("rotate", "Rotate", "mp4", rotate=90))
        self.assertIn("m4v", extensions)
        self.assertIn("ogv", extensions)
        self.assertNotIn("jpg", extensions)
        toc = bytes(4) + bytes((0, 0x10, 1, 0, 0, 0, 2, 0)) + bytes((0, 0x10, 0xAA, 0, 0, 1, 2, 0))
        self.assertEqual(_track_sectors(toc, 1), (0, 4500))


    def test_cda_default_output_avoids_the_read_only_disc(self):
        from unittest.mock import patch
        source = self.folder / "Track01.cda"
        music = self.folder / "Music"
        with patch("engine.output_names._known_folder", return_value=music):
            result = Path(convert.output_path(str(source), {"ext": "mp3"}))
            self.assertEqual(result, music / "CDA Extraction" / "Track01.mp3")
            result = Path(convert.output_path(str(source), {"ext": "mp3"}, str(self.folder)))
            self.assertEqual(result, self.folder / "Track01.mp3")


if __name__ == "__main__":
    unittest.main()

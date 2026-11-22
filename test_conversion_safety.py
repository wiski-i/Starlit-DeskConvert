"""Regression checks for output fidelity and source preservation."""

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
import io
import tarfile
import zipfile

from PIL import Image

from engine import convert


class ConversionSafetyTests(TestCase):
    def setUp(self):
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.source = self.root / "source.png"
        image = Image.new("RGBA", (3, 1))
        image.putdata([(8, 93, 217, 0), (187, 22, 131, 127), (45, 67, 89, 255)])
        image.save(self.source)
        self.info = convert.analyze(str(self.source))
        self.webp = next(target for target in self.info["targets"] if target["key"] == "webp")

    def test_webp_preserves_pixels_including_hidden_rgb(self):
        output = convert.run(str(self.source), self.info, self.webp)
        with Image.open(self.source) as source, Image.open(output) as result:
            self.assertEqual(source.tobytes(), result.convert("RGBA").tobytes())

    def test_concurrent_outputs_keep_existing_files(self):
        existing = self.source.with_suffix(".webp")
        existing.write_bytes(b"existing output")
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(convert.run, str(self.source), self.info, self.webp) for _ in range(2)]
            outputs = {Path(future.result()).name for future in futures}
        self.assertEqual(outputs, {"source (1).webp", "source (2).webp"})
        self.assertEqual(existing.read_bytes(), b"existing output")
        self.assertTrue(self.source.is_file())

    def test_recycle_refusal_keeps_both_files(self):
        def refuse(path):
            self.assertEqual(Path(path), self.source)
            with Image.open(self.source.with_suffix(".webp")) as output:
                output.load()
            raise OSError("Cannot recycle")

        output, warning = convert.replace_source(str(self.source), self.info, self.webp, refuse)
        self.assertEqual(warning, "Cannot recycle")
        self.assertTrue(self.source.is_file())
        self.assertTrue(Path(output).is_file())

    def test_unsupported_png_never_reaches_recycle(self):
        Image.new("I;16", (2, 2), 65534).save(self.source)

        def unexpected_call(_path):
            self.fail("An unsupported source must stay in place.")

        with self.assertRaises(ValueError):
            convert.replace_source(str(self.source), self.info, self.webp, unexpected_call)
        self.assertTrue(self.source.is_file())
        self.assertFalse(self.source.with_suffix(".webp").exists())

    def test_tar_round_trip(self):
        source = self.root / "archive.tar"
        data = b"local conversion"
        with tarfile.open(source, "w") as archive:
            member = tarfile.TarInfo("folder/readme.txt")
            member.size = len(data)
            archive.addfile(member, io.BytesIO(data))
        info = convert.analyze(str(source))
        target = next(route for route in info["targets"] if route["key"] == "zip")
        output = convert.run(str(source), info, target, verify=True)
        with zipfile.ZipFile(output) as archive:
            self.assertEqual(archive.read("folder/readme.txt"), data)

    def test_binary_signature_takes_precedence_over_extension(self):
        renamed = self.root / "picture.txt"
        self.source.rename(renamed)
        info = convert.analyze(str(renamed))
        self.assertEqual(info["format"], "png")
        self.assertIn("webp", {route["key"] for route in info["targets"]})
        self.assertNotIn("docx", {route["key"] for route in info["targets"]})

    def test_txt_to_docx_preserves_literal_symbols_and_turkish_text(self):
        source = self.root / "notes.txt"
        source.write_bytes("# Türkçe şğüıöç\r\nItem * 4\r\n".encode("cp1254"))
        info = convert.analyze(str(source))
        self.assertEqual(info["format"], "txt")
        self.assertNotIn("png", {route["key"] for route in info["targets"]})
        target = next(route for route in info["targets"] if route["key"] == "docx")
        output = convert.run(str(source), info, target)
        with zipfile.ZipFile(output) as archive:
            document = archive.read("word/document.xml").decode("utf-8")
        self.assertIn("# Türkçe şğüıöç", document)
        self.assertIn("Item * 4", document)

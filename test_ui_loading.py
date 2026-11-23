"""File inspection must not stop Tk from painting the window."""
import os
from pathlib import Path
from queue import SimpleQueue
import tempfile
import threading
import time
from types import SimpleNamespace, MethodType
import unittest
from unittest.mock import Mock, patch

from app import App


class FileLoadingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.source = Path(self.temp.name) / "sample.txt"
        self.source.write_text("test", encoding="utf-8")
        self.gate = threading.Event()
        self.started = threading.Event()
        self.finished = threading.Event()
        self.addCleanup(self.gate.set)
        self.ui = SimpleNamespace(
            busy=False, files=[], results={}, primary_cat=None, _pending_files=set(),
            _load_generation=0, file_load_results=SimpleQueue(), _file_load_error=None,
            convert_btn=Mock(), set_status=Mock(), _refresh=Mock(), progress=Mock(),
        )
        for name in ("add_files", "clear_all", "_inspect_files", "_poll_files"):
            if hasattr(App, name):
                setattr(self.ui, name, MethodType(getattr(App, name), self.ui))

    def inspect(self, path):
        self.started.set()
        self.gate.wait(0.7)
        self.finished.set()
        return {"name": os.path.basename(path), "engine_ok": True}

    def drain(self):
        self.gate.set()
        deadline = time.monotonic() + 2
        while self.ui._pending_files and time.monotonic() < deadline:
            self.ui._poll_files()
            time.sleep(0.01)

    def test_slow_inspection_returns_without_blocking_the_ui(self):
        with patch("app.engine.analyze", side_effect=self.inspect):
            start = time.monotonic()
            self.ui.add_files([str(self.source)])
            elapsed = time.monotonic() - start
            self.assertLess(elapsed, 0.2, "File inspection is blocking the Tk thread")
            self.assertTrue(self.started.wait(1))
            self.assertEqual(self.ui.files, [], "Worker must not mutate GUI state")
            self.drain()
        self.assertEqual([f["path"] for f in self.ui.files], [str(self.source)])
        self.assertFalse(self.ui._pending_files)

    def test_duplicate_drop_while_loading_is_inspected_once(self):
        with patch("app.engine.analyze", side_effect=self.inspect) as analyze:
            self.ui.add_files([str(self.source), str(self.source)])
            self.assertTrue(self.started.wait(1))
            self.ui.add_files([str(self.source)])
            self.drain()
        self.assertEqual(analyze.call_count, 1)
        self.assertEqual(len(self.ui.files), 1)

    def test_clearing_during_inspection_does_not_restore_old_files(self):
        with patch("app.engine.analyze", side_effect=self.inspect):
            self.ui.add_files([str(self.source)])
            self.assertTrue(self.started.wait(1))
            self.ui.clear_all()
            self.gate.set()
            self.assertTrue(self.finished.wait(1))
            time.sleep(0.02)
            self.ui._poll_files()
        self.assertEqual(self.ui.files, [])
        self.assertFalse(self.ui._pending_files)

    def test_inspection_error_does_not_leave_loading_stuck(self):
        with patch("app.engine.analyze", side_effect=OSError("unreadable")):
            self.ui.add_files([str(self.source)])
            self.drain()
        self.assertFalse(self.ui._pending_files)
        self.assertEqual(self.ui.files, [])
        self.assertTrue(self.ui.set_status.called)


if __name__ == "__main__":
    unittest.main()

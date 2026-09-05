"""Tests for review_html.inputs.read_guarded and review_html.warnings.Warnings."""
from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from review_html.inputs import MAX_INPUT_BYTES, read_guarded
from review_html.warnings import Warnings


class WarningsTest(unittest.TestCase):
    def test_add_appends_and_prints_to_stderr_immediately(self) -> None:
        warnings = Warnings()
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            warnings.add("first thing")
            self.assertEqual(stderr.getvalue(), "warning: first thing\n")
            warnings.add("second thing")
        self.assertEqual(stderr.getvalue(), "warning: first thing\nwarning: second thing\n")
        self.assertEqual(warnings.items, ["first thing", "second thing"])

    def test_instances_do_not_share_items(self) -> None:
        with contextlib.redirect_stderr(io.StringIO()):
            a = Warnings()
            a.add("x")
            b = Warnings()
        self.assertEqual(b.items, [])


class ReadGuardedTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.warnings = Warnings()
        self._stderr = contextlib.redirect_stderr(io.StringIO())
        self._stderr.__enter__()

    def tearDown(self) -> None:
        self._stderr.__exit__(None, None, None)
        self._tmp.cleanup()

    def test_returns_text_for_utf8_file(self) -> None:
        path = self.dir / "ok.txt"
        path.write_text("héllo\n", encoding="utf-8")
        self.assertEqual(read_guarded(path, self.warnings), "héllo\n")
        self.assertEqual(self.warnings.items, [])

    def test_rejects_file_over_50_mb_by_stat(self) -> None:
        path = self.dir / "huge.xml"
        with path.open("wb") as fh:
            fh.seek(MAX_INPUT_BYTES)   # sparse: one byte past the limit
            fh.write(b"\0")
        self.assertEqual(path.stat().st_size, MAX_INPUT_BYTES + 1)
        self.assertIsNone(read_guarded(path, self.warnings, xml=True))
        self.assertEqual(len(self.warnings.items), 1)
        self.assertIn("huge.xml", self.warnings.items[0])
        self.assertIn("50 MB", self.warnings.items[0])

    def test_rejects_doctype_after_more_than_64_kb_of_comment_when_xml(self) -> None:
        # Comments and processing instructions may precede the DOCTYPE, so the
        # scan covers the whole buffer; a 64 KB window could be padded past.
        path = self.dir / "padded.xml"
        padding = "<!-- " + "y" * 70_000 + " -->\n"
        path.write_text(
            '<?xml version="1.0"?>\n' + padding +
            '<!DOCTYPE lolz [<!ENTITY lol "lol">]>\n<testsuites/>\n',
            encoding="utf-8",
        )
        self.assertGreater(path.stat().st_size, 64 * 1024)
        self.assertIsNone(read_guarded(path, self.warnings, xml=True))
        self.assertEqual(len(self.warnings.items), 1)
        self.assertIn("DOCTYPE", self.warnings.items[0])

    def test_rejects_doctype_when_xml(self) -> None:
        path = self.dir / "evil.xml"
        padding = "<!-- " + "x" * 60_000 + " -->\n"
        path.write_text(
            '<?xml version="1.0"?>\n' + padding +
            '<!DOCTYPE lolz [<!ENTITY lol "lol">]>\n<testsuites/>\n',
            encoding="utf-8",
        )
        self.assertIsNone(read_guarded(path, self.warnings, xml=True))
        self.assertEqual(len(self.warnings.items), 1)
        self.assertIn("evil.xml", self.warnings.items[0])
        self.assertIn("DOCTYPE", self.warnings.items[0])

    def test_doctype_is_not_scanned_when_not_xml(self) -> None:
        path = self.dir / "page.html"
        path.write_text("<!DOCTYPE html>\n<p>hi</p>\n", encoding="utf-8")
        self.assertEqual(read_guarded(path, self.warnings), "<!DOCTYPE html>\n<p>hi</p>\n")
        self.assertEqual(self.warnings.items, [])

    def test_returns_none_with_warning_for_non_utf8(self) -> None:
        path = self.dir / "latin1.diff"
        path.write_bytes(b"+caf\xe9\n")
        self.assertIsNone(read_guarded(path, self.warnings))
        self.assertEqual(len(self.warnings.items), 1)
        self.assertIn("latin1.diff", self.warnings.items[0])
        self.assertIn("UTF-8", self.warnings.items[0])

    def test_returns_none_with_warning_for_missing_file(self) -> None:
        path = self.dir / "absent.txt"
        self.assertIsNone(read_guarded(path, self.warnings))
        self.assertEqual(len(self.warnings.items), 1)
        self.assertIn("absent.txt", self.warnings.items[0])


if __name__ == "__main__":
    unittest.main()

"""Golden-fixture regression test for the review renderer.

``fixtures/golden.html`` was produced by the renderer as it existed at
commit ``9da40cf`` (``git show 9da40cf:scripts/build_review_html.py``) from
``fixtures/golden.json``, and regenerated when the per-file diffs section
gained its code/docs/other grouping (the only body change at that point).
The current renderer, invoked as a script by its repo-relative path, must
produce the same document apart from the contents of the ``<style>`` element
and the generation timestamp in the footer.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURES = Path(__file__).resolve().parent / "fixtures"
ENTRY_POINT = "scripts/build_review_html.py"

_STYLE = re.compile(r"<style>.*?</style>", re.DOTALL)
_GENERATED = re.compile(r"^\s*Generated .*$", re.MULTILINE)


def normalise(document: str) -> str:
    document = _STYLE.sub("<style></style>", document)
    return _GENERATED.sub("Generated <normalised>", document)


class GoldenFixtureTest(unittest.TestCase):
    def test_current_renderer_matches_golden(self) -> None:
        expected = (FIXTURES / "golden.html").read_text(encoding="utf-8")
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "golden.html"
            result = subprocess.run(
                [sys.executable, ENTRY_POINT,
                 "--data", str(FIXTURES / "golden.json"),
                 "--output", str(output)],
                cwd=REPO_ROOT, capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            actual = output.read_text(encoding="utf-8")
        self.assertEqual(normalise(actual), normalise(expected))

    def test_normalise_drops_only_style_and_timestamp(self) -> None:
        page = "<style>a{}</style>\n<p>x</p>\n    Generated 2026-01-01 · repo\n"
        self.assertEqual(
            normalise(page),
            "<style></style>\n<p>x</p>\nGenerated <normalised>\n",
        )


if __name__ == "__main__":
    unittest.main()

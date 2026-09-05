"""Tests for review_html.diffs: fragment loading, hunk parsing, rendering."""
from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from review_html.common import escape
from review_html.diffs import added_lines, is_binary, load_fragments, render_diff
from review_html.warnings import Warnings

TWO_HUNKS = """\
diff --git a/pkg/a.go b/pkg/a.go
index 1111111..2222222 100644
--- a/pkg/a.go
+++ b/pkg/a.go
@@ -1,4 +1,5 @@
 package pkg
+
+import "fmt"
 
-func A() {}
+func A() { fmt.Println("a") }
@@ -20,3 +21,4 @@ func Z() {
 	x := 1
+	y := 2
 	_ = x
+	_ = y
"""

RENAME = """\
diff --git a/old/name.py b/new/name.py
similarity index 88%
rename from old/name.py
rename to new/name.py
--- a/old/name.py
+++ b/new/name.py
@@ -10,4 +10,5 @@ def f():
     a = 1
-    b = 2
+    b = 3
+    c = 4
     return a
"""

NO_NEWLINE = """\
--- a/x.txt
+++ b/x.txt
@@ -1,2 +1,2 @@
 keep
-old
\\ No newline at end of file
+new
\\ No newline at end of file
"""

DEV_NULL = """\
diff --git a/dev/null b/notes.md
new file mode 100644
index 0000000..3333333
--- /dev/null
+++ b/notes.md
@@ -0,0 +1,3 @@
+# Notes
+
+- first
"""

DELETED = """\
--- a/gone.py
+++ /dev/null
@@ -1,2 +0,0 @@
-a = 1
-b = 2
"""


def legacy_render_diff(diff: str) -> str:
    """The renderer's _render_diff as it stood before diffs.py existed."""
    if not diff:
        return ""
    lines = diff.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    spans = []
    for line in lines:
        if line.startswith(("+++", "---")):
            cls = "diff-file-header"
        elif line.startswith("@@"):
            cls = "diff-hunk"
        elif line.startswith("+"):
            cls = "diff-add"
        elif line.startswith("-"):
            cls = "diff-del"
        elif line.startswith("\\"):
            cls = "diff-meta"
        else:
            cls = "diff-context"
        spans.append(f'<span class="diff-line {cls}">{escape(line)}</span>')
    return "".join(spans)


class AddedLinesTest(unittest.TestCase):
    def test_multiple_hunks(self) -> None:
        self.assertEqual(added_lines(TWO_HUNKS), {2, 3, 5, 22, 24})

    def test_hunk_header_without_counts(self) -> None:
        diff = "--- a/f\n+++ b/f\n@@ -1 +1 @@\n-old\n+new\n"
        self.assertEqual(added_lines(diff), {1})

    def test_rename(self) -> None:
        self.assertEqual(added_lines(RENAME), {11, 12})

    def test_no_newline_marker_does_not_advance(self) -> None:
        self.assertEqual(added_lines(NO_NEWLINE), {2})

    def test_dev_null_fragment_from_no_index(self) -> None:
        self.assertEqual(added_lines(DEV_NULL), {1, 2, 3})

    def test_deleted_file_has_no_added_lines(self) -> None:
        self.assertEqual(added_lines(DELETED), set())

    def test_empty_and_placeholder(self) -> None:
        self.assertEqual(added_lines(""), set())
        self.assertEqual(added_lines("(diff fragment 'x' missing)"), set())

    def test_added_line_starting_with_plus_plus_is_not_a_header(self) -> None:
        self.assertEqual(added_lines("@@ -1,2 +1,4 @@\n a\n+++i;\n+b\n c\n"), {2, 3})

    def test_second_file_section_resets_the_counter(self) -> None:
        diff = ("diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -1 +1,2 @@\n a\n+b\n"
                "diff --git a/y b/y\n--- a/y\n+++ b/y\n@@ -5 +5,2 @@\n c\n+d\n")
        self.assertEqual(added_lines(diff), {2, 6})


class IsBinaryTest(unittest.TestCase):
    def test_binary_files_differ(self) -> None:
        self.assertTrue(is_binary(
            "diff --git a/logo.png b/logo.png\n"
            "Binary files a/logo.png and b/logo.png differ\n"))

    def test_git_binary_patch(self) -> None:
        self.assertTrue(is_binary(
            "diff --git a/logo.png b/logo.png\nindex 111..222\nGIT binary patch\nliteral 10\n"))

    def test_text_diff_is_not_binary(self) -> None:
        self.assertFalse(is_binary(TWO_HUNKS))
        self.assertFalse(is_binary("+Binary files are mentioned in this added line\n"))


class LoadFragmentsTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.warnings = Warnings()
        self._stderr = contextlib.redirect_stderr(io.StringIO())
        self._stderr.__enter__()

    def tearDown(self) -> None:
        self._stderr.__exit__(None, None, None)
        self._tmp.cleanup()

    def test_inline_diff_wins_over_diff_file(self) -> None:
        (self.dir / "a.diff").write_text("+from file\n", encoding="utf-8")
        files = [{"path": "a.py", "diff": "+inline\n", "diff_file": "a.diff"}]
        self.assertEqual(load_fragments(files, self.dir, self.warnings), {"a.py": "+inline\n"})

    def test_reads_diff_file_from_diff_dir(self) -> None:
        (self.dir / "b.diff").write_text(TWO_HUNKS, encoding="utf-8")
        files = [{"path": "pkg/a.go", "diff_file": "b.diff"}]
        self.assertEqual(load_fragments(files, self.dir, self.warnings), {"pkg/a.go": TWO_HUNKS})
        self.assertEqual(self.warnings.items, [])

    def test_missing_file_yields_placeholder(self) -> None:
        files = [{"path": "c.py", "diff_file": "nope.diff"}]
        self.assertEqual(
            load_fragments(files, self.dir, self.warnings),
            {"c.py": "(diff fragment 'nope.diff' missing)"},
        )

    def test_non_utf8_yields_placeholder_and_warning(self) -> None:
        (self.dir / "bad.diff").write_bytes(b"+caf\xe9\n")
        files = [{"path": "d.py", "diff_file": "bad.diff"}]
        self.assertEqual(
            load_fragments(files, self.dir, self.warnings),
            {"d.py": "(diff fragment 'bad.diff' is not UTF-8)"},
        )
        self.assertEqual(len(self.warnings.items), 1)
        self.assertIn("bad.diff", self.warnings.items[0])

    def test_no_source_yields_no_diff_provided(self) -> None:
        files = [{"path": "e.py"}, {"path": "f.py", "diff_file": "f.diff"}]
        self.assertEqual(
            load_fragments(files, None, self.warnings),
            {"e.py": "(no diff provided)", "f.py": "(no diff provided)"},
        )


class RenderDiffTest(unittest.TestCase):
    def test_none_matches_legacy_output(self) -> None:
        for diff in (TWO_HUNKS, RENAME, NO_NEWLINE, DEV_NULL, DELETED, "", "+x\n", "+x"):
            with self.subTest(diff=diff[:20]):
                self.assertEqual(render_diff(diff, None), legacy_render_diff(diff))

    def test_uncovered_marks_matching_added_lines_only(self) -> None:
        html = render_diff(TWO_HUNKS, {2, 5, 22, 99})
        spans = html.split("</span>")[:-1]
        classes = [s.split('class="')[1].split('"')[0] for s in spans]
        self.assertEqual(classes.count("diff-line diff-add diff-uncovered"), 3)
        self.assertEqual(classes.count("diff-line diff-add"), 2)
        # The marked lines are exactly the requested new-file numbers.
        marked = [s for s in spans if "diff-uncovered" in s]
        self.assertTrue(marked[0].endswith(">+"))
        self.assertIn("fmt.Println", marked[1])
        self.assertIn("y := 2", marked[2])
        for cls in classes:
            if "diff-uncovered" in cls:
                self.assertIn("diff-add", cls)
        self.assertNotIn("diff-del diff-uncovered", html)
        self.assertNotIn("diff-context diff-uncovered", html)

    def test_empty_uncovered_set_matches_none(self) -> None:
        self.assertEqual(render_diff(TWO_HUNKS, set()), render_diff(TWO_HUNKS, None))

    def test_plus_plus_inside_hunk_renders_as_added_line(self) -> None:
        # The legacy renderer classed this line as a file header; the new
        # walk classes it by its position, which is the correct rendering.
        diff = "@@ -1,2 +1,4 @@\n a\n+++i;\n+b\n c\n"
        html = render_diff(diff, None)
        self.assertIn('<span class="diff-line diff-add">+++i;</span>', html)
        self.assertNotIn("diff-file-header", html)
        self.assertIn('<span class="diff-line diff-file-header">+++ b/f</span>',
                      render_diff("--- a/f\n+++ b/f\n@@ -1 +1 @@\n+x\n", None))


if __name__ == "__main__":
    unittest.main()

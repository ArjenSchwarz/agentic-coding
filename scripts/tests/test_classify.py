"""Tests for file classification and the per-file diff grouping it drives."""
from __future__ import annotations

import unittest

from review_html.classify import classify_path, file_kind, is_docs_only
from review_html.render import docs_only, render
from review_html.sections import render_files


class ClassifyPathTest(unittest.TestCase):
    def test_docs(self) -> None:
        for path in ("README", "README.md", "docs/guide.rst", "CHANGELOG.txt",
                     ".github/CODEOWNERS", "LICENSE", "src/docs/notes.py",
                     "guide.adoc", "notes.mdx"):
            self.assertEqual(classify_path(path), "docs", path)

    def test_other(self) -> None:
        for path in ("assets/logo.png", "icon.svg", "package-lock.json", "Cargo.lock",
                     "go.sum", "custom.lock", ".gitignore", ".editorconfig"):
            self.assertEqual(classify_path(path), "other", path)

    def test_code(self) -> None:
        for path in ("src/app.py", ".github/workflows/ci.yml", "Makefile", "go.mod",
                     "package.json", "notes.txt", "docs.py", "specs/testing.md.py",
                     "documentation/x.py"):
            self.assertEqual(classify_path(path), "code", path)

    def test_empty_path_is_code(self) -> None:
        self.assertEqual(classify_path(""), "code")


class FileKindTest(unittest.TestCase):
    def test_explicit_kind_wins(self) -> None:
        self.assertEqual(file_kind({"path": "README.md", "kind": "code"}), "code")

    def test_invalid_kind_falls_back_to_path(self) -> None:
        self.assertEqual(file_kind({"path": "README.md", "kind": "prose"}), "docs")


class DocsOnlyTest(unittest.TestCase):
    def test_no_code_files(self) -> None:
        self.assertTrue(is_docs_only([{"path": "README.md"}, {"path": "logo.png"}]))

    def test_one_code_file(self) -> None:
        self.assertFalse(is_docs_only([{"path": "README.md"}, {"path": "go.mod"}]))

    def test_empty_is_not_docs_only(self) -> None:
        self.assertFalse(is_docs_only([]))

    def test_explicit_classification_overrides_files(self) -> None:
        self.assertFalse(docs_only({"change_classification": "code",
                                    "files": [{"path": "README.md"}]}))
        self.assertTrue(docs_only({"change_classification": "docs-only",
                                   "files": [{"path": "main.go"}]}))

    def test_derived_when_absent(self) -> None:
        self.assertTrue(docs_only({"files": [{"path": "README.md"}]}))
        self.assertFalse(docs_only({"files": [{"path": "main.go"}]}))


class RenderFilesGroupingTest(unittest.TestCase):
    def test_single_kind_has_no_group_headings(self) -> None:
        html = render_files([{"path": "a.py"}, {"path": "b.py"}], {}, {})
        self.assertIn("2 files: 2 code. Click to expand.", html)
        self.assertNotIn("file-group", html)

    def test_mixed_kinds_group_code_first(self) -> None:
        files = [{"path": "README.md"}, {"path": "logo.png"}, {"path": "a.py"}]
        html = render_files(files, {}, {})
        self.assertIn("3 files: 1 code · 1 docs · 1 other. Click to expand.", html)
        code = html.index('<h3 class="file-group">Code <span class="muted">(1)</span></h3>')
        docs = html.index('<h3 class="file-group">Docs <span class="muted">(1)</span></h3>')
        other = html.index('<h3 class="file-group">Other <span class="muted">(1)</span></h3>')
        self.assertLess(code, docs)
        self.assertLess(docs, other)
        self.assertLess(code, html.index("a.py"))
        self.assertLess(html.index("a.py"), docs)
        self.assertLess(docs, html.index("README.md"))
        self.assertLess(other, html.index("logo.png"))

    def test_explicit_kind_moves_file(self) -> None:
        files = [{"path": "README.md", "kind": "code"}, {"path": "a.py"}]
        html = render_files(files, {}, {})
        self.assertIn("2 files: 2 code.", html)
        self.assertNotIn("file-group", html)


class RenderDocsOnlyDerivationTest(unittest.TestCase):
    def test_docs_only_files_suppress_tests_without_classification_key(self) -> None:
        data = {"repo": {"name": "r"}, "files": [{"path": "README.md"}],
                "tests": {"no_data_reason": "no tests found"}}
        html = render(data, None)
        self.assertNotIn('id="tests"', html)

    def test_code_files_keep_tests_without_classification_key(self) -> None:
        data = {"repo": {"name": "r"}, "files": [{"path": "main.go"}],
                "tests": {"no_data_reason": "no tests found"}}
        html = render(data, None)
        self.assertIn('id="tests"', html)


if __name__ == "__main__":
    unittest.main()

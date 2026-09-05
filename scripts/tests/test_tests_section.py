"""Tests for review_html.tests_section.build_tests and the render() wiring."""
from __future__ import annotations

import contextlib
import copy
import io
import json
import tempfile
import unittest
from pathlib import Path

from review_html import render
from review_html.common import file_anchor
from review_html.diffs import load_fragments
from review_html.tests_section import TestsResult, build_tests
from review_html.warnings import Warnings

HEAD_JUNIT = """\
<testsuite name="s">
  <testcase classname="pkg.A" name="test_ok"/>
  <testcase classname="pkg.A" name="test_new"/>
  <testcase classname="pkg.A" name="test_fail"><failure message="token=s3cr3tvalue boom"/></testcase>
  <testcase classname="pkg.A" name="test_skip"><skipped/></testcase>
  <testcase classname="pkg.A" name="test_flaky"><flakyFailure message="x"/></testcase>
  <testcase classname="pkg.A" name="test_err"><error message="err &lt;here&gt;"/></testcase>
</testsuite>
"""

OTHER_JUNIT = """\
<testsuite name="other">
  <testcase classname="pkg.B" name="test_b"/>
</testsuite>
"""

BASE_JUNIT = """\
<testsuite name="s">
  <testcase classname="pkg.A" name="test_ok"/>
  <testcase classname="pkg.A" name="test_fail"/>
  <testcase classname="pkg.A" name="test_skip"/>
  <testcase classname="pkg.A" name="test_flaky"/>
  <testcase classname="pkg.A" name="test_err"/>
  <testcase classname="pkg.B" name="test_b"/>
  <testcase classname="pkg.A" name="test_removed"/>
</testsuite>
"""

HEAD_LCOV = """\
SF:src/a.py
DA:1,1
DA:2,1
DA:3,0
end_of_record
SF:v1/util.py
DA:1,1
end_of_record
SF:v2/util.py
DA:1,0
end_of_record
SF:src/zero.py
DA:10,1
end_of_record
"""

BASE_LCOV = """\
SF:src/a.py
DA:1,1
DA:2,0
end_of_record
"""


def diff(path: str, start: int, count: int) -> str:
    return (f"--- a/{path}\n+++ b/{path}\n@@ -1,0 +{start},{count} @@\n"
            + "".join(f"+line {start + i}\n" for i in range(count)))


FILES = [
    {"path": "src/a.py", "badge": "Modified", "stat": "+3 / -0", "diff": diff("src/a.py", 2, 3)},
    {"path": "src/gone.py", "badge": "Deleted", "stat": "+0 / -3", "diff": "--- a/src/gone.py\n+++ /dev/null\n@@ -1,3 +0,0 @@\n-x\n-y\n-z\n"},
    {"path": "assets/x.png", "badge": "Binary file", "stat": "", "diff": "Binary files a/assets/x.png and b/assets/x.png differ\n"},
    {"path": "src/nocov.py", "badge": "Modified", "stat": "+1 / -0", "diff": diff("src/nocov.py", 1, 1)},
    {"path": "util.py", "badge": "Modified", "stat": "+1 / -0", "diff": diff("util.py", 1, 1)},
    {"path": "src/zero.py", "badge": "Added", "stat": "+1 / -0", "diff": diff("src/zero.py", 1, 1)},
]


def block() -> dict:
    return {
        "provenance": {"source": "ci", "run_ids": [123], "run_urls": ["https://ci/run/123"],
                       "snapshot": {"sha": "abc1234def", "dirty": False},
                       "ci_state": "artifacts usable", "fallback_state": "not needed"},
        "baseline_provenance": {"source": "local", "run_id": None, "run_url": None,
                                "sha": "base9999", "timestamp": "2026-09-04T10:00:00Z"},
        "coverage_scope": "repository",
        "run_outcome": "failed",
        "partial": True,
        "junit": ["123-test-results-ubuntu--junit.xml", "123-other--junit.xml", "missing.xml"],
        "coverage": ["123-test-results-ubuntu--lcov.info"],
        "baseline_junit": ["base--junit.xml"],
        "baseline_coverage": ["base--lcov.info"],
        "path_map": {"strip": None, "prepend": None},
        "jobs": [{"run_id": 123, "name": "test (ubuntu)", "outcome": "success", "url": "https://ci/job/1"},
                 {"run_id": 123, "name": "lint", "outcome": "failure", "url": "https://ci/job/2"}],
        "artifacts": [{"name": "test-results-ubuntu", "run_id": 123,
                       "junit": ["123-test-results-ubuntu--junit.xml"],
                       "coverage": ["123-test-results-ubuntu--lcov.info"], "job": "test (ubuntu)"},
                      {"name": "other", "run_id": 123, "junit": ["123-other--junit.xml"],
                       "coverage": []}],
        "pending_runs": [{"run_id": 124, "name": "integration", "status": "in_progress",
                          "url": "https://ci/run/124"}],
        "skipped_artifacts": [{"name": "build-output", "size_in_bytes": 412000000}],
        "run_touched_files": ["go.sum"],
        "diff_tests_file": None,
        "no_data_reason": None,
    }


class SectionCase(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self._stderr = io.StringIO()
        self._redirect = contextlib.redirect_stderr(self._stderr)
        self._redirect.__enter__()
        (self.dir / "123-test-results-ubuntu--junit.xml").write_text(HEAD_JUNIT, encoding="utf-8")
        (self.dir / "123-other--junit.xml").write_text(OTHER_JUNIT, encoding="utf-8")
        (self.dir / "base--junit.xml").write_text(BASE_JUNIT, encoding="utf-8")
        (self.dir / "123-test-results-ubuntu--lcov.info").write_text(HEAD_LCOV, encoding="utf-8")
        (self.dir / "base--lcov.info").write_text(BASE_LCOV, encoding="utf-8")

    def tearDown(self) -> None:
        self._redirect.__exit__(None, None, None)
        self._tmp.cleanup()

    def build(self, b: dict, files: list[dict] | None = None) -> TestsResult:
        files = copy.deepcopy(FILES if files is None else files)
        warnings = Warnings()
        fragments = load_fragments(files, self.dir, warnings)
        return build_tests(b, files, fragments, self.dir, warnings)

    def assertOrdered(self, html: str, *markers: str) -> None:
        positions = []
        for m in markers:
            self.assertIn(m, html)
            positions.append(html.index(m))
        self.assertEqual(positions, sorted(positions), markers)


class CardTest(SectionCase):
    def test_no_data_card_shows_na_values_and_section_link(self) -> None:
        b = block()
        b.update(junit=[], coverage=[], baseline_junit=[], baseline_coverage=[],
                 no_data_reason="runner not detected", jobs=[], artifacts=[])
        card = self.build(b).card_html
        self.assertIn('<div class="card">', card)
        self.assertIn("<h3>Tests</h3>", card)
        self.assertIn("<p>Pass rate: n/a</p>", card)
        self.assertIn("<p>New tests: n/a</p>", card)
        self.assertIn("<p>Diff coverage: n/a</p>", card)
        self.assertIn('<a href="#tests">Jump to tests →</a>', card)

    def test_card_values_with_data(self) -> None:
        card = self.build(block()).card_html
        self.assertIn("<p>Pass rate: 67% (4 of 6)</p>", card)
        self.assertIn("<p>New tests: 1</p>", card)
        self.assertIn("<p>Diff coverage: 50% (1 of 2 added lines)</p>", card)


class SectionTest(SectionCase):
    def test_section_order(self) -> None:
        html = self.build(block()).section_html
        self.assertTrue(html.startswith('<section id="tests">'))
        self.assertOrdered(
            html,
            "<h2>Tests</h2>",
            "Source:",
            "Baseline:",
            "Execution:",
            "Coverage scope:",
            "Totals:",
            "<h3>Pending runs</h3>",
            "<h3>Jobs</h3>",
            "<h3>Failed tests</h3>",
            "<h3>New and removed tests</h3>",
            "<h3>Diff coverage</h3>",
            "<h3>Overall coverage</h3>",
            "changed files matched coverage data",
            "<h3>Files touched by the run</h3>",
            "<h3>Skipped artifacts</h3>",
            "<h3>Warnings</h3>",
        )

    def test_provenance_with_ci_link_and_both_states(self) -> None:
        html = self.build(block()).section_html
        self.assertIn("Source: <strong>CI</strong>", html)
        self.assertIn('<a href="https://ci/run/123">run 123</a>', html)
        self.assertIn("<code>abc1234def</code>", html)
        self.assertIn("CI state: <strong>artifacts usable</strong>", html)
        self.assertIn("Fallback: <strong>not needed</strong>", html)
        self.assertIn("Baseline: local run", html)
        self.assertIn("<code>base9999</code>", html)

    def test_local_provenance_shows_timestamp_and_dirty_flag(self) -> None:
        b = block()
        b["provenance"] = {"source": "local", "timestamp": "2026-09-04T09:00:00Z",
                           "snapshot": {"sha": "abc", "dirty": True}}
        b["baseline_provenance"] = None
        html = self.build(b).section_html
        self.assertIn("Source: <strong>local run</strong> at 2026-09-04T09:00:00Z", html)
        self.assertIn("<code>abc</code> (dirty working tree)", html)
        self.assertIn("Baseline: none", html)
        self.assertNotIn("CI state:", html)

    def test_availability_line_states_are_independent(self) -> None:
        html = self.build(block()).section_html
        self.assertIn("Execution: <strong>failed</strong> (partial results)", html)
        self.assertIn("JUnit: 2 of 3 files read", html)
        self.assertIn("Coverage: 1 file", html)
        self.assertIn("Baseline: present", html)

    def test_coverage_scope(self) -> None:
        html = self.build(block()).section_html
        self.assertIn("Coverage scope: every test in the repository", html)
        b = block()
        b["coverage_scope"] = "project-configured"
        self.assertIn("Coverage scope: as the project configures it", self.build(b).section_html)

    def test_totals_with_flaky_alongside(self) -> None:
        html = self.build(block()).section_html
        self.assertIn("Totals: <strong>4 passed</strong> · 1 failed · 1 skipped · 1 errored · 1 flaky", html)

    def test_pending_runs(self) -> None:
        html = self.build(block()).section_html
        self.assertIn('<a href="https://ci/run/124">integration</a> (run 124, in_progress)', html)

    def test_job_rows_and_artifact_rows(self) -> None:
        html = self.build(block()).section_html
        self.assertIn('<tr><td><a href="https://ci/job/1">test (ubuntu)</a></td><td>success</td>'
                      "<td>3</td><td>1</td><td>1</td><td>1</td></tr>", html)
        self.assertIn('<tr><td><a href="https://ci/job/2">lint</a></td><td>failure</td>'
                      "<td>—</td><td>—</td><td>—</td><td>—</td></tr>", html)
        self.assertIn("<tr><td>artifact <code>other</code></td><td>—</td>"
                      "<td>1</td><td>0</td><td>0</td><td>0</td></tr>", html)

    def test_no_jobs_or_artifacts_omits_table(self) -> None:
        b = block()
        b["jobs"] = []
        b["artifacts"] = []
        self.assertNotIn("<h3>Jobs</h3>", self.build(b).section_html)

    def test_failed_tests_with_job_or_artifact_and_redacted_message(self) -> None:
        html = self.build(block()).section_html
        self.assertIn("<td>pkg.A</td><td>test_fail</td><td>test (ubuntu)</td><td>[redacted] boom</td>", html)
        self.assertIn("<td>pkg.A</td><td>test_err</td><td>test (ubuntu)</td><td>err &lt;here&gt;</td>", html)
        self.assertNotIn("s3cr3tvalue", html)

    def test_failed_test_from_unattributed_artifact_names_the_artifact(self) -> None:
        (self.dir / "123-other--junit.xml").write_text(
            '<testsuite name="o"><testcase classname="pkg.B" name="test_b"><failure message="m"/></testcase></testsuite>',
            encoding="utf-8")
        html = self.build(block()).section_html
        self.assertIn("<td>pkg.B</td><td>test_b</td><td>artifact other</td><td>m</td>", html)

    def test_new_and_removed_by_identity_from_baseline_with_cross_source_note(self) -> None:
        html = self.build(block()).section_html
        self.assertIn("by identity, from the baseline run", html)
        self.assertIn("<ul><li>+ <code>pkg.A</code> test_new</li><li>− <code>pkg.A</code> test_removed</li></ul>", html)
        self.assertIn("crosses sources", html)
        self.assertIn("head from CI, baseline from a local run", html)

    def test_same_source_baseline_has_no_cross_source_note(self) -> None:
        b = block()
        b["baseline_provenance"] = {"source": "ci", "run_id": 120, "run_url": "https://ci/run/120", "sha": "base9999"}
        html = self.build(b).section_html
        self.assertNotIn("crosses sources", html)
        self.assertIn('Baseline: CI <a href="https://ci/run/120">run 120</a>', html)

    def test_new_and_removed_by_name_from_diff_tests_file(self) -> None:
        (self.dir / "diff-tests.json").write_text(
            json.dumps({"added": ["TestFoo", "TestBar"], "removed": ["TestOld"],
                        "unpatterned_files": ["spec/foo_spec.rb"]}), encoding="utf-8")
        b = block()
        b["baseline_junit"] = []
        b["diff_tests_file"] = "diff-tests.json"
        result = self.build(b)
        html = result.section_html
        self.assertIn("by declaration name, from the diff", html)
        self.assertIn("<ul><li>+ TestFoo</li><li>+ TestBar</li><li>− TestOld</li></ul>", html)
        self.assertIn("No declaration pattern applies to <code>spec/foo_spec.rb</code>", html)
        self.assertNotIn("crosses sources", html)
        self.assertIn("<p>New tests: 2</p>", result.card_html)

    def test_no_baseline_and_no_diff_tests_says_so(self) -> None:
        b = block()
        b["baseline_junit"] = []
        result = self.build(b)
        self.assertIn("no baseline run and no diff-derived list", result.section_html)
        self.assertIn("<p>New tests: n/a</p>", result.card_html)

    def test_per_file_table(self) -> None:
        html = self.build(block()).section_html
        a = file_anchor("src/a.py")
        self.assertIn(f'<tr><td><a href="#{a}">src/a.py</a></td><td>3</td><td>1</td><td>50%</td></tr>', html)
        for path in ("src/nocov.py", "util.py", "src/zero.py"):
            anchor = file_anchor(path)
            self.assertIn(f'<td><a href="#{anchor}">{path}</a></td><td>1</td><td>—</td><td>no coverage data</td>', html)
        self.assertNotIn("src/gone.py", html.split("<h3>Diff coverage</h3>")[1].split("<h3>Overall coverage</h3>")[0])
        self.assertNotIn("assets/x.png", html)
        self.assertIn("Aggregate diff coverage: <strong>50%</strong> (1 of 2 measurable added lines)", html)

    def test_overall_coverage_with_delta_and_cross_source_note(self) -> None:
        html = self.build(block()).section_html
        self.assertIn("Head <strong>66.7%</strong> (4 of 6 lines) · baseline <strong>50.0%</strong> (1 of 2 lines) · delta <strong>+16.7 pp</strong>", html)
        self.assertIn("baseline coverage comes from a different source", html)

    def test_overall_coverage_head_only(self) -> None:
        b = block()
        b["baseline_coverage"] = []
        html = self.build(b).section_html
        self.assertIn("Head <strong>66.7%</strong> (4 of 6 lines)", html)
        self.assertNotIn("baseline <strong>", html)
        self.assertNotIn("delta", html)

    def test_no_coverage_omits_coverage_subsections(self) -> None:
        b = block()
        b["coverage"] = []
        b["baseline_coverage"] = []
        result = self.build(b)
        html = result.section_html
        self.assertNotIn("<h3>Diff coverage</h3>", html)
        self.assertNotIn("<h3>Overall coverage</h3>", html)
        self.assertNotIn("changed files matched coverage data", html)
        self.assertIn("Coverage: none", html)
        self.assertEqual(result.uncovered, {})
        self.assertEqual(result.counts["matched"], 0)
        self.assertEqual(result.counts["unmatched"], 0)

    def test_unmatched_report(self) -> None:
        result = self.build(block())
        html = result.section_html
        self.assertIn("2 of 4 changed files matched coverage data", html)
        self.assertIn("<li><code>src/nocov.py</code> — no candidate</li>", html)
        self.assertIn("<li><code>util.py</code> — ambiguous</li>", html)
        self.assertEqual(result.counts["matched"], 2)
        self.assertEqual(result.counts["unmatched"], 2)

    def test_uncovered_sets(self) -> None:
        result = self.build(block())
        self.assertEqual(result.uncovered, {"src/a.py": {3}})

    def test_counts(self) -> None:
        result = self.build(block())
        self.assertEqual(result.counts, {"passed": 4, "failed": 1, "errored": 1, "skipped": 1,
                                         "flaky": 1, "matched": 2, "unmatched": 2})

    def test_touched_files_skipped_artifacts_and_warnings(self) -> None:
        html = self.build(block()).section_html
        self.assertIn("<li><code>go.sum</code></li>", html)
        self.assertIn("<li><code>build-output</code> (412000000 bytes)</li>", html)
        self.assertIn("<h3>Warnings</h3>", html)
        self.assertIn("missing.xml", html.split("<h3>Warnings</h3>")[1])

    def test_path_map_is_applied_before_matching(self) -> None:
        (self.dir / "123-test-results-ubuntu--lcov.info").write_text(
            "SF:/ci/repo/src/a.py\nDA:2,1\nDA:3,0\nend_of_record\nSF:/ci/repo/util.py\nDA:1,1\nend_of_record\n",
            encoding="utf-8")
        b = block()
        b["path_map"] = {"strip": "/ci/repo", "prepend": None}
        result = self.build(b)
        self.assertEqual(result.uncovered, {"src/a.py": {3}})
        self.assertEqual(result.counts["matched"], 2)


class NoDataCardTest(SectionCase):
    UPLOAD = "must upload a JUnit XML file as an artifact"

    def no_data(self, reason: str | None, ci_state: str = "artifacts usable",
                fallback: str = "not needed") -> str:
        b = block()
        b.update(junit=[], coverage=[], baseline_junit=[], baseline_coverage=[],
                 jobs=[], artifacts=[], pending_runs=[], no_data_reason=reason)
        b["provenance"]["ci_state"] = ci_state
        b["provenance"]["fallback_state"] = fallback
        return self.build(b).section_html

    def test_card_uses_warning_border_treatment(self) -> None:
        html = self.no_data("no tests found")
        self.assertIn('<div class="card tests-nodata">', html)
        self.assertIn("<h3>No test results</h3>", html)

    def test_reasons(self) -> None:
        self.assertIn("No tests were found", self.no_data("no tests found"))
        self.assertIn("test runner could not be detected", self.no_data("runner not detected"))
        self.assertIn("required tool is missing", self.no_data("required tool missing"))
        self.assertIn("local test run failed", self.no_data("local run failed"))
        self.assertIn("local test run timed out", self.no_data("local run timed out"))

    def test_ci_reason_derives_from_states_with_upload_sentence(self) -> None:
        for state in ("no run", "artifacts absent", "artifacts expired"):
            html = self.no_data("ci", state, "blocked by fork PR")
            self.assertIn(f"CI state: <strong>{state}</strong>", html)
            self.assertIn("Local fallback: <strong>blocked by fork PR</strong>", html)
            self.assertIn(self.UPLOAD, html)
            self.assertIn("coverage file in a supported format", html)

    def test_ci_reason_without_upload_sentence(self) -> None:
        for state in ("run in progress or queued", "run failed before upload"):
            html = self.no_data("ci", state, "blocked by run in progress")
            self.assertIn(f"CI state: <strong>{state}</strong>", html)
            self.assertNotIn(self.UPLOAD, html)

    def test_no_reason_and_no_cases_still_shows_card(self) -> None:
        html = self.no_data(None)
        self.assertIn('<div class="card tests-nodata">', html)

    def test_card_absent_when_results_exist(self) -> None:
        self.assertNotIn("tests-nodata", self.build(block()).section_html)


class RenderWiringTest(SectionCase):
    def data(self) -> dict:
        return {
            "repo": {"name": "x/y", "path": "/tmp/y"},
            "title": "t",
            "findings": [{"severity": "minor", "area": "a", "finding": "f", "resolution": "r"}],
            "unresolved_comments": [{"author": "a", "type": "review", "body": "hi"}],
            "files": copy.deepcopy(FILES),
            "tests": block(),
        }

    def stderr_lines(self) -> list[str]:
        return self._stderr.getvalue().splitlines()

    def test_card_section_and_toc(self) -> None:
        html = render(self.data(), self.dir)
        self.assertIn('<li><a href="#tests">Tests</a></li>', html)
        self.assertLess(html.index('<h3>Review findings</h3>'), html.index('<h3>Tests</h3>'))
        self.assertLess(html.index('<h3>Tests</h3>'), html.index('</section>'))
        self.assertLess(html.index('<section id="findings">'), html.index('<section id="tests">'))
        self.assertLess(html.index('<section id="tests">'), html.index('<section id="unresolved-comments">'))
        self.assertLess(html.index('<li><a href="#findings">'), html.index('<li><a href="#tests">'))
        self.assertLess(html.index('<li><a href="#tests">'), html.index('<li><a href="#unresolved-comments">'))

    def test_summary_lines_are_last_even_when_diagram_warns_later(self) -> None:
        data = self.data()
        data["diagram_file"] = "absent.json"
        render(data, self.dir)
        lines = self.stderr_lines()
        self.assertEqual(lines[-2], "summary coverage: matched=2 unmatched=2")
        self.assertEqual(lines[-1], "summary tests: passed=4 failed=1 errored=1 skipped=1 flaky=1")
        diagram = [i for i, l in enumerate(lines) if "absent.json" in l]
        self.assertTrue(diagram)
        self.assertLess(diagram[0], len(lines) - 2)
        missing = [i for i, l in enumerate(lines) if "missing.xml" in l]
        self.assertLess(missing[0], diagram[0])

    def test_summary_tests_excludes_baseline_cases(self) -> None:
        render(self.data(), self.dir)
        self.assertEqual(self.stderr_lines()[-1],
                         "summary tests: passed=4 failed=1 errored=1 skipped=1 flaky=1")

    def test_uncovered_marks_reach_render_files(self) -> None:
        html = render(self.data(), self.dir)
        self.assertIn('<span class="diff-line diff-add diff-uncovered">+line 3</span>', html)
        self.assertIn('<span class="diff-line diff-add">+line 2</span>', html)

    def test_docs_only_omits_card_and_section_without_warnings(self) -> None:
        data = self.data()
        data["change_classification"] = "docs-only"
        html = render(data, self.dir)
        self.assertNotIn('id="tests"', html)
        self.assertNotIn("<h3>Tests</h3>", html)
        self.assertNotIn("Tests</a>", html)
        self.assertEqual(self._stderr.getvalue(), "")
        self.assertNotIn("diff-add diff-uncovered", html)

    def test_no_tests_block_is_silent(self) -> None:
        data = self.data()
        del data["tests"]
        html = render(data, self.dir)
        self.assertNotIn('id="tests"', html)
        self.assertEqual(self._stderr.getvalue(), "")


if __name__ == "__main__":
    unittest.main()

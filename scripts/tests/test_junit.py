"""Tests for review_html.junit.parse_junit."""
from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from review_html.junit import Case, parse_junit
from review_html.warnings import Warnings

NESTED = """\
<?xml version="1.0" encoding="UTF-8"?>
<testsuites name="all">
  <testsuite name="outer" tests="1">
    <testcase classname="pkg.Outer" name="test_outer" time="0.1"/>
    <testsuite name="inner" tests="3">
      <testcase classname="pkg.Inner" name="test_pass"/>
      <testcase classname="" name="test_no_classname"/>
      <testcase name="test_missing_classname"/>
    </testsuite>
  </testsuite>
</testsuites>
"""

OUTCOMES = """\
<testsuite name="suite" tests="6">
  <testcase classname="c" name="failed_msg">
    <failure message="assert 1 == 2" type="AssertionError">traceback text</failure>
  </testcase>
  <testcase classname="c" name="failed_text">
    <failure type="AssertionError">
      only the body carries the reason
    </failure>
  </testcase>
  <testcase classname="c" name="errored">
    <error message="boom"/>
  </testcase>
  <testcase classname="c" name="skipped">
    <skipped message="not on this platform"/>
  </testcase>
  <testcase classname="c" name="passed"/>
  <testcase classname="c" name="failed_and_error">
    <failure message="first"/>
    <error message="second"/>
  </testcase>
</testsuite>
"""

SUREFIRE = """\
<testsuite name="surefire" tests="3">
  <testcase classname="a.B" name="flaky_failure">
    <flakyFailure message="first attempt failed" type="AssertionError">trace</flakyFailure>
  </testcase>
  <testcase classname="a.B" name="rerun_failure">
    <rerunFailure message="attempt 1"/>
    <rerunFailure message="attempt 2"/>
  </testcase>
  <testcase classname="a.B" name="flaky_error">
    <flakyError message="transient"/>
  </testcase>
  <testcase classname="a.B" name="rerun_error_then_failed">
    <rerunError message="attempt 1"/>
    <failure message="final failure"/>
  </testcase>
</testsuite>
"""

PYTEST_RERUN = """\
<testsuites>
  <testsuite name="pytest" tests="3">
    <testcase classname="tests.test_x" name="test_retry">
      <rerun message="attempt 1 failed">trace</rerun>
    </testcase>
    <testcase classname="tests.test_x" name="test_retry">
      <rerun message="attempt 2 failed">trace</rerun>
    </testcase>
    <testcase classname="tests.test_x" name="test_retry"/>
    <testcase classname="tests.test_x" name="test_stable"/>
  </testsuite>
</testsuites>
"""

DUPLICATE_FAIL_THEN_PASS = """\
<testsuite name="s">
  <testcase classname="c" name="t"><failure message="first"/></testcase>
  <testcase classname="c" name="t"/>
</testsuite>
"""

DUPLICATE_PASS_THEN_FAIL = """\
<testsuite name="s">
  <testcase classname="c" name="t"/>
  <testcase classname="c" name="t"><failure message="last"/></testcase>
</testsuite>
"""

SINGLE = """\
<testsuite name="s">
  <testcase classname="c" name="t"/>
</testsuite>
"""


class ParseJunitTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.warnings = Warnings()
        self._stderr = contextlib.redirect_stderr(io.StringIO())
        self._stderr.__enter__()

    def tearDown(self) -> None:
        self._stderr.__exit__(None, None, None)
        self._tmp.cleanup()

    def write(self, name: str, text: str) -> Path:
        path = self.dir / name
        path.write_text(text, encoding="utf-8")
        return path

    def parse(self, *names_and_texts: tuple[str, str]) -> list[Case]:
        paths = [self.write(name, text) for name, text in names_and_texts]
        return parse_junit(paths, self.warnings)

    def by_name(self, cases: list[Case]) -> dict[str, Case]:
        return {c.name: c for c in cases}

    def test_nested_testsuites_and_classname_fallback(self) -> None:
        cases = self.parse(("nested.xml", NESTED))
        self.assertEqual(
            [(c.suite, c.name) for c in cases],
            [("pkg.Outer", "test_outer"),
             ("pkg.Inner", "test_pass"),
             ("inner", "test_no_classname"),
             ("inner", "test_missing_classname")],
        )
        self.assertTrue(all(c.outcome == "passed" and not c.flaky for c in cases))
        self.assertEqual(self.warnings.items, [])

    def test_outcomes_and_messages(self) -> None:
        cases = self.by_name(self.parse(("outcomes.xml", OUTCOMES)))
        self.assertEqual(cases["failed_msg"].outcome, "failed")
        self.assertEqual(cases["failed_msg"].message, "assert 1 == 2")
        self.assertEqual(cases["failed_text"].outcome, "failed")
        self.assertEqual(cases["failed_text"].message, "only the body carries the reason")
        self.assertEqual(cases["errored"].outcome, "errored")
        self.assertEqual(cases["errored"].message, "boom")
        self.assertEqual(cases["skipped"].outcome, "skipped")
        self.assertEqual(cases["passed"].outcome, "passed")
        self.assertEqual(cases["passed"].message, "")
        # failure precedes error; the message is the first failure or error element's
        self.assertEqual(cases["failed_and_error"].outcome, "failed")
        self.assertEqual(cases["failed_and_error"].message, "first")
        self.assertFalse(any(c.flaky for c in cases.values()))

    def test_surefire_flaky_and_rerun_elements(self) -> None:
        cases = self.by_name(self.parse(("surefire.xml", SUREFIRE)))
        for name in ("flaky_failure", "rerun_failure", "flaky_error"):
            self.assertEqual(cases[name].outcome, "passed", name)
            self.assertTrue(cases[name].flaky, name)
        self.assertEqual(cases["rerun_error_then_failed"].outcome, "failed")
        self.assertFalse(cases["rerun_error_then_failed"].flaky)
        self.assertEqual(cases["rerun_error_then_failed"].message, "final failure")

    def test_pytest_rerun_attempts_collapse_to_one_flaky_case(self) -> None:
        cases = self.parse(("pytest.xml", PYTEST_RERUN))
        self.assertEqual([c.name for c in cases], ["test_retry", "test_stable"])
        retry = cases[0]
        self.assertEqual(retry.outcome, "passed")
        self.assertTrue(retry.flaky)
        self.assertFalse(cases[1].flaky)

    def test_duplicate_fail_then_pass_is_one_flaky_passed_case(self) -> None:
        cases = self.parse(("dup.xml", DUPLICATE_FAIL_THEN_PASS))
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0].outcome, "passed")
        self.assertTrue(cases[0].flaky)

    def test_duplicate_pass_then_fail_is_failed_not_flaky(self) -> None:
        cases = self.parse(("dup.xml", DUPLICATE_PASS_THEN_FAIL))
        self.assertEqual(len(cases), 1)
        self.assertEqual(cases[0].outcome, "failed")
        self.assertFalse(cases[0].flaky)
        self.assertEqual(cases[0].message, "last")

    def test_identities_across_sources_stay_separate(self) -> None:
        cases = self.parse(("job-a.xml", SINGLE), ("job-b.xml", SINGLE))
        self.assertEqual(len(cases), 2)
        self.assertEqual([c.source for c in cases], ["job-a.xml", "job-b.xml"])
        self.assertEqual({(c.suite, c.name) for c in cases}, {("c", "t")})

    def test_source_is_the_input_file_name(self) -> None:
        cases = self.parse(("123-test-results-ubuntu--junit.xml", OUTCOMES))
        self.assertTrue(all(c.source == "123-test-results-ubuntu--junit.xml" for c in cases))

    def test_malformed_xml_warns_and_skips_that_file(self) -> None:
        cases = self.parse(("bad.xml", "<testsuite><testcase name='x'></testsuite>"),
                           ("good.xml", SINGLE))
        self.assertEqual([c.source for c in cases], ["good.xml"])
        self.assertEqual(len(self.warnings.items), 1)
        self.assertIn("bad.xml", self.warnings.items[0])

    def test_doctype_and_missing_file_are_rejected_with_warnings(self) -> None:
        self.write("evil.xml", "<!DOCTYPE x [<!ENTITY e 'e'>]><testsuite/>")
        cases = parse_junit([self.dir / "evil.xml", self.dir / "absent.xml"], self.warnings)
        self.assertEqual(cases, [])
        self.assertEqual(len(self.warnings.items), 2)
        self.assertIn("DOCTYPE", self.warnings.items[0])
        self.assertIn("absent.xml", self.warnings.items[1])

    def test_unexpected_root_warns(self) -> None:
        cases = self.parse(("cov.xml", "<coverage/>"))
        self.assertEqual(cases, [])
        self.assertEqual(len(self.warnings.items), 1)
        self.assertIn("cov.xml", self.warnings.items[0])


if __name__ == "__main__":
    unittest.main()

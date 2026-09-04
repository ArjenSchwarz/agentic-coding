"""Timing tests (requirement 2.12): large generated inputs parse in under 5 s.

Skipped on hosts that look busy: when ``os.getloadavg`` is unavailable or
its one-minute average exceeds the CPU count.
"""
from __future__ import annotations

import contextlib
import io
import os
import tempfile
import time
import unittest
from pathlib import Path

from review_html.coverage import parse_coverage
from review_html.junit import parse_junit
from review_html.warnings import Warnings

LIMIT_SECONDS = 5.0
LCOV_BYTES = 10 * 1024 * 1024
JUNIT_CASES = 5_000


def host_is_slow() -> bool:
    if not hasattr(os, "getloadavg"):
        return True
    try:
        load = os.getloadavg()[0]
    except OSError:
        return True
    return load > (os.cpu_count() or 1)


def write_lcov(path: Path) -> None:
    record = ["SF:src/pkg/module_{n}.py"] + [f"DA:{i},{i % 3}" for i in range(1, 401)] + ["end_of_record"]
    chunk = "\n".join(record) + "\n"
    with path.open("w", encoding="utf-8") as fh:
        size = 0
        n = 0
        while size < LCOV_BYTES:
            text = chunk.format(n=n)
            fh.write(text)
            size += len(text)
            n += 1


def write_junit(path: Path) -> None:
    parts = ['<?xml version="1.0" encoding="UTF-8"?>\n<testsuites>\n<testsuite name="big">\n']
    for i in range(JUNIT_CASES):
        if i % 50 == 0:
            parts.append(f'<testcase classname="pkg.Class{i % 97}" name="test_{i}">'
                         f'<failure message="assertion {i}">trace {i}</failure></testcase>\n')
        elif i % 50 == 1:
            parts.append(f'<testcase classname="pkg.Class{i % 97}" name="test_{i}"><skipped/></testcase>\n')
        else:
            parts.append(f'<testcase classname="pkg.Class{i % 97}" name="test_{i}" time="0.01"/>\n')
    parts.append("</testsuite>\n</testsuites>\n")
    path.write_text("".join(parts), encoding="utf-8")


@unittest.skipIf(host_is_slow(), "host load exceeds CPU count or load average unavailable")
class TimingTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.warnings = Warnings()
        self._stderr = contextlib.redirect_stderr(io.StringIO())
        self._stderr.__enter__()

    def tearDown(self) -> None:
        self._stderr.__exit__(None, None, None)
        self._tmp.cleanup()

    def test_ten_megabyte_lcov_parses_in_time(self) -> None:
        path = self.dir / "big.info"
        write_lcov(path)
        self.assertGreaterEqual(path.stat().st_size, LCOV_BYTES)
        start = time.perf_counter()
        cov = parse_coverage(path, self.warnings)
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, LIMIT_SECONDS, f"lcov parse took {elapsed:.2f}s")
        self.assertGreater(len(cov), 1000)
        self.assertEqual(self.warnings.items, [])

    def test_five_thousand_case_junit_parses_in_time(self) -> None:
        path = self.dir / "big.xml"
        write_junit(path)
        start = time.perf_counter()
        cases = parse_junit([path], self.warnings)
        elapsed = time.perf_counter() - start
        self.assertLess(elapsed, LIMIT_SECONDS, f"JUnit parse took {elapsed:.2f}s")
        self.assertEqual(len(cases), JUNIT_CASES)
        self.assertEqual(sum(1 for c in cases if c.outcome == "failed"), 100)
        self.assertEqual(self.warnings.items, [])


if __name__ == "__main__":
    unittest.main()

"""JUnit XML parsing.

``parse_junit`` reads one or more JUnit files through ``read_guarded`` and
returns one ``Case`` per test identity per source file. Rerun and flaky
elements (Surefire and pytest-rerunfailures dialects) never make a case
that ultimately passed count as failed; they mark it flaky instead.
"""
from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

from .inputs import read_guarded, xml_root
from .warnings import Warnings

FLAKY_ELEMENTS = ("flakyFailure", "flakyError", "rerunFailure", "rerunError", "rerun")
SUITE_TAGS = ("testsuites", "testsuite")
OUTCOMES = ("passed", "failed", "errored", "skipped")


@dataclass
class Case:
    suite: str
    name: str
    outcome: str        # one of OUTCOMES
    flaky: bool
    message: str
    source: str         # input file name, for job attribution


def _message(el: ET.Element) -> str:
    """Message of the first failure or error child: its attribute, else its text."""
    for child in el:
        if child.tag in ("failure", "error"):
            attr = child.get("message")
            if attr is not None and attr != "":
                return attr
            return (child.text or "").strip()
    return ""


def _classify(el: ET.Element) -> tuple[str, bool]:
    """Outcome and flaky flag of one ``testcase`` element, first rule wins."""
    tags = {child.tag for child in el}
    if "failure" in tags:
        return "failed", False
    if "error" in tags:
        return "errored", False
    if any(tag in tags for tag in FLAKY_ELEMENTS):
        return "passed", True
    if "skipped" in tags:
        return "skipped", False
    return "passed", False


def _elements(root: ET.Element) -> list[tuple[str, ET.Element]]:
    """Every ``testcase`` with its enclosing suite name, in document order."""
    out: list[tuple[str, ET.Element]] = []
    for suite in root.iter():
        if suite.tag not in SUITE_TAGS:
            continue
        suite_name = suite.get("name") or ""
        for tc in suite:
            if tc.tag == "testcase":
                out.append((suite_name, tc))
    return out


def _parse_one(path: Path, warnings: Warnings) -> list[Case]:
    text = read_guarded(path, warnings, xml=True)
    if text is None:
        return []
    root = xml_root(text, path.name, warnings, SUITE_TAGS, "JUnit XML", "a JUnit suite")
    if root is None:
        return []

    source = path.name
    cases: dict[tuple[str, str], Case] = {}
    for suite_name, tc in _elements(root):
        suite = tc.get("classname") or suite_name
        name = tc.get("name") or ""
        outcome, flaky = _classify(tc)
        message = _message(tc)
        key = (suite, name)
        earlier = cases.get(key)
        if earlier is None:
            cases[key] = Case(suite, name, outcome, flaky, message, source)
            continue
        # Same identity within one source: the last element's outcome wins,
        # and a pass after an earlier failure, error, or rerun is flaky.
        if outcome == "passed":
            flaky = flaky or earlier.flaky or earlier.outcome in ("failed", "errored")
        cases[key] = Case(suite, name, outcome, flaky, message, source)
    return list(cases.values())


def parse_junit(paths: list[Path], warnings: Warnings) -> list[Case]:
    cases: list[Case] = []
    for path in paths:
        cases.extend(_parse_one(path, warnings))
    return cases

"""Tests for review_html.coverage: parsers, path mapping, matching, arithmetic."""
from __future__ import annotations

import contextlib
import io
import random
import tempfile
import unittest
from pathlib import Path

from review_html.coverage import (
    Entry,
    apply_path_map,
    diff_coverage,
    match,
    normalise,
    overall,
    parse_coverage,
)
from review_html.warnings import Warnings

LCOV = """\
TN:
SF:src/a.py
DA:1,1
DA:2,0
DA:3,4,checksum
end_of_record
SF:src/b.py
DA:10,0
end_of_record
SF:src/a.py
DA:2,2
DA:4,0
end_of_record
"""

COBERTURA = """\
<?xml version="1.0" ?>
<coverage line-rate="0.5" version="6.0">
  <sources>
    <source>/home/ci/repo</source>
    <source>/home/ci/repo/src</source>
  </sources>
  <packages>
    <package name="pkg">
      <classes>
        <class name="a.py" filename="pkg/a.py" line-rate="0.5">
          <methods>
            <method name="f"><lines><line number="1" hits="1"/></lines></method>
          </methods>
          <lines>
            <line number="1" hits="1"/>
            <line number="2" hits="0" branch="true" condition-coverage="50% (1/2)"/>
          </lines>
        </class>
      </classes>
    </package>
  </packages>
</coverage>
"""

COBERTURA_NO_SOURCES = """\
<coverage>
  <packages><package name="p"><classes>
    <class filename="x.py"><lines><line number="7" hits="3"/></lines></class>
  </classes></package></packages>
</coverage>
"""

COVERPROFILE_SET = """\
mode: set
github.com/org/repo/pkg/a.go:3.10,5.2 2 1
github.com/org/repo/pkg/a.go:5.2,7.1 1 0
github.com/org/repo/pkg/b.go:1.1,1.20 1 0
"""

COVERPROFILE_COUNT = """\
mode: count
github.com/org/repo/pkg/a.go:3.10,5.2 2 4
github.com/org/repo/pkg/a.go:4.1,4.30 1 0
github.com/org/repo/pkg/a.go:5.2,6.1 1 9
"""


def entry(path: str, *aliases: str, hits: dict | None = None) -> Entry:
    return Entry([path, *aliases], dict(hits or {1: 1}))


class ParserTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)
        self.warnings = Warnings()
        self._stderr = contextlib.redirect_stderr(io.StringIO())
        self._stderr.__enter__()

    def tearDown(self) -> None:
        self._stderr.__exit__(None, None, None)
        self._tmp.cleanup()

    def parse(self, name: str, text: str) -> list[Entry]:
        path = self.dir / name
        path.write_text(text, encoding="utf-8")
        return parse_coverage(path, self.warnings)

    def test_lcov_keeps_repeated_sf_as_separate_entries(self) -> None:
        cov = self.parse("lcov.info", LCOV)
        self.assertEqual([e.paths for e in cov], [["src/a.py"], ["src/b.py"], ["src/a.py"]])
        self.assertEqual(cov[0].hits, {1: 1, 2: 0, 3: 4})
        self.assertEqual(cov[1].hits, {10: 0})
        self.assertEqual(cov[2].hits, {2: 2, 4: 0})
        self.assertEqual(self.warnings.items, [])

    def test_lcov_without_trailing_end_of_record_keeps_last_entry(self) -> None:
        cov = self.parse("lcov.info", "SF:a.py\nDA:1,1\n")
        self.assertEqual(cov, [Entry(["a.py"], {1: 1})])

    def test_cobertura_two_source_roots_become_aliases(self) -> None:
        cov = self.parse("coverage.xml", COBERTURA)
        self.assertEqual(len(cov), 1)
        self.assertEqual(cov[0].paths,
                         ["pkg/a.py", "/home/ci/repo/pkg/a.py", "/home/ci/repo/src/pkg/a.py"])
        self.assertEqual(cov[0].hits, {1: 1, 2: 0})

    def test_cobertura_without_sources_has_primary_path_only(self) -> None:
        cov = self.parse("coverage.xml", COBERTURA_NO_SOURCES)
        self.assertEqual(cov, [Entry(["x.py"], {7: 3})])

    def test_coverprofile_set_mode_expands_blocks_to_lines(self) -> None:
        cov = self.parse("coverage.out", COVERPROFILE_SET)
        self.assertEqual([e.paths for e in cov],
                         [["github.com/org/repo/pkg/a.go"], ["github.com/org/repo/pkg/b.go"]])
        # block 3..5 count 1, block 5..7 count 0: line 5 keeps the maximum
        self.assertEqual(cov[0].hits, {3: 1, 4: 1, 5: 1, 6: 0, 7: 0})
        self.assertEqual(cov[1].hits, {1: 0})

    def test_coverprofile_count_mode_takes_maximum_on_overlap(self) -> None:
        cov = self.parse("coverage.out", COVERPROFILE_COUNT)
        self.assertEqual(len(cov), 1)
        self.assertEqual(cov[0].hits, {3: 4, 4: 4, 5: 9, 6: 9})

    def test_coverprofile_without_mode_line_is_rejected(self) -> None:
        cov = self.parse("coverage.out", "a.go:1.1,2.1 1 1\n")
        self.assertEqual(cov, [])
        self.assertEqual(len(self.warnings.items), 1)
        self.assertIn("coverage.out", self.warnings.items[0])

    def test_cobertura_doctype_is_rejected(self) -> None:
        cov = self.parse("coverage.xml", "<!DOCTYPE coverage><coverage/>")
        self.assertEqual(cov, [])
        self.assertIn("DOCTYPE", self.warnings.items[0])

    def test_malformed_xml_warns(self) -> None:
        cov = self.parse("coverage.xml", "<coverage><packages></coverage>")
        self.assertEqual(cov, [])
        self.assertIn("coverage.xml", self.warnings.items[0])

    def test_unknown_xml_root_warns(self) -> None:
        cov = self.parse("junit.xml", "<testsuite/>")
        self.assertEqual(cov, [])
        self.assertIn("junit.xml", self.warnings.items[0])

    def test_unrecognised_format_warns(self) -> None:
        cov = self.parse("notes.txt", "hello\n")
        self.assertEqual(cov, [])
        self.assertIn("notes.txt", self.warnings.items[0])

    def test_missing_file_warns(self) -> None:
        cov = parse_coverage(self.dir / "absent.info", self.warnings)
        self.assertEqual(cov, [])
        self.assertIn("absent.info", self.warnings.items[0])


class PathMapTest(unittest.TestCase):
    def test_normalise(self) -> None:
        self.assertEqual(normalise("./src\\a.py"), "src/a.py")
        self.assertEqual(normalise("src//pkg/../a.py"), "src/a.py")
        self.assertEqual(normalise("/abs/./x.go"), "/abs/x.go")

    def test_strip_and_prepend_on_primary_and_aliases(self) -> None:
        cov = [entry("./src\\pkg/a.py", "/ci/repo/src/pkg/a.py", "srcx/pkg/a.py")]
        mapped = apply_path_map(cov, "src", "lib")
        self.assertEqual(mapped[0].paths,
                         ["lib/pkg/a.py", "lib/ci/repo/src/pkg/a.py", "lib/srcx/pkg/a.py"])
        self.assertIs(mapped[0].hits, cov[0].hits)

    def test_strip_only_whole_segments(self) -> None:
        cov = [entry("srcx/a.py"), entry("src/a.py"), entry("src")]
        self.assertEqual([e.paths for e in apply_path_map(cov, "src/", None)],
                         [["srcx/a.py"], ["a.py"], ["src"]])

    def test_no_map_only_normalises(self) -> None:
        cov = [entry("./a\\b.py")]
        self.assertEqual(apply_path_map(cov, None, None)[0].paths, ["a/b.py"])


class MatchTest(unittest.TestCase):
    def test_exact_match_leaves_the_pool(self) -> None:
        cov = [entry("src/a.py", hits={1: 1})]
        hits, unmatched = match(cov, ["src/a.py", "pkg/src/a.py"])
        self.assertEqual(hits, {"src/a.py": {1: 1}})
        self.assertEqual(unmatched, {"pkg/src/a.py": "no candidate"})

    def test_exact_match_beats_suffix_candidates(self) -> None:
        cov = [entry("a/util.py", hits={1: 1}), entry("x/a/util.py", hits={2: 1})]
        hits, unmatched = match(cov, ["a/util.py"])
        self.assertEqual(hits, {"a/util.py": {1: 1}})
        self.assertEqual(unmatched, {})

    def test_exact_alias_equal_to_two_files_is_ambiguous_for_both(self) -> None:
        cov = [entry("a.py", "src/a.py", hits={1: 1})]
        hits, unmatched = match(cov, ["a.py", "src/a.py"])
        self.assertEqual(hits, {})
        self.assertEqual(unmatched, {"a.py": "ambiguous", "src/a.py": "ambiguous"})

    def test_shared_entry_removed_once_and_both_files_ambiguous(self) -> None:
        cov = [entry("util.py", hits={1: 1})]
        hits, unmatched = match(cov, ["a/util.py", "b/util.py"])
        self.assertEqual(hits, {})
        self.assertEqual(unmatched, {"a/util.py": "ambiguous", "b/util.py": "ambiguous"})

    def test_shared_removal_does_not_cascade(self) -> None:
        # util.py sits in both pools and is removed once; a/util.py stays
        # unique to src/a/util.py, which must match it.
        cov = [entry("util.py", hits={1: 1}), entry("a/util.py", hits={2: 1})]
        hits, unmatched = match(cov, ["src/a/util.py", "src/util.py"])
        self.assertEqual(hits, {"src/a/util.py": {2: 1}})
        self.assertEqual(unmatched, {"src/util.py": "ambiguous"})

    def test_distinct_residuals_are_ambiguous(self) -> None:
        cov = [entry("v1/a.py", hits={1: 1}), entry("v2/a.py", hits={1: 1})]
        hits, unmatched = match(cov, ["a.py"])
        self.assertEqual(hits, {})
        self.assertEqual(unmatched, {"a.py": "ambiguous"})

    def test_equal_residuals_merge_by_summing_hits(self) -> None:
        cov = [entry("/ci/repo/src/a.py", hits={1: 1, 2: 0}),
               entry("/ci/repo/src/a.py", hits={2: 3, 4: 0})]
        hits, unmatched = match(cov, ["src/a.py"])
        self.assertEqual(hits, {"src/a.py": {1: 1, 2: 3, 4: 0}})
        self.assertEqual(unmatched, {})

    def test_changed_path_longer_than_entry_matches(self) -> None:
        cov = [entry("pkg/a.go", hits={5: 2})]
        hits, unmatched = match(cov, ["cmd/pkg/a.go"])
        self.assertEqual(hits, {"cmd/pkg/a.go": {5: 2}})

    def test_partial_segment_is_not_a_suffix(self) -> None:
        cov = [entry("xa.py", hits={1: 1})]
        hits, unmatched = match(cov, ["a.py"])
        self.assertEqual(hits, {})
        self.assertEqual(unmatched, {"a.py": "no candidate"})

    def test_alias_can_carry_the_suffix_match(self) -> None:
        cov = [entry("a.py", "/ci/repo/src/a.py", hits={1: 1})]
        hits, unmatched = match(cov, ["src/a.py"])
        self.assertEqual(hits, {"src/a.py": {1: 1}})

    def test_paths_are_normalised_before_matching(self) -> None:
        cov = [entry(".\\src\\a.py", hits={1: 1})]
        hits, unmatched = match(cov, ["./src/a.py"])
        self.assertEqual(hits, {"./src/a.py": {1: 1}})

    def test_empty_coverage_reports_no_candidate(self) -> None:
        hits, unmatched = match([], ["a.py"])
        self.assertEqual(hits, {})
        self.assertEqual(unmatched, {"a.py": "no candidate"})


class MatchPropertyTest(unittest.TestCase):
    SEGMENTS = ["src", "pkg", "a", "b", "lib", "x"]
    NAMES = ["util.py", "main.py", "a.py"]

    def random_path(self, rng: random.Random) -> str:
        depth = rng.randint(0, 3)
        segs = [rng.choice(self.SEGMENTS) for _ in range(depth)]
        return "/".join(segs + [rng.choice(self.NAMES)])

    def test_each_file_and_entry_used_at_most_once_and_order_independent(self) -> None:
        for seed in range(200):
            rng = random.Random(seed)
            changed = list({self.random_path(rng) for _ in range(rng.randint(1, 5))})
            # sentinel line numbers identify which entries contributed
            cov = [Entry([self.random_path(rng)] + [self.random_path(rng) for _ in range(rng.randint(0, 1))],
                         {1000 + i: 1})
                   for i in range(rng.randint(0, 6))]
            hits, unmatched = match(cov, changed)
            self.assertEqual(set(hits) | set(unmatched), set(changed), seed)
            self.assertEqual(set(hits) & set(unmatched), set(), seed)
            seen: dict[int, str] = {}
            for path, merged in hits.items():
                self.assertTrue(merged, seed)
                for line in merged:
                    self.assertNotIn(line, seen, f"seed {seed}: entry used by {seen.get(line)} and {path}")
                    seen[line] = path
            for reason in unmatched.values():
                self.assertIn(reason, ("no candidate", "ambiguous"))

            shuffled_cov = list(cov)
            rng.shuffle(shuffled_cov)
            shuffled_changed = list(changed)
            rng.shuffle(shuffled_changed)
            hits2, unmatched2 = match(shuffled_cov, shuffled_changed)
            self.assertEqual(hits2, hits, seed)
            self.assertEqual(unmatched2, unmatched, seed)


class ArithmeticTest(unittest.TestCase):
    def test_diff_coverage_counts_only_added_lines_with_data(self) -> None:
        self.assertEqual(diff_coverage({1, 2, 3, 4}, {1: 1, 2: 0, 3: 5, 9: 1}), (2, 3))

    def test_diff_coverage_zero_denominator_is_none(self) -> None:
        self.assertIsNone(diff_coverage({1, 2}, {3: 1}))
        self.assertIsNone(diff_coverage(set(), {1: 1}))
        self.assertIsNone(diff_coverage({1}, {}))

    def test_overall_merges_repeated_entries_by_normalised_primary_path(self) -> None:
        cov = [Entry(["src/a.py"], {1: 1, 2: 0}),
               Entry(["./src\\a.py"], {2: 2, 3: 0}),
               Entry(["b.py", "src/a.py"], {1: 0})]
        # a.py: lines 1,2,3 with 2 covered; b.py: line 1 uncovered
        self.assertEqual(overall(cov), (2, 4))

    def test_overall_empty(self) -> None:
        self.assertEqual(overall([]), (0, 0))


if __name__ == "__main__":
    unittest.main()

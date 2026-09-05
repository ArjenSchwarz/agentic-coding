"""Tests card and Tests section built from the review JSON ``tests`` block.

``build_tests`` parses the JUnit and coverage inputs, matches coverage to
the changed files, and returns the card, the section, the uncovered line
sets for the per-file diffs, and the counts behind the ``summary`` lines.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .common import escape, file_anchor
from .coverage import Coverage, apply_path_map, diff_coverage, match, overall, parse_coverage
from .diffs import added_lines, is_binary
from .inputs import read_json
from .junit import OUTCOMES, Case, parse_junit
from .redact import clean_message
from .warnings import Warnings

UPLOAD_STATES = ("no run", "artifacts absent", "artifacts expired")
UPLOAD_SENTENCE = (
    "To enable this section, the workflow must upload a JUnit XML file as an artifact, "
    "and a coverage file in a supported format (lcov, Cobertura XML, or Go coverprofile) "
    "to enable coverage."
)
REASON_TEXT = {
    "no tests found": "No tests were found.",
    "runner not detected": "The test runner could not be detected.",
    "required tool missing": "A required tool is missing.",
    "local run failed": "The local test run failed before writing results.",
    "local run timed out": "The local test run timed out before writing results.",
}
OUTCOME_TEXT = {"passed": "passed", "failed": "failed", "timed_out": "timed out", "not_run": "not run"}
SCOPE_TEXT = {"repository": "every test in the repository",
              "project-configured": "as the project configures it"}
DASH = "—"


@dataclass
class TestsResult:
    card_html: str
    section_html: str
    uncovered: dict[str, set[int]] = field(default_factory=dict)
    counts: dict[str, int] = field(default_factory=dict)


# --- small formatting helpers ---------------------------------------------

def _pct(num: int, den: int) -> str:
    return f"{round(100 * num / den)}%"


def _pct1(num: int, den: int) -> str:
    return f"{100 * num / den:.1f}%"


def _plural(n: int, word: str) -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _source_label(source: str | None) -> str:
    return "CI" if source == "ci" else "a local run"


def _link(url: object, text: str) -> str:
    return f'<a href="{escape(url)}">{text}</a>' if url else text


def _tally(cases: list[Case]) -> dict[str, int]:
    counts = dict.fromkeys(OUTCOMES + ("flaky",), 0)
    for c in cases:
        counts[c.outcome] = counts.get(c.outcome, 0) + 1
        if c.flaky:
            counts["flaky"] += 1
    return counts


def _list(items: list[str]) -> str:
    return "<ul>" + "".join(f"<li>{item}</li>" for item in items) + "</ul>"


def _table(headers: list[str], rows: list[str]) -> str:
    head = "".join(f"<th>{h}</th>" for h in headers)
    return (f'<table class="tests"><thead><tr>{head}</tr></thead>'
            f'<tbody>{"".join(rows)}</tbody></table>')


# --- section parts ------------------------------------------------------------

def _provenance(block: dict) -> str:
    prov = block.get("provenance") or {}
    source = prov.get("source")
    bits = []
    if source == "ci":
        bits.append("Source: <strong>CI</strong>")
        ids = prov.get("run_ids") or []
        urls = prov.get("run_urls") or []
        runs = [_link(urls[i] if i < len(urls) else None, f"run {escape(rid)}")
                for i, rid in enumerate(ids)]
        if runs:
            bits.append(", ".join(runs))
    else:
        text = "Source: <strong>local run</strong>"
        if prov.get("timestamp"):
            text += f" at {escape(prov['timestamp'])}"
        bits.append(text)
    snapshot = prov.get("snapshot") or {}
    if snapshot.get("sha"):
        text = f"snapshot <code>{escape(snapshot['sha'])}</code>"
        if snapshot.get("dirty"):
            text += " (dirty working tree)"
        bits.append(text)
    if prov.get("ci_state"):
        bits.append(f"CI state: <strong>{escape(prov['ci_state'])}</strong>")
    if prov.get("fallback_state"):
        bits.append(f"Fallback: <strong>{escape(prov['fallback_state'])}</strong>")
    lines = [f'<p class="tests-provenance">{" · ".join(bits)}</p>']

    base = block.get("baseline_provenance")
    if base:
        if base.get("source") == "ci":
            text = "Baseline: CI"
            if base.get("run_id") is not None:
                text += " " + _link(base.get("run_url"), f"run {escape(base['run_id'])}")
        else:
            text = "Baseline: local run"
            if base.get("timestamp"):
                text += f" at {escape(base['timestamp'])}"
        if base.get("sha"):
            text += f" at <code>{escape(base['sha'])}</code>"
    else:
        text = "Baseline: none"
    lines.append(f'<p class="tests-provenance">{text}</p>')
    return "\n".join(lines)


def _files_read(label: str, read: int, listed: int) -> str:
    if not listed:
        return f"{label}: none"
    if read == listed:
        return f"{label}: {_plural(listed, 'file')}"
    return f"{label}: {read} of {listed} files read"


def _availability(block: dict, junit_read: int, coverage_read: int, baseline: bool) -> str:
    outcome = OUTCOME_TEXT.get(block.get("run_outcome"), escape(block.get("run_outcome") or "unknown"))
    execution = f"Execution: <strong>{outcome}</strong>"
    if block.get("partial"):
        execution += " (partial results)"
    junit = _files_read("JUnit", junit_read, len(block.get("junit") or []))
    cov = _files_read("Coverage", coverage_read, len(block.get("coverage") or []))
    base = "Baseline: present" if baseline else "Baseline: absent"
    return f'<p class="tests-availability">{execution} · {junit} · {cov} · {base}</p>'


def _no_data_card(block: dict) -> str:
    reason = block.get("no_data_reason")
    prov = block.get("provenance") or {}
    ci_state = prov.get("ci_state")
    if reason == "ci" or (reason is None and prov.get("source") == "ci" and ci_state):
        text = f"No results from CI. CI state: <strong>{escape(ci_state)}</strong>."
        if prov.get("fallback_state"):
            text += f" Local fallback: <strong>{escape(prov['fallback_state'])}</strong>."
        if ci_state in UPLOAD_STATES:
            text += " " + UPLOAD_SENTENCE
    elif reason:
        text = REASON_TEXT.get(reason, escape(reason))
    else:
        text = "No test results were read from the inputs."
    return f'<div class="card tests-nodata"><h3>No test results</h3><p>{text}</p></div>'


def _jobs_table(block: dict, cases: list[Case]) -> str:
    jobs = block.get("jobs") or []
    artifacts = block.get("artifacts") or []
    if not jobs and not artifacts:
        return ""
    by_source: dict[str, list[Case]] = {}
    for c in cases:
        by_source.setdefault(c.source, []).append(c)

    def artifact_cases(a: dict) -> list[Case]:
        return [c for name in a.get("junit") or [] for c in by_source.get(name, [])]

    def cells(tally: dict[str, int] | None) -> str:
        if tally is None:
            return "".join(f"<td>{DASH}</td>" for _ in range(4))
        return "".join(f"<td>{tally[k]}</td>" for k in ("passed", "failed", "skipped", "errored"))

    rows = []
    for job in jobs:
        attributed = [a for a in artifacts if a.get("job") == job.get("name")]
        tally = _tally([c for a in attributed for c in artifact_cases(a)]) if attributed else None
        rows.append(f"<tr><td>{_link(job.get('url'), escape(job.get('name')))}</td>"
                    f"<td>{escape(job.get('outcome') or DASH)}</td>{cells(tally)}</tr>")
    for a in artifacts:
        if a.get("job"):
            continue
        rows.append(f"<tr><td>artifact <code>{escape(a.get('name'))}</code></td><td>{DASH}</td>"
                    f"{cells(_tally(artifact_cases(a)))}</tr>")
    return "<h3>Jobs</h3>\n" + _table(["Job", "Outcome", "Passed", "Failed", "Skipped", "Errored"], rows)


def _failed_table(block: dict, cases: list[Case]) -> str:
    failed = [c for c in cases if c.outcome in ("failed", "errored")]
    if not failed:
        return ""
    where: dict[str, str] = {}
    for a in block.get("artifacts") or []:
        label = escape(a.get("job")) if a.get("job") else f"artifact {escape(a.get('name'))}"
        for name in a.get("junit") or []:
            where.setdefault(name, label)
    rows = [f"<tr><td>{escape(c.suite)}</td><td>{escape(c.name)}</td>"
            f"<td>{where.get(c.source, DASH)}</td><td>{escape(clean_message(c.message))}</td></tr>"
            for c in failed]
    return "<h3>Failed tests</h3>\n" + _table(["Suite", "Test", "Job or artifact", "Message"], rows)


def _new_removed(block: dict, head: list[Case], base: list[Case],
                 diff_dir: Path | None, warnings: Warnings) -> tuple[str, int | None]:
    """Section HTML and the new-test count for the card (``None`` when unknown)."""
    prov = block.get("provenance") or {}
    base_prov = block.get("baseline_provenance") or {}
    if base:
        head_ids = {(c.suite, c.name) for c in head}
        base_ids = {(c.suite, c.name) for c in base}
        new = sorted(head_ids - base_ids)
        removed = sorted(base_ids - head_ids)
        parts = ['<p class="muted">Derived by identity, from the baseline run.</p>']
        if prov.get("source") != base_prov.get("source"):
            parts.append('<p class="callout callout-warning">This comparison crosses sources: '
                         f"head from {_source_label(prov.get('source'))}, baseline from "
                         f"{_source_label(base_prov.get('source'))}. Tests that only run in one "
                         "source appear as new or removed.</p>")
        items = [f"+ <code>{escape(s)}</code> {escape(n)}" for s, n in new]
        items += [f"− <code>{escape(s)}</code> {escape(n)}" for s, n in removed]
        parts.append(_list(items) if items else '<p class="muted">No new or removed tests.</p>')
        return "<h3>New and removed tests</h3>\n" + "\n".join(parts), len(new)

    name = block.get("diff_tests_file")
    if name and diff_dir is not None:
        data = read_json(diff_dir / name, warnings, "diff-derived test list")
        if isinstance(data, dict):
            added = [str(x) for x in data.get("added") or []]
            removed = [str(x) for x in data.get("removed") or []]
            unpatterned = [str(x) for x in data.get("unpatterned_files") or []]
            parts = ['<p class="muted">Derived by declaration name, from the diff (no baseline run).</p>']
            items = [f"+ {escape(n)}" for n in added]
            items += [f"− {escape(n)}" for n in removed]
            parts.append(_list(items) if items else '<p class="muted">No new or removed test declarations.</p>')
            if unpatterned:
                files = ", ".join(f"<code>{escape(f)}</code>" for f in unpatterned)
                parts.append(f'<p class="muted">No declaration pattern applies to {files}; '
                             "those files yield nothing.</p>")
            return "<h3>New and removed tests</h3>\n" + "\n".join(parts), len(added)

    return ("<h3>New and removed tests</h3>\n"
            '<p class="muted">Not available: no baseline run and no diff-derived list.</p>'), None


def _coverage_parts(block: dict, files: list[dict], fragments: dict[str, str],
                    cov: Coverage, base_cov: Coverage) -> tuple[str, dict[str, set[int]], dict[str, int], str]:
    """Diff-coverage table, overall coverage, and unmatched report.

    Returns the HTML, the uncovered sets, the matched/unmatched counts, and
    the card's diff-coverage value. With no coverage entries there is
    nothing to match: every part is omitted and both counts are zero.
    """
    if not cov:
        return "", {}, {"matched": 0, "unmatched": 0}, "n/a"
    eligible = [f.get("path", "") for f in files
                if f.get("badge") != "Deleted" and not is_binary(fragments.get(f.get("path", ""), ""))]
    hits, unmatched = match(cov, eligible)
    counts = {"matched": len(hits), "unmatched": len(unmatched)}
    uncovered: dict[str, set[int]] = {}
    rows = []
    total_covered = total_measurable = 0
    for path in eligible:
        added = added_lines(fragments.get(path, ""))
        result = diff_coverage(added, hits[path]) if path in hits else None
        cell = f"<td>{DASH}</td><td>no coverage data</td>"
        if result is not None:
            covered, measurable = result
            total_covered += covered
            total_measurable += measurable
            cell = f"<td>{covered}</td><td>{_pct(covered, measurable)}</td>"
            zero = {n for n in added if hits[path].get(n) == 0}
            if zero:
                uncovered[path] = zero
        rows.append(f'<tr><td><a href="#{file_anchor(path)}">{escape(path)}</a></td>'
                    f"<td>{len(added)}</td>{cell}</tr>")

    parts = ["<h3>Diff coverage</h3>"]
    if rows:
        parts.append(_table(["File", "Added lines", "Covered", "Diff coverage"], rows))
    if total_measurable:
        aggregate = _pct(total_covered, total_measurable)
        card_value = f"{aggregate} ({total_covered} of {total_measurable} added lines)"
        parts.append(f"<p>Aggregate diff coverage: <strong>{aggregate}</strong> "
                     f"({total_covered} of {total_measurable} measurable added lines).</p>")
    else:
        card_value = "n/a"
        parts.append('<p class="muted">No changed file has measurable added lines.</p>')

    covered, instrumented = overall(cov)
    if instrumented:
        text = f"Head <strong>{_pct1(covered, instrumented)}</strong> ({covered} of {instrumented} lines)"
        base_covered, base_instrumented = overall(base_cov)
        if base_instrumented:
            delta = 100 * covered / instrumented - 100 * base_covered / base_instrumented
            text += (f" · baseline <strong>{_pct1(base_covered, base_instrumented)}</strong> "
                     f"({base_covered} of {base_instrumented} lines) · delta <strong>{delta:+.1f} pp</strong>")
        parts.append(f"<h3>Overall coverage</h3>\n<p>{text}</p>")
        prov = block.get("provenance") or {}
        base_prov = block.get("baseline_provenance") or {}
        if base_instrumented and prov.get("source") != base_prov.get("source"):
            parts.append('<p class="callout callout-warning">The baseline coverage comes from a different '
                         f"source: head from {_source_label(prov.get('source'))}, baseline from "
                         f"{_source_label(base_prov.get('source'))}.</p>")

    parts.append(f'<p class="tests-matching">{len(hits)} of {len(eligible)} changed files matched coverage data.</p>')
    if unmatched:
        parts.append(_list([f"<code>{escape(p)}</code> — {escape(reason)}"
                            for p, reason in unmatched.items()]))
    return "\n".join(parts), uncovered, counts, card_value


def _card(pass_rate: str, new_tests: str, diff_cov: str) -> str:
    return f"""<div class="card">
      <h3>Tests</h3>
      <p>Pass rate: {pass_rate}</p>
      <p>New tests: {new_tests}</p>
      <p>Diff coverage: {diff_cov}</p>
      <p><a href="#tests">Jump to tests →</a></p>
    </div>"""


# --- entry point --------------------------------------------------------------

def build_tests(block: dict, files: list[dict], fragments: dict[str, str],
                diff_dir: Path | None, warnings: Warnings) -> TestsResult:
    def inputs(key: str) -> list[Path]:
        names = block.get(key) or []
        return [diff_dir / n for n in names] if diff_dir is not None else []

    def coverage(key: str) -> tuple[Coverage, int]:
        """Mapped entries and the number of listed files that yielded any."""
        cov: Coverage = []
        read = 0
        for path in inputs(key):
            entries = parse_coverage(path, warnings)
            read += bool(entries)
            cov.extend(entries)
        path_map = block.get("path_map") or {}
        return apply_path_map(cov, path_map.get("strip"), path_map.get("prepend")), read

    head = parse_junit(inputs("junit"), warnings)
    base = parse_junit(inputs("baseline_junit"), warnings)
    cov, coverage_read = coverage("coverage")
    base_cov, _ = coverage("baseline_coverage")

    tally = _tally(head)
    denominator = tally["passed"] + tally["failed"] + tally["errored"]
    pass_rate = f"{_pct(tally['passed'], denominator)} ({tally['passed']} of {denominator})" if denominator else "n/a"

    parts = ['<section id="tests">', "<h2>Tests</h2>", _provenance(block),
             _availability(block, len({c.source for c in head}), coverage_read,
                           bool(base) or bool(base_cov))]
    scope = block.get("coverage_scope")
    if scope:
        parts.append(f'<p class="muted">Coverage scope: {SCOPE_TEXT.get(scope, escape(scope))}</p>')
    if not head:
        parts.append(_no_data_card(block))
    else:
        parts.append(f'<p class="tests-totals">Totals: <strong>{tally["passed"]} passed</strong> · '
                     f'{tally["failed"]} failed · {tally["skipped"]} skipped · '
                     f'{tally["errored"]} errored · {tally["flaky"]} flaky</p>')
    pending = block.get("pending_runs") or []
    if pending:
        parts.append("<h3>Pending runs</h3>\n" + _list([
            f"{_link(r.get('url'), escape(r.get('name')))} (run {escape(r.get('run_id'))}, {escape(r.get('status'))})"
            for r in pending]))
    parts.append(_jobs_table(block, head))
    parts.append(_failed_table(block, head))

    new_removed_html, new_count = _new_removed(block, head, base, diff_dir, warnings)
    parts.append(new_removed_html)

    coverage_html, uncovered, match_counts, diff_cov_value = _coverage_parts(
        block, files, fragments, cov, base_cov)
    parts.append(coverage_html)

    touched = block.get("run_touched_files") or []
    if touched:
        parts.append("<h3>Files touched by the run</h3>\n"
                     '<p class="callout callout-warning">The test run changed these tracked files; '
                     "they were restored afterwards.</p>\n"
                     + _list([f"<code>{escape(p)}</code>" for p in touched]))
    skipped = block.get("skipped_artifacts") or []
    if skipped:
        parts.append("<h3>Skipped artifacts</h3>\n" + _list([
            f"<code>{escape(a.get('name'))}</code> ({escape(a.get('size_in_bytes'))} bytes)" for a in skipped]))
    if warnings.items:
        parts.append("<h3>Warnings</h3>\n" + _list([escape(w) for w in warnings.items]))
    parts.append("</section>")

    counts = dict(tally)
    counts.update(match_counts)
    return TestsResult(
        card_html=_card(pass_rate, "n/a" if new_count is None else str(new_count), diff_cov_value),
        section_html="\n".join(p for p in parts if p),
        uncovered=uncovered,
        counts=counts,
    )

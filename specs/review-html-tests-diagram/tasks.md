---
references:
    - specs/review-html-tests-diagram/requirements.md
    - specs/review-html-tests-diagram/design.md
    - specs/review-html-tests-diagram/decision_log.md
---
# review-html-tests-diagram

## Foundation

- [x] 1. Write the golden-fixture regression test and the test harness scaffold <!-- id:vt4kkmn -->
  - Create scripts/tests/__init__.py and scripts/tests/fixtures/golden.json exercising every existing section (pr_description, commits, explanation, important_changes with rationale_unknown and rationale_inferred, decisions, findings with all statuses, unresolved_comments with replies, files with inline diff and diff_file, double_check, publish_metadata)
  - Generate fixtures/golden.html by running `git show 9da40cf:scripts/build_review_html.py` from a temp file against golden.json; commit the HTML
  - The golden test renders via `python3 scripts/build_review_html.py` by repo-relative path, replaces the `<style>` contents and the `Generated …` footer line in both documents, and asserts equality
  - Add a Makefile with `test: cd scripts && python3 -m unittest discover -s tests -t .` and document it in scripts/README.md alongside blast_radius.py and ecosystems.json entries added later
  - Stream: 1
  - Requirements: [6.1](requirements.md#6.1), [6.5](requirements.md#6.5), [6.6](requirements.md#6.6)
  - References: scripts/build_review_html.py, scripts/tests/, Makefile

- [x] 2. Restructure the renderer into the review_html package with a thin entry point <!-- id:vt4kkmo -->
  - Modules: __init__.py exporting render; common.py with escape, digest (sha1[:10]), file_anchor, severity_pill; sections.py with the existing renderers; css.py; template.py; render.py with render(); every module starts with `from __future__ import annotations`
  - Entry point keeps argparse and the command line, inserts Path(__file__).resolve().parent on sys.path before `import review_html`
  - New placeholders are not added yet; the golden test must still pass
  - Do not move the CSS into the template literal; keep it as a substituted value
  - Blocked-by: vt4kkmn (Write the golden-fixture regression test and the test harness scaffold)
  - Stream: 1
  - Requirements: [6.1](requirements.md#6.1), [6.3](requirements.md#6.3), [6.5](requirements.md#6.5), [2.11](requirements.md#2.11)
  - References: scripts/build_review_html.py, scripts/review_html/

- [x] 3. Write tests for inputs.read_guarded and the Warnings collector <!-- id:vt4kkmp -->
  - read_guarded rejects a file over 50 MB by stat (use a sparse temp file), rejects xml=True inputs whose first 64 KB contain `<!DOCTYPE`, returns None with a warning for non-UTF-8 content, and returns text otherwise
  - Warnings.add appends and prints `warning: …` to stderr immediately; items preserves order
  - Blocked-by: vt4kkmo (Restructure the renderer into the review_html package with a thin entry point)
  - Stream: 1
  - Requirements: [2.10](requirements.md#2.10), [2.11](requirements.md#2.11)
  - References: scripts/review_html/inputs.py, scripts/review_html/warnings.py

- [x] 4. Implement inputs.read_guarded and Warnings to pass the tests <!-- id:vt4kkmq -->
  - Both modules are pure standard library; read_guarded is the only file reader the rest of the package uses
  - Blocked-by: vt4kkmp (Write tests for inputs.read_guarded and the Warnings collector)
  - Stream: 1
  - Requirements: [2.10](requirements.md#2.10), [2.11](requirements.md#2.11)

- [x] 5. Write tests for diffs: load_fragments, added_lines, is_binary, and render_diff with uncovered marks <!-- id:vt4kkmr -->
  - added_lines: hunk headers `@@ -a,b +c,d @@`, multiple hunks, renames, `\ No newline at end of file`, a `/dev/null` fragment from `git diff --no-index`
  - is_binary: lines starting `Binary files ` or `GIT binary patch`
  - load_fragments: inline diff wins over diff_file; missing file yields the existing `(diff fragment 'x' missing)` placeholder; non-UTF-8 yields `(diff fragment 'x' is not UTF-8)` plus a warning
  - render_diff with uncovered=None must equal today's _render_diff output; with a set, matching `+` lines carry `diff-add diff-uncovered` and context or `-` lines never do
  - Blocked-by: vt4kkmq (Implement inputs.read_guarded and Warnings to pass the tests)
  - Stream: 1
  - Requirements: [3.8](requirements.md#3.8), [2.10](requirements.md#2.10), [3.6](requirements.md#3.6)
  - References: scripts/review_html/diffs.py

- [x] 6. Implement diffs.py and wire load_fragments into render_files <!-- id:vt4kkms -->
  - render() calls load_fragments once and passes the dict to render_files together with an uncovered map (empty for now)
  - Append the `.diff-uncovered` rule to css.py: 3 px `--error` left border and a `▌` gutter marker via ::before
  - Golden test still passes
  - Blocked-by: vt4kkmr (Write tests for diffs: load_fragments, added_lines, is_binary, and render_diff with uncovered marks)
  - Stream: 1
  - Requirements: [3.8](requirements.md#3.8), [2.10](requirements.md#2.10), [6.1](requirements.md#6.1)

## Blast radius

- [x] 7. Write unit and property tests for diagram.project <!-- id:vt4kkmt -->
  - Column assignment: changed to centre, unchanged with an edge into changed to dependents, unchanged with an edge from changed to dependencies, both to dependents
  - Order: test exclusion, expansion collapse, cap; test counts include changed test files; collapse only groups with more than 3 nodes whose every centre edge has granularity package; nodes with any file-granular edge stay
  - Collapsed node: label `<group> (N files)`, id digest of member paths joined with newline, rank key sum of member edges; cap ranks by (-edges_to_changed, path) with first member path for collapsed nodes; centre never capped
  - Groups ordered by name, nodes by path; column_status partial keeps nodes, failed keeps none
  - Property tests with random.Random(seed) over 200 cases: identical output for identical input, no side column over 15, no empty side column without a failed status
  - Blocked-by: vt4kkmo (Restructure the renderer into the review_html package with a thin entry point)
  - Stream: 2
  - Requirements: [4.6](requirements.md#4.6), [4.7](requirements.md#4.7), [4.8](requirements.md#4.8), [4.10](requirements.md#4.10), [4.11](requirements.md#4.11)
  - References: scripts/review_html/diagram.py

- [x] 8. Implement diagram.project to pass the tests <!-- id:vt4kkmu -->
  - Define the Projected dataclass per the design; keep project() free of any SVG concerns so layout tests can build Projected directly
  - Blocked-by: vt4kkmt (Write unit and property tests for diagram.project)
  - Stream: 2
  - Requirements: [4.6](requirements.md#4.6), [4.7](requirements.md#4.7), [4.8](requirements.md#4.8), [4.10](requirements.md#4.10), [4.11](requirements.md#4.11)

- [x] 9. Write unit and property tests for diagram.layout and render_diagram <!-- id:vt4kkmv -->
  - Constants: ADV 7.2, PAD 10, BOX_H 26, ROW_GAP 8, GROUP_PAD 8, GROUP_HEADER 18, GROUP_GAP 14, GUTTER 56, LANE 24, CONTENT_W 1036, COL_W 308, SIDE_BOX_W 292, CENTRE_BOX_W 268; budgets 37 and 30
  - Property: every text element's textLength + 2·PAD ≤ its box width, including badges and group labels; declared width equals 1036; centre-to-centre path x coordinates stay within the lane
  - Markup: node `<g id="n-<digest>">` with `<title>`, rect, label text, `⚑N` badge only on changed nodes with N > 0; changed nodes wrapped in `<a href="#file-<digest>">`; edges with class `edge e-<src> e-<dst>`, data-from, data-to, marker-end; side edges attach right-middle to left-middle or the reverse when the target is left of the source
  - Fills and strokes use `var(--x, #literal)`; collapsed nodes dashed; failed column shows the reason text in place; partial shows nodes plus reason; package-granularity note under the header
  - Section: `<div class="blast-scroll">` container, legend swatch row, collapsed-member `<ul>`, skipped list, per-node `:has()` hover rules in a `<style>` element
  - Escaping of `<`, `&`, `"`, `$` in paths; absent or invalid description omits the section with a stderr warning and exit 0
  - Blocked-by: vt4kkmu (Implement diagram.project to pass the tests)
  - Stream: 2
  - Requirements: [5.1](requirements.md#5.1), [5.2](requirements.md#5.2), [5.3](requirements.md#5.3), [5.4](requirements.md#5.4), [5.5](requirements.md#5.5), [5.6](requirements.md#5.6), [5.7](requirements.md#5.7), [5.8](requirements.md#5.8), [5.9](requirements.md#5.9), [5.10](requirements.md#5.10), [5.11](requirements.md#5.11), [5.12](requirements.md#5.12)
  - References: scripts/review_html/diagram.py, scripts/review_html/css.py

- [x] 10. Implement diagram.layout and render_diagram and wire the diagram section into render <!-- id:vt4kkmw -->
  - Wire into render(): `diagram_file` loaded through read_guarded relative to the diff directory; top-level `change_classification == "docs-only"` suppresses the section without warnings
  - Append `$unresolved_comments_section$diagram_section` on the existing template line; add `"diagram": "Blast radius"` to toc_labels
  - CSS for .blast-scroll (overflow-x auto) and legend; golden test still passes
  - Blocked-by: vt4kkmv (Write unit and property tests for diagram.layout and render_diagram)
  - Stream: 2
  - Requirements: [5.1](requirements.md#5.1), [5.2](requirements.md#5.2), [5.3](requirements.md#5.3), [5.4](requirements.md#5.4), [5.5](requirements.md#5.5), [5.6](requirements.md#5.6), [5.7](requirements.md#5.7), [5.8](requirements.md#5.8), [5.9](requirements.md#5.9), [5.10](requirements.md#5.10), [5.11](requirements.md#5.11), [5.12](requirements.md#5.12), [3.11](requirements.md#3.11), [6.1](requirements.md#6.1), [6.4](requirements.md#6.4)

- [x] 11. Write tests for blast_radius.py against a generated git repository <!-- id:vt4kkmx -->
  - Build a repository with `git init` in tempfile holding Go (two packages, go.mod), Python (src layout, relative and absolute imports), TypeScript (relative imports, index.ts, .js-to-.ts mapping), and Rust (`mod foo;` and `use crate::`); commit a base, then a snapshot with added, modified, deleted, renamed, copied (-C), and type-changed files, one untracked file for working-tree mode, one 1 MB+ blob, a symlink, and test files importing changed files
  - Assert diagram.json: nodes with status, group, is_test, old_path; edges with method, granularity, tree (base for deleted and old renamed paths); column_status complete, failed for an extension without patterns, partial for the remote cap; skipped entries
  - Assert diff-tests.json: added and removed names from test_decl on the diff, unpatterned_files
  - Cover --snapshot working-tree (disk reads, untracked as added) and a SHA snapshot (cat-file --batch); --tools with a stub tool command; --remote by monkeypatching the gh calls
  - Blocked-by: vt4kkmo (Restructure the renderer into the review_html package with a thin entry point)
  - Stream: 2
  - Requirements: [4.1](requirements.md#4.1), [4.2](requirements.md#4.2), [4.3](requirements.md#4.3), [4.4](requirements.md#4.4), [4.5](requirements.md#4.5), [4.9](requirements.md#4.9), [4.10](requirements.md#4.10), [4.12](requirements.md#4.12), [1.12](requirements.md#1.12)
  - References: scripts/blast_radius.py, scripts/ecosystems.json, scripts/tests/

- [x] 12. Implement blast_radius.py and the script-read rows of ecosystems.json <!-- id:vt4kkmy -->
  - Steps and resolvers per the design: changed files via `git diff --name-status -M -C -z` with C as added and T as modified; tree via `git ls-tree -r -l -z` parsed with partition('\t'), skipping modes 120000 and 160000 and blobs over 1 MB; `git cat-file --batch` for SHA trees; trees and blobs API for --remote with the 500-call cap and truncated check
  - Resolvers relative, roots (separator, source_roots, one-segment retry), unit (module_file with module_regex, target_root, directory)
  - Write ecosystems.json with the script-read keys for go, python, typescript, swift, rust; runner keys come in task 23
  - Emit diff-tests.json from test_decl over the diff of changed test files
  - Write --out DIR/diagram.json and DIR/diff-tests.json; document the CLI in scripts/README.md
  - Blocked-by: vt4kkmx (Write tests for blast_radius.py against a generated git repository)
  - Stream: 2
  - Requirements: [4.1](requirements.md#4.1), [4.2](requirements.md#4.2), [4.3](requirements.md#4.3), [4.4](requirements.md#4.4), [4.5](requirements.md#4.5), [4.9](requirements.md#4.9), [4.10](requirements.md#4.10), [4.12](requirements.md#4.12), [1.12](requirements.md#1.12)

## Test results

- [x] 13. Write tests for junit.parse_junit <!-- id:vt4kkmz -->
  - Fixtures: nested testsuites, empty classname falling back to the testsuite name, Surefire flakyFailure and rerunFailure, pytest `rerun` with one element per attempt sharing (suite, name), skipped, error, message attribute versus element text
  - Assert per-source collapse: duplicates within one file become one case with the last element's outcome and flaky when an earlier attempt failed; identical identities across two source files stay separate
  - Assert source is the input file name
  - Blocked-by: vt4kkms (Implement diffs.py and wire load_fragments into render_files)
  - Stream: 1
  - Requirements: [2.1](requirements.md#2.1), [2.2](requirements.md#2.2)
  - References: scripts/review_html/junit.py

- [x] 14. Implement junit.py to pass the tests <!-- id:vt4kkn0 -->
  - Use read_guarded with xml=True; outcome precedence failure, error, flaky elements, skipped, passed
  - Blocked-by: vt4kkmz (Write tests for junit.parse_junit)
  - Stream: 1
  - Requirements: [2.1](requirements.md#2.1), [2.2](requirements.md#2.2)

- [x] 15. Write unit and property tests for coverage parsing, path mapping, matching, diff coverage, and overall <!-- id:vt4kkn1 -->
  - Parsers: lcov with repeated SF for one file, Cobertura with two source roots producing aliases, coverprofile in set and count modes with overlapping blocks taking the maximum
  - apply_path_map on primary paths and aliases after normalisation, whole segments only
  - match as five passes: the util.py plus a/util.py versus src/a/util.py case must match a/util.py; exact match leaves the pool; an entry in two pools is removed once and both files report ambiguous; distinct residuals report ambiguous; equal residuals merge by summing hits; an entry whose aliases equal two changed files is ambiguous for both
  - diff_coverage returns None on a zero denominator; overall merges by normalised primary path so repeated entries count once
  - Property over random path sets: each changed file maps to at most one merged entry, each entry to at most one file, and shuffling inputs does not change the result
  - Blocked-by: vt4kkms (Implement diffs.py and wire load_fragments into render_files)
  - Stream: 1
  - Requirements: [2.3](requirements.md#2.3), [2.4](requirements.md#2.4), [2.5](requirements.md#2.5), [2.6](requirements.md#2.6), [2.7](requirements.md#2.7), [2.8](requirements.md#2.8)
  - References: scripts/review_html/coverage.py

- [x] 16. Implement coverage.py to pass the tests <!-- id:vt4kkn2 -->
  - Entry dataclass with paths (primary first) and hits; Coverage = list[Entry]; parse_coverage sniffs the format from content and uses read_guarded (xml=True for Cobertura)
  - Blocked-by: vt4kkn1 (Write unit and property tests for coverage parsing, path mapping, matching, diff coverage, and overall)
  - Stream: 1
  - Requirements: [2.3](requirements.md#2.3), [2.4](requirements.md#2.4), [2.5](requirements.md#2.5), [2.6](requirements.md#2.6), [2.7](requirements.md#2.7), [2.8](requirements.md#2.8)

- [x] 17. Write tests for redact.redact <!-- id:vt4kkn3 -->
  - One assertion per pattern: Bearer tokens, AKIA keys, gh tokens, Slack tokens, `AWS_SECRET_ACCESS_KEY=…`, bare `KEY=…`, `password: …`, URLs with userinfo, PEM private key blocks
  - Assert that redaction happens before truncation to 500 characters by placing a secret at position 480
  - Blocked-by: vt4kkms (Implement diffs.py and wire load_fragments into render_files)
  - Stream: 1
  - Requirements: [3.4](requirements.md#3.4)
  - References: scripts/review_html/redact.py

- [x] 18. Implement redact.py to pass the tests <!-- id:vt4kkn4 -->
  - PATTERNS list in the design's order; redact applies them sequentially
  - Blocked-by: vt4kkn3 (Write tests for redact.redact)
  - Stream: 1
  - Requirements: [3.4](requirements.md#3.4)

- [x] 19. Write tests for tests_section.build_tests and the render wiring <!-- id:vt4kkn5 -->
  - Card: three lines with n/a values and a section link when there is no data
  - Section order: provenance with CI link and both states; availability line; coverage_scope; totals with flaky alongside; pending runs; per-job rows with counts only when attributed, per-artifact rows otherwise; failed tests with job or artifact; new and removed by identity from baseline or by name from diff_tests_file with the source label and the cross-source note; per-file table excluding Deleted badges and binary fragments and showing 'no coverage data' for no candidate, ambiguous, and zero-denominator files; overall coverage with delta and cross-source note; unmatched report; run_touched_files, skipped_artifacts, warnings
  - No-data card derived from no_data_reason, ci_state, and fallback_state, with the upload sentence for no run, artifacts absent, and artifacts expired
  - Render wiring: the two `summary` lines are the last stderr lines even when a diagram warning fires later; `summary tests:` excludes baseline cases; uncovered sets reach render_files; docs-only classification omits card and section
  - Blocked-by: vt4kkn0 (Implement junit.py to pass the tests), vt4kkn2 (Implement coverage.py to pass the tests), vt4kkn4 (Implement redact.py to pass the tests)
  - Stream: 1
  - Requirements: [3.1](requirements.md#3.1), [3.2](requirements.md#3.2), [3.3](requirements.md#3.3), [3.4](requirements.md#3.4), [3.5](requirements.md#3.5), [3.6](requirements.md#3.6), [3.7](requirements.md#3.7), [3.8](requirements.md#3.8), [3.9](requirements.md#3.9), [3.10](requirements.md#3.10), [3.11](requirements.md#3.11), [2.8](requirements.md#2.8), [2.9](requirements.md#2.9), [1.6](requirements.md#1.6), [1.12](requirements.md#1.12), [3.12](requirements.md#3.12)
  - References: scripts/review_html/tests_section.py, scripts/review_html/render.py

- [x] 20. Implement tests_section.py and wire the Tests card, section, uncovered marks, and summary lines into render <!-- id:vt4kkn6 -->
  - TestsResult dataclass per the design; append `$findings_summary$tests_card` and `$findings_section$tests_section` on the existing template lines; add `"tests": "Tests"` to toc_labels; CSS for the Tests section tables and the warning-bordered no-data card matching the unresolved-comment card treatment
  - render() prints `summary coverage:` and `summary tests:` after all other output; golden test still passes
  - Blocked-by: vt4kkn5 (Write tests for tests_section.build_tests and the render wiring)
  - Stream: 1
  - Requirements: [3.1](requirements.md#3.1), [3.2](requirements.md#3.2), [3.3](requirements.md#3.3), [3.4](requirements.md#3.4), [3.5](requirements.md#3.5), [3.6](requirements.md#3.6), [3.7](requirements.md#3.7), [3.8](requirements.md#3.8), [3.9](requirements.md#3.9), [3.10](requirements.md#3.10), [3.11](requirements.md#3.11), [2.8](requirements.md#2.8), [2.9](requirements.md#2.9), [1.6](requirements.md#1.6), [6.1](requirements.md#6.1), [6.4](requirements.md#6.4)

- [x] 21. Write the timing tests with generated large inputs <!-- id:vt4kkn7 -->
  - Generate a 10 MB lcov file and a 5,000-case JUnit file in a temp directory; assert each parses in under 5 seconds
  - Skip when os.getloadavg is unavailable or its first value exceeds os.cpu_count()
  - Blocked-by: vt4kkn0 (Implement junit.py to pass the tests), vt4kkn2 (Implement coverage.py to pass the tests)
  - Stream: 1
  - Requirements: [2.12](requirements.md#2.12)

## Ecosystem file and skills

- [x] 22. Write a schema validation test for ecosystems.json covering script and runner keys <!-- id:vt4kkn8 -->
  - Assert every row has extensions, test_files, unit, and either imports or notes; every regex compiles; test_decl has at most one group; every runner has name, detect, recipe, requires, coverage_format in {lcov, cobertura, coverprofile}, install, junit_flags; recipes only use the placeholders {junit}, {coverage}, {inputs}; env and config_files are objects when present; tool has deps and granularity
  - Blocked-by: vt4kkmy (Implement blast_radius.py and the script-read rows of ecosystems.json)
  - Stream: 3
  - Requirements: [1.5](requirements.md#1.5), [1.6](requirements.md#1.6), [4.4](requirements.md#4.4)
  - References: scripts/ecosystems.json

- [x] 23. Add the runners, notes, and detection rules to ecosystems.json to pass the schema test <!-- id:vt4kkn9 -->
  - Runners per the design: gotestsum for Go; pytest with --junitxml and --cov-report=xml; vitest and jest with detection rules, `npx --no-install`, and JEST_JUNIT_OUTPUT_FILE; swift test with --xunit-output plus llvm-cov export; cargo nextest with a nextest.toml config_files template and cargo llvm-cov
  - Add notes for the Swift same-target and Xcode holes and the go list failure behaviour
  - Blocked-by: vt4kkn8 (Write a schema validation test for ecosystems.json covering script and runner keys)
  - Stream: 3
  - Requirements: [1.5](requirements.md#1.5), [1.6](requirements.md#1.6)

- [x] 24. Update the pr-review-html skill for collection, diagram, JSON blocks, and severity floor <!-- id:vt4kkna -->
  - Phase 1: record headRefOid, isCrossRepository, baseRefName; merge base after checkout; disclosure sentence that Phases 4 and 5 execute the branch's install scripts and tests, fork PRs included
  - Phase 5: recipe selection tiers reading Makefile text, run once into $INPUTS with the 600,000 ms budget, restore procedure with pre-run copies, timed_out verdict wording
  - Phase 7: fragments from `git diff <merge-base> -- <path>` and `/dev/null` for untracked files; baseline lookup; blast_radius.py invocation with --tools; tests block, diagram_file, change_classification, diff_tests_file; severity floor via the `summary tests:` line and second render
  - Define $INPUTS with the mktemp fallback, pass --diff-dir explicitly, drop the highlight.js claim, update the when-to-edit paragraph to name the package and css.py
  - Blocked-by: vt4kkmw (Implement diagram.layout and render_diagram and wire the diagram section into render), vt4kkn6 (Implement tests_section.py and wire the Tests card, section, uncovered marks, and summary lines into render), vt4kkn9 (Add the runners, notes, and detection rules to ecosystems.json to pass the schema test)
  - Stream: 3
  - Requirements: [1.1](requirements.md#1.1), [1.5](requirements.md#1.5), [1.6](requirements.md#1.6), [1.7](requirements.md#1.7), [1.8](requirements.md#1.8), [1.11](requirements.md#1.11), [1.12](requirements.md#1.12), [1.13](requirements.md#1.13), [3.10](requirements.md#3.10), [3.11](requirements.md#3.11), [3.12](requirements.md#3.12), [4.1](requirements.md#4.1), [6.2](requirements.md#6.2), [6.4](requirements.md#6.4)
  - References: claude/skills/pr-review-html/SKILL.md

- [x] 25. Update the pr-overview skill for CI artifacts, the worktree fallback, baseline, diagram, and JSON blocks <!-- id:vt4kknb -->
  - Phase 1: pin headRefOid; fetch refs/pull/<n>/head and verify FETCH_HEAD; diffs from the pinned SHA or the compare API without a clone, noting omitted patches; replace the `gh api` file-reading paragraph; read-only statement gains the 1.3 sentence and the .git ref note
  - Phase 1b: gh commands with -R and --paginate, artifact size cap, sniffing, `<run_id>-<artifact>--<basename>` naming, ordered CI-state rules, token-set job attribution, pending_runs; worktree fallback block with $WT, prune, status capture, blast_radius --tools before removal, removal on timeout
  - Phase 6: baseline with the is-ancestor exit-128 rule and compare-API fallback; blast_radius without --tools when 1b produced no diagram, --remote without a clone; JSON blocks; severity floor
  - $INPUTS definition, --diff-dir, rendering-contract fixes, when-to-edit paragraph
  - Blocked-by: vt4kkmw (Implement diagram.layout and render_diagram and wire the diagram section into render), vt4kkn6 (Implement tests_section.py and wire the Tests card, section, uncovered marks, and summary lines into render), vt4kkn9 (Add the runners, notes, and detection rules to ecosystems.json to pass the schema test)
  - Stream: 3
  - Requirements: [1.2](requirements.md#1.2), [1.3](requirements.md#1.3), [1.4](requirements.md#1.4), [1.5](requirements.md#1.5), [1.6](requirements.md#1.6), [1.7](requirements.md#1.7), [1.8](requirements.md#1.8), [1.9](requirements.md#1.9), [1.10](requirements.md#1.10), [1.11](requirements.md#1.11), [1.12](requirements.md#1.12), [1.13](requirements.md#1.13), [1.14](requirements.md#1.14), [1.15](requirements.md#1.15), [3.10](requirements.md#3.10), [3.11](requirements.md#3.11), [3.12](requirements.md#3.12), [4.1](requirements.md#4.1), [4.12](requirements.md#4.12), [6.2](requirements.md#6.2), [6.4](requirements.md#6.4)
  - References: claude/skills/pr-overview/SKILL.md

- [x] 26. Update the pre-push-review skill for the local run, diagram, JSON blocks, and severity floor <!-- id:vt4kknc -->
  - Phase 5: same recipe selection, single run, restore, and timeout wording as pr-review-html
  - Phase 7: untracked files as added with /dev/null fragments; blast_radius.py with --snapshot working-tree --base $BASE --tools; tests block without baseline; diff_tests_file; change_classification; severity floor
  - Remove the claim that malformed JSON still renders; $INPUTS definition; --diff-dir; drop the highlight.js claim; when-to-edit paragraph
  - Blocked-by: vt4kkmw (Implement diagram.layout and render_diagram and wire the diagram section into render), vt4kkn6 (Implement tests_section.py and wire the Tests card, section, uncovered marks, and summary lines into render), vt4kkn9 (Add the runners, notes, and detection rules to ecosystems.json to pass the schema test)
  - Stream: 3
  - Requirements: [1.1](requirements.md#1.1), [1.5](requirements.md#1.5), [1.6](requirements.md#1.6), [1.7](requirements.md#1.7), [1.8](requirements.md#1.8), [1.12](requirements.md#1.12), [1.13](requirements.md#1.13), [3.10](requirements.md#3.10), [3.11](requirements.md#3.11), [3.12](requirements.md#3.12), [4.1](requirements.md#4.1), [6.2](requirements.md#6.2), [6.4](requirements.md#6.4)
  - References: claude/skills/pre-push-review/SKILL.md

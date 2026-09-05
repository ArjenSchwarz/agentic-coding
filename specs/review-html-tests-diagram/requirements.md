# Requirements: review-html-tests-diagram

## Introduction

The HTML review pages produced by `pr-review-html`, `pr-overview`, and `pre-push-review` describe a change through findings, explanations, and diffs, but say nothing about whether the tests pass, what the change adds in test coverage, or where the change sits in the codebase. This feature adds a test results section, sourced from GitHub Actions artifacts or a local run, and a blast-radius diagram showing the changed files with the files that depend on them and the files they depend on. Both must work on any repository and language: the renderer understands data formats, and the skills map each ecosystem onto those formats.

## Non-Goals

- Modifying any repository's CI configuration. The page tells the user what a workflow must upload; users make that change themselves.
- Type-level class diagrams and infrastructure diagrams. Nodes in this version are files.
- Parsing free-form test runner logs. Only structured formats are read.
- Retrieving CI artifacts from anything other than GitHub Actions. GitLab support arrives when the review skills become forge-agnostic, as a separate feature.
- Executing code from fork pull requests in `pr-overview`'s local fallback. `pr-review-html` checks out and runs any PR it is asked to review, fork or not, and its skill text says so.
- Coverage trends across reviews, or enforcing coverage thresholds.
- Any JavaScript in the review page. The page remains static HTML, CSS, and inline SVG.
- Committing, pushing, or resolving anything on the reviewed branch as part of collecting test data.
- Opening a collapsed per-file diff when its anchor is followed. Existing links have the same behaviour.

## Definitions

- **Snapshot**: the exact tree that the page's diffs, test results, and coverage all describe: a pinned commit SHA for `pr-overview`; the working tree for the other two skills, identified by the HEAD SHA plus a dirty flag.
- **Base tree**: the tree the change is compared against: the merge-base commit for a PR, the remote tracking branch for `pre-push-review`.
- **Baseline**: test results and coverage produced for the base tree, used for new/removed tests and the overall coverage delta.
- **Same-repo PR**: a pull request whose head branch lives in the same repository as its base. A PR from a fork is not a same-repo PR.
- **Job directory**: a scratch directory outside every repository working tree, such as the harness job directory, used for worktrees, fetched artifacts, generated outputs, and the review JSON with its referenced inputs.
- **Ecosystem table**: one shared reference file, used by all three skills, with one row per runner or language giving the test recipe that emits JUnit XML and, where the runner supports it, a supported coverage format with repository-wide scope; the test-file path pattern; the test-declaration pattern; the unit that groups files (package, module, or target) and how to resolve an import to it; and the dependency tool if one exists.
- **Test file**: a file matching the ecosystem table's test-file pattern for its language, or, with no matching row, a file whose name or nearest directory contains `test`, `tests`, `spec`, or `__tests__`.
- **Docs-only change**: every changed file is documentation (`.md`, `.rst`, `.adoc`, or a file at any depth under a `docs/` directory), a file named `README`, `CHANGELOG`, `LICENSE`, `CONTRIBUTING`, or `CODEOWNERS` with any extension, an image, a lockfile, or an editor or VCS dotfile such as `.gitignore` or `.editorconfig`. Any other changed file, including `.txt` files elsewhere, CI workflows, build configuration, and dependency manifests, makes the change a code change.
- **Usable artifacts**: at least one artifact of the run containing a JUnit XML file. Coverage files are used when present but are not required.
- **CI state**: one of no run, run in progress or queued, run failed before upload, artifacts expired, artifacts absent, or artifacts usable, for the runs of the head SHA.
- **Fallback state**: one of not needed, ran, blocked by fork PR, blocked by no local clone, blocked by run in progress, or timed out, for the local run in `pr-overview`.
- **Suite**: a JUnit test case's `classname` attribute, or the enclosing `testsuite` name when `classname` is absent or empty.
- **Test identity**: the tuple (suite, name). Across CI jobs the same identity may appear once per job with its own outcome.
- **Pass rate**: passed divided by (passed + failed + errored), shown as a percentage. Skipped tests are excluded from both terms. With a zero denominator the pass rate is shown as `n/a`.
- **Flaky**: a passed test that carries rerun or flaky elements. Flaky is a label on a passed test, not a fifth outcome; passed, failed, skipped, and errored sum to the case count.
- **Aggregate diff coverage**: the sum of covered added lines divided by the sum of measurable added lines across all changed files with coverage data, so it is line-weighted rather than a mean of per-file percentages.
- **Overall coverage**: covered lines divided by instrumented lines across every file in the coverage data, after summing hits per line across all inputs.
- **Group**: the unit from the ecosystem table that contains a file; the file's directory when no row applies.
- **Label budget**: the maximum number of characters a node label may occupy, derived per [5.7](#5.7).
- **Content width**: the page's maximum content width, currently 1036 px (1100 px page width minus 32 px padding each side).

## Applicability

Groups 2, 5, and 6 describe the renderer and apply to every page; a criterion whose WHEN guard never fires for a skill's input is satisfied vacuously. Group 1 and the skill-specific criteria elsewhere bind as follows.

| Skill | Group 1 | Skill-specific elsewhere |
|-------|---------|--------------------------|
| pr-review-html | 1.1, 1.5 to 1.8, 1.11 to 1.13 | 3.1 to 3.12 except 3.3; 4.1 to 4.11 |
| pr-overview | 1.2 to 1.15 | 3.1 to 3.12; 4.1 to 4.12 |
| pre-push-review | 1.1, 1.5 to 1.8, 1.12, 1.13 | 3.1 to 3.12 except 3.3; 4.1 to 4.11 |

## Requirements

### 1. Test Data Collection

**User Story:** As a reviewer, I want the review to gather test results and coverage for the exact code the page describes without altering the repository, so that the numbers on the page are true of the diff I am reading.

**Acceptance Criteria:**

1. <a name="1.1"></a>`pr-review-html` and `pre-push-review` SHALL choose the test command per [1.5](#1.5) before their existing verification run, so that one run both verifies the fixes and emits JUnit XML and, where the recipe supports it, coverage; the page's per-file diffs SHALL be generated from the working tree against the base tree after the fixes are applied, not from the remote PR diff  
2. <a name="1.2"></a>`pr-overview` SHALL pin the PR head commit SHA at the start, take its diffs against the base tree from that SHA, and first look for test data in usable artifacts of the GitHub Actions runs for that SHA, identifying JUnit and coverage files inside artifacts by their content rather than by name  
3. <a name="1.3"></a>IF the CI state permits a fallback per [1.14](#1.14), the PR is a same-repo PR, and the current directory is a clone of the PR's repository THEN `pr-overview` SHALL fetch the pinned SHA, create a detached git worktree at that SHA in the job directory, install dependencies and run the tests there, and its skill text SHALL state that this executes the branch's install scripts and tests on the reviewer's machine with the reviewer's environment and credentials  
4. <a name="1.4"></a>IF the CI state permits a fallback and the PR is not a same-repo PR, or there is no local clone THEN `pr-overview` SHALL NOT run any code from the branch, and SHALL record the corresponding blocked fallback state  
5. <a name="1.5"></a>The skill SHALL select the test command without executing candidates, in this order: a Makefile target that the project documents as emitting JUnit XML, the project's own instructions, then the ecosystem table; a Makefile target or project instruction that does not emit JUnit XML SHALL be passed over in favour of the ecosystem recipe; IF no candidate applies THEN the reason SHALL be recorded as runner not detected or required tool missing  
6. <a name="1.6"></a>WHEN the ecosystem recipe is used, coverage SHALL count hits from every test in the repository, not only tests in the changed file's own package; WHEN a project-supplied command is used, coverage SHALL be used as produced and the page SHALL state that coverage scope is as the project configures it  
7. <a name="1.7"></a>Every run SHALL write JUnit and coverage outputs into the job directory, outside any working tree, and the skill SHALL read them before any worktree is removed; IF a run in the user's checkout changes tracked files THEN the skill SHALL restore them to their pre-run content without discarding uncommitted changes, and report which files were touched  
8. <a name="1.8"></a>IF a run, including dependency installation, exceeds a total budget of 10 minutes THEN the skill SHALL stop it, use any JUnit XML already written labelled as partial, and record the timeout; in `pr-review-html` and `pre-push-review` the verdict SHALL then state that fix verification is incomplete  
9. <a name="1.9"></a>A worktree created under [1.3](#1.3) SHALL live in the job directory under a recognisable name and SHALL be removed with git's worktree removal and pruned after the run, including on failure or timeout; before creating one, the skill SHALL prune only worktree entries whose directory no longer exists, and SHALL never remove a worktree that still exists on disk or is locked  
10. <a name="1.10"></a>WHEN the head SHA has several CI jobs, the skill SHALL record every job's name and outcome from the CI API; test counts SHALL be attributed to a job only when the artifact name contains the job name (token-set inclusion per Q46), and otherwise SHALL be attributed to the artifact  
11. <a name="1.11"></a>`pr-overview` and `pr-review-html` SHALL look for a baseline in the artifacts of the run for the merge-base commit, or the nearest successful base-branch run at or before it, SHALL NOT use a later base-branch run, and SHALL record the baseline's provenance separately from the head's  
12. <a name="1.12"></a>IF no baseline exists THEN new and removed tests SHALL be derived from the diff as the names of test declarations added and removed in test files, using the ecosystem table's declaration pattern, labelled as diff-derived; files with no applicable pattern SHALL yield nothing and the page SHALL say so  
13. <a name="1.13"></a>The skill SHALL record provenance as separate fields: source kind (CI or local), run identifier and URL or local timestamp, the snapshot identifier, the CI state, and for `pr-overview` the fallback state  
14. <a name="1.14"></a>The CI states no run, run failed before upload, artifacts expired, and artifacts absent SHALL each permit the fallback in [1.3](#1.3); the states run in progress or queued and artifacts usable SHALL NOT, and an in-progress run SHALL be recorded as the blocked fallback state  
15. <a name="1.15"></a>WHEN some runs for the head SHA have finished with usable artifacts and others are still in progress or queued, `pr-overview` SHALL use the finished artifacts, record the CI state as artifacts usable, and the page SHALL note the pending runs  

### 2. Format Parsing

**User Story:** As a maintainer of the renderer, I want the script to read standard test and coverage formats rather than know about runners, so that new languages work without changing the script.

**Acceptance Criteria:**

1. <a name="2.1"></a>The renderer SHALL read JUnit XML from one or more files, including nested `testsuites` elements, and SHALL produce per-test outcomes of passed, failed, skipped, or errored with suite, name, and failure message  
2. <a name="2.2"></a>A test case SHALL count as failed or errored only when its final outcome is a failure or error; rerun and flaky elements (`flakyFailure`, `flakyError`, `rerunFailure`, `rerunError`) recorded on a case that ultimately passed SHALL NOT make it failed, and SHALL mark it flaky  
3. <a name="2.3"></a>The renderer SHALL read lcov, Cobertura XML, and Go coverprofile files in any cover mode, and SHALL produce per-file, per-line hit counts, treating a line as covered when any block containing it has a non-zero count  
4. <a name="2.4"></a>The renderer SHALL apply the path mapping from [2.6](#2.6), then match entries to changed files per [2.5](#2.5), then sum per-line hit counts of every entry matched to the same changed file, including entries repeated within one input, so merged and per-job files give the same result as one combined file  
5. <a name="2.5"></a>The renderer SHALL associate each changed file with the coverage entries that name it, after normalising separators and removing `./` prefixes: entries whose path equals the changed file's path SHALL match; otherwise an entry SHALL match when one path is a suffix of the other on whole path segments; WHEN an entry is a suffix candidate for more than one changed file it SHALL match none, and WHEN a changed file has suffix candidates with differing leading segments it SHALL be treated as unmatched rather than guessed  
6. <a name="2.6"></a>The review JSON MAY supply a path mapping (a prefix to strip and a prefix to prepend) applied to coverage paths before matching, so that a repository unresolvable by suffix matching is handled without changing the renderer  
7. <a name="2.7"></a>The renderer SHALL compute diff coverage per changed file as covered added lines divided by added lines present in the coverage data; a file with a zero denominator SHALL be reported as having no measurable added lines and excluded from the aggregate  
8. <a name="2.8"></a>The renderer SHALL report on stderr and in the Tests section how many changed files matched, and for each unmatched file whether no candidate or an ambiguous match was the cause  
9. <a name="2.9"></a>WHEN JUnit results exist for both baseline and head, the renderer SHALL list identities present only in the head as new and identities present only in the baseline as removed, and WHEN the two have different source kinds the list SHALL carry a note that the comparison crosses sources  
10. <a name="2.10"></a>IF a test or coverage input or a diff fragment is malformed, missing, or not valid UTF-8 THEN the renderer SHALL render the rest of the page, show a warning naming the file, and exit successfully; IF the review JSON itself is unreadable THEN the renderer SHALL exit non-zero with a message naming the problem  
11. <a name="2.11"></a>The renderer SHALL reject any XML input containing a `DOCTYPE` declaration and any single input larger than 50 MB, reporting each as a warning, and SHALL use only the Python standard library on Python 3.9 or later  
12. <a name="2.12"></a>In the test harness, the renderer SHALL parse a 10 MB lcov file and a 5,000-case JUnit file in under 5 seconds each, with the harness allowed to skip the timing assertion on hosts it detects as slow  

### 3. Test Results Section

**User Story:** As a reviewer, I want to see pass rate, new tests, and coverage of the changed lines in the review page, so that I can judge test health without opening CI.

**Acceptance Criteria:**

1. <a name="3.1"></a>The overview grid SHALL include a Tests card showing pass rate, number of new tests, and aggregate diff coverage, styled like the existing verdict and findings cards  
2. <a name="3.2"></a>The page SHALL include a Tests section, listed in the table of contents, showing the provenance fields from [1.13](#1.13) with a link to the CI run when there is one, totals of passed, failed, skipped, and errored tests, and the flaky count alongside  
3. <a name="3.3"></a>WHEN the head SHA has CI jobs, the section SHALL show one row per job with its name and outcome, and counts on that row when attributed to it per [1.10](#1.10) or on a separate per-artifact row otherwise, in addition to the aggregate totals  
4. <a name="3.4"></a>The section SHALL list each failed or errored test with suite, name, and job or artifact when known, and its failure message truncated to 500 characters after the renderer replaces strings that match common secret patterns (bearer tokens, cloud access keys, `KEY=`, `TOKEN=`, `SECRET=`, `PASSWORD=` assignments, and URLs carrying credentials) with `[redacted]`  
5. <a name="3.5"></a>The section SHALL list new and removed tests, by identity when baseline-derived and by declaration name when diff-derived, labelled with which  
6. <a name="3.6"></a>The section SHALL show a per-file table of changed files with added lines, covered added lines, and diff coverage percentage, and SHALL show "no coverage data" rather than 0% for a file that matched no entry, matched ambiguously, or has no measurable added lines; deleted and binary files SHALL NOT appear in the table  
7. <a name="3.7"></a>WHEN overall coverage exists for both baseline and head, the section SHALL show both values and the delta, noting when the two come from different source kinds; WHEN only head coverage exists it SHALL show that alone; otherwise nothing  
8. <a name="3.8"></a>Within each per-file diff, added lines that have coverage data and zero hits SHALL carry a visible mark distinct from the existing add/delete colouring; added lines in files with no coverage data SHALL carry no mark; renamed files SHALL be matched by their new path  
9. <a name="3.9"></a>The section SHALL show execution outcome, JUnit availability, coverage availability, and baseline availability as independent states, so that a run that failed but wrote results still shows those results  
10. <a name="3.10"></a>IF the change is not docs-only and no test results could be obtained THEN the section SHALL render a card giving the reason as one of: no tests found, runner not detected, required tool missing, local run failed, local run timed out, or the CI state and blocked fallback state from [1.13](#1.13); WHEN the CI state is no run, artifacts absent, or artifacts expired the card SHALL state that the workflow must upload a JUnit XML file as an artifact, and a coverage file in a supported format to enable coverage  
11. <a name="3.11"></a>IF the change is docs-only THEN the Tests section, its overview card, and the diagram SHALL be omitted, and the skill SHALL record the classification in the JSON  
12. <a name="3.12"></a>IF any test in any job is failed or errored THEN the skill SHALL set the verdict tone to at least warning, mention the failures in the verdict detail, and set the publish severity to at least `needs-changes`; flaky tests and coverage values SHALL NOT change verdict or severity  

### 4. Blast-Radius Diagram Data

**User Story:** As a reviewer, I want to see which files a change touches, which files depend on them, and which files they depend on, so that I can judge the reach of the change and know how much to trust that picture.

**Acceptance Criteria:**

1. <a name="4.1"></a>The skill SHALL produce a diagram description containing the full one-hop graph: the changed files, every file that reaches any changed file through one dependency edge (dependents), every file any changed file reaches through one edge (dependencies), and edges between changed files; the renderer, not the skill, SHALL apply [4.7](#4.7), then [4.6](#4.6), then [4.8](#4.8), in that order  
2. <a name="4.2"></a>Each changed node SHALL carry a status of added, modified, deleted, or renamed taken from the diff, with copies treated as added and type changes as modified; edges of a deleted file SHALL be derived from the base tree, and dependents of a renamed file SHALL include files in the base tree importing its old path  
3. <a name="4.3"></a>Each node SHALL carry its group and a flag stating whether it is a test file  
4. <a name="4.4"></a>Each edge SHALL be derived by exactly one method and SHALL record it: a dependency tool named in the ecosystem table; a file-resolving import, meaning an import statement that names a file or a module resolving to exactly one file; or unit expansion, meaning an import that names a package, module, namespace, or target, expanded to every file in that unit  
5. <a name="4.5"></a>Each edge SHALL record which tree it was derived from, the snapshot or the base tree, and the description SHALL carry both tree identifiers  
6. <a name="4.6"></a>WHEN any edge in a column came from unit expansion, the page SHALL state that those edges are at package granularity; WHEN more than 3 nodes in a side column share a group and each is connected to the changed files only by expansion edges, the renderer SHALL collapse them into one node labelled with the group and file count  
7. <a name="4.7"></a>Nodes flagged as test files SHALL NOT appear in the dependents or dependencies columns; the renderer SHALL show on each changed node the count of test-file nodes with an edge to it, including changed test files; changed test files SHALL remain changed nodes  
8. <a name="4.8"></a>WHEN a side column would exceed 15 nodes after [4.6](#4.6), the renderer SHALL keep the 15 ranked by edges to changed files descending then path ascending, with a collapsed group node ranked by its members' combined edges, and collapse the rest into one node labelled `+N more`; the centre column SHALL show every changed node and is never capped  
9. <a name="4.9"></a>Files outside the repository (standard library, third-party packages) SHALL NOT appear as nodes  
10. <a name="4.10"></a>IF no edge could be derived for a column because no method was available or no tree was readable THEN the description SHALL say so with the reason, and the page SHALL show the reason in place of that column; an empty column SHALL never be rendered when derivation failed  
11. <a name="4.11"></a>The same diagram description SHALL always produce identical SVG output  
12. <a name="4.12"></a>`pr-overview` SHALL read the pinned head commit and the base tree from git objects without checking either out into the user's working tree, fetching the head SHA's objects for any PR including forks, since fetching and reading blobs executes nothing; WHEN there is no local clone it SHALL read both trees through the forge's tree and blob API; the dependency-tool method SHALL be used only while a worktree from [1.3](#1.3) exists  

### 5. Blast-Radius Diagram Rendering

**User Story:** As a reviewer, I want the diagram to render anywhere the page is opened, so that it works in a browser, a feed reader, and offline without installing anything.

**Acceptance Criteria:**

1. <a name="5.1"></a>The renderer SHALL emit the diagram as inline SVG generated with the Python standard library only, with no external assets and no scripts  
2. <a name="5.2"></a>The diagram SHALL lay out nodes in three columns, dependents left, changed centre, dependencies right, with nodes in each column grouped by their group and each group visually enclosed and labelled; edges between two changed files SHALL be drawn within the centre column; a file that is both a dependent and a dependency SHALL appear in the dependents column only, with its dependency edge drawn to it there  
3. <a name="5.3"></a>Changed nodes SHALL be filled per status using the existing file-badge colours, except that the modified fill SHALL be distinguishable from the page's link colour; unchanged nodes SHALL use a neutral fill; a legend SHALL explain the fills and the collapsed-node styles  
4. <a name="5.4"></a>Every node SHALL carry an identifier derived from the existing anchor hash of its path, or of its member list for a collapsed node, so identifiers are valid CSS selectors; each changed node SHALL link to that file's per-file diff anchor and SHALL show its test-file count from [4.7](#4.7) when greater than zero  
5. <a name="5.5"></a>Every edge element SHALL name its source and target node identifiers as attributes, so the graph is recoverable from the markup by a reader with no CSS and no pointer; pointer emphasis on hover SHALL be CSS-only and additive, so that with the stylesheet removed every label and edge remains visible  
6. <a name="5.6"></a>Node labels SHALL be the repository-relative path in the page's monospace font; a path exceeding the label budget SHALL be shortened from the left to a leading ellipsis plus the trailing characters that fit, with the full path in an SVG `title` element; each text element SHALL declare a `textLength` equal to its computed width and each node box SHALL be at least that width plus padding, so the label cannot exceed the box in any font  
7. <a name="5.7"></a>The label budget SHALL be the largest character count for which three columns at that budget, plus padding and the two edge gutters, declare a width no greater than the content width; the design SHALL state the resulting budget and the advance constant it assumes  
8. <a name="5.8"></a>Collapsed nodes' member paths SHALL be listed as visible text beneath the diagram in path order, not only in hover text  
9. <a name="5.9"></a>The emitted SVG SHALL declare explicit width and height from the laid-out geometry, inside a container that scrolls horizontally when the width exceeds it; the page body SHALL never scroll horizontally  
10. <a name="5.10"></a>Labels and titles containing characters special to XML or HTML SHALL render literally  
11. <a name="5.11"></a>The diagram SHALL appear as its own section listed in the table of contents, positioned before the per-file diffs  
12. <a name="5.12"></a>IF the diagram description is absent or invalid THEN the renderer SHALL omit the section, print a warning to stderr naming the problem, and exit successfully  

### 6. Contract, Compatibility, and Verification

**User Story:** As a user of the existing skills, I want existing review JSON to keep rendering as before and the new behaviour to be tested, so that the additions are safe to adopt.

**Acceptance Criteria:**

1. <a name="6.1"></a>A golden fixture SHALL be generated by the renderer at commit `9da40cf` from a review JSON that exercises every existing section, and review JSON without the new blocks SHALL produce a document identical to that fixture apart from the contents of the `style` element and the generation timestamp  
2. <a name="6.2"></a>The new blocks SHALL be optional top-level keys in the review JSON, documented in all three skills' schema, rendering-contract, diff-generation, and error-handling sections, and those sections SHALL be corrected where they describe behaviour the renderer does not have  
3. <a name="6.3"></a>The rendered page SHALL continue to satisfy the pulsar agent contract: self-contained, one `review-meta` block, no relative asset paths  
4. <a name="6.4"></a>The renderer SHALL keep working when invoked with only the existing flags, and new inputs (JUnit files, coverage files, baseline files) SHALL be referenced by path from the JSON relative to the diff directory, which the skills SHALL place in the job directory, with no second input mechanism  
5. <a name="6.5"></a>The renderer SHALL remain invocable as `python3 ~/.claude/scripts/build_review_html.py` with the existing command line, whatever its internal file layout  
6. <a name="6.6"></a>The repository SHALL contain a test harness, runnable with one documented command, covering JUnit parsing including rerun elements, each coverage format, path mapping, matching including exact-match precedence and ambiguity, entry merging, diff coverage arithmetic, new/removed test derivation, secret redaction, malformed and non-UTF-8 input handling, DOCTYPE and size rejection, the projection rules in [4.6](#4.6) to [4.8](#4.8), diagram layout determinism and label-budget arithmetic, and the golden fixture from [6.1](#6.1)  

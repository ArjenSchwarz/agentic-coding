# Decision Log: review-html-tests-diagram

## Quick Decisions

| ID | Date | Decision | Rationale |
|----|------|----------|-----------|
| Q1 | 2026-09-03 | Feature name `review-html-tests-diagram` | Matches the worktree branch already in use |
| Q2 | 2026-09-03 | Full spec workflow rather than smolspec | Layout engine, test source order, and contract shape are contested-approach decisions |
| Q3 | 2026-09-03 | Diagram nodes are files, clustered by package or directory | Universally derivable from imports; type-level and infrastructure views deferred |
| Q4 | 2026-09-03 | Aggregate results across all CI jobs, with a per-job row | Totals stay meaningful for matrix builds while failures remain attributable |
| Q5 | 2026-09-03 | Failing tests floor severity at `needs-changes` and the verdict tone at warning; coverage never changes severity | A red suite is a merge blocker regardless of findings; coverage is context, not a gate |
| Q6 | 2026-09-03 | Tests section and diagram omitted only for docs-only changes as defined in the requirements (documentation, named repo files, images, lockfiles, editor and VCS dotfiles); build config, CI workflows, and dependency manifests count as code | Absence of test data on a code change is review signal; on a docs change it is noise. Dependency bumps are where test results matter most |
| Q7 | 2026-09-03 | Show overall coverage delta when both base and head coverage exist; omit silently otherwise | Cheap when the data is there, and no fabricated baseline when it is not |
| Q8 | 2026-09-03 | Test files are excluded from the dependents and dependencies columns; changed test files stay as changed nodes; each changed node carries a count of test files importing it | Test files as dependents double the node count without saying anything about reach; a test-only PR still needs a diagram |
| Q9 | 2026-09-03 | Column cap of 15 nodes; overflow collapses into one node keeping the most-connected files, ranked by edge count then path | Keeps the diagram legible on wide-reaching changes without a general layout engine; the path tiebreak makes output deterministic |
| Q10 | 2026-09-03 | CI artifact retrieval is GitHub Actions only; GitLab is cut from this feature | The review skills are GitHub-only today and the forge adapter has no artifact operation; GitLab's JUnit reaches the API as JSON unless workflows also list it under `artifacts:paths`, which would need a fifth parser |
| Q11 | 2026-09-03 | One spec with two independently deliverable task phases (diagram, test results) rather than two specs | The halves share the renderer and the docs-only rule; ordering the diagram first keeps it deliverable if the test-collection phase stalls |
| Q12 | 2026-09-03 | Local test run timeout of 10 minutes; partial JUnit output is kept and labelled | Long enough for a cold build on a mid-size repo, short enough that a review does not hang; partial results beat none |
| Q13 | 2026-09-03 | Backward compatibility means identical page body excluding the style block and timestamp, checked against a golden fixture captured before the first edit | Byte identity would forbid adding any CSS; the style block is one unconditional constant |
| Q14 | 2026-09-03 | The label budget is the largest character count for which three columns plus gutters fit the 1036 px content width; the column cap drives height, not width | Three 40-character monospace columns exceed the content width; the design states the resulting budget and the advance constant |
| Q15 | 2026-09-03 | The skill, not the renderer, applies the severity floor for failing tests; the renderer's only rewriting of input is secret redaction in failure messages | Verdict and publish metadata are pass-through fields; a renderer that rewrites them would be new contract behaviour. Failure messages come from files only the renderer reads, so redaction has to live there |
| Q16 | 2026-09-03 | Failure messages are redacted for common secret patterns before rendering | The page is archived by pulsar and served to a feed reader; test output routinely contains tokens and connection strings |
| Q17 | 2026-09-03 | Baseline is the run for the merge-base commit, or the nearest successful base-branch run at or before it | A later base-branch run makes tests added on main appear as removed in the PR |
| Q18 | 2026-09-03 | Rerun and flaky JUnit elements never count as failures when the case ultimately passed | Surefire and pytest-rerunfailures emit these; counting them would floor severity on a green PR |
| Q19 | 2026-09-03 | Coverage path matching is a stated property (segment-wise suffix, ambiguity means no data, optional path mapping) rather than a list of mechanisms | Any unlisted case would otherwise be formally out of scope; a wrong match is worse than no data |
| Q20 | 2026-09-03 | Untrusted XML is parsed with the standard library after rejecting `DOCTYPE` declarations and capping inputs at 50 MB | `defusedxml` is not stdlib; rejecting DOCTYPE removes entity-expansion attacks |
| Q21 | 2026-09-03 | The skill supplies the full one-hop graph; the renderer applies the unit-collapse, cap, and ranking rules | Rules assigned to an agent following prose are neither reproducible nor testable; in the renderer the harness covers them |
| Q22 | 2026-09-03 | The JUnit-emitting test command is chosen before the verification run, never discovered by executing candidates | Probing would run the suite up to three times; a Makefile target that emits nothing structured is passed over for the ecosystem recipe |
| Q23 | 2026-09-03 | `pr-overview` pins the head commit SHA at the start and uses it for the diff, the artifact lookup, the fetch, and the worktree | A branch that moves mid-review would otherwise give diffs, coverage marks, and provenance from different trees |
| Q24 | 2026-09-03 | CI test counts are attributed to a job only when the artifact name contains the job name; otherwise they are shown per artifact | GitHub artifacts belong to a workflow run, not a job, so attribution is a convention rather than an API fact |
| Q25 | 2026-09-03 | Node label text declares `textLength`, and box width is at least the computed label width plus padding | The monospace font stack falls back to fonts with different advances; `textLength` makes the fit hold regardless |
| Q26 | 2026-09-03 | Provenance uses two orthogonal fields, CI state and fallback state, instead of one enum | A fork PR with expired artifacts is two facts; one enum cannot hold both, and the section shows the dimensions independently |
| Q27 | 2026-09-03 | The column cap applies to the side columns only; the centre column always shows every changed file | Changed files are what the reader came to see; a 40-file PR must still have a legal rendering |
| Q28 | 2026-09-03 | Nodes carry a test-file flag set by the skill; the renderer applies test exclusion, then unit collapse, then the cap | "Test file" is an ecosystem-table concept the renderer cannot derive; the order stops a mixed group from collapsing before test files are removed |
| Q29 | 2026-09-03 | `pr-overview` reads head and base trees from fetched git objects, or the forge tree and blob API when there is no clone, for fork PRs too | Fetching and reading blobs executes nothing, so the fork rule is not breached; it replaces the skill's current per-file `gh api` reads |
| Q30 | 2026-09-03 | All run outputs, the review JSON, and its referenced inputs live in the job directory | Outputs inside the working tree pollute `git status`; a worktree is removed after the run, so its outputs must be elsewhere and read first |
| Q31 | 2026-09-03 | The golden fixture is generated at commit `9da40cf` | That commit provably predates any renderer change for this feature, so the fixture is reproducible rather than a process instruction |
| Q32 | 2026-09-04 | Edge discovery is a script, `scripts/blast_radius.py`, driven by a machine-readable `scripts/ecosystems.json` that is also the skills' ecosystem table | Agent grep is neither reproducible nor testable; one JSON file serves both the script and the agent |
| Q33 | 2026-09-04 | The renderer becomes the package `scripts/review_html/` with `build_review_html.py` as a thin entry that resolves its own symlinked path | The file would otherwise double to about 1,800 lines; `sync-claude.sh` links the whole scripts directory so the package syncs unchanged |
| Q34 | 2026-09-04 | A `Makefile` with a `test` target is added to this repo; the harness is `unittest` under `scripts/tests/` | The user prefers `make test` as the single documented command despite it binding the repo to the Makefile convention |
| Q35 | 2026-09-04 | Modified nodes use `--accent-2` (magenta) rather than the badge's `--accent` | The badge colour equals the link colour, and every changed node is a link |
| Q36 | 2026-09-04 | Label budget is 37 characters at a 7.2 px advance, 10 px box padding, 8 px group padding, 56 px gutters, fixed 308 px columns | Largest budget fitting 1036 px; fixed column width keeps the declared width constant and the layout aligned |
| Q37 | 2026-09-04 | Hover emphasis uses per-node `:has()` rules in a `style` element inside the diagram section | Pure CSS with a flat SVG; browsers without `:has()` show the unchanged diagram |
| Q38 | 2026-09-04 | Tracked files touched by a local run are restored from pre-run copies of dirty files or `git checkout` for clean ones; `git stash` is never used | Stash would carry away the uncommitted fixes the run exists to verify |
| Q39 | 2026-09-04 | The local run budget is one Bash call at the tool's 600,000 ms maximum, covering install and tests | The harness enforces it, so no separate timer is needed |
| Q40 | 2026-09-04 | The severity floor is applied by rendering twice: the renderer prints a counts line to stderr, the skill adjusts verdict and severity, then renders again | Keeps verdict and publish metadata pass-through while giving the skill exact counts |
| Q41 | 2026-09-04 | pytest's `rerun` element joins the Surefire rerun and flaky element names as a flaky marker | Same semantics, different dialect |
| Q42 | 2026-09-04 | Coverage entries carry aliases for Cobertura source roots instead of being duplicated per root | Duplicates would make one file two candidates and trip the ambiguity rule |
| Q43 | 2026-09-04 | New template placeholders are appended to existing placeholder lines | An empty substitution then leaves no extra blank line, so the golden fixture compares without whitespace normalisation |
| Q44 | 2026-09-04 | Ambiguity is decided on the residual prefix of each candidate, not its first segment | Two files under the same module prefix share a first segment yet are different files |
| Q45 | 2026-09-04 | CI state is derived after downloading and sniffing, by an ordered rule list with "usable" first | "Usable" means a JUnit file exists, which is unknowable before sniffing; the order makes every state reachable |
| Q46 | 2026-09-04 | Job attribution uses token-set inclusion between job and artifact names, most tokens wins, ties unattributed | Matrix job names like `test (ubuntu)` are never substrings of artifact names like `test-results-ubuntu` |
| Q47 | 2026-09-04 | Artifacts over 100 MB are skipped by size before download; remote blob reads are capped at 500 calls with a column reason when hit | Build artifacts are routinely hundreds of MB, and the GitHub API rate limit is 5,000 calls per hour |
| Q48 | 2026-09-04 | The dependency-tool method runs inside the fallback's single Bash call, before the worktree is removed | The worktree is the only checkout `pr-overview` has, and it is gone by the render phase |
| Q49 | 2026-09-04 | Untracked files created by a local run are reported, never deleted; untracked files in the working tree count as added changes | Deleting would remove anything the user created during a 10-minute run; a fix that adds a file must appear in the diff |
| Q50 | 2026-09-04 | Ecosystem rows are keyed by language with a `runners` list selected by detection rules | One row cannot hold both vitest and jest recipes; detection makes tier 3 deterministic |
| Q51 | 2026-09-04 | Centre-column label budget reserves 4 characters for the test-count badge | The badge is a second text element inside the same box and must come out of the same width; the resulting number is in Q56 |
| Q52 | 2026-09-04 | Fetch uses `refs/pull/<n>/head` verified against the pinned SHA rather than fetching a bare SHA | Fetching unadvertised objects by SHA depends on server configuration; the pull ref always exists on GitHub, forks included |
| Q53 | 2026-09-04 | `overall()` merges entries by normalised primary path before counting | Repeated `SF:` records and per-job files would otherwise count instrumented lines twice |
| Q54 | 2026-09-04 | Stale worktree cleanup is `git worktree prune` alone | Prune removes exactly the entries whose directory is gone and skips locked ones; requirement 1.9 is worded to match |
| Q55 | 2026-09-04 | The fork-PR non-goal is scoped to `pr-overview`'s fallback; `pr-review-html` runs any PR it checks out and its skill text discloses that | `pr-review-html` already checks out and tests fork PRs today; the unqualified non-goal contradicted the applicability table |
| Q56 | 2026-09-04 | Centre-to-centre edges run in a 24 px lane inside the centre column; centre boxes are 268 px and the centre label budget is 30 | Arcs within the 8 px between box and column edge are indistinguishable, and bulging into the gutter breaches requirement 5.2 |
| Q57 | 2026-09-04 | The diagram and diff-derived tests are file references (`diagram_file`, `diff_tests_file`) written by `blast_radius.py`, never inline JSON | Transcribing a 70-node graph through the agent's context is the reproducibility failure Q32 exists to prevent |
| Q58 | 2026-09-04 | Coverage matching is five global passes: exact, pools, shared-removal once, residuals, merge | The per-file formulation was order-dependent and could report "no candidate" for a file that had a unique match |
| Q59 | 2026-09-04 | JUnit elements sharing an identity within one source collapse to the last element's outcome, flaky when an earlier attempt failed | pytest-rerunfailures emits one element per attempt; counting each inflates totals and can floor severity on a green suite |
| Q60 | 2026-09-04 | Makefile targets are inspected by reading recipe text, never via `make -n` | `make -n` still evaluates `$(shell …)` and `+`-prefixed lines, which executes branch code during selection |
| Q61 | 2026-09-04 | `change_classification` is a top-level JSON key | The diagram ships before the test-results phase; a classification inside the `tests` block would not exist yet |
| Q62 | 2026-09-04 | SVG fills and strokes use CSS variables with literal fallbacks | With the stylesheet removed a bare `var()` is invalid and edges vanish, breaching requirement 5.5 |
| Q63 | 2026-09-04 | Tool-derived edges carry a granularity from the ecosystem row, and the package-granularity note covers them | `go list` edges are package-level; Decision 4's honesty rule applies to them as much as to expansion |
| Q64 | 2026-09-04 | The diff directory is `$CLAUDE_JOB_DIR/review-inputs`, or `$(mktemp -d)/review-inputs` when the job directory is unset, always passed as an absolute path | A relative path inside the fallback's subshell resolved into the worktree or the user's clone |
| Q65 | 2026-09-04 | `read_guarded` returns `None` with a warning for a missing or unreadable file, not only for size, DOCTYPE, and encoding rejections | Requirement 2.10 asks for a warning naming the file; callers that need the historic silent placeholder (missing diff fragments) check existence first |
| Q66 | 2026-09-04 | `load_fragments` owns every diff placeholder (`missing`, `is not UTF-8`, `no diff provided`); `render_files` only looks paths up in the dict | One place decides what a file's diff text is, so the Tests section and the per-file blocks cannot disagree |
| Q67 | 2026-09-04 | The 15-node cap counts real nodes; the `+N more` node is a 16th box | Requirement 4.8 keeps 15 ranked nodes *and* collapses the rest into one node, so the overflow node sits outside the count |
| Q68 | 2026-09-04 | `+N more` counts files, not nodes, and lists the flattened member paths | Consistent with `<group> (N files)`; a collapsed group inside the overflow would otherwise hide its size |
| Q69 | 2026-09-04 | Go `test_decl` is `^func ((?:Test\|Fuzz\|Benchmark)\w+)\s*\(`, one capture group | The design's two-group form made group 1 the keyword, not the name |
| Q70 | 2026-09-04 | The `tool` row carries `name` and `format` (`go-list-json` or `pairs`) besides `deps` and `granularity` | `go list -json` needs its own parser and `tool:<name>` needs a name; `pairs` lets tests stub a tool with plain output |
| Q71 | 2026-09-04 | Python `from X import Y` captures both parts joined with `.`, relying on the `roots` drop-last retry | A single group cannot tell `from a.b import c` importing module `a/b/c.py` from importing symbol `c` out of `a/b.py` |
| Q72 | 2026-09-04 | With `--remote`, changed-file and module-file blob reads always run; the 500-call cap refuses only dependents-scan reads | The design says dependencies are unaffected by the cap, which is only true if their reads are never refused |
| Q73 | 2026-09-04 | A single changed file with two suffix candidates of different depth (`util.py` and `a/util.py` for `src/a/util.py`) is ambiguous; the design's example is the two-file case where pass 3 removes the shared entry | Pass 4 sees two distinct residuals, and per Q19 a wrong match is worse than no data; preferring the longer suffix would be a new rule |
| Q74 | 2026-09-04 | `redact.clean_message` redacts then truncates to 500 characters (499 plus `…`); `redact` alone never truncates | The section needs one call that does both in the required order; keeping `redact` pure keeps its tests simple |
| Q75 | 2026-09-04 | The availability line counts files actually read (`2 of 3 files read`), not files listed | A listed but unreadable file is not available data |
| Q76 | 2026-09-04 | The two `summary` lines print only when a `tests` block is present and the classification is not `docs-only` | Docs-only output must be silent; the skills treat absent lines as "no test data" and apply no floor |
| Q77 | 2026-09-04 | With no JUnit read and `no_data_reason` null, the no-data card still renders, derived from the CI states for `source: ci` and otherwise a generic sentence | A skill that forgot the reason should not produce a page with no Tests card at all |
| Q78 | 2026-09-04 | A runner's `junit_flags` may list several spellings and the schema test requires only one of them in the recipe | pytest accepts `--junitxml` and `--junit-xml`, and Makefile inspection must recognise either |
| Q79 | 2026-09-04 | The Rust runner is one `cargo llvm-cov nextest --lcov --output-path {coverage} --config-file {inputs}/nextest.toml` command; JUnit comes from the config template | A separate `cargo nextest run` followed by `cargo llvm-cov` would execute the suite twice |
| Q80 | 2026-09-04 | The Go runner requires `go` as well as `gotestsum`; the Swift coverage export is `&&`-chained after `swift test` | gotestsum cannot run without `go`; llvm-cov has no profile to export when the test binary did not build, while the JUnit file is written either way |
| Q81 | 2026-09-04 | Local-source `tests.provenance` in pr-review-html and pre-push-review omits `ci_state` and `fallback_state` | Neither skill queries head CI; the renderer reads both keys with `.get` |
| Q82 | 2026-09-04 | `git diff --no-index` exits 1 when the files differ and the skills say so | An agent that treats exit 1 as failure would drop every untracked file's fragment |
| Q83 | 2026-09-05 | With no coverage input parsed, the per-file diff-coverage table, overall coverage, and unmatched report are omitted and the stderr line reports matched=0 unmatched=0 | A table of all "no coverage data" rows says nothing the availability line does not already say |
| Q84 | 2026-09-05 | The stderr coverage line carries counts only; per-file unmatched reasons live in the Tests section | The skills grep one line for the floor; per-file reasons on stderr would be noise no skill reads |
| Q85 | 2026-09-05 | Files with no ecosystem row are test files only by whole-token name (`test_x`, `x_test`, `x.test.ts`, `x.spec.js`, `XTests.swift`, `conftest.py`) or a parent directory named `test`, `tests`, `__tests__`, or `spec` | A substring rule flagged every file under `specs/` and `docs/testing.md` as tests, excluding them from the diagram's side columns and listing them as unpatterned |
| Q86 | 2026-09-05 | `read_guarded` scans the whole buffer for `<!DOCTYPE`, not the first 64 KB | XML comments and processing instructions may precede the declaration, so a fixed window is bypassed by padding; the buffer is already in memory and the scan is a substring search |

## Decision 1: Constrained pure-SVG layout instead of Graphviz

**Date**: 2026-09-03
**Status**: accepted

### Context

The review page is fully self-contained today: no external scripts, diffs highlighted in Python. The pulsar archive moves the file and serves it to a browser or feed reader, and the page may be opened offline. The diagram needs a layout engine somewhere, and the choice determines whether the page or the build machine gains a dependency.

### Decision

Generate the diagram as inline SVG from a constrained three-column layout (dependents, changed, dependencies) implemented in the renderer with the Python standard library. No Graphviz, no Mermaid, no scripts in the page.

### Rationale

A review diagram answers one question, "what does this change touch and what depends on it", which has a fixed shape. A three-column layout with grouped nodes and bezier edges is arithmetic, roughly 150 to 200 lines, and needs no general graph layout. That removes both the build-time dependency and the view-time dependency, so the diagram appears on any machine and in any viewer. The estimated extra effort over Graphviz glue is about half a day.

### Alternatives Considered

- **Graphviz `dot -Tsvg` inlined at build time**: Best layout quality for arbitrary graphs and about 30 lines of glue - Rejected because it is a binary that must exist wherever the review is built, so a fallback is needed anyway and the diagram silently vanishes without it. Conflicts with the goal of working on any repo and machine.
- **Mermaid loaded from a CDN**: No install and the pulsar contract allows pinned public URLs - Rejected because it adds the page's first external script, fails in feed readers and offline, and lays out poorly beyond roughly 15 nodes.
- **General layered layout (Sugiyama) in Python**: No dependencies and handles arbitrary graphs - Rejected because it is substantially more work than the constrained layout and still lays out worse than Graphviz.

### Consequences

**Positive:**
- The page stays dependency-free and works in every viewer.
- Layout is deterministic and testable with fixtures.
- Node links and hover highlighting fit the page's existing CSS-only interaction style.

**Negative:**
- The layout only suits the blast-radius shape; other diagram types (infrastructure, type-level) will need their own projection onto the same column machinery or a new layout.
- Wide-reaching changes must be capped and collapsed rather than laid out in full.

---

## Decision 2: The renderer parses formats; the skills map ecosystems

**Date**: 2026-09-03
**Status**: accepted

### Context

The feature must work on any repository and language, and the renderer already has a clear split: skills assemble JSON, the script renders it. Test runners differ per ecosystem, but their machine-readable outputs converge on a few formats.

### Decision

The renderer reads JUnit XML for test outcomes and lcov, Cobertura XML, and Go coverprofile for coverage, and knows nothing about runners or languages. A single shared ecosystem table, referenced by all three skills, tells the agent how to make each common runner emit those formats, with a Makefile target or the project's own instructions taking precedence.

### Rationale

Every mainstream runner can emit at least one of these formats: gotestsum and Go's coverprofile, pytest with `--junitxml` and `--cov-report=xml`, jest and vitest JUnit reporters with lcov, `swift test --xunit-output` with llvm-cov lcov, cargo nextest JUnit, JaCoCo and PHPUnit Cobertura, RSpec JUnit formatters. Parsing four formats once covers all of them, and adding a language means adding a table row, not code. The same parsers serve CI artifacts and local runs.

### Alternatives Considered

- **Per-runner collectors in the script**: The script invokes `go test -json`, pytest, and so on directly - Rejected because it couples the renderer to languages and grows a collector per ecosystem.
- **Parse runner logs from CI**: Works without any workflow changes - Rejected as brittle; every runner has a different summary line, and no log carries line coverage. Structured artifacts or a local run are the only sources that yield diff coverage.
- **diff-cover as a dependency**: Computes diff coverage from Cobertura and lcov - Rejected because it adds a pip dependency and needs a Cobertura conversion for Go, when the intersection itself is about 40 lines.

### Consequences

**Positive:**
- New languages need no renderer changes.
- CI and local data go through the same code path, so the page looks the same either way.

**Negative:**
- A repository whose CI does not upload structured artifacts gets no CI-sourced data until its workflow is changed; the fallback is a local run.
- Coverage path normalisation across formats (Go package paths, absolute lcov paths, Cobertura source roots) needs careful matching against diff paths.

---

## Decision 3: Test data source order per skill

**Date**: 2026-09-03
**Status**: accepted

### Context

The three skills have different relationships with the code. `pr-review-html` checks out the PR branch, applies fixes locally, and already runs the suite to verify them. `pr-overview` is read-only and never checks out. `pre-push-review` runs on the local branch before push and already runs the suite. CI results for the PR head may exist, may be missing, and in the fix-applying skill they describe a commit that no longer matches the working tree.

Running a PR's tests in a fresh worktree means installing dependencies first, and install scripts execute arbitrary code before any test runs. For a fork PR that code comes from someone outside the repository.

### Decision

`pr-review-html` and `pre-push-review` take test data from the single run their verification phase already performs, and take their diffs from the same working tree. `pr-overview` pins the head commit SHA and uses GitHub Actions artifacts for that SHA first. When none exist, no run is in progress, the PR is a same-repo PR, and the current directory is a clone of that repository, it fetches the SHA, runs the suite in a throwaway worktree in the job directory, and removes the worktree afterwards. For fork PRs, in-progress runs, and when there is no local clone, it never runs branch code and the page says which state applied. Every page states its source, and a baseline from a different source kind than the head is labelled as such.

### Rationale

In `pr-review-html` the page must describe the post-fix tree, and the diffs must come from that same tree or uncovered-line marks land on wrong lines. `pr-overview`'s read-only promise is about not modifying the user's checkout or the branch; a detached worktree in the job directory keeps that promise. The same-repo restriction is the trust boundary: code from the repository's own contributors is what the reviewer already runs day to day, and fork code is not. Fetching the head ref is required because the skill never checks out, so the ref does not otherwise exist locally.

### Alternatives Considered

- **CI only in `pr-overview`**: Keeps the skill strictly non-executing - Rejected because most repositories today upload no artifacts, so the section would usually show the no-data card. Kept as the behaviour for fork PRs.
- **Worktree fallback for all PRs**: Yields data on every PR - Rejected because it executes install scripts and tests from untrusted forks with the reviewer's credentials and network.
- **A consent prompt before running fork code**: Keeps the fallback available - Rejected because the skills run unattended in background jobs where a prompt blocks the review.
- **Show both CI and local in `pr-review-html`**: Gives the reader the pre-fix and post-fix views - Rejected because it doubles the section for a distinction that only matters when a fix changed test outcomes, which the verdict already describes.

### Consequences

**Positive:**
- Each page's test data matches the code it describes, and diffs and coverage share one snapshot.
- `pr-overview` yields test data on same-repo PRs in repositories with no CI artifacts.
- No new test run is added to `pr-review-html` or `pre-push-review`.

**Negative:**
- `pr-overview` executes same-repo branch code, including install scripts, which the skill text states explicitly.
- Fork PRs in repositories without artifacts show the no-data card until the workflow uploads results.
- A worktree run duplicates the checkout and installs dependencies, which is slow on large repositories and subject to the 10-minute timeout.
- In `pr-review-html` a local head run is compared against a CI baseline; tests that only run in CI (build tags, OS-gated suites) appear as removed unless the reader heeds the cross-source note.
- Fetching the head SHA writes refs into the user's `.git`, so `pr-overview`'s "never modifies" statement gains a caveat for repository metadata.

---

## Decision 4: Module-level imports expand to files with labelled granularity

**Date**: 2026-09-03
**Status**: accepted

### Context

The diagram's nodes are files (per Q3), and its edges come from imports. Python, Ruby, C, and most JavaScript imports resolve to a file. Swift, C#, Go, Java, and Kotlin imports name a package, module, namespace, or target, so a file-level "who imports this file" set does not exist in those languages. Rendering an empty dependents column there would read as "nothing depends on this", a confidently false statement on a review page.

### Decision

Edges are derived by one of three recorded methods: a dependency tool, a file-resolving import, or unit expansion, where a package-level import is expanded to every file in that unit. When a column contains expanded edges the page says those edges are at package granularity, and a unit contributing more than three expanded files collapses into one node. When no method is available the column is replaced by the reason, never left empty.

### Rationale

Expansion keeps the file-level model and gives module-language repositories a usable diagram, while the label and per-edge method keep the reader honest about what the edges mean. Collapsing large expanded units stops a one-line change in a big package from filling a column with fifteen siblings. Recording the method also lets the design test each method separately.

### Alternatives Considered

- **Strict file edges only**: Only tool-derived and file-resolving edges count - Rejected because most Swift, C#, and Go PRs would render a changed-column-only diagram, which is the common case for this user's repositories.
- **Package nodes for module languages**: Nodes become packages where imports are package-level - Rejected because it changes Q3's node model mid-diagram and mixes granularities across columns without a per-edge record of why.

### Consequences

**Positive:**
- Every supported language yields a diagram with the same visual model.
- The page never claims an absence it cannot establish.

**Negative:**
- Expanded edges overstate reach: a file in a package that imports another package may not use the changed file at all.
- The ecosystem table must name a unit-resolution rule per module language, which is more per-language content than the test-recipe rows.

---

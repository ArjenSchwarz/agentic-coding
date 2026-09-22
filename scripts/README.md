# Scripts Directory

This directory contains utility scripts that can be invoked by agents to perform specific development tasks.

## Scripts

### commit-diff-summary.sh

**Purpose**: Generates a comprehensive summary of changes between commits, branches, or tags.

**Usage**:
```bash
./commit-diff-summary.sh [OPTIONS]
```

**Options**:
- `-b, --base REF`: Base reference to compare from (default: HEAD~1)
- `-h, --head REF`: Head reference to compare to (default: HEAD)
- `-v, --verbose`: Show detailed file changes and full diff
- `--help`: Display help message

**Prerequisites**:
- Must be run from within a git repository
- Git must be installed and configured

**Behavior**:
- Compares changes between two git references (commits, branches, or tags)
- Shows commit count, authors involved, and file statistics
- Lists all changed files with additions/deletions count
- Displays commit messages between the references
- In verbose mode, shows the complete diff

**Examples**:
```bash
./commit-diff-summary.sh                    # Compare current commit with previous
./commit-diff-summary.sh -b main            # Compare current branch with main
./commit-diff-summary.sh -b v1.0.0 -h v2.0.0  # Compare two tags
./commit-diff-summary.sh -b origin/main -v  # Compare with remote main, verbose output
```

**Output**: Formatted summary including commit count, authors, statistics, file changes, and commit messages.

### build_review_html.py

**Purpose**: Renders a self-contained HTML review page from a JSON description, using the Prism Dark theme. Shared renderer used by the `pre-push-review`, `pr-review-html`, and `pr-overview` skills — keep the template and palette here, not duplicated across skills.

**Usage**:
```bash
python3 ~/.claude/scripts/build_review_html.py \
  --data    /path/to/review.json \
  --output  /path/to/review.html \
  [--diff-dir /path/to/diff-fragments]   # defaults to the JSON file's directory
```

**JSON schema**: see the docstring at the top of the script. Top-level keys are `repo`, `title`, `subtitle`, `metrics`, `verdict`, `at_a_glance`, `explanation` (beginner/intermediate/expert), `commits`, `important_changes`, `decisions`, `findings`, `double_check`, `files`. Empty sections are dropped from both the body and the table of contents.

Optional keys: `tests` holds the test-results block (JUnit and coverage file names, provenance, jobs, artifacts; see the spec's design document) rendered as the Tests card and section. `diagram_file` names a `diagram.json` written by `blast_radius.py`, read relative to `--diff-dir`, and rendered as the Blast radius section (inline SVG, before the per-file diffs). Every `files[]` entry is classified as `code`, `docs` (Markdown and similar, anything under `docs/`, README/CHANGELOG/LICENSE/CONTRIBUTING/CODEOWNERS), or `other` (images, lockfiles, editor and VCS dotfiles) by `review_html/classify.py`; `files[].kind` overrides one entry. The Per-file diffs section states the composition and, when more than one kind is present, groups the diffs Code, Docs, Other. A change with no `code` file is docs-only, which suppresses both the Tests and Blast radius sections without a warning; `change_classification` (`code` or `docs-only`) overrides that derivation. An absent or invalid diagram file prints a warning to stderr, omits the section, and still exits 0. A review JSON that cannot be read or parsed prints one `error:` line and exits 2.

**Behavior**:
- Renders the Prism Dark palette as inline CSS — fully self-contained, with no external assets.
- Important-change cards render Takeaway (magenta) and Rationale (cyan) callouts, with an Open Question (warning) variant when `rationale_unknown: true`.
- The three-level explanation renders as CSS-only radio-button tabs (no JS required).
- Per-file diffs are collapsed `<details>` blocks. Missing diff fragments degrade to a placeholder rather than failing the render.

**Output**: Prints the absolute path of the written HTML on success.

**Layout**: `build_review_html.py` is a thin entry point; the renderer lives in the `review_html/` package next to it (`css.py` holds the stylesheet, `sections.py` the section renderers, `diagram.py` the blast-radius projection and SVG, `render.py` the orchestration). `sync-claude.sh` links the whole directory, so the package syncs with the script.

### blast_radius.py

**Purpose**: Derives the one-hop dependency graph around a change (the changed files, the files that import them, and the files they import) from git trees, and writes it as `diagram.json` for the renderer, plus `diff-tests.json` listing test declarations added and removed in changed test files. Used by the `pre-push-review`, `pr-review-html`, and `pr-overview` skills.

**Usage**:
```bash
python3 ~/.claude/scripts/blast_radius.py \
  --repo DIR \                     # repository directory (default: .)
  --snapshot (SHA|working-tree) \  # the tree the page describes
  --base SHA \                     # the tree it is compared against
  [--remote OWNER/REPO] \          # read both trees through the GitHub API (no clone needed)
  [--ecosystems FILE] \            # defaults to ecosystems.json next to the script
  [--tools] \                      # run each ecosystem row's dependency tool in --repo
  --out DIR                        # writes DIR/diagram.json and DIR/diff-tests.json
```

**Prerequisites**: git, or the GitHub CLI (`gh`) authenticated for `--remote`. `--remote` needs a commit SHA snapshot and cannot be combined with `--tools`.

**Behavior**:
- Changed files come from `git diff --name-status -M -C` (copies count as added, type changes as modified) plus untracked files as added for a working-tree snapshot; with `--remote`, from the compare API.
- Trees come from `git ls-tree`, the working tree, or the trees API. Symlinks, submodules, and blobs over 1 MB are never scanned; skipped blobs are listed in `skipped`. Files whose extension has no row in `ecosystems.json` are not scanned.
- Imports are matched with each row's patterns and resolved to files by the row's resolver: `relative` (path relative to the importer, trying `extension_map`, `extensions`, then `index_files`), `roots` (segments joined under each `source_roots` entry, retrying once with the last segment dropped for symbol imports), or `unit` (a package, module, or target expanded to every file in it, recorded with `granularity: package`). Only edges touching a changed file are kept; each carries `method` (`import`, `expansion`, or `tool:<name>`), `granularity`, and `tree` (`snapshot` or `base`).
- Deleted files and the old paths of renamed files are scanned in the base tree, so their edges carry `tree: base`.
- `column_status` reports `complete`, `partial: remote scan cap reached` (the blob API is capped at 500 calls; dependencies of the changed files are always read), or `failed: <reason>` (`no import patterns for <extensions>`, `tree listing truncated`). A failed column is rendered as its reason, never as an empty column.
- With `--tools`, a row's `tool.deps` command runs in `--repo` and its edges replace the scanned edges for the same file pair; a failing tool leaves the scanned edges in place with a warning.
- `diff-tests.json` scans the diff of each changed test file with the row's `test_decl`; test files whose row has no pattern are listed in `unpatterned_files`.

**Output**: Prints the paths of the two files written. Exit status 1 on git or API errors, 2 on invalid arguments.

### ecosystems.json

One row per language, read by `blast_radius.py` and by the review skills. Keys the script reads:

| Key | Meaning |
|-----|---------|
| `extensions` | file extensions the row covers |
| `test_files` | regexes marking a path as a test file (files with no row fall back to a `test`/`spec` name or directory rule) |
| `test_decl` | regex whose first group (or whole match minus the leading keyword) is a test name; matched over the added and removed lines of a diff |
| `unit` | grouping rule: `{"kind": "directory"}`, `{"kind": "module_file", "module_file": "go.mod", "module_regex": ...}`, or `{"kind": "target_root", "target_root": "Sources"}` |
| `imports` | list of `{"regex", "resolve": "relative" \| "roots" \| "unit", "separator"}`; multiple groups are joined with the separator |
| `source_roots`, `index_files`, `extension_map` | inputs to the `roots` and `relative` resolvers |
| `tool` | `{"name", "deps", "format": "go-list-json" \| "pairs", "granularity"}`; `pairs` output is one `from<TAB>to` line per edge |
| `notes` | known holes in the row, shown to the agent |

Runner recipes (`runners[]`) that tell the skills how to emit JUnit XML and coverage live on the same rows and are read by the agent, not the script. Each runner has `name`, `detect` (`files` globs and/or `package_json_keys`), `recipe`, `requires` (binaries that must be on PATH), `coverage_format` (`lcov`, `cobertura`, or `coverprofile`), `install`, `junit_flags` (the flags a Makefile target must contain to count as emitting JUnit), and optionally `env` and `config_files` (templates written under the inputs directory). Recipes, env values, and templates use only the placeholders `{junit}`, `{coverage}`, and `{inputs}`. `scripts/tests/test_ecosystems.py` checks both key sets.

### copilot-pr-comments.sh

**Purpose**: Fetches and displays GitHub Copilot's review comments and inline comments for the current branch's pull request.

**Usage**:
```bash
./copilot-pr-comments.sh
```

**Prerequisites**:
- Must be run from within a git repository
- Requires GitHub CLI (`gh`) to be installed and authenticated
- Current branch must have an open pull request

**Behavior**:
- Automatically detects the current git branch
- Finds the associated pull request for that branch
- Retrieves both general review comments and inline comments from GitHub Copilot
- Displays formatted output with warnings about potential inaccuracies
- Lists all open PRs if no PR is found for the current branch

**Output**: Formatted GitHub Copilot comments with file locations and line numbers, plus cautionary warnings about review accuracy.

### move_code_section.py

**Purpose**: Moves a specified section of code (by line numbers) from one file to another.

**Usage**:
```bash
python move_code_section.py <source_file> <start_line> <end_line> <dest_file> [--create-if-missing]
```

**Parameters**:
- `source_file`: Path to the file containing the code section to move
- `start_line`: Starting line number (1-based indexing)
- `end_line`: Ending line number (inclusive, 1-based indexing)
- `dest_file`: Path to the destination file
- `--create-if-missing`: Optional flag to create the destination file if it doesn't exist

**Behavior**:
- Extracts the specified line range from the source file
- Removes the extracted section from the source file
- Appends the section to the destination file (or creates a new file with Go package structure)
- When creating new Go files, automatically adds "package output" header and copies relevant imports
- Validates line numbers and file existence before performing operations

**Example**:
```bash
python move_code_section.py src/main.go 15 25 src/utils.go --create-if-missing
```

### test-conversion/ (Go Application)

**Purpose**: Converts Go test files from slice-based table-driven tests to map-based table-driven tests for better test isolation and cleaner syntax.

**Usage**:
```bash
cd test-conversion
go run . <file.go>      # Convert single test file
go run . <directory>    # Convert all _test.go files in directory
```

**What it converts**:
- Transforms slice-based test tables with `name` field to map-based test tables where the test name becomes the map key
- Updates the corresponding `for` loop to use map iteration pattern
- Removes redundant `name` field from test structs

**Benefits**:
- Better test isolation with unique test names as map keys
- Easier debugging with prominent test names
- Follows modern Go testing best practices
- Cleaner, more readable test code structure

**Example transformation**:
From: `tests := []struct { name string; ... }` with `for _, tt := range tests`
To: `tests := map[string]struct { ... }` with `for name, tt := range tests`

## Tests

Run the renderer test suite from the repository root with:

```bash
make test
```

This runs `cd scripts && python3 -m unittest discover -s tests -t .`. Tests live in `scripts/tests/` with fixtures under `scripts/tests/fixtures/`. `fixtures/golden.html` is the page the renderer at commit `9da40cf` produced from `fixtures/golden.json`; `test_golden.py` renders the same JSON with the current entry point and compares the two after blanking the `<style>` contents and the `Generated …` footer line. Regenerate the golden page only when the rendering contract intentionally changes.

## Agent Usage Notes

- Both scripts include error handling and provide informative output messages
- The copilot script requires network access and GitHub authentication
- The move_code_section script is designed with Go project structure in mind but works with any text files
- The test-conversion tool requires Go to be installed
- Always verify the results of these scripts, especially when moving code sections or converting test files
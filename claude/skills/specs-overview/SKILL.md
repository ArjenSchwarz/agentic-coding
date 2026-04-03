---
name: specs-overview
description: Generate or regenerate specs/OVERVIEW.md with a tabular summary, status, and per-spec file listings
---

# Specs Overview Generator

Generate a `specs/OVERVIEW.md` file that catalogues all feature specs in the project's `specs/` directory. This skill can create the file from scratch or fully regenerate it.

## Prerequisites

- A `specs/` directory must exist in the project root
- At least one spec subdirectory must exist with spec files (requirements.md, smolspec.md, design.md, plan.md, etc.)

## Process

### 1. Discover Specs

- List all subdirectories under `specs/`
- Exclude `specs/bugfixes/` (bug-specific specs are tracked separately)
- For each directory, collect:
  - **Directory name** (used as the spec identifier)
  - **Display name** (derived from directory name: kebab-case to Title Case)
  - **Creation date** (earliest git commit that added files in the directory): `git log --diff-filter=A --format='%aI' -- 'specs/{dirname}/'` — take the last (oldest) entry, format as YYYY-MM-DD
  - **Status** — determined by examining the spec's task file:
    - `Done` — all tasks are completed (all checkboxes checked)
    - `In Progress` — some tasks are completed, some remain
    - `Planned` — tasks exist but none are completed
    - `No Tasks` — no tasks.md file exists
  - **Summary** — a one-sentence description (max ~15 words) extracted from the first substantive paragraph of the primary document (check in order: requirements.md, smolspec.md, design.md, plan.md, implementation.md)
  - **Files** — list of all `.md` files in the directory (exclude non-documentation artifacts like `comparison-report` directories)

### 2. Generate the Overview

The output file `specs/OVERVIEW.md` MUST follow this structure:

```markdown
# Specs Overview

| Name | Creation Date | Status | Summary |
|------|---------------|--------|---------|
| [Spec Name](#anchor) | YYYY-MM-DD | Status | One-line summary |
...

---

## Spec Name

One-line summary.

- [filename.md](spec-dir/filename.md)
- [filename2.md](spec-dir/filename2.md)
...
```

**Table rules:**
- Sort rows chronologically by creation date (oldest first)
- Name column links to the detail section anchor below the table (e.g., `[Spec Name](#spec-name)`)
- Anchors are the display name lowercased with spaces replaced by hyphens

**Detail section rules:**
- One H2 section per spec, in the same chronological order as the table
- Summary line repeated below the heading
- Bulleted list of all `.md` files in the spec directory, each linking to the file relative to `specs/`
- Exclude non-markdown items (directories like `comparison-report`, `.DS_Store`, etc.)

### 3. Write the File

- Write the complete file to `specs/OVERVIEW.md`
- If the file already exists, overwrite it entirely (this is a full regeneration)

## Constraints

- The model MUST NOT include specs from `specs/bugfixes/`
- The model MUST use git history for creation dates, not filesystem timestamps
- The model MUST examine task files to determine status, not guess from other signals
- The model SHOULD parallelize git date lookups and file reads where possible for efficiency
- The model MUST NOT create any files other than `specs/OVERVIEW.md`

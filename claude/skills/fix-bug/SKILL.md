---
name: fix-bug
description: Systematic bug investigation, resolution, and documentation. Use when fixing bugs that need thorough analysis, test coverage, and a formal bugfix report. Applies systematic debugging methodology, creates regression tests, and generates a standardized report in specs/bugfixes/<bug-name>/. Triggers on requests like "fix this bug", "debug and document this issue", or when a bug needs both resolution and documentation.
# model: inherit
# allowed-tools: Read,Write,Edit,Bash,Grep,Glob,Task
---

# Bug Fix Workflow

Fix bugs systematically while ensuring proper test coverage and documentation.

## Transit Integration

If a `T-[number]` ticket is mentioned (e.g., `T-42`), track it throughout the workflow:
- Extract the display ID from the reference
- Automatically create a branch named `T-{number}/bugfix-{bug-name}` (no user prompt needed)
- Move the ticket to `in-progress` status after branch creation. Add a comment: "Starting bugfix — investigating on branch T-{number}/bugfix-{bug-name}"
- Move the ticket to `ready-for-review` status after the PR is created. Add a comment: "Fix ready for review — PR #{pr-number}"

Use `mcp__transit__update_task_status` with the display ID to update status. Always include a comment when changing status.

If no Transit ticket is mentioned, skip all Transit-related steps.

## Workflow

### 1. Bug Name

Determine a concise, descriptive bug name (kebab-case) for the report directory. Derive from the issue description or ask the user if unclear.

### 2. Branch Creation

**When a Transit ticket is present:** Automatically create a branch named `T-{number}/bugfix-{bug-name}` and switch to it. Do not ask for permission. Move the ticket to `in-progress` status.

**When no Transit ticket is present:** Use AskUserQuestion to offer branch naming options:
- `bugfix/{bug-name}` - Standard bugfix branch
- Skip branch creation

### 3. Systematic Investigation

Invoke the `systematic-debugger` skill to perform structured root cause analysis:
- Phase 1: Initial Overview (problem statement)
- Phase 2: Systematic Inspection (identify defects)
- Phase 3: Root Cause Analysis (Five Whys)
- Phase 4: Solution & Verification (proposed fixes)

Capture findings for the bugfix report.

### 4. Create Regression Test

Before implementing the fix:
1. Write a failing test that reproduces the bug
2. Run the test to confirm it fails as expected
3. This test prevents future regressions

The test should:
- Be minimal and focused on the specific bug
- Include a descriptive name referencing the bug
- Document the expected vs actual behaviour in comments

### 5. Implement Fix

Apply the fix identified during investigation:
1. Make minimal, targeted changes
2. Run the regression test to confirm it passes
3. Run full test suite to ensure no breakage
4. Run linters/validators as per project conventions

### 6. Update Documentation

Review and update any affected documentation:
- Code comments if behaviour changed
- README or docs if user-facing
- API docs if interface changed

### 7. Generate Bugfix Report

Create `specs/bugfixes/<bug-name>/report.md` using the template in `references/report-template.md`.

### 8. Commit and PR (Transit bugs only)

When a Transit ticket is present, after all checks pass:
1. Commit all changes using the `/commit` skill
2. Push the branch to the remote
3. Create a PR using `gh pr create` with:
   - Title: `Fix T-{number}: {bug-name-in-title-case}`
   - Body: Summary of the bug, root cause, and fix (reference the bugfix report)
4. Move the Transit ticket to `ready-for-review` status. Add a comment with the PR URL.

When no Transit ticket is present, do not commit or create a PR unless asked.

## Output

Upon completion:
1. Bug is fixed and verified
2. Regression test exists and passes
3. Full test suite passes
4. Report exists at `specs/bugfixes/<bug-name>/report.md`
5. If a Transit ticket was tracked: changes committed, PR created, ticket moved to `ready-for-review`
6. If no Transit ticket: code is ready for commit (do not commit unless asked)

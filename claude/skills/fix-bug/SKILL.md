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
- Move the ticket to `in-progress` status at the start of work (after branch creation or before investigation)
- Move the ticket to `ready-for-review` status after the workflow completes

Use `mcp__transit__update_task_status` with the display ID to update status.

If no Transit ticket is mentioned, skip all Transit-related steps.

## Workflow

### 1. Bug Name

Determine a concise, descriptive bug name (kebab-case) for the report directory. Derive from the issue description or ask the user if unclear.

### 2. Branch Creation (Optional)

Offer to create a bugfix branch before starting investigation.

Use AskUserQuestion to offer branch naming options:
- `T-{number}/bugfix-{bug-name}` - When a Transit ticket is present (recommended)
- `bugfix/{bug-name}` - Standard bugfix branch
- Skip branch creation

If a branch is created and a Transit ticket is present, move the ticket to `in-progress` status via `mcp__transit__update_task_status`.

If branch creation is skipped and a Transit ticket is present, still move the ticket to `in-progress` before proceeding.

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

## Output

Upon completion:
1. Bug is fixed and verified
2. Regression test exists and passes
3. Full test suite passes
4. Report exists at `specs/bugfixes/<bug-name>/report.md`
5. Code is ready for commit (do not commit unless asked)
6. If a Transit ticket was tracked, move it to `ready-for-review` status via `mcp__transit__update_task_status`

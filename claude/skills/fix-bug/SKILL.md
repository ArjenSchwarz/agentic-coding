---
name: fix-bug
description: Systematic bug investigation, resolution, and documentation. Use when fixing bugs that need thorough analysis, test coverage, and a formal bugfix report. Applies systematic debugging methodology, creates regression tests, and generates a standardized report in specs/bugfixes/<bug-name>/. Triggers on requests like "fix this bug", "debug and document this issue", or when a bug needs both resolution and documentation.
# model: inherit
# allowed-tools: Read,Write,Edit,Bash,Grep,Glob,Task
---

# Bug Fix Workflow

Fix bugs systematically while ensuring proper test coverage and documentation.

## Workflow

### 1. Bug Name

Determine a concise, descriptive bug name (kebab-case) for the report directory. Derive from the issue description or ask the user if unclear.

### 2. Systematic Investigation

Invoke the `systematic-debugger` skill to perform structured root cause analysis:
- Phase 1: Initial Overview (problem statement)
- Phase 2: Systematic Inspection (identify defects)
- Phase 3: Root Cause Analysis (Five Whys)
- Phase 4: Solution & Verification (proposed fixes)

Capture findings for the bugfix report.

### 3. Create Regression Test

Before implementing the fix:
1. Write a failing test that reproduces the bug
2. Run the test to confirm it fails as expected
3. This test prevents future regressions

The test should:
- Be minimal and focused on the specific bug
- Include a descriptive name referencing the bug
- Document the expected vs actual behaviour in comments

### 4. Implement Fix

Apply the fix identified during investigation:
1. Make minimal, targeted changes
2. Run the regression test to confirm it passes
3. Run full test suite to ensure no breakage
4. Run linters/validators as per project conventions

### 5. Update Documentation

Review and update any affected documentation:
- Code comments if behaviour changed
- README or docs if user-facing
- API docs if interface changed

### 6. Generate Bugfix Report

Create `specs/bugfixes/<bug-name>/report.md` using the template in `references/report-template.md`.

## Output

Upon completion:
1. Bug is fixed and verified
2. Regression test exists and passes
3. Full test suite passes
4. Report exists at `specs/bugfixes/<bug-name>/report.md`
5. Code is ready for commit (do not commit unless asked)

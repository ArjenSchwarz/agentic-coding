# Bugfix Report Template

Use this template when creating `specs/bugfixes/<bug-name>/report.md`.

---

```markdown
# Bugfix Report: <Bug Name>

**Date:** YYYY-MM-DD
**Status:** Fixed

## Description of the Issue

<What was happening and how it manifested>

**Reproduction steps:**
1. <Step to reproduce>
2. <Step to reproduce>
3. <Observe the bug>

**Impact:** <Severity and scope - who/what was affected>

## Investigation Summary

<Overview of the systematic debugging process>

- **Symptoms examined:** <What was observed>
- **Code inspected:** <Key files/areas reviewed>
- **Hypotheses tested:** <What was considered and ruled out>

## Discovered Root Cause

<The fundamental defect that caused the bug>

**Defect type:** <e.g., Logic error, Race condition, Missing validation, etc.>

**Why it occurred:** <Chain of causation - what led to this defect existing>

**Contributing factors:** <Any environmental or design factors>

## Resolution for the Issue

**Changes made:**
- `path/to/file.ext:line` - <Description of change>

**Approach rationale:** <Why this fix was chosen>

**Alternatives considered:**
- <Alternative approach> - <Why not chosen>

## Regression Test

**Test file:** `path/to/test_file.ext`
**Test name:** `test_<descriptive_name>`

**What it verifies:** <The specific behaviour being tested>

**Run command:** `<command to run the test>`

## Affected Files

| File | Change |
|------|--------|
| `path/to/file.ext` | <Brief description> |

## Verification

**Automated:**
- [ ] Regression test passes
- [ ] Full test suite passes
- [ ] Linters/validators pass

**Manual verification:**
- <Any manual steps taken to verify>

## Prevention

**Recommendations to avoid similar bugs:**
- <Code pattern to avoid or adopt>
- <Process improvement>
- <Additional safeguards to consider>

## Related

- <Links to related issues, PRs, or documentation>
```

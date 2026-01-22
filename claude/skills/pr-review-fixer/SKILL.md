---
name: pr-review-fixer
description: Fetch unresolved PR review comments, validate issues, and fix them. Use when reviewing and addressing GitHub PR feedback. Filters out resolved comments, keeps only the last claude[bot] comment per thread, creates review-overview and task files with iteration tracking, then fixes validated issues.
# model: inherit
# allowed-tools: Bash,Read,Write,Edit,Grep,Glob
---

# PR Review Fixer

Fetch unresolved PR comments, validate each issue, create a fix plan, and implement fixes.

## Workflow

### 1. Fetch PR Comments

```bash
# Get PR info
PR_NUM=$(gh pr view --json number --jq '.number')

# Get review threads with resolution status via GraphQL
gh api graphql -f query='
  query($owner: String!, $repo: String!, $pr: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        reviewThreads(first: 100) {
          nodes {
            isResolved
            comments(first: 50) {
              nodes { id body author { login } path line }
            }
          }
        }
      }
    }
  }
' -f owner=OWNER -f repo=REPO -F pr=$PR_NUM
```

### 2. Filter Comments

1. **Exclude resolved threads**: Filter out threads where `isResolved: true`
2. **claude[bot] handling**: For `claude[bot]` comments, keep only the **last comment** per thread
3. **Group by file/location**: Organize by path and line number

### 3. Determine Output Location

**Spec detection** (in order):
1. Check if branch name matches a folder in `specs/`
2. Check if PR modifies files in `specs/` directory

**Output paths**:
- Spec PRs: `specs/[name]/review-overview-[N].md` and `specs/[name]/review-fixes-[N].md`
- Non-spec PRs: `.claude/reviews/review-overview-[N].md` and `.claude/reviews/review-fixes-[N].md`

**Iteration**: Find highest existing iteration number in output dir, increment by 1.

### 4. Validate Issues

For each unresolved comment:
1. Read the referenced code at path:line
2. Evaluate: Is issue still present? Is suggestion correct? Does it align with project conventions?
3. Mark as valid or invalid with brief rationale

### 5. Create Review Overview

Write `review-overview-[N].md`:

```markdown
# PR Review Overview - Iteration [N]

**PR**: #[number] | **Branch**: [name] | **Date**: [YYYY-MM-DD]

## Valid Issues

### Issue 1: [title]
- **File**: `path:line`
- **Reviewer**: @user
- **Comment**: [quoted]
- **Validation**: [rationale]

## Invalid/Skipped Issues

### Issue A: [title]
- **File**: `path:line`
- **Reviewer**: @user
- **Comment**: [quoted]
- **Reason**: [why invalid]
```

### 6. Create Task List

Use rune to create `review-fixes-[N].md`:

```bash
rune create ${OUTPUT_DIR}/review-fixes-${N}.md \
  --title "PR Review Fixes - Iteration ${N}" \
  --reference ${OUTPUT_DIR}/review-overview-${N}.md

# Add tasks via batch for efficiency
rune batch ${OUTPUT_DIR}/review-fixes-${N}.md --input '{
  "file": "review-fixes-'${N}'.md",
  "operations": [
    {"type": "add", "title": "Fix: [issue 1]"},
    {"type": "add", "title": "Fix: [issue 2]"}
  ]
}'
```

### 7. Fix Issues

Loop through tasks:
1. `rune next [file]` - get next task
2. `rune progress [file] [id]` - mark in-progress
3. Implement the fix
4. `rune complete [file] [id]` - mark complete
5. Repeat until done

## Key Behaviors

- **Auto-fix**: Fix all validated issues without pausing for approval
- **Context preservation**: Keep diff_hunk context when analyzing
- **Convention adherence**: Follow project's existing patterns
- **Deduplication**: Consolidate multiple comments on same issue into one task

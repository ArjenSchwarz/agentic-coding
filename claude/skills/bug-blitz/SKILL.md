---
name: bug-blitz
description: Batch-fix all open bugs in parallel using git worktrees. Fetches bug-type tasks in "idea" status from Transit, creates an isolated worktree per bug, and spawns parallel subagents each running the fix-bug workflow. Use when you want to tackle all open bugs at once, e.g. "fix all open bugs", "bug blitz", "resolve all Transit bugs".
# model: inherit
# allowed-tools: Read,Write,Edit,Bash,Grep,Glob,Task
---

# Bug Blitz

Resolve all open bugs in parallel — one worktree and one subagent per bug.

## Workflow

### 1. Fetch Bugs

Query Transit for all bug-type tasks in "idea" status:

```
mcp__transit__query_tasks(type="bug", status="idea")
```

If the current project has a Transit project ID, filter by `projectId` as well.

If no bugs are found, inform the user and stop.

Present the list of bugs to the user with their `T-{displayId}` references and names. Ask for confirmation before proceeding. The user may choose to exclude specific bugs.

### 2. Create Worktrees

For each confirmed bug:

1. Derive a bug name in kebab-case from the task name
2. Create a worktree based off `main` with branch `T-{displayId}/bugfix-{bug-name}`:
   ```
   git worktree add ../{repo-name}-worktrees/T-{displayId} -b T-{displayId}/bugfix-{bug-name} main
   ```

All worktrees go in a sibling directory `../{repo-name}-worktrees/` to keep the main repo clean. Use the repo's directory name as `{repo-name}`.

If a worktree or branch already exists for a bug, skip creation and reuse it.

### 3. Spawn Subagents

Spawn one Task subagent per bug using `subagent_type="general-purpose"`. Run all subagents in parallel (single message, multiple Task tool calls).

Each subagent receives this prompt (fill in the values):

```
You are working in a git worktree at {worktree_path}.

Fix the bug described by Transit ticket T-{displayId}:
- Name: {task_name}
- Description: {task_description}

Run the /fix-bug skill with the ticket reference T-{displayId}.
The worktree already has the correct branch checked out — do NOT create a new branch or switch branches.
Work entirely within {worktree_path} as your working directory.
```

Important: The fix-bug skill handles branch creation as part of its Transit integration. Since the worktree already has the correct branch, the subagent's working directory ensures it operates in the right place. The fix-bug skill will detect the existing branch and skip branch creation.

### 4. Report Results

After all subagents complete, summarise results in a table:

| Bug | Branch | Status | PR |
|-----|--------|--------|----|
| T-{id}: {name} | T-{id}/bugfix-{name} | success/failed | #{pr} or — |

### 5. Cleanup

After reporting, offer to remove the worktrees:

```
git worktree remove ../{repo-name}-worktrees/T-{displayId}
```

Only remove worktrees for successfully resolved bugs (PR created). Keep worktrees for failed bugs so the user can investigate.

---
name: code-audit
description: >-
  Parallel code audit combining simplification and design critique analysis.
  Spawns two subagents (code-simplifier and design-critic) to independently
  review the current directory, consolidates findings into a prioritised report,
  and offers to create Transit tasks for actionable items. Use when you want a
  broad quality review of a codebase, e.g. "audit this code", "review codebase
  quality", "find improvements", "code audit".
# model: inherit
# allowed-tools: "Read,Glob,Grep,Task,Bash(ls:*)"
---

# Code Audit

Parallel codebase quality review that orchestrates the `code-simplifier` and `design-critic` skills via subagents, then consolidates and presents findings.

## Workflow

### Phase 1: Parallel Analysis

Launch two `general-purpose` subagents in parallel using the Task tool:

**Subagent A — Code Simplifier**

Prompt the subagent to use the `code-simplifier` skill (via the Skill tool) against the current working directory. Instruct it to:
- Scan source files for complexity hotspots, unnecessary abstractions, and simplification opportunities
- Return a structured list of findings, each with: file path, line range, issue summary, suggested fix, and severity (high/medium/low)

**Subagent B — Design Critic**

Prompt the subagent to use the `design-critic` skill (via the Skill tool) against the current working directory. Instruct it to:
- Review architecture, module boundaries, data flow, and design decisions visible in the code
- Return a structured list of findings, each with: scope (file/module/system), issue summary, questions to resolve, and severity (high/medium/low)

Both subagents should focus on the current working directory and respect any project conventions in CLAUDE.md.

### Phase 2: Consolidation

After both subagents complete:

1. Deduplicate overlapping findings (same file + same concern)
2. Group findings into categories:
   - **Simplification** — complexity reduction, readability
   - **Architecture** — design issues, module boundaries, abstraction problems
   - **Shared concerns** — findings flagged by both analyses
3. Sort by severity (high first), then by category

### Phase 3: Present Report

Present findings to the user in this format:

```
## Code Audit: {directory name}

### Shared Concerns
{Findings flagged by both subagents — these are highest signal}

### Architecture Issues
{Design critic findings, sorted by severity}

### Simplification Opportunities
{Code simplifier findings, sorted by severity}

### Summary
- {total} findings: {high} high, {medium} medium, {low} low
```

Each finding should include: location, description, and suggested action.

### Phase 4: Transit Tasks

After presenting the report, ask the user if they want Transit tasks created for any findings. If yes:

- Create one task per actionable finding (or group related findings into a single task)
- Use type `chore` for simplification items, `bug` for design issues that could cause problems
- Include the finding details in the task description
- Use `mcp__transit__create_task` to create tasks

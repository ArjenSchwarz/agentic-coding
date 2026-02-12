---
name: transit
description: Route Transit tickets to the appropriate workflow based on task type. Use when a user mentions a T-[number] ticket reference and wants to work on it. Fetches task details and dispatches to the correct skill (fix-bug, creating-spec, planning mode, or asks for clarification).
---

# Transit Ticket Router

Route Transit tickets to the appropriate workflow based on their task type.

## Workflow

### 1. Extract Ticket Reference

Parse the `T-[number]` reference from the user input. Extract the numeric display ID (e.g., `T-42` -> display ID `42`).

If no valid `T-[number]` reference is found, ask the user which ticket they want to work on.

### 2. Fetch Task Details

Query Transit for the task using `mcp__transit__query_tasks`. Match the task by its display ID from the results.

**If task is not found:** Stop and inform the user that the ticket could not be found in Transit. Do not proceed.

**If task status is `done` or `abandoned`:** Warn the user that the ticket is already marked as `{status}` and ask whether they still want to proceed. Stop if they decline.

### 3. Route by Task Type

Based on the task's `type` field, route to the appropriate workflow:

| Type | Action |
|------|--------|
| `bug` | Invoke `/fix-bug` and pass the ticket reference (`T-{number}`) and task context (name, description) |
| `feature` | Invoke `/starwave:creating-spec` and pass the ticket reference (`T-{number}`) and task context (name, description) |
| `research` | Enter planning mode with the research question from the task description |
| `chore` | Ask the user to clarify: is this closer to a bug fix or a feature? Route accordingly |
| `documentation` | Ask the user to clarify the scope, then route to the appropriate workflow |

### 4. Handoff

When routing to a skill, include:
- The Transit ticket reference (e.g., `T-42`)
- The task name and description from Transit as context
- Any relevant metadata from the task

The target skill is responsible for managing Transit status transitions from that point forward.

## Edge Cases

- **Ambiguous type:** If the task type doesn't clearly map to a workflow, ask a single clarifying question before routing.
- **Missing description:** If the task has no description, ask the user to provide context about what needs to be done.

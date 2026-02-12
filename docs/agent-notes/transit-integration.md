# Transit Integration

Transit is the project management tool accessed via MCP. Tickets use `T-[number]` format (e.g., T-42).

## MCP Tools

- `mcp__transit__query_tasks` - Search/filter tasks. All filters optional.
- `mcp__transit__update_task_status` - Move a task to a new status. Use `displayId` (numeric part of T-number) to identify tasks.
- `mcp__transit__create_task` - Create new tasks.

## Transit Statuses

`idea` -> `planning` -> `spec` -> `ready-for-implementation` -> `in-progress` -> `ready-for-review` -> `done` / `abandoned`

## Skills with Transit Integration

### `/transit` (router skill)
- Fetches task details and routes by type: bug -> `/fix-bug`, feature -> `/starwave:creating-spec`, research -> plan mode, chore/documentation -> asks user to clarify.
- Does not manage status transitions itself; delegates to target skills.

### `/starwave:creating-spec`
- Moves ticket to `spec` after scope assessment approval (Phase 1).
- Moves ticket to `ready-for-implementation` at end of Phase 5.
- Branch naming: `T-{number}/{spec-name}` is recommended default when ticket present.

### `/fix-bug`
- Moves ticket to `in-progress` after branch creation (or before investigation if branch skipped).
- Moves ticket to `ready-for-review` at workflow completion.
- Branch naming: `T-{number}/bugfix-{bug-name}` is recommended default when ticket present.

### `/commit`
- Ticket extraction pattern updated to support 1-5 letter prefixes (was 3-5), so `T-42` format matches.

## Key Design Decisions

- Transit integration is opt-in: all skills skip Transit steps when no ticket is mentioned.
- The transit router skill only dispatches; target skills own their status transitions.
- Branch naming puts the ticket reference first (`T-42/feature-name`) for easy extraction by the commit skill.

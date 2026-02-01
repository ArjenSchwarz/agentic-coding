---
name: rune-tasks
description: Manage hierarchical task lists using the rune CLI tool. Create, update, and organize tasks with phases, subtasks, status tracking, task dependencies, and work streams for multi-agent parallel execution.
---

# Rune Task Management Skill

You are a specialized assistant for managing hierarchical task lists using the `rune` CLI tool.

## Your Capabilities

You excel at:
- Creating new task files with proper structure
- Adding tasks and subtasks with appropriate hierarchy
- Organizing tasks into phases for logical grouping
- Tracking task status (pending, in-progress, completed)
- Finding and querying tasks efficiently
- Using batch operations for atomic multi-task updates
- Managing task dependencies and references
- Coordinating multi-agent parallel execution with work streams
- Managing task dependencies (blocked-by relationships)
- Claiming and releasing task ownership for agents

## Rune Command Reference

### Core Commands

**Creating and Listing:**
- `rune create [file] --title "Title"` - Initialize a new task file (title is required)
- `rune create [file] --title "Title" --reference "file.md"` - Create with top-level references (repeatable flag)
- `rune list [file]` - Display all tasks (supports --filter for status, --format for output)
- `rune list [file] --stream 2` - Filter to tasks in stream 2
- `rune list [file] --owner "agent-1"` - Filter to tasks owned by agent-1
- `rune list [file] --owner ""` - Filter to unowned tasks
- `rune next [file]` - Get the next incomplete task
- `rune next [file] --stream 2` - Get next ready task in stream 2
- `rune next [file] --claim "agent-1"` - Claim and start the next ready task
- `rune next [file] --stream 2 --claim "agent-1"` - Claim all ready tasks in stream 2
- `rune next [file] --phase` - Get all tasks from the next phase
- `rune streams [file]` - Show status of all work streams
- `rune streams [file] --available` - Show only streams with ready tasks
- `rune streams [file] --json` - Output stream status as JSON

**Task Management:**
- `rune add [file] --title "Task name"` - Add a top-level task
- `rune add [file] --title "Subtask" --parent "1.2"` - Add a subtask
- `rune add [file] --title "Task" --phase "Phase Name"` - Add task to a phase
- `rune add [file] --title "Task" --stream 2` - Add task to stream 2
- `rune add [file] --title "Task" --blocked-by "1,2"` - Add task blocked by tasks 1 and 2
- `rune add [file] --title "Task" --owner "agent-1"` - Add task owned by agent-1
- `rune complete [file] [task-id]` - Mark task as completed (task-id is positional, e.g., `rune complete tasks.md 1.2`)
- `rune progress [file] [task-id]` - Mark task as in-progress (task-id is positional)
- `rune uncomplete [file] [task-id]` - Mark task as pending (task-id is positional)
- `rune update [file] [task-id] --title "New title"` - Update task title (task-id is positional)
- `rune update [file] [task-id] --details "Details"` - Add/update task details
- `rune update [file] [task-id] --stream 2` - Assign task to stream 2
- `rune update [file] [task-id] --blocked-by "1,2"` - Set task dependencies
- `rune update [file] [task-id] --owner "agent-1"` - Claim task for agent
- `rune update [file] [task-id] --release` - Release task ownership
- `rune remove [file] [task-id]` - Remove task and subtasks (task-id is positional)

**Organization:**
- `rune add-phase [file] "Phase Name"` - Add a new phase (name is positional)
- `rune has-phases [file]` - Check if file uses phases
- `rune find [file] --pattern "search term"` - Search tasks
- `rune renumber [file]` - Recalculate all task IDs to sequential numbering (creates backup)

**Front Matter:**
- `rune add-frontmatter [file] --reference "file.md"` - Add references to existing file (repeatable flag)
- `rune add-frontmatter [file] --meta "key:value"` - Add metadata to front matter (repeatable flag)

**Batch Operations:**
- `rune batch [file] --input '{"file":"tasks.md","operations":[...]}'` - Execute multiple operations atomically

### Batch Operation Format

Batch operations use JSON input with the following structure:

```json
{
  "file": "tasks.md",
  "operations": [
    {
      "type": "add-phase",
      "phase": "Implementation"
    },
    {
      "type": "add",
      "title": "Task title",
      "parent": "1.2",
      "phase": "Phase Name",
      "requirements": ["1.1", "1.2"],
      "requirements_file": "requirements.md",
      "stream": 1,
      "blocked_by": ["1", "2"],
      "owner": "agent-1"
    },
    {
      "type": "update",
      "id": "2.1",
      "title": "Updated title",
      "status": 2,
      "details": "Additional details",
      "references": ["ref1", "ref2"],
      "stream": 2,
      "blocked_by": ["1"],
      "owner": "agent-2"
    },
    {
      "type": "update",
      "id": "3.1",
      "release": true
    },
    {
      "type": "remove",
      "id": "3"
    }
  ],
  "dry_run": false
}
```

**Operation Types:**
- `add` - Add a new task
  - Required: `title`
  - Optional: `parent`, `phase`, `requirements` (array of task IDs), `requirements_file`, `stream` (integer), `blocked_by` (array of task IDs), `owner` (string)
- `add-phase` - Create a new phase header
  - Required: `phase` (name of the phase to create)
  - Note: Phase is created at the end of the document
- `update` - Update an existing task
  - Required: `id`
  - Optional: `title`, `status` (0=pending, 1=in-progress, 2=completed), `details`, `references` (array of file paths), `stream` (integer), `blocked_by` (array of task IDs), `owner` (string), `release` (boolean, clears owner)
- `remove` - Remove a task and all its subtasks
  - Required: `id`

**Important**: In batch operations, `references`, `requirements`, and `blocked_by` must be arrays, not comma-separated strings:
- Correct: `"references": ["file1.md", "file2.md"]`
- Correct: `"blocked_by": ["1", "2"]`
- Incorrect: `"references": "file1.md,file2.md"`
- Incorrect: `"blocked_by": "1,2"`

**Status Values:**
- `0` - Pending
- `1` - In-progress
- `2` - Completed

All operations in a batch are atomic - either all succeed or none are applied.

### Task Status Types
- `[ ]` - Pending (not started)
- `[-]` - In-progress (currently working on)
- `[x]` - Completed (finished)

### Phases

Phases are H2 headers (`## Phase Name`) that group tasks. Tasks are numbered globally across phases.
- `rune add-phase [file] "Phase Name"` - Adds H2 header at end of file
- `rune add [file] --title "Task" --phase "Phase Name"` - Adds task under specified phase

### Renumbering

`rune renumber [file]` recalculates task IDs to sequential numbering.
- Creates .bak backup before changes
- Preserves hierarchy, statuses, and phase markers
- Does NOT update requirement links in task details
- Use `--dry-run` to preview
- Stable IDs (used for dependencies) survive renumbering

### Task Dependencies (Blocked-by)

Tasks can declare dependencies on other tasks using the `--blocked-by` flag. A task is "ready" only when all its blocking tasks are completed.

- `rune add [file] --title "Task" --blocked-by "1,2"` - Task blocked by tasks 1 and 2
- `rune update [file] [task-id] --blocked-by "1,2"` - Set/update dependencies
- Dependencies are stored as stable IDs (7-character alphanumeric) internally
- Circular dependencies are detected and rejected
- Deleting a task automatically removes it from dependent tasks' blocked-by lists

**Stable IDs**: Tasks have persistent stable IDs (hidden in markdown as HTML comments) that survive renumbering. These are used for dependency references and are generated automatically.

### Work Streams

Streams partition tasks for parallel agent execution. Each stream represents an independent workstream that can be processed concurrently.

- `rune streams [file]` - Show all streams with ready/blocked/active task counts
- `rune streams [file] --available` - Show only streams with ready tasks
- `rune streams [file] --json` - Machine-readable stream status
- Default stream is 1 for tasks without explicit assignment
- Streams are derived from task assignments (no upfront definition needed)

**Stream Status Output:**
```
Stream 1: 2 ready, 3 blocked, 1 active
Stream 2: 0 ready, 2 blocked, 0 active
```

### Task Ownership

Agents can claim tasks by setting an owner. This prevents multiple agents from working on the same task.

- `rune next [file] --claim "agent-1"` - Claim next ready task (sets owner and status to in-progress)
- `rune next [file] --stream 2 --claim "agent-1"` - Claim all ready tasks in stream 2
- `rune update [file] [task-id] --owner "agent-1"` - Manually claim a task
- `rune update [file] [task-id] --release` - Release ownership
- `rune list [file] --owner "agent-1"` - Filter to tasks owned by agent
- `rune list [file] --owner ""` - Filter to unowned tasks

### Git Integration
When git discovery is enabled in rune's config, you can omit the filename and rune will auto-discover based on the current branch.

## Workflow Guidelines

### When Creating Tasks
1. Check if a task file exists for the current context (use `rune list` or check git branch)
2. Create phases for logical grouping when tasks span multiple areas
3. Use clear, actionable task titles
4. Break complex tasks into subtasks with proper parent references
5. Link requirements when tasks relate to specification documents

### When Managing Tasks
1. Use `rune list --filter pending` to see what needs to be done
2. Use `rune next` to identify the next task to work on
3. Mark tasks as in-progress when starting work
4. Complete tasks immediately when finished
5. Use batch operations when making multiple related changes

### Multi-Agent Parallel Execution
1. Use `rune streams` to see available work streams
2. Assign agents to streams: `rune next --stream N --claim "agent-id"`
3. Each agent works independently within its claimed stream
4. Use `rune list --owner "agent-id"` to see an agent's tasks
5. Complete tasks to unblock dependent tasks in other streams
6. Use `--release` when an agent needs to give up a task

### When Organizing
1. Group related tasks under phases (e.g., "Planning", "Development", "Testing")
2. Use subtasks for breaking down complex work
3. Keep task hierarchy shallow (avoid deeply nested structures)
4. Use descriptive phase names that reflect workflow stages

### Output Formats
- Use `--format table` (default) for human-readable display
- Use `--format json` when you need to parse task data
- Use `--format markdown` for documentation or reports

## Best Practices

1. **Atomic Operations**: Use `rune batch` for related changes to ensure all-or-nothing updates
2. **Status Tracking**: Keep task status current - mark in-progress when starting, completed when done
3. **Hierarchy**: Use parent-child relationships to show task structure
4. **Dependencies**: Use `--blocked-by` to define execution order between tasks
5. **Streams**: Partition independent work into streams for parallel agent execution
6. **Phases**: Organize tasks by workflow stage or feature area
7. **Dry Run**: Use `--dry-run` flag to preview changes before applying them
8. **Git Integration**: Leverage branch-based file discovery for feature-specific task lists
9. **Batch for Multiple Updates**: When marking multiple tasks complete or updating status, use batch operations instead of individual commands for efficiency
10. **Auto-completion**: When all subtasks of a parent task are completed, the parent task is automatically marked as completed
11. **Filtering**: Use `--filter pending|in-progress|completed` with `rune list` to focus on tasks in specific states
12. **Search**: Use `rune find` to quickly locate tasks by keyword across titles and details
13. **Claiming Tasks**: Use `rune next --claim` to atomically claim and start tasks
14. **Stream Discovery**: Use `rune streams --available` to find streams with ready work

## Common Patterns

### Creating a New Task File
```bash
rune create tasks.md --title "Project Name or Description"
```

### Creating a Feature Task File with References
```bash
rune create specs/${feature_name}/tasks.md --title "Project Tasks" \
  --reference specs/${feature_name}/requirements.md \
  --reference specs/${feature_name}/design.md \
  --reference specs/${feature_name}/decision_log.md
```

### Creating a Phase and Adding Tasks to It
Use batch operations to create a phase and add tasks in one atomic operation:
```bash
rune batch tasks.md --input '{
  "file": "tasks.md",
  "operations": [
    {"type": "add-phase", "phase": "Implementation"},
    {"type": "add", "title": "Build core feature", "phase": "Implementation"},
    {"type": "add", "title": "Add error handling", "phase": "Implementation"}
  ]
}'
```

### Adding Multiple Related Tasks
Use batch operations to add a group of related tasks atomically:
```bash
rune batch tasks.md --input '{
  "file": "tasks.md",
  "operations": [
    {"type": "add", "title": "Parent Task", "phase": "Phase Name"},
    {"type": "add", "title": "Subtask 1", "parent": "1"},
    {"type": "add", "title": "Subtask 2", "parent": "1"}
  ]
}'
```

### Marking Multiple Tasks Complete
```bash
rune batch tasks.md --input '{
  "file": "tasks.md",
  "operations": [
    {"type": "update", "id": "1.1", "status": 2},
    {"type": "update", "id": "1.2", "status": 2},
    {"type": "update", "id": "2.1", "status": 2}
  ]
}'
```

### Adding References and Requirements
```bash
rune batch tasks.md --input '{
  "file": "tasks.md",
  "operations": [
    {
      "type": "update",
      "id": "2.1",
      "references": ["docs/api-spec.md", "examples/usage.md"]
    },
    {
      "type": "add",
      "title": "Integration tests",
      "requirements": ["1.2", "1.3"]
    }
  ]
}'
```

### Setting Up Tasks with Dependencies and Streams
```bash
rune batch tasks.md --input '{
  "file": "tasks.md",
  "operations": [
    {"type": "add", "title": "Initialize project", "stream": 1},
    {"type": "add", "title": "Configure database", "stream": 1, "blocked_by": ["1"]},
    {"type": "add", "title": "Build API", "stream": 1, "blocked_by": ["2"]},
    {"type": "add", "title": "Build UI", "stream": 2, "blocked_by": ["1"]},
    {"type": "add", "title": "Write tests", "stream": 2, "blocked_by": ["3", "4"]}
  ]
}'
```

### Multi-Agent Task Claiming
```bash
# Agent 1 claims all ready tasks in stream 1
rune next tasks.md --stream 1 --claim "agent-backend"

# Agent 2 claims all ready tasks in stream 2
rune next tasks.md --stream 2 --claim "agent-frontend"

# Check stream status
rune streams tasks.md

# Agent releases a task it can't complete
rune update tasks.md 3 --release
```

### Checking Available Work
```bash
# See which streams have ready tasks
rune streams tasks.md --available

# See all unowned pending tasks
rune list tasks.md --filter pending --owner ""

# Get JSON for programmatic processing
rune streams tasks.md --json
```

## Key Command Syntax Notes

### Positional vs Flag Arguments
Many rune commands use **positional arguments** for task IDs, not flags:

**Correct:**
- `rune complete tasks.md 1.2`
- `rune progress tasks.md 3.1`
- `rune update tasks.md 2.3 --title "New title"`
- `rune remove tasks.md 4`

**Incorrect:**
- `rune complete tasks.md --id 1.2` ❌
- `rune progress tasks.md --id 3.1` ❌

### Array Fields in Batch Operations
When using batch operations, `references` and `requirements` **must be arrays**:

**Correct:**
```json
{
  "type": "update",
  "id": "1.1",
  "references": ["file1.md", "file2.md"],
  "requirements": ["2.1", "2.2"]
}
```

**Incorrect:**
```json
{
  "type": "update",
  "id": "1.1",
  "references": "file1.md,file2.md",
  "requirements": "2.1,2.2"
}
```

### Output Formats
The `--format` flag supports three output modes:
- `table` - Default, human-readable table view
- `markdown` - Markdown checklist format with `[ ]`, `[-]`, `[x]` checkboxes
- `json` - Machine-readable JSON for parsing

### Task Filtering
The `--filter` flag with `rune list` accepts:
- `pending` - Show only incomplete tasks
- `in-progress` - Show only tasks currently being worked on
- `completed` - Show only finished tasks

Additional filters for multi-agent workflows:
- `--stream N` - Filter to tasks in stream N
- `--owner "agent-id"` - Filter to tasks owned by agent-id
- `--owner ""` - Filter to unowned tasks

### Markdown Storage Format for Dependencies/Streams

Tasks with dependencies, streams, or owners are stored with metadata as list items:

```markdown
- [ ] 1. Initialize project <!-- id:abc1234 -->
  - Details about initialization
  - Stream: 1

- [ ] 2. Configure database <!-- id:def5678 -->
  - Blocked-by: abc1234 (Initialize project)
  - Stream: 1

- [-] 3. Build API <!-- id:ghi9012 -->
  - Blocked-by: def5678 (Configure database)
  - Stream: 1
  - Owner: agent-backend
```

- **Stable IDs**: Hidden as HTML comments after the title (system-managed)
- **Blocked-by, Stream, Owner**: Visible list items under the task (user-editable)
- **Title hints**: Dependency references include task titles for readability

## Response Format

When managing tasks:
1. Explain what operations you'll perform
2. Execute the rune commands
3. Show the results (list updated tasks if relevant)
4. Confirm what was accomplished

Remember: Rune is designed for AI agents, so use it efficiently with batch operations when appropriate and always maintain clean, hierarchical task structures.

# Skills Usage

This project uses custom skills extensively. Available skills include: spec creation, PR review fixing, pre-push review, and explain-like. Check `.claude/skills/` for the full list before suggesting manual approaches.

When asked to analyze or document something, first check if there's an existing skill/workflow for that task (e.g., spec creation, review). Use the established workflow rather than doing ad-hoc analysis.

# Communication Style

- DO NOT overcomplicate things. There is beauty in simplicity and code needs to be easily understandable.
- DO NOT act sycophantic. Instead of praising the user, a simple statement acknowledging something is true is enough.
- DO NOT use hyperbolic terms like comprehensive. Be clear and concise in your wording.
- DO think through your answers and push back against ideas from the user when they might not lead to the best result. Explain why you disagree with the user.

# Development Workflow

- After writing code, you MUST ensure you use appropriate linters and validators.
- When you discover a learning specific to a language that needs to be kept, add it to the related language-rule file (or create a new one if needed).
- When managing tasks, use the rune skill.
- When creating GitHub issues, ALWAYS create them in the current repository unless explicitly told otherwise.

# Agent Notes

Maintain implementation notes in `docs/agent-notes/` to preserve knowledge across sessions.

**Before starting a task**: Check `docs/agent-notes/` for relevant notes and read them. Only read what's relevant — don't load everything.

**After completing a task**: Create or update notes about the code you worked on. Focus on:
- How things work (architecture, data flow, key abstractions)
- Non-obvious behavior, gotchas, and things that don't work as expected
- Why certain approaches were chosen or rejected
- Setup/configuration details that aren't obvious from the code

Keep notes factual and concise. Organise by topic or module (e.g., `auth.md`, `api-layer.md`) — not by date or task. Update existing notes rather than creating duplicates.

# Project Conventions

- When the user talks about a feature or spec, this will be a feature that has requirements, design, and tasks documents as well as a decision log in a subfolder of the specs directory. The feature's name will be that of the subfolder. It is possible not all of the files are present yet, but all files in that subfolder SHOULD be taken into consideration when discussing the feature. If the user does not mention the feature by name, check the current branch and verify if a matching feature exists.
- If `.claude/scripts/README.md` exists in the project, you SHOULD use the tools mentioned in there for their intended purposes.
- If a project has a Makefile, the commands there MUST be used for development tooling.
- References in the form `T-<id>` are Transit tickets. Query and update them using the Transit MCP tools (`mcp__transit__query_tasks`, `mcp__transit__update_task_status`, `mcp__transit__create_task`). Use the `transit` skill to route tickets to the appropriate workflow.

# CLI Commands

If `run_silent` is available (check with `which run_silent`), use it to reduce token usage by buffering stdout/stderr and only showing them on non-zero exit.

- Wrap bash/CLI commands with `run_silent` unless you need to see all the stdout
- Good commands to prefix: package installs, builds, tests, linting
- Examples:
  - `run_silent pnpm install`
  - `run_silent cargo check`
  - `run_silent make lint`

# Documentation Standards

When creating or updating decision log entries, follow the format in `rules/references/decision-log-format.md`. This uses the Enhanced Nygard ADR structure with required fields (ID, Date, Status, Context, Decision, Rationale) and recommended fields (Alternatives Considered, Consequences). Read the format file before creating entries.

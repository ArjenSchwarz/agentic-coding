# Skills Usage

This project uses custom skills extensively. Available skills include: spec creation, PR review fixing, pre-push review, and explain-like. Check `.claude/skills/` for the full list before suggesting manual approaches.

When asked to analyze or document something, first check if there's an existing skill/workflow for that task (e.g., spec creation, review). Use the established workflow rather than doing ad-hoc analysis.

# Communication Style

- DO NOT overcomplicate things. There is beauty in simplicity and code needs to be easily understandable.
- DO NOT act sycophantic. Instead of praising the user, a simple statement acknowledging something is true is enough.
- DO NOT use hyperbolic terms like comprehensive. Be clear and concise in your wording.
- DO think through your answers and push back against ideas from the user when they might not lead to the best result. Explain why you disagree with the user.

# Development Workflow

- Skills and routed workflows have approval gates — HONOUR THEM. When a skill says to present something and wait for approval (e.g. smolspec presents the spec, then the tasks), STOP and wait for an explicit go-ahead before continuing. A multi-step pipeline (e.g. spec → implement → commit → review → PR) is a sequence of gated phases, NOT a licence to run end-to-end autonomously.
- A cancelled, empty, or missing tool result is NOT success. If a tool call was cancelled (e.g. by a sibling error in a batch) or returned nothing, treat the step as NOT done — re-run and verify before reporting it. Never narrate an action (commit, push, PR, merge, review) as complete without confirming it actually happened.
- Before editing any file, read it first. Before modifying a function, grep for all callers. Research before you edit
- After writing code, you MUST ensure you use appropriate linters and validators.
- When you discover a learning specific to a language that needs to be kept, add it to the related language-rule file (or create a new one if needed).
- When managing tasks, use the rune skill.
- When creating GitHub issues, ALWAYS create them in the current repository unless explicitly told otherwise.

# Persisting Knowledge

Two destinations, picked by scope. Default to writing nothing — only persist what a future session would otherwise re-investigate.

## Cross-project patterns → `/capture-knowledge` and `/recall-knowledge`

**Before starting a task**: if it touches a framework, language, or domain you've worked in before, run `/recall-knowledge` to see if the vault already has notes — a quick check beats re-investigating something you already documented.

If what you learned would help on a *different* project (framework gotchas, integration recipes, reusable patterns, platform quirks), use the `/capture-knowledge` skill to write it into the Obsidian vault. This is the preferred destination for anything generalizable. Be proactive: when you've just solved something non-obvious that isn't tied to this one repo, offer to capture it even if the user didn't ask.

## Project-specific notes → `docs/agent-notes/`

For knowledge that only makes sense inside this one repo (subsystem flow, in-flight refactor state, where-to-look pointers), use `docs/agent-notes/`.

**Before starting a task**: check `docs/agent-notes/` for relevant notes and read what's relevant. Don't load everything.

**Write a note only when** a future session would otherwise re-investigate the same thing — a non-obvious gotcha, a rejected approach worth remembering, a subsystem flow not derivable from the code. Do NOT write a note as a checkbox at task end; most tasks shouldn't produce a note.

**Do NOT duplicate CLAUDE.md.** If the project's CLAUDE.md already covers it (architecture overview, file structure, conventions), don't restate it in agent-notes.

Organise by topic or module (e.g., `auth.md`, `api-layer.md`). Update existing notes rather than creating duplicates. If you find a note that's stale or wrong, fix or delete it — a stale note is worse than no note.

# Project Conventions

- When the user talks about a feature or spec, this will be a feature that has requirements, design, and tasks documents as well as a decision log in a subfolder of the specs directory. The feature's name will be that of the subfolder. It is possible not all of the files are present yet, but all files in that subfolder SHOULD be taken into consideration when discussing the feature. If the user does not mention the feature by name, check the current branch and verify if a matching feature exists.
- If `.claude/scripts/README.md` exists in the project, you SHOULD use the tools mentioned in there for their intended purposes.
- If a project has a Makefile, the commands there MUST be used for development tooling.
- References in the form `T-<id>` are Transit tickets. Query and update them using the Transit MCP tools (`mcp__transit__query_tasks`, `mcp__transit__update_task_status`, `mcp__transit__create_task`). Use the `transit` skill to route tickets to the appropriate workflow.
- When changing a Transit ticket's status, ALWAYS add a comment explaining why the status was changed (e.g., "Moving to spec — scope assessment approved", "Marking done — all tasks implemented and tests passing").

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

---
name: claude-code-workshop
description: >-
  Interactive Claude Code workshop that teaches features through hands-on exploration.
  Fetches the latest docs and changelog, organizes content into modules (basics, hooks, MCP,
  skills, subagents, etc.), and walks through each one step-by-step with explanations and
  live exercises in the current project. Supports version-based filtering to focus on what's
  new since a specific release (e.g., "everything from 2.1.90"). Use this skill whenever the
  user wants to learn Claude Code features, run a workshop, catch up on recent releases,
  explore what's new, get a guided tour of Claude Code capabilities, or says things like
  "teach me about Claude Code", "what's new in Claude Code", "workshop", or "walk me through
  the latest features".
---

# Claude Code Workshop

An interactive, hands-on workshop for learning Claude Code features. Works as both a getting-started guide and a "what's new" walkthrough for recent releases.

## How It Works

You are a workshop facilitator. Your job is to teach Claude Code features through a combination of explanation, demonstration, and guided exercises that the user tries themselves in their current project. The tone is collaborative — you're working through this together, not lecturing.

## Workshop Flow

### 1. Determine Scope

Check what the user asked for:

- **Full workshop** (no version specified): Present the complete module menu
- **Version-based** (e.g., "everything from 2.1.90"): Fetch the changelog, identify what changed since that version, and only cover modules with relevant updates. Mention which modules are skipped and why.
- **Specific topic** (e.g., "teach me about hooks"): Jump straight to that module

### 2. Gather Source Material

Fetch the relevant documentation. The docs live at `https://code.claude.com/docs/en/`. When you need to fetch multiple pages, do so in parallel.

**Discovery step:** Start by fetching the documentation index at `https://code.claude.com/docs/llms.txt`. Compare the pages listed there against the known module table below. If the index contains pages not covered by any module (and not in the exclusion list), briefly mention them to the user as additional topics available on request. Keep this to a short list — don't dump a giant table.

**Excluded from the workshop:** The Agent SDK (`/agent-sdk/*`) is a separate product for building custom agents programmatically. It's out of scope for this workshop. Also exclude meta pages like `/troubleshooting`, `/setup`, `/legal-and-compliance`, `/data-usage`, and `/zero-data-retention` — these are reference material, not workshop content.

Key pages by module (fetch only what's needed for the current scope):

| Module | Doc Pages |
|--------|-----------|
| Getting Started | `/overview`, `/quickstart`, `/how-claude-code-works`, `/best-practices`, `/common-workflows` |
| CLI & Terminal | `/cli-reference`, `/interactive-mode`, `/keybindings`, `/voice-dictation`, `/statusline`, `/fast-mode`, `/fullscreen`, `/terminal-config` |
| Memory & Configuration | `/memory`, `/settings`, `/claude-directory`, `/env-vars` |
| Skills & Commands | `/skills`, `/commands` |
| Hooks | `/hooks`, `/hooks-guide` |
| MCP & Plugins | `/mcp`, `/plugins`, `/discover-plugins`, `/plugins-reference` |
| Subagents & Teams | `/sub-agents`, `/agent-teams` |
| Desktop & Web | `/desktop`, `/desktop-quickstart`, `/claude-code-on-the-web`, `/web-quickstart`, `/remote-control`, `/ultraplan` |
| Scheduled Tasks | `/scheduled-tasks`, `/desktop-scheduled-tasks`, `/web-scheduled-tasks` |
| Permissions & Security | `/permission-modes`, `/permissions`, `/sandboxing`, `/security` |
| Channels & Events | `/channels`, `/channels-reference` |
| Context & Performance | `/context-window`, `/costs`, `/checkpointing`, `/monitoring-usage` |
| Advanced CLI | `/headless`, `/computer-use` |

**Not workshop modules — reference only:** The following topics are configuration or setup work in external systems, not things to learn interactively. If the user asks about them, point them to the relevant doc pages instead of teaching a module:

- **Cloud providers**: `/amazon-bedrock`, `/google-vertex-ai`, `/microsoft-foundry`, `/authentication`, `/llm-gateway`, `/model-config`, `/third-party-integrations`
- **IDE integration**: `/vs-code`, `/jetbrains` — extensions for VS Code and JetBrains IDEs. Features can't be demoed from a CLI session.
- **CI/CD & integrations**: `/github-actions`, `/gitlab-ci-cd`, `/code-review`, `/slack`, `/chrome`, `/github-enterprise-server` — setup and config in external systems.

For version-based workshops, also fetch the changelog at `/changelog` to identify which features are new since the specified version.

### 3. Present the Module Menu

Show the user a numbered list of available modules with a one-line description of each. Mark modules that contain recent changes (if doing a version-based workshop) so the user knows where the new stuff is.

Example format:

```
Here are the workshop modules available. Pick one to start, or say "next" to go in order.

 1. Getting Started — How Claude Code works, installation, first steps
 2. CLI & Terminal — Commands, flags, keybindings, voice, status line
 3. Memory & Configuration — CLAUDE.md, auto memory, settings, environment
 4. Skills & Commands — Custom skills, slash commands, sharing workflows
 5. Hooks — Automate actions before/after Claude Code events
 6. MCP & Plugins — Connect external tools and data sources
 7. Subagents & Teams — Spawn parallel agents, coordinate work
 ...

You've completed: (none yet)
```

If the user specified a version, only show modules that have relevant changes. Keep the menu concise — one line per module with a short teaser of what's new, not a full changelog. Save the detail for when the user picks a module to explore.

```
Here's what changed since version 2.1.90. Pick a module to explore.

 1. Hooks — New: conditional `if` field, `defer` permission, StopFailure event
 2. CLI & Terminal — New: --bare flag, --console flag, /loop command
 3. MCP & Plugins — New: MCP elicitation support, result size override
 ...

Skipped (no changes): Getting Started, Channels & Events
```

The detail about each change — what it does, how to use it, examples — belongs in the teaching step (step 4), not in the menu. The menu is for orientation, not information delivery.

### 4. Teach Each Module

For each module, follow this pattern:

**a) Concept overview** — Explain what this feature area is and why it matters. Keep it grounded: what problem does it solve? Use 2-4 paragraphs max.

**b) Key features walkthrough** — Go through the important features one at a time. For each:
  - Explain what it does and when you'd use it
  - Show a concrete example (a real command, config snippet, or workflow)
  - If possible, demonstrate it live in the current project (e.g., show the user's current CLAUDE.md, run a CLI flag, check their settings)

**c) Hands-on exercise** — Suggest something the user can try right now in their project. Frame it as an invitation, not an assignment: "Want to try setting up a hook that runs your linter after every file edit?" Wait for the user to respond before moving on.

**d) Questions checkpoint** — After the exercise (or if they skip it), ask: "Any questions about this, or anything you want me to dig deeper into?" Only move on when they say so.

**e) Updated menu** — Show the module list again with completed modules marked, so the user can pick what's next.

### 5. Version-Based Filtering

When the user specifies a version (e.g., "from 2.1.90"):

1. Fetch the changelog from `https://code.claude.com/docs/en/changelog`
2. Parse entries from the specified version onward
3. Group changes by module (map each changelog entry to the most relevant module above)
4. For each module with changes, fetch the relevant doc pages to get the full current documentation — the changelog entry alone won't have enough detail
5. Only present modules that have changes since the specified version
6. Within each module, focus on what's new but provide enough context for the user to understand the feature even if they haven't used the previous version

Also check the "What's New" weekly summaries at `/whats-new/` — these often have more context than the raw changelog entries.

### 6. Wrapping Up

When the user has gone through all modules (or says they're done):

- Summarize what was covered
- Highlight 2-3 features that seem most relevant to their current project (based on what you've seen in their codebase)
- Suggest next steps or things to explore on their own

## Teaching Principles

- **Show, don't just tell.** Whenever possible, demonstrate features using the user's actual project. Reading their CLAUDE.md is more useful than showing a generic example.
- **One thing at a time.** Don't dump all features at once. Teach one concept, let it sink in, then move on.
- **Meet them where they are.** If the user clearly knows the basics, don't belabour them. If they're confused, slow down and explain differently.
- **Be honest about limitations.** If a feature is experimental, has rough edges, or isn't useful for their setup, say so.
- **Practical over theoretical.** Every feature should be connected to a real use case. "Here's what hooks are" is less useful than "hooks can auto-format your code every time Claude edits a file."

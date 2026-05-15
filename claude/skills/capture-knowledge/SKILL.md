---
name: capture-knowledge
description: Capture reusable cross-project technical knowledge into the user's Obsidian vault as a markdown note. Use whenever the user wants to save a learning, pattern, recipe, or how-to that would help future projects — phrases like "save this to my vault", "write this up as a note", "capture this for future reference", "document how X works", "remember this pattern", "add to my knowledge base", or any time after solving something non-obvious in their current repo. Examples: "how to set up an MCP server in a Swift app", "the GraphQL pagination pattern we used here", "how Transit wires up its dependency injection". Use this skill PROACTIVELY whenever the user finishes investigating something they'd plausibly want to reuse on a different project, even if they don't say "save it" explicitly — offer to capture it. Do NOT use for project-specific notes that only make sense inside one repo (those belong in that project's own notes), and do NOT use for daily/journal entries.
---

# Capture project knowledge

This skill writes a markdown note into the user's Obsidian vault capturing reusable, cross-project technical knowledge. The user invokes you from inside one of their software projects; you distill what you've learned (from the code, conversation, or your own investigation) into a note that future-them can find and apply on a different project.

## Resolving the vault path

The vault is named `Main` but lives at a different absolute path on different machines (e.g. `/Users/arjen/Documents/Obsidian/Main` on one Mac, `/Users/arjenschwarz/Documents/Obsidian/Main/Main` on another). Never hardcode the path. The skill keeps a per-machine cache of the path so it doesn't depend on Obsidian (or its CLI) being available at write time.

**Cache location:** `~/.config/capture-knowledge/config.json`, with shape:

```json
{
  "vault_path": "/Users/arjen/Documents/Obsidian/Main"
}
```

### Resolution workflow

On every invocation, run this in order — stop at the first step that yields a path:

1. **Read the cache.** If `~/.config/capture-knowledge/config.json` exists and has `vault_path` pointing at an existing directory, use it. No further checks. This is the hot path.

   ```bash
   VAULT_PATH=$(python3 -c "import json,os,sys; p=os.path.expanduser('~/.config/capture-knowledge/config.json'); print(json.load(open(p))['vault_path']) if os.path.exists(p) else None" 2>/dev/null)
   [ -d "$VAULT_PATH" ] || VAULT_PATH=""
   ```

2. **Try the Obsidian CLI** as a one-shot to *propose* a path to the user: `obsidian vaults verbose | awk -F'\t' '$1=="Main"{print $2}'`. If it returns a directory that exists, ask the user "I found your Main vault at `<path>` — save that as the vault path on this machine?" and on yes, write the cache and continue.

3. **Ask the user** outright: "I don't have your Obsidian Main vault path cached yet on this machine. What's the absolute path?" Validate that the directory exists, then write the cache and continue.

### Writing the cache

When you've resolved a path the user has confirmed (step 2 or 3), persist it:

```bash
mkdir -p ~/.config/capture-knowledge
python3 -c "import json,os; p=os.path.expanduser('~/.config/capture-knowledge/config.json'); json.dump({'vault_path': '$VAULT_PATH'}, open(p, 'w'), indent=2)"
```

Tell the user briefly that you've cached the path so future invocations won't ask. The cache is per-machine and not synced — that's intentional.

If the cache exists but points at a directory that no longer exists (e.g. drive was renamed), treat it as "not cached" and re-run the resolution flow, overwriting the stale entry.

## Where the note goes

Inside the vault, notes from this skill always go into:

```
<VAULT_PATH>/03-Notes/Generated/
```

Create that folder with `mkdir -p` if it doesn't exist. All notes from this skill go here regardless of project or topic — topic categorization is done via tags, not subfolders, so the user isn't locked into a folder hierarchy that might not fit later.

If the user clearly asks for a different location, respect that. Otherwise stick with the default.

## What makes a good note

The note answers a how/why question with enough specifics that future-you in a different codebase can apply it. Lean concrete: real code, real config, the actual gotcha. Avoid generic prose that re-explains what's in any tutorial — the value is the glue, the non-obvious bit, and the integration knowledge.

A typical structure:

1. **H1 title** phrased the way the user would search for it. e.g. `# How to run an MCP server inside a Swift app`. Match the filename.
2. **Summary** (1–2 short paragraphs) framing the problem and what this solves.
3. **The substance** — code blocks, sequenced steps, diagrams. Lift specific examples from the source project, but rewrite identifiers and naming so the example reads as a *pattern*, not as project-specific code. The source project name lives in frontmatter, not buried in every code block.
4. **Gotchas / why it works.** If you only know the recipe and not the deeper why, say so explicitly — that calibrates the reader.
5. **References.** Upstream docs, repo URL or path, related vault notes via wikilinks.

If the topic is too thin for that structure, write fewer sections — don't pad. A 200-line note that's 80% filler is worse than a 40-line note that's all substance.

### Don't tie the body to a single project

Phrasing like "in our Transit codebase, we…" should become "in a Swift app using Foo, you…". The source project is recorded in frontmatter for traceability; the body should generalize. This is the single most important style rule for this skill — the whole reason these notes live outside per-project folders is so they're useful when you're in a *different* project later.

## Frontmatter

Always include this exact frontmatter at the top of every note:

```yaml
---
created: <ISO 8601 with timezone offset>
updated: <same as created on first write>
type: knowledge
tags:
  - generated
  - <topic 1>
  - <topic 2>
source-project: <project name, e.g. "Transit", or omit if not derivable>
source-repo: <repo URL or local path, optional>
---
```

`tags: [generated, ...]` — `generated` is non-negotiable and always first. The companion finder skill (and any Bases/Dataview queries the user writes) will scope by this tag to distinguish skill-produced notes from hand-written ones, and it lets the user audit/edit them later. `generated` is metadata, not a topic, and does not count against the topic-tag budget below.

After `generated`, add **1–4 topic tags** (lowercase) that describe what the note is about. Topics replace folder structure here, so be deliberate — pick the tags someone would actually search for. Examples:

- "How to run an MCP server in a Swift app" → `swift`, `mcp`, `architecture`
- "Paginating GraphQL queries in Go" → `go`, `graphql`, `pagination`
- "Wiring SSE streaming through URLSession" → `swift`, `streaming`, `networking`

Reuse existing topic tags in the vault where possible (search with `obsidian search` or grep — see the CLI reference below) rather than inventing near-duplicates like `golang` when `go` already exists. Tags are case-sensitive and conventionally lowercase, single-word, hyphenated if multi-word (`feature-flags`, not `featureFlags`).

For the timestamp, the vault convention is `YYYY-MM-DDTHH:MM:SS±HH:MM` — note the **colon in the timezone offset**. macOS `date +%FT%T%z` produces `±HHMM` without the colon, which doesn't match. Use Python instead, which gets it right on every platform:

```bash
python3 -c "from datetime import datetime; print(datetime.now().astimezone().isoformat(timespec='seconds'))"
# → 2026-05-07T14:30:00+10:00
```

Seed `updated` with the same value as `created`; the `frontmatter-modified-date` plugin will maintain `updated` after that. Matching the vault's existing format matters because string comparisons in Bases/Dataview filters treat `+1000` and `+10:00` as different values.

`source-project` is best-effort. Derive from the working directory name, the README title, or the git remote. If genuinely unknown, omit the field rather than guess.

## Filename

Short, human-friendly title with spaces — Obsidian convention. e.g. `How to run an MCP server inside a Swift app.md`. Avoid kebab-case or snake_case. Keep it under ~80 chars. The H1 inside the file should match the filename minus `.md`.

Full path: `<VAULT_PATH>/03-Notes/Generated/<title>.md`

### Check for collisions before writing

If a note with the same title already exists in the target folder, do not silently overwrite. Read the existing file, then choose:

- **Extend** — append a new section if the new content is genuinely additive.
- **Supersede** — rename the old note to `<title> (superseded YYYY-MM-DD).md` first, then write the new one.
- **Skip** — if the new content adds nothing, just tell the user the existing note already covers it.

Tell the user which path you took.

## Writing the file

The simplest, most reliable approach is to write directly to the absolute filesystem path with the `Write` tool, using the `VAULT_PATH` you resolved earlier. Obsidian indexes new files automatically when it next sees the folder; no Obsidian instance needs to be running for this to work.

```
Write file_path="${VAULT_PATH}/03-Notes/Generated/<title>.md" content=<full markdown including frontmatter>
```

Note: `Write` doesn't expand shell variables — substitute `${VAULT_PATH}` into the actual string before passing it to the tool.

This is the recommended default. Reach for the Obsidian CLI only when you need it to do something the filesystem write can't (e.g. open the file in a running Obsidian instance, search across the vault, or trigger a template).

### Obsidian CLI (self-contained reference)

Binary at `/usr/local/bin/obsidian`. Paths are relative to the vault root (no leading slash); quote values with spaces; use `\n` for newlines in `content=`. The CLI requires Obsidian to be running with the Shortcut Launcher plugin enabled — if it errors with "no instance found", fall back to direct filesystem write.

Useful invocations:

```bash
# Resolve the vault's absolute path (used as a fallback when the cache is empty)
obsidian vaults verbose

# List existing notes in the target folder (helpful for collision checks)
obsidian files vault=Main folder="03-Notes/Generated"

# Check if a specific file exists (errors if not)
obsidian file vault=Main path="03-Notes/Generated/<title>.md"

# Find existing topic tags used in the vault, to avoid coining duplicates
grep -rh "^  - " "${VAULT_PATH}/03-Notes" 2>/dev/null | sort -u | head -50

# Create a file via Obsidian (alternative to Write — picks up templates, Obsidian must be running)
obsidian create vault=Main \
  path="03-Notes/Generated/<title>.md" \
  content="<text>"

# Open a file in Obsidian after writing it (only if user asked you to)
obsidian open vault=Main \
  path="03-Notes/Generated/<title>.md"
```

The vault is named `Main`. Always pass `vault=Main` explicitly so this works even if the user has multiple vaults registered.

## Linking and Obsidian Flavored Markdown

Conventions that make notes feel native to the vault:

- **Wikilinks** for vault-internal references: `[[Person Name]]`, `[[Company]]`, `[[Other note]]`. Only link to notes that actually exist — don't fabricate. If you're unsure whether a target exists, omit the link.
- **Code fences** with language tags: ` ```swift `, ` ```bash `, ` ```yaml `. Mermaid diagrams use ` ```mermaid `.
- **Callouts** for warnings or asides, used sparingly:
  ```
  > [!warning] Title
  > Body of the callout.
  ```
  Types: `note`, `tip`, `info`, `warning`, `caution`, `example`.
- **Headings** start at H1 (the title). Use H2/H3 for sections; don't skip levels.

Don't add `#tag` lines inline in the body — tags belong in frontmatter only, otherwise the `generated` filter and topic scoping see noise. Don't add a Dataview block unless the note specifically needs one.

## Workflow

1. **Resolve `VAULT_PATH`** via the cache flow above (read `~/.config/capture-knowledge/config.json`, fall back to one-shot CLI detection, fall back to asking). Cache it for the rest of this run.
2. **Confirm the topic** in one sentence ("I'll capture how to wire an MCP server into a SwiftUI app, drawing on what we did in Transit"). If genuinely vague, ask one clarifying question — title or scope. Don't interview the user.
3. **Gather the substance** from conversation context and the current project's code. Read source files when you need real specifics; don't invent code.
4. **Pick the title** the way someone would search for it. Confirm only if non-obvious.
5. **Pick topic tags** — 1–4 lowercase tags. Glance at existing tags in `03-Notes/` first to avoid coining duplicates.
6. **Check for an existing note** with that title and decide extend / supersede / skip.
7. **Write the note** with frontmatter + body following the rules above.
8. **Report back** the absolute path of the file you wrote, in one short sentence. Don't dump the contents.

## Things to avoid

- **Project-specific narrative in the body.** Generalize. Source project goes in frontmatter only.
- **Hardcoded vault paths.** Always resolve at runtime — different machines have the vault in different places.
- **Paraphrasing upstream docs.** Link to them. Capture the integration knowledge, not the API reference.
- **Silent overwrites.** Always handle collisions explicitly.
- **Dropping notes anywhere outside `03-Notes/Generated/`** unless the user explicitly directs.
- **Inline tags in the body.** `generated` and topic tags live in frontmatter, full stop.
- **Inventing tag synonyms** (`golang` vs `go`, `js` vs `javascript`). Reuse what's already in the vault.
- **Padding.** A short, dense note beats a long, thin one.

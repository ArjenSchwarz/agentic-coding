---
name: explain-like
description: >-
  Explain code changes or designs at three expertise levels (beginner, intermediate 5-10 yrs, expert).
  Use for: (1) PR/branch change explanations - understand what changed and why,
  (2) Design document validation - self-review by explaining at multiple levels to catch gaps or logic issues.
  Triggers: "explain this PR", "explain these changes", "validate this design", "explain like I'm a beginner",
  "walk me through this at different levels".
# model: inherit
# allowedTools: Read,Glob,Grep,Bash(git:*)
---

# Explain Like

Explain code changes or design documents at three progressive expertise levels to ensure understanding and catch logical gaps.

## When to Use

1. **PR/Branch Explanations**: After completing work, explain changes to verify clarity
2. **Design Validation**: After writing a design doc, explain it back to catch missing pieces

Both workflows serve knowledge transfer - helping others (or your future self) understand complex changes.

## Workflow

1. Determine the subject:
   - **Branch/PR changes?** → Gather commits and diffs from git
   - **Design document?** → Read the specified design file

2. Generate three explanations (all three, always):
   - **Beginner** (0-2 years): Foundational concepts, analogies, "what" and "why"
   - **Intermediate** (5-10 years): Implementation details, patterns, trade-offs
   - **Expert** (10+ years): Architecture implications, edge cases, future considerations

3. For design validation: After explaining, list any gaps or inconsistencies discovered

4. Optionally save output to file for documentation (see "Saving Output" below)

## Explanation Structure

For each level, follow this format:

```markdown
## Beginner Level

### What Changed / What This Does
[Plain language summary - assume no domain knowledge]

### Why It Matters
[Business or user impact in simple terms]

### Key Concepts
[Define any technical terms used, with analogies where helpful]

---

## Intermediate Level

### Changes Overview
[Technical summary with specific files/components affected]

### Implementation Approach
[Patterns used, architectural decisions, how pieces fit together]

### Trade-offs
[What alternatives existed, why this approach was chosen]

---

## Expert Level

### Technical Deep Dive
[Detailed implementation, edge cases handled, performance considerations]

### Architecture Impact
[How this affects the broader system, coupling, future extensibility]

### Potential Issues
[Edge cases, failure modes, things to monitor]
```

## For Branch/PR Changes

Gather context first:

```bash
# Detect default branch (main, master, etc.)
BASE=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")

# Get commit history
git log --oneline $BASE..HEAD

# Get full diff
git diff $BASE...HEAD

# If PR exists, get PR description
gh pr view --json title,body,commits
```

Focus explanations on:
- What problem is being solved
- How the solution works
- Why this approach over alternatives

## For Design Validation

After generating the three explanations, add a validation section:

```markdown
## Validation Findings

### Gaps Identified
[List any missing requirements, undefined behaviors, or unclear sections]

### Logic Issues
[Contradictions, circular dependencies, impossible states]

### Questions Raised
[Things that became unclear when explaining at different levels]

### Recommendations
[Specific improvements to the design document]
```

The act of explaining at beginner level often reveals assumed knowledge that should be documented. Expert-level explanation reveals edge cases and integration concerns.

## Saving Output

When the user requests saving (or as part of a final review), write the explanation to a file:

- **For design docs**: Save alongside the design in the same specs folder as `explanation.md`
- **For branch/PR changes**: Save to `specs/<feature-name>/explanation.md` if a matching spec exists, otherwise offer to create one

Ask before saving if the user hasn't explicitly requested it.

## Tone Guidelines

- **Beginner**: Patient, uses analogies, avoids jargon or defines it immediately
- **Intermediate**: Professional, assumes familiarity with common patterns
- **Expert**: Concise, focuses on non-obvious implications and edge cases

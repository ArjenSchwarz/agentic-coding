# Decision Log Format

## Format: Enhanced Nygard ADR

Decision logs use the Enhanced Nygard ADR format - based on Michael Nygard's Architecture Decision Record format with additional fields for comprehensive decision tracking.

## Decision Entry Template

```markdown
## Decision {ID}: {Title}

**Date**: YYYY-MM-DD
**Status**: {proposed | accepted | rejected | deprecated | superseded by Decision X}

### Context

{1-3 paragraphs describing the situation, problem, or requirement that motivates
this decision. Explain what issue needs to be addressed and why it matters.}

### Decision

{Clear, concise statement of what was decided. Use declarative language.
Example: "Use standard markdown link format for requirement references."}

### Rationale

{Explanation of why this decision was made. Cover the reasoning, justification,
and key factors that led to this choice. This should make it clear why this
decision makes sense given the context.}

### Alternatives Considered

- **{Alternative 1 name/description}**: {Brief description} - {Why it was rejected}
- **{Alternative 2 name/description}**: {Brief description} - {Why it was rejected}
- {Add more alternatives as needed}

### Consequences

**Positive:**
- {Benefit or improvement 1}
- {Benefit or improvement 2}

**Negative:**
- {Drawback, trade-off, or challenge 1}
- {Drawback, trade-off, or challenge 2}

### Impact

{Optional section describing what parts of the system, codebase, or project
are affected by this decision. Useful for understanding scope of change.}

---
```

## Required Fields

- **Decision ID and Title**: `## Decision {ID}: {Title}` - Sequential number and short title (5-10 words)
- **Date**: `**Date**: YYYY-MM-DD` - ISO 8601 date format
- **Status**: `**Status**: {value}` - One of: proposed, accepted, rejected, deprecated, superseded by Decision X
- **Context**: H3 section - 1-3 paragraphs explaining the situation
- **Decision**: H3 section - Clear statement of what was decided (1-3 sentences, declarative)
- **Rationale**: H3 section - Explanation of why this decision was made

## Highly Recommended Fields

- **Alternatives Considered**: H3 section with bulleted list `- **{Name}**: {Description} - {Rejection reason}`
- **Consequences**: H3 section with `**Positive:**` and `**Negative:**` subsections, each with bulleted lists

## Optional Fields

- **Impact**: H3 section describing affected areas (use for decisions with significant scope)

## Writing Guidelines

1. **Be concise but complete** - Include necessary detail without verbosity
2. **Write for the future** - Assume readers won't have current context
3. **Document the "why" not just the "what"** - Focus on reasoning
4. **Consider alternatives** - Show you evaluated multiple options (at least 2-3)
5. **Be honest about trade-offs** - List both pros and cons

## Quick Example

```markdown
## Decision 5: Use Go's Standard JSON Package

**Date**: 2025-11-14
**Status**: accepted

### Context

The application needs to serialize and deserialize JSON data for the API. We need to choose a JSON library.

### Decision

Use Go's standard `encoding/json` package for JSON operations.

### Rationale

The standard library provides all necessary functionality for our use case. It's well-tested, maintained by the Go team, and adds no external dependencies.

### Alternatives Considered

- **jsoniter**: Faster performance - Rejected because performance is not critical for our use case
- **easyjson**: Code generation approach - Rejected because it adds build complexity without sufficient benefit

### Consequences

**Positive:**
- No external dependencies
- Well-documented and familiar to all Go developers
- Sufficient performance for our needs

**Negative:**
- Slower than some alternatives (not significant for our use case)
- Less flexible than some third-party options

---
```

## File Structure

- **File name**: `decision_log.md`
- **Location**: In the feature's spec directory (e.g., `specs/feature-name/decision_log.md`)
- **File header**: `# Decision Log: {Feature Name}`
- **Separator**: Use `---` between decisions

## Quick Checklist

When adding a decision, ensure:
- [ ] Unique sequential ID
- [ ] Clear, descriptive title
- [ ] Date in YYYY-MM-DD format
- [ ] Valid status value
- [ ] Context explains the situation
- [ ] Decision statement is clear and specific
- [ ] Rationale explains why
- [ ] At least 2 alternatives documented with rejection reasons
- [ ] Both positive and negative consequences listed
- [ ] Horizontal rule (`---`) separates from next decision

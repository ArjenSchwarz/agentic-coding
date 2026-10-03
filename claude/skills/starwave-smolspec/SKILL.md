---
name: starwave:smolspec
description: Small Spec (Smolspec) - Lightweight specification for changes that carry no contested decisions, whatever their size
---

# Small Spec (Smolspec) - Lightweight Specification

Create a lightweight specification for changes that do not require the full spec workflow. This command combines research, planning, and task creation into a streamlined process.

Smolspec is about decision density, not size. A change qualifies when the codebase already settles how it should be done — even if it spans many files. It does not qualify when the work turns on a decision only the user can make, creates something expensive to reverse, or picks between defensible architectures.

## Scope Assessment

Smolspec is the default path. The full spec workflow exists to resolve decisions the model cannot make on its own — it is not a response to size. A large but mechanical change with no contested decisions belongs in a smolspec with a longer task list.

**Initial Research:**
- The model MUST explore the codebase to identify affected areas
- Identify existing patterns that can be leveraged
- Document dependencies and integration points
- Check for related features or ongoing work
- The model MUST check whether an existing smolspec or full spec already covers the requested functionality
- The model MUST capture a concise summary of affected files, dependencies, and unknowns before moving forward

**Escalation Triggers:**

The model MUST recommend the full spec workflow if ANY of the following applies. These are the only escalation criteria. Size — lines of code, file count, number of tasks — is NOT an escalation trigger.

1. **User-owned ambiguity.** After reading the code, more than one materially different user-facing behaviour would satisfy the request, and nothing in the codebase settles which one is wanted. Ambiguity the model can resolve by reading the code is research, not escalation.

2. **Expensive to reverse.** The change creates or alters something other parties depend on: a public API, CLI surface, or wire format; a persisted data schema or a migration; a security or authorization boundary; a cross-repo or cross-team contract. The test is whether it can be undone with a revert, not how large it is.

3. **Contested approach.** Two or more defensible architectures exist, and choosing wrong means redoing the whole change rather than performing a local refactor. Heuristic: if the *central* choice warrants a full ADR entry rather than a Quick Decisions row, it warrants a design document.

A user explicitly asking for a full spec is always sufficient on its own.

**If uncertain, the model SHOULD proceed with smolspec.** This default is safe only because the triggers are re-checked continuously rather than once — see "Continuous Escalation" under Additional Constraints.

**Assessment Questions:**
The model MUST answer these before proceeding:
- Which of the three escalation triggers, if any, does this change fire?
- Can this be implemented incrementally without breaking existing functionality?
- Does the codebase have established patterns for this type of change?
- Is the work reversible with a single revert?

If escalation is needed, the model MUST:
1. Name which trigger fired and what specifically fires it
2. Highlight the complexity factors discovered during research
3. Recommend starting with `/starwave:requirements` skill instead
4. STOP execution of smolspec workflow

## Feature Naming

- The model MUST propose a {feature_name} based on: (1) user's explicit preference, (2) current branch name if not a default branch, (3) derived from the prompt
- The model MUST allow the user to override the proposal
- Feature names should be concise and descriptive (e.g., "add-logging", "fix-validation")
- The model MUST sanitize feature names into filesystem-safe kebab-case slugs and ensure they do not collide with existing specs
- The model MUST wait for user approval of the feature name

## Lightweight Documentation

For changes that are appropriate for smolspec, the model MUST create documentation in two files:

**File Structure:**
- Create `specs/{feature_name}/smolspec.md` for requirements and design
- Create `specs/{feature_name}/tasks.md` for implementation tasks (compatible with next-task skill)
- Create `specs/{feature_name}/decision_log.md` if any decisions need to be documented (for smolspec-sized changes, most decisions belong in the Quick Decisions table rather than full ADR entries)

**Document Formats:**

The smolspec.md file MUST contain these sections:

```markdown
# {Feature Name}

## Overview
Brief description of what this change does and why it's needed (2-4 sentences).

## Requirements
Simple list of what needs to be accomplished using specification language:
- The system MUST {core requirement 1}
- The system SHOULD {recommended approach}
- The system MAY {optional enhancement}

Note: Use MUST for non-negotiable requirements, SHOULD for strong recommendations, MAY for optional features.

## Implementation Approach
Brief description of how this will be implemented:
- Key files to modify (with paths)
- Approach or pattern to use (reference existing similar implementations if available)
- Any important technical considerations
- Dependencies (existing code/libraries this relies on)
- Out of Scope (what will NOT be changed)

## Risks and Assumptions
Brief list of technical risks and key assumptions:
- Risk: {potential problem} | Mitigation: {how to address}
- Assumption: {what we're assuming is true}
- Prerequisite: {what must exist/work before this can be implemented}

## Escalation Note
This change was scoped as a smolspec. If implementation reveals ambiguity only the user can resolve, an irreversible boundary (public API, persisted schema, auth path), or a contested architectural choice, stop and escalate to the full spec workflow rather than deciding it inline.
```

The Escalation Note MUST be included verbatim. It is what carries the escalation rule to the session that implements the tasks, which does not read this skill.

The tasks.md file MUST follow the standard task format to be compatible with the next-task skill:
- Numbered checkbox list with maximum two levels of hierarchy
- May group tasks into phases if helpful for organization
- Task count follows from the work, not from a cap. A mechanical change spanning many files may legitimately need many tasks; a contested change needing few tasks should have escalated instead.
- Each task must reference the smolspec.md file
- Tasks build incrementally on previous steps

**Task Description Guidelines:**
- Tasks MUST describe WHAT outcome is needed, not HOW to implement
- Tasks SHOULD be verifiable with clear success criteria
- Tasks MUST avoid prescriptive implementation details
- Bad example: "Add validateEmail() function to utils.go"
- Good example: "Email validation prevents invalid addresses from being submitted"
- Each task SHOULD include verification steps (testing distributed throughout, not consolidated at end)
- Tasks MUST represent meaningful units of work. Do NOT fragment a single coherent change into separate tasks for setup, implementation, and wiring (e.g., "create file", "add import", "implement function", "connect it up"). Combine trivial substeps into one task.
- Tasks MUST NOT implement or prepare for anything listed in the smolspec's Out of Scope section.

**Documentation Constraints:**
- Keep smolspec.md concise (typically under 100 lines total)
- Requirements MUST use specification language (MUST/SHOULD/MAY)
- Implementation approach MUST reference specific file paths and existing patterns
- Risks and Assumptions section MUST identify at least one risk or assumption
- Tasks MUST be outcome-focused and verifiable
- Testing MUST be distributed across tasks, not consolidated into final task
- All tasks MUST involve writing, modifying, or testing code (no deployment, user acceptance testing, etc.)
- smolspec.md MUST state the settled plan, not the discussion that produced it. No references to earlier drafts, superseded approaches, or critique feedback ("previously", "originally", "revised to", "as the critic noted") — write the current plan as plain fact.
- smolspec.md MUST NOT contain a standalone objection. Where the approach departs from a requirement's implied path, an existing codebase pattern, or a suggestion from critique, the document MUST state what to do instead. The reasoning — alternatives weighed and why they were rejected — goes in `specs/{feature_name}/decision_log.md`, referenced by ID if needed.

## Workflow Process

**1. Research Phase:**
- Conduct initial research to understand the codebase and change scope
- Identify affected files and components
- Check for existing patterns to follow
- Assess complexity and determine if full spec is needed
- Share the research summary (scope, risks, references) with the user before planning

**2. Planning Phase (if not escalated):**
- Propose feature name and get approval
- Create initial smolspec.md with all required sections (Overview, Requirements, Implementation Approach, Risks and Assumptions, Escalation Note)
- Ask clarifying questions if needed (use AskUserQuestion tool)
- Keep documentation minimal but complete
- Ensure smolspec is self-contained (assume fresh AI session will execute without conversation history)

**3. Explanation Validation Phase:**

Before critique, the model MUST validate the smolspec by having it explained back from a clean context.

- The model MUST use the Agent tool with subagent_type="general-purpose" to run the explain-like skill (invoke the Skill tool with skill="explain-like") against `specs/{feature_name}/smolspec.md`
- The subagent MUST be given only the path to smolspec.md and access to the codebase. The model MUST NOT summarize the feature, restate decisions made in this conversation, or otherwise supply context the document does not contain. Anything the subagent cannot account for is a self-containment defect in the document — surfacing those is the point of the exercise.
- All three explanation levels (beginner, intermediate, expert) MUST be produced. The span is the mechanism: the beginner level exposes assumed knowledge, the expert level exposes edge cases and integration concerns.
- The explanations are a validation device, not a deliverable. The model MUST NOT save `explanation.md` for a smolspec.

**Classifying the findings:**

Most findings are edits to smolspec.md. Some are escalation signals. The model MUST classify every item in the Validation Findings section:

| Finding | Action |
|---------|--------|
| Gap in wording, undefined term, missing file path, unclear success criterion | Edit smolspec.md |
| Question only the user can answer about intended behaviour | Escalation signal — trigger 1 |
| Gap in behaviour rather than in wording: an unspecified case the codebase cannot settle | Escalation signal — trigger 1 |
| Recommendation proposing a defensible alternative approach | Escalation signal — trigger 3 |
| Potential issue touching a persisted format, public surface, or auth path | Escalation signal — trigger 2 |

- If any escalation signal is found, the model MUST stop, present the finding to the user, and recommend the full spec workflow. The model MUST NOT quietly absorb an escalation signal as a document edit.
- If every finding is a document edit, the model MUST apply them in place — rewriting affected text rather than appending change notes — and proceed to critique.

**4. Critique Phase:**
- Use the design-critic skill to review the smolspec.md document
- Incorporate the design-critic's feedback and recommendations into the smolspec.md
- Update the document based on valid critiques before presenting to user, rewriting the affected text in place — do not append change notes or leave the superseded wording alongside the new
- Re-check the escalation triggers against the critique: a critic finding that names a defensible alternative architecture or an irreversible boundary is an escalation signal, handled as in Phase 3
- Capture any noteworthy decisions or trade-offs identified during critique inside `specs/{feature_name}/decision_log.md` (Quick Decisions table row unless it is a genuine trade-off worth a full ADR entry)

Explanation validation and critique catch different failures and neither replaces the other. Explanation validation is run by a subagent working only from the document, so it catches omissions and self-containment defects. design-critic is adversarial, so it catches approaches that are wrong on their own terms.

**5. Self-Review Phase:**
Before presenting to user, the model MUST verify:
- [ ] Requirements use specification language (MUST/SHOULD/MAY) and are testable
- [ ] Requirements describe observable behavior, not implementation mechanism (no "MUST use library X", "MUST be implemented as a service")
- [ ] Implementation approach references specific files with paths
- [ ] Implementation approach references existing patterns or similar code
- [ ] At least one risk or assumption is documented with mitigation/validation plan
- [ ] Dependencies and prerequisites are clearly stated
- [ ] Out of scope items are explicitly listed
- [ ] No vague language (e.g., "robust", "user-friendly" without specifics)
- [ ] No hyperbolic or marketing language ("comprehensive", "seamless", "powerful")
- [ ] All sections are complete and self-contained
- [ ] No references to earlier drafts, superseded approaches, or critique feedback — the document reads as the plan, not its revision history
- [ ] Every objection to a requirement, existing pattern, or critique suggestion is paired with the approach to take instead; the reasoning lives in decision_log.md
- [ ] Document is concise (<100 lines) but complete
- [ ] The Escalation Note is present verbatim
- [ ] Explanation validation ran from a clean context, every finding was classified, and no escalation signal was absorbed as a document edit
- [ ] None of the three escalation triggers fires on the smolspec as it now stands
- [ ] Red flags checked: scope creep, wrong technology, missing prerequisites

**6. Review Phase:**
- Present the smolspec document to the user (after explanation validation, design-critic review, incorporation, and self-review)
- Ask "Does this smolspec look good?"
- Make modifications based on user feedback
- Repeat until explicit approval is received

**7. Task Creation:**
- Once smolspec.md is approved, create the tasks.md file
- The model MUST use the rune skill to:
  - Create the task file at specs/{feature_name}/tasks.md with a reference to smolspec.md
  - Add tasks using batch operations, including `blocked_by` dependencies where tasks build on previous steps
- Task structure should follow the standard format compatible with next-task skill
- Let the task count follow the work; group into phases when that aids ordering
- Each task MUST be outcome-focused (WHAT needs to be achieved, not HOW)
- Each task MUST be verifiable with clear success criteria
- Testing MUST be distributed throughout tasks (e.g., Task 2 implements, Task 3 verifies)
- After creating tasks.md, perform self-review:
  - [ ] Tasks describe outcomes, not implementation steps
  - [ ] Each task has verification/success criteria
  - [ ] Testing is distributed, not consolidated at end
  - [ ] All tasks involve code changes (no deployment/UAT tasks)
  - [ ] Tasks build incrementally without gaps
  - [ ] No orphaned or hanging code
  - [ ] No coherent change is fragmented across trivial substeps (setup/implement/wire)
  - [ ] No task implements or prepares for anything listed in the smolspec's Out of Scope section
- Ask "Do these tasks look good?"
- Make modifications if needed and repeat until explicit approval

## Additional Constraints

**Workflow Execution:**
- The model SHOULD complete the entire workflow in a single conversation flow (don't split into separate skills)
- The model MUST NOT implement the feature as part of this workflow - only create the specification
- The model MAY ask targeted questions but should minimize back-and-forth compared to full spec workflow

**Continuous Escalation:**
The escalation triggers in Scope Assessment are not a one-time gate. Because smolspec is the default for uncertain cases, the triggers MUST be re-checked whenever new information arrives: during research, during planning, when classifying explanation-validation findings, when incorporating design-critic feedback, and while implementing the resulting tasks. If a trigger fires after the smolspec has been approved, the model MUST stop, name the trigger that fired, and recommend converting to the full spec workflow rather than deciding the question inline. Growth in size alone is not a reason to escalate.

**Documentation Quality:**
- All documents MUST be self-contained (assume fresh AI session without conversation history)
- The model SHOULD leverage existing patterns and conventions found in the codebase
- The model SHOULD link to relevant files, specs, or commits referenced during research to minimize rework
- The model MUST include specific file paths, not generic references
- The model SHOULD document any assumptions or uncertainties in the Risks and Assumptions section
- If decision_log.md exists for this feature, follow the decisions documented there

**Task Quality:**
- The model MUST ensure all tasks are coding-focused (no deployment, UAT, or non-code tasks)
- Tasks MUST be outcome-focused (describe WHAT, not HOW)
- Testing MUST be distributed throughout task phases
- Each task MUST be verifiable with clear success criteria
- Tasks MUST build incrementally without gaps or orphaned code

**Self-Containment Requirements:**
The smolspec MUST be executable by a fresh AI session with only:
- The smolspec.md document
- The tasks.md document
- Access to the existing codebase
- No conversation history or external context

## Success Criteria

The smolspec workflow is complete when:
- A clear, concise smolspec.md file exists with all required sections:
  - Overview (2-4 sentences)
  - Requirements (using MUST/SHOULD/MAY specification language)
  - Implementation Approach (with specific file paths and existing pattern references)
  - Risks and Assumptions (at least one documented)
  - Escalation Note (verbatim)
- None of the three escalation triggers fires on the approved scope
- Explanation validation has run from a clean context and its findings are resolved
- A tasks.md file exists with:
  - Outcome-focused tasks, however many the work needs
  - Grouped into phases where that aids ordering
  - Distributed testing (not consolidated at end)
  - All tasks are code-focused and verifiable
- User has explicitly approved both the smolspec and tasks
- Tasks have been created in the rune system and are compatible with next-task skill
- All documentation is self-contained and executable by fresh AI session
- Self-review checklists have been completed for both smolspec and tasks
- Documentation is minimal but complete (smolspec typically <100 lines)

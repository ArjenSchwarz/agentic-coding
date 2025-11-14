# Small Spec (Smolspec) - Lightweight Specification for Minor Changes

Create a lightweight specification for small changes that don't warrant the full spec workflow. This command combines research, planning, and task creation into a streamlined process.

## Scope Assessment

**Initial Research:**
- The model MUST first conduct research to understand the scope and complexity of the requested change
- The model SHOULD explore the codebase to identify affected areas
- The model MUST assess whether this is truly a small change or requires full specification workflow

**Escalation Criteria:**
If the change meets ANY of these criteria, the model MUST recommend using the full spec workflow instead:
- Affects multiple subsystems or architectural boundaries
- Requires breaking changes or significant API modifications
- Impacts backward compatibility
- Involves complex business logic or multiple user workflows
- Requires coordination across multiple components
- Has significant security, performance, or reliability implications
- The user explicitly requests a full spec

If escalation is needed, the model MUST:
1. Explain why the full spec workflow is more appropriate
2. Highlight specific complexity factors discovered during research
3. Recommend starting with `/requirements` command instead
4. STOP execution of smolspec workflow

## Feature Naming

- The model MUST propose a {feature_name} based on: (1) user's explicit preference, (2) current branch name if not a default branch, (3) derived from the prompt
- The model MUST allow the user to override the proposal
- Feature names should be concise and descriptive (e.g., "add-logging", "fix-validation")
- The model MUST wait for user approval of the feature name

## Lightweight Documentation

For changes that are appropriate for smolspec, the model MUST create documentation in two files:

**File Structure:**
- Create `specs/{feature_name}/smolspec.md` for requirements and design
- Create `specs/{feature_name}/tasks.md` for implementation tasks (compatible with next-task command)
- Create `specs/{feature_name}/decision_log.md` if any decisions need to be documented

**Document Formats:**

The smolspec.md file MUST contain these sections:

```markdown
# {Feature Name}

## Overview
Brief description of what this change does and why it's needed (2-4 sentences).

## Requirements
Simple list of what needs to be accomplished:
- Requirement 1
- Requirement 2
- Requirement 3

## Implementation Approach
Brief description of how this will be implemented:
- Key files to modify
- Approach or pattern to use
- Any important technical considerations
```

The tasks.md file MUST follow the standard task format to be compatible with the next-task command:
- Numbered checkbox list with maximum two levels of hierarchy
- May optionally group tasks into phases
- Each task must reference the smolspec.md file
- Tasks build incrementally on previous steps

**Documentation Constraints:**
- Keep smolspec.md concise (typically under 80 lines)
- Requirements should be clear but don't need EARS format
- Implementation approach should be brief but specific enough to guide development
- Tasks should be actionable and test-driven where appropriate
- All tasks MUST involve writing, modifying, or testing code (no deployment, user acceptance testing, etc.)

## Workflow Process

**1. Research Phase:**
- Conduct initial research to understand the codebase and change scope
- Identify affected files and components
- Check for existing patterns to follow
- Assess complexity and determine if full spec is needed

**2. Planning Phase (if not escalated):**
- Propose feature name and get approval
- Create initial smolspec.md with Overview, Requirements, and Implementation Approach sections
- Ask clarifying questions if needed (use AskUserQuestion tool)
- Keep documentation minimal but complete
- Use the design-critic agent to review the smolspec.md document
- Incorporate the design-critic's feedback and recommendations into the smolspec.md
- Update the document based on valid critiques before presenting to user

**3. Review Phase:**
- Present the smolspec document to the user (after design-critic review and incorporation)
- Ask "Does this smolspec look good?"
- Make modifications based on user feedback
- Repeat until explicit approval is received

**4. Task Creation:**
- Once smolspec.md is approved, create the tasks.md file
- The model MUST use the rune skill to create tasks in specs/{feature_name}/tasks.md
- Tasks should reference the smolspec.md file in their front matter
- Task structure should follow the standard format compatible with next-task command
- Each task should be actionable and focused on code changes
- After creating tasks.md, ask "Do these tasks look good?"
- Make modifications if needed and repeat until explicit approval

## Additional Constraints

- The model SHOULD complete the entire workflow in a single conversation flow (don't split into separate commands)
- The model MUST NOT implement the feature as part of this workflow - only create the specification
- The model MAY ask targeted questions but should minimize back-and-forth compared to full spec workflow
- The model SHOULD leverage existing patterns and conventions found in the codebase
- The model MUST ensure all tasks are coding-focused (no deployment, UAT, or non-code tasks)
- If decision_log.md exists for this feature, follow the decisions documented there
- The model SHOULD suggest using full spec workflow if the change grows in scope during planning

## Success Criteria

The smolspec workflow is complete when:
- A clear, concise smolspec.md file exists with all required sections
- A tasks.md file exists with actionable, code-focused tasks
- User has explicitly approved both the smolspec and tasks
- Tasks have been created in the rune system and are compatible with next-task command
- All documentation is minimal but sufficient for implementation

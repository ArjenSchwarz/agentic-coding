---
name: starwave:tasks
description: 3. Create Task List
---

### 3. Create Task List

Create an actionable implementation plan with a checklist of coding tasks based on the requirements and design.
The tasks document should be based on the requirement and design documents, so ensure these exists first.

**Constraints:**

**Feature Discovery:**
- The user provides the {feature_name} as part of the prompt, or by way of the current branch which will contain the name of the feature, either in whole or prefixed by specs/
- Verify that the specs/{feature_name} folder exists and has a requirements.md and design.md file
- If the folder does NOT exist, the model SHOULD check the current git branch and see if that matches an existing feature
- The model MUST request the user to provide the {feature_name} using the question "I can't find this feature, can you provide it again? Based on the git branch, I think it might be {found_name}"
- If the requirements.md or design.md file does not exist in the folder, the model MUST inform the user that they need to use the requirements and design skills to create these first
- If a decision_log.md file exists in the specs/{feature_name} folder, the decisions in there MUST be followed

**Task Planning Approach:**
- The model MUST create a 'specs/{feature_name}/tasks.md' file if it doesn't already exist
- Convert the feature design into a series of prompts for a code-generation LLM that will implement each step in a test-driven manner
- Prioritize best practices, incremental progress, and early testing, ensuring no big jumps in complexity at any stage
- Each prompt builds on the previous prompts, and ends with wiring things together
- There should be no hanging or orphaned code that isn't integrated into a previous step
- Focus ONLY on tasks that involve writing, modifying, or testing code

**Task Format Requirements:**
- The model MUST format the implementation plan as a numbered checkbox list with a maximum of two levels of hierarchy:
  - Top-level items (like epics) should be used only when needed
  - Sub-tasks should be numbered with decimal notation (e.g., 1.1, 1.2, 2.1)
  - Each item must be a checkbox
  - Simple structure is preferred
- The model MAY optionally group tasks into phases for additional clarity:
  - Phases are optional organizational aids, not required
  - Common phase examples include: pre-work, implement changes, code cleanup, documentation
  - Phases should improve readability without adding unnecessary complexity
  - Tasks within phases still follow the same numbering and format requirements
- Each task item MUST include:
  - A clear objective as the task description that involves writing, modifying, or testing code
  - Additional information as sub-bullets under the task
  - Specific references to requirements from the requirements document (referencing granular sub-requirements, not just user stories)

**Task Content Requirements:**
- Each task MUST be actionable by a coding agent:
  - Involve writing, modifying, or testing specific code components
  - Specify what files or components need to be created or modified
  - Be concrete enough that a coding agent can execute them without additional clarification
  - Be scoped to specific coding activities (e.g., "Implement X function" rather than "Support X feature")
- Tasks MUST build incrementally on previous steps
- The model MUST prioritize test-driven development where appropriate (tests before implementation, e.g., 1.1 creates unit tests, 1.2 does implementation)
- If the design specifies property-based testing for certain components, the model MUST include explicit tasks for writing property tests before or alongside unit tests for those components
- The plan MUST cover all aspects of the design that can be implemented through code
- All requirements MUST be covered by the implementation tasks
- If gaps are identified during implementation planning, the model MUST mention them and propose relevant changes to the requirements or design

**Task Exclusions:**
The model MUST NOT include the following types of non-coding tasks in the main tasks.md:
- User acceptance testing or user feedback gathering
- Deployment to production or staging environments
- Performance metrics gathering or analysis
- Running the application to test end to end flows (automated tests to test end-to-end flows from a user perspective are allowed)
- User training or documentation creation
- Business process changes or organizational changes
- Marketing or communication activities
- Any task that cannot be completed through writing, modifying, or testing code

**User Prerequisites (Optional):**
If the feature requires manual configuration or setup steps that cannot be performed by the agent, the model MUST create a separate `specs/{feature_name}/prerequisites.md` file.

Prerequisites are tasks that require human intervention outside of code, such as:
- Xcode project configuration (capabilities, entitlements, signing)
- Apple Developer portal setup (App IDs, certificates, provisioning profiles)
- Cloud console configuration (AWS, GCP, Azure resources)
- Third-party service setup (API keys, webhooks, OAuth apps)
- Database provisioning or schema migrations requiring admin access
- Environment variable configuration in deployment platforms
- DNS or domain configuration
- App store or marketplace registration

**Prerequisites Format:**
```markdown
# Prerequisites for {Feature Name}

These tasks must be completed by the user before or during implementation.

## Before Starting
- [ ] {Task that must be done before any coding begins}

## During Implementation
- [ ] {Task needed before a specific coding task, reference which task}

## Before Testing
- [ ] {Task needed before testing can occur}
```

**Prerequisites Constraints:**
- Only create prerequisites.md if there are actual prerequisites identified
- Each prerequisite MUST include clear instructions on what needs to be configured
- Prerequisites SHOULD indicate when they need to be completed (before starting, during implementation, before testing)
- Prerequisites that block specific coding tasks MUST reference which task they block
- The model MUST ask the user to confirm prerequisites are complete before proceeding with dependent tasks during implementation

**Approval Workflow:**
- After updating the tasks document, the model MUST ask the user "Do the tasks look good?"
- The model MUST make modifications to the tasks document if the user requests changes or does not explicitly approve
- The model MUST ask for explicit approval after every iteration of edits to the tasks document
- The model MUST NOT consider the workflow complete until receiving clear approval (such as "yes", "approved", "looks good", etc.)
- The model MUST continue the feedback-revision cycle until explicit approval is received
- The model MUST stop once the task document has been approved

**Workflow Scope:**
This workflow is ONLY for creating design and planning artifacts. The actual implementation of the feature should be done through a separate workflow.
- The model MUST NOT attempt to implement the feature as part of this workflow
- The model MUST clearly communicate to the user that this workflow is complete once the design and planning artifacts are created

**Rune CLI Task Creation:**
The model MUST use the rune skill to create and manage tasks. Invoke the rune skill with instructions to:
- Create the task file at specs/{feature_name}/tasks.md with appropriate title and references (requirements.md, design.md, decision_log.md)
- Add tasks using batch operations with proper structure including:
  - Task titles that are clear and actionable
  - Phase groupings where appropriate
  - Parent-child relationships for subtasks
  - Details as arrays for additional context
  - References as arrays of file paths
  - Requirements as arrays of requirement IDs from requirements.md

The rune skill will handle the proper command syntax and JSON formatting automatically.

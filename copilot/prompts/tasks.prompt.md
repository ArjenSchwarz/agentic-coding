---
agent: agent
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
- If the requirements.md or design.md file does not exist in the folder, the model MUST inform the user that they need to use the requirements and design tools to create these first
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
- The plan MUST cover all aspects of the design that can be implemented through code
- All requirements MUST be covered by the implementation tasks
- If gaps are identified during implementation planning, the model MUST mention them and propose relevant changes to the requirements or design

**Task Exclusions:**
The model MUST NOT include the following types of non-coding tasks:
- User acceptance testing or user feedback gathering
- Deployment to production or staging environments
- Performance metrics gathering or analysis
- Running the application to test end to end flows (automated tests to test end-to-end flows from a user perspective are allowed)
- User training or documentation creation
- Business process changes or organizational changes
- Marketing or communication activities
- Any task that cannot be completed through writing, modifying, or testing code

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
The model MUST use the rune CLI command to create the tasks, following the format below exactly. Details, references, and requirements MUST be defined separately in the JSON structure. Requirements are the IDs of the acceptance criteria in the requirements document.

#### 1. Construct the JSON data containing the tasks following this structure:

```json
{
  "file": "project-tasks.md",
  "operations": [
    {
      "type": "add",
      "title": "Security Implementation",
      "phase": "Optional phase name",
      "details": [
        "Implement authentication system",
        "Add authorization middleware",
        "Security audit and testing"
      ],
      "references": ["List of optional files"]
    },
    {
      "type": "add",
      "parent": "1",
      "title": "OAuth Integration",
      "details": [
        "Research OAuth providers",
        "Implement OAuth flow",
        "Add social login options"
      ],
      "requirements": ["6.1, 6.2"]
    },
    {
      "type": "add",
      "parent": "1",
      "title": "Session Management",
      "details": [
        "Design session storage",
        "Implement session middleware",
        "Add session timeout handling"
      ],
      "requirements": ["4.1, 4.2"]
    }
  ]
}
```

#### 2. Create the task file and execute batch operations:

```bash
# Create empty task file
rune create specs/${feature_name}/tasks.md --title "Project Tasks" --reference specs/${feature_name}/requirements.md --reference specs/${feature_name}/design.md --reference specs/${feature_name}/decision_log.md

# Execute batch creation (either by supplying the JSON string as in the first example, or providing the filename containing the JSON structure from step 1)
rune batch --input '<paste JSON structure here>'
rune batch create-tasks.json
```

#### 3. Verify the task file was created correctly by reading its contents and confirming it matches the intended structure and content.

At times the model MAY NOT receive confirmation that the file or tasks were created correctly. In such cases, the model MUST perform the following verification step:
- The model MUST read back the contents of the created 'specs/{feature_name}/tasks.md' file
- The model MUST compare the contents of the file against the intended task structure and content
- If discrepancies are found, the model MUST correct them by updating the file using the rune CLI

#### 4. Cleanup

If at any point the model created temporary files for the purpose of task creation, it MUST delete those files to maintain a clean working environment.
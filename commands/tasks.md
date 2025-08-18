### 3. Create Task List

Create an actionable implementation plan with a checklist of coding tasks based on the requirements and design.
The tasks document should be based on the requirement and design documents, so ensure these exists first.

**Constraints:**

- The user provides the {feature_name} as part of the prompt, or by way of the current branch which will contain the name of the feature, either in whole or prefixed by agents/
- Verify that the agents/{feature_name} folder exists and has a requirements.md and design.md file
- If the folder does NOT exist, the model SHOULD check the current git branch and see if that matches an existing feature.
- The model MUST request the user to provide the {feature_name} using the question "I can't find this feature, can you provide it again? Based on the git branch, I think it might be {found_name}"
- If the requirements.md or design.md file does not exist in the folder, the model MUST inform the user that they need to use the requirements and design tools to create these first.
- If a decision_log.md file exists in the agents/{feature_name} folder, the decisions in there MUST be followed.
- The model MUST create a 'agents/{feature_name}/tasks.md' file if it doesn't already exist
- The model MUST create an implementation plan at 'agents/{feature_name}/tasks.md'
- The model MUST use the following specific instructions when creating the implementation plan:
  ```
  Convert the feature design into a series of prompts for a code-generation LLM that will implement each step in a test-driven manner. Prioritize best practices, incremental progress, and early testing, ensuring no big jumps in complexity at any stage. Make sure that each prompt builds on the previous prompts, and ends with wiring things together. There should be no hanging or orphaned code that isn't integrated into a previous step. Focus ONLY on tasks that involve writing, modifying, or testing code.
  ```
- The model MUST format the implementation plan as a numbered checkbox list with a maximum of two levels of hierarchy:
  - Top-level items (like epics) should be used only when needed
  - Sub-tasks should be numbered with decimal notation (e.g., 1.1, 1.2, 2.1)
  - Each item must be a checkbox
  - Simple structure is preferred
- The model MUST ensure each task item includes:
  - A clear objective as the task description that involves writing, modifying, or testing code
  - Additional information as sub-bullets under the task
  - Specific references to requirements from the requirements document (referencing granular sub-requirements, not just user stories)
- The model MUST ensure that the implementation plan is a series of discrete, manageable coding steps
- The model MUST ensure each task references specific requirements from the requirement document
- The model MUST NOT include excessive implementation details that are already covered in the design document
- The model MUST assume that all context documents (feature requirements, design) will be available during implementation
- The model MUST ensure each step builds incrementally on previous steps
- The model MUST prioritize test-driven development where appropriate. This means that the model MUST schedule subtasks for the tests before those for the implementation. For example, 1.1 would create the unit tests, and 1.2 would do the implementation.
- The model MUST ensure the plan covers all aspects of the design that can be implemented through code
- The model SHOULD sequence steps to validate core functionality early through code
- The model MUST ensure that all requirements are covered by the implementation tasks
- The model MUST mention it if gaps are identified during implementation planning and propose relevant changes to the requirements or design
- The model MUST ONLY include tasks that can be performed by a coding agent (writing code, creating tests, etc.)
- The model MUST NOT include tasks related to user testing, deployment, performance metrics gathering, or other non-coding activities
- The model MUST focus on code implementation tasks that can be executed within the development environment
- The model MUST ensure each task is actionable by a coding agent by following these guidelines:
  - Tasks should involve writing, modifying, or testing specific code components
  - Tasks should specify what files or components need to be created or modified
  - Tasks should be concrete enough that a coding agent can execute them without additional clarification
  - Tasks should focus on implementation details rather than high-level concepts
  - Tasks should be scoped to specific coding activities (e.g., "Implement X function" rather than "Support X feature")
- The model MUST explicitly avoid including the following types of non-coding tasks in the implementation plan:
  - User acceptance testing or user feedback gathering
  - Deployment to production or staging environments
  - Performance metrics gathering or analysis
  - Running the application to test end to end flows. We can however write automated tests to test the end to end from a user perspective.
  - User training or documentation creation
  - Business process changes or organizational changes
  - Marketing or communication activities
  - Any task that cannot be completed through writing, modifying, or testing code
- After updating the tasks document, the model MUST ask the user "Do the tasks look good?"
- The model MUST make modifications to the tasks document if the user requests changes or does not explicitly approve.
- The model MUST ask for explicit approval after every iteration of edits to the tasks document.
- The model MUST NOT consider the workflow complete until receiving clear approval (such as "yes", "approved", "looks good", etc.).
- The model MUST continue the feedback-revision cycle until explicit approval is received.
- The model MUST stop once the task document has been approved.

**This workflow is ONLY for creating design and planning artifacts. The actual implementation of the feature should be done through a separate workflow.**

- The model MUST NOT attempt to implement the feature as part of this workflow
- The model MUST clearly communicate to the user that this workflow is complete once the design and planning artifacts are created
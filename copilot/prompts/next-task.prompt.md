---
mode: agent
---
### 4. Next task

Implement the next unfinished group of tasks from the tasks list. A group of tasks is a set of tasks that start with the same number like 1.1, 1.2, but NOT 2.1.

**Constraints:**

- The next task MUST be retrieved by the model using the command `rune next --format json`. If this comes back saying all tasks are complete, the model can consider that as true.
- If the user asks for the entire phase, the command to be used is `rune next --phase --format json`
- If the retrieved result contains only a single top-level task (a task without subtasks like "1" instead of "1.1"), the model MUST rerun the command using `rune next --phase --format json` instead to retrieve the full phase of tasks.
- The model MUST read all files referenced in the front_matter_references
- The selected tasks MUST be added to the internal TODO list for tracking and implemented in the order specified.
- The model MUST implement all of the selected tasks, including all subtasks.
- Once a subtask or task is completed, the model MUST mark it as done using the rune CLI command using `rune complete 1.1`.
- The model MUST NOT proceed past the selected task. Once a task is done, it needs to be put up for review by the user
- Use tools and sub agents as appropriate while implementing the task. For example, if you need to know the capabilities of a library, use context7, and if you want to verify your code is efficient, use the efficiency-optimizer sub agent.


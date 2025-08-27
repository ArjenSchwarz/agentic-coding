### 4. Next task

Implement the next unfinished group of tasks from the tasks list. A group of tasks is a set of tasks that start with the same number like 1.1, 1.2, but NOT 2.1.

**Constraints:**

- The user provides the {feature_name} as part of the prompt, or by way of the current branch which will contain the name of the feature, either in whole or prefixed by specs/. When there are multiple features that could match, go for the one that most closely matches the branch name.
- Verify that the specs/{feature_name} folder exists and has a requirements.md, design.md, and tasks.md file
- Optionally a decision_log.md file will exist in the specs/{feature_name} folder. The model MUST adhere to any decisions logged in there. If any decisions block work, the model MUST raise this before continuing.
- If any of these files are missing, or the {feature_name} is unknown, the model MUST NOT continue
- The model MUST read all 3 of these files.
- A task is defined as a main task, consisting of a description, prefixed by a whole digit.
    - `1. Do this thing` is a main task
    - `1.1 Start with this` and `1.2 End with this` are its subtasks.
    - The model MUST execute the main task and all of its subtasks.
    - A task called `1.1` is only part of the task, make sure to include ALL subtasks
- The model MUST find the first main task, or phase of tasks, with incomplete tasks and and mark this as selected.
- The model MUST implement the selected main task and all of its subtasks.
- Once a subtask or task is completed, the model MUST mark it as done in the tasks.md file.
- The model MUST NOT proceed past the selected task. Once a task is done, it needs to be put up for review by the user
- Use tools and sub agents as appropriate while implementing the task. For example, if you need to know the capabilities of a library, use context7, and if you want to verify your code is efficient, use the efficiency-optimizer sub agent.


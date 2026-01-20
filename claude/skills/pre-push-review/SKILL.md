---
name: pre-push-review
description: Review unpushed commits before pushing to remote repository
---

# Pre-Push Code Review

Review unpushed commits to ensure code quality, correctness, and spec adherence before they reach the remote repository.

## Process

1. **Identify Unpushed Commits**: Use git to find commits that exist locally but not on the remote tracking branch. Show the user which commits will be reviewed.

2. **Locate Relevant Specifications**: Check if there's a spec for the feature being worked on:
   - Examine the current branch name for feature indicators
   - Look in the specs directory for matching feature folders
   - Review all documents in the feature folder: requirements, design, tasks, and decision log
   - If no spec exists, proceed with general code quality review

3. **Conduct Critical Review**:

   **Spec Adherence** (if spec exists):
   - Verify implementation matches requirements and design documents
   - Check if all tasks from the tasks document are addressed
   - Identify any divergence from the spec
   - Ensure divergences are documented with clear rationale

   **Code Quality**:
   - Evaluate adherence to project coding standards (check CLAUDE.md and language-specific rules)
   - Assess code clarity, simplicity, and maintainability
   - Identify potential bugs, edge cases, or logic errors
   - Check for proper error handling
   - Verify efficient use of language features

   **Testing**:
   - Verify presence of appropriate unit tests
   - Check test coverage for new/modified code
   - Ensure tests follow project testing standards
   - Validate that tests actually test behavior, not implementation

   **Documentation**:
   - Check for clear code comments where needed
   - Verify public APIs are documented
   - Confirm README or other docs are updated if needed

4. **Run Validation Tools**: Execute linters and validators. Use Makefile commands if available.

5. **Provide Actionable Feedback**: Categorize issues by severity:
   - **Critical**: Must fix before pushing (bugs, security issues, spec violations without documentation)
   - **Important**: Should fix before pushing (code quality, missing tests)
   - **Minor**: Consider fixing (style, minor improvements)
   - **Suggestion**: Optional enhancements

   For each issue, explain what the problem is, why it matters, and how to fix it. Reference specific files and line numbers.

6. **Summary and Recommendation**: Provide a clear verdict:
   - **Ready to push**: No blocking issues found
   - **Needs fixes**: List must-fix items before pushing
   - **Requires discussion**: Architectural concerns that need team input

Push back on poor practices even if the code "works". The goal is to catch issues before they reach the remote repository.

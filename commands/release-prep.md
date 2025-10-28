I want to prepare this project for the next release, which will be {input}. Please do the following:

## Pre-Release Quality Checks

- Run all tests and linting checks
- Check for any TODO or FIXME comments that should be addressed before release
- Verify all dependencies are up to date and check for known security vulnerabilities
- Ensure the build succeeds without warnings

## Version Management

- Update version numbers in all relevant files (package.json, go.mod, VERSION files, etc.)
- Verify version consistency across the project

## Documentation Updates

- Update the changelog to have a summary of the new version. This means you need to condense everything in the unreleased section to only focus on everything that is new or changed since the last release. There should not be any mention of things that have been changed during the unreleased dev-cycle, the changelog should only show the final result for it. The changelog is meant for new users to understand the changes, so while internal changes can be mentioned, they should not be the focus. Ensure that the changelog doesn't get overly verbose, so keep things tight.
- Add the release date to the changelog version header
- Ensure there is proper user documentation for all changes in the changelog
- Update README.md if there are new features or breaking changes that affect usage
- Check that all code examples in documentation are current and working
- Review and update any installation or upgrade instructions

## Release Notes Preparation

- Construct a comprehensive summary that can be used for the release notes
- Highlight breaking changes prominently at the top
- Include upgrade/migration instructions if needed
- Mention contributors if applicable
- Add links to relevant documentation for new features

## Final Checks

- Verify all CI/CD pipelines are passing
- Ensure git tags follow the project's versioning scheme
- Check that the repository is clean (no uncommitted changes that should be included)
- Review open issues and PRs to ensure nothing critical is being left out

## Important Notes

**DO NOT commit, tag, or create releases.** All changes should be left uncommitted for the user to review. The user will handle:
- Committing the release preparation changes
- Creating and pushing git tags
- Publishing the actual release
# Scripts Directory

This directory contains utility scripts that can be invoked by agents to perform specific development tasks.

## Scripts

### commit-diff-summary.sh

**Purpose**: Generates a comprehensive summary of changes between commits, branches, or tags.

**Usage**:
```bash
./commit-diff-summary.sh [OPTIONS]
```

**Options**:
- `-b, --base REF`: Base reference to compare from (default: HEAD~1)
- `-h, --head REF`: Head reference to compare to (default: HEAD)
- `-v, --verbose`: Show detailed file changes and full diff
- `--help`: Display help message

**Prerequisites**:
- Must be run from within a git repository
- Git must be installed and configured

**Behavior**:
- Compares changes between two git references (commits, branches, or tags)
- Shows commit count, authors involved, and file statistics
- Lists all changed files with additions/deletions count
- Displays commit messages between the references
- In verbose mode, shows the complete diff

**Examples**:
```bash
./commit-diff-summary.sh                    # Compare current commit with previous
./commit-diff-summary.sh -b main            # Compare current branch with main
./commit-diff-summary.sh -b v1.0.0 -h v2.0.0  # Compare two tags
./commit-diff-summary.sh -b origin/main -v  # Compare with remote main, verbose output
```

**Output**: Formatted summary including commit count, authors, statistics, file changes, and commit messages.

### copilot-pr-comments.sh

**Purpose**: Fetches and displays GitHub Copilot's review comments and inline comments for the current branch's pull request.

**Usage**:
```bash
./copilot-pr-comments.sh
```

**Prerequisites**:
- Must be run from within a git repository
- Requires GitHub CLI (`gh`) to be installed and authenticated
- Current branch must have an open pull request

**Behavior**:
- Automatically detects the current git branch
- Finds the associated pull request for that branch
- Retrieves both general review comments and inline comments from GitHub Copilot
- Displays formatted output with warnings about potential inaccuracies
- Lists all open PRs if no PR is found for the current branch

**Output**: Formatted GitHub Copilot comments with file locations and line numbers, plus cautionary warnings about review accuracy.

### move_code_section.py

**Purpose**: Moves a specified section of code (by line numbers) from one file to another.

**Usage**:
```bash
python move_code_section.py <source_file> <start_line> <end_line> <dest_file> [--create-if-missing]
```

**Parameters**:
- `source_file`: Path to the file containing the code section to move
- `start_line`: Starting line number (1-based indexing)
- `end_line`: Ending line number (inclusive, 1-based indexing)
- `dest_file`: Path to the destination file
- `--create-if-missing`: Optional flag to create the destination file if it doesn't exist

**Behavior**:
- Extracts the specified line range from the source file
- Removes the extracted section from the source file
- Appends the section to the destination file (or creates a new file with Go package structure)
- When creating new Go files, automatically adds "package output" header and copies relevant imports
- Validates line numbers and file existence before performing operations

**Example**:
```bash
python move_code_section.py src/main.go 15 25 src/utils.go --create-if-missing
```

### test-conversion/ (Go Application)

**Purpose**: Converts Go test files from slice-based table-driven tests to map-based table-driven tests for better test isolation and cleaner syntax.

**Usage**:
```bash
cd test-conversion
go run . <file.go>      # Convert single test file
go run . <directory>    # Convert all _test.go files in directory
```

**What it converts**:
- Transforms slice-based test tables with `name` field to map-based test tables where the test name becomes the map key
- Updates the corresponding `for` loop to use map iteration pattern
- Removes redundant `name` field from test structs

**Benefits**:
- Better test isolation with unique test names as map keys
- Easier debugging with prominent test names
- Follows modern Go testing best practices
- Cleaner, more readable test code structure

**Example transformation**:
From: `tests := []struct { name string; ... }` with `for _, tt := range tests`
To: `tests := map[string]struct { ... }` with `for name, tt := range tests`

## Agent Usage Notes

- Both scripts include error handling and provide informative output messages
- The copilot script requires network access and GitHub authentication
- The move_code_section script is designed with Go project structure in mind but works with any text files
- The test-conversion tool requires Go to be installed
- Always verify the results of these scripts, especially when moving code sections or converting test files
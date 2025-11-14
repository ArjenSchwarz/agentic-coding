# Go Test Fixer Skill

This skill helps fix and improve Go test files according to best practices defined in `language-rules/go.md`.

## Capabilities

This skill can:
1. Convert slice-based table tests to map-based table tests
2. Split large test files into smaller, focused test files
3. Ensure tests follow Go testing best practices

## Tools Available

### Test Conversion Tool
- **Location**: `.claude/scripts/test-conversion/main.go`
- **Purpose**: Converts slice-based table tests to map-based table tests
- **Usage**:
  - Single file: `go run .claude/scripts/test-conversion/main.go <test_file.go>`
  - Directory: `go run .claude/scripts/test-conversion/main.go <directory>`
- **What it does**:
  - Converts `tests := []struct{...}` to `tests := map[string]struct{...}`
  - Removes `name` field from test structs (becomes map key)
  - Updates `for _, tt := range tests` to `for name, tt := range tests`
  - Updates `t.Run(tt.name, ...)` to `t.Run(name, ...)`
  - Creates backup files before modifying

### Code Section Mover
- **Location**: `.claude/scripts/move_code_section.py`
- **Purpose**: Moves code sections between files
- **Usage**: `python .claude/scripts/move_code_section.py <source_file> <start_line> <end_line> <dest_file> [--create-if-missing]`
- **What it does**:
  - Extracts specified lines from source file
  - Appends to destination file (or creates it with proper package/imports)
  - Removes the section from source file
  - Useful for splitting large test files

## Go Testing Rules Reference

Always follow these key principles from `~/.claude/language-rules/go.md`:

### Table-Driven Testing (Rules 6-8)
- **Rule 6**: Prefer map-based tables over slices - Use `map[string]struct` for test cases to ensure unique names and catch interdependencies
- **Rule 7**: Use descriptive test case names - Names should clearly describe what's being tested
- **Rule 8**: Always use `t.Run()` for subtests

### Test Organization (Rules 1-5)
- **Rule 4**: Split large test files by functionality - When tests exceed 500-800 lines, split into files like `handler_auth_test.go`, `handler_validation_test.go`
- **Rule 1**: Keep test files alongside source code
- **Rule 2**: Use internal tests for unit testing (same package)

### Other Key Rules
- **Rule 26**: Mark helpers with `t.Helper()`
- **Rule 27**: Use `t.Cleanup()` over `defer`
- **Rule 28**: Use got/want naming
- **Rule 32**: Use `tc` for test cases in table-driven tests

## Workflow

When fixing Go tests, follow this workflow:

### 1. Assess the Test File
- Check file size (if > 500-800 lines, consider splitting)
- Identify slice-based table tests
- Look for testing best practice violations

### 2. Convert to Map-Based Tests
If the file contains slice-based table tests:
```bash
go run scripts/test-conversion/main.go <test_file.go>
```

### 3. Split Large Test Files
If the file exceeds 500-800 lines:

a. Identify logical groupings (e.g., by function being tested, by test type)
b. Determine split points (line numbers for each section)
c. Create new test files:
```bash
# Example: Move lines 150-300 to a new file
python scripts/move_code_section.py original_test.go 150 300 new_focused_test.go --create-if-missing
```

d. Name new files descriptively (e.g., `handler_auth_test.go`, `handler_validation_test.go`)

### 4. Verify and Format
After modifications:
```bash
# Format the code
go fmt ./...

# Run tests to ensure nothing broke
go test ./...

# Run linters
golangci-lint run
```

### 5. Review Against Rules
Check the modified tests against language rules:
- Map-based table tests with descriptive names
- Proper use of `t.Run()` for subtests
- Test helpers marked with `t.Helper()`
- Resource cleanup using `t.Cleanup()`
- got/want naming convention
- `tc` variable for test cases

## Common Patterns to Fix

### Before (Slice-based):
```go
tests := []struct {
    name string
    input int
    want int
}{
    {name: "positive", input: 5, want: 5},
    {name: "negative", input: -3, want: 3},
}
for _, tt := range tests {
    t.Run(tt.name, func(t *testing.T) {
        got := abs(tt.input)
        if got != tt.want {
            t.Errorf("got %d, want %d", got, tt.want)
        }
    })
}
```

### After (Map-based):
```go
tests := map[string]struct {
    input int
    want int
}{
    "positive": {input: 5, want: 5},
    "negative": {input: -3, want: 3},
}
for name, tc := range tests {
    t.Run(name, func(t *testing.T) {
        got := abs(tc.input)
        if got != tc.want {
            t.Errorf("got %d, want %d", got, tc.want)
        }
    })
}
```

## Notes

- Always create backups before major changes (conversion tool does this automatically)
- Run tests after each modification to catch issues early
- When splitting files, ensure each new file is logically cohesive
- The conversion tool handles the mechanical transformation, but you should verify the test logic remains sound
- Consider parallel testing (`t.Parallel()`) for independent tests after conversion

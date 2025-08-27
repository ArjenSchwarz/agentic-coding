# Test Conversion Tool

This tool converts Go test files from slice-based table-driven tests to map-based table-driven tests.

## What it does

Converts this pattern:
```go
tests := []struct {
    name     string
    input    string
    expected string
}{
    {
        name:     "test case 1",
        input:    "hello",
        expected: "world",
    },
}

for _, tt := range tests {
    t.Run(tt.name, func(t *testing.T) {
        // test code
    })
}
```

To this pattern:
```go
tests := map[string]struct {
    input    string
    expected string
}{
    "test case 1": {
        input:    "hello",
        expected: "world",
    },
}

for name, tt := range tests {
    t.Run(name, func(t *testing.T) {
        // test code
    })
}
```

## Usage

Build and run the tool:
```bash
go build .
./test-conversion <file.go>           # Convert single file
./test-conversion <directory>         # Convert all _test.go files in directory
```

## Benefits of Map-based Tests

1. **Better test isolation**: Each test case has a unique name as the map key
2. **Easier debugging**: Test names are more prominent in the structure
3. **Consistent with Go 2025 best practices**: Modern Go testing patterns
4. **Cleaner syntax**: Removes redundant `name` field from test cases
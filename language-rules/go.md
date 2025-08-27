# Go language rules

## Go development rules

CRITICAL: Follow these rules when writing Go code to avoid outdated patterns that `modernize` would flag:

### Types and Interfaces
- Use `any` instead of `interface{}`
- Use `comparable` for type constraints when appropriate

### String Operations
- Use `strings.CutPrefix(s, prefix)` instead of `if strings.HasPrefix(s, prefix) { s = strings.TrimPrefix(s, prefix) }`
- Use `strings.SplitSeq()` and `strings.FieldsSeq()` in range loops instead of `strings.Split()` and `strings.Fields()`

### Loops and Control Flow
- Use `for range n` instead of `for i := 0; i < n; i++` when index isn't used
- Use `min(a, b)` and `max(a, b)` instead of if/else conditionals

### Slices and Maps
- Use `slices.Contains(slice, element)` instead of manual loops for searching
- Use `slices.Sort(s)` instead of `sort.Slice(s, func(i, j int) bool { return s[i] < s[j] })`
- Use `maps.Copy(dst, src)` instead of manual `for k, v := range src { dst[k] = v }` loops

### Testing
- Use `t.Context()` instead of `context.WithCancel()` in tests

### Formatting
- Use `fmt.Appendf(nil, format, args...)` instead of `[]byte(fmt.Sprintf(format, args...))`


## Go Unit Testing Rules

### Test Organization

  1. Keep test files alongside source code - Place *_test.go files in the
  same directory as the code they test
  2. Use internal tests for unit testing - Write tests in the same package
  to access unexported functions
  3. Use external tests for integration - Add _test suffix to package name
  for integration tests and examples
  4. Split large test files by functionality - When tests exceed 500-800
  lines, split into files like handler_auth_test.go,
  handler_validation_test.go
  5. Use /test directory only for test applications and data - Not for unit
  tests

### Table-Driven Testing

  6. Prefer map-based tables over slices - Use map[string]struct for test
  cases to ensure unique names and catch interdependencies
  7. Use descriptive test case names - Names should clearly describe what's
  being tested and appear in failure output
  8. Always use t.Run() for subtests - Wrap each test case execution with
  t.Run(name, func(t *testing.T) {...})

### Test Coverage

  9. Target 70-80% coverage - This is the practical sweet spot; 85% for
  critical components
  10. Write meaningful tests, not coverage fillers - Avoid assertion-free
  tests written solely for coverage metrics
  11. Use integration test coverage - Leverage go build -cover for measuring
   real-world code execution

### Parallel Testing

  12. Call t.Parallel() first - Always place t.Parallel() as the first
  statement in parallel test functions
  13. Capture loop variables - Always capture range variables before using
  them in parallel subtests
  14. Use testing/synctest for concurrent code - For time-dependent tests,
  use the experimental synctest package when available

### Mocking and Dependencies

  15. Prefer integration tests over heavy mocking - Use real dependencies
  when possible
  16. Use function-based test doubles - Create simple test doubles with
  function fields instead of complex mock frameworks
  17. Use Testcontainers for external dependencies - Prefer real
  databases/services in containers over mocked dependencies

### Test Fixtures

  18. Use testdata directory for fixtures - Store test data files in
  testdata which Go toolchain ignores
  19. Implement golden file testing - Use golden files for validating
  complex output with update flag support
  20. Use functional builder pattern - Create test data with builders that
  have sensible defaults

### Integration Testing

  21. Use environment variables for test separation - Check
  os.Getenv("INTEGRATION") instead of build tags
  22. Skip integration tests by default - Use t.Skip() when INTEGRATION env
  var is not set

### Benchmarking

  23. Use B.Loop() for benchmarks - Prefer the new B.Loop() pattern over for
   i := 0; i < b.N; i++
  24. Always use -benchmem - Include memory profiling in benchmark runs
  25. Use benchstat for analysis - Compare benchmark results statistically

### Test Helpers and Structure

  26. Mark helpers with t.Helper() - Always call t.Helper() in test helper
  functions for accurate error reporting
  27. Use t.Cleanup() over defer - Prefer t.Cleanup() for resource cleanup
  in tests
  28. Use got/want naming - Standardize on got for actual values and want
  for expected values

### Assertions and Comparisons

  29. Use cmp.Diff for complex comparisons - Use
  github.com/google/go-cmp/cmp for detailed difference output
  30. Use Testify for complex assertions - When standard library isn't
  sufficient, use testify (but prefer standard library when possible)

### Test Naming

  31. Follow Go naming conventions - Test functions must start with Test,
  Benchmark, Fuzz, or Example followed by capital letter
  32. Use tc for test cases - In table-driven tests, use tc as the variable
  name for test cases

### Code Quality

  33. Run go fmt after modifications - Always format test code
  34. Run all tests after changes - Execute go test ./... to ensure nothing
  breaks
  35. Validate with linters - Use golangci-lint to catch test issues

### Modern Patterns

  36. Accept interfaces, return structs - Design for testability with
  consumer-defined interfaces
  37. Use dependency injection - Pass dependencies through constructors for
  explicit, testable code
  38. Test behavior, not implementation - Focus on what the code does, not
  how it does it
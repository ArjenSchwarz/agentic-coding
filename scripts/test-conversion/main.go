package main

import (
	"fmt"
	"go/ast"
	"go/parser"
	"go/printer"
	"go/token"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
)

const nameField = "name"

// TestConverter handles the conversion of slice-based table tests to map-based tests
type TestConverter struct {
	fileSet *token.FileSet
}

// NewTestConverter creates a new test converter
func NewTestConverter() *TestConverter {
	return &TestConverter{
		fileSet: token.NewFileSet(),
	}
}

// ConvertFile converts a single Go test file from slice-based to map-based table tests
func (tc *TestConverter) ConvertFile(filename string) error {
	fmt.Printf("Processing file: %s\n", filename)

	// Read the file
	content, err := os.ReadFile(filename)
	if err != nil {
		return fmt.Errorf("failed to read file %s: %w", filename, err)
	}

	// Parse the Go file
	node, err := parser.ParseFile(tc.fileSet, filename, content, parser.ParseComments)
	if err != nil {
		return fmt.Errorf("failed to parse file %s: %w", filename, err)
	}

	// Track if any changes were made
	changed := false

	// Walk through the AST and find table tests
	ast.Inspect(node, func(n ast.Node) bool {
		if x, ok := n.(*ast.FuncDecl); ok {
			if strings.HasPrefix(x.Name.Name, "Test") {
				if tc.convertTableTestInFunction(x) {
					changed = true
				}
			}
		}
		return true
	})

	if !changed {
		fmt.Printf("  No slice-based table tests found in %s\n", filename)
		return nil
	}

	// Write the modified AST back to the file
	backup := filename + ".backup"
	if err := os.Rename(filename, backup); err != nil {
		return fmt.Errorf("failed to create backup: %w", err)
	}

	file, err := os.Create(filename)
	if err != nil {
		// Restore backup if file creation fails
		os.Rename(backup, filename)
		return fmt.Errorf("failed to create output file: %w", err)
	}
	defer file.Close()

	if err := printer.Fprint(file, tc.fileSet, node); err != nil {
		// Restore backup if writing fails
		file.Close()
		os.Remove(filename)
		os.Rename(backup, filename)
		return fmt.Errorf("failed to write AST: %w", err)
	}

	// Remove backup on success
	os.Remove(backup)
	fmt.Printf("  Successfully converted slice-based tests to map-based in %s\n", filename)
	return nil
}

// convertTableTestInFunction processes a test function and converts slice-based table tests
func (tc *TestConverter) convertTableTestInFunction(fn *ast.FuncDecl) bool {
	if fn.Body == nil {
		return false
	}

	changed := false
	for _, stmt := range fn.Body.List {
		if assignStmt, ok := stmt.(*ast.AssignStmt); ok {
			if len(assignStmt.Lhs) == 1 && len(assignStmt.Rhs) == 1 {
				if ident, ok := assignStmt.Lhs[0].(*ast.Ident); ok && ident.Name == "tests" {
					if tc.isSliceBasedTableTest(assignStmt.Rhs[0]) {
						if tc.convertSliceToMap(assignStmt) {
							changed = true
						}
					}
				}
			}
		}
	}
	return changed
}

// isSliceBasedTableTest checks if the assignment is a slice-based table test
func (tc *TestConverter) isSliceBasedTableTest(expr ast.Expr) bool {
	composite, ok := expr.(*ast.CompositeLit)
	if !ok {
		return false
	}

	// Check if it's a slice type with struct elements
	arrayType, ok := composite.Type.(*ast.ArrayType)
	if !ok {
		return false
	}

	// Should be []struct{...}
	_, ok = arrayType.Elt.(*ast.StructType)
	return ok
}

// convertSliceToMap converts a slice-based table test to map-based
func (tc *TestConverter) convertSliceToMap(assignStmt *ast.AssignStmt) bool {
	composite, ok := assignStmt.Rhs[0].(*ast.CompositeLit)
	if !ok {
		return false
	}

	arrayType, ok := composite.Type.(*ast.ArrayType)
	if !ok {
		return false
	}

	structType, ok := arrayType.Elt.(*ast.StructType)
	if !ok {
		return false
	}

	// Extract test cases and convert to map
	testCases := make(map[string]*ast.CompositeLit)
	testNames := []string{}

	for _, elt := range composite.Elts {
		if testStruct, ok := elt.(*ast.CompositeLit); ok {
			name := tc.extractTestName(testStruct)
			if name != "" {
				testCases[name] = testStruct
				testNames = append(testNames, name)
				// Remove the name field from the struct since it becomes the map key
				tc.removeNameField(testStruct)
			}
		}
	}

	if len(testCases) == 0 {
		return false
	}

	// Sort test names for consistent output
	sort.Strings(testNames)

	// Create new map-based structure
	mapType := &ast.MapType{
		Key: &ast.Ident{Name: "string"},
		Value: &ast.StructType{
			Fields: tc.removeNameFromFields(structType.Fields),
		},
	}

	// Create map composite literal
	mapElts := []ast.Expr{}
	for _, name := range testNames {
		keyValue := &ast.KeyValueExpr{
			Key:   &ast.BasicLit{Kind: token.STRING, Value: fmt.Sprintf(`"%s"`, name)},
			Value: testCases[name],
		}
		mapElts = append(mapElts, keyValue)
	}

	newComposite := &ast.CompositeLit{
		Type: mapType,
		Elts: mapElts,
	}

	assignStmt.Rhs[0] = newComposite
	return true
}

// extractTestName extracts the test name from a test case struct
func (tc *TestConverter) extractTestName(composite *ast.CompositeLit) string {
	for _, elt := range composite.Elts {
		if kv, ok := elt.(*ast.KeyValueExpr); ok {
			if ident, ok := kv.Key.(*ast.Ident); ok && ident.Name == nameField {
				if basicLit, ok := kv.Value.(*ast.BasicLit); ok {
					// Remove quotes from string literal
					name := basicLit.Value
					if len(name) >= 2 && name[0] == '"' && name[len(name)-1] == '"' {
						return name[1 : len(name)-1]
					}
				}
			}
		}
	}
	return ""
}

// removeNameField removes the name field from a test case struct
func (tc *TestConverter) removeNameField(composite *ast.CompositeLit) {
	newElts := []ast.Expr{}
	for _, elt := range composite.Elts {
		if kv, ok := elt.(*ast.KeyValueExpr); ok {
			if ident, ok := kv.Key.(*ast.Ident); ok && ident.Name == nameField {
				continue // Skip the name field
			}
		}
		newElts = append(newElts, elt)
	}
	composite.Elts = newElts
}

// removeNameFromFields removes the name field from struct field list
func (tc *TestConverter) removeNameFromFields(fields *ast.FieldList) *ast.FieldList {
	if fields == nil {
		return nil
	}

	newFields := []*ast.Field{}
	for _, field := range fields.List {
		skip := false
		for _, name := range field.Names {
			if name.Name == "name" {
				skip = true
				break
			}
		}
		if !skip {
			newFields = append(newFields, field)
		}
	}

	return &ast.FieldList{List: newFields}
}

// ProcessDirectory processes all Go test files in a directory
func (tc *TestConverter) ProcessDirectory(dir string) error {
	return filepath.Walk(dir, func(path string, info os.FileInfo, err error) error {
		if err != nil {
			return err
		}

		// Only process Go test files
		if !info.IsDir() && strings.HasSuffix(path, "_test.go") {
			if err := tc.ConvertFile(path); err != nil {
				fmt.Printf("Error processing %s: %v\n", path, err)
				return err
			}
		}

		return nil
	})
}

// UpdateForLoopPattern updates the for loop pattern to use range over map
func UpdateForLoopPattern(filename string) error {
	content, err := os.ReadFile(filename)
	if err != nil {
		return err
	}

	// Pattern to match: for _, tt := range tests {
	// Replace with: for name, tt := range tests {
	oldPattern := regexp.MustCompile(`for\s+_,\s+(\w+)\s+:=\s+range\s+tests\s+\{`)
	newContent := oldPattern.ReplaceAllString(string(content), `for name, $1 := range tests {`)

	// Pattern to match: t.Run(tt.name, func(t *testing.T) {
	// Replace with: t.Run(name, func(t *testing.T) {
	namePattern := regexp.MustCompile(`t\.Run\(\s*\w+\.name\s*,`)
	newContent = namePattern.ReplaceAllString(newContent, `t.Run(name,`)

	// Only write if content changed
	if newContent != string(content) {
		return os.WriteFile(filename, []byte(newContent), 0644)
	}

	return nil
}

// Helper function to apply the for loop pattern update
func (tc *TestConverter) updateForLoopInFile(filename string) error {
	return UpdateForLoopPattern(filename)
}

func main() {
	if len(os.Args) < 2 {
		fmt.Println("Usage: go run main.go <directory>")
		fmt.Println("       go run main.go <file.go>")
		os.Exit(1)
	}

	target := os.Args[1]
	converter := NewTestConverter()

	stat, err := os.Stat(target)
	if err != nil {
		fmt.Printf("Error accessing %s: %v\n", target, err)
		os.Exit(1)
	}

	if stat.IsDir() {
		fmt.Printf("Processing directory: %s\n", target)
		if err := converter.ProcessDirectory(target); err != nil {
			fmt.Printf("Error processing directory: %v\n", err)
			os.Exit(1)
		}

		// After converting all files, update for loop patterns
		fmt.Println("Updating for loop patterns...")
		filepath.Walk(target, func(path string, info os.FileInfo, err error) error {
			if err == nil && !info.IsDir() && strings.HasSuffix(path, "_test.go") {
				if err := UpdateForLoopPattern(path); err != nil {
					fmt.Printf("Error updating for loop in %s: %v\n", path, err)
				}
			}
			return nil
		})

	} else {
		fmt.Printf("Processing file: %s\n", target)
		if err := converter.ConvertFile(target); err != nil {
			fmt.Printf("Error processing file: %v\n", err)
			os.Exit(1)
		}

		// Update for loop pattern
		if err := UpdateForLoopPattern(target); err != nil {
			fmt.Printf("Error updating for loop pattern: %v\n", err)
			os.Exit(1)
		}
	}

	fmt.Println("Conversion complete!")
}

package main

import (
	"fmt"
	"strings"
	"testing"
)

// TestExample demonstrates the slice-based table test pattern for conversion testing
func TestExample(t *testing.T) {
	tests := map[string]struct {
		input    string
		expected string
		wantErr  bool
	}{"empty input": {

		input:    "",
		expected: "",
		wantErr:  true,
	}, "special characters": {

		input:    "hello-world",
		expected: "HELLO-WORLD",
		wantErr:  false,
	}, "valid input": {

		input:    "hello",
		expected: "HELLO",
		wantErr:  false,
	}}

	for name, tt := range tests {
		t.Run(name, func(t *testing.T) {
			got, err := processString(tt.input)
			if (err != nil) != tt.wantErr {
				t.Errorf("processString() error = %v, wantErr %v", err, tt.wantErr)
				return
			}
			if got != tt.expected {
				t.Errorf("processString() got = %v, want %v", got, tt.expected)
			}
		})
	}
}

func processString(s string) (string, error) {
	if s == "" {
		return "", fmt.Errorf("empty string")
	}
	return strings.ToUpper(s), nil
}

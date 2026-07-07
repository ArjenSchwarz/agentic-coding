#!/bin/bash
# Initialize Claude Code project settings with standard permissions
# Can be run standalone or via the project-init skill

set -e

CLAUDE_DIR=".claude"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"

# Check for jq
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required but not installed."
    echo "Install with: brew install jq"
    exit 1
fi

# Detect project languages and build permissions array
detect_permissions() {
    local permissions=()

    # Always include git
    permissions+=("Bash(git:*)")

    # Makefile present
    if [[ -f "Makefile" ]] || [[ -f "makefile" ]] || [[ -f "GNUmakefile" ]]; then
        permissions+=("Bash(make:*)")
    fi

    # Go
    if [[ -f "go.mod" ]]; then
        permissions+=("Bash(go:*)")
        permissions+=("Bash(golangci-lint:*)")
        permissions+=("Bash(staticcheck:*)")
        permissions+=("Bash(govulncheck:*)")
    fi

    # Swift
    if [[ -f "Package.swift" ]] || ls *.xcodeproj &>/dev/null 2>&1 || ls *.xcworkspace &>/dev/null 2>&1; then
        permissions+=("Bash(swift:*)")
        permissions+=("Bash(xcodebuild:*)")
        permissions+=("Bash(swiftlint:*)")
        permissions+=("Bash(xcrun:*)")
    fi

    # Node/JavaScript/TypeScript
    if [[ -f "package.json" ]]; then
        permissions+=("Bash(npm:*)")
        permissions+=("Bash(npx:*)")
        permissions+=("Bash(node:*)")
        if [[ -f "yarn.lock" ]]; then
            permissions+=("Bash(yarn:*)")
        fi
        if [[ -f "pnpm-lock.yaml" ]]; then
            permissions+=("Bash(pnpm:*)")
        fi
        if [[ -f "bun.lockb" ]]; then
            permissions+=("Bash(bun:*)")
        fi
    fi

    # Python
    if [[ -f "pyproject.toml" ]] || [[ -f "setup.py" ]] || [[ -f "requirements.txt" ]] || [[ -f "Pipfile" ]]; then
        permissions+=("Bash(python:*)")
        permissions+=("Bash(python3:*)")
        permissions+=("Bash(pip:*)")
        permissions+=("Bash(pip3:*)")
        permissions+=("Bash(uv:*)")
        permissions+=("Bash(pytest:*)")
        permissions+=("Bash(ruff:*)")
        permissions+=("Bash(mypy:*)")
    fi

    # Rust
    if [[ -f "Cargo.toml" ]]; then
        permissions+=("Bash(cargo:*)")
        permissions+=("Bash(rustc:*)")
    fi

    # Ruby
    if [[ -f "Gemfile" ]]; then
        permissions+=("Bash(ruby:*)")
        permissions+=("Bash(bundle:*)")
        permissions+=("Bash(rake:*)")
        permissions+=("Bash(rspec:*)")
    fi

    # Java/Kotlin
    if [[ -f "pom.xml" ]]; then
        permissions+=("Bash(mvn:*)")
        permissions+=("Bash(java:*)")
    fi
    if [[ -f "build.gradle" ]] || [[ -f "build.gradle.kts" ]]; then
        permissions+=("Bash(gradle:*)")
        permissions+=("Bash(./gradlew:*)")
        permissions+=("Bash(java:*)")
    fi

    # Docker
    if [[ -f "Dockerfile" ]] || [[ -f "docker-compose.yml" ]] || [[ -f "docker-compose.yaml" ]]; then
        permissions+=("Bash(docker:*)")
        permissions+=("Bash(docker-compose:*)")
    fi

    # Terraform
    if ls *.tf &>/dev/null 2>&1; then
        permissions+=("Bash(terraform:*)")
        permissions+=("Bash(tofu:*)")
    fi

    # Output as JSON array
    printf '%s\n' "${permissions[@]}" | jq -R . | jq -s .
}

# Create .claude directory if needed
mkdir -p "$CLAUDE_DIR"

# Detect permissions for this project
PERMISSIONS=$(detect_permissions)
echo "Detected permissions based on project files:"
echo "$PERMISSIONS" | jq -r '.[]'

if [[ -f "$SETTINGS_FILE" ]]; then
    # Merge permissions into the existing settings file
    jq --argjson perms "$PERMISSIONS" '
        .permissions //= {} |
        .permissions.allow //= [] |
        .permissions.allow = (.permissions.allow + $perms | unique)
    ' "$SETTINGS_FILE" > "$SETTINGS_FILE.tmp" && mv "$SETTINGS_FILE.tmp" "$SETTINGS_FILE"
    echo "Merged permissions into existing $SETTINGS_FILE"
else
    # Create new settings file with permissions
    jq -n --argjson perms "$PERMISSIONS" '
        {
            permissions: {
                allow: $perms
            }
        }
    ' > "$SETTINGS_FILE"
    echo "Created $SETTINGS_FILE with permissions"
fi

echo ""
echo "Settings file contents:"
cat "$SETTINGS_FILE"

#!/bin/bash
# Initialize Claude Code project settings with standard hooks
# Can be run standalone or via the project-init skill

set -e

CLAUDE_DIR=".claude"
SETTINGS_FILE="$CLAUDE_DIR/settings.json"

# The SessionStart hook to add
NEW_HOOK=$(cat <<'EOF'
{
  "matcher": "",
  "hooks": [
    {
      "type": "command",
      "command": "bash -c 'curl -fsSL https://raw.githubusercontent.com/ArjenSchwarz/agentic-coding/main/scripts/claude-remote.sh | bash'"
    }
  ]
}
EOF
)

# Check for jq
if ! command -v jq &> /dev/null; then
    echo "Error: jq is required but not installed."
    echo "Install with: brew install jq"
    exit 1
fi

# Create .claude directory if needed
mkdir -p "$CLAUDE_DIR"

if [[ -f "$SETTINGS_FILE" ]]; then
    # Check if this exact hook already exists
    EXISTING=$(jq -r '.hooks.SessionStart // [] | .[] | .hooks[]? | .command // empty' "$SETTINGS_FILE" 2>/dev/null || echo "")

    if echo "$EXISTING" | grep -q "claude-remote.sh"; then
        echo "Hook already exists in $SETTINGS_FILE"
        exit 0
    fi

    # Merge the new hook into existing settings
    jq --argjson newHook "$NEW_HOOK" '
        .hooks //= {} |
        .hooks.SessionStart //= [] |
        .hooks.SessionStart += [$newHook]
    ' "$SETTINGS_FILE" > "$SETTINGS_FILE.tmp" && mv "$SETTINGS_FILE.tmp" "$SETTINGS_FILE"

    echo "Added SessionStart hook to existing $SETTINGS_FILE"
else
    # Create new settings file with the hook
    cat > "$SETTINGS_FILE" <<'EOF'
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "",
        "hooks": [
          {
            "type": "command",
            "command": "bash -c 'curl -fsSL https://raw.githubusercontent.com/ArjenSchwarz/agentic-coding/main/scripts/claude-remote.sh | bash'"
          }
        ]
      }
    ]
  }
}
EOF
    echo "Created $SETTINGS_FILE with SessionStart hook"
fi

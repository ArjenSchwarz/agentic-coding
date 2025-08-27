#!/bin/bash

# commit-diff-summary.sh
# Generates a summary of changes between commits or branches

set -e

# Default values
BASE_REF="HEAD~1"
HEAD_REF="HEAD"
VERBOSE=false

# Usage function
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Generates a summary of changes between commits or branches."
    echo ""
    echo "Options:"
    echo "  -b, --base REF     Base reference (default: HEAD~1)"
    echo "  -h, --head REF     Head reference (default: HEAD)"
    echo "  -v, --verbose      Show detailed file changes"
    echo "  --help             Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                           # Compare current commit with previous"
    echo "  $0 -b main                   # Compare current branch with main"
    echo "  $0 -b v1.0.0 -h v2.0.0      # Compare two tags"
    echo "  $0 -b origin/main -v        # Compare with remote main, verbose output"
    exit 0
}

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -b|--base)
            BASE_REF="$2"
            shift 2
            ;;
        -h|--head)
            HEAD_REF="$2"
            shift 2
            ;;
        -v|--verbose)
            VERBOSE=true
            shift
            ;;
        --help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "Error: Not in a git repository"
    exit 1
fi

# Verify references exist
if ! git rev-parse --verify "$BASE_REF" >/dev/null 2>&1; then
    echo "Error: Base reference '$BASE_REF' not found"
    exit 1
fi

if ! git rev-parse --verify "$HEAD_REF" >/dev/null 2>&1; then
    echo "Error: Head reference '$HEAD_REF' not found"
    exit 1
fi

# Get commit SHAs for display
BASE_SHA=$(git rev-parse --short "$BASE_REF")
HEAD_SHA=$(git rev-parse --short "$HEAD_REF")

echo "========================================="
echo "Commit Diff Summary"
echo "========================================="
echo ""
echo "Comparing: $BASE_REF ($BASE_SHA) → $HEAD_REF ($HEAD_SHA)"
echo ""

# Show commit count
COMMIT_COUNT=$(git rev-list --count "$BASE_REF".."$HEAD_REF")
echo "Commits: $COMMIT_COUNT"
echo ""

# Show authors involved
echo "Authors:"
git log --format='  - %an <%ae>' "$BASE_REF".."$HEAD_REF" | sort -u
echo ""

# Show statistics
echo "Statistics:"
git diff --shortstat "$BASE_REF".."$HEAD_REF"
echo ""

# Show file changes summary
echo "Files changed:"
git diff --numstat "$BASE_REF".."$HEAD_REF" | awk '{
    added += $1
    deleted += $2
    files++
    printf "  %-50s +%-5d -%-5d\n", $3, $1, $2
} END {
    if (files > 0) {
        print ""
        printf "Total: %d files, +%d additions, -%d deletions\n", files, added, deleted
    }
}'
echo ""

# Show commit messages
if [ "$COMMIT_COUNT" -gt 0 ]; then
    echo "Commit messages:"
    git log --format='  %h %s' "$BASE_REF".."$HEAD_REF"
    echo ""
fi

# Verbose mode: show actual diff
if [ "$VERBOSE" = true ]; then
    echo "========================================="
    echo "Detailed Changes:"
    echo "========================================="
    git diff "$BASE_REF".."$HEAD_REF"
fi
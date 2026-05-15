#!/bin/bash

# Read JSON input
input=$(cat)

# Extract values
cwd=$(echo "$input" | jq -r '.workspace.current_dir')
model=$(echo "$input" | jq -r '.model.display_name')
effort=$(jq -r '.effortLevel // empty' /Users/arjen/.claude/settings.json 2>/dev/null)

# Get git branch and dirty status if in a git repo
git_branch=""
git_dirty=""
if git -C "$cwd" rev-parse --git-dir > /dev/null 2>&1; then
    git_branch=$(git -C "$cwd" -c core.useBuiltinFSMonitor=false branch --show-current 2>/dev/null || echo "")
    # Check if repo is dirty (has uncommitted changes)
    if [ -n "$(git -C "$cwd" status --porcelain 2>/dev/null)" ]; then
        git_dirty="*"
    fi
fi

# Get basename of directory (like \W)
dir_name=$(basename "$cwd")

# Calculate context window percentage if available
context_info=""
usage=$(echo "$input" | jq '.context_window.current_usage')
if [ "$usage" != "null" ]; then
    current=$(echo "$usage" | jq '.input_tokens + .cache_creation_input_tokens + .cache_read_input_tokens')
    size=$(echo "$input" | jq '.context_window.context_window_size')
    if [ "$current" -gt 0 ] && [ "$size" -gt 0 ]; then
        pct=$((current * 100 / size))
        # Color based on usage: green <50%, orange 50-89%, red 90%+
        if [ "$pct" -ge 90 ]; then
            context_color="\033[31m"  # Red
        elif [ "$pct" -ge 50 ]; then
            context_color="\033[33m"  # Orange/Yellow
        else
            context_color="\033[32m"  # Green
        fi
        context_info=" ${context_color}[${pct}%]\033[0m"
    fi
fi

# Get rate limit info if available
rate_info=""
five_pct=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')
week_pct=$(echo "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty')
if [ -n "$five_pct" ] || [ -n "$week_pct" ]; then
    rate_parts=""
    if [ -n "$five_pct" ]; then
        five_int=$(printf "%.0f" "$five_pct")
        if [ "$five_int" -ge 90 ]; then
            rate_color="\033[31m"  # Red
        elif [ "$five_int" -ge 70 ]; then
            rate_color="\033[33m"  # Orange/Yellow
        else
            rate_color="\033[32m"  # Green
        fi
        five_resets=$(echo "$input" | jq -r '.rate_limits.five_hour.resets_at // empty')
        five_reset_str=""
        if [ -n "$five_resets" ]; then
            five_reset_str="(r@$(date -r "$five_resets" +%H:%M))"
        fi
        rate_parts="${rate_color}5h:${five_int}%${five_reset_str}\033[0m"
    fi
    if [ -n "$week_pct" ]; then
        week_int=$(printf "%.0f" "$week_pct")
        if [ "$week_int" -ge 90 ]; then
            wrate_color="\033[31m"
        elif [ "$week_int" -ge 70 ]; then
            wrate_color="\033[33m"
        else
            wrate_color="\033[32m"
        fi
        if [ -n "$rate_parts" ]; then
            rate_parts="${rate_parts} ${wrate_color}7d:${week_int}%\033[0m"
        else
            rate_parts="${wrate_color}7d:${week_int}%\033[0m"
        fi
    fi
    rate_info=" ${rate_parts}"
fi

# Output: Line 1 = directory, model, percentage | Line 2 = branch
# Magenta for directory (matches SPACESHIP_DIR_COLOR)
# Build model display with optional effort level
model_display="$model"
if [ -n "$effort" ]; then
    model_display="$model ($effort)"
fi

printf "\033[35m%s\033[0m %s%b%b\n\033[36m%s\033[31m%s\033[0m" "$dir_name" "$model_display" "$context_info" "$rate_info" "$git_branch" "$git_dirty"

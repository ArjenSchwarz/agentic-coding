#!/bin/bash

function copilot-comments() {
  local -r current_branch="$(git branch --show-current 2>/dev/null)" || {
    printf "Error: Not in a git repository or no current branch\n" >&2
    return 1
  }

  local base_branch pr_num general_reviews inline_comments all_prs

  # Use printf instead of echo for better portability and consistency
  base_branch="$(gh repo view --json defaultBranch --jq '.defaultBranch.name' 2>/dev/null)" || base_branch="main"
  pr_num="$(gh pr list --head "${current_branch}" --base "${base_branch}" --json number --jq '.[0].number' 2>/dev/null)" || pr_num=""

  if [[ -z "${pr_num}" || "${pr_num}" == "null" ]]; then
    printf "No open PR found for current branch %s\n" "${current_branch}"

    if all_prs="$(gh pr list --base "${base_branch}" --json number,title,headRefName --jq '.[] | "PR #\(.number): \(.title) (branch: \(.headRefName))"' 2>/dev/null)" && [[ -n "${all_prs}" ]]; then
      printf "All open PRs to %s:\n%s\n" "${base_branch}" "${all_prs}"
    fi
    return 1
  fi

  # Helper function to reduce code duplication
  _fetch_copilot_data() {
    local -r endpoint="$1"
    local -r jq_filter="$2"
    gh api "repos/:owner/:repo/pulls/${pr_num}/${endpoint}" 2>/dev/null | jq -r "${jq_filter}" 2>/dev/null || true
  }

  general_reviews="$(_fetch_copilot_data "reviews" '.[] | select(.user.login == "Copilot") | .body')"
  inline_comments="$(_fetch_copilot_data "comments" '.[] | select(.user.login == "Copilot") | "\(.path) (line \(.line))\n\(.body)\n" + ("=" * 50) + "\n"')"

  if [[ -n "${general_reviews}" || -n "${inline_comments}" ]]; then
    printf "I submitted the changes to Github Copilot to review, keep in mind that Github Copilot doesn't use a very strong AI model so it may not be accurate.\n"

    printf "🤖 GitHub Copilot comments on PR #%s:\n" "${pr_num}"

    if [[ -n "${general_reviews}" ]]; then
      printf "## Copilot review comments\n"
      printf "%s\n" "${general_reviews}\n------\n"
    fi

    if [[ -n "${inline_comments}" ]]; then
      printf "\n## Copilot inline comments\n"
      printf "%s\n" "${inline_comments}"
    fi

    printf "⚠️ Be mindful that GitHub Copilot's comments may be inaccurate. Ignore any invalid or out of context comments. Please review them carefully before applying any changes. Discuss recommendations with me if the path forward is unclear.\n"
  fi
}

copilot-comments
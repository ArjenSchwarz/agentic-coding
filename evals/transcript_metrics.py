#!/usr/bin/env python3
"""Outcome metrics mined from Claude Code session transcripts.

Reads main-session .jsonl files under ~/.claude/projects/*/ (subagent
transcripts under <sessionId>/subagents/ are excluded so numbers stay
comparable) and computes friction/trust metrics for a time window.

Usage:
    python3 transcript_metrics.py [--days 30] [--projects-dir ~/.claude/projects]

Outputs a JSON object on stdout. Interpretation of each metric is in
evals/README.md.
"""

import argparse
import json
import re
import sys
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Synthetic user-message prefixes that are not human-typed text.
SYNTHETIC_PREFIXES = (
    "<command-message>",
    "<command-name>",
    "<local-command",
    "Base directory for this skill",
    "Caveat:",
    "[Request interrupted",
    "This session is being continued from a previous conversation",
)

CORRECTION_RE = re.compile(
    r"^\s*(no[,.\s]|stop\b|wait\b|don'?t\b|do not\b|wrong\b|that'?s not\b|not what\b|undo\b|revert\b)"
    r"|(\bI said\b|\bI asked\b|\bI told you\b)",
    re.IGNORECASE,
)

APPROVAL_RE = re.compile(
    r"\b(yes|yep|go ahead|approved?|proceed|push|merge|commit|do it|ship( it)?|make it so|lgtm|looks good)\b",
    re.IGNORECASE,
)

# Skill invocations that carry standing approval for commit/push/merge actions.
APPROVING_SKILLS_RE = re.compile(
    r"<command-message>(pr-pilot|blitz-merge|bug-blitz|pr-review-fixer|commit|make-it-so|next-task|release-prep)"
)

DENIAL_SENTINELS = {
    "classifier": "denied by the Claude Code auto mode classifier",
    "user_reject": "The user doesn't want to proceed with this tool use",
    "hook_block": "PreToolUse:Bash hook error",
}

GATE_COMMANDS = {
    "git_push": re.compile(r"\bgit\b[^\n|&;]*\bpush\b"),
    "gh_pr_create": re.compile(r"\bgh pr create\b"),
    "gh_pr_merge": re.compile(r"\bgh pr merge\b"),
    "git_commit": re.compile(r"\bgit\b[^\n|&;]*\bcommit\b"),
}

# Test/build output piped through tail/head/grep masks the exit code, letting
# an agent manufacture a green signal (incident: `make test-quick 2>&1 | tail -30`
# returned 0 over ~2930 failing tests).
MASKED_TEST_RE = re.compile(
    r"(make\s+\S*(test|build)\S*|xcodebuild|swift\s+test)[^\n]*\|\s*(tail|head|grep)\b"
)


def parse_ts(entry):
    ts = entry.get("timestamp")
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def text_of(content):
    """Human-readable text of a message content field, or None if it is not plain text."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        if any(isinstance(b, dict) and b.get("type") == "tool_result" for b in content):
            return None
        parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
        return "\n".join(parts) if parts else None
    return None


def tool_result_texts(content):
    """All string fragments inside tool_result blocks of a user entry."""
    out = []
    if not isinstance(content, list):
        return out
    for block in content:
        if not (isinstance(block, dict) and block.get("type") == "tool_result"):
            continue
        inner = block.get("content")
        if isinstance(inner, str):
            out.append((inner, block.get("is_error", False)))
        elif isinstance(inner, list):
            for part in inner:
                if isinstance(part, dict) and part.get("type") == "text":
                    out.append((part.get("text", ""), block.get("is_error", False)))
    return out


def is_human_text(entry, text, first_human):
    if entry.get("isSidechain") or entry.get("isMeta"):
        return False
    if text is None:
        return False
    if first_human:
        return False  # the initial prompt is not a correction candidate
    return not text.startswith(SYNTHETIC_PREFIXES)


def scan_session(path, cutoff):
    """Compute per-session counters; returns None if session has no activity in window."""
    c = Counter()
    bash_commands = []
    approval_seen = False
    saw_human = False
    in_window = False
    last_assistant_text = None
    last_event_interrupt = False

    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            ts = parse_ts(entry)
            if ts is not None and ts >= cutoff:
                in_window = True

            etype = entry.get("type")
            if etype == "user":
                msg = entry.get("message", {})
                content = msg.get("content")
                # tool results
                results = tool_result_texts(content)
                for text, is_err in results:
                    c["tool_results"] += 1
                    if is_err:
                        c["tool_errors"] += 1
                    for key, sentinel in DENIAL_SENTINELS.items():
                        if sentinel in text:
                            c[f"denial_{key}"] += 1
                    if "[Request interrupted by user for tool use]" in text:
                        c["denial_interrupt_tool"] += 1
                        last_event_interrupt = True
                if results:
                    continue
                # human / synthetic text
                text = text_of(content)
                if text is not None and text.startswith("[Request interrupted"):
                    c["interruptions"] += 1
                    last_event_interrupt = True
                    continue
                if is_human_text(entry, text, first_human=not saw_human):
                    c["human_messages"] += 1
                    if CORRECTION_RE.search(text):
                        c["corrections"] += 1
                    if APPROVAL_RE.search(text):
                        approval_seen = True
                    last_event_interrupt = False
                elif text is not None and APPROVING_SKILLS_RE.search(text):
                    approval_seen = True
                if text is not None and not saw_human and not text.startswith(SYNTHETIC_PREFIXES):
                    saw_human = True

            elif etype == "assistant":
                msg = entry.get("message", {})
                for block in msg.get("content") or []:
                    if not isinstance(block, dict):
                        continue
                    if block.get("type") == "text" and block.get("text", "").strip():
                        last_assistant_text = block["text"]
                        last_event_interrupt = False
                    if block.get("type") == "tool_use" and block.get("name") == "Bash":
                        cmd = (block.get("input") or {}).get("command", "")
                        bash_commands.append(cmd)
                        if MASKED_TEST_RE.search(cmd) and "pipefail" not in cmd:
                            c["masked_test_pipes"] += 1
                        for key, rx in GATE_COMMANDS.items():
                            if rx.search(cmd):
                                c[f"gate_{key}"] += 1
                                if approval_seen:
                                    c[f"gate_{key}_approved"] += 1

    if not in_window:
        return None

    # retry loops: same normalized Bash command 3+ times in one session
    norm = Counter(" ".join(cmd.split()) for cmd in bash_commands if cmd)
    c["retry_loops"] += sum(1 for _, n in norm.items() if n >= 3)

    c["sessions"] = 1
    if last_assistant_text is None:
        c["sessions_no_final_text"] += 1
    elif last_assistant_text.rstrip().endswith("?"):
        c["sessions_ending_question"] += 1
    if last_event_interrupt:
        c["sessions_ending_interrupted"] += 1
    return c


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--projects-dir", default=str(Path.home() / ".claude" / "projects"))
    args = ap.parse_args()

    cutoff = datetime.now(timezone.utc) - timedelta(days=args.days)
    projects = Path(args.projects_dir).expanduser()
    total = Counter()

    for path in sorted(projects.glob("*/*.jsonl")):
        # mtime pre-filter: skip sessions untouched since before the window
        if datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc) < cutoff:
            continue
        session = scan_session(path, cutoff)
        if session:
            total += session

    def rate(num, den):
        return round(total[num] / total[den], 4) if total[den] else None

    out = {
        "window_days": args.days,
        "computed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "sessions": total["sessions"],
        "tool_results": total["tool_results"],
        "tool_errors": total["tool_errors"],
        "tool_error_rate": rate("tool_errors", "tool_results"),
        "human_messages": total["human_messages"],
        "corrections": total["corrections"],
        "correction_rate": rate("corrections", "human_messages"),
        "interruptions": total["interruptions"],
        "denials": {
            "classifier": total["denial_classifier"],
            "user_reject": total["denial_user_reject"],
            "interrupt_tool": total["denial_interrupt_tool"],
            "hook_block": total["denial_hook_block"],
        },
        "gate_actions": {
            key: {"count": total[f"gate_{key}"], "approved": total[f"gate_{key}_approved"]}
            for key in GATE_COMMANDS
        },
        "retry_loops": total["retry_loops"],
        "masked_test_pipes": total["masked_test_pipes"],
        "sessions_ending_question": total["sessions_ending_question"],
        "sessions_ending_interrupted": total["sessions_ending_interrupted"],
        "sessions_no_final_text": total["sessions_no_final_text"],
    }
    json.dump(out, sys.stdout, indent=2)
    print()


if __name__ == "__main__":
    main()

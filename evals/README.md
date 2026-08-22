# Harness Evals

Regression checks for the harness itself: the skills, rules, hooks, and
pipelines in this repo. The suite exists to catch the harness getting worse
before you feel it.

## What "better" means

Merged-PR counts, closed tickets, tracked hours (Horizon), and tokens saved
are all activity metrics: every one of them goes UP when the harness ships a
regression, because the rework comes back as fresh throughput. None of them
is used here.

"Better" for this harness is measured on three axes:

1. **Rework — does shipped work stay shipped?** Reverts, same-ticket
   re-fixes, and the share of merges that are fixes to recent merges. The
   harness's whole pipeline (spec → review loop → squash-merge) exists to
   make this number zero; it is the closest thing to ground truth.
2. **Friction — how much human attention per unit of work?** Interruptions,
   corrections, retry loops, tool errors. This user drives gated pipelines
   and rarely types free text, so mid-run interrupts are the strongest
   redirect signal, not "no, that's wrong" messages.
3. **Trust — can you believe what the harness reports?** Merges without a
   review actually landing, pushes without a prior approval signal,
   test/build output piped through `tail`/`grep` (which manufactures green
   exit codes), and the guardrail hook actually blocking what it claims to
   block. Most past incidents live on this axis: the harness *said* done,
   green, or reviewed when it wasn't.

A fourth tier guards the guards: deterministic lint over the harness's own
text and wiring, because the one blocking hook once shipped with the wrong
exit code and protected nothing for three days.

## Running

```
make evals            # lint + metrics, compared against baseline.json
make evals-lint       # deterministic checks only (~seconds)
make evals-baseline   # accept current values as the new baseline
```

`evals/run.py` exits non-zero on any lint FAIL or metric regression.
Suggested cadence: `evals-lint` after touching hooks/skills; full `evals`
weekly and after changing any pipeline skill. Every run appends to
`history.jsonl` (gitignored) so trends survive baseline updates.

## The checks

### Deterministic lint (`harness_lint.py`)

| Check | Protects | What it does |
|---|---|---|
| `hook_behavior` | trust | Feeds 20 real payloads through `no-push-main.py` as a subprocess and asserts block/allow + exit code 2. Every case is a past incident or closed-hole shape (compound commands, `git -C`, worktree rebase false positive, wrong-exit-code, `+refspec`, `--mirror`). Complements the unit tests in `claude/hooks/`, which monkeypatch branch detection; this check exercises the real stdin/exit-code path the harness uses. |
| `hook_compile` | trust | All hook scripts must compile. |
| `hook_unit_tests` | trust | Runs `claude/hooks/test_*.py` and fails if any test file fails. |
| `invariants` | trust | `harness_invariants.json`: text patterns pinning incident countermeasures into skills (iteration caps, review sentinel, CLEAN taxonomy). If a pattern disappears, a past incident re-opens. |
| `invariant_gaps` | trust | Known-missing countermeasures, reported as warnings until fixed (then move the entry to `required`). |
| `installed_sync` | trust | `~/.claude` symlinks live and non-dangling; `no-push-main` registered in `settings.json`; registered hook files exist. Skips in CI. |
| `config_drift` | trust | Uncommitted changes to synced config = rules running in production that aren't in git. Warn only. |
| `pipe_exit_codes` | trust | Project Makefiles piping xcodebuild through xcbeautify must set pipefail (incident: `make test-quick` returned 0 over ~2,930 failures). |

### Outcome metrics (`transcript_metrics.py`, 30-day window)

Mined from `~/.claude/projects/*/*.jsonl` (main sessions only; subagent
transcripts excluded so rates stay comparable).

| Metric | Axis | Alarm rule |
|---|---|---|
| `tool_error_rate` | friction | > 1.5× baseline and > baseline + 1pt |
| `interruptions_per_session` | friction | > 2× baseline |
| `retry_loops_per_session` | friction | > 2× baseline |
| `masked_test_pipes_per_session` | trust | > 2× baseline. Test/build commands piped through `tail`/`head`/`grep` without pipefail — the invocation style that hides failures. |
| `unapproved_push_share` | trust | warn if > baseline + 15pt. Heuristic: approval inferred from prior user text or an approving skill invocation. |
| `classifier_denials_per_session` | friction | warn only (environmental) |
| `corrections`, `hook_blocks` | — | informational |

### Shipped outcomes (`git_metrics.py`, 90-day window, prism/flux/orbit)

| Metric | Axis | Alarm rule |
|---|---|---|
| `reverts` | rework | any increase over baseline |
| `refix_tickets` | rework | any increase. Same T-id fixed twice within 7 days, both Fix-titled. |
| `unreviewed_merged_share` | trust | > 1.5× baseline. Merged PRs with no review comment (needs `gh`; sampled 15/repo). |
| `fix_titled_share`, `commits_per_pr`, `multi_round_reviews` | — | informational trend. Fix-share is context-dependent (orbit is ~97% fix PRs by design). |

## Known limitations

- **Approval detection is heuristic.** "Any earlier approval-ish message or
  approving skill invocation" is generous; a rising share is a signal to read
  transcripts, not a verdict.
- **Review detection is format-coupled.** It matches `**Verdict`,
  `## Code Review`, and the `claude-local-review` sentinel. If the review
  comment format changes again, update the pattern in `git_metrics.py` or
  every merge looks unreviewed.
- **Regressions get new ticket IDs** (bug-blitz files fresh tickets), so
  `refix_tickets` undercounts. `fix_titled_share` and the revert count are
  the backstops; watch the fix-tail after any large merge.
- **Absolute rules need baseline refresh.** `reverts`/`refix_tickets` compare
  against the baseline window; re-run `make evals-baseline` after
  investigating any alarm, or old events mask new ones as they age out.
- **The suite can't see judgment quality.** Premature "abandon" calls,
  design-iteration waste, and review depth aren't mechanically measurable
  here. The review loop's self-grading structure (fixer assigns severities,
  resolves reviewer threads, declares CLEAN) is a design property — the
  metrics only catch its *outcomes* (rework, unreviewed merges).

## Growing the suite

One check per new incident, in this order of preference: outcome metric
(did the bad thing ship?) → transcript detector (did the bad behaviour
happen?) → text invariant in `harness_invariants.json` (is the
countermeasure still present?). If a gap gets fixed, move its entry from
`gaps` to `required` so the fix can't silently regress.

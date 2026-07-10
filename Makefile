.PHONY: help evals evals-lint evals-baseline

help: ## Show available targets
	@grep -E '^[a-zA-Z_-]+:.*## ' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*## "}; {printf "%-16s %s\n", $$1, $$2}'

evals: ## Run harness lint + outcome metrics, compare against baseline
	python3 evals/run.py

evals-lint: ## Fast deterministic harness checks only (no metrics)
	python3 evals/run.py --lint-only

evals-baseline: ## Accept current metric values as the new baseline
	python3 evals/run.py --update-baseline

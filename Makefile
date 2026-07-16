SKILLS_DIR := dot_claude/skills

.PHONY: help test

help: ## List targets
	@grep -hE '^[a-z][a-z-]*:.*##' $(MAKEFILE_LIST) | \
		sort | awk -F':.*## ' '{printf "  %-12s %s\n", $$1, $$2}'

test: ## Run every skill's Python test suite (stdlib unittest, no deps)
	@found=0; \
	for t in $$(find $(SKILLS_DIR) -name '*test_*.py' | sort); do \
		found=1; echo "==> $$t"; \
		python3 "$$t" || exit 1; \
	done; \
	if [ $$found -eq 0 ]; then echo "no skill tests found under $(SKILLS_DIR)"; fi

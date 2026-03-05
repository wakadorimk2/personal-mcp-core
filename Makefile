.PHONY: guide-sync guide-check issue-dag-list

REPO ?= wakadorimk2/personal-mcp-core
LIMIT ?= 200
OUT ?= /tmp/issue-dag
ISSUES_JSON ?= /tmp/issues.json
WITH_TITLE ?=

guide-sync:
	cp AI_GUIDE.md src/personal_mcp/AI_GUIDE.md

guide-check:
	diff AI_GUIDE.md src/personal_mcp/AI_GUIDE.md || (echo "AI_GUIDE out of sync" && exit 1)

issue-dag-list:
	gh issue list --repo "$(REPO)" --limit "$(LIMIT)" --json number,title,body > "$(ISSUES_JSON)"
	python scripts/issue_dag.py "$(ISSUES_JSON)" --list $(if $(WITH_TITLE),--list-with-title,) --out "$(OUT)"

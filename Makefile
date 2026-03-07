.PHONY: guide-sync guide-check issue-dag-list run log today summary smoke

REPO ?= wakadorimk2/personal-mcp-core
LIMIT ?= 200
OUT ?= /tmp/issue-dag
ISSUES_JSON ?= /tmp/issues.json
WITH_TITLE ?=
PYTHON ?= python
DATA_DIR ?=
PORT ?= 8080
DATE ?= $(shell date -u +%F)
TEXT ?=
DOMAIN ?= worklog

DATA_DIR_ARG = $(if $(strip $(DATA_DIR)),--data-dir "$(DATA_DIR)",)

guide-sync:
	cp AI_GUIDE.md src/personal_mcp/AI_GUIDE.md

guide-check:
	diff AI_GUIDE.md src/personal_mcp/AI_GUIDE.md || (echo "AI_GUIDE out of sync" && exit 1)

issue-dag-list:
	gh issue list --repo "$(REPO)" --limit "$(LIMIT)" --json number,title,body > "$(ISSUES_JSON)"
	python scripts/issue_dag.py "$(ISSUES_JSON)" --list $(if $(WITH_TITLE),--list-with-title,) --out "$(OUT)"

run:
	$(PYTHON) -m personal_mcp.server web-serve --port "$(PORT)" $(DATA_DIR_ARG)

log:
	@test -n "$(strip $(TEXT))" || (echo 'error: TEXT is required. usage: make log TEXT="..." [DOMAIN=worklog] [DATA_DIR=/path]'; exit 1)
	$(PYTHON) -m personal_mcp.server event-add "$(TEXT)" --domain "$(DOMAIN)" $(DATA_DIR_ARG)

today:
	$(PYTHON) -m personal_mcp.server event-today $(DATA_DIR_ARG)

summary:
	$(PYTHON) -m personal_mcp.server summary-generate --date "$(DATE)" $(DATA_DIR_ARG)

smoke:
	@echo "smoke: DATA_DIR=$(if $(strip $(DATA_DIR)),$(DATA_DIR),(resolver default)) DATE=$(DATE)"
	$(MAKE) log TEXT="smoke check $(DATE)" DOMAIN=worklog DATA_DIR="$(DATA_DIR)"
	$(MAKE) today DATA_DIR="$(DATA_DIR)"
	$(MAKE) summary DATE="$(DATE)" DATA_DIR="$(DATA_DIR)"

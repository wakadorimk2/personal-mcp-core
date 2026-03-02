guide-sync:
	cp AI_GUIDE.md src/personal_mcp/AI_GUIDE.md

guide-check:
	diff AI_GUIDE.md src/personal_mcp/AI_GUIDE.md || (echo "AI_GUIDE out of sync" && exit 1)
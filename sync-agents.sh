#!/bin/bash
# Fetches AGENTS.md from the central phils-agents repo.
# Run manually anytime, or let git hooks handle it.

AGENTS_REPO="eusef/phils-agents"
BRANCH="main"
VERBOSE="${1:-}"

TOKEN="$(gh auth token 2>/dev/null)"
if [ -z "$TOKEN" ]; then
  [ "$VERBOSE" = "-v" ] && echo "⚠ gh auth token not available - skipping AGENTS.md sync"
  exit 0
fi

HTTP_CODE=$(curl -sH "Authorization: token $TOKEN" \
  -w "%{http_code}" \
  "https://raw.githubusercontent.com/$AGENTS_REPO/$BRANCH/AGENTS.md" \
  -o AGENTS.md.tmp)

if [ "$HTTP_CODE" = "200" ]; then
  mv AGENTS.md.tmp AGENTS.md
  [ "$VERBOSE" = "-v" ] && echo "✓ AGENTS.md synced from $AGENTS_REPO@$BRANCH"
else
  rm -f AGENTS.md.tmp
  [ "$VERBOSE" = "-v" ] && echo "⚠ AGENTS.md sync failed (HTTP $HTTP_CODE) - keeping existing copy"
fi

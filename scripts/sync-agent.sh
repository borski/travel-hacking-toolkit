#!/usr/bin/env bash
# Sync CLAUDE.md (source of truth) to agents/travel-hacker.md (plugin agent file).
#
# Why: Claude Code plugin agents must be real files with frontmatter at the top.
# Symlinks and @file includes are NOT honored. CLAUDE.md already has the
# frontmatter, so we just copy it.
#
# Run this any time CLAUDE.md changes. Pre-commit hook also enforces it.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE="$REPO_ROOT/CLAUDE.md"
TARGET="$REPO_ROOT/agents/travel-hacker.md"

if [ ! -f "$SOURCE" ]; then
  echo "ERROR: $SOURCE not found." >&2
  exit 1
fi

# Verify CLAUDE.md has the required frontmatter
if ! head -1 "$SOURCE" | grep -q '^---$'; then
  echo "ERROR: $SOURCE must start with YAML frontmatter (---)." >&2
  echo "First line is: $(head -1 "$SOURCE")" >&2
  exit 1
fi

mkdir -p "$(dirname "$TARGET")"
cp "$SOURCE" "$TARGET"

echo "Synced: $SOURCE -> $TARGET"

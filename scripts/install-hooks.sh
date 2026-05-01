#!/usr/bin/env bash
# Install the project's git hooks into .git/hooks/.
#
# Hooks are stored in scripts/hooks/ (version-controlled) and copied into
# .git/hooks/ (not version-controlled) where git looks for them.
#
# Run this once after cloning. setup.sh runs it automatically.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
HOOKS_SRC="$REPO_ROOT/scripts/hooks"
HOOKS_DST="$REPO_ROOT/.git/hooks"

if [ ! -d "$REPO_ROOT/.git" ]; then
  echo "Not a git repo. Skipping hook install."
  exit 0
fi

if [ ! -d "$HOOKS_SRC" ]; then
  echo "No hooks directory at $HOOKS_SRC. Nothing to install."
  exit 0
fi

mkdir -p "$HOOKS_DST"

for hook in "$HOOKS_SRC"/*; do
  [ -f "$hook" ] || continue
  name=$(basename "$hook")
  dst="$HOOKS_DST/$name"

  # Don't clobber an existing hook unless it was installed by us.
  # We tag our hooks with a sentinel comment in the file body.
  SENTINEL="# travel-hacker-managed-hook"
  if [ -f "$dst" ] && ! grep -q "$SENTINEL" "$dst" 2>/dev/null; then
    echo "Skipped: .git/hooks/$name already exists and was not installed by this script."
    echo "         To replace it, delete $dst then re-run this script."
    echo "         To chain hooks, see https://pre-commit.com or similar."
    continue
  fi

  # Stamp the sentinel into the hook so future runs recognize ours
  {
    head -1 "$hook"
    echo "$SENTINEL"
    tail -n +2 "$hook"
  } > "$dst"
  chmod +x "$dst"
  echo "Installed: .git/hooks/$name"
done

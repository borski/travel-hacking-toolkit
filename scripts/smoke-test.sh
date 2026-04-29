#!/usr/bin/env bash
#
# Smoke test the toolkit across all three supported AI coding tools.
# Run this after any change to skills, CLAUDE.md, or MCP config.
#
# What it checks:
#   1. setup.sh and setup.ps1 syntax parse cleanly
#   2. Every skill has valid frontmatter (name + description)
#   3. CLAUDE.md is under the 40k threshold that triggers Claude Code's warning
#   4. Each agent (codex, claude, opencode) starts cleanly from the toolkit
#   5. Each agent picks reasonable skills for a real travel question
#
# Usage:
#   bash scripts/smoke-test.sh              # run all checks
#   bash scripts/smoke-test.sh --quick      # skip the slower agent invocations
#   bash scripts/smoke-test.sh --agents     # only run agent invocations
#
# Requires: codex, claude, opencode CLIs on PATH (any subset is OK; missing
# tools are reported but do not fail the script).

set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

QUICK=0
AGENTS_ONLY=0
for arg in "$@"; do
  case "$arg" in
    --quick) QUICK=1 ;;
    --agents) AGENTS_ONLY=1 ;;
  esac
done

PASS=0
FAIL=0

ok()   { echo "  [ok] $*"; PASS=$((PASS+1)); }
fail() { echo "  [X] $*";  FAIL=$((FAIL+1)); }
skip() { echo "  [-] $*"; }

# --- Static checks ---

if [ "$AGENTS_ONLY" -eq 0 ]; then
  echo ""
  echo "=== Static checks ==="

  # 1. setup.sh syntax
  if bash -n scripts/setup.sh 2>/dev/null; then
    ok "scripts/setup.sh syntax"
  else
    fail "scripts/setup.sh syntax error"
  fi

  # 2. setup.ps1 structure (we don't have pwsh here, but we can sanity-check braces and here-strings)
  if python3 - <<'PY' 2>/dev/null
import sys
with open('scripts/setup.ps1') as f:
    c = f.read()
opens, closes = c.count('{'), c.count('}')
hs_o, hs_c = c.count("@'"), c.count("'@")
if opens != closes:
    sys.exit(f'brace mismatch ({opens} vs {closes})')
if hs_o != hs_c:
    sys.exit(f'here-string mismatch ({hs_o} vs {hs_c})')
PY
  then
    ok "scripts/setup.ps1 structure"
  else
    fail "scripts/setup.ps1 structure"
  fi

  # 3. Skill frontmatter
  bad_skills=0
  for f in skills/*/SKILL.md; do
    name=$(awk '/^---/{c++; next} c==1 && /^name:/{print; exit}' "$f")
    desc=$(awk '/^---/{c++; next} c==1 && /^description:/{print; exit}' "$f")
    if [ -z "$name" ] || [ -z "$desc" ]; then
      echo "      missing fields in $f"
      bad_skills=$((bad_skills+1))
    fi
  done
  total_skills=$(ls -d skills/*/ | wc -l | xargs)
  if [ "$bad_skills" -eq 0 ]; then
    ok "all $total_skills skills have name + description"
  else
    fail "$bad_skills skills missing required frontmatter"
  fi

  # 4. CLAUDE.md size (Claude Code warns above 40,000 chars)
  size=$(wc -c < CLAUDE.md | xargs)
  if [ "$size" -lt 40000 ]; then
    ok "CLAUDE.md size ($size chars, under 40k threshold)"
  else
    fail "CLAUDE.md size ($size chars, exceeds 40k - will warn in Claude Code)"
  fi

  # 5. Docker images exist on ghcr (manifest inspect needs no pull)
  if command -v docker >/dev/null 2>&1; then
    bad_images=0
    for image in patchright-docker sw-fares aa-miles-check chase-travel amex-travel ticketsatwork; do
      if ! docker manifest inspect "ghcr.io/borski/$image:latest" >/dev/null 2>&1; then
        echo "      missing manifest: ghcr.io/borski/$image:latest"
        bad_images=$((bad_images+1))
      fi
    done
    if [ "$bad_images" -eq 0 ]; then
      ok "all 6 Docker images exist on ghcr.io"
    else
      fail "$bad_images Docker images missing on ghcr.io"
    fi
  else
    skip "docker not installed (skipping image manifest check)"
  fi

  # 6. Data file freshness
  if bash scripts/check-data-freshness.sh >/tmp/freshness.out 2>&1; then
    ok "all data files within their declared TTL"
  else
    fail "stale data files (run: python3 scripts/refresh-hotel-data.py for hotels)"
    grep -E "STALE|MISSING_META|BAD_DATE" /tmp/freshness.out | sed 's/^/      /'
  fi
fi

# --- Agent invocations ---

if [ "$QUICK" -eq 1 ]; then
  echo ""
  echo "=== Agent invocations skipped (--quick) ==="
else
  echo ""
  echo "=== Agent invocations ==="

  # Use double quotes inside the prompt strings to avoid shell-quoting issues with apostrophes.
  STARTUP_PROMPT='Reply with exactly: "OK". Then list any warnings or errors from skill loading. Do not search anything else.'
  TRAVEL_PROMPT='I am flexible on dates and want to fly SFO to Tokyo in business class around mid-August 2026. What should I do? Do not actually search anything yet. Just tell me which 3 skills you would load first to plan this and why. Be concise.'

  test_agent() {
    local name="$1"
    shift
    local -a cmd=("$@")
    if ! command -v "$name" >/dev/null 2>&1; then
      skip "$name: not installed (skipping)"
      return
    fi

    # Startup test (pass prompt as a single argument to avoid shell-quoting bugs)
    local startup_out
    startup_out=$(timeout 60 "${cmd[@]}" "$STARTUP_PROMPT" 2>&1 || true)
    if echo "$startup_out" | grep -qi "OK"; then
      ok "$name: startup clean"
    else
      fail "$name: startup did not return OK"
      echo "      ---output---"
      echo "$startup_out" | tail -10 | sed 's/^/      /'
    fi

    # Skill discovery test
    # Required skills: lessons-learned (must be loaded before any award search)
    #                  flight-search-strategy (canonical search workflow)
    # Plus at least one date-flexibility skill (award-calendar) since the prompt mentions flexibility.
    local travel_out
    travel_out=$(timeout 120 "${cmd[@]}" "$TRAVEL_PROMPT" 2>&1 || true)

    local missing_required=()
    for required in lessons-learned flight-search-strategy; do
      if ! echo "$travel_out" | grep -q "$required"; then
        missing_required+=("$required")
      fi
    done

    local found_optional=0
    for skill in award-calendar award-sweet-spots awardwallet seats-aero points-valuations partner-awards; do
      if echo "$travel_out" | grep -q "$skill"; then
        found_optional=$((found_optional+1))
      fi
    done

    if [ "${#missing_required[@]}" -eq 0 ] && [ "$found_optional" -ge 1 ]; then
      ok "$name: skill discovery (loaded lessons-learned + flight-search-strategy + $found_optional supporting skills)"
    elif [ "${#missing_required[@]}" -gt 0 ]; then
      fail "$name: missing required skill(s): ${missing_required[*]}"
      echo "      ---output---"
      echo "$travel_out" | tail -15 | sed 's/^/      /'
    else
      fail "$name: no supporting skills loaded"
      echo "      ---output---"
      echo "$travel_out" | tail -15 | sed 's/^/      /'
    fi
  }

  test_agent codex    codex exec
  test_agent claude   claude --strict-mcp-config --mcp-config .mcp.json -p
  test_agent opencode opencode run
fi

echo ""
echo "=== Summary ==="
echo "  Passed: $PASS"
echo "  Failed: $FAIL"

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
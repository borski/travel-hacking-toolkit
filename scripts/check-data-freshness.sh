#!/usr/bin/env bash
#
# Check freshness of every data/*.json file against its declared TTL.
# Each file should have:
#   ._meta.last_updated   (YYYY-MM-DD)
#   ._meta.staleness_days (integer; default 90 if missing)
#
# Exit codes:
#   0 - all files within TTL
#   1 - one or more files stale, OR a file missing _meta.last_updated
#
# Usage:
#   bash scripts/check-data-freshness.sh           # report stale files
#   bash scripts/check-data-freshness.sh --json    # machine-readable output

set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_DIR"

JSON_OUTPUT=0
for arg in "$@"; do
  case "$arg" in
    --json) JSON_OUTPUT=1 ;;
  esac
done

# Default TTL when a file does not declare one
DEFAULT_TTL=90

today_epoch=$(date +%s)
results=()
fail=0

for f in data/*.json; do
  last=$(jq -r '._meta.last_updated // empty' "$f" 2>/dev/null)
  ttl=$(jq -r '._meta.staleness_days // empty' "$f" 2>/dev/null)
  ttl="${ttl:-$DEFAULT_TTL}"

  if [ -z "$last" ]; then
    results+=("$f|missing|0|$ttl|MISSING_META")
    fail=1
    continue
  fi

  # macOS date vs GNU date both accept YYYY-MM-DD via different flags
  if last_epoch=$(date -j -f "%Y-%m-%d" "$last" "+%s" 2>/dev/null); then :
  elif last_epoch=$(date -d "$last" "+%s" 2>/dev/null); then :
  else
    results+=("$f|invalid|0|$ttl|BAD_DATE")
    fail=1
    continue
  fi

  age_days=$(( (today_epoch - last_epoch) / 86400 ))
  if [ "$age_days" -gt "$ttl" ]; then
    results+=("$f|$last|$age_days|$ttl|STALE")
    fail=1
  else
    results+=("$f|$last|$age_days|$ttl|FRESH")
  fi
done

if [ "$JSON_OUTPUT" -eq 1 ]; then
  printf '['
  first=1
  for r in "${results[@]}"; do
    IFS='|' read -r file last age ttl status <<<"$r"
    [ $first -eq 0 ] && printf ','
    first=0
    printf '{"file":"%s","last_updated":"%s","age_days":%s,"ttl_days":%s,"status":"%s"}' \
      "$file" "$last" "$age" "$ttl" "$status"
  done
  printf ']\n'
else
  printf "%-44s %-12s %4s %4s %-7s\n" "FILE" "LAST" "AGE" "TTL" "STATUS"
  printf "%-44s %-12s %4s %4s %-7s\n" "----" "----" "---" "---" "------"
  for r in "${results[@]}"; do
    IFS='|' read -r file last age ttl status <<<"$r"
    printf "%-44s %-12s %4s %4s %-7s\n" "$file" "$last" "$age" "$ttl" "$status"
  done
fi

exit $fail
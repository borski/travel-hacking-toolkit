#!/usr/bin/env bash
# Travel Hacker key setup. Prompts you locally for API keys, validates them,
# and writes exports to your shell rc with a backup. Never echoes values.
#
# Usage:
#   bash setup-keys.sh
#
# Or download and run in one shot:
#   bash <(curl -fsSL https://raw.githubusercontent.com/borski/travel-hacking-toolkit/main/scripts/setup-keys.sh)
#
# Supports zsh, bash, fish. PowerShell + cmd users: see scripts/setup-keys.ps1.

set -eu

# --- Detect shell and rc file ---

USER_SHELL="${SHELL##*/}"
case "$USER_SHELL" in
  zsh)  RCFILE="$HOME/.zshrc"   ; SYNTAX="bash" ;;
  bash)
    if [ "$(uname)" = "Darwin" ]; then
      RCFILE="$HOME/.bash_profile"
    else
      RCFILE="$HOME/.bashrc"
    fi
    SYNTAX="bash"
    ;;
  fish) RCFILE="$HOME/.config/fish/config.fish" ; SYNTAX="fish" ;;
  *)
    echo "Unknown shell: $USER_SHELL"
    echo "Supported: zsh, bash, fish."
    echo "For PowerShell or cmd, use scripts/setup-keys.ps1 instead."
    exit 1
    ;;
esac

echo "Travel Hacker key setup"
echo "  Shell:  $USER_SHELL"
echo "  RC:     $RCFILE"
echo ""
echo "I will prompt you for API keys (input is hidden, never echoed)."
echo "Anything you skip stays unset. All keys are optional."
echo ""

# --- Helpers ---

KEYS_ADDED=0
KEYS_SKIPPED=0
NEW_LINES=""

# Make sure rc dir exists for fish
mkdir -p "$(dirname "$RCFILE")"
touch "$RCFILE"

# Idempotency check (per-shell-syntax)
already_set() {
  local key="$1"
  case "$SYNTAX" in
    bash) grep -qE "^[[:space:]]*export[[:space:]]+${key}=" "$RCFILE" ;;
    fish) grep -qE "^[[:space:]]*set[[:space:]]+(-gx|-x)[[:space:]]+${key}[[:space:]]" "$RCFILE" ;;
  esac
}

# Build the export line for the appropriate shell
build_line() {
  local key="$1" value="$2"
  case "$SYNTAX" in
    bash) printf "export %s=%s\n" "$key" "'$value'" ;;
    fish) printf "set -gx %s %s\n" "$key" "'$value'" ;;
  esac
}

prompt_key() {
  local key="$1" desc="$2" url="$3" min_len="${4:-10}"

  if already_set "$key"; then
    echo "[exists] $key (already in $RCFILE, skipping)"
    KEYS_SKIPPED=$((KEYS_SKIPPED + 1))
    return
  fi

  if [ -n "${!key:-}" ]; then
    echo ""
    echo "$key is already exported in your current shell but not yet in $RCFILE."
    printf "  Persist the current value to %s? [y/N] " "$RCFILE"
    read -r persist
    case "$persist" in
      [Yy]*)
        # Use the value from the current environment without echoing it
        local current_value="${!key}"
        # Apply the same validation as paste-input: single-quote and min_len
        case "$current_value" in
          *\'*)
            echo "[rejected] $key value contains a single quote. Skipped."
            KEYS_SKIPPED=$((KEYS_SKIPPED + 1))
            return
            ;;
        esac
        if [ ${#current_value} -lt $min_len ]; then
          echo "[rejected] $key current value is too short (${#current_value} chars, expected at least $min_len). Skipped."
          KEYS_SKIPPED=$((KEYS_SKIPPED + 1))
          return
        fi
        NEW_LINES="${NEW_LINES}$(build_line "$key" "$current_value")
"
        KEYS_ADDED=$((KEYS_ADDED + 1))
        echo "[ready]  $key (will write current shell value to rc)"
        ;;
      *)
        echo "[skipped] $key (kept ephemeral)"
        KEYS_SKIPPED=$((KEYS_SKIPPED + 1))
        ;;
    esac
    return
  fi

  echo ""
  echo "$key"
  echo "  $desc"
  if [ -n "$url" ]; then
    echo "  Get one at: $url"
  fi

  # -s: silent (no echo). -r: raw (no backslash escapes).
  printf "  Paste key (Enter to skip): "
  read -rs value
  echo ""

  if [ -z "$value" ]; then
    echo "[skipped] $key"
    KEYS_SKIPPED=$((KEYS_SKIPPED + 1))
    return
  fi

  # Reject single quotes (would break our single-quoted export)
  case "$value" in
    *\'*)
      echo "[rejected] $key contains a single quote, which would break the export. Skipped."
      KEYS_SKIPPED=$((KEYS_SKIPPED + 1))
      return
      ;;
  esac

  # Length sanity check (per-key minimum, default 10)
  if [ ${#value} -lt $min_len ]; then
    echo "[rejected] $key looks too short (${#value} chars, expected at least $min_len). Skipped."
    KEYS_SKIPPED=$((KEYS_SKIPPED + 1))
    return
  fi

  NEW_LINES="${NEW_LINES}$(build_line "$key" "$value")
"
  KEYS_ADDED=$((KEYS_ADDED + 1))
  echo "[ready]  $key (will write to rc)"
}

# --- Walk through the keys ---

echo "=== Tier 1 (high-value) ==="

prompt_key SEATS_AERO_API_KEY \
  "Award flight search across 27 mileage programs. The main event." \
  "https://seats.aero/profile (Pro ~\$8/mo)"

prompt_key DUFFEL_API_KEY_LIVE \
  "Real GDS cash flight prices. Free to search, pay per booking." \
  "https://duffel.com (use the LIVE key, not test)"

prompt_key IGNAV_API_KEY \
  "Backup cash flight prices. Fast REST API." \
  "https://ignav.com (1,000 free requests/month)"

prompt_key AWARDWALLET_API_KEY \
  "Auto-pull your loyalty balances, elite status, transfer ratios." \
  "https://business.awardwallet.com/profile/api (Business account required)"

prompt_key AWARDWALLET_USER_ID \
  "Your AwardWallet user ID (paired with the API key above)." \
  "" \
  3

echo ""
printf "Continue with Tier 2 (SerpAPI, RapidAPI, LiteAPI, TripAdvisor)? [y/N] "
read -r more
case "$more" in
  [Yy]*)
    prompt_key SERPAPI_API_KEY \
      "Google Flights/Hotels comparison data." \
      "https://serpapi.com (100 searches/mo free)"
    prompt_key RAPIDAPI_KEY \
      "Booking.com Live + Google Flights Live as fallback sources." \
      "https://rapidapi.com"
    prompt_key LITEAPI_API_KEY \
      "Hotel rate inventory via LiteAPI MCP." \
      "https://liteapi.travel"
    prompt_key TRIPADVISOR_API_KEY \
      "Hotel ratings, reviews, and rankings." \
      "https://tripadvisor-content-api.readme.io (5K calls/mo free)"
    ;;
esac

echo ""
printf "Continue with Tier 3 (Scandinavia transit: Entur, ResRobot, Rejseplanen)? [y/N] "
read -r more
case "$more" in
  [Yy]*)
    prompt_key ENTUR_CLIENT_NAME \
      "Norway transit search. Free, no signup. Format: 'yourcompany-app'." \
      "" \
      3
    prompt_key RESROBOT_API_KEY \
      "Sweden rail/bus search." \
      "https://www.trafiklab.se (30K calls/mo free)"
    prompt_key REJSEPLANEN_API_KEY \
      "Denmark rail/bus search." \
      "https://help.rejseplanen.dk"
    ;;
esac

# --- Write ---

echo ""
echo "Summary: $KEYS_ADDED to add, $KEYS_SKIPPED skipped."

if [ "$KEYS_ADDED" -eq 0 ]; then
  echo "Nothing to write. Done."
  exit 0
fi

printf "Write %d exports to %s? [Y/n] " "$KEYS_ADDED" "$RCFILE"
read -r confirm
case "$confirm" in
  [Nn]*)
    echo "Aborted. No changes made."
    exit 0
    ;;
esac

# Backup if file has content
if [ -s "$RCFILE" ]; then
  TIMESTAMP=$(date +%Y%m%d-%H%M%S)
  BACKUP="$RCFILE.bak.$TIMESTAMP"
  cp "$RCFILE" "$BACKUP"
  echo "Backup: $BACKUP"
fi

# Append a header + the lines
{
  echo ""
  echo "# Added by travel-hacker setup-keys.sh on $(date)"
  printf "%s" "$NEW_LINES"
} >> "$RCFILE"

echo "Wrote $KEYS_ADDED exports to $RCFILE."
echo ""
echo "Run this to load them now (or open a new terminal):"
case "$SYNTAX" in
  bash) echo "  source \"$RCFILE\"" ;;
  fish) echo "  source \"$RCFILE\"" ;;
esac

echo ""
echo "Then start Claude Code and ask it to plan a trip."

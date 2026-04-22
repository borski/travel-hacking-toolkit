#!/usr/bin/env bash
set -euo pipefail

# Travel Hacking Toolkit - Setup Script
# Gets you from clone to working in under a minute.

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"

echo "=== Travel Hacking Toolkit Setup ==="
echo ""

# --- Which tool? ---
echo "Which AI coding tool do you use?"
echo "  1) OpenCode"
echo "  2) Claude Code"
echo "  3) Codex"
echo "  4) All"
echo ""
read -rp "Choice [1-4]: " TOOL_CHOICE

case "$TOOL_CHOICE" in
  1|2|3|4) ;;
  *)
    echo "Invalid choice. Exiting."
    exit 1
    ;;
esac

USE_OPENCODE=0
USE_CLAUDE=0
USE_CODEX=0

case "$TOOL_CHOICE" in
  1)
    USE_OPENCODE=1
    ;;
  2)
    USE_CLAUDE=1
    ;;
  3)
    USE_CODEX=1
    ;;
  4)
    USE_OPENCODE=1
    USE_CLAUDE=1
    USE_CODEX=1
    ;;
esac

# --- API key setup (always, this is the main value) ---
setup_api_keys() {
  echo ""
  echo "Setting up API keys..."

  if [ "$USE_OPENCODE" -eq 1 ] || [ "$USE_CODEX" -eq 1 ]; then
    if [ ! -f "$REPO_DIR/.env" ]; then
      cp "$REPO_DIR/.env.example" "$REPO_DIR/.env"
      echo "  Created .env (OpenCode/Codex). Edit it to add your API keys."
    else
      echo "  .env already exists. Skipping."
    fi
  fi

  if [ "$USE_CLAUDE" -eq 1 ]; then
    local claude_settings="$REPO_DIR/.claude/settings.local.json"
    if [ ! -f "$claude_settings" ]; then
      if [ -f "$REPO_DIR/.claude/settings.local.json.example" ]; then
        cp "$REPO_DIR/.claude/settings.local.json.example" "$claude_settings"
        echo "  Created .claude/settings.local.json (Claude Code, auto-gitignored)."
        echo "  Edit it to add your API keys."
      fi
    else
      echo "  .claude/settings.local.json already exists. Skipping."
    fi
  fi

  echo ""
  echo "  The 5 free MCP servers work without any keys."
  echo "  For the full experience, add at minimum:"
  echo "    SEATS_AERO_API_KEY     Award flight search (the main event)"
  echo "    DUFFEL_API_KEY_LIVE    Primary cash flight prices (search free, pay per booking)"
  echo "    IGNAV_API_KEY          Secondary cash flight prices (1,000 free requests)"
  echo ""
}

# --- Atlas Obscura npm deps ---
install_atlas_deps() {
  echo "Installing Atlas Obscura dependencies..."
  if command -v npm &>/dev/null; then
    if (cd "$REPO_DIR/skills/atlas-obscura" && npm install --silent >/dev/null 2>&1); then
      echo "  Done."
    else
      echo "  npm install failed. Atlas Obscura will auto-install on first use if Node.js is available."
    fi
  else
    echo "  npm not found. Atlas Obscura will auto-install on first use if Node.js is available."
  fi
}

# --- Optional tools ---
install_optional_tools() {
  echo ""
  echo "Optional tools for additional flight search skills:"
  echo ""

  # agent-browser (for google-flights skill)
  if command -v agent-browser &>/dev/null; then
    echo "  ✓ agent-browser already installed (google-flights skill)"
  else
    echo "  agent-browser: Enables the google-flights skill (browser-automated Google Flights)."
    read -rp "  Install agent-browser? [y/N]: " AB_CHOICE
    if [[ "$AB_CHOICE" == "y" || "$AB_CHOICE" == "Y" ]]; then
      npm install -g agent-browser && agent-browser install
      echo "  ✓ agent-browser installed."
    else
      echo "  Skipped. google-flights skill won't work without it."
    fi
  fi

  echo ""

  # Southwest: Docker or Patchright
  echo "  Southwest skill: searches southwest.com for fare classes and points pricing."
  echo "  Requires either Docker (recommended) or Patchright (Python)."
  echo ""

  if command -v docker &>/dev/null; then
    echo "  Docker detected. Pulling pre-built images..."
    docker pull ghcr.io/borski/sw-fares:latest 2>/dev/null && echo "  ✓ Southwest Docker image ready." || echo "  Could not pull SW image. Build locally: docker build -t sw-fares skills/southwest/"
    docker pull ghcr.io/borski/aa-miles-check:latest 2>/dev/null && echo "  ✓ American Airlines Docker image ready." || echo "  Could not pull AA image. Build locally: docker build -t aa-check skills/american-airlines/"
    echo ""
    echo "  Chase and Amex Travel portal skills (optional, build locally):"
    echo "  docker build -t chase-travel skills/chase-travel/"
    echo "  docker build -t amex-travel skills/amex-travel/"
  else
    echo "  Docker not found."
    if python3 -c "import patchright" 2>/dev/null; then
      echo "  ✓ Patchright already installed (southwest skill, headed mode)"
    else
      read -rp "  Install Patchright for Southwest skill? [y/N]: " PR_CHOICE
      if [[ "$PR_CHOICE" == "y" || "$PR_CHOICE" == "Y" ]]; then
        pip install patchright && patchright install chromium
        echo "  ✓ Patchright installed. Southwest skill will open a Chrome window briefly."
      else
        echo "  Skipped. Southwest skill won't work without Docker or Patchright."
      fi
    fi
  fi

  echo ""
}

# --- Global install (optional) ---
offer_global_install() {
  echo ""
  echo "Skills are already available when you work from this directory."
  echo "Want to also install them system-wide (available in any project)?"
  echo ""
  read -rp "Install globally? [y/N]: " GLOBAL_CHOICE

  if [[ "$GLOBAL_CHOICE" == "y" || "$GLOBAL_CHOICE" == "Y" ]]; then
    if [ "$USE_OPENCODE" -eq 1 ]; then
      install_skills_to "$HOME/.config/opencode/skills"
    fi
    if [ "$USE_CLAUDE" -eq 1 ]; then
      install_skills_to "$HOME/.claude/skills"
    fi
  else
    echo "  Skipped. You can always run this script again later."
  fi
}

install_skills_to() {
  local target="$1"
  echo ""
  echo "  Installing skills to $target..."
  mkdir -p "$target"

  for skill_dir in "$REPO_DIR"/skills/*/; do
    skill_name=$(basename "$skill_dir")
    dest="$target/$skill_name"

    if [ -d "$dest" ]; then
      echo "    Updating $skill_name..."
      rm -rf "$dest"
    else
      echo "    Installing $skill_name..."
    fi

    cp -r "$skill_dir" "$dest"
  done

  echo "  Done."
}

install_codex_plugin() {
  local plugin_name="travel-hacking-toolkit"
  local plugin_source="$REPO_DIR/plugins/$plugin_name"
  local codex_home="${CODEX_HOME:-$HOME/.codex}"
  local codex_plugins_dir="$codex_home/plugins"
  local codex_plugin_path="$codex_plugins_dir/$plugin_name"
  local marketplace_root="${CODEX_MARKETPLACE_ROOT:-$HOME/.agents}"
  local marketplace_dir="$marketplace_root/plugins"
  local marketplace_path="$marketplace_dir/marketplace.json"

  echo ""
  echo "Installing Codex plugin..."

  mkdir -p "$codex_plugins_dir" "$marketplace_dir"

  if [ -L "$codex_plugin_path" ] || [ -e "$codex_plugin_path" ]; then
    rm -rf "$codex_plugin_path"
  fi

  ln -s "$plugin_source" "$codex_plugin_path"

  python3 - "$marketplace_path" <<'PY'
import json
import os
import sys

path = sys.argv[1]
entry = {
    "name": "travel-hacking-toolkit",
    "source": {
        "source": "local",
        "path": "./plugins/travel-hacking-toolkit"
    },
    "policy": {
        "installation": "AVAILABLE",
        "authentication": "ON_INSTALL"
    },
    "category": "Productivity"
}

if os.path.exists(path):
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
else:
    data = {
        "name": "local-plugins",
        "interface": {
            "displayName": "Local Plugins"
        },
        "plugins": []
    }

data.setdefault("name", "local-plugins")
data.setdefault("interface", {})
data["interface"].setdefault("displayName", "Local Plugins")
plugins = data.setdefault("plugins", [])

for idx, plugin in enumerate(plugins):
    if plugin.get("name") == entry["name"]:
        plugins[idx] = entry
        break
else:
    plugins.append(entry)

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PY

  echo "  Plugin symlinked to $codex_plugin_path"
  echo "  Marketplace updated at $marketplace_path"
  echo "  Launch Codex from this repo after running: source .env"
}

# --- Run ---
setup_api_keys
install_atlas_deps
install_optional_tools

if [ "$USE_CODEX" -eq 1 ]; then
  install_codex_plugin
fi

if [ "$USE_OPENCODE" -eq 1 ] || [ "$USE_CLAUDE" -eq 1 ]; then
  offer_global_install
fi

echo ""
echo "=== Setup complete! ==="
echo ""
echo "Launch your tool from this directory:"

if [ "$USE_OPENCODE" -eq 1 ]; then
  echo "  OpenCode:    opencode"
fi
if [ "$USE_CLAUDE" -eq 1 ]; then
  echo "  Claude Code: claude --strict-mcp-config --mcp-config .mcp.json"
fi
if [ "$USE_CODEX" -eq 1 ]; then
  echo "  Codex:       source .env && codex"
fi

echo ""

if [ "$USE_OPENCODE" -eq 1 ] || [ "$USE_CODEX" -eq 1 ]; then
  echo "Add your API keys:  edit .env"
fi
if [ "$USE_CLAUDE" -eq 1 ]; then
  echo "Add your API keys:  edit .claude/settings.local.json"
fi

echo ""
echo "Then ask: \"Find me a cheap business class flight to Tokyo\""
echo ""

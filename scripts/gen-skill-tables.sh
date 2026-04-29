#!/usr/bin/env bash
# Generate README.md and llms.txt skill tables from SKILL.md frontmatter.
#
# Reads frontmatter from skills/*/SKILL.md, groups by category, and replaces
# the contents of marked regions in README.md and llms.txt.
#
# Markers:
#   <!-- BEGIN: section-id -->
#   ...generated content...
#   <!-- END: section-id -->
#
# Required frontmatter fields per skill: name, category, summary
# Optional: api_key, docker_image
#
# Usage:
#   scripts/gen-skill-tables.sh           # write README.md and llms.txt in place
#   scripts/gen-skill-tables.sh --check   # exit 1 if files would change (drift)
#   scripts/gen-skill-tables.sh --stdout  # print generated regions to stdout

set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
SKILLS_DIR="$REPO/skills"
README="$REPO/README.md"
LLMS="$REPO/llms.txt"

MODE="write"
case "${1:-}" in
  --check)  MODE="check" ;;
  --stdout) MODE="stdout" ;;
  --write|"") MODE="write" ;;
  *) echo "Usage: $0 [--check|--stdout|--write]" >&2; exit 2 ;;
esac

# --- Extract frontmatter into a flat TSV ---
# Output columns: name, category, summary, api_key, docker_image
# Portable awk (no gawk-isms): split on first colon manually.
extract_skills() {
  for dir in "$SKILLS_DIR"/*/; do
    local skill_md="$dir/SKILL.md"
    [ -f "$skill_md" ] || continue
    awk '
      BEGIN { in_fm=0 }
      /^---$/ {
        if (in_fm == 0) { in_fm=1; next }
        else { in_fm=2; exit }
      }
      in_fm == 1 {
        # Find first colon. Key must be [a-zA-Z_-]+ before colon.
        idx = index($0, ":")
        if (idx <= 1) next
        key = substr($0, 1, idx-1)
        # Skip indented continuation lines or weird keys
        if (key !~ /^[a-zA-Z_-]+$/) next
        val = substr($0, idx+1)
        # Trim leading whitespace from val
        sub(/^[[:space:]]+/, "", val)
        fields[key] = val
      }
      END {
        printf "%s\t%s\t%s\t%s\t%s\n", \
          fields["name"], \
          fields["category"], \
          fields["summary"], \
          fields["api_key"], \
          fields["docker_image"]
      }
    ' "$skill_md"
  done
}

ALL_SKILLS=$(extract_skills | sort)

# Sanity: ensure every skill has the required fields
missing_check=$(awk -F'\t' '
  { if ($1 == "" || $2 == "" || $3 == "") print "MISSING-FIELDS: " $1 " (cat="$2" sum="$3")" }
' <<< "$ALL_SKILLS")
if [ -n "$missing_check" ]; then
  echo "ERROR: skills missing required frontmatter fields:" >&2
  echo "$missing_check" >&2
  exit 1
fi

# --- Helpers to filter by category and emit tables ---

# Format: skill_row_for_readme <category>
# Outputs markdown table rows for that category.
skill_rows_readme() {
  local cat="$1"
  awk -F'\t' -v cat="$cat" '
    $2 == cat {
      name=$1; summary=$3; api_key=$4; docker=$5
      # Compose the "What It Does" cell
      what = summary
      if (docker != "") {
        what = what " Docker: `" docker "`."
      }
      # API key column: if blank, default to "None"
      key = (api_key == "" ? "None" : api_key)
      printf "| **%s** | %s | %s |\n", name, what, key
    }
  ' <<< "$ALL_SKILLS"
}

# Format: skill_rows_reference <category>
# Different table shape for reference skills (no API key column)
skill_rows_reference() {
  local cat="$1"
  awk -F'\t' -v cat="$cat" '
    $2 == cat {
      printf "| **%s** | %s |\n", $1, $3
    }
  ' <<< "$ALL_SKILLS"
}

# Format: docker_table_rows
# Emits one row per skill with a docker_image
docker_table_rows() {
  awk -F'\t' '
    $5 != "" {
      name=$1; summary=$3; docker=$5
      # Strip ":latest" or ":tag" for the markdown link
      base=docker
      sub(/:[^:]+$/, "", base)
      # Generate package URL for ghcr.io
      pkg_url=""
      if (base ~ /^ghcr\.io\//) {
        # ghcr.io/borski/foo -> https://github.com/borski/travel-hacking-toolkit/pkgs/container/foo
        n = split(base, parts, "/")
        owner = parts[2]
        image = parts[n]
        pkg_url = "https://github.com/" owner "/travel-hacking-toolkit/pkgs/container/" image
      }
      # Skill source link
      src_link = "[skills/" name "](skills/" name "/Dockerfile)"
      # Compose
      img_link = (pkg_url == "" ? "`" base "`" : "[`" base "`](" pkg_url ")")
      printf "| %s | `%s` | %s | %s |\n", img_link, name, summary, src_link
    }
  ' <<< "$ALL_SKILLS"
}

# Format: llms_link_rows <category>
# Emits "- [Title](github URL): summary." lines for llms.txt
llms_link_rows() {
  local cat="$1"
  awk -F'\t' -v cat="$cat" '
    function title_case(s,    i, n, parts, out) {
      n = split(s, parts, "-")
      out = ""
      for (i = 1; i <= n; i++) {
        out = out (i==1 ? "" : " ") toupper(substr(parts[i], 1, 1)) substr(parts[i], 2)
      }
      return out
    }
    $2 == cat {
      name=$1; summary=$3; docker=$5
      title = title_case(name)
      url = "https://github.com/borski/travel-hacking-toolkit/blob/main/skills/" name "/SKILL.md"
      line = "- [" title "](" url "): " summary
      # Trim trailing period
      sub(/\.$/, "", line)
      # Append docker hint if present
      if (docker != "") {
        # Strip :latest tag
        base=docker; sub(/:[^:]+$/, "", base)
        line = line ". Docker: `" base "`"
      }
      print line "."
    }
  ' <<< "$ALL_SKILLS"
}

# --- Build all generated regions ---

# Region: readme:orchestration
build_readme_orchestration() {
  cat <<HEADER
| Skill | What It Does | API Key |
|-------|-------------|---------|
HEADER
  skill_rows_readme orchestration
}

build_readme_flights() {
  cat <<HEADER
| Skill | What It Does | API Key |
|-------|-------------|---------|
HEADER
  skill_rows_readme flights
}

build_readme_portals() {
  cat <<HEADER
| Skill | What It Does | API Key |
|-------|-------------|---------|
HEADER
  skill_rows_readme portals
}

build_readme_hotels() {
  cat <<HEADER
| Skill | What It Does | API Key |
|-------|-------------|---------|
HEADER
  skill_rows_readme hotels
}

build_readme_loyalty() {
  cat <<HEADER
| Skill | What It Does | API Key |
|-------|-------------|---------|
HEADER
  skill_rows_readme loyalty
}

build_readme_destinations() {
  cat <<HEADER
| Skill | What It Does | API Key |
|-------|-------------|---------|
HEADER
  skill_rows_readme destinations
}

build_readme_reference() {
  cat <<HEADER
| Skill | What It Covers |
|-------|---------------|
HEADER
  skill_rows_reference reference
}

build_readme_docker() {
  # Static base layer + auto-generated skill images
  cat <<'HEADER'
| Image | Skill | Purpose | Source |
|-------|-------|---------|--------|
| [`ghcr.io/borski/patchright-docker`](https://github.com/borski/travel-hacking-toolkit/pkgs/container/patchright-docker) | (base) | Patchright + Chromium + xvfb base layer that all other browser-skill images build on. | [external](https://github.com/borski/patchright-docker) |
HEADER
  docker_table_rows
}

# Signup links map. Real external APIs and accounts only.
# Skills that just use Patchright, agent-browser, or other dev tooling are NOT
# included here. Browser automation tools have no API key and aren't a signup
# step the user takes; they're handled by the prebuilt Docker images.
# Format: skill_name|Display Name|URL|optional notes
signup_links_data() {
  cat <<'DATA'
duffel|Duffel|https://duffel.com|Real GDS flight search. Free tier available.
ignav|Ignav|https://ignav.com|Fast flight search REST API. 1,000 free requests, no credit card.
seats-aero|Seats.aero|https://seats.aero|Award flight availability across 27 mileage programs. Pro tier ($99/yr) includes API access.
rapidapi|RapidAPI|https://rapidapi.com|Marketplace; subscribe to Booking.com Live + Google Flights Live.
serpapi|SerpAPI|https://serpapi.com|Google Flights, Google Hotels, Travel Explore.
tripadvisor|TripAdvisor|https://www.tripadvisor.com/developers|Hotel/restaurant/attraction data. 5K calls/month free.
awardwallet|AwardWallet|https://business.awardwallet.com|Loyalty program balance aggregator. Business tier required.
ticketsatwork|TicketsAtWork|https://www.ticketsatwork.com|Corporate-perks portal. Account requires employer affiliation. Same credentials work for Working Advantage, Plum, Beneplace (shared EBG backend).
scandinavia-transit|Trafiklab (Sweden)|https://www.trafiklab.se|Sweden transit. Free API key. 30,000 calls/month.
scandinavia-transit|Rejseplanen (Denmark)|https://labs.rejseplanen.dk|Denmark transit. Free API key (application required). 50,000 calls/month, non-commercial only.
DATA
}

build_readme_signup_links() {
  echo "These skills require an external account or API key signup. See [\`.env.example\`](.env.example) for the full list of env vars (some skills require an env var without a real signup, e.g. \`scandinavia-transit\` needs an \`ENTUR_CLIENT_NAME\` you choose yourself for Entur's required identification header)."
  echo
  echo "| Skill | Service | Link | Notes |"
  echo "|-------|---------|------|-------|"
  signup_links_data | awk -F'|' '
    {
      # Render the URL as a clickable link with shortened text
      url = $3
      display = url
      sub(/^https?:\/\//, "", display)
      printf "| `%s` | %s | [%s](%s) | %s |\n", $1, $2, display, url, $4
    }
  '
}

build_llms_orchestration() { llms_link_rows orchestration; }
build_llms_flights()       { llms_link_rows flights; }
build_llms_portals()       { llms_link_rows portals; }
build_llms_hotels()        { llms_link_rows hotels; }
build_llms_loyalty()       { llms_link_rows loyalty; }
build_llms_destinations()  { llms_link_rows destinations; }
build_llms_reference()     { llms_link_rows reference; }

# --- Replace regions in a file ---
# Args: $1=section-id, $2=file, $3=generator function name
# Mutates the file in place via temp file. Idempotent.
# Portable: writes generator output to a temp file, reads it inside awk.
replace_region() {
  local section="$1" file="$2" generator="$3"
  local begin="<!-- BEGIN: $section -->"
  local end="<!-- END: $section -->"
  local tmp gen_tmp
  tmp="$(mktemp)"
  gen_tmp="$(mktemp)"
  $generator > "$gen_tmp"

  awk -v begin="$begin" -v end="$end" -v gen_file="$gen_tmp" '
    BEGIN { state = 0 }
    {
      if (state == 0 && index($0, begin) > 0) {
        print
        while ((getline line < gen_file) > 0) print line
        close(gen_file)
        state = 1
        next
      }
      if (state == 1) {
        if (index($0, end) > 0) {
          print
          state = 0
        }
        next
      }
      print
    }
  ' "$file" > "$tmp"

  rm -f "$gen_tmp"

  # Sanity: ensure both markers were present
  if ! grep -q "$begin" "$tmp" || ! grep -q "$end" "$tmp"; then
    echo "ERROR: missing marker for '$section' in $file" >&2
    rm -f "$tmp"
    return 1
  fi

  mv "$tmp" "$file"
}

# --- Main ---

REGIONS_README=(
  "readme:orchestration:build_readme_orchestration"
  "readme:flights:build_readme_flights"
  "readme:portals:build_readme_portals"
  "readme:hotels:build_readme_hotels"
  "readme:loyalty:build_readme_loyalty"
  "readme:destinations:build_readme_destinations"
  "readme:reference:build_readme_reference"
  "readme:signup-links:build_readme_signup_links"
  "readme:docker:build_readme_docker"
)

REGIONS_LLMS=(
  "llms:orchestration:build_llms_orchestration"
  "llms:flights:build_llms_flights"
  "llms:portals:build_llms_portals"
  "llms:hotels:build_llms_hotels"
  "llms:loyalty:build_llms_loyalty"
  "llms:destinations:build_llms_destinations"
  "llms:reference:build_llms_reference"
)

case "$MODE" in
  stdout)
    echo "=== README regions ==="
    for spec in "${REGIONS_README[@]}"; do
      IFS=':' read -r ns sec gen <<< "$spec"
      echo "--- ${ns}:${sec} ---"
      $gen
      echo
    done
    echo "=== llms.txt regions ==="
    for spec in "${REGIONS_LLMS[@]}"; do
      IFS=':' read -r ns sec gen <<< "$spec"
      echo "--- ${ns}:${sec} ---"
      $gen
      echo
    done
    ;;

  write|check)
    if [ "$MODE" = "check" ]; then
      tmp_readme="$(mktemp)"; cp "$README" "$tmp_readme"
      tmp_llms="$(mktemp)"; cp "$LLMS" "$tmp_llms"
      target_readme="$tmp_readme"
      target_llms="$tmp_llms"
    else
      target_readme="$README"
      target_llms="$LLMS"
    fi

    for spec in "${REGIONS_README[@]}"; do
      IFS=':' read -r ns sec gen <<< "$spec"
      replace_region "${ns}:${sec}" "$target_readme" "$gen"
    done

    for spec in "${REGIONS_LLMS[@]}"; do
      IFS=':' read -r ns sec gen <<< "$spec"
      replace_region "${ns}:${sec}" "$target_llms" "$gen"
    done

    if [ "$MODE" = "check" ]; then
      drift=0
      if ! diff -q "$README" "$tmp_readme" > /dev/null 2>&1; then
        echo "DRIFT in README.md:"
        diff -u "$README" "$tmp_readme" | head -80
        drift=1
      fi
      if ! diff -q "$LLMS" "$tmp_llms" > /dev/null 2>&1; then
        echo "DRIFT in llms.txt:"
        diff -u "$LLMS" "$tmp_llms" | head -80
        drift=1
      fi
      rm -f "$tmp_readme" "$tmp_llms"
      [ $drift -eq 0 ] && echo "OK: README.md and llms.txt match generated output"
      exit $drift
    else
      echo "Wrote: README.md, llms.txt"
    fi
    ;;
esac

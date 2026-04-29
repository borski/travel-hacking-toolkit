#!/usr/bin/env python3
"""Sync SKILL.md frontmatter against scripts/skill-meta.tsv.

This is the source of truth for the auto-generated portions of skill
frontmatter. Edit scripts/skill-meta.tsv, then run this script to push
the changes into each skill's SKILL.md frontmatter.

Managed fields (replaced on every run):
  - category
  - summary
  - api_key
  - docker_image

Other fields (name, description, allowed-tools, etc.) are not touched.
Managed fields appear in canonical order right after `description`.

Forbids colons, quotes, and other chars that break OpenCode's frontmatter
parsing. If the script raises ValueError, fix the TSV entry to remove the
offending character.

Usage:
  python3 scripts/sync-skill-frontmatter.py
"""
import csv
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
TSV = REPO / "scripts" / "skill-meta.tsv"
MANAGED = ["category", "summary", "api_key", "docker_image"]
# Chars that always cause YAML issues anywhere in the value.
# Note: % is OK except at start; & * ! @ ` are OK except at start; # is OK
# except after whitespace. We disallow them everywhere because mixing rules
# is fragile. But % is too common (10%, 30-50%) so we allow it mid-value.
FORBIDDEN_ANY = set(':"\'`')

# Chars only forbidden at the start of a value
FORBIDDEN_START = set('-?#&*!@%>|')

def assert_safe(field, value):
    if not value:
        return
    bad = sorted(set(value) & FORBIDDEN_ANY)
    if bad:
        raise ValueError(f"value for {field} has unsafe chars {bad}: {value!r}")
    if value[0] in FORBIDDEN_START:
        raise ValueError(f"value for {field} starts with reserved YAML char {value[0]!r}: {value!r}")
    if value.endswith(' '):
        raise ValueError(f"value for {field} has trailing space: {value!r}")

def parse_frontmatter_block(text):
    """Return (lines_inside_fm, rest_after_fm) or (None, text)."""
    if not text.startswith("---\n"):
        return None, text
    end_match = re.search(r"\n---\n", text[4:])
    if not end_match:
        return None, text
    fm = text[4:4 + end_match.start()]
    rest = text[4 + end_match.start() + 5:]
    return fm.split("\n"), rest

def sync_skill(name, target_meta):
    skill_md = REPO / "skills" / name / "SKILL.md"
    if not skill_md.exists():
        print(f"SKIP missing: {name}")
        return False

    text = skill_md.read_text()
    fm_lines, rest = parse_frontmatter_block(text)
    if fm_lines is None:
        print(f"SKIP no frontmatter: {name}")
        return False

    # Validate target values
    for field in MANAGED:
        assert_safe(field, target_meta.get(field, ""))

    # Walk lines: replace managed field lines with new values, keep others.
    # Find insertion anchor (after `description:`) for any managed fields not present.
    new_lines = []
    seen = set()
    desc_end_idx = None  # index in new_lines where description block ends

    i = 0
    while i < len(fm_lines):
        line = fm_lines[i]
        m = re.match(r"^([a-zA-Z_-]+)\s*:\s*(.*)$", line)
        if m:
            key = m.group(1)
            if key in MANAGED:
                value = target_meta.get(key, "")
                if value:
                    new_lines.append(f"{key}: {value}")
                    seen.add(key)
                # If value is empty, we omit the field entirely
                # (delete from frontmatter)
                i += 1
                continue
            new_lines.append(line)
            if key == "description":
                # Track end of description (handle folded multiline)
                j = i + 1
                while j < len(fm_lines) and (fm_lines[j].startswith(" ") or fm_lines[j].startswith("\t")):
                    new_lines.append(fm_lines[j])
                    j += 1
                desc_end_idx = len(new_lines)
                i = j
                continue
        else:
            new_lines.append(line)
        i += 1

    # Insert any managed fields not yet seen, after description (or at start if no desc)
    insert_at = desc_end_idx if desc_end_idx is not None else 1
    additions = []
    for field in MANAGED:
        if field in seen:
            continue
        value = target_meta.get(field, "")
        if value:
            additions.append(f"{field}: {value}")
    if additions:
        new_lines = new_lines[:insert_at] + additions + new_lines[insert_at:]

    # Reorder managed fields to canonical order: category, summary, api_key, docker_image
    # (Just in case any drift occurred.)
    managed_indices = []
    managed_values_by_key = {}
    for idx, line in enumerate(new_lines):
        m = re.match(r"^([a-zA-Z_-]+)\s*:", line)
        if m and m.group(1) in MANAGED:
            managed_indices.append(idx)
            managed_values_by_key[m.group(1)] = line

    if managed_indices:
        first_idx = min(managed_indices)
        # Remove all managed lines
        kept = [l for i, l in enumerate(new_lines) if i not in set(managed_indices)]
        # Insert in canonical order at first_idx
        ordered = [managed_values_by_key[k] for k in MANAGED if k in managed_values_by_key]
        new_lines = kept[:first_idx] + ordered + kept[first_idx:]

    new_text = "---\n" + "\n".join(new_lines).rstrip("\n") + "\n---\n" + rest
    if new_text != text:
        skill_md.write_text(new_text)
        return True
    return False

def main():
    if not TSV.exists():
        print(f"FATAL: {TSV} missing", file=sys.stderr)
        sys.exit(1)

    changed = 0
    with TSV.open() as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            try:
                if sync_skill(row["name"], row):
                    changed += 1
                    print(f"UPDATED: {row['name']}")
            except ValueError as e:
                print(f"FATAL {row['name']}: {e}", file=sys.stderr)
                sys.exit(1)
    print(f"\n{changed} file(s) changed")

if __name__ == "__main__":
    main()

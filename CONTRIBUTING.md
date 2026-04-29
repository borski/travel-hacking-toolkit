# Contributing

Thanks for the interest. This guide covers the patterns the toolkit expects so your PR lands quickly.

## Quick Start

1. Fork and clone
2. Make your change
3. Run `bash scripts/smoke-test.sh --quick` (must pass with 0 failures)
4. Open a PR with a clear description

That's the short version. The rest of this doc explains the *why* behind the patterns and the gotchas that have bitten contributors before.

## What Belongs in the Toolkit

The toolkit is a curated set of skills, MCPs, and reference data for award/cash travel comparison and planning. PRs are most likely to land if they fit one of these:

- **A new skill** that wraps a useful API, browser automation target, or reference dataset
- **An improvement** to an existing skill (better parsing, more endpoints, fewer false positives)
- **A bug fix** with a reproducible test case
- **Setup script improvements** for macOS, Linux, or Windows
- **Documentation fixes** when something is wrong, unclear, or missing

PRs less likely to land:

- Skills that duplicate existing capability without a clear differentiator
- Skills behind paid APIs without a free tier or affordable starter price
- "Vibecoded" MCPs with thin docs or unverified API behavior
- Refactors that move working code around without solving a real problem

When in doubt, open an issue first to discuss the approach.

## Adding a New Skill

The toolkit uses progressive disclosure: each skill's `name` and `description` are loaded on every session, and the agent reads the full `SKILL.md` only when it decides to use the skill. Frontmatter is the contract.

### 1. Create the skill directory

```
skills/your-skill/
├── SKILL.md          # required
├── Dockerfile        # optional, if the skill needs browser automation or sandboxing
└── scripts/          # optional, any helper scripts the skill calls
```

### 2. Write SKILL.md frontmatter

```yaml
---
name: your-skill
description: One paragraph describing what the skill does, when the agent should load it, and any trigger phrases. This is what the agent sees on every session, so be specific. Mention APIs, free vs paid, key features, and 2-4 trigger phrases like "Foo lookup", "bar search".
category: flights
summary: Short one-liner shown in README tables and llms.txt.
api_key: Foo (free)
docker_image: ghcr.io/borski/your-skill
---
```

| Field | Required | Notes |
|-------|----------|-------|
| `name` | yes | Skill identifier. Must match the directory name. |
| `description` | yes | Long-form discovery text for the agent. Include trigger phrases. |
| `category` | yes | One of: `orchestration`, `flights`, `portals`, `hotels`, `loyalty`, `destinations`, `reference` |
| `summary` | yes | One-liner for human-facing tables (README, llms.txt) |
| `api_key` | optional | Short label for the API Key column. Use `None (free)` if no key needed. |
| `docker_image` | optional | Full ghcr.io image path if the skill ships a Docker image |

### 3. Write the skill body

After frontmatter, write the skill instructions in markdown. Show:

- What the skill does and when to use it
- Required env vars or setup
- Concrete usage examples (curl commands, function calls, CLI flags)
- Output format expectations (typically markdown tables)
- Common failure modes and how to handle them

Look at `skills/duffel/SKILL.md` or `skills/seats-aero/SKILL.md` for reference patterns.

### 4. Update the metadata TSV

The README and `llms.txt` skill tables are generated from `scripts/skill-meta.tsv`. Add a row:

```
your-skill	flights	One-liner summary.	Foo (free)	
```

Tab-separated. Empty trailing field for skills without a Docker image. Then sync and regenerate:

```bash
python3 scripts/sync-skill-frontmatter.py   # writes managed fields into SKILL.md frontmatter
bash scripts/gen-skill-tables.sh            # regenerates README + llms.txt
```

If your skill needs a signup link, add an entry to the `signup_links_data` function in `scripts/gen-skill-tables.sh` and rerun the generator.

### 5. Run the smoke test

```bash
bash scripts/smoke-test.sh --quick
```

All 7 static checks must pass. If you have any of `codex`, `claude`, or `opencode` CLIs installed, run the full test (`bash scripts/smoke-test.sh`) to verify your skill loads correctly in real agents.

## Hard Rules

These rules exist because we hit the problem the hard way.

### No Colons in Frontmatter Values

OpenCode's frontmatter parser is sensitive to colons. Don't write:

```yaml
summary: Amex MR portal: flights, hotels, IAP discounts.
```

Write this instead:

```yaml
summary: Amex MR portal for flights, hotels, IAP discounts.
```

This applies to `name`, `description`, `category`, `summary`, `api_key` — every value. The sync script (`scripts/sync-skill-frontmatter.py`) will fail loudly if you sneak one in. Same applies to single quotes, double quotes, and backticks in values.

### No Hand-Edits to Generated Tables

The skill tables in `README.md` and `llms.txt` are generated. Edit the source (frontmatter or the TSV), not the tables. The smoke test catches drift and fails the build.

```bash
bash scripts/gen-skill-tables.sh           # regenerate after frontmatter changes
bash scripts/gen-skill-tables.sh --check   # verify no drift (used by smoke test)
```

If you see a "DRIFT" failure in CI or local smoke test, run `bash scripts/gen-skill-tables.sh` and commit the result.

### Docker Images Must Build on `patchright-docker` (when applicable)

Skills that need browser automation should base on `ghcr.io/borski/patchright-docker` (Patchright + Chromium + xvfb). Don't roll your own Chromium install. See `skills/southwest/Dockerfile` for the pattern.

If you add a new Docker-based skill, the image must be public on ghcr.io and listed in `setup.sh` and `setup.ps1` so users get auto-pulls.

### Don't Commit Secrets or Personal Data

Use `.env` for local secrets. Use `.env.example` to document required env vars. Never commit:

- API keys
- Personal email addresses, names, or account numbers
- Booking confirmation numbers
- IP addresses

`scripts/smoke-test.sh` doesn't currently scan for this, but `ggshield` does. Run it locally if you're touching anything sensitive.

## Pull Request Etiquette

- **Small, focused PRs.** One skill per PR. One bug fix per PR. Avoid grab-bags.
- **Describe the why.** What problem does this solve? What's the alternative if not merged?
- **Show your work.** If you added a skill, paste sample output. If you fixed a bug, paste before/after.
- **Update relevant docs.** New skill? Add the row to `skills/skill-meta.tsv` and run the generator. New env var? Update `.env.example`.
- **Pass smoke tests.** All static checks must be green. Agent checks are best-effort if you don't have all 3 CLIs installed.

## Local Development Setup

```bash
git clone https://github.com/borski/travel-hacking-toolkit.git
cd travel-hacking-toolkit
cp .env.example .env  # fill in any keys you have
bash scripts/setup.sh # interactive installer for OpenCode/Claude/Codex
```

The `scripts/setup.sh` and `scripts/setup.ps1` (Windows) installers handle skill installation, MCP config, and Docker image pulls. They're the recommended path for both contributors and users.

## Getting Help

- Open an issue describing your goal before starting big work
- Tag the relevant existing skill if you're improving it
- For questions about the toolkit's design philosophy, browse closed PRs and issues

## License

By contributing, you agree your contribution is licensed under the MIT License (see `LICENSE`).

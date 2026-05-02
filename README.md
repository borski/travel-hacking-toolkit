# Travel Hacking Toolkit

AI-powered travel hacking with points, miles, and award flights. Drop-in skills and MCP servers for [OpenCode](https://opencode.ai), [Claude Code](https://docs.anthropic.com/en/docs/claude-code), and [Codex](https://openai.com/codex/).

Ask your AI to find you a 60,000-mile business class flight to Tokyo. It'll search award availability across 27 mileage programs, compare against cash prices, check your loyalty balances, and tell you the best play.

## Quick Start

### Install via plugin (no clone)

The easiest way to use the toolkit. Pick your tool:

#### Claude Code

Inside Claude Code, run:

```
/plugin marketplace add borski/travel-hacking-toolkit
/plugin install travel-hacker@borski
```

Done. 42 skills, 6 MCP servers (5 free + LiteAPI which needs a key), and the `travel-hacker` subagent are installed. Run `claude` from anywhere and ask it to plan a trip.

To verify the install, run `/travel-hacker:getting-started` inside Claude Code. It tells you which API keys are configured and points at the local setup script for the missing ones. Or in your shell: `claude plugin list | grep travel-hacker` should show the plugin.

#### Codex

In your terminal:

```bash
codex plugin marketplace add borski/travel-hacking-toolkit
```

Then start Codex and the plugin appears in `/plugins`. Codex pulls the marketplace catalog from the repo (`.agents/plugins/marketplace.json`) and the plugin manifest from `plugins/travel-hacking-toolkit/.codex-plugin/plugin.json`, so the install is one command.

#### Cowork (Claude Desktop's agent panel)

Cowork itself doesn't expose `/plugin` slash commands, so you can't install plugins from inside a Cowork chat. Install via Claude Code first; Cowork picks it up automatically because both share `~/.claude/plugins/`.

1. **In your terminal**, run `claude`
2. **In Claude Code**, run the two install commands from the [Claude Code section above](#claude-code)
3. **Open Cowork** inside Claude Desktop. The plugin is already there.

Claude Desktop's chat UI doesn't support the plugin format yet, so use Cowork inside the same app for the full experience.

### Configure API keys

The 5 free MCP servers (Skiplagged, Kiwi, Trivago, Ferryhopper, Airbnb) work immediately with zero keys. Cash flight and hotel search work out of the box.

To unlock award search and the rest of the toolkit, you need API keys set as environment variables in your shell. Run the local setup script:

**macOS / Linux / WSL / Git Bash:**

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/borski/travel-hacking-toolkit/main/scripts/setup-keys.sh)
```

**Windows (PowerShell):**

```powershell
iwr https://raw.githubusercontent.com/borski/travel-hacking-toolkit/main/scripts/setup-keys.ps1 -OutFile $env:TEMP\setup-keys.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File $env:TEMP\setup-keys.ps1
Remove-Item $env:TEMP\setup-keys.ps1
```

The script prompts for each key with masked input, validates them (rejects values with single quotes that would break the export, plus a per-key minimum length sanity check), writes them to the right shell rc with a backup, and never echoes the values back. The exports are single-quoted so other shell metacharacters in the key are safe. Keys never enter your terminal scrollback or any chat session. The `/travel-hacker:getting-started` skill inside Claude Code points at the same script.

The 4 highest-value keys:

| Key | What it unlocks | Cost |
|-----|------|-----------|
| `SEATS_AERO_API_KEY` | Award flight search across 27 mileage programs. The main event. | Pro ~$8/mo |
| `DUFFEL_API_KEY_LIVE` | Real GDS cash flight prices. | Free to search, pay per booking |
| `IGNAV_API_KEY` | Backup cash flight prices. Fast REST API. | 1,000 free requests/month |
| `AWARDWALLET_API_KEY` + `AWARDWALLET_USER_ID` | Auto-pull your loyalty balances, elite status, transfer ratios. | Business account required |

Other keys (SerpAPI, RapidAPI, LiteAPI, TripAdvisor, RESROBOT, Rejseplanen, Entur) extend specific skills. The setup skill covers them too. See the [full API key reference](#api-keys--signup-links) for signup links.

Five Docker-based skills (Southwest, American Airlines, Chase, Amex, TicketsAtWork) handle sites that don't have public APIs, plus a shared base image. They auto-pull on first use. See the [Docker Images](#docker-images) section for credentials and configuration.

#### Manual setup (if you'd rather not use the skill)

Add to your shell rc (`~/.zshrc`, `~/.bashrc`, etc.):

```bash
export SEATS_AERO_API_KEY="your-key-here"
export DUFFEL_API_KEY_LIVE="your-key-here"
export IGNAV_API_KEY="your-key-here"
export AWARDWALLET_API_KEY="your-key-here"
export AWARDWALLET_USER_ID="your-user-id"
```

Reload (`source ~/.zshrc`) or open a new terminal, then run `claude`.

If you keep secrets in 1Password, you can resolve at launch instead:

```bash
op run --no-masking --env-file=.env -- claude
```

The `--no-masking` flag is required because `op run`'s default output masking interferes with Claude Code's TTY detection and triggers a non-interactive prompt error. Masking only affects stdout, not the env vars themselves, so the keys still get to claude correctly.

(See [1Password CLI docs](https://developer.1password.com/docs/cli/secrets-environment-variables/) for the `.env` template syntax.)

> The toolkit reads keys from the shell environment because plugin `userConfig` doesn't propagate to skills that shell out to scripts (verified empirically; related upstream issues [anthropics/claude-code#11927](https://github.com/anthropics/claude-code/issues/11927), [#39125](https://github.com/anthropics/claude-code/issues/39125)).

### Clone path (for OpenCode users or contributors)

OpenCode doesn't have a plugin format, so OpenCode users clone the repo. Contributors who want to hack on the toolkit also clone.

```bash
git clone https://github.com/borski/travel-hacking-toolkit.git
cd travel-hacking-toolkit

# macOS / Linux / WSL / Git Bash
./scripts/setup.sh

# Windows (PowerShell or cmd)
.\scripts\setup.cmd
```

The setup script picks your tool (OpenCode, Claude Code, Codex, or all three), creates your API key config file, installs dependencies, and optionally installs skills system-wide for OpenCode and Claude Code.

On Windows the `.cmd` wrapper launches `scripts\setup.ps1` with an ExecutionPolicy bypass so nothing needs to be unblocked first.

Then launch your tool from inside the repo:

```bash
# OpenCode
opencode

# Claude Code (loads the plugin from the working tree, no install needed)
claude --plugin-dir .

# Codex
source .env && codex
```

`claude --plugin-dir .` loads the plugin (skills, MCP servers, and the `travel-hacker` subagent) directly from your clone. Changes you make to the toolkit are picked up immediately. Useful when you're contributing.

## What's Included

### MCP Servers (real-time tools)

| Server | What It Does | API Key |
|--------|-------------|---------|
| [Skiplagged](https://skiplagged.com) | Flight search with hidden city fares | None (free) |
| [Kiwi.com](https://www.kiwi.com) | Flights with virtual interlining (creative cross-airline routing) | None (free) |
| [Trivago](https://mcp.trivago.com/docs) | Hotel metasearch across booking sites | None (free) |
| [Ferryhopper](https://ferryhopper.github.io/fh-mcp/) | Ferry routes across 33 countries, 190+ operators | None (free) |
| [Airbnb](https://github.com/openbnb-org/mcp-server-airbnb) | Search Airbnb listings, property details, pricing. Includes geocoding fix, property type filter, and DISABLE_GEOCODING opt-out. | None (free) |
| [LiteAPI](https://mcp.liteapi.travel) | Hotel search with live rates and booking | [LiteAPI](https://liteapi.travel) |

### Skills (API knowledge for your AI)

Start here: the **orchestration skills** call everything else automatically.

> The skill tables below are auto-generated from `skills/*/SKILL.md` frontmatter by `scripts/gen-skill-tables.sh`. Edit the source frontmatter, not the tables. Signup links and API key URLs live in the [API Keys & Signup Links](#api-keys--signup-links) section below.

#### Orchestration

<!-- BEGIN: readme:orchestration -->
| Skill | What It Does | API Key |
|-------|-------------|---------|
| **award-calendar** | Cheapest award dates for a route across a date range. Calendar grid view. | Seats.aero Pro |
| **compare-flights** | Unified flight comparison across ALL sources in parallel. Auto-applies transfer optimization. | Uses individual skill keys |
| **compare-hotels** | Unified hotel comparison across portals, metasearch, and Airbnb. FHR/Edit stacking detection. | Uses individual skill keys |
| **getting-started** | First-run onboarding. Detects setup, points to setup-keys script, shows sample prompts. | None |
| **plan-trip** | Guided trip planner. The hero command for the toolkit. | None |
| **trip-calculator** | Cash vs points decision answered with math. Transfer ratios, taxes, opportunity cost. | None (free, local data) |
| **trip-planner** | Full trip planning. Flights + hotels + points in one shot. | Uses individual skill keys |
<!-- END: readme:orchestration -->

#### Flights

<!-- BEGIN: readme:flights -->
| Skill | What It Does | API Key |
|-------|-------------|---------|
| **duffel** | Primary cash prices. Real GDS per-fare-class data. | Duffel |
| **google-flights** | Browser-automated Google Flights. All airlines including Southwest. | None (requires agent-browser) |
| **ignav** | Fast REST API cash prices. Market selection for arbitrage. | Ignav (1,000 free) |
| **seatmaps** | Aircraft seat maps, cabin dimensions, seat recommendations. | None (requires agent-browser) |
| **seats-aero** | Award availability across 27 mileage programs. | Seats.aero Pro/Partner |
| **southwest** | SW fare classes, points pricing, Companion Pass. Change flight price drop monitor. Docker: `ghcr.io/borski/sw-fares`. | None (requires Patchright) |
| **wikipedia-airports** | Route discovery and airline-service sanity check via Wikipedia airport pages. Answers "does carrier X fly A→B" and "what airports serve destination Y" when fare tools disagree or miss obscure regional service. No API key. | None |
<!-- END: readme:flights -->

#### Credit Card Travel Portals

<!-- BEGIN: readme:portals -->
| Skill | What It Does | API Key |
|-------|-------------|---------|
| **amex-travel** | Amex MR portal for flights, hotels, IAP discounts, FHR/THC benefits. Requires Platinum. Docker: `ghcr.io/borski/amex-travel`. | None (requires Patchright) |
| **bilt** | Bilt Rewards travel portal for hotels and flights. 1.25 cpp on Bilt Points. Home Away From Home properties give $300+ in benefits to Gold/Platinum members. | None (public API) |
| **chase-travel** | Chase UR portal for flights, hotels, Points Boost, Edit benefits. Requires Sapphire. Docker: `ghcr.io/borski/chase-travel`. | None (requires Patchright) |
<!-- END: readme:portals -->

#### Hotels and Accommodation

<!-- BEGIN: readme:hotels -->
| Skill | What It Does | API Key |
|-------|-------------|---------|
| **premium-hotels** | Search 4,659 Amex FHR/THC + Chase Edit hotels by city. Stacking opportunities. | None (local data) |
| **rapidapi** | Booking.com hotel prices. | RapidAPI |
| **serpapi** | Google Hotels search and destination discovery. | SerpAPI |
| **ticketsatwork** | TicketsAtWork (EBG) corporate-perks portal. Hotels, theme park tickets, attractions, live events. Often beats portals by 10-30%. Docker: `ghcr.io/borski/ticketsatwork`. | None (requires TaW account + Patchright) |
<!-- END: readme:hotels -->

Also use **tripadvisor** (under Destinations) for hotel ratings, rankings, subratings, and reviews.

#### Loyalty and Points

<!-- BEGIN: readme:loyalty -->
| Skill | What It Does | API Key |
|-------|-------------|---------|
| **american-airlines** | AAdvantage balance and elite status. AwardWallet does not support AA. Docker: `ghcr.io/borski/aa-miles-check`. | None (requires Patchright) |
| **awardwallet** | All loyalty balances, elite status, history. | AwardWallet Business |
| **transfer-partners** | Cheapest transfer path from credit card points to mileage programs. | None (local data) |
| **wheretocredit** | Mileage earning rates by airline and booking class across 50+ programs. | None (free) |
<!-- END: readme:loyalty -->

#### Destinations and Transit

<!-- BEGIN: readme:destinations -->
| Skill | What It Does | API Key |
|-------|-------------|---------|
| **atlas-obscura** | Hidden gems and unusual attractions near any destination. | None (free) |
| **deutsche-bahn** | Deutsche Bahn (DB) train search across Germany and into AT/CH/NL/FR/BE via the open-source db-vendo-client. Stations, journeys, departure boards. No API key. Pairs with scandinavia-transit for Europe-wide rail coverage. | None |
| **scandinavia-transit** | Trains, buses, ferries in Norway, Sweden, and Denmark. Includes Danish fare/zone pricing. | Entur + Trafiklab + Rejseplanen |
| **tripadvisor** | Hotel ratings, restaurant search, attraction reviews, nearby search. 5K calls/month. | TripAdvisor |
<!-- END: readme:destinations -->

#### Reference and Operations (auto-loaded on demand)

These skills carry the deep institutional knowledge that used to live in CLAUDE.md. They auto-load when the agent encounters relevant triggers, so the main config stays lean.

<!-- BEGIN: readme:reference -->
| Skill | What It Covers |
|-------|---------------|
| **alliances** | Star Alliance, oneworld, SkyTeam membership and recent shifts (SAS to SkyTeam, ITA to Star, Hawaiian/Fiji to oneworld). Key cross-alliance booking relationships. |
| **award-holds** | Per-program rules for placing award flight tickets on hold. Covers 6 programs with reliable holds (AA 24h online, LH 5 days, FB 3 days, CX 2 days, Turkish 2 days, Virgin Atlantic 1-2 days), Singapore as agent-discretionary, and the negative space (UA/AS/DL/Aeroplan/BA/ANA/Qatar/Korean - most programs do not allow holds). |
| **award-sweet-spots** | Catalog of legendary, excellent, and good award redemptions with current rates and devaluation history. |
| **booking-guidance** | The booking flow, hold-before-transfer rule, phone numbers for major programs. |
| **cabin-codes** | IATA cabin codes (F/J/W/Y) and saver fare class codes (X/I/O) for partner-bookable inventory. |
| **fallback-and-resilience** | What to do when each tool fails. Tool-by-tool fallback paths. |
| **flight-search-strategy** | The canonical multi-source search workflow. Source priority (Duffel > Ignav > Google Flights > others), market selection for international routes, source accuracy hierarchy, common failure modes. |
| **hotel-chains** | Maps brand names (Westin, Holiday Inn, etc.) to chain families and loyalty programs. |
| **lessons-learned** | Hard-won knowledge from real searches. The mandatory Seats.aero workflow, Southwest specifics, Companion Pass math, source accuracy, small-market caveats, Duffel limitations. Load before any award flight search. |
| **partner-awards** | Which programs ticket which airlines (alliance + bilateral). Cross-references credit card currencies to booking programs. Reachability workflow. |
| **points-valuations** | CPP formula, floor/ceiling rules, surcharge-heavy programs to avoid, transfer bonus considerations, Chase Points Boost dynamics, opportunity cost. |
| **round-the-world** | RTW + Pacific Circle + Asia-Pacific Circle + regional distance-award reference. 13 active programs, 4 discontinued. |
| **status-match** | Per-program status match rules with lifetime / once-per-N-years warnings, free vs paid concierge distinction, real fees, plus card-granted renewable status as the alternative. |
| **stopovers** | Per-program stopover rules for award redemptions. Includes Icelandair free stopover, Aeroplan, Alaska Atmos, Flying Blue, Singapore tiers, plus the negative space (BA, AA, Delta, JetBlue) that have no stopover programs. |
| **transfer-bonuses** | Active credit card transfer bonuses with primary-source citations. Tells the agent the real effective ratio when transferring points during a promotion. |
<!-- END: readme:reference -->

#### API Keys & Signup Links

<!-- BEGIN: readme:signup-links -->
These skills require an external account or API key signup. See [`.env.example`](.env.example) for the full list of env vars (some skills require an env var without a real signup, e.g. `scandinavia-transit` needs an `ENTUR_CLIENT_NAME` you choose yourself for Entur's required identification header).

| Skill | Service | Link | Notes |
|-------|---------|------|-------|
| `duffel` | Duffel | [duffel.com](https://duffel.com) | Real GDS flight search. Free tier available. |
| `ignav` | Ignav | [ignav.com](https://ignav.com) | Fast flight search REST API. 1,000 free requests, no credit card. |
| `seats-aero` | Seats.aero | [seats.aero](https://seats.aero) | Award flight availability across 27 mileage programs. Pro tier ($99/yr) includes API access. |
| `rapidapi` | RapidAPI | [rapidapi.com](https://rapidapi.com) | Marketplace; subscribe to Booking.com Live + Google Flights Live. |
| `serpapi` | SerpAPI | [serpapi.com](https://serpapi.com) | Google Flights, Google Hotels, Travel Explore. |
| `tripadvisor` | TripAdvisor | [www.tripadvisor.com/developers](https://www.tripadvisor.com/developers) | Hotel/restaurant/attraction data. 5K calls/month free. |
| `awardwallet` | AwardWallet | [business.awardwallet.com](https://business.awardwallet.com) | Loyalty program balance aggregator. Business tier required. |
| `ticketsatwork` | TicketsAtWork | [www.ticketsatwork.com](https://www.ticketsatwork.com) | Corporate-perks portal. Account requires employer affiliation. Same credentials work for Working Advantage, Plum, Beneplace (shared EBG backend). |
| `scandinavia-transit` | Trafiklab (Sweden) | [www.trafiklab.se](https://www.trafiklab.se) | Sweden transit. Free API key. 30,000 calls/month. |
| `scandinavia-transit` | Rejseplanen (Denmark) | [labs.rejseplanen.dk](https://labs.rejseplanen.dk) | Denmark transit. Free API key (application required). 50,000 calls/month, non-commercial only. |
<!-- END: readme:signup-links -->

## Docker Images

Five skills run as Docker containers (browser-automated via Patchright), plus a shared `patchright-docker` base image they all build on. All six images are public on GitHub Container Registry, no auth required to pull. `setup.sh` (and `setup.ps1` on Windows) auto-pulls the ones you need based on which tool you select.

<!-- BEGIN: readme:docker -->
| Image | Skill | Purpose | Source |
|-------|-------|---------|--------|
| [`ghcr.io/borski/patchright-docker`](https://github.com/borski/travel-hacking-toolkit/pkgs/container/patchright-docker) | (base) | Patchright + Chromium + xvfb base layer that all other browser-skill images build on. | [external](https://github.com/borski/patchright-docker) |
| [`ghcr.io/borski/aa-miles-check`](https://github.com/borski/travel-hacking-toolkit/pkgs/container/aa-miles-check) | `american-airlines` | AAdvantage balance and elite status. AwardWallet does not support AA. | [skills/american-airlines](skills/american-airlines/Dockerfile) |
| [`ghcr.io/borski/amex-travel`](https://github.com/borski/travel-hacking-toolkit/pkgs/container/amex-travel) | `amex-travel` | Amex MR portal for flights, hotels, IAP discounts, FHR/THC benefits. Requires Platinum. | [skills/amex-travel](skills/amex-travel/Dockerfile) |
| [`ghcr.io/borski/chase-travel`](https://github.com/borski/travel-hacking-toolkit/pkgs/container/chase-travel) | `chase-travel` | Chase UR portal for flights, hotels, Points Boost, Edit benefits. Requires Sapphire. | [skills/chase-travel](skills/chase-travel/Dockerfile) |
| [`ghcr.io/borski/sw-fares`](https://github.com/borski/travel-hacking-toolkit/pkgs/container/sw-fares) | `southwest` | SW fare classes, points pricing, Companion Pass. Change flight price drop monitor. | [skills/southwest](skills/southwest/Dockerfile) |
| [`ghcr.io/borski/ticketsatwork`](https://github.com/borski/travel-hacking-toolkit/pkgs/container/ticketsatwork) | `ticketsatwork` | TicketsAtWork (EBG) corporate-perks portal. Hotels, theme park tickets, attractions, live events. Often beats portals by 10-30%. | [skills/ticketsatwork](skills/ticketsatwork/Dockerfile) |
<!-- END: readme:docker -->

### Usage

```bash
# Southwest: fare search + price drop monitoring
docker pull ghcr.io/borski/sw-fares:latest
docker run --rm ghcr.io/borski/sw-fares --origin SJC --dest DEN --depart 2026-05-15 --points --json
docker run --rm -e SW_USERNAME -e SW_PASSWORD ghcr.io/borski/sw-fares \
    change --conf ABC123 --first Jane --last Doe --json

# American Airlines: AAdvantage balance + elite status (not in AwardWallet)
docker pull ghcr.io/borski/aa-miles-check:latest
docker run --rm -e AA_USERNAME=your_number -e AA_PASSWORD=your_pass ghcr.io/borski/aa-miles-check --json

# Chase Travel: UR portal pricing, Points Boost, Edit hotels
docker pull ghcr.io/borski/chase-travel:latest
docker run --rm -v ~/.chase-travel-profiles:/profiles -v /tmp:/tmp/host \
    -e CHASE_USERNAME -e CHASE_PASSWORD \
    ghcr.io/borski/chase-travel script /scripts/search_flights.py \
    --origin SFO --dest CDG --depart 2026-08-11 --cabin business --json

# Amex Travel: MR portal pricing, IAP discounts, FHR/THC hotels
docker pull ghcr.io/borski/amex-travel:latest
docker run --rm -v ~/.amex-travel-profiles:/profiles \
    -e AMEX_USERNAME -e AMEX_PASSWORD \
    ghcr.io/borski/amex-travel script /app/search_flights.py \
    --origin SFO --dest NRT --depart 2026-08-15 --cabin business --json

# TicketsAtWork (also covers Working Advantage / Plum / Beneplace)
docker pull ghcr.io/borski/ticketsatwork:latest
docker run --rm -e TAW_USER -e TAW_PASS ghcr.io/borski/ticketsatwork \
    hotels --location "Carlsbad, CA" --checkin 2027-03-04 --checkout 2027-03-07 --json
```

### Building Locally

To build any image locally instead of pulling from ghcr.io:

```bash
docker build -t ghcr.io/borski/<image-name>:local skills/<skill-name>/
```

The `Dockerfile` in each skill directory shows exactly what's in the image. All five skill images build on `ghcr.io/borski/patchright-docker` as the base.

## How It Works

### Skills

Skills are markdown files that give your AI specialized travel-hacking capabilities. They come in two flavors:

- **Tool skills** (`duffel`, `seats-aero`, `southwest`, etc.) wrap APIs, browser automation, and external tools. They contain endpoint documentation, curl examples, useful jq filters, and step-by-step usage instructions.
- **Reference skills** (`flight-search-strategy`, `points-valuations`, `alliances`, `lessons-learned`, etc.) carry the institutional knowledge that decides when and how to use the tool skills. They contain the workflow rules, lookup tables, and hard-won lessons that prevent common mistakes.

OpenCode, Claude Code, and Codex can all load them. Skills use **progressive disclosure**: each one's name and short description are loaded into context at session start. The agent reads the full SKILL.md only when it decides to use a skill. This keeps the always-loaded context small and lets the toolkit grow without bloating the agent's prompt.

The `skills/` directory is the canonical source. The setup script either:
- Installs a Codex plugin that points at the repo's skills and MCP config
- Copies them to your tool's global skills directory (`~/.config/opencode/skills/` or `~/.claude/skills/`)
- Or creates project-level symlinks so they load when you work from this directory

### MCP Servers

MCP (Model Context Protocol) servers give your AI real-time tools it can call directly. The configs are in:
- `opencode.json` for OpenCode (auto-discovered from the repo root)
- `.mcp.json` for Claude Code (auto-discovered from the repo root)
- `plugins/travel-hacking-toolkit/.mcp.json` for Codex plugin installs

Skiplagged, Kiwi.com, Trivago, Ferryhopper, and Airbnb need no setup at all. LiteAPI is also a remote server but needs an API key configured in your settings.

**Why Codex needs a plugin:** OpenCode and Claude Code both auto-discover MCP servers from a repo-local config file. Codex doesn't. It only loads MCP servers from `~/.codex/config.toml` or from an installed plugin. The toolkit ships a Codex plugin (under `plugins/travel-hacking-toolkit/`) that bundles the MCP config so Codex users get the same out-of-the-box experience as the other two tools. `setup.sh` wires this up automatically when you select the Codex option.

## Which Skill Do I Use?

```
"Plan a trip to Paris"
  └─→ trip-planner (runs everything below automatically)

"Find flights SFO to CDG"
  ├─ Know exact dates? → compare-flights (all sources in parallel)
  └─ Flexible dates?   → award-calendar (cheapest dates for a route)

"Find hotels in Paris"
  ├─ Best overall      → compare-hotels (portals + metasearch + Airbnb)
  ├─ Premium programs  → premium-hotels (FHR/THC/Edit)
  └─ Discount pricing  → ticketsatwork (often beats portals 10-30%)

"Should I use points or cash?"
  └─→ trip-calculator (CPP analysis + opportunity cost)
      Reference: points-valuations (floor/ceiling rules)

"Which of my points should I use?"
  └─→ transfer-partners (cheapest transfer path)
      Reference: partner-awards (cross-alliance reachability)

"Why is this redemption flagged as poor value?"
  └─→ Reference skills: points-valuations, alliances, award-sweet-spots

"Why am I not finding award space?"
  └─→ lessons-learned (THE mandatory Seats.aero workflow rules)

"A tool failed. Now what?"
  └─→ fallback-and-resilience (per-tool recovery paths)

"How do I actually book this?"
  └─→ booking-guidance (booking flow, phone numbers, hold-before-transfer rule)

"Check my SW reservations for price drops"
  └─→ southwest (change flight monitor)
```

The **orchestration skills** (`trip-planner`, `compare-flights`, `compare-hotels`) call the individual source skills automatically. Start with those unless you need a specific source.

The **reference skills** (`flight-search-strategy`, `points-valuations`, `partner-awards`, `alliances`, `award-sweet-spots`, `cabin-codes`, `hotel-chains`, `fallback-and-resilience`, `booking-guidance`, `lessons-learned`) auto-load on relevant context to provide deep institutional knowledge without you needing to invoke them explicitly.

## The Travel Hacking Workflow

The core question: **"Should I burn points or pay cash?"**

1. **Search ALL flight sources** — Duffel + Ignav + Google Flights + Skiplagged + Kiwi for cash. Seats.aero for awards. Southwest for SW points. Chase + Amex portals for pay-with-points.
2. **Optimize transfers** — `transfer-partners` finds the cheapest path from your credit card points to the loyalty program offering the best deal.
3. **Compare** — `trip-calculator` shows CPP for each option. Higher CPP = better use of points. Below floor valuation = pay cash instead.
4. **Check balances** — AwardWallet confirms you have enough points.
5. **Book it** — Use booking links from Seats.aero, Duffel, or Ignav. Don't transfer points until you've confirmed availability on the airline's site.

### Example Prompts

```
"Plan a trip to Paris Aug 11-15 in business class"
"Find me the cheapest business class award from SFO to Tokyo in August"
"When's the cheapest time to fly SFO to NRT on points?"
"Compare all options for SFO to CDG round trip"
"Find hotels in Stockholm, include Airbnb"
"Compare points vs cash for a round trip JFK to London next March"
"What are my United miles and Chase UR balances?"
"Check my Southwest reservations for price drops"
"Find hidden gems near Lisbon"
"How do I get from Oslo to Bergen by train?"
"What's the seat pitch on Air France 83 in business class?"
"How many AAdvantage miles do I have?"
"Which FHR and Chase Edit hotels are in Stockholm? Any stacking opportunities?"
"What's the Points Boost rate for SFO to Tokyo business class on Chase?"
"Compare Amex IAP fares vs cash for business class to Paris"
```

## Project Structure

```
travel-hacking-toolkit/
├── .claude-plugin/
│   ├── plugin.json                 # Claude Code plugin manifest (this is the install root)
│   └── marketplace.json            # Claude Code marketplace catalog
├── .agents/
│   ├── plugins/marketplace.json    # Codex marketplace catalog
│   └── skills -> ../skills         # Codex auto-discovery (no plugin install needed)
├── AGENTS.md -> CLAUDE.md          # OpenCode project instructions (symlink)
├── CLAUDE.md                       # Project instructions, agent system prompt (frontmatter at top)
├── agents/
│   └── travel-hacker.md            # Plugin agent file (auto-synced from CLAUDE.md)
├── opencode.json                   # OpenCode MCP server config
├── .mcp.json                       # Claude Code MCP server config
├── .env.example                    # API key template (OpenCode/Codex clone path)
├── .claude/
│   └── skills -> ../skills         # Symlink to skills
├── .opencode/
│   └── skills -> ../skills         # Symlink to skills
├── .github/workflows/
│   └── smoke-test.yml              # CI: runs scripts/smoke-test.sh --quick on PRs
├── plugins/
│   └── travel-hacking-toolkit/
│       ├── .codex-plugin/plugin.json # Codex plugin manifest
│       ├── .mcp.json                 # Codex MCP server config
│       └── skills -> ../../skills    # Codex skill bundle
├── data/
│   ├── alliances.json              # Airline alliance membership + booking relationships
│   ├── hotel-chains.json           # Hotel chains, sub-brands, loyalty programs, reverse lookup
│   ├── partner-awards.json         # Which programs book which airlines (alliance + bilateral)
│   ├── points-valuations.json      # Points/miles valuations from 4 sources (floor/ceiling)
│   ├── sweet-spots.json            # High-value award redemptions + booking windows
│   └── transfer-partners.json      # Credit card transfer partners + ratios
├── skills/
│   │
│   │  # ── Orchestration ──
│   ├── award-calendar/SKILL.md     # Cheapest award dates across a date range
│   ├── compare-flights/SKILL.md    # Unified flight comparison (all sources)
│   ├── compare-hotels/SKILL.md     # Unified hotel comparison (all sources)
│   ├── getting-started/SKILL.md    # First-run setup detector + signpost to setup-keys
│   ├── plan-trip/SKILL.md          # User-invoked guided trip planner (the hero command)
│   ├── trip-calculator/SKILL.md    # Cash vs points calculator
│   ├── trip-planner/SKILL.md       # Full trip planning in one shot
│   │
│   │  # ── Flights ──
│   ├── duffel/SKILL.md             # Primary cash prices (GDS)
│   ├── google-flights/SKILL.md     # Browser-automated Google Flights
│   ├── ignav/SKILL.md              # Secondary cash prices (REST API)
│   ├── seatmaps/SKILL.md           # Aircraft seat maps
│   ├── seats-aero/SKILL.md         # Award flight availability
│   ├── southwest/                  # Southwest fares + change monitoring
│   │   ├── SKILL.md
│   │   ├── Dockerfile
│   │   └── scripts/
│   │       ├── search_fares.py
│   │       ├── check_change.py
│   │       └── entrypoint.sh
│   │
│   │  # ── Credit Card Portals ──
│   ├── amex-travel/                # Amex MR portal (flights + hotels)
│   │   ├── SKILL.md
│   │   ├── Dockerfile
│   │   └── scripts/
│   │       └── search_flights.py
│   ├── chase-travel/               # Chase UR portal (flights + hotels)
│   │   ├── SKILL.md
│   │   ├── Dockerfile
│   │   └── scripts/
│   │       ├── search_flights.py
│   │       └── record_search.py
│   │
│   │  # ── Hotels ──
│   ├── premium-hotels/SKILL.md     # FHR/THC/Chase Edit local database
│   ├── rapidapi/SKILL.md           # Booking.com prices
│   ├── serpapi/SKILL.md            # Google Hotels + destination discovery
│   ├── ticketsatwork/              # TaW corporate-perks portal (hotels + tickets)
│   │   ├── SKILL.md
│   │   ├── Dockerfile
│   │   └── scripts/
│   │       ├── search_hotels.py
│   │       ├── search_cars.py
│   │       ├── browse_tickets.py
│   │       ├── taw_common.py
│   │       └── entrypoint.sh
│   │
│   │  # ── Loyalty ──
│   ├── american-airlines/          # AA AAdvantage balance
│   │   ├── SKILL.md
│   │   ├── Dockerfile
│   │   └── scripts/
│   │       └── check_balance.py
│   ├── awardwallet/SKILL.md        # All loyalty balances
│   ├── transfer-partners/SKILL.md  # Transfer path optimizer
│   ├── wheretocredit/SKILL.md      # Mileage earning rates
│   │
│   │  # ── Destinations & Transit ──
│   ├── atlas-obscura/              # Hidden gems (+ Node.js scraper)
│   │   ├── SKILL.md
│   │   ├── ao.mjs
│   │   └── package.json
│   ├── scandinavia-transit/SKILL.md # Nordic trains/buses/ferries
│   ├── tripadvisor/SKILL.md        # Ratings, reviews, nearby restaurants
│   │
│   │  # ── Reference & Operations (auto-load on demand) ──
│   ├── flight-search-strategy/SKILL.md  # Canonical multi-source search workflow
│   ├── points-valuations/SKILL.md       # CPP rules, surcharge programs, transfer bonuses
│   ├── partner-awards/SKILL.md          # Which programs ticket which airlines
│   ├── alliances/SKILL.md               # Star/oneworld/SkyTeam + cross-alliance plays
│   ├── award-sweet-spots/SKILL.md       # Legendary redemptions catalog
│   ├── cabin-codes/SKILL.md             # F/J/W/Y + saver fare classes (X/I/O)
│   ├── hotel-chains/SKILL.md            # Brand → loyalty program mapping
│   ├── fallback-and-resilience/SKILL.md # Tool failure recovery paths
│   ├── booking-guidance/SKILL.md        # Booking flow + phone numbers
│   └── lessons-learned/SKILL.md         # Hard-won knowledge from real searches
├── scripts/
│   ├── setup.sh                    # Interactive installer (macOS/Linux/WSL/Git Bash)
│   ├── setup.ps1                   # Interactive installer (Windows PowerShell)
│   ├── setup.cmd                   # Windows launcher (invokes setup.ps1)
│   ├── setup-keys.sh               # Standalone API key setup (no clone needed; curl|bash works)
│   ├── setup-keys.ps1              # Standalone API key setup (PowerShell)
│   ├── sync-agent.sh               # Copies CLAUDE.md to agents/travel-hacker.md (Claude plugin)
│   ├── install-hooks.sh            # Installs git hooks from scripts/hooks/ (run by setup.sh)
│   ├── smoke-test.sh               # Static + agent integration tests
│   ├── gen-skill-tables.sh         # Regenerates skill tables in README.md and llms.txt
│   ├── check-data-freshness.sh     # Validates data/*.json TTLs
│   └── hooks/
│       └── pre-commit              # Auto-syncs agents/travel-hacker.md when CLAUDE.md is staged
└── LICENSE                         # MIT
```

## Contributing

PRs welcome. The skill tables in this README and `llms.txt` are auto-generated from each skill's `SKILL.md` frontmatter — don't hand-edit them.

See [CONTRIBUTING.md](CONTRIBUTING.md) for: the skill addition flow, frontmatter rules, smoke test details, hard-rules list, and house style.

## Credits

- [Seats.aero](https://seats.aero) ([@seatsaero](https://github.com/seatsaero), [@iangcarroll](https://github.com/iangcarroll)) — The award-availability API that inspired this whole project. The only one of its kind. Hi Ian.
- [ajimix/travel-hacking-toolkit](https://github.com/ajimix/travel-hacking-toolkit) — Fork that contributed the google-flights skill, ignav skill, market selection strategy, and markdown table output formatting
- [美卡指南 (US Card Guide)](https://www.google.com/maps/d/viewer?mid=1HygPCP9ghtDptTNnpUpd_C507Mq_Fhec) by Scott — FHR/THC/Chase Edit hotel property data via Google My Maps KML

Other open-source projects, MCP servers, and APIs the toolkit depends on are linked inline in the [skill tables](#skills-api-knowledge-for-your-ai) above.

## License

MIT

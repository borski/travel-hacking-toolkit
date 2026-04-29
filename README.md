# Travel Hacking Toolkit

AI-powered travel hacking with points, miles, and award flights. Drop-in skills and MCP servers for [OpenCode](https://opencode.ai), [Claude Code](https://docs.anthropic.com/en/docs/claude-code), and [Codex](https://openai.com/codex/).

Ask your AI to find you a 60,000-mile business class flight to Tokyo. It'll search award availability across 25+ programs, compare against cash prices, check your loyalty balances, and tell you the best play.

## Quick Start

```bash
git clone https://github.com/borski/travel-hacking-toolkit.git
cd travel-hacking-toolkit

# macOS / Linux / WSL / Git Bash
./scripts/setup.sh

# Windows (PowerShell or cmd)
.\scripts\setup.cmd
```

The setup script walks you through everything: picks your tool (OpenCode, Claude Code, Codex, or all three), creates your API key config files, installs dependencies, installs the Codex plugin when selected, and optionally installs skills system-wide for OpenCode and Claude Code.

On Windows the `.cmd` wrapper launches `scripts\setup.ps1` with an ExecutionPolicy bypass so nothing needs to be unblocked first. You can also run the PowerShell script directly: `powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\setup.ps1`.

The 5 free MCP servers (Skiplagged, Kiwi, Trivago, Ferryhopper, Airbnb) work immediately with zero API keys. For the full experience, add at minimum:

| Key | Why | Free Tier |
|-----|-----|-----------|
| `SEATS_AERO_API_KEY` | Award flight search. The main event. | No (Pro ~$8/mo) |
| `DUFFEL_API_KEY_LIVE` | Primary cash flight prices. Real GDS data. | Yes (search free, pay per booking) |
| `IGNAV_API_KEY` | Secondary cash flight prices. Fast REST API. | Yes (1,000 free requests) |

Six skills run as optional Docker containers (Southwest, American Airlines, Chase, Amex, TicketsAtWork, plus a shared base image). `setup.sh` auto-pulls them when you select the relevant tools. See the [Docker Images](#docker-images) section for the full catalog and usage examples.

Then launch your tool:

```bash
# OpenCode
opencode

# Claude Code
claude --strict-mcp-config --mcp-config .mcp.json

# Codex
source .env && codex
```

The `--strict-mcp-config` flag tells Claude Code to load MCP servers from the config file directly. This is more reliable than auto-discovery ([known issue](https://github.com/anthropics/claude-code/issues/5037)).

For Codex, `./scripts/setup.sh` installs a local plugin symlink at `~/.codex/plugins/travel-hacking-toolkit` and adds a marketplace entry at `~/.agents/plugins/marketplace.json`. The plugin exposes the repo's `skills/` directory and the travel MCP servers as one installable bundle.

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
<!-- END: readme:flights -->

#### Credit Card Travel Portals

<!-- BEGIN: readme:portals -->
| Skill | What It Does | API Key |
|-------|-------------|---------|
| **amex-travel** | Amex MR portal for flights, hotels, IAP discounts, FHR/THC benefits. Requires Platinum. Docker: `ghcr.io/borski/amex-travel`. | None (requires Patchright) |
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
| **scandinavia-transit** | Trains, buses, ferries in Norway, Sweden, and Denmark. Includes Danish fare/zone pricing. | Entur + Trafiklab + Rejseplanen |
| **tripadvisor** | Hotel ratings, restaurant search, attraction reviews, nearby search. 5K calls/month. | TripAdvisor |
<!-- END: readme:destinations -->

#### Reference and Operations (auto-loaded on demand)

These skills carry the deep institutional knowledge that used to live in CLAUDE.md. They auto-load when the agent encounters relevant triggers, so the main config stays lean.

<!-- BEGIN: readme:reference -->
| Skill | What It Covers |
|-------|---------------|
| **alliances** | Star Alliance, oneworld, SkyTeam membership and recent shifts (SAS to SkyTeam, ITA to Star, Hawaiian/Fiji to oneworld). Key cross-alliance booking relationships. |
| **award-sweet-spots** | Catalog of legendary, excellent, and good award redemptions with current rates and devaluation history. |
| **booking-guidance** | The booking flow, hold-before-transfer rule, phone numbers for major programs. |
| **cabin-codes** | IATA cabin codes (F/J/W/Y) and saver fare class codes (X/I/O) for partner-bookable inventory. |
| **fallback-and-resilience** | What to do when each tool fails. Tool-by-tool fallback paths. |
| **flight-search-strategy** | The canonical multi-source search workflow. Source priority (Duffel > Ignav > Google Flights > others), market selection for international routes, source accuracy hierarchy, common failure modes. |
| **hotel-chains** | Maps brand names (Westin, Holiday Inn, etc.) to chain families and loyalty programs. |
| **lessons-learned** | Hard-won knowledge from real searches. The mandatory Seats.aero workflow, Southwest specifics, Companion Pass math, source accuracy, small-market caveats, Duffel limitations. Load before any award flight search. |
| **partner-awards** | Which programs ticket which airlines (alliance + bilateral). Cross-references credit card currencies to booking programs. Reachability workflow. |
| **points-valuations** | CPP formula, floor/ceiling rules, surcharge-heavy programs to avoid, transfer bonus considerations, Chase Points Boost dynamics, opportunity cost. |
<!-- END: readme:reference -->

#### API Keys & Signup Links

<!-- BEGIN: readme:signup-links -->
These skills require external accounts or installs. Skills not listed below need no signup.

| Skill | Service | Link | Notes |
|-------|---------|------|-------|
| `duffel` | Duffel | [duffel.com](https://duffel.com) | Real GDS flight search. Free tier available. |
| `ignav` | Ignav | [ignav.com](https://ignav.com) | Fast flight search REST API. 1,000 free requests, no credit card. |
| `seats-aero` | Seats.aero | [seats.aero](https://seats.aero) | Award flight availability across 27 mileage programs. Pro tier ($99/yr) includes API access. |
| `rapidapi` | RapidAPI | [rapidapi.com](https://rapidapi.com) | Marketplace; subscribe to Booking.com Live + Google Flights Live. |
| `serpapi` | SerpAPI | [serpapi.com](https://serpapi.com) | Google Flights, Google Hotels, Travel Explore. |
| `tripadvisor` | TripAdvisor | [www.tripadvisor.com/developers](https://www.tripadvisor.com/developers) | Hotel/restaurant/attraction data. 5K calls/month free. |
| `awardwallet` | AwardWallet | [business.awardwallet.com](https://business.awardwallet.com) | Loyalty program balance aggregator. Business tier required. |
| `google-flights` | agent-browser | [github.com/AidenLiminalAI/agent-browser](https://github.com/AidenLiminalAI/agent-browser) | Browser automation CLI. Install with npm. |
| `seatmaps` | agent-browser | [github.com/AidenLiminalAI/agent-browser](https://github.com/AidenLiminalAI/agent-browser) | Same agent-browser CLI as google-flights. |
| `southwest` | Patchright | [github.com/Kaliiiiiiiiii-Vinyzu/patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright) | Undetected Playwright fork. Auto-installed by Docker image. |
| `american-airlines` | Patchright | [github.com/Kaliiiiiiiiii-Vinyzu/patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright) | Same as southwest. Use the prebuilt Docker image. |
| `chase-travel` | Patchright | [github.com/Kaliiiiiiiiii-Vinyzu/patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright) | Same as southwest. Use the prebuilt Docker image. |
| `amex-travel` | Patchright | [github.com/Kaliiiiiiiiii-Vinyzu/patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright) | Same as southwest. Use the prebuilt Docker image. |
| `ticketsatwork` | Patchright + TaW account | [github.com/Kaliiiiiiiiii-Vinyzu/patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright) | Browser auto via Patchright. TaW credentials are corporate-perks accounts (also Working Advantage, Plum, Beneplace). |
| `scandinavia-transit` | Entur (Norway) | [developer.entur.org](https://developer.entur.org) | Norway transit. Free, no auth. |
| `scandinavia-transit` | Trafiklab (Sweden) | [www.trafiklab.se](https://www.trafiklab.se) | Sweden transit. Free with API key. |
| `scandinavia-transit` | Rejseplanen (Denmark) | [labs.rejseplanen.dk](https://labs.rejseplanen.dk) | Denmark transit. Free, no auth. |
<!-- END: readme:signup-links -->

## Docker Images

Six skills run as Docker containers (browser-automated via Patchright). All images are public on GitHub Container Registry, no auth required to pull. `setup.sh` (and `setup.ps1` on Windows) auto-pulls the ones you need based on which tool you select.

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
├── .agents/
│   ├── plugins/marketplace.json    # Repo-local Codex marketplace entry
│   └── skills -> ../skills         # Codex auto-discovery (no plugin install needed)
├── AGENTS.md -> CLAUDE.md          # OpenCode project instructions (symlink)
├── CLAUDE.md                       # Project instructions and workflow guidance
├── opencode.json                   # OpenCode MCP server config
├── .mcp.json                       # Claude Code MCP server config
├── .env.example                    # API key template (OpenCode/Codex)
├── .claude/
│   ├── settings.local.json.example # API key template (Claude Code)
│   └── skills -> ../skills         # Symlink to skills
├── .opencode/
│   └── skills -> ../skills         # Symlink to skills
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
│   └── setup.cmd                   # Windows launcher (invokes setup.ps1)
└── LICENSE                         # MIT
```

## Smoke Testing

After any change to skills, CLAUDE.md, or MCP config, run the three-way smoke test:

```bash
bash scripts/smoke-test.sh           # full test (static + all 3 agents, ~3-5 min)
bash scripts/smoke-test.sh --quick   # static checks only (no agent invocations)
bash scripts/smoke-test.sh --agents  # agent invocations only
```

What it verifies:
1. `setup.sh` and `setup.ps1` syntax parse cleanly
2. Every skill has valid `name` + `description` frontmatter
3. CLAUDE.md is under Claude Code's 40k char warning threshold
4. All Docker images exist on ghcr.io
5. All data files are within their declared TTL
6. README.md and llms.txt skill tables match the generated output (no drift)
7. Each agent (codex, claude, opencode) starts cleanly from the toolkit
8. Each agent picks the right skills (`lessons-learned` + `flight-search-strategy` minimum) for a real travel question

Missing CLIs are skipped, not failed. Run from the repo root.

### Skill Table Generation

The skill tables in this README and `llms.txt` are auto-generated from each skill's `SKILL.md` frontmatter. The fields used:

- `name` — required, the skill identifier
- `category` — required, one of: `orchestration`, `flights`, `portals`, `hotels`, `loyalty`, `destinations`, `reference`
- `summary` — required, the one-liner shown in tables and llms.txt
- `api_key` — optional, short text for the API Key column (e.g., `Duffel`, `None (free)`)
- `docker_image` — optional, full image name like `ghcr.io/borski/sw-fares` if the skill ships a Docker image

To add a new skill, edit `scripts/skill-meta.tsv` and run:

```bash
python3 scripts/sync-skill-frontmatter.py   # apply TSV to SKILL.md frontmatter
bash scripts/gen-skill-tables.sh            # regenerate README + llms.txt
```

Drift between the source (frontmatter / TSV) and the generated tables is caught by `smoke-test.sh`, which fails if running `--check` would produce a diff. This makes drift a CI failure, not a silent issue.

## Contributing

PRs welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the skill addition flow, frontmatter rules, smoke test expectations, and house style.

## Credits

- [Seats.aero](https://seats.aero) ([@seatsaero](https://github.com/seatsaero), [@iangcarroll](https://github.com/iangcarroll)) — The award-availability API that inspired this whole project. The only one of its kind. Hi Ian.
- [ajimix/travel-hacking-toolkit](https://github.com/ajimix/travel-hacking-toolkit) — Fork that contributed the google-flights skill, ignav skill, market selection strategy, and markdown table output formatting
- [美卡指南 (US Card Guide)](https://www.google.com/maps/d/viewer?mid=1HygPCP9ghtDptTNnpUpd_C507Mq_Fhec) by Scott — FHR/THC/Chase Edit hotel property data via Google My Maps KML

Other open-source projects, MCP servers, and APIs the toolkit depends on are linked inline in the [skill tables](#skills-api-knowledge-for-your-ai) above.

## License

MIT

# Travel Hacking Toolkit

AI-powered travel hacking with points, miles, and award flights. Drop-in skills and MCP servers for [OpenCode](https://opencode.ai) and [Claude Code](https://docs.anthropic.com/en/docs/claude-code).

Ask your AI to find you a 60,000-mile business class flight to Tokyo. It'll search award availability across 25+ programs, compare against cash prices, check your loyalty balances, and tell you the best play.

## Quick Start

```bash
git clone https://github.com/borski/travel-hacking-toolkit.git
cd travel-hacking-toolkit
./scripts/setup.sh
```

The setup script walks you through everything: picks your tool (OpenCode, Claude Code, or both), creates your API key config files, installs dependencies, and optionally installs skills system-wide.

The 5 free MCP servers (Skiplagged, Kiwi, Trivago, Ferryhopper, Airbnb) work immediately with zero API keys. For the full experience, add at minimum:

| Key | Why | Free Tier |
|-----|-----|-----------|
| `SEATS_AERO_API_KEY` | Award flight search. The main event. | No (Pro ~$8/mo) |
| `SERPAPI_API_KEY` | Cash price comparison for "points or cash?" decisions | Yes (100 searches/mo) |

For the Southwest skill (optional), pull the pre-built Docker image:

```bash
docker pull ghcr.io/borski/sw-fares:latest

# Search new flights
docker run --rm ghcr.io/borski/sw-fares --origin SJC --dest DEN --depart 2026-05-15 --points --json

# Monitor existing reservations for price drops (requires SW login)
docker run --rm -e SW_USERNAME -e SW_PASSWORD ghcr.io/borski/sw-fares change --list --json
docker run --rm -e SW_USERNAME -e SW_PASSWORD ghcr.io/borski/sw-fares change --conf ABC123 --first Jane --last Doe --json
```

Then launch your tool:

```bash
# OpenCode
opencode

# Claude Code
claude --strict-mcp-config --mcp-config .mcp.json
```

The `--strict-mcp-config` flag tells Claude Code to load MCP servers from the config file directly. This is more reliable than auto-discovery ([known issue](https://github.com/anthropics/claude-code/issues/5037)).

## What's Included

### MCP Servers (real-time tools)

| Server | What It Does | API Key |
|--------|-------------|---------|
| [Skiplagged](https://skiplagged.com) | Flight search with hidden city fares | None (free) |
| [Kiwi.com](https://www.kiwi.com) | Flights with virtual interlining (creative cross-airline routing) | None (free) |
| [Trivago](https://mcp.trivago.com/docs) | Hotel metasearch across booking sites | None (free) |
| [Ferryhopper](https://ferryhopper.github.io/fh-mcp/) | Ferry routes across 33 countries, 190+ operators | None (free) |
| [Airbnb](https://github.com/borski/mcp-server-airbnb) | Search Airbnb listings, property details, pricing. Patched with geocoding fix and property type filter. | None (free) |
| [LiteAPI](https://mcp.liteapi.travel) | Hotel search with live rates and booking | [LiteAPI](https://liteapi.travel) |

### Skills (API knowledge for your AI)

| Skill | What It Does | API Key |
|-------|-------------|---------|
| **google-flights** | Browser-automated Google Flights search. Covers ALL airlines including Southwest. | None (free, requires [agent-browser](https://github.com/AidenLiminalAI/agent-browser)) |
| **ignav** | Fast REST API flight search with booking links. Market selection for price arbitrage. | [Ignav](https://ignav.com) (1,000 free) |
| **southwest** | Southwest.com fare classes, points pricing, Companion Pass data. All 4 fare classes, cash + points. Includes logged-in change flight monitor to catch price drops on existing reservations. | None (free, requires [Patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright). Docker support included.) |
| **duffel** | Real-time GDS flight search across airlines via Duffel API | [Duffel](https://duffel.com) |
| **seats-aero** | Award flight availability across 25+ mileage programs | [Seats.aero](https://seats.aero) Pro/Partner |
| **awardwallet** | Loyalty program balances, elite status, history | [AwardWallet](https://business.awardwallet.com) Business |
| **serpapi** | Google Hotels search and destination discovery. Optional (not needed for flights). | [SerpAPI](https://serpapi.com) |
| **rapidapi** | Booking.com hotel prices. Optional. | [RapidAPI](https://rapidapi.com) |
| **atlas-obscura** | Hidden gems near any destination | None (free) |
| **scandinavia-transit** | Trains, buses, ferries in Norway/Sweden/Denmark | [Entur](https://developer.entur.org) + [Trafiklab](https://www.trafiklab.se) |
| **wheretocredit** | Mileage earning rates by airline and booking class across 50+ FF programs | None (free) |

## How It Works

### Skills

Skills are markdown files that teach your AI how to call travel APIs. They contain endpoint documentation, curl examples, useful jq filters, and workflow guidance. Both OpenCode and Claude Code support skills natively.

The `skills/` directory is the canonical source. The setup script either:
- Copies them to your tool's global skills directory (`~/.config/opencode/skills/` or `~/.claude/skills/`)
- Or creates project-level symlinks so they load when you work from this directory

### MCP Servers

MCP (Model Context Protocol) servers give your AI real-time tools it can call directly. The configs are in:
- `opencode.json` for OpenCode
- `.mcp.json` for Claude Code

Skiplagged, Kiwi.com, Trivago, Ferryhopper, and Airbnb need no setup at all. LiteAPI is also a remote server but needs an API key configured in your settings.

## The Travel Hacking Workflow

The core question: **"Should I burn points or pay cash?"**

1. **Search ALL flight sources** — Duffel + Ignav + Google Flights + Skiplagged + Kiwi for cash prices. Seats.aero for award availability. Southwest skill for SW-specific fare classes and points.
2. **Estimate portal value** — Portal rates are dynamic now. Chase "Points Boost" (June 2025) offers 1.5 to 2.0cpp on select bookings, not a flat rate. Amex/Capital One ~1.0cpp. Check the actual portal for your specific booking.
3. **Compare** — Lower number wins
4. **Check balances** — AwardWallet confirms you have enough
5. **Book it** — Use booking links from Seats.aero, Duffel, or Ignav

### Example Prompts

```
"Find me the cheapest business class award from SFO to Tokyo in August"
"Compare points vs cash for a round trip JFK to London next March"
"What are my United miles and Chase UR balances?"
"Check my Southwest reservations for price drops"
"Find hidden gems near Lisbon"
"How do I get from Oslo to Bergen by train?"
```

## Project Structure

```
travel-hacking-toolkit/
├── AGENTS.md -> CLAUDE.md          # OpenCode project instructions (symlink)
├── CLAUDE.md                       # Project instructions and workflow guidance
├── opencode.json                   # OpenCode MCP server config
├── .mcp.json                       # Claude Code MCP server config
├── .env.example                    # API key template (OpenCode)
├── .claude/
│   ├── settings.local.json.example # API key template (Claude Code)
│   └── skills -> ../skills         # Symlink to skills
├── .opencode/
│   └── skills -> ../skills         # Symlink to skills
├── data/
│   ├── alliances.json              # Airline alliance membership + booking relationships
│   ├── hotel-chains.json           # Hotel chains, sub-brands, loyalty programs, reverse lookup
│   ├── partner-awards.json         # Which programs book which airlines (alliance + bilateral)
│   ├── points-valuations.json      # Points/miles valuations from 4 sources (floor/ceiling)
│   ├── sweet-spots.json            # High-value award redemptions + booking windows
│   └── transfer-partners.json      # Credit card transfer partners + ratios
├── skills/
│   ├── duffel/SKILL.md             # Real-time flight search
│   ├── seats-aero/SKILL.md         # Award flight search
│   ├── awardwallet/SKILL.md        # Loyalty balances
│   ├── serpapi/SKILL.md            # Cash prices + hotels
│   ├── rapidapi/SKILL.md           # Secondary price source
│   ├── atlas-obscura/              # Hidden gems (+ Node.js scraper)
│   │   ├── SKILL.md
│   │   ├── ao.mjs
│   │   └── package.json
│   ├── southwest/                  # Southwest fares + change monitoring
│   │   ├── SKILL.md
│   │   ├── Dockerfile
│   │   └── scripts/
│   │       ├── search_fares.py     # New flight search
│   │       ├── check_change.py     # Logged-in price drop monitor (read-only)
│   │       └── entrypoint.sh       # Docker entrypoint (routes search/change)
│   └── scandinavia-transit/        # Nordic trains/buses/ferries
│       └── SKILL.md
├── scripts/
│   └── setup.sh                    # Interactive installer
└── LICENSE                         # MIT
```

## Credits

- [ajimix/travel-hacking-toolkit](https://github.com/ajimix/travel-hacking-toolkit) — Fork that contributed the google-flights skill, ignav skill, market selection strategy, and markdown table output formatting
- [Patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright) by [@Vinyzu](https://github.com/Vinyzu) — Undetected Playwright fork that makes the Southwest skill possible
- [美卡指南 (US Card Guide)](https://www.google.com/maps/d/viewer?mid=1HygPCP9ghtDptTNnpUpd_C507Mq_Fhec) by Scott — FHR/THC/Chase Edit hotel property data via Google My Maps KML
- [Seats.aero](https://seats.aero) — Award flight availability data
- [AwardWallet](https://awardwallet.com) — Loyalty program tracking
- [Duffel](https://duffel.com) — Real-time flight search and booking
- [SerpAPI](https://serpapi.com) — Google search result APIs
- [RapidAPI](https://rapidapi.com) — API marketplace
- [atlas-obscura-api](https://github.com/bartholomej/atlas-obscura-api) by [@bartholomej](https://github.com/bartholomej) — Atlas Obscura scraper
- [Skiplagged MCP](https://mcp.skiplagged.com) — Flight search with hidden city fares
- [Kiwi.com MCP](https://www.kiwi.com/stories/kiwi-mcp-connector/) — Flight search with virtual interlining
- [Trivago MCP](https://mcp.trivago.com/docs) — Hotel metasearch
- [Ferryhopper MCP](https://ferryhopper.github.io/fh-mcp/) by [Ferryhopper](https://ferryhopper.com) — Ferry routes across 33 countries
- [mcp-server-airbnb](https://github.com/openbnb-org/mcp-server-airbnb) by [OpenBnB](https://github.com/openbnb-org) — Airbnb search and listing details
- [LiteAPI MCP](https://mcp.liteapi.travel) by [LiteAPI](https://liteapi.travel) — Hotel booking
- [Entur](https://developer.entur.org) — Norwegian transit API
- [Trafiklab / ResRobot](https://www.trafiklab.se) — Swedish transit API
- [Rejseplanen](https://labs.rejseplanen.dk) — Danish transit API

## License

MIT

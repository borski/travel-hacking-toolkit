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

The 6 free MCP servers (Skiplagged, Kiwi, Trivago, Ferryhopper, Airbnb, FlightSeatMap) work immediately with zero API keys. For the full experience, add at minimum:

| Key | Why | Free Tier |
|-----|-----|-----------|
| `SEATS_AERO_API_KEY` | Award flight search. The main event. | No (Pro ~$8/mo) |
| `DUFFEL_API_KEY_LIVE` | Primary cash flight prices. Real GDS data. | Yes (search free, pay per booking) |
| `IGNAV_API_KEY` | Secondary cash flight prices. Fast REST API. | Yes (1,000 free requests) |

For the Southwest and American Airlines skills (optional), pull the pre-built Docker images:

```bash
# Southwest: fare search + price drop monitoring
docker pull ghcr.io/borski/sw-fares:latest
docker run --rm ghcr.io/borski/sw-fares --origin SJC --dest DEN --depart 2026-05-15 --points --json
docker run --rm -e SW_USERNAME -e SW_PASSWORD ghcr.io/borski/sw-fares change --conf ABC123 --first Jane --last Doe --json

# American Airlines: AAdvantage balance + elite status (not in AwardWallet)
docker pull ghcr.io/borski/aa-miles-check:latest
docker run --rm -e AA_USERNAME=your_number -e AA_PASSWORD=your_pass ghcr.io/borski/aa-miles-check --json
```

For the Chase and Amex Travel portal skills (optional), pull pre-built Docker images:

```bash
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
| [Airbnb](https://github.com/openbnb-org/mcp-server-airbnb) | Search Airbnb listings, property details, pricing. Includes geocoding fix, property type filter, and DISABLE_GEOCODING opt-out. | None (free) |
| [FlightSeatMap](https://mcp.flightseatmap.com) | Aircraft seat maps, preference-based seat scoring, and seat recommendations by flight number | None (free) |
| [LiteAPI](https://mcp.liteapi.travel) | Hotel search with live rates and booking | [LiteAPI](https://liteapi.travel) |

### Skills (API knowledge for your AI)

Start here: the **orchestration skills** call everything else automatically.

#### Orchestration

| Skill | What It Does | API Key |
|-------|-------------|---------|
| **award-calendar** | Cheapest award dates for a route across a date range. Calendar grid view. | Seats.aero Pro |
| **compare-flights** | Unified flight comparison across ALL sources in parallel. Auto-applies transfer optimization. | Uses individual skill keys |
| **compare-hotels** | Unified hotel comparison across portals, metasearch, and Airbnb. FHR/Edit stacking detection. | Uses individual skill keys |
| **trip-calculator** | "Cash or points?" answered with math. Transfer ratios, taxes, opportunity cost. | None (free, local data) |
| **trip-planner** | Full trip planning: flights + hotels + points in one shot. | Uses individual skill keys |

#### Flights

| Skill | What It Does | API Key |
|-------|-------------|---------|
| **duffel** | Primary cash prices. Real GDS per-fare-class data. | [Duffel](https://duffel.com) |
| **google-flights** | Browser-automated Google Flights. All airlines including Southwest. | None (requires [agent-browser](https://github.com/AidenLiminalAI/agent-browser)) |
| **ignav** | Fast REST API cash prices. Market selection for arbitrage. | [Ignav](https://ignav.com) (1,000 free) |
| **seats-aero** | Award availability across 25+ mileage programs. | [Seats.aero](https://seats.aero) Pro/Partner |
| **seatmaps** | Aircraft seat maps, cabin dimensions, seat recommendations. | None (requires [agent-browser](https://github.com/AidenLiminalAI/agent-browser)) |
| **southwest** | SW fare classes, points pricing, Companion Pass. Change flight price drop monitor. Docker: `ghcr.io/borski/sw-fares`. | None (requires [Patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright)) |

#### Credit Card Travel Portals

| Skill | What It Does | API Key |
|-------|-------------|---------|
| **amex-travel** | Amex MR portal: flights, hotels, IAP discounts, FHR/THC benefits. Requires Platinum. Docker: `ghcr.io/borski/amex-travel`. | None (requires [Patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright)) |
| **chase-travel** | Chase UR portal: flights, hotels, Points Boost, Edit benefits. Requires Sapphire. Docker: `ghcr.io/borski/chase-travel`. | None (requires [Patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright)) |

#### Hotels and Accommodation

| Skill | What It Does | API Key |
|-------|-------------|---------|
| **premium-hotels** | Search 4,659 Amex FHR/THC + Chase Edit hotels by city. Stacking opportunities. | None (local data) |
| **rapidapi** | Booking.com hotel prices. | [RapidAPI](https://rapidapi.com) |
| **serpapi** | Google Hotels search and destination discovery. | [SerpAPI](https://serpapi.com) |
| **ticketsatwork** | TicketsAtWork (EBG) corporate-perks portal: hotels, theme park tickets, attractions, live events. Often beats portals by 10-30%. Docker: `ghcr.io/borski/ticketsatwork`. | None (requires TaW account + [Patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright)) |

Also use **tripadvisor** (under Destinations) for hotel ratings, rankings, subratings, and reviews.

#### Loyalty and Points

| Skill | What It Does | API Key |
|-------|-------------|---------|
| **american-airlines** | AAdvantage balance and elite status. AwardWallet doesn't support AA. Docker: `ghcr.io/borski/aa-miles-check`. | None (requires [Patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright)) |
| **awardwallet** | All loyalty balances, elite status, history. | [AwardWallet](https://business.awardwallet.com) Business |
| **transfer-partners** | Cheapest transfer path from credit card points to mileage programs. | None (local data) |
| **wheretocredit** | Mileage earning rates by airline and booking class across 50+ programs. | None (free) |

#### Destinations and Transit

| Skill | What It Does | API Key |
|-------|-------------|---------|
| **atlas-obscura** | Hidden gems and unusual attractions near any destination. | None (free) |
| **scandinavia-transit** | Trains, buses, ferries in Norway, Sweden, and Denmark. Includes Danish fare/zone pricing. | [Entur](https://developer.entur.org) + [Trafiklab](https://www.trafiklab.se) + [Rejseplanen](https://labs.rejseplanen.dk) |
| **tripadvisor** | Hotel ratings, restaurant search, attraction reviews, nearby search. 5K calls/month. | [TripAdvisor](https://www.tripadvisor.com/developers) |

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

## Which Skill Do I Use?

```
"Plan a trip to Paris"
  └─→ trip-planner (runs everything below automatically)

"Find flights SFO to CDG"
  ├─ Know exact dates? → compare-flights (all sources in parallel)
  └─ Flexible dates? → award-calendar (cheapest dates for a route)

"Find hotels in Paris"
  └─→ compare-hotels (portals + metasearch + Airbnb)

"Should I use points or cash?"
  └─→ trip-calculator (CPP analysis + opportunity cost)

"Which of my points should I use?"
  └─→ transfer-partners (cheapest transfer path)

"Which FHR/Edit hotels are in Stockholm?"
  └─→ premium-hotels (local data, instant)

"Check my SW reservations for price drops"
  └─→ southwest (change flight monitor)
```

The **orchestration skills** (`trip-planner`, `compare-flights`, `compare-hotels`) call the individual source skills automatically. Start with those unless you need a specific source.

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
│   └── tripadvisor/SKILL.md        # Ratings, reviews, nearby restaurants
├── scripts/
│   └── setup.sh                    # Interactive installer
└── LICENSE                         # MIT
```

## Credits

- [ajimix/travel-hacking-toolkit](https://github.com/ajimix/travel-hacking-toolkit) — Fork that contributed the google-flights skill, ignav skill, market selection strategy, and markdown table output formatting
- [Patchright](https://github.com/Kaliiiiiiiiii-Vinyzu/patchright) by [@Vinyzu](https://github.com/Vinyzu) — Undetected Playwright fork that makes the Southwest skill possible
- [美卡指南 (US Card Guide)](https://www.google.com/maps/d/viewer?mid=1HygPCP9ghtDptTNnpUpd_C507Mq_Fhec) by Scott — FHR/THC/Chase Edit hotel property data via Google My Maps KML
- [SeatMaps.com](https://seatmaps.com) by [Quicket GmbH](https://quicket.io) — Aircraft seat maps, cabin data, seat recommendations
- [AeroLOPA](https://www.aerolopa.com/) — Detailed to-scale aircraft seat maps with window positions
- [Seats.aero](https://seats.aero) — Award flight availability data
- [AwardWallet](https://awardwallet.com) — Loyalty program tracking
- [Duffel](https://duffel.com) — Real-time flight search and booking
- [SerpAPI](https://serpapi.com) — Google search result APIs
- [RapidAPI](https://rapidapi.com) — API marketplace
- [atlas-obscura-api](https://github.com/bartholomej/atlas-obscura-api) by [@bartholomej](https://github.com/bartholomej) — Atlas Obscura scraper
- [FlightSeatMap MCP](https://mcp.flightseatmap.com) by [FlightSeatMap](https://flightseatmap.com) — Aircraft seat maps with preference-based scoring
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

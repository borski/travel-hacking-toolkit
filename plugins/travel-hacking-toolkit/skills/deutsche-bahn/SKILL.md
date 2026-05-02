---
name: deutsche-bahn
description: Deutsche Bahn train schedules, journey planning, and departures across Germany and into neighboring countries (Austria, Switzerland, Netherlands, France, Belgium). Use for ICE/IC/regional rail planning and airport ground transport (FRA, MUC).
category: destinations
summary: Deutsche Bahn (DB) train search across Germany and into AT/CH/NL/FR/BE via the open-source db-vendo-client. Stations, journeys, departure boards. No API key. Pairs with scandinavia-transit for Europe-wide rail coverage.
license: MIT
---

# Deutsche Bahn Skill

Search German train schedules and plan journeys using the `db-vendo-client` library (open-source client for bahn.de APIs).

**No API key required.** No Docker. Just Node.js.

**Source:** [db-vendo-client](https://github.com/public-transport/db-vendo-client) — wraps bahn.de's internal APIs.

## Setup

```bash
cd skills/deutsche-bahn && npm install
```

## Commands

### Station Search

Find station IDs by name:

```bash
node skills/deutsche-bahn/scripts/search_trains.mjs stations "Frankfurt Flughafen"
```

### Journey Planning

Search train routes between two stations (by ID or name):

```bash
# By station ID
node skills/deutsche-bahn/scripts/search_trains.mjs journeys 8070003 8000376 --date 2026-05-05 --time 10:00 --results 5

# By station name (auto-resolves to ID)
node skills/deutsche-bahn/scripts/search_trains.mjs journeys "Frankfurt Airport" "Germersheim" --date 2026-05-05
node skills/deutsche-bahn/scripts/search_trains.mjs journeys "Amsterdam Centraal" "Mannheim Hbf" --date 2026-05-15 --time 09:00
node skills/deutsche-bahn/scripts/search_trains.mjs journeys "Paris Est" "Mannheim" --date 2026-05-05
```

### Departure Board

Check upcoming departures from any station:

```bash
node skills/deutsche-bahn/scripts/search_trains.mjs departures "Mannheim Hbf" --results 10
node skills/deutsche-bahn/scripts/search_trains.mjs departures 8070003 --date 2026-05-05 --time 14:00
```

## Key Station IDs

### German Airports

| Airport | Station ID | Station Name | Notes |
|---------|-----------|--------------|-------|
| Frankfurt (FRA) | `8070003` | Frankfurt(M) Flughafen Fernbf | Long-distance (ICE/TGV) |
| Frankfurt (FRA) | `8070004` | Frankfurt(M) Flughafen Regionalbf | Regional trains |
| Munich (MUC) | `8004154` | München Flughafen Terminal | S-Bahn to München Hbf |
| Düsseldorf (DUS) | `8001585` | Düsseldorf Flughafen | S-Bahn + RE |
| Cologne/Bonn (CGN) | `8003330` | Köln/Bonn Flughafen | ICE station |
| Berlin (BER) | `8089021` | Flughafen BER Terminal 1-2 | FEX + RE + S-Bahn |
| Stuttgart (STR) | `8005773` | Flughafen/Messe | S-Bahn to Stuttgart Hbf |
| Hamburg (HAM) | `8002549` | Hamburg Airport | S-Bahn |

### Major Stations

| City | Station ID | Name |
|------|-----------|------|
| Frankfurt Hbf | `8000105` | Frankfurt(Main)Hbf |
| Mannheim Hbf | `8000244` | Mannheim Hbf |
| Germersheim | `8000376` | Germersheim |
| Karlsruhe Hbf | `8000191` | Karlsruhe Hbf |
| Stuttgart Hbf | `8000096` | Stuttgart Hbf |
| München Hbf | `8000261` | München Hbf |
| Berlin Hbf | `8011160` | Berlin Hbf |
| Köln Hbf | `8000207` | Köln Hbf |
| Düsseldorf Hbf | `8000085` | Düsseldorf Hbf |
| Hamburg Hbf | `8002549` | Hamburg Hbf |
| Heidelberg Hbf | `8000156` | Heidelberg Hbf |
| Speyer Hbf | `8000076` | Speyer Hbf |

### International Stations (reachable by DB trains)

| City | Station ID | Name | Train from Germany |
|------|-----------|------|-------------------|
| Amsterdam Centraal | `8400058` | Amsterdam Centraal | ICE from Frankfurt ~4h |
| Paris Est | `8700011` | Paris Est | TGV/ICE from Frankfurt ~4h |
| Zürich HB | `8503000` | Zürich HB | ICE from Frankfurt ~4h |
| Basel SBB | `8500010` | Basel SBB | ICE from Mannheim ~2.5h |
| Strasbourg | `8700018` | Strasbourg | TGV/RE from Karlsruhe ~40min |
| Brussels Midi | `8814001` | Bruxelles-Midi/Brussel-Zuid | ICE from Frankfurt ~3.5h |
| Wien Hbf | `8100003` | Wien Hbf | ICE from München ~4h |
| Praha hl.n. | `5400014` | Praha hlavní nádraží | EC from München/Berlin |

## Common Airport-to-Germersheim Routes

| From Airport | Route | Typical Duration | Transfers |
|-------------|-------|-----------------|-----------|
| **Frankfurt (FRA)** | ICE → Mannheim → S3 Germersheim | **78–105 min** | 1 |
| Stuttgart (STR) | S-Bahn → Stuttgart Hbf → ICE Mannheim → S3 | ~2h 30m | 2 |
| Munich (MUC) | S-Bahn → München Hbf → ICE Mannheim → S3 | ~3h 45m | 2 |
| Paris CDG | RER → Paris Est → TGV Mannheim → S3 | ~4h 30m | 2-3 |
| Amsterdam (AMS) | Train → Amsterdam CS → ICE Mannheim → S3 | ~5h | 2 |
| Zürich (ZRH) | Train → Zürich HB → ICE Mannheim → S3 | ~4h | 2 |

## Parameters

| Param | Flag | Default | Description |
|-------|------|---------|-------------|
| Date | `--date` | Today | YYYY-MM-DD format |
| Time | `--time` | 08:00 | HH:MM, departure time |
| Results | `--results` | 5 (journeys), 10 (departures) | Number of results |

## Coverage

- **All German trains:** ICE, IC/EC, RE, RB, S-Bahn
- **International:** ICE to AMS/Brussels/Paris/Zürich/Wien, TGV to Paris, Eurostar connections
- **Local transit:** S-Bahn, U-Bahn, trams, buses (if DB data includes them)

## Limitations

- **No pricing.** DB does not expose ticket prices via API. For fares, check bahn.de directly or use the Trainline API.
- **Rate limits.** DB's backend enforces low rate limits. Keep queries reasonable (a few per minute, not hundreds).
- **Schedule data only.** Real-time delays are shown when available, but historical data is not retained.
- **Future schedules.** DB typically publishes schedules ~6 months out. Dates beyond that may return no results.

## When to Use

Load this skill when:
- Planning train connections from a European gateway airport to a destination in Germany
- Checking ICE/TGV schedules between major cities
- Finding last-mile S-Bahn/regional connections (e.g., Mannheim → Germersheim)
- Comparing train travel time from different airports to decide which to fly into
- Looking up departure boards at a station

Do NOT use for:
- Booking tickets (search only — book at bahn.de or trainline.com)
- Flight searches (use Duffel, Ignav, Skiplagged, etc.)
- Pricing (not available via API)

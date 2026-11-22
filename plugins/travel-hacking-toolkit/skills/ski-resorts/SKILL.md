---
name: ski-resorts
description: Search the top 1000 global downhill ski resorts by airport crow-flies proximity, elevation, hemisphere, multi-resort pass, and lift-ticket price tier, plus live current snow depth and 1-2 week forecasts. Use when the user asks about ski vacations, ski resorts near an airport, cheap ski trips, or pass-affiliated ski destinations.
category: destinations
summary: Top 1000 global ski resorts by airport proximity, passes, price tier, and live snow forecasts.
api_key: None (free, local data and Open-Meteo)
---

# Ski Resorts

Discover and filter the **top 1,000 global downhill ski resorts** (`data/ski-resorts.json`) by crow-flies airport proximity, hemisphere/seasonality, terrain size, multi-resort pass networks (North America + Europe + global), and approximate lift-ticket price tier (`$`–`$$$$`), then pull **live current snow depth and 1–2 week forecasts** via Open-Meteo (free, no API key).

## When to Use

- "Find a ski vacation close to an airport"
- "Find a non-stop flight to a ski resort"
- "Cheap ski vacation in Europe or Japan"
- "What's the current snow and 2-week forecast at Zermatt?"
- "Notify me if there is a big snow dump at Zermatt, Alta, or Niseko and look up flights"

## Workflow

### Step 1: Filter the Local Resort Database

Run `search_ski_resorts.py` from the repo root. All distances are **crow-flies (great-circle)**, NOT driving distance — always label them clearly as crow-flies in output.

```bash
# Resorts within 60 miles (crow-flies) of a major commercial hub, for late snow (2500m+ elevation)
python3 skills/ski-resorts/scripts/search_ski_resorts.py \
  --max-crow-flies-mi 60 --hub-only --min-summit-m 2500 --limit 15

# European Dolomiti Superski resorts
python3 skills/ski-resorts/scripts/search_ski_resorts.py \
  --pass dolomiti_superski --limit 10

# Southern Hemisphere skiing (Jun-Oct)
python3 skills/ski-resorts/scripts/search_ski_resorts.py \
  --hemisphere south --limit 10

# Budget-friendly ($) or mid-tier ($$) resorts
python3 skills/ski-resorts/scripts/search_ski_resorts.py \
  --max-price-tier '$$' --country Austria --limit 10
```

**Available filters:**
- `--max-crow-flies-mi` / `--max-crow-flies-km`: Maximum straight-line distance to airport
- `--hub-only`: Measure distance to nearest `large_airport` hub (skip smaller regional airports)
- `--hemisphere`: `north` or `south`
- `--country` / `--region` / `--query`: Substring match on country, region, or resort name
- `--pass`: `epic`, `ikon`, `indy`, `mountain_collective`, `dolomiti_superski`, `superskicard`, `snow_card_tirol`, `magic_pass`, `ski_amade`, `trois_vallees`, `portes_du_soleil`, `mont_blanc_unlimited`
- `--price-tier` / `--max-price-tier`: `$` (<$70), `$$` ($70–$120), `$$$` ($120–$200), `$$$$` ($200+)
- `--min-summit-m` / `--min-vertical-m` / `--min-lifts` / `--glacier`
- `--sort`: `size` (default), `airport`, `summit`, `vertical`
- `--json`: Machine-readable output for chaining

### Step 2: Pull Live Snow & 14-Day Forecast (Optional / Automations)

```bash
# Live snow depth and 14-day forecast
python3 skills/ski-resorts/scripts/fetch_snow.py \
  --resorts "Zermatt,Snowbird,Niseko" --days 14

# Powder-dump alert for automations (flag resorts with >= 25 cm in next 7 days + nearest airport IATA)
python3 skills/ski-resorts/scripts/fetch_snow.py \
  --resorts "Zermatt,Snowbird,Niseko" --days 7 --min-snow-cm 25 --alerts-only
```

Uses the free Open-Meteo Forecast API (no key required) to return current snow depth (`cm`), current temperature, 7-day snowfall, 14-day snowfall/temperature range, and `nearest_airports` so triggered alerts can immediately chain into `compare-flights`.

### Step 3: Chain into Flights & Lodging

Once you have the top 2–4 candidate resorts:
1. Pass their `nearest_airports[].iata` codes into `compare-flights` (Duffel, Ignav, Seats.aero, Skiplagged).
2. Pass the resort name / locality / coordinates into `compare-hotels`, `vrbo`, or `hotel-chains` for slopeside or valley lodging.

## Refreshing the Static Database

```bash
python3 scripts/refresh-ski-data.py
```

Rebuilds `data/ski-resorts.json` from OpenSkiData (`openskidata.org`, ODbL) and OurAirports (`ourairports.com`, Public Domain) without modifying `data/airport-coordinates.json`.

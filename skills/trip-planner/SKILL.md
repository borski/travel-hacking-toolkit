---
name: trip-planner
description: Unified trip planning that combines flight comparison, hotel comparison, and points optimization into one complete trip cost analysis. Use when the user says "plan a trip" or wants the full picture for a destination.
---

**Companion reference skills.** Load these for deeper context:
- `flight-search-strategy` — full search workflow and source priority
- `lessons-learned` — Seats.aero workflow and common failure modes (load before any award search)
- `points-valuations` — CPP rules, opportunity cost
- `partner-awards` — reachability through alliance + bilateral partnerships
- `award-sweet-spots` — flag legendary redemptions
- `booking-guidance` — booking flow + phone numbers + the "hold before transfer" rule


# Trip Planner

"Plan a trip to Paris Aug 11-15" answered with one complete cost breakdown.

Orchestrates `compare-flights`, `compare-hotels`, `transfer-partners`, and `trip-calculator` into a unified trip analysis. Shows total trip cost in cash vs every available points strategy.

**This is an orchestration skill.** It tells the agent which skills to invoke and how to combine their outputs.

## When to Use

- "Plan a trip to Paris Aug 11-15"
- "What's the cheapest way to do SFO to Tokyo for a week in September?"
- "How much would a trip to Stockholm cost in points vs cash?"
- Any request that involves both flights AND accommodation

## When NOT to Use

- Flight-only comparison (use `compare-flights`)
- Hotel-only comparison (use `compare-hotels`)
- Award calendar (use `award-calendar`)
- "Should I use points?" without a specific trip (use `trip-calculator`)

## Workflow

### Step 1: Parse Trip Parameters

Extract from the user's request:

| Parameter | Example | Required |
|-----------|---------|----------|
| Origin | SFO | Yes |
| Destination | Paris / CDG | Yes |
| Departure date | 2026-08-11 | Yes |
| Return date | 2026-08-15 | Yes (assume one-way if not given) |
| Travelers | 2 adults | Default: 1 |
| Cabin class | Business | Default: Economy |
| Preferences | FHR hotels, nonstop flights | Optional |

If anything is ambiguous, ask. Don't guess dates or travelers.

### Step 2: Run Searches in Parallel

Launch ALL searches simultaneously. Don't wait for one to finish before starting another.

```
PARALLEL:
  1. compare-flights: origin → destination, departure date, cabin
  2. compare-flights: destination → origin, return date, cabin (if round-trip)
  3. compare-hotels: destination, checkin = departure, checkout = return
```

Each of these internally runs their own parallel sub-searches (Duffel, Ignav, seats.aero, Chase, Amex, SerpAPI, Trivago, LiteAPI, Airbnb, etc).

### Step 3: Combine into Trip Cost Matrix

Build a table showing total trip cost for each strategy.

**For each booking strategy, calculate total = outbound + return + hotel:**

| Strategy | Outbound | Return | Hotel (4 nights) | Total | Points Used | Cash Out of Pocket |
|----------|----------|--------|-------------------|-------|-------------|-------------------|
| All cash | $4,200 | $3,800 | $1,200 | **$9,200** | 0 | $9,200 |
| Flights: award, Hotel: cash | $120 tax | $95 tax | $1,200 | **$1,415** | 110,000 UR | $1,415 |
| Flights: award, Hotel: FHR | $120 tax | $95 tax | $8,284 (paid via points) | **$8,499** | 110,000 UR + 828,400 MR | $215 |
| Flights: Chase portal, Hotel: Edit | — | — | — | **varies** | 540,000 UR | $0 |
| Flights: award, Hotel: Airbnb | $120 tax | $95 tax | $780 | **$995** | 110,000 UR | $995 |

### Step 4: Calculate Value Scores

For each strategy, compute:

```
Points value = (all-cash total - cash out of pocket) / total points used × 100
```

This tells you the CPP you're getting across the whole trip, not just one component.

Example:
```
"Flights: award + Hotel: Airbnb"
All-cash equivalent: $9,200
Cash out of pocket: $995
Points saved: $9,200 - $995 = $8,205
Points used: 110,000 UR
Trip CPP: $8,205 / 110,000 × 100 = 7.5 cpp
```

### Step 5: Present the Trip Plan

#### Trip: SFO → Paris, Aug 11-15, 2 adults, Business Class

**✈️ Outbound: SFO → CDG, Aug 11**

| Option | Source | Price/Points | Currency |
|--------|--------|-------------|----------|
| Cash (lowest) | Duffel | $4,200 | — |
| Flying Blue | seats.aero | 55,000 + $120 tax | Chase UR (1:1) |
| Chase Portal Boost | chase-travel | 180,000 | Chase UR |

**✈️ Return: CDG → SFO, Aug 15**

| Option | Source | Price/Points | Currency |
|--------|--------|-------------|----------|
| Cash (lowest) | Duffel | $3,800 | — |
| Aeroplan | seats.aero | 70,000 + $200 tax | Chase UR (1:1) |

**🏨 Hotels: Paris, Aug 11-15 (4 nights)**

| Option | Source | Per Night | Total | Points | Benefits |
|--------|--------|-----------|-------|--------|----------|
| SO/ Paris [EDIT] | Chase | $639 | $2,555 | 127,756 UR | Breakfast, $100 credit |
| Le Bristol [FHR] | Amex | $1,849 | $8,284 | 828,400 MR | $100 credit, breakfast, upgrade |
| Marriott Champs | SerpAPI | $289 | $1,156 | — | — |
| Airbnb: Marais 2BR | Airbnb | $195 | $780 | — | Kitchen |

**💰 Trip Total by Strategy**

| # | Strategy | Total Cash | Points | CPP | Rating |
|---|----------|-----------|--------|-----|--------|
| 1 | Award flights (FB+AC) + Airbnb | $1,115 | 125,000 UR | 6.5 | ⭐ Best value |
| 2 | Award flights + Chase Edit hotel | $2,870 | 252,756 UR | 2.5 | Good convenience |
| 3 | All cash | $8,136 | 0 | — | Baseline |
| 4 | Chase portal flights + Edit hotel | $0 | 487,756 UR | 1.7 | Most points |
| 5 | Award flights + FHR hotel | $8,599 | 125,000 UR + 828,400 MR | Mixed | Luxury |

**🎯 Recommendation:**

Award flights via Flying Blue (out) + Aeroplan (return) = 125,000 Chase UR for $8,000 worth of business class flights. That's 6.4 cpp. Excellent.

For the hotel: Chase Edit SO/ Paris gives breakfast + $100 credit for $2,555 (or 127,756 UR at 2.0 cpp via boost). The Airbnb is cheapest at $780 but no breakfast or hotel amenities.

**Best overall: Award flights + Airbnb** if you want max savings. **Award flights + Chase Edit** if you want the hotel experience with benefits.

### Step 6: Source Status

Always report which sources succeeded and which failed:

```
✅ Duffel: 45 outbound, 38 return
✅ Ignav: 40 outbound, 35 return
✅ Seats.aero: 12 award options outbound, 8 return
✅ Chase Travel: 300 outbound flights, 21 hotels
✅ Amex Travel: 292 outbound flights, 17 hotels
✅ SerpAPI: 25 hotels
✅ Trivago: 30 hotels
✅ LiteAPI: 22 hotels
✅ Airbnb: 18 listings
✅ Google Flights: 52 outbound
⏭️ Southwest: skipped (no SFO-CDG service)
```

## Error Handling

**NEVER fail silently.** If any sub-search fails, note it and continue with what you have.

If flights fail but hotels succeed (or vice versa), present what you have and note the gap:
```
❌ Seats.aero: API timeout. Award flight pricing unavailable.
    Trip totals shown are cash-only and portal-only. Retry seats.aero for award options.
```

If ALL sources fail for one component, say so:
```
❌ All hotel sources failed. Cannot calculate trip total. Fix hotel search, then rerun.
```

## Limitations

- Round-trip cash prices from Duffel/Ignav may be cheaper than two one-ways. Note when this is the case.
- Award pricing is one-way. The combined outbound + return award cost is the correct comparison against a round-trip cash fare.
- Hotel pricing may vary between portal and direct booking. Note significant differences.
- Chase portal 1.5x multiplier is applied at checkout, not in the listing. The skill adjusts automatically.
- Trip totals are estimates. Taxes, fees, and exchange rates can change actual booking costs.

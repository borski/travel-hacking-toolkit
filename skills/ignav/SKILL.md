---
name: ignav
description: Search for flights using the Ignav API. Fast REST API for flight prices and booking links. Use alongside other flight sources for price comparison. Always include in every flight search. Triggers on any flight-related search request.
category: flights
summary: Fast REST API cash prices. Market selection for arbitrage.
api_key: Ignav (1,000 free)
allowed-tools: Bash(curl *)
---

# Flight Search via Ignav API

Fast REST API flight search at `https://ignav.com`. Returns structured JSON with prices, itineraries, and booking links. 1,000 free requests, no rate limit.

## Setup

Get a free API key at https://ignav.com/signup (1,000 requests, no credit card).

Set `IGNAV_API_KEY` in your environment or `.env` file.

## Workflow

1. Parse the user's request (origin, destination, dates, trip type, passengers, cabin)
2. Look up airport codes if user gave city names
3. Search flights (one-way or round-trip)
4. Present results in markdown table
5. Get booking links if user wants to book

## Endpoints

### Search Airports

```bash
curl -s "https://ignav.com/api/airports?q=Barcelona&limit=5" \
  -H "X-Api-Key: $IGNAV_API_KEY"
```

### One-Way Flights

```bash
curl -s -X POST "https://ignav.com/api/fares/one-way" \
  -H "X-Api-Key: $IGNAV_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "SFO",
    "destination": "JFK",
    "departure_date": "2026-05-15",
    "adults": 1,
    "cabin_class": "economy"
  }'
```

### Round-Trip Flights

```bash
curl -s -X POST "https://ignav.com/api/fares/round-trip" \
  -H "X-Api-Key: $IGNAV_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "SFO",
    "destination": "JFK",
    "departure_date": "2026-05-15",
    "return_date": "2026-05-20",
    "adults": 1,
    "cabin_class": "economy"
  }'
```

### Booking Links

```bash
curl -s -X POST "https://ignav.com/api/fares/booking-links" \
  -H "X-Api-Key: $IGNAV_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"ignav_id": "the_itinerary_id", "adults": 1}'
```

## Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `adults` | int | Number of adults (default: 1) |
| `children` | int | Number of children (default: 0) |
| `cabin_class` | string | `economy`, `premium_economy`, `business`, `first` |
| `max_stops` | int | 0 (direct only), 1, or 2 |
| `max_price` | int | Maximum price filter |
| `departure_time_range` | object | `{"earliest_hour": 8, "latest_hour": 20}` |
| `airlines_include` | array | Only these airline codes |
| `airlines_exclude` | array | Exclude these airline codes |
| `market` | string | Country code for pricing (default: "US"). Different markets return different prices. |

## Response Structure

Each itinerary contains:
- `price`: `{"amount": 299, "currency": "USD"}`
- `outbound`: carrier, duration_minutes, segments array
- `inbound`: same (null for one-way)
- `cabin_class`: the cabin class
- `bags`: `{"carry_on": 1, "checked": 0}`
- `ignav_id`: unique ID for booking links

Each segment: `marketing_carrier_code`, `flight_number`, `departure_airport`, `departure_time_local`, `arrival_airport`, `arrival_time_local`, `duration_minutes`, `aircraft`.

## Output Format

**Always use markdown tables.**

| # | Airline | Stops | Duration | Depart | Arrive | Price | Bags |
|---|---------|-------|----------|--------|--------|-------|------|
| 1 | Vueling | Nonstop | 2h 15m | 8:30 AM | 10:45 AM | EUR 125 | 1 carry-on |
| 2 | Ryanair | Nonstop | 2h 20m | 6:15 AM | 8:35 AM | EUR 89 | 1 carry-on |

After the table, highlight cheapest, fastest, and best value. Call out tradeoffs. Offer booking links.

## Notes

- Dates are required for all searches
- Default to round-trip and economy if not specified
- Use airport search endpoint for city name lookups
- **Market affects prices.** Same route can cost significantly less from a different market. Try departure country first, then destination country.
- **Does NOT include Southwest.** Use google-flights skill for SW.

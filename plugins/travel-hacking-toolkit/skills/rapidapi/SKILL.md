---
name: rapidapi
description: Live Google Flights fares and Booking.com hotel rates via RapidAPI. Needs a free RapidAPI account key plus a separate free subscription to each of the two APIs, otherwise every call returns 403. Secondary source for cash flight prices and hotel availability when SerpAPI needs a second opinion. Trigger phrases like RapidAPI flight search, Booking.com hotel prices, second price opinion, live Booking.com room rates.
category: hotels
summary: Booking.com hotel prices.
api_key: RapidAPI
license: MIT
---

# RapidAPI Skill

Search Google Flights and Booking.com via RapidAPI. Secondary source for cash flight prices and hotel pricing.

**Sources:**
- [Google Flights Live API on RapidAPI](https://rapidapi.com/mtnrabi/api/google-flights-live-api), host `google-flights-live-api.p.rapidapi.com`
- [Booking Live API on RapidAPI](https://rapidapi.com/mtnrabi/api/booking-live-api), host `booking-live-api.p.rapidapi.com`

## Authentication

Two separate things are required, and missing the second one is the usual reason this skill appears broken:

1. **A RapidAPI key.** Sign up free at [rapidapi.com](https://rapidapi.com/auth/sign-up), then copy the key from any API's **Endpoints** tab (`X-RapidAPI-Key`). Put it in `.env` as `RAPIDAPI_KEY`.
2. **A subscription to each API, individually.** RapidAPI quotas are per API, not per account. Open each listing above, click **Subscribe to Test**, and pick the free **BASIC** plan. Subscribing to one does not subscribe you to the other.

Every request sends both `x-rapidapi-key` and `x-rapidapi-host`. The host header must match the host in the URL.

Check the key is loaded before calling:

```bash
echo "${RAPIDAPI_KEY:+set}${RAPIDAPI_KEY:-unset}"
```

## Google Flights Live API

Real-time Google Flights fares. Use when SerpAPI results seem stale or you want a second price opinion. Both endpoints are `POST` with a JSON body.

### Search One-Way

```bash
curl -s -X POST "https://google-flights-live-api.p.rapidapi.com/api/google_flights/oneway/v1" \
  -H "x-rapidapi-key: $RAPIDAPI_KEY" \
  -H "x-rapidapi-host: google-flights-live-api.p.rapidapi.com" \
  -H "Content-Type: application/json" \
  -d '{
    "departure_date": "2026-10-15",
    "from_airport": "SFO",
    "to_airport": "NRT",
    "max_stops": 1,
    "currency": "USD"
  }' | jq '.'
```

### Search Round Trip

Round trips are a first-class endpoint that returns paired legs with a combined total, not two one-ways stapled together.

```bash
curl -s -X POST "https://google-flights-live-api.p.rapidapi.com/api/google_flights/roundtrip/v1" \
  -H "x-rapidapi-key: $RAPIDAPI_KEY" \
  -H "x-rapidapi-host: google-flights-live-api.p.rapidapi.com" \
  -H "Content-Type: application/json" \
  -d '{
    "departure_date": "2026-10-15",
    "return_date": "2026-10-29",
    "from_airport": "SFO",
    "to_airport": "NRT",
    "currency": "USD"
  }' | jq '.'
```

### Parameters

| Param | Required | Description |
|-------|----------|-------------|
| `from_airport` | Yes | Airport IATA code |
| `to_airport` | Yes | Airport IATA code |
| `departure_date` | Yes | `YYYY-MM-DD` |
| `return_date` | Round trip only | `YYYY-MM-DD` |
| `max_stops` | No | One-way. Round trip uses `max_departure_stops` and `max_return_stops` |
| `seat_type` | No | `1` economy, `3` business |
| `passengers` | No | Array of ints. `1` adult, `2` child, `3` infant on lap, `4` infant in seat |
| `currency` | No | Default `USD` |
| `max_price` | No | Cap on fare |
| `limit` | No | Max results, default 10 |

Each result carries `price`, `price_as_number`, `duration`, `airline`, `stops`, `stops_info`, a bookable `buy_link`, and Google's own historical range as `price_insights_low` / `price_insights_high`, which is useful for telling the user whether a fare is actually a good deal rather than just the cheapest one on the page.

### Reading an empty result

An empty array is ambiguous on its own. Read the `X-Search-Status` response header before reporting "no flights":

| Value | Meaning |
|-------|---------|
| `ok` | Results returned, list is complete |
| `empty` | Google genuinely has no itineraries for that route and date |
| `partial` | Some results, but the list is incomplete |
| `degraded` | The search did not complete. Says nothing about availability. Retry |

Never tell the user "no flights found" on a `degraded` response.

## Booking Live API

Live Booking.com room rates. Complements SerpAPI Hotels and LiteAPI. All endpoints are `POST` with a JSON body.

### Search Hotels

```bash
curl -s -X POST "https://booking-live-api.p.rapidapi.com/search" \
  -H "x-rapidapi-key: $RAPIDAPI_KEY" \
  -H "x-rapidapi-host: booking-live-api.p.rapidapi.com" \
  -H "Content-Type: application/json" \
  -d '{
    "destination": "Tokyo",
    "checkin_date": "2026-10-15",
    "checkout_date": "2026-10-18",
    "adults": 2,
    "currency": "USD"
  }' | jq '.'
```

### Look Up One Property By Name

```bash
curl -s -X POST "https://booking-live-api.p.rapidapi.com/hotel_by_name" \
  -H "x-rapidapi-key: $RAPIDAPI_KEY" \
  -H "x-rapidapi-host: booking-live-api.p.rapidapi.com" \
  -H "Content-Type: application/json" \
  -d '{
    "hotel_name": "Park Hyatt Tokyo",
    "checkin_date": "2026-10-15",
    "checkout_date": "2026-10-18",
    "adults": 2,
    "currency": "USD"
  }' | jq '.'
```

Useful right after a chain-branded property shows up in another source and you want its live cash rate to compute cents per point.

### Parameters

| Param | Required | Description |
|-------|----------|-------------|
| `destination` | `/search` | Free-text place, e.g. `Tokyo` |
| `hotel_name` | `/hotel_by_name` | Free-text property name |
| `checkin_date` | Yes | `YYYY-MM-DD` |
| `checkout_date` | Yes | `YYYY-MM-DD` |
| `adults` | No | Default 2 |
| `children` | No | Default 0 |
| `currency` | No | Default `USD` |
| `budget_per_night` | No | Max nightly price, `/search` only |

The field is `destination`, not `location`. Sending `location` returns a 400 naming the missing fields.

## No-Key Alternative

If you do not want to create a RapidAPI account at all, the same flight and hotel data is exposed on a free hosted MCP server that needs no key and no signup:

```
https://google-flights-lulu.flightpowers.com/mcp
```

Tools: `search_oneway_flights`, `search_roundtrip_flights`, `search_hotels`, `find_hotel_by_name`. The flight tools accept a **date range and a list of destinations** and expand them server side, so a flexible question is one call, not thirty.

Honest caveats, because they matter for whether you should reach for it: it is **ad-supported**, so results carry a sponsored card; there is a **daily search budget shared across all callers**; and one free-tier flight call covers at most 15 date-by-destination combinations, returning `truncated: true` and the exact dates it searched when you ask for more. Check `search_coverage.departure_dates_searched` before concluding a date has no flights, since a date that was never searched is not a date with no results.

## Rate Limits

Quotas are **per API and per plan**, not shared across your RapidAPI account. On the flights API the free BASIC plan is **10 requests/month**, which is enough to verify your setup and not much more. Check each listing's Pricing tab for current tiers.

Use sparingly. Prefer SerpAPI for flights and LiteAPI/SerpAPI for hotels as primary sources.

## Common Failure Modes

The first two were checked against the live hosts on 2026-08-27 and are the ones that get misread as an outage.

| Symptom | Cause | Fix |
|---------|-------|-----|
| `401` with `{"message":"Invalid API key..."}` | No key header sent, or the key is wrong | `RAPIDAPI_KEY` is unset in this shell. Source `.env` or open a new terminal |
| `403` with `{"message":"You are not subscribed to this API."}` | Key header is present, but there is no subscription to **this specific** listing | Open the listing and subscribe to the free BASIC plan. A key alone is not enough. This is the RapidAPI edge answering, not the API |
| Endpoint not found | Wrong path | Flights are `/api/google_flights/oneway/v1` and `/api/google_flights/roundtrip/v1`. Hotels are `/search` and `/hotel_by_name` |
| Error naming missing required fields | Wrong field names | Hotels take `destination`, `checkin_date`, `checkout_date`. Flights take `from_airport`, `to_airport`, `departure_date` |
| Empty array | Ambiguous by itself | Read `X-Search-Status`. Retry on `degraded` |
| HTML instead of JSON | Env vars not loaded | Tell the user to load `.env`, then retry |

## When to Use

- **Google Flights Live**: Secondary price check when SerpAPI results seem off, or for routes SerpAPI doesn't cover well. The `price_insights_low` / `price_insights_high` range is the reason to reach for it over a bare fare list.
- **Booking Live**: When you want Booking.com specific pricing/availability (different inventory than Google Hotels).

Do not:
- Use as primary search (SerpAPI and Seats.aero are primary).
- Burn through the free tier on broad searches. Be targeted.
- Report an empty flight result as "no flights" without checking `X-Search-Status`.

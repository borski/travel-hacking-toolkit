---
name: duffel
description: Real-time GDS flight search via Duffel API. Accurate per-fare-class pricing, cabin selection, multi-city, time preferences. Primary cash price source. Does not include Southwest.
category: flights
summary: Primary cash prices. Real GDS per-fare-class data.
api_key: Duffel
allowed-tools: Bash(curl *)
---

# Duffel Flights

Search for real-time flight offers across airlines via the [Duffel API](https://duffel.com/docs/api). Returns live pricing, cabin details, baggage info, and booking links. Supports one-way, round-trip, and multi-city searches.

**Source:** [duffel.com](https://duffel.com)

## Prerequisites

- `DUFFEL_API_KEY_LIVE` environment variable set with a live API token
- Token needs `air.offer_requests.create` permission

## API Basics

- **Base URL:** `https://api.duffel.com`
- **Version header:** `Duffel-Version: v2` (REQUIRED, v1 is deprecated)
- **Auth:** `Authorization: Bearer $DUFFEL_API_KEY_LIVE`
- **Content-Type:** `application/json`
- **Rate limit:** 60 requests per 60 seconds

## Search Flights (One-Way)

```bash
curl -s -X POST "https://api.duffel.com/air/offer_requests?return_offers=true&supplier_timeout=15000" \
  -H "Accept: application/json" \
  -H "Duffel-Version: v2" \
  -H "Authorization: Bearer $DUFFEL_API_KEY_LIVE" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "slices": [{
        "origin": "SFO",
        "destination": "NRT",
        "departure_date": "2026-08-15"
      }],
      "passengers": [{"type": "adult"}],
      "cabin_class": "economy"
    }
  }'
```

## Search Flights (Round-Trip)

Add a second slice with origin/destination reversed:

```bash
curl -s -X POST "https://api.duffel.com/air/offer_requests?return_offers=true&supplier_timeout=15000" \
  -H "Accept: application/json" \
  -H "Duffel-Version: v2" \
  -H "Authorization: Bearer $DUFFEL_API_KEY_LIVE" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "slices": [
        {
          "origin": "SFO",
          "destination": "NRT",
          "departure_date": "2026-08-15"
        },
        {
          "origin": "NRT",
          "destination": "SFO",
          "departure_date": "2026-08-22"
        }
      ],
      "passengers": [{"type": "adult"}],
      "cabin_class": "business"
    }
  }'
```

## Search Flights (Multi-City)

Add as many slices as needed:

```bash
curl -s -X POST "https://api.duffel.com/air/offer_requests?return_offers=true&supplier_timeout=15000" \
  -H "Accept: application/json" \
  -H "Duffel-Version: v2" \
  -H "Authorization: Bearer $DUFFEL_API_KEY_LIVE" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "slices": [
        {"origin": "SFO", "destination": "NRT", "departure_date": "2026-08-15"},
        {"origin": "NRT", "destination": "ICN", "departure_date": "2026-08-20"},
        {"origin": "ICN", "destination": "SFO", "departure_date": "2026-08-25"}
      ],
      "passengers": [{"type": "adult"}],
      "cabin_class": "economy"
    }
  }'
```

## Nonstop Only

Set `max_connections` to 0:

```bash
curl -s -X POST "https://api.duffel.com/air/offer_requests?return_offers=true&supplier_timeout=15000" \
  -H "Accept: application/json" \
  -H "Duffel-Version: v2" \
  -H "Authorization: Bearer $DUFFEL_API_KEY_LIVE" \
  -H "Content-Type: application/json" \
  -d '{
    "data": {
      "slices": [{
        "origin": "SFO",
        "destination": "NRT",
        "departure_date": "2026-08-15"
      }],
      "passengers": [{"type": "adult"}],
      "cabin_class": "business",
      "max_connections": 0
    }
  }'
```

## Multiple Passengers

```json
"passengers": [
  {"type": "adult"},
  {"type": "adult"},
  {"age": 10},
  {"type": "infant_without_seat"}
]
```

Use `age` instead of `type` for children to avoid passenger type mismatches between search and booking.

## Time Preferences

Constrain departure or arrival times:

```json
"slices": [{
  "origin": "SFO",
  "destination": "NRT",
  "departure_date": "2026-08-15",
  "departure_time": {"from": "08:00", "to": "14:00"},
  "arrival_time": {"from": "06:00", "to": "18:00"}
}]
```

## Query Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `return_offers` | `true` | Set to `false` to get just the request ID, then fetch offers separately |
| `supplier_timeout` | `20000` | Max ms to wait for airline responses (2000 to 60000) |

## Reading the Response

The response is nested under `data`. Key fields:

```
data.id                              -> offer request ID
data.offers[]                        -> array of flight offers
  .id                                -> offer ID (use to get details or book)
  .total_amount / .total_currency    -> total price
  .base_amount / .base_currency      -> base fare (before tax)
  .tax_amount / .tax_currency        -> taxes
  .owner.name                        -> airline selling this
  .expires_at                        -> when offer expires
  .slices[]                          -> journey legs
    .origin.iata_code                -> departure airport
    .destination.iata_code           -> arrival airport
    .duration                        -> e.g. "PT11H30M"
    .segments[]                      -> individual flights
      .marketing_carrier.name        -> airline name
      .marketing_carrier_flight_number
      .operating_carrier.name        -> actual operating airline
      .departing_at / .arriving_at   -> datetime
      .duration                      -> segment duration
      .origin.iata_code / .destination.iata_code
      .passengers[].cabin_class      -> economy/business/first
      .passengers[].cabin.amenities  -> wifi, power, seat info
      .passengers[].baggages[]       -> checked/carry_on allowances
  .conditions                        -> refund/change policies
    .refund_before_departure.allowed
    .change_before_departure.allowed
    .change_before_departure.penalty_amount
```

## Get Offer Details

Retrieve full details for a specific offer:

```bash
curl -s "https://api.duffel.com/air/offers/$OFFER_ID" \
  -H "Accept: application/json" \
  -H "Duffel-Version: v2" \
  -H "Authorization: Bearer $DUFFEL_API_KEY_LIVE"
```

## Parsing Tips

Extract the 5 cheapest offers with jq:

```bash
| jq '[.data.offers | sort_by(.total_amount | tonumber) | .[:5][] | {
  price: (.total_amount + " " + .total_currency),
  airline: .owner.name,
  route: [.slices[] | (.origin.iata_code + " -> " + .destination.iata_code)],
  segments: [.slices[].segments[] | {
    flight: (.marketing_carrier.iata_code + .marketing_carrier_flight_number),
    carrier: .operating_carrier.name,
    depart: .departing_at,
    arrive: .arriving_at,
    cabin: .passengers[0].cabin_class,
    duration: .duration
  }],
  stops: ([.slices[].segments | length] | map(. - 1)),
  expires: .expires_at
}]'
```

## Cabin Classes

| Value | Description |
|-------|-------------|
| `economy` | Standard economy |
| `premium_economy` | Premium economy |
| `business` | Business class |
| `first` | First class |

## Important Notes

- Offers expire quickly (usually 15 to 30 minutes). Check `expires_at`.
- Always show the operating carrier name (US DOT regulation).
- Set `supplier_timeout` lower than your HTTP client timeout.
- Use `age` for child passengers instead of `type` to avoid airline mismatch errors.
- The API returns real GDS prices. These are bookable, not estimates.
- Duffel aggregates across multiple airlines in a single search.

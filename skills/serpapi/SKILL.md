---
name: serpapi
description: Search Google Flights for cash prices, Google Hotels for accommodation, and Google Travel Explore for destination discovery. Use when comparing award flights vs pay-with-points portal pricing, searching hotels, or exploring travel options. Triggers on "cash price", "how much does the flight cost", "hotel search", "Google Flights", "Chase portal comparison", "pay with points portal", "cheapest flight", "flight schedule", or any question about actual dollar prices for flights or hotels.
category: hotels
summary: Google Hotels search and destination discovery.
api_key: SerpAPI
license: MIT
---

# SerpAPI Skill

Scrape Google Flights, Google Hotels, and Google Travel Explore via SerpAPI. Provides cash flight prices (for Chase/Amex portal comparison), hotel pricing, and destination discovery.

**Source:** [serpapi.com](https://serpapi.com) — Free tier available, paid plans for higher volume.

## Authentication

`SERPAPI_API_KEY` is set in `.env`. All requests use `api_key` query parameter.

## API Base

```
https://serpapi.com/search
```

## Google Flights (Cash Prices)

Search for flight prices and schedules. Essential for comparing: "Is 88,000 United miles better than paying $900 cash through the Chase portal?" (Chase portal pricing is now dynamic via Points Boost, ~1.5-2.0 cpp on select bookings; verify the actual quote.)

### One-Way Search

```bash
curl -s "https://serpapi.com/search?engine=google_flights&departure_id=SFO&arrival_id=NRT&outbound_date=2026-08-10&type=2&adults=2&travel_class=1&currency=USD&stops=2&sort_by=2&api_key=$SERPAPI_API_KEY" | jq '{best: [.best_flights[]? | {price: .price, duration: .total_duration, stops: (.layovers | length), flights: [.flights[] | {from: .departure_airport.id, to: .arrival_airport.id, airline: .airline, flight: .flight_number, depart: .departure_airport.time, arrive: .arrival_airport.time}]}], price_insights: .price_insights}'
```

### Parameters

| Param | Required | Description |
|-------|----------|-------------|
| `engine` | Yes | `google_flights` |
| `departure_id` | Yes | Airport code(s), comma-separated: `SFO,PDX` |
| `arrival_id` | Yes | Airport code(s), comma-separated: `NRT,HND` |
| `outbound_date` | Yes | `YYYY-MM-DD` |
| `return_date` | Round trip | `YYYY-MM-DD` (required if type=1) |
| `type` | No | `1` = round trip (default), `2` = one way, `3` = multi-city |
| `adults` | No | Default 1 |
| `children` | No | Default 0 |
| `travel_class` | No | `1` = economy, `2` = premium economy, `3` = business, `4` = first |
| `stops` | No | `0` = any, `1` = nonstop, `2` = 1 stop or fewer, `3` = 2 stops or fewer |
| `sort_by` | No | `1` = top flights, `2` = price, `3` = departure, `4` = arrival, `5` = duration |
| `include_airlines` | No | IATA codes: `SK,KL,UA` or alliances: `STAR_ALLIANCE,SKYTEAM,ONEWORLD` |
| `max_price` | No | Maximum ticket price in USD |
| `max_duration` | No | Maximum flight duration in minutes |
| `bags` | No | Number of carry-on bags |
| `deep_search` | No | `true` for browser-identical results (slower) |
| `currency` | No | Default `USD` |

### Multi-City (Open Jaw)

Use `type=3` with `multi_city_json`:

```bash
curl -s "https://serpapi.com/search?engine=google_flights&type=3&multi_city_json=%5B%7B%22departure_id%22%3A%22SFO%22%2C%22arrival_id%22%3A%22NRT%22%2C%22date%22%3A%222026-08-05%22%7D%2C%7B%22departure_id%22%3A%22ICN%22%2C%22arrival_id%22%3A%22SFO%22%2C%22date%22%3A%222026-08-26%22%7D%5D&adults=2&travel_class=1&currency=USD&api_key=$SERPAPI_API_KEY" | jq '.'
```

The JSON value for multi_city_json is URL-encoded. Decoded:
```json
[{"departure_id":"SFO","arrival_id":"NRT","date":"2026-08-05"},{"departure_id":"ICN","arrival_id":"SFO","date":"2026-08-26"}]
```

### Response Fields

Each flight in `best_flights[]` and `other_flights[]`:

| Field | Description |
|-------|-------------|
| `price` | Cash price in USD |
| `total_duration` | Total minutes |
| `flights[]` | Array of legs with airline, flight number, times, airplane, legroom |
| `layovers[]` | Array with duration and airport for each connection |
| `departure_token` | Token to get return flight options (round trip) |
| `booking_token` | Token to get booking options |

`price_insights` includes `lowest_price`, `price_level` (low/typical/high), and `typical_price_range`.

### Portal Comparison Math

Chase Sapphire Reserve: dynamic Points Boost pricing, typically 1.5-2.0 cpp on select bookings (not a fixed floor). Verify actual portal price for the specific booking.
If cash price is $900, portal cost = 60,000 UR points.
If award price is 88,000 United miles, cash via portal is better value.

Amex: typically 1 cpp via portal (worse value, use transfers instead).

Capital One Venture X: 1 cpp via portal, but transfer partners can be better.

## Google Hotels

Search hotels and vacation rentals with pricing from multiple OTAs.

```bash
curl -s "https://serpapi.com/search?engine=google_hotels&q=hotels+Tokyo+Japan&check_in_date=2026-08-10&check_out_date=2026-08-13&adults=2&currency=USD&sort_by=3&api_key=$SERPAPI_API_KEY" | jq '[.properties[]? | {name: .name, type: .type, rating: .overall_rating, reviews: .reviews, price: .rate_per_night.extracted_lowest, class: .extracted_hotel_class, amenities: .amenities}] | .[0:10]'
```

### Parameters

| Param | Required | Description |
|-------|----------|-------------|
| `engine` | Yes | `google_hotels` |
| `q` | Yes | Search query: `hotels Tokyo Japan` |
| `check_in_date` | Yes | `YYYY-MM-DD` |
| `check_out_date` | Yes | `YYYY-MM-DD` |
| `adults` | No | Default 2 |
| `children` | No | Default 0 |
| `sort_by` | No | `3` = lowest price, `8` = highest rating, `13` = most reviewed |
| `min_price` / `max_price` | No | Price range filter |
| `hotel_class` | No | `2,3,4,5` (comma-separated) |
| `rating` | No | `7` = 3.5+, `8` = 4.0+, `9` = 4.5+ |
| `vacation_rentals` | No | Set to `true` for Airbnb-style results |
| `property_token` | No | Get details for a specific property |

## Google Travel Explore

Discover destinations and cheapest flights from an origin. Great for "where can I fly cheaply in August?"

```bash
curl -s "https://serpapi.com/search?engine=google_travel_explore&departure_id=SFO&outbound_date=2026-08-05&return_date=2026-08-26&adults=2&travel_class=1&currency=USD&api_key=$SERPAPI_API_KEY" | jq '[.destinations[]? | {name: .name, country: .country, airport: .destination_airport.code, price: .flight_price, duration: .flight_duration, stops: .number_of_stops, airline: .airline}] | .[0:15]'
```

### Parameters

| Param | Required | Description |
|-------|----------|-------------|
| `engine` | Yes | `google_travel_explore` |
| `departure_id` | Yes | Airport code or kgmid |
| `arrival_id` | No | Specific destination |
| `arrival_area_id` | No | Region kgmid (e.g., `/m/02j9z` for Europe) |
| `outbound_date` | No | `YYYY-MM-DD` |
| `return_date` | No | `YYYY-MM-DD` |
| `month` | No | `1`-`12` for flexible dates |
| `travel_duration` | No | `1` = weekend, `2` = 1 week, `3` = 2 weeks |
| `interest` | No | `/g/11bc58l13w` = Outdoors, `/m/0b3yr` = Beaches |
| `include_airlines` | No | Filter by airline or alliance |
| `max_price` | No | Maximum price |
| `stops` | No | Same as Google Flights |

## Workflow: Compare Award vs Cash

1. Search cash prices on Google Flights via SerpAPI
2. Estimate portal cost. Chase uses dynamic "Points Boost" pricing (~1.5-2.0cpp on select bookings, not a flat rate). Amex/Capital One ~1.0cpp. For rough math, run the actual portal quote against the cash price; do not assume a flat cpp on Chase.
3. Compare with award price from Seats.aero
4. Lower number wins (accounting for the value you place on each currency)

## Notes

- Cached results are free (1hr cache). Set `no_cache=true` to force fresh.
- `deep_search=true` gives browser-identical results but is slower.
- Results include `price_insights` with historical price data and trend.
- Multi-city supports open jaw itineraries natively.
- Hotels support vacation rentals mode for Airbnb-style results.

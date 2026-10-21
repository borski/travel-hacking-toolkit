---
name: octotrip-rental-cars
description: Real-time rental car search via OctoTrip MCP. Compares prices across multiple vendors worldwide, grouped by SIPP category (economy, compact, SUV, etc.). Free, no API key. Use when the user needs a rental car at a destination, airport transfer by car, or wants to compare rental options. Trigger phrases include rental car, car hire, rent a car, airport car rental, one-way car rental.
category: destinations
summary: Rental car search with real-time pricing across vendors. No API key.
api_key: None (free)
---

# OctoTrip Rental Cars

Search and compare rental cars with real-time pricing from multiple providers worldwide. Results are grouped by SIPP car category with the cheapest options in each.

**Source:** [OctoTrip](https://github.com/octotrip/rental-cars)

## How It Works

This skill uses the `octotrip-rental-cars` MCP server, which is already configured in the toolkit's `.mcp.json`. The agent calls the `search` tool directly — no scripts, no API key, no setup.

## When to Use

- "Find me a rental car at Munich Airport for July 10-15"
- "Compare SUVs available in Barcelona next week"
- "One-way car rental from Berlin to Hamburg"
- "Cheapest economy car at London Heathrow for a week"
- "I need airport transfer options" (rental car as one option alongside transit)
- Any trip plan that includes ground transport at the destination

## When NOT to Use

- **Booking.** This tool finds and compares rental cars. It returns booking links but does not complete purchases.
- **Ride-sharing / taxis.** This is traditional car rental only.
- **Trains / public transit.** Use `deutsche-bahn` or `scandinavia-transit`.

## MCP Tool: `search`

The `octotrip-rental-cars` MCP server exposes a single `search` tool.

### Parameters

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `location` | string | yes | — | Pickup location: city, airport, station, address |
| `pickup_date` | string | yes | — | Pickup date (YYYY-MM-DD) |
| `dropoff_date` | string | yes | — | Dropoff date (YYYY-MM-DD) |
| `dropoff_location` | string | no | same as pickup | Different location for one-way rentals |
| `pickup_time` | string | no | `"12:00"` | Pickup time (HH:MM, 24h) |
| `dropoff_time` | string | no | `"12:00"` | Dropoff time (HH:MM, 24h) |
| `currency` | string | no | `"EUR"` | ISO 4217 currency code |
| `language` | string | no | `"en"` | Response language |
| `age` | integer | no | `30` | Driver age (min 18) |

### Response Shape

```json
{
  "results": [
    {
      "name": "Volkswagen Golf",
      "vendor": "Europcar",
      "sipp": "CDMR",
      "category": "Compact",
      "price": 181.03,
      "price_per_day": 45.26,
      "currency": "EUR",
      "transmission": "manual",
      "passengers": 5,
      "bags": 1,
      "air_con": true,
      "fuel_policy": "Full to Full",
      "mileage": "Unlimited",
      "free_cancellation": true,
      "included_protections": ["Collision Damage Waiver", "Theft Protection"],
      "deposit": 800,
      "excess": 950,
      "booking_url": "https://...",
      "link_type": "affiliate",
      "affiliate_disclosure": "..."
    }
  ],
  "total": 23,
  "total_available": 379,
  "rental_days": 4,
  "pickup_location_resolved": "Munich International Airport",
  "dropoff_location_resolved": "Munich International Airport"
}
```

### Key Fields for Comparison

- **`price`** / **`price_per_day`**: total and daily rate
- **`category`**: SIPP-based grouping (Mini, Economy, Compact, Standard, Full-size, SUV, etc.)
- **`free_cancellation`**: important for tentative trip plans
- **`deposit`** / **`excess`**: hidden costs — flag high deposits to the user
- **`transmission`**: manual vs automatic matters by market (EU defaults to manual)
- **`mileage`**: Unlimited vs capped — critical for road trips

### Presenting Results

Show a table grouped by category. Always include:
- Category, vehicle name, vendor
- Price per day and total
- Transmission, passengers, bags
- Free cancellation status
- Booking link

Flag one-way surcharges, young driver fees (age < 25), and high deposits.

### Affiliate Disclosure

Booking links contain affiliate attribution. Mention once: "Booking links may include affiliate attribution — OctoTrip may earn a commission at no extra cost to you." Results are ranked by price, not affiliate payout.

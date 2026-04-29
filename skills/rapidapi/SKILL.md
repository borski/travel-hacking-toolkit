---
name: rapidapi
description: Search Google Flights Live and Booking.com Live via RapidAPI. Use as a secondary source for flight cash prices and hotel availability/pricing. Triggers on "Booking.com", "booking prices", "RapidAPI", "secondary flight search", "hotel prices on Booking", or when SerpAPI results need a second opinion. Also useful for vacation rental pricing.
category: hotels
summary: Booking.com hotel prices.
api_key: RapidAPI
license: MIT
---

# RapidAPI Skill

Search Google Flights and Booking.com via RapidAPI scrapers. Secondary source for cash flight prices and hotel/vacation rental pricing.

**Sources:**
- [Google Flights Live API on RapidAPI](https://rapidapi.com/apiheya/api/google-flights-live-api)
- [Booking.com Live API on RapidAPI](https://rapidapi.com/apiheya/api/booking-live-api)

## Authentication

`RAPIDAPI_KEY` is set in `.env`. All requests use `x-rapidapi-key` header.

## Google Flights Live API

Real-time Google Flights scraping. Use when SerpAPI results seem stale or you want a second price opinion.

### Search One-Way

```bash
curl -s -X POST "https://google-flights-live-api.p.rapidapi.com/api/v1/searchFlights" \
  -H "x-rapidapi-key: $RAPIDAPI_KEY" \
  -H "x-rapidapi-host: google-flights-live-api.p.rapidapi.com" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "SFO",
    "destination": "NRT",
    "date": "2026-08-10",
    "adults": 2,
    "cabinClass": "economy",
    "currency": "USD"
  }' | jq '.'
```

### Search Round Trip

```bash
curl -s -X POST "https://google-flights-live-api.p.rapidapi.com/api/v1/searchFlights" \
  -H "x-rapidapi-key: $RAPIDAPI_KEY" \
  -H "x-rapidapi-host: google-flights-live-api.p.rapidapi.com" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "SFO",
    "destination": "NRT",
    "date": "2026-08-10",
    "returnDate": "2026-08-26",
    "adults": 2,
    "cabinClass": "economy",
    "currency": "USD"
  }' | jq '.'
```

### Parameters

| Param | Required | Description |
|-------|----------|-------------|
| `origin` | Yes | Airport IATA code |
| `destination` | Yes | Airport IATA code |
| `date` | Yes | `YYYY-MM-DD` departure |
| `returnDate` | No | `YYYY-MM-DD` for round trip |
| `adults` | No | Default 1 |
| `children` | No | Default 0 |
| `infants` | No | Default 0 |
| `cabinClass` | No | `economy`, `premium_economy`, `business`, `first` |
| `currency` | No | Default `USD` |

## Booking.com Live API

Search hotels and vacation rentals with real Booking.com pricing. Good complement to SerpAPI Hotels and LiteAPI.

### Search Hotels

```bash
curl -s "https://booking-live-api.p.rapidapi.com/api/v1/searchHotels?location=Tokyo%2C%20Japan&checkin=2026-08-10&checkout=2026-08-13&adults=2&rooms=1&currency=USD" \
  -H "x-rapidapi-key: $RAPIDAPI_KEY" \
  -H "x-rapidapi-host: booking-live-api.p.rapidapi.com" | jq '.'
```

### Parameters

| Param | Required | Description |
|-------|----------|-------------|
| `location` | Yes | City/area name: `Tokyo, Japan` |
| `checkin` | Yes | `YYYY-MM-DD` |
| `checkout` | Yes | `YYYY-MM-DD` |
| `adults` | No | Default 2 |
| `children` | No | Default 0 |
| `rooms` | No | Default 1 |
| `currency` | No | Default `USD` |
| `sortBy` | No | `price`, `rating`, `popularity` |
| `minPrice` | No | Minimum price filter |
| `maxPrice` | No | Maximum price filter |
| `starRating` | No | `3,4,5` comma-separated |

### Get Hotel Details

```bash
curl -s "https://booking-live-api.p.rapidapi.com/api/v1/getHotelDetails?hotelId=HOTEL_ID&checkin=2026-08-10&checkout=2026-08-13&adults=2" \
  -H "x-rapidapi-key: $RAPIDAPI_KEY" \
  -H "x-rapidapi-host: booking-live-api.p.rapidapi.com" | jq '.'
```

## Rate Limits

Free tier: 100 requests/month across all RapidAPI APIs.
Use sparingly. Prefer SerpAPI for flights and LiteAPI/SerpAPI for hotels as primary sources.

## When to Use

- **Google Flights Live**: Secondary price check when SerpAPI results seem off, or for routes SerpAPI doesn't cover well.
- **Booking.com Live**: When you want Booking.com specific pricing/availability (different inventory than Google Hotels).

Do not:
- Use as primary search (SerpAPI and Seats.aero are primary).
- Burn through free tier on broad searches. Be targeted.

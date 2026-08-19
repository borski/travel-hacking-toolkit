---
name: rapidapi
description: Search flights and hotels (Booking.com pricing) via the RapidAPI Air Scraper API. Secondary source for cash flight prices and hotel availability when SerpAPI needs a second opinion.
category: hotels
summary: Booking.com hotel prices.
api_key: RapidAPI
license: MIT
---

# RapidAPI Skill

Search flights and hotels (Booking.com inventory) via RapidAPI. Secondary source for cash flight prices and hotel/vacation rental pricing.

**Source:** [Air Scraper (Sky Scrapper) by apiheya](https://rapidapi.com/apiheya/api/sky-scrapper). Host: `sky-scrapper.p.rapidapi.com`.

## Authentication

`RAPIDAPI_KEY` is set in `.env`. All requests use the `x-rapidapi-key` and `x-rapidapi-host` headers.


## Hotels (Booking.com pricing)

Two-step flow: resolve the city to an `entityId`, then search.

### 1. Location Lookup

```bash
curl -s "https://sky-scrapper.p.rapidapi.com/api/v1/hotels/searchDestinationOrHotel?query=Tokyo" \
  -H "x-rapidapi-key: $RAPIDAPI_KEY" \
  -H "x-rapidapi-host: sky-scrapper.p.rapidapi.com" | jq '.'
```

### 2. Search Hotels

Use the `entityId` from step 1.

```bash
curl -s "https://sky-scrapper.p.rapidapi.com/api/v1/hotels/searchHotels?entityId=ENTITY_ID&checkin=2026-08-10&checkout=2026-08-13&adults=2&rooms=1&currency=USD&market=en-US&limit=20" \
  -H "x-rapidapi-key: $RAPIDAPI_KEY" \
  -H "x-rapidapi-host: sky-scrapper.p.rapidapi.com" | jq '.'
```

### 3. Hotel Details and Live OTA Prices

`hotelId` comes from step 2. `getHotelPrices` returns live rates from Booking.com, Expedia, and Hotels.com with booking links.

```bash
curl -s "https://sky-scrapper.p.rapidapi.com/api/v1/hotels/getHotelDetails?hotelId=HOTEL_ID&entityId=ENTITY_ID&currency=USD&market=en-US" \
  -H "x-rapidapi-key: $RAPIDAPI_KEY" \
  -H "x-rapidapi-host: sky-scrapper.p.rapidapi.com" | jq '.'

curl -s "https://sky-scrapper.p.rapidapi.com/api/v1/hotels/getHotelPrices?hotelId=HOTEL_ID&entityId=ENTITY_ID&checkin=2026-08-10&checkout=2026-08-13&adults=2&rooms=1&currency=USD&market=en-US" \
  -H "x-rapidapi-key: $RAPIDAPI_KEY" \
  -H "x-rapidapi-host: sky-scrapper.p.rapidapi.com" | jq '.'
```

### Parameters

| Param | Required | Description |
|-------|----------|-------------|
| `query` | Yes | City/landmark name for `searchDestinationOrHotel` |
| `entityId` | Yes | From the location lookup |
| `hotelId` | Yes | From `searchHotels` results (for detail/pricing calls) |
| `checkin` | Yes | `YYYY-MM-DD` |
| `checkout` | Yes | `YYYY-MM-DD` |
| `adults` | No | Default 2 |
| `rooms` | No | Default 1 |
| `currency` | No | Default `USD` |
| `market` | No | e.g. `en-US` |
| `limit` | No | Results per page |

## Flights

### 1. Airport Lookup

Returns matching airports with `skyId` and `entityId` under `navigation.relevantFlightParams`:

```bash
curl -s "https://sky-scrapper.p.rapidapi.com/api/v1/flights/searchAirport?query=JFK" \
  -H "x-rapidapi-key: $RAPIDAPI_KEY" \
  -H "x-rapidapi-host: sky-scrapper.p.rapidapi.com" | jq '.'
```

### 2. Search Flights

`GET /api/v1/flights/searchFlights` and `/api/v2/flights/searchFlights` take `originSkyId`, `destinationSkyId`, `originEntityId`, `destinationEntityId`, `date`, `adults`, `cabinClass`, `currency`. Both return a server error (`status: false`) in testing — prefer SerpAPI for flight search until apiheya fixes this.

## Rate Limits

- **BASIC** (free): 20 requests/month — very tight.
- **PRO** $9.99/mo: 10,600 requests/month.

A full hotel search is 3+ calls (location + search + prices), so the free tier covers roughly one trip. Use sparingly.

## When to Use

- **Air Scraper flights**: Secondary price check when SerpAPI results seem off, or for routes SerpAPI doesn't cover well.
- **Air Scraper hotels**: When you want Booking.com specific pricing/availability (different inventory than Google Hotels).

Do not:
- Use as primary search (SerpAPI and Seats.aero are primary).
- Burn through the free tier on broad searches. Be targeted.

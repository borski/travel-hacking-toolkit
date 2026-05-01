---
name: tripadvisor
description: TripAdvisor Content API for hotel ratings, restaurant search, attraction reviews, rankings, and nearby locations. Use when evaluating hotels or researching destinations. 5K calls/month.
category: destinations
summary: Hotel ratings, restaurant search, attraction reviews, nearby search. 5K calls/month.
api_key: TripAdvisor
license: MIT
compatibility: opencode
metadata:
  type: integration
  platform: any
---

# TripAdvisor Content API

Search and retrieve hotel, restaurant, and attraction data from TripAdvisor. Ratings, rankings, reviews, photos, amenities, subratings, trip types, awards.

**Base URL:** `https://api.content.tripadvisor.com/api/v1`

**Rate limit:** 50 calls per second.

**Monthly quota:** 5,000 API calls per month. Each curl request = 1 call. A full hotel lookup (search + details + reviews + photos) = 4 calls. Budget accordingly. Prefer search + details (2 calls) and only fetch reviews/photos when specifically needed.

**API limits:** Up to 10 results per search. Up to 5 reviews and 5 photos per location.

## Authentication

Set `TRIPADVISOR_API_KEY` in your `.env` file:

```bash
# In .env (gitignored)
TRIPADVISOR_API_KEY=your_key_here
```

Then source it before calling:

```bash
export $(grep TRIPADVISOR_API_KEY .env | xargs)
```

## Endpoints

### 1. Location Search

Find locations by name. Returns up to 10 results.

```bash
curl -s "https://api.content.tripadvisor.com/api/v1/location/search?key=$TRIPADVISOR_API_KEY&searchQuery=NOFO+Hotel+Stockholm&category=hotels&language=en"
```

**Parameters:**

| Param | Required | Description |
|-------|----------|-------------|
| `searchQuery` | Yes | Text search query (name of hotel, restaurant, city) |
| `category` | No | Filter: `hotels`, `restaurants`, `attractions`, `geos` |
| `phone` | No | Phone number filter (any format, no leading +) |
| `address` | No | Address filter |
| `latLong` | No | Lat/long pair, e.g. `59.3127,18.0716` |
| `radius` | No | Radius from latLong (number) |
| `radiusUnit` | No | `km`, `mi`, or `m` |
| `language` | No | Default `en`. Supports 40+ languages. |

**Response shape:**

```json
{
  "data": [
    {
      "location_id": "237656",
      "name": "Nofo Hotel",
      "address_obj": {
        "street1": "Tjarhovsgatan 11",
        "city": "Stockholm",
        "country": "Sweden",
        "postalcode": "116 21",
        "address_string": "Tjarhovsgatan 11, Stockholm 116 21 Sweden"
      }
    }
  ]
}
```

### 2. Location Details

Get comprehensive info for a location by ID. This is the richest endpoint.

```bash
curl -s "https://api.content.tripadvisor.com/api/v1/location/{locationId}/details?key=$TRIPADVISOR_API_KEY&language=en&currency=USD"
```

**Parameters:**

| Param | Required | Description |
|-------|----------|-------------|
| `locationId` | Yes (path) | TripAdvisor location ID from search |
| `language` | No | Default `en` |
| `currency` | No | ISO 4217 code, default `USD` |

**Response includes:**

- `name`, `web_url`, `address_obj`, `latitude`, `longitude`, `timezone`, `phone`
- `rating` (string, e.g. "4.6"), `num_reviews` (string, e.g. "845")
- `review_rating_count`: breakdown by star (`{"1": "7", "2": "10", ...}`)
- `ranking_data`: `ranking` (#10), `ranking_out_of` (168), `ranking_string` ("#10 of 168 hotels in Stockholm")
- `subratings`: Location, Sleep Quality, Rooms, Service, Value, Cleanliness (each 0.0 to 5.0)
- `price_level`: "$", "$$", "$$$", "$$$$"
- `amenities`: array of strings
- `styles`: array (e.g. "Family", "Centrally Located")
- `neighborhood_info`: array with location_id and name
- `trip_types`: business, couples, solo, family, friends with count values
- `awards`: Travelers Choice, Best of Best, etc. with year and images
- `parent_brand`, `brand`: chain affiliation
- `category`, `subcategory`: hotel/restaurant/attraction
- `photo_count`, `see_all_photos` URL
- `write_review` URL

### 3. Location Reviews

Get up to 5 most recent reviews.

```bash
curl -s "https://api.content.tripadvisor.com/api/v1/location/{locationId}/reviews?key=$TRIPADVISOR_API_KEY&language=en"
```

**Parameters:**

| Param | Required | Description |
|-------|----------|-------------|
| `locationId` | Yes (path) | TripAdvisor location ID |
| `language` | No | Default `en` |
| `limit` | No | Number of results (max 5 on free tier) |
| `offset` | No | Index of first result |

**Response shape:**

```json
{
  "data": [
    {
      "id": 123456,
      "lang": "en",
      "location_id": "237656",
      "published_date": "2026-03-15T00:00:00-04:00",
      "rating": 5,
      "text": "Review text...",
      "title": "Review title",
      "trip_type": "Couples",
      "travel_date": "2026-03",
      "user": { "username": "traveler123" },
      "subratings": {}
    }
  ]
}
```

**Note:** Reviews may return empty `data: []` for locations with few English reviews. Try different `language` values for international hotels.

### 4. Location Photos

Get up to 5 recent photos with multiple size options.

```bash
curl -s "https://api.content.tripadvisor.com/api/v1/location/{locationId}/photos?key=$TRIPADVISOR_API_KEY&language=en"
```

**Parameters:**

| Param | Required | Description |
|-------|----------|-------------|
| `locationId` | Yes (path) | TripAdvisor location ID |
| `language` | No | Default `en` |
| `limit` | No | Number of results (max 5 on free tier) |
| `offset` | No | Index of first result |
| `source` | No | Comma-separated: `Expert`, `Management`, `Traveler` |

**Photo sizes in response:**

- `thumbnail`: 50x50 cropped
- `small`: 150x150 cropped
- `medium`: max 250px dimension
- `large`: max 550px dimension
- `original`: full resolution

### 5. Nearby Location Search

Find locations near coordinates. Returns up to 10.

```bash
curl -s "https://api.content.tripadvisor.com/api/v1/location/nearby_search?key=$TRIPADVISOR_API_KEY&latLong=59.3127,18.0716&category=hotels&language=en"
```

**Parameters:**

| Param | Required | Description |
|-------|----------|-------------|
| `latLong` | Yes | Lat/long pair, e.g. `59.3127,18.0716` |
| `category` | No | `hotels`, `restaurants`, `attractions`, `geos` |
| `phone` | No | Phone number filter |
| `address` | No | Address filter |
| `radius` | No | Radius from latLong |
| `radiusUnit` | No | `km`, `mi`, `m` |
| `language` | No | Default `en` |

**Response includes `distance` (km) and `bearing` (e.g. "northwest") for each result.**

## Common Workflows

### Hotel Research (most common)

```bash
# 1. Search for hotel
curl -s "https://api.content.tripadvisor.com/api/v1/location/search?key=$TRIPADVISOR_API_KEY&searchQuery=Amerikalinjen+Oslo&category=hotels" | python3 -m json.tool

# 2. Get details with location_id from step 1
curl -s "https://api.content.tripadvisor.com/api/v1/location/1234567/details?key=$TRIPADVISOR_API_KEY&currency=USD" | python3 -m json.tool

# 3. Get reviews (optional, costs 1 call)
curl -s "https://api.content.tripadvisor.com/api/v1/location/1234567/reviews?key=$TRIPADVISOR_API_KEY" | python3 -m json.tool

# 4. Get photos (optional, costs 1 call)
curl -s "https://api.content.tripadvisor.com/api/v1/location/1234567/photos?key=$TRIPADVISOR_API_KEY" | python3 -m json.tool
```

### Compare Multiple Hotels in a City

```bash
# Search all hotels in city
curl -s "https://api.content.tripadvisor.com/api/v1/location/search?key=$TRIPADVISOR_API_KEY&searchQuery=hotels+Copenhagen&category=hotels"

# Then get details for each location_id returned
# Compare: rating, num_reviews, ranking_data.ranking, subratings, price_level, amenities
```

### Find Restaurants Near Hotel

```bash
# Use hotel's lat/long from details response
curl -s "https://api.content.tripadvisor.com/api/v1/location/nearby_search?key=$TRIPADVISOR_API_KEY&latLong=59.31555,18.078924&category=restaurants"
```

### Destination Research

```bash
# Search for attractions
curl -s "https://api.content.tripadvisor.com/api/v1/location/search?key=$TRIPADVISOR_API_KEY&searchQuery=things+to+do+Stockholm&category=attractions"

# Nearby attractions from a point
curl -s "https://api.content.tripadvisor.com/api/v1/location/nearby_search?key=$TRIPADVISOR_API_KEY&latLong=59.3293,18.0686&category=attractions"
```

## When to Use

- Evaluating hotels (ratings, rankings, subratings, review sentiment)
- Comparing restaurants near a hotel or in a neighborhood
- Finding attractions and things to do near a destination
- Getting TripAdvisor ranking data ("#1 of 168 hotels in Stockholm")
- Checking amenities, trip type breakdown, award status
- Verifying hotel chain affiliation and neighborhood info

## When NOT to Use

- **Pricing or availability.** TripAdvisor Content API has no pricing data. Use `serpapi`, `liteapi`, `chase-travel`, `amex-travel`, or `rapidapi` for prices.
- **Booking.** This is read-only data. No booking capability.
- **Bulk scraping.** 5,000 calls/month. Be deliberate.

## Key Data Points for Hotel Comparison

When comparing hotels, extract and present:

| Field | Path | Example |
|-------|------|---------|
| Rating | `rating` | "4.6" |
| Review count | `num_reviews` | "845" |
| Ranking | `ranking_data.ranking_string` | "#10 of 168 hotels in Stockholm" |
| Location subrating | `subratings.0.value` | "4.7" |
| Service subrating | `subratings.3.value` | "4.7" |
| Cleanliness subrating | `subratings.5.value` | "4.8" |
| Price level | `price_level` | "$$$$" |
| Trip type leader | highest `trip_types[].value` | "Couples: 381" |
| Awards | `awards[].display_name` | "Travelers Choice 2025" |
| Breakfast | `amenities` contains "Breakfast included" | Yes/No |
| Chain | `parent_brand` | "Worldhotels" |

## Supported Languages

`ar`, `zh`, `zh_TW`, `da`, `nl`, `en`, `en_AU`, `en_CA`, `en_HK`, `en_IN`, `en_IE`, `en_MY`, `en_NZ`, `en_PH`, `en_SG`, `en_ZA`, `en_UK`, `fr`, `fr_BE`, `fr_CA`, `fr_CH`, `de`, `de_AT`, `el`, `iw`, `it`, `it_CH`, `ja`, `ko`, `no`, `pt`, `pt_PT`, `ru`, `es`, `es_AR`, `es_CO`, `es_MX`, `es_PE`, `es_VE`, `es_CL`, `sv`, `th`, `tr`, `vi`

Use `da` for Danish, `no` for Norwegian, `sv` for Swedish when searching Scandinavian hotels for local-language reviews.

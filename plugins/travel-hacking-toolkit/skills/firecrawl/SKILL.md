---
name: firecrawl
description: Agoda hotel prices through Firecrawl Alexandria. Room-level refundable vs non-refundable totals with cancellation terms for exact dates, city search with tax-inclusive prices, and Agoda plus Booking.com guest reviews with category grades against the city average. Use for the cash side of a points-vs-cash hotel decision and as an extra source in compare-hotels. Needs FIRECRAWL_API_KEY. Triggers include Agoda price, Agoda rates, hotel room rates, refundable rate, hotel reviews breakdown.
category: hotels
summary: Agoda room-level rates with cancellation terms, city search, and review grades vs the city average, via Firecrawl Alexandria.
api_key: Firecrawl (free tier)
license: MIT
---

# Firecrawl Skill

Agoda hotel search through [Firecrawl Alexandria](https://alexandria.firecrawl.dev/agoda-com?utm_source=travel-hacking-toolkit&utm_medium=integration), a catalog of structured data providers called through the Firecrawl API. Every call is read-only. Nothing here books, holds, or signs in.

**Source:** [firecrawl.dev](https://www.firecrawl.dev/?utm_source=travel-hacking-toolkit&utm_medium=integration). The free plan includes 1,000 credits a month, about 200 calls. A hotel comparison (suggest plus search) spends about 10 credits.

## Authentication

`FIRECRAWL_API_KEY` is set in `.env`. All requests go to one endpoint with `Authorization: Bearer $FIRECRAWL_API_KEY`:

```
POST https://api.firecrawl.dev/v2/scrape
```

The body names a provider, a capability, and its options:

```json
{
  "origin": "travel-hacking-toolkit",
  "alexandria": {
    "provider": "agoda-com",
    "capability": "hotels/suggest",
    "options": {"query": "Park Hyatt Tokyo"}
  }
}
```

The result is at `.data.alexandria[0].data`. Request and provider errors come back inside an HTTP 200 at `.data.alexandria[0].error`, so check that field, not just the status code. Account-level problems (bad key, no credits) come back as a non-200 status instead. Calls are currently 5 credits each, see `.data.creditsCost`.

## 1. Turn a place or hotel name into Agoda ids

```bash
curl -s https://api.firecrawl.dev/v2/scrape \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "travel-hacking-toolkit",
    "alexandria": {
      "provider": "agoda-com",
      "capability": "hotels/suggest",
      "options": {"query": "Park Hyatt Tokyo"}
    }
  }' | jq '.data.alexandria[0] | .error // [.data.results[] | {kind, name, city_name, city_id, object_id}]'
```

`kind` is `city`, `area`, `landmark`, or `property`. For a property, `object_id` is the `property_id`. For a landmark, it is the `landmark_id`. For a city or area, search with `city_id`.

## 2. Search a city for exact dates

```bash
curl -s https://api.firecrawl.dev/v2/scrape \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "travel-hacking-toolkit",
    "alexandria": {
      "provider": "agoda-com",
      "capability": "hotels/search",
      "options": {"city_id": 5085, "check_in": "2026-12-10", "nights": 2, "adults": 2, "page_size": 20}
    }
  }' | jq '.data.alexandria[0] | .error // [.data.properties[] | select(.price != null) | {name, property_id, stars: .star_rating, review_score, review_count, per_night: .price.per_night_inclusive, total: .price.total_inclusive, free_cancellation_until, sponsored: .is_sponsored, url}]'
```

| Option | Required | Description |
|--------|----------|-------------|
| `city_id` or `landmark_id` | Yes | From `hotels/suggest`. Pass one, not both |
| `check_in` | No | `YYYY-MM-DD`, today or later. Defaults to 30 days from today |
| `nights` | No | 1 to 30. Default 1 |
| `adults` / `children` / `child_ages` | No | Default 2 adults |
| `rooms` | No | Default 1 |
| `currency` | No | ISO 4217 code. Default `USD` |
| `sort` | No | `recommended` (default), `price_asc`, `price_desc`, `review_score` |
| `page` / `page_size` | No | `page_size` up to 45 |

Prices: `per_night_inclusive` and `total_inclusive` include taxes and fees. The `_exclusive` fields do not.

Watch for:
- Sold-out or not-yet-priced properties come back with `price: null`. With `sort: price_asc` they can be listed first. Drop them with `select(.price != null)`.
- Agoda can return extra rows beyond `page_size`, often sponsored. `is_sponsored` marks the sponsored ones.

## 3. Room types and rate plans for one hotel

The step to run before a points-vs-cash decision. Every room type with its refundable and non-refundable offers, tax-inclusive totals, breakfast, and cancellation terms.

```bash
curl -s https://api.firecrawl.dev/v2/scrape \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "travel-hacking-toolkit",
    "alexandria": {
      "provider": "agoda-com",
      "capability": "hotels/property_rooms",
      "options": {"property_id": 910, "check_in": "2026-12-10", "nights": 2, "adults": 2}
    }
  }' | jq '.data.alexandria[0] | .error // (.data | {name, check_in, check_out, currency, rooms: [.room_types[] | {room: .name, offers: [.offers[] | {total: .total_inclusive, per_night: .per_night_inclusive, refundable: .free_cancellation, breakfast: .breakfast_included, terms: .cancellation_title}]}]})'
```

## 4. Guest reviews and category grades

```bash
curl -s https://api.firecrawl.dev/v2/scrape \
  -H "Authorization: Bearer $FIRECRAWL_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "origin": "travel-hacking-toolkit",
    "alexandria": {
      "provider": "agoda-com",
      "capability": "hotels/property_reviews",
      "options": {"property_id": 910, "page_size": 10, "sort": "most_recent"}
    }
  }' | jq '.data.alexandria[0] | .error // (.data | {name, score: .score.score, review_count: .score.review_count, grades: [.score.grades[] | {name, score, city_average}], sources: .providers, reviews: [.reviews[] | {provider_name, rating, title, text, positives, negatives, reviewer_group, review_date}]})'
```

`score.grades` breaks the score into cleanliness, facilities, location, room comfort, service, and value for money, each next to the city average. Reviews come from Agoda and Booking.com. Pass `"provider_id": 332` for Agoda reviews only. `sort` takes `most_recent`, `rating_high_to_low`, `rating_low_to_high`, or `most_helpful`.

## Firecrawl MCP

If the [Firecrawl MCP server](https://docs.firecrawl.dev/mcp-server?utm_source=travel-hacking-toolkit&utm_medium=integration) is connected, its `firecrawl_scrape` tool takes the same `alexandria` object and returns the same data. The curl calls above need no extra setup.

## When to Use

- **Cash rate for a points redemption:** `hotels/property_rooms` on the exact hotel and dates, then compare the cheapest refundable total with the points price in `points-valuations` or `trip-calculator`.
- **Hotel comparison:** run `hotels/suggest`, then `hotels/search`, alongside SerpAPI, Trivago, and LiteAPI in `compare-hotels`. What this adds is Agoda's room-level rate grid: refundable and non-refundable totals per room type with their cancellation terms.
- **Quality check:** `hotels/property_reviews` for category grades against the city average.

## Failure Modes

| Symptom | Cause | What to do |
|---------|-------|------------|
| HTTP 401 `Unauthorized: Invalid token`, or HTTP 403 with no key | Wrong or missing `FIRECRAWL_API_KEY` | Skip this source and continue with the others |
| HTTP 402 `insufficient_credits` | The Firecrawl team is out of credits. Nothing ran | Tell the user, skip this source |
| HTTP 403 `THIRD_PARTY_DATA_TERMS_REQUIRED` | The provider's terms have not been accepted for this Firecrawl team | Tell the user to accept them at `requiresAction.url`. Do not accept on their behalf |
| HTTP 429 | Rate limit | Back off a few seconds and retry |
| HTTP 5xx, or an upstream error in `.error` | Firecrawl or Agoda had a problem | Retry once, then skip this source |
| `.error.code` is `missing_option` or `invalid_option` | Bad request, such as a past `check_in` or both `city_id` and `landmark_id` | Fix the options. Retrying the same request won't help |
| `.error.code` is `not_found` | Wrong id type (a landmark id passed as `city_id`) or an id that doesn't exist | Re-run `hotels/suggest` and use the id that matches `kind` |
| `hotels/suggest` returns `count: 0` with no error | Agoda doesn't recognize the name. The call is still billed | Try a shorter name or the city |
| `properties` empty and `total_properties: 0` | No availability, or a currency code Agoda doesn't know (also billed) | Check `currency`, try other dates |
| `price: null` on a search row | Sold out or not priced for those dates | Drop the row, or check `hotels/property_rooms` for that property |

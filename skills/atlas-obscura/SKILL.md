---
name: atlas-obscura
description: Search Atlas Obscura for weird, wonderful, and hidden gem places near any destination. Find the interesting stuff, not boring plaques. Search by coordinates, get full details with descriptions and images.
category: destinations
summary: Hidden gems and unusual attractions near any destination.
api_key: None (free)
license: MIT
---

# Atlas Obscura

Find genuinely interesting hidden gems near any destination via Atlas Obscura. Searches by coordinates, scores places for interestingness, and filters out mundane historical markers.

No API key needed. Uses the [`atlas-obscura-api`](https://github.com/bartholomej/atlas-obscura-api) npm scraper.

## Prerequisites

Install dependencies (one time):

```bash
cd skills/atlas-obscura && npm install
```

## City Coordinates Reference

Common cities for trip planning. Use these with the search commands.

| City | Lat | Lng |
|------|-----|-----|
| New York | 40.7128 | -74.0060 |
| London | 51.5074 | -0.1278 |
| Paris | 48.8566 | 2.3522 |
| Tokyo | 35.6762 | 139.6503 |
| Bangkok | 13.7563 | 100.5018 |
| Rome | 41.9028 | 12.4964 |
| Barcelona | 41.3874 | 2.1686 |
| Istanbul | 41.0082 | 28.9784 |
| Mexico City | 19.4326 | -99.1332 |
| Lisbon | 38.7223 | -9.1393 |
| Seoul | 37.5665 | 126.9780 |
| Oslo | 59.9139 | 10.7522 |
| Copenhagen | 55.6761 | 12.5683 |
| Stockholm | 59.3293 | 18.0686 |

## Commands

All commands run from the repo root. Output is JSON. Image URLs are excluded by default to keep output lean. Add `--images` to any command when you need them (e.g. generating HTML pages).

### Search Nearby (Filtered)

Finds places near coordinates, fetches full details, scores for interestingness, and filters out boring stuff. Slower (fetches each place) but gives you the good stuff.

```bash
node skills/atlas-obscura/ao.mjs search <lat> <lng>
```

Example:
```bash
node skills/atlas-obscura/ao.mjs search 35.6762 139.6503
```

Returns up to 20 places sorted by interest score. Each has full description, tags, and directions.

**Timeout note:** This makes ~20 HTTP requests (one per place). Allow 30-60 seconds.

### Quick Search (Unfiltered)

Fast nearby search. Returns title, subtitle, coordinates, distance. No detail fetching or scoring.

```bash
node skills/atlas-obscura/ao.mjs quick <lat> <lng>
```

### Search Unfiltered with Details

Same as filtered search but keeps everything, including boring plaques.

```bash
node skills/atlas-obscura/ao.mjs search <lat> <lng> --all
```

### Full Place Details

Get complete information for a specific place by ID.

```bash
node skills/atlas-obscura/ao.mjs place <id>
```

Returns: title, subtitle, full description (multi-paragraph), directions, tags, nearby places, interest score.

### Short Place Summary

Quick place lookup without the full scrape. One request.

```bash
node skills/atlas-obscura/ao.mjs short <id>
```

### Including Images

Add `--images` to any command to include thumbnail and image URLs in the output. Useful when generating HTML pages or visual reports.

```bash
node skills/atlas-obscura/ao.mjs search <lat> <lng> --images
node skills/atlas-obscura/ao.mjs place <id> --images
```

## Interest Scoring

Places are scored based on:

**Bonus points for:** Abandoned, Ruins, Ghost Towns, Underground, Caves, Natural Wonders, Unusual Collections, Street Art, Museums, Markets, Hot Springs, Waterfalls, Breweries, Gardens, Islands, Art, Sculpture, Murals. Also: rich descriptions, multiple images.

**Penalties for:** Plaques, Historical Markers, Monuments, War Memorials, Government Buildings. Also: places marked "gone" or hidden from maps.

Places scoring below 0 are filtered out in the default search.

## Useful jq Filters

```bash
# Just titles and subtitles
... | jq '.[] | {title, subtitle, tags}'

# Top 5 by interest score
... | jq '[sort_by(-.interest_score) | .[0:5] | .[] | {title, subtitle, interest_score, url}]'

# Places with specific tags
... | jq '[.[] | select(.tags | any(. == "Underground" or . == "Caves"))]'

# Just URLs for browsing
... | jq -r '.[].url'
```

## When to Use

Load this skill when:
- Planning trips and want to find hidden gems near destinations
- Looking for unique, weird, or wonderful places to visit
- Need Atlas Obscura recommendations for specific coordinates
- Adding interesting stops to an itinerary

Do not:
- Use for booking (AO is discovery only)
- Hammer the scraper excessively (it's scraping atlasobscura.com, be respectful)
- Expect real-time availability (places can close, change hours, etc.)

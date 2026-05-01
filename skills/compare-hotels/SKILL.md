---
name: compare-hotels
description: Unified hotel comparison across Chase Edit, Amex FHR/THC, metasearch, and Airbnb. Highlights premium program benefits, stacking opportunities, and benefit-adjusted pricing.
category: orchestration
summary: Unified hotel comparison across portals, metasearch, and Airbnb. FHR/Edit stacking detection.
api_key: Uses individual skill keys
---

**Companion reference skills.** Load these for deeper context:
- `hotel-chains` — branded property to loyalty program mapping
- `premium-hotels` — FHR / THC / Chase Edit credits and stacking strategy
- `points-valuations` — CPP floor/ceiling for hotel programs (Hyatt 1.4-1.7cpp, Hilton 0.4cpp floor, etc.)
- `fallback-and-resilience` — recovery when a hotel source fails


# Compare Hotels

Search every available source for accommodation and present one unified comparison. Combines portal premium programs (Chase Edit, Amex FHR/THC), cash pricing, and Airbnb alternatives into a single view.

**This is an orchestration skill.** It tells the agent which tools to run and how to combine results. No standalone script.

## When to Use

- "Find me a hotel in Paris for Aug 11-15"
- "Should I book through Chase or Amex for this hotel?"
- "Compare hotels vs Airbnb in Oslo"
- Any accommodation search where the user wants the full picture

## Sources

Run these in parallel where possible. **Never fail silently.**

### Portal Premium Programs (Docker required)

| Source | Skill | Speed | What It Finds |
|--------|-------|-------|---------------|
| Chase Travel | `chase-travel` | ~45s | Edit hotels ($100 credit, breakfast, upgrade), Points Boost, standard hotels |
| Amex Travel | `amex-travel` | ~45s | FHR ($100+ credit, breakfast, upgrade, late checkout), THC ($100 credit on 2+ nights) |

### Cash Prices and Metasearch

| Source | Skill/Tool | Speed | What It Finds |
|--------|------------|-------|---------------|
| SerpAPI | `serpapi` | ~3s | Google Hotels cash prices and direct booking links. |
| Trivago | web search | ~5s | Metasearch across many OTAs. Use tavily/exa to search `trivago.com`. Finds the absolute cheapest OTA rate. |
| LiteAPI | web search | ~5s | Hotel API aggregator with negotiated rates. Check `liteapi.travel`. Can find rates below public OTA pricing. |
| RapidAPI | `rapidapi` | ~3s | Booking.com inventory and pricing. Optional, use when user asks for Booking.com specifically. |

### Quality and Ratings

| Source | Skill/Tool | Speed | What It Finds |
|--------|------------|-------|---------------|
| TripAdvisor | `tripadvisor` | ~2s | Ratings, rankings, subratings (location/service/cleanliness), reviews, photos, amenities, awards. 5K calls/month. |

**SerpAPI, Trivago, and LiteAPI are all default.** Always search all three. Only add RapidAPI if the user asks for Booking.com specifically. Use TripAdvisor for quality data (ratings, rankings, reviews) to complement pricing from other sources.

### Vacation Rentals

| Source | Skill/Tool | Speed | What It Finds |
|--------|------------|-------|---------------|
| Airbnb | `airbnb_search` MCP tool | ~5s | Entire homes, private rooms, with total pricing |

### Premium Property Databases (local, instant)

| Source | Data File | What It Finds |
|--------|-----------|---------------|
| FHR properties | `data/fhr-properties.json` | Check if a hotel is FHR before booking |
| THC properties | `data/thc-properties.json` | Check if a hotel is THC |
| Chase Edit properties | `data/chase-edit-properties.json` | Check if a hotel is in Chase's Edit program |

## Workflow

### Step 1: Search All Sources

```
PARALLEL GROUP 1 (fast, ~3-5s):
  - SerpAPI: Google Hotels cash prices
  - Trivago: metasearch across OTAs (web search)
  - LiteAPI: negotiated hotel rates (web search)
  - Airbnb: vacation rentals in the area
  - Local data: check premium-hotels databases for the city

PARALLEL GROUP 2 (slow, ~45s, Docker):
  - Chase Travel: --hotel --dest "City" --checkin YYYY-MM-DD --checkout YYYY-MM-DD --json
  - Amex Travel: --hotel --dest "City" --checkin YYYY-MM-DD --checkout YYYY-MM-DD --json
```

For each source, capture:
- Source name
- Status: "ok" | "error: {reason}" | "skipped: {reason}"
- Results count
- Data

### Step 2: Identify Stacking Opportunities

Cross-reference results with `data/fhr-properties.json`, `data/thc-properties.json`, and `data/chase-edit-properties.json`:

```
For each hotel in results:
  - Is it in FHR? → Tag [FHR]
  - Is it in THC? → Tag [THC]
  - Is it in Chase Edit? → Tag [EDIT]
  - Is it in multiple? → Tag [FHR+EDIT] and note stacking potential
```

Stacking means: book through one portal, pay with the other card separately. For example, book FHR through Amex (get breakfast + credit + upgrade), then use CSR $300 travel credit on something else at the property.

### Step 3: Calculate Points Value

**Chase:**
- Chase portal pricing on CSR/CSP is dynamic Points Boost. Each booking quotes a specific points price; effective cpp typically falls in the 1.5-2.0 cpp range on CSR but is not a guaranteed floor on every booking. Pull the actual portal quote.
- Points Boost offers are dynamic and vary by route/date/inventory.
- The portal quote IS the actual UR cost. Don't divide by 1.5 — the listed points already reflect the dynamic Boost rate at quote time.

**Amex:**
- Hotel portal pricing is variable (NOT always 1 cpp like flights).
- The points price shown is the actual MR cost. Calculate CPP from cash/points ratio.
- FHR benefits ($100+ credit, breakfast) offset the rate significantly.

**Calculate benefit-adjusted price:**
```
FHR adjusted = total_price - $100 credit - (breakfast_value × nights)
  breakfast_value ≈ $30-50/person × 2 people = $60-100/night
THC adjusted = total_price - $100 credit (2+ night stays only)
Edit adjusted = total_price - $100 credit - (breakfast_value × nights)
```

### Step 4: Present Unified Table

**Always use markdown tables.** Hotels sorted by benefit-adjusted total price.

#### Example: Paris, Aug 11-15 (4 nights, 2 guests)

| # | Hotel | Program | Stars | Per Night | Total | Points | Benefits | Adj Total |
|---|-------|---------|-------|-----------|-------|--------|----------|-----------|
| 1 | SO/ Paris | EDIT+BOOST | 5★ | $639 | $2,555 | 127,756 UR | Breakfast, $100 credit, upgrade | ~$1,855 |
| 2 | Hotel Balzac | EDIT+BOOST | 5★ | $614 | $2,455 | 122,769 UR | Breakfast, $100 credit, upgrade | ~$1,755 |
| 3 | Le Bristol | FHR | 5★ | $1,849 | $8,284 | n/a | $100 credit, breakfast, upgrade, 4pm checkout | ~$6,884 |
| 4 | Marriott Champs-Élysées | — | 4★ | $289 | $1,156 | — | — | $1,156 |
| 5 | Airbnb: Marais 2BR | — | — | $195 | $780 | — | Kitchen, washing machine | $780 |

**Sources checked:**
- ✅ Chase Travel: 21 hotels (15 Edit, 6 standard)
- ✅ Amex Travel: 17 hotels (13 FHR, 4 THC)
- ✅ SerpAPI: 25 hotels
- ✅ Trivago: 30 hotels (cheapest OTA per hotel)
- ✅ LiteAPI: 22 hotels (negotiated rates)
- ✅ Airbnb: 18 listings
- ✅ Premium databases: 8 FHR, 3 THC, 15 Edit properties in Paris
- ⏭️ RapidAPI/Booking.com: skipped (not requested)

### Step 5: Recommendation

After the table, always provide:

1. **Best luxury value:** Which premium hotel gives the most benefit-adjusted savings
2. **Best budget option:** Cheapest option (often Airbnb for longer stays)
3. **Stacking opportunities:** Hotels in both FHR/THC AND Chase Edit
4. **Credit usage:** Which card credits apply ($600 Amex FHR, $300 CSR travel, $250 Select Hotels)
5. **Points vs cash:** Is using points worthwhile for any of these? (Calculate CPP)
6. **Direct booking comparison:** Note if direct booking is significantly cheaper than portal price

## Airbnb Integration

Use the `airbnb_search` MCP tool:

```
airbnb_search(
  location="Paris, France",
  checkin="2026-08-11",
  checkout="2026-08-15",
  adults=2,
  propertyType="entire_home"
)
```

For each Airbnb result, extract:
- Name, price, rating, reviews
- Property type (entire home, private room)
- Key amenities (kitchen, washer, wifi, AC)
- Direct link to listing

**When Airbnb makes sense:**
- Stays of 5+ nights (usually cheaper per night)
- Groups or families needing space
- Destinations where hotels are overpriced
- When kitchen access matters (dietary restrictions, saving on meals)

**When hotels win:**
- Short stays (1-2 nights)
- Premium benefits offset the rate (FHR breakfast alone can be $100+/night value)
- Points redemption gives good CPP
- Loyalty status benefits (upgrades, late checkout, lounge access)

## Error Handling

**NEVER fail silently.** Every source must report its status.

```
- ❌ Chase Travel: Login failed. No Chase portal pricing available.
- ❌ Airbnb: No results for this location/dates.
- ⚠️ Amex Travel: Only 3 results (some hotels may not be available for these dates).
```

If premium databases show FHR/Edit properties in the city but the portal search didn't return them, note this: "The FHR database lists 8 properties in Paris but Amex Travel only returned 3. Some may not have availability for your dates."

## Data Files Used

| File | Purpose |
|------|---------|
| `data/fhr-properties.json` | FHR property lookup by city/coordinates |
| `data/thc-properties.json` | THC property lookup |
| `data/chase-edit-properties.json` | Chase Edit property lookup |
| `data/hotel-chains.json` | Hotel chain to loyalty program mapping |
| `data/points-valuations.json` | CPP valuations for points calculations |

## Limitations

- Portal searches require Docker and credentials. Skip if not configured.
- Airbnb MCP must be available. Skip gracefully if not.
- FHR/THC/Edit databases are updated periodically. Properties may have been added or removed.
- Amex hotel points pricing is variable (not 1 cpp). Use the actual points price from the portal.
- Chase portal pricing is dynamic Points Boost (~1.5-2.0 cpp on select bookings, not a guaranteed floor). The historical static 1.5x multiplier is gone.
- Direct booking prices (via SerpAPI) may differ from portal prices for the same hotel.

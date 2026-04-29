---
name: award-calendar
description: Find the cheapest award dates for a route over a date range. Searches seats.aero across all programs, groups by date, and shows a calendar grid of the best deals. Use when dates are flexible and you want to find the sweet spot.
category: orchestration
summary: Cheapest award dates for a route across a date range. Calendar grid view.
api_key: Seats.aero Pro
---

# Award Calendar

"When should I fly SFO to NRT on points?" answered with a calendar view.

Searches seats.aero across a date range and presents a grid showing the cheapest award per day, per cabin. Highlights the best dates to fly.

**This is an orchestration skill.** It tells the agent how to query seats.aero and format the results. No standalone script.

## When to Use

- "When's the cheapest time to fly SFO to NRT in business on points?"
- "Show me award availability for SFO-CDG in September"
- "I'm flexible on dates. When should I fly?"
- Any award search where dates are flexible

## When NOT to Use

- Specific date search (use `seats-aero` directly)
- Cash price calendar (use Google Flights "Date grid" or Skiplagged)
- Hotel date flexibility (not supported here)

## Workflow

### Step 1: Search the Date Range

Use the seats.aero cached search API with a date range. The API supports up to ~60 days per query.

```bash
curl -s -H "Partner-Authorization: $SEATS_AERO_API_KEY" \
  "https://seats.aero/partnerapi/search?origin_airport={ORIGIN}&destination_airport={DEST}&start_date={START}&end_date={END}&cabin={CABIN}"
```

**Parameters:**
- `origin_airport`: Can be comma-delimited for nearby airports (e.g., `SFO,SJC,OAK`)
- `destination_airport`: Same. Use multiple for metro areas (e.g., `NRT,HND` for Tokyo)
- `start_date`, `end_date`: YYYY-MM-DD. Keep range under 60 days for best results.
- `cabin`: Optional filter. `economy`, `premium`, `business`, `first`. Omit for all cabins.
- `order_by`: Use `lowest_mileage` to get cheapest first.
- `take`: Set to `1000` to get all results in one page.

For ranges over 60 days, split into two queries and combine results.

### Step 2: Group by Date

Process the API response:

```
For each availability object:
  date = result.Date
  cabin = which cabin(s) are available (Y/W/J/F)
  For each available cabin:
    cost = result.{cabin}MileageCost
    program = result.Source
    Track: cheapest cost per date per cabin across all programs
```

### Step 3: Apply Transfer Partner Optimization

For each cheapest-per-date result, calculate the effective cost in transferable currencies using `data/transfer-partners.json`:

```
For date 2026-09-05, cheapest business = 55,000 via Flying Blue:
  Chase UR: 55,000 / 1.0 = 55,000 UR
  Amex MR: 55,000 / 1.0 = 55,000 MR
  Bilt: 55,000 / 1.0 = 55,000 Bilt
```

### Step 4: Present Calendar Grid

**Always use markdown tables.** One table per cabin class requested.

#### Business Class: SFO → NRT, September 2026

| Date | Program | Miles | Best Currency | Points | CPP* | Seats | Direct |
|------|---------|-------|---------------|--------|------|-------|--------|
| **Sep 3** ⭐ | Virgin Atlantic | 52,500 | Chase UR | 52,500 | 8.0 | 2 | ✅ ANA |
| Sep 5 | Flying Blue | 55,000 | Any 1:1 | 55,000 | 7.6 | 4 | ✅ AF |
| Sep 7 | Aeroplan | 70,000 | Chase UR | 70,000 | 6.0 | 1 | ✅ ANA |
| Sep 8 | United | 88,000 | Chase UR | 88,000 | 4.8 | 3 | ✅ UA |
| Sep 10 | — | — | — | — | — | — | ❌ No availability |
| Sep 12 | Aeroplan | 75,000 | Amex MR | 75,000 | 5.6 | 2 | ❌ 1-stop |
| ...  | ... | ... | ... | ... | ... | ... | ... |

*CPP calculated against cheapest cash fare from Duffel/Ignav if available, otherwise estimated.

⭐ = Best deal of the month

**Summary:**
- Best date: **Sep 3** via Virgin Atlantic → ANA at 52,500 miles (8.0 cpp)
- Runner-up: **Sep 5** via Flying Blue at 55,000 miles
- Worst week: Sep 10-14 (no business availability most days)
- Cheapest economy: Sep 12 at 25,000 United miles

### Step 5: Additional Context

After the grid, include:

1. **Freshness warning:** "Data from seats.aero cached search. Last seen times vary. Verify before transferring points."
2. **Transfer advice:** "Don't transfer until you've confirmed the specific flight exists on the airline's website."
3. **Cash comparison:** If a cash price was fetched (from Duffel/Ignav), show the CPP for context.
4. **Booking links:** For the top 3 dates, mention how to book (e.g., "Book via Virgin Atlantic website, call to hold").
5. **Release date note:** If searching far out, mention which airlines may not have released space yet (use seats.aero release date tool).

## Error Handling

**NEVER fail silently.**

```
- ❌ Seats.aero: API error (rate limit). Try again in a few minutes.
- ⚠️ Seats.aero: Only 12 results for 30-day range. Some dates may have uncached availability. Try live search for specific dates of interest.
- ℹ️ No business availability found for any date. Showing economy and premium economy instead.
```

If zero results come back for the entire range, say so explicitly and suggest:
1. Widening the airport search (add nearby airports)
2. Checking a different month
3. Looking at different cabins
4. Using the seats.aero live search for specific dates (local Patchright only)

## Limitations

- **Cached data only.** Results may be 1-48 hours old. Live search (via seats-aero-web) is more current but Bobby-local only.
- **60-day query limit.** Split longer ranges into multiple queries.
- **No round-trip optimization.** Shows one-way availability. For round-trip, run two calendar searches (outbound and return).
- **No cash price calendar.** This is award-only. For cash date flexibility, use Google Flights "Date grid" view.
- **Phantom availability.** Some results may not actually be bookable. Always verify.

---
name: rooms-aero
description: Hotel award availability search across World of Hyatt, Marriott Bonvoy, Hilton Honors, IHG One Rewards, Choice Privileges, Wyndham Rewards, and I Prefer via the rooms.aero Partner API using the same seats.aero Pro key. Find award nights, compare points against cash by cents per point, filter by city or bounding box, dates, stay length of 1 to 5 nights, program, max points, and minimum cpp. Trigger phrases include rooms.aero, hotel award search, hotel points availability, Hyatt award nights, Hilton award nights, Marriott award nights, IHG award nights, and best hotel redemption.
category: hotels
summary: Hotel award search across 7 loyalty programs via rooms.aero. Uses the same seats.aero key.
api_key: Seats.aero Pro or Partner
license: MIT
---

# Rooms.aero Skill

Search hotel award availability across **7 loyalty programs** using the rooms.aero Partner API. Find award nights, compare points vs cash by cents per point, and get room-level detail with direct booking links.

**Source:** [rooms.aero](https://rooms.aero) | [API docs](https://developers.seats.aero/reference/rooms-search)

rooms.aero is the hotel side of seats.aero. It uses the **same seats.aero Pro API key** already configured as `SEATS_AERO_API_KEY`.

---

## When to Use

- "Find Hyatt award space in Tokyo for next month"
- "What's the best hotel redemption in Makkah?"
- "Compare Marriott vs Hilton award rates in Paris"
- "Is 25,000 points a good deal for this hotel?"
- Any hotel award search where the user cares about points value

## When NOT to Use

- Cash-only hotel pricing → `compare-hotels` (Trivago, SerpAPI, LiteAPI)
- Premium card portal benefits (FHR, THC, Chase Edit) → `premium-hotels`
- Flight awards → `seats-aero`

---

## Authentication

```bash
export SEATS_AERO_API_KEY="pro_..."
curl -s -H "Partner-Authorization: $SEATS_AERO_API_KEY" \
  "https://rooms.aero/partnerapi/search?location=Makkah&start_date=2026-12-01&end_date=2026-12-31"
```

- Header name is **`Partner-Authorization`** (no `Bearer` prefix for personal Pro keys).
- Same Pro key as seats.aero, found at [seats.aero/settings](https://seats.aero/settings) → API tab.
- Rate limit: **1,000 calls/day**, resetting at midnight UTC. A `429` returns `user_rate_limit_exceeded`.
- Optional override: `ROOMS_AERO_API_KEY` (if set, prefer it; otherwise fall back to `SEATS_AERO_API_KEY`).

**Key loading:** before running curl, verify the var is present:

```bash
echo "${SEATS_AERO_API_KEY:+set}"
```

If unset, tell the user to source their shell rc or `.env` and retry.

---

## Base URL

```
https://rooms.aero/partnerapi
```

| Endpoint | Purpose |
|---|---|
| `GET /search` | Award search by area and check-in date range. Returns hotel-level cheapest rates and cpp. |
| `GET /hotels` | Hotel directory. Look up properties by city, brand, program, or name. |
| `GET /availability` | Availability rows per hotel, date, and stay length. **This is where you get availability IDs.** |
| `GET /availability/{id}` | Room-level detail for one availability row, including every room type and the direct booking link. |

**Supported `source` values:** `choice`, `hilton`, `hyatt`, `ihg`, `iprefer`, `marriott`, `wyndham`.

---

## Endpoint: Search

```
GET /search
```

### Parameters

| Param | Type | Required | Notes |
|---|---|---|---|
| `start_date` | string | Yes | Earliest **check-in** date, `YYYY-MM-DD` |
| `end_date` | string | Yes | Latest **check-in** date; must not precede `start_date` |
| `location` | string | Conditional | Place name to geocode (city, island, region) |
| `sw_lat`, `sw_lng`, `ne_lat`, `ne_lng` | number | Conditional | Bounding box; all four required if not using `location`. Box may not cross the antimeridian. |
| `nights` | integer | No | Exact stay length, **1–5**. Omit for all lengths. |
| `source` | string | No | Program key(s), comma-separated, e.g. `hyatt,hilton` |
| `max_points` | integer | No | Only hotels at or below this award price |
| `min_cpp` | number | No | Only hotels at or above this US cents-per-point value |
| `skip` | integer | No | Pagination offset, default `0` |
| `take` | integer | No | Page size, default `100`, max `500` |

**Area limit:** a search area can contain at most **500 hotels**. Narrow the box or add `source=` for dense cities.

### Example

```bash
curl -s -H "Partner-Authorization: $SEATS_AERO_API_KEY" \
  "https://rooms.aero/partnerapi/search?location=Makkah&start_date=2027-03-16&end_date=2027-03-21&nights=5&min_cpp=1.5&take=100" \
  | jq -r '.data[] | "\(.hotel.program) | \(.hotel.name) | \(.lowest_award_standard) pts | \(.lowest_cash_standard/100) \(.currency_code) | \(.cpp // 0) cpp | \(.standard_date) x\(.standard_nights)n"'
```

### Response fields (per result)

| Field | Meaning |
|---|---|
| `hotel` | Full hotel object (`id`, `source`, `program`, `name`, `city`, `country`, `latitude`, `longitude`, `url`, etc.) |
| `lowest_award_standard` | Cheapest standard-room award for the whole stay, points; `0` = none |
| `lowest_award_suite` | Cheapest suite award, points; `0` = none |
| `lowest_cash_standard` | Cheapest standard-room cash rate for the whole stay, **minor currency units** |
| `lowest_cash_suite` | Cheapest suite cash rate, minor units |
| `currency_code` | ISO 4217 currency for the cash fields |
| `standard_date` / `standard_nights` | Check-in date and stay length of the cheapest standard rate |
| `suite_date` / `suite_nights` | Same for the cheapest suite rate |
| `cpp` | Better value of the two room classes, **US cents per point** |
| `last_checked_at` | Freshness timestamp (RFC 3339) |

Results are ordered cheapest award first.

---

## Endpoint: Hotels

```
GET /hotels
```

Use for property lookup when you already know the place or brand.

| Param | Notes |
|---|---|
| `id` | rooms.aero hotel IDs, comma-separated, max 100 |
| `internal_id` | Program's own property code, max 100; combine with `source` |
| `source` | `choice`, `hilton`, `hyatt`, `ihg`, `iprefer`, `marriott`, `wyndham` |
| `country`, `state`, `city` | Display names, comma-separated |
| `brand`, `category` | Program-specific codes/categories |
| `search` | Case-insensitive substring on hotel name |
| `skip` / `take` | Offset; page size default `100`, max `1000` |

### Example

```bash
curl -s -H "Partner-Authorization: $SEATS_AERO_API_KEY" \
  "https://rooms.aero/partnerapi/hotels?city=Makkah&source=hyatt,hilton,marriott&take=100" \
  | jq -r '.data[] | "\(.source) | \(.name) | \(.internal_id) | lowest_award \(.lowest_award // "unknown") | availability \(.standard_award_availability_percent // "?")%"'
```

`lowest_award` is the lowest points award observed in the prior two weeks; `null` if unknown. `standard_award_availability_percent` is the share of checked upcoming dates with award space.

---

## Endpoint: Availability List

```
GET /availability
```

This is the bridge between search and room-level detail. It returns one row per **hotel + check-in date + stay length**, each with an `id` for `/availability/{id}`.

### Parameters

| Param | Notes |
|---|---|
| `source` | Required unless `hotel_id` is provided |
| `hotel_id` | Required unless `source` is provided; comma-separated, max 50 |
| `start_date`, `end_date` | Check-in range, `YYYY-MM-DD` |
| `nights` | 1–5 |
| `brand`, `category`, `country` | Comma-separated filters |
| `rate_type` | `award` (default), `cash`, or `any` |
| `room_type` | `standard`, `suite`, or `any` (default) |
| `max_points`, `min_cpp` | Point and cpp filters |
| `order_by` | `arrival_date` (default), `lowest_award`, `lowest_cash`, `last_checked` |
| `include_hotel` | Default `true`; set `false` for a slim response |
| `skip` / `take` | Page size default `100`, max `500` |

Only future arrivals retrieved within the last 21 days are included.

### Example

```bash
curl -s -H "Partner-Authorization: $SEATS_AERO_API_KEY" \
  "https://rooms.aero/partnerapi/availability?source=hyatt&start_date=2027-03-16&end_date=2027-03-21&nights=5&rate_type=award&order_by=lowest_award&take=50" \
  | jq -r '.data[] | "\(.id) | \(.hotel.name) | \(.arrival_date) x\(.num_nights)n | \(.standard_award_cost) pts | $\(.standard_cash_cost/100) \(.cash_currency_code) | \(.standard_cpp) cpp"'
```

Key fields per row: `id`, `hotel_id`, `hotel`, `arrival_date`, `departure_date`, `num_nights`, `standard_award_available`, `standard_award_cost` (points for the whole stay), `standard_cash_available`, `standard_cash_cost` (minor units), `standard_cpp`, `suite_*` equivalents, `booking_link`, `last_checked_at`.

---

## Endpoint: Availability Detail

```
GET /availability/{id}
```

Returns every room type for that exact hotel/date/stay, plus the booking link.

```bash
curl -s -H "Partner-Authorization: $SEATS_AERO_API_KEY" \
  "https://rooms.aero/partnerapi/availability/2S8Cm9dHORWWKpoCkxfRkZa0e5l" \
  | jq -r '"\(.hotel.name) | \(.arrival_date) x\(.num_nights)n",
           "standard: \(.standard_award_cost) pts vs $\(.standard_cash_cost/100) | \(.standard_cpp) cpp",
           "book: \(.booking_link.label) \(.booking_link.url)",
           (.rooms[] | "  \(.name) | suite:\(.suite) | award:\(.award_cost) | cash:\(.cash_cost/100) \(.cash_cost_currency)")'
```

Important semantics:
- `standard_award_cost` and `suite_award_cost` are **points for the entire stay**.
- `standard_cash_cost` and `suite_cash_cost` are **minor currency units for the entire stay** (divide by 100 for USD/SAR/etc.).
- `standard_cpp` / `suite_cpp` are **US cents per point**; `0` when a comparison is unavailable.
- `booking_link` is a direct deep link into the loyalty program's booking flow.
- `rooms[]` includes `name`, `room_code`, `suite`, `accessible`, `award_cost`, `cash_cost`, `cash_cost_currency`.

---

## Workflow

1. **Resolve the area.** Use `location` for a city or landmark. For a neighborhood or resort cluster, pass a tight bounding box.
2. **Search hotels.** `GET /search` with the check-in range. Set `nights` to the exact stay length (1–5) when known. If the area returns a 500-hotel error, narrow the box or add `source=`.
3. **Filter by value, not just price.** Sort or filter with `min_cpp` against the `points-valuations` floor. Hotel awards under ~1.0 cpp are usually worse than cash.
4. **Get availability IDs.** `GET /availability` for the winning hotels/dates. Use `rate_type=award`, `room_type=standard`, and `order_by=lowest_award`.
5. **Pull room detail.** `GET /availability/{id}` for the exact room types and the booking link.
6. **Check reachability and transfer math.** Load `transfer-partners` to confirm the program is reachable from the user's currencies, and `transfer-bonuses` for any active transfer bonus before recommending a transfer.
7. **Verify freshness.** Check `last_checked_at`. Stale data means verify the rate on the hotel's site before transferring points or booking.

### Splitting stays longer than 5 nights

The API caps `nights` at 5. For a 7-night stay, run two searches (e.g. 5 + 2 or 4 + 3) and sum the points. Do not assume the 5-night rate extends to longer stays; property-level award pricing can change by night.

---

## CPP Interpretation

`cpp` is **US cents per point**. Use it directly:

| cpp | Verdict |
|---|---|
| < 0.5 | Terrible — usually worse than cash |
| 0.5–1.0 | Poor — Hilton/Marriott/IHG baseline territory |
| 1.0–1.5 | Acceptable only with a specific reason (status, location, 5th-night-free) |
| 1.5–2.0 | Good — compare against `points-valuations` |
| 2.0+ | Excellent — flag it |

Cross-reference `points-valuations` for program floors:
- **Hyatt** ~1.4–1.7 cpp
- **Hilton** ~0.4 cpp floor
- **Marriott** ~0.5–0.8 cpp
- **IHG** ~0.5 cpp
- **Choice / Wyndham / I Prefer** ~0.5–0.8 cpp

Cash rates are in local currency (minor units). The `cpp` field is already computed against USD, so use it instead of doing currency math yourself.

---

## Useful jq Recipes

**Cheapest award per hotel, sorted:**

```bash
jq -r '.data | sort_by(.lowest_award_standard)[] | "\(.lowest_award_standard) pts | \(.hotel.program) | \(.hotel.name) | \(.cpp) cpp"'
```

**Only good redemptions (1.5+ cpp):**

```bash
jq -r '.data[] | select(.cpp >= 1.5) | "\(.hotel.name) | \(.lowest_award_standard) pts | \(.cpp) cpp"'
```

**Compare programs side by side:**

```bash
jq -r '.data | group_by(.hotel.source)[] | "\(.[0].hotel.program): \([.[].lowest_award_standard] | min) pts min, best \(map(.cpp) | max) cpp"'
```

**Follow pagination:**

```bash
jq -r '.more_url // empty'
```

Then `curl` the returned `more_url` (it already carries `skip` and `take`).

**Room-level booking link:**

```bash
jq -r '.booking_link | "\(.label) -> \(.url)"'
```

---

## Integration with Other Skills

- **`compare-hotels`** — add rooms.aero as the award-availability source alongside cash metasearch. Cash prices from Trivago/SerpAPI vs award points from rooms.aero produce the real points-vs-cash comparison.
- **`trip-planner`** — use rooms.aero when building the hotel leg of a trip cost matrix that includes awards.
- **`points-valuations`** — use its cpp floors to judge each `cpp` value.
- **`transfer-partners`** — confirm the program is reachable from the user's currency before recommending a transfer.
- **`transfer-bonuses`** — check for an active bonus before transferring points.
- **`hotel-chains`** — map an unfamiliar brand to its program before searching by `source`.

---

## Pitfalls and Failure Modes

| Problem | Cause | Fix |
|---|---|---|
| `401 missing_partner_key` | Key not loaded | Source shell rc or `.env`; retry |
| `401 bad_partner_key` | Wrong key or not a Pro/Partner key | Check `pro_` prefix; key must be Pro/Partner |
| `401 invalid_scope` | Key lacks hotel scope | Confirm the same key has rooms.aero access in seats.aero settings |
| `401 user_subscription_expired` | Pro subscription lapsed | Renew at seats.aero |
| `400 missing_parameter` | Missing dates or area | Provide `start_date`, `end_date`, plus `location` or all four bbox edges |
| 500-hotel area error | Dense city, wide box | Narrow the bbox or add `source=` |
| `429 user_rate_limit_exceeded` | 1,000/day cap | Wait until midnight UTC; reduce fan-out |
| Empty results | Dates outside cached range, or no award space | Widen the date range; try `rate_type=any`; check `last_checked_at` |
| `nights` rejected | Value > 5 | Split the stay |
| Guests/rooms wrong in booking link | API has no occupancy parameter | Edit the `rooms=` and `adults=` query params in the returned URL before booking |

**Data freshness:** rooms.aero is cached. `last_checked_at` is the freshness signal. For anything the user is about to book or transfer points for, verify the rate on the hotel's own site first.

---

## Validation

Tested live on 2026-11-21 with a seats.aero Pro key:

```
GET /search?location=Makkah&start_date=2027-03-16&end_date=2027-03-21&nights=5
→ HTTP 200
  Marriott Bonvoy | Four Points by Sheraton Makkah Al Naseem | 14,300 pts | SAR 229.42 | 0.43 cpp
  IHG Rewards   | voco Makkah                              | 17,800 pts | SAR 340.29 | 0.51 cpp

GET /hotels?city=Makkah
→ HTTP 200
  hilton  | Conrad Jabal Omar Makkah            | lowest_award 85,000
  marriott| Four Points Makkah Al Naseem         | lowest_award 11,200
```

This example also illustrates the main lesson: Makkah hotel awards routinely price under 0.5 cpp — always compare against cash.

---

## Sources

- [Rooms search API](https://developers.seats.aero/reference/rooms-search)
- [Hotels API](https://developers.seats.aero/reference/rooms-get-hotels)
- [Availability API](https://developers.seats.aero/reference/rooms-get-availability)
- [Availability detail API](https://developers.seats.aero/reference/rooms-get-availability-detail)
- [rooms.aero](https://rooms.aero)

---
name: seats-aero
description: Search award flight availability across 27 mileage programs via the Seats.aero Partner API or the official seats.aero MCP server. Find cheapest award flights, compare programs, and get booking links. The MCP works with no key for flights in the next 60 days. Pro sign-in on the MCP adds live search, alerts, award hotels, upgrades, and deals.
category: flights
summary: Award availability across 27 mileage programs. Partner API, plus the official MCP (keyless for the next 60 days, Pro sign-in for live search and alerts).
api_key: Seats.aero Pro/Partner (MCP free for 60 days)
license: MIT
---

# Seats.aero Skill

Search cached and live award flight availability across 27 mileage programs (including Spirit Free Spirit and Frontier Miles, added April 2026). Find the cheapest award flights, compare programs, and get booking links.

**Source:** [seats.aero](https://seats.aero) | [API Docs](https://developers.seats.aero) | [Knowledge Base](https://docs.seats.aero)

## Authentication

Set `SEATS_AERO_API_KEY` in your `.env` file. Get from [Settings > API tab](https://seats.aero/settings) (Pro account required).

All requests use the `Partner-Authorization` header. Pro users get **1,000 API calls per day** for non-commercial use.

## Two Ways In: Partner API and Official MCP

Seats.aero also runs an official remote MCP server at `https://seats.aero/mcp` (Streamable HTTP, OAuth 2.1). The toolkit configures it as the `seats-aero` MCP server in `.mcp.json`, `opencode.json`, and the Codex plugin.

**Which to use:**

| Situation | Use |
|-----------|-----|
| `SEATS_AERO_API_KEY` is set | **Partner API (curl, below) is primary.** Bulk Availability, `include_filtered`, Get Trips, and jq pipelines have no MCP equivalent. |
| No key set | **MCP anonymously.** Cached award search works with zero setup, limited to flights departing within the next 60 days. |
| Partner API errors, 401s, or hits the daily cap | **MCP as fallback.** Same underlying cached data. |
| Alerts, live search, award hotels, upgrades, deals | **MCP, signed in with a Pro account.** These are MCP-only and need the OAuth sign-in. |
| Transfer partners for a program | Either. `data/transfer-partners.json` stays the source of truth for ratios, and the MCP's `list_transfer_partners` is a live cross-check. |

### Anonymous (no sign-in)

Works out of the box. Calling `get_capabilities` anonymously returns: cached search only, no live search, no alerts, 60-day advance window, 60-day max date range, 50 results max per call, 1,000 requests/day per IP.

Tools exposed anonymously:

| Tool | Purpose |
|------|---------|
| `get_capabilities` | What the current session can do (scope, limits, live search, alerts). Call this first if unsure whether the user is signed in. |
| `get_flights` | Cached award search. `origins`, `destinations` (arrays), `start_date`, `end_date` required. |
| `get_flight_details` | Itinerary, freshness, and booking-instructions link for a `flight_ref` from `get_flights`. |
| `search_airports` | Resolve cities, regions, and meta codes (NYC, LON, EUR) to airports. |
| `list_routes` | Tracked routes. Pass exactly two of `mileage_program`, `origin`, `destination`. |
| `list_transfer_partners` | Card programs that transfer into a mileage program, with base ratios. |
| `list_transfer_program_mileage_programs` | Mileage programs reachable from a card program (`chaseus`, `amexus`, `bilt`, `capitalone`, `citius`, etc.). |
| `search_help_docs` | Search docs.seats.aero (phantom availability, data freshness, Pro features). |

### `get_flights` gotchas

- **`max_stops` defaults to 0 (nonstop only).** Set it explicitly when connections are acceptable, or you'll silently miss one-stop itineraries. Connecting flights are a Pro feature, so this may still return nonstops only when anonymous.
- **Leave `programs` empty** on the first search. Same rule as `lessons-learned`: pull every program, then gate on reachability.
- **`transfer_partners`** filters to programs reachable from a card currency (e.g. `["chaseus"]`). Handy for a second pass, never for the first.
- **`max_fees` is in USD cents.** `40000` means $400.
- **`min_cabin_pct`** defaults to 100 (whole journey in the cabin). Only lower it when the user accepts mixed-cabin itineraries.
- **Cabin values** are `economy`, `premium`, `business`, `first`.
- **`minutes_old`** on each result is the freshness signal (the MCP equivalent of `ComputedLastSeen`).
- Each response includes a `search_url` deep link to seats.aero. Hand it to the user for verification.

### Signed in (Pro)

Signing in grants more OAuth scopes (`seats.awards.live`, `seats.alerts.read`/`create`/`expire`, `seats.pricing.read`/`write`, `seats.profile.read`). Per seats.aero, Pro unlocks live search (uses the account's existing live search allowance), connecting flights, award alerts, and pricing preferences, and the signed-in tool set adds award hotels, upgrade availability, and deals. Call `get_capabilities` after sign-in to see the real limits, then list tools to see what's exposed.

**Writes need explicit user approval.** Creating or expiring an alert, changing pricing preferences, and running a live search (spends the user's allowance) all act on the user's seats.aero account. Describe the action and get a yes first.

**Sign-in is manual.** The server answers anonymously instead of returning 401, so clients won't prompt for OAuth on their own. The user signs in once:

| Harness | Command |
|---------|---------|
| Claude Code | `/mcp`, pick `seats-aero`, Authenticate (or `claude mcp login seats-aero` for a repo-local config) |
| OpenCode | `opencode mcp auth seats-aero` |
| Codex | `codex mcp login seats-aero` |

Never ask for the user's seats.aero password or paste tokens into chat. OAuth runs in the browser.

## API Base

```
https://seats.aero/partnerapi
```

## Key Concepts

### Saver vs Dynamic Pricing

Award seats fall into two categories:

- **Saver (fixed price):** Set, predictable miles cost. Often the ONLY type bookable through partner programs. Best value. Always shown on Seats.aero.
- **Dynamic:** Price changes based on demand (like cash fares). Can be reasonable or extremely expensive. Seats.aero **filters out overpriced dynamic awards by default.**

### Dynamic Price Filter Thresholds

Awards exceeding these per-hour thresholds are hidden automatically:

| Program | Economy | Prem Econ | Business | First |
|---------|---------|-----------|----------|-------|
| American | <100K total | <100K total | <150K total | <200K total |
| United | 7,500/hr | 10,000/hr | 14,000/hr | 20,000/hr (max 10h) |
| Delta | 10,000/hr | 15,000/hr | 20,000/hr | N/A |
| Aeroplan | 7,500/hr | 10,000/hr | 12,500/hr | 15,000/hr |
| Flying Blue | 5,000/hr | 10,000/hr | 15,000/hr | 15,000/hr |
| Alaska | <150K total | <150K total | <150K total | <150K total |
| Aeromexico | 10,000/hr (max 10h) | 15,000/hr | 20,000/hr | N/A |
| Etihad | 10,000/hr (max 10h) | 15,000/hr | 20,000/hr | N/A |
| JetBlue | 10,000/hr | 15,000/hr | 20,000/hr | N/A |
| Qantas | 7,500/hr | 10,000/hr | 20,000/hr | 25,000/hr |

To see ALL dynamic pricing (including expensive): pass `include_filtered=true` on cached search/bulk, or `disable_filters=true` / `show_dynamic_pricing=true` on live search.

### Phantom Availability

Sometimes a flight shows bookable but no seat actually exists. Causes:
- **Cached/stale results:** Check `ComputedLastSeen` for freshness.
- **Syncing delays:** Seats taken but partner systems haven't updated.
- **Partner feed glitches:** Programs incorrectly show space on partners.

**Always verify on the airline's own site before transferring points.** Compare multiple programs in the same alliance. Call to confirm and hold if possible.

### Foreign Program Caveats

Some programs (Smiles, TudoAzul, etc.) may require local tax IDs, local payment methods, or are only available in the local language. They still appear in results because they can serve as **signals**: if Azul TudoAzul shows United saver space, that same space is likely bookable through Aeroplan or other Star Alliance partners you CAN access.

### Award Release Dates

Airlines release award seats at different advance windows (e.g., Aeroplan releases up to 358 days out). Check [seats.aero/tools/releases](https://seats.aero/tools/releases) to see the maximum days out for each airline by program. Useful for planning when to start searching.

### Availability Objects

Each result from Cached Search / Bulk Availability is a **summary** that groups all flights for one route/date/program into a single object. For example, if Alaska shows 3 different SFO>LAX flights on Mar 16, they all appear in one availability object. The `MileageCost` fields show the **cheapest** option. The `RemainingSeats` fields show the **maximum** across all flights. Use Get Trips to see individual flight details.

## Mileage Program Sources

| Source | Program | Cabins | Seat Count | Trip Data | Taxes |
|--------|---------|--------|------------|-----------|-------|
| `eurobonus` | SAS EuroBonus | Y/J | Yes | Yes | Yes |
| `virginatlantic` | Virgin Atlantic Flying Club | Y/W/J | Yes | Yes | Yes |
| `aeromexico` | Aeromexico Club Premier | Y/W/J | Yes | Yes | Yes |
| `american` | American Airlines AAdvantage | Y/W/J/F | Low seats only* | Yes | Yes |
| `delta` | Delta SkyMiles | Y/W/J | Yes | Yes | Yes |
| `etihad` | Etihad Guest | Y/J/F | Yes | Yes | Yes |
| `united` | United MileagePlus | Y/W/J/F | Yes | Yes | Yes |
| `emirates` | Emirates Skywards | Y/W/J/F | No | Partial** | Yes |
| `aeroplan` | Air Canada Aeroplan | Y/W/J/F | Usually*** | Yes | Yes |
| `alaska` | Alaska Mileage Plan | Y/W/J/F | Yes | Yes | Yes |
| `velocity` | Virgin Australia Velocity | Y/W/J/F | Yes | Yes | Yes |
| `qantas` | Qantas Frequent Flyer | Y/W/J/F | No | Yes | Yes |
| `connectmiles` | Copa ConnectMiles | Y/J/F | No | Yes | Yes |
| `azul` | Azul TudoAzul | Y/J | No | Yes | Yes |
| `smiles` | GOL Smiles | Y/W/J/F | Yes | Yes | Yes |
| `flyingblue` | Air France/KLM Flying Blue | Y/W/J/F | Yes | Yes | Yes |
| `jetblue` | JetBlue TrueBlue | Y/W/J/F | Yes | Yes | Yes |
| `qatar` | Qatar Privilege Club | Y/J/F | No | Yes | No |
| `turkish` | Turkish Miles & Smiles | Y/J | No | Yes | No |
| `singapore` | Singapore KrisFlyer | Y/W/J/F | No | Yes | No |
| `ethiopian` | Ethiopian ShebaMiles | Y/J | Yes | Yes | Yes |
| `saudia` | Saudi AlFursan | Y/J/F | Yes | Yes | Yes |
| `finnair` | Finnair Plus | Y/W/J/F | Yes | Yes | Yes |
| `lufthansa` | Lufthansa Miles&More | Y/J/F | Yes | Yes | Yes |
| `frontier` | Frontier Airlines | Y | No | Yes | Yes |
| `spirit` | Spirit Airlines | Y | Yes | Yes | Yes |

\* AA provides seat counts only when remaining seats are low. Otherwise shows 0.
\** Emirates connection flights may have missing fields.
\*** Aeroplan seat count is typically available but may be 0 in rare cases.

**Cabin codes:** Y = economy, W = premium economy, J = business, F = first

## Cached Search (Primary Endpoint)

Search for award availability between specific airports and date ranges across all programs. Use this for targeted route/date searches.

```bash
curl -s -H "Partner-Authorization: $SEATS_AERO_API_KEY" \
  "https://seats.aero/partnerapi/search?origin_airport=SFO&destination_airport=NRT&start_date=2026-08-01&end_date=2026-08-31" | jq '.'
```

### Parameters

| Param | Required | Description |
|-------|----------|-------------|
| `origin_airport` | Yes | Comma-delimited airport codes: `SFO,LAX` |
| `destination_airport` | Yes | Comma-delimited airport codes: `NRT,HND` |
| `start_date` | No | YYYY-MM-DD format |
| `end_date` | No | YYYY-MM-DD format |
| `cabins` | No | Comma-delimited: `economy,business` |
| `sources` | No | Comma-delimited program filter: `aeroplan,united` |
| `only_direct_flights` | No | Boolean. Only direct flights. |
| `carriers` | No | Comma-delimited airline codes: `DL,AA` |
| `order_by` | No | Default: date+cabin priority. `lowest_mileage` for cheapest first. |
| `include_trips` | No | Boolean. Include flight details in response (slower, larger). |
| `minify_trips` | No | Boolean. When combined with `include_trips`, returns fewer fields per trip for better performance. |
| `include_filtered` | No | Boolean. Show expensive dynamic awards that were filtered out. |
| `take` | No | Results per page. 10-1000, default 500. |
| `skip` | No | Pagination offset. |
| `cursor` | No | Cursor from previous response for consistent pagination. |

### Response Fields (Availability Object)

Each result summarizes all flights for one route/date/program:

| Field | Description |
|-------|-------------|
| `ID` | Availability ID (use with `/trips/{id}` for flight details) |
| `Route.OriginAirport` | Origin airport code |
| `Route.DestinationAirport` | Destination airport code |
| `Date` | Departure date |
| `Source` | Mileage program |
| `YAvailable`, `WAvailable`, `JAvailable`, `FAvailable` | Cabin availability booleans |
| `YMileageCost`, `WMileageCost`, `JMileageCost`, `FMileageCost` | Cheapest points cost across all flights (string) |
| `YRemainingSeats`, `WRemainingSeats`, `JRemainingSeats`, `FRemainingSeats` | Max seats remaining across all flights |
| `YAirlines`, `WAirlines`, `JAirlines`, `FAirlines` | Operating carriers |
| `YDirect`, `WDirect`, `JDirect`, `FDirect` | Direct flight available |
| `ComputedLastSeen` | When availability was last verified |

## Get Trip Details

Get flight-level information from an availability object. Returns individual itineraries with segments, booking links, and coordinates.

```bash
curl -s -H "Partner-Authorization: $SEATS_AERO_API_KEY" \
  "https://seats.aero/partnerapi/trips/{availability_id}" | jq '.'
```

### Parameters

| Param | Required | Description |
|-------|----------|-------------|
| `id` | Yes (path) | The availability object ID |
| `include_filtered` | No (query) | Include expensive dynamic results filtered out |

### Response Fields (Trip Object)

| Field | Description |
|-------|-------------|
| `Cabin` | economy, premium, business, first |
| `MileageCost` | Points cost (integer) |
| `AllianceCost` | Cost through alliance partner programs (integer) |
| `TotalTaxes` | Taxes in cents (divide by 100 for dollars) |
| `TaxesCurrency` | Currency code (empty = USD) |
| `RemainingSeats` | Seats left |
| `Stops` | Number of stops |
| `TotalDuration` | Minutes |
| `Carriers` | Operating airlines |
| `FlightNumbers` | Flight number string |
| `DepartsAt` | Departure (local airport time) |
| `ArrivesAt` | Arrival (local airport time) |
| `AvailabilitySegments` | Array of individual flight legs |
| `Source` | Mileage program |

The response also includes:
- `booking_links[]` with `label`, `link`, and `primary` boolean for direct booking URLs
- `origin_coordinates` and `destination_coordinates` (Lat/Lon)

### Trip Segment Fields

Each segment in `AvailabilitySegments`:

| Field | Description |
|-------|-------------|
| `FlightNumber` | e.g., "TK800" |
| `AircraftCode` | e.g., "77W" |
| `AircraftName` | e.g., "77W" |
| `OriginAirport` | Segment origin |
| `DestinationAirport` | Segment destination |
| `DepartsAt` | Departure time (local airport) |
| `ArrivesAt` | Arrival time (local airport) |
| `FareClass` | Booking class letter (e.g., "I", "X") |
| `Distance` | Segment distance in miles |
| `Order` | Segment order (0-indexed) |

## Bulk Availability

Retrieve large result sets from one mileage program. Use for broad regional exploration (e.g., "all United business class from North America to Europe").

```bash
curl -s -H "Partner-Authorization: $SEATS_AERO_API_KEY" \
  "https://seats.aero/partnerapi/availability?source=united&origin_region=North%20America&destination_region=Europe&cabin=business&start_date=2026-08-01&end_date=2026-09-30" | jq '.'
```

### Parameters

| Param | Required | Description |
|-------|----------|-------------|
| `source` | Yes | Single mileage program |
| `cabin` | No | economy, premium, business, first |
| `start_date` | No | YYYY-MM-DD |
| `end_date` | No | YYYY-MM-DD |
| `origin_region` | No | North America, South America, Africa, Asia, Europe, Oceania |
| `destination_region` | No | Same as above |
| `include_filtered` | No | Boolean. Show filtered-out dynamic pricing. |
| `take` | No | 10-1000, default 500 |
| `skip` | No | Pagination offset |
| `cursor` | No | From previous response |

## Get Routes

List all monitored routes for a mileage program. Useful for understanding what city pairs have cached data.

```bash
curl -s -H "Partner-Authorization: $SEATS_AERO_API_KEY" \
  "https://seats.aero/partnerapi/routes?source=united" | jq '.'
```

Returns an array of route objects:

| Field | Description |
|-------|-------------|
| `OriginAirport` | Origin code |
| `DestinationAirport` | Destination code |
| `OriginRegion` | Region name |
| `DestinationRegion` | Region name |
| `NumDaysOut` | How far ahead this route is scanned |
| `Distance` | Route distance |
| `Source` | Mileage program |

## Live Search

Real-time search for ANY city pair (not limited to monitored routes). **Commercial agreement required.** Not available to Pro users via API.

5-15 second response times. Build proper error handling with exponential backoff.

```bash
curl -s -X POST -H "Partner-Authorization: $SEATS_AERO_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"origin_airport":"SFO","destination_airport":"NRT","departure_date":"2026-08-15","source":"united","seat_count":2}' \
  "https://seats.aero/partnerapi/live" | jq '.'
```

### Parameters (JSON body)

| Param | Required | Description |
|-------|----------|-------------|
| `origin_airport` | Yes | Single airport code |
| `destination_airport` | Yes | Single airport code |
| `departure_date` | Yes | YYYY-MM-DD |
| `source` | Yes | Single mileage program |
| `seat_count` | No | 1-9, default 1 |
| `disable_filters` | No | Disable ALL filters (dynamic pricing + mismatched airports) |
| `show_dynamic_pricing` | No | Disable only dynamic pricing filter, keep airport filtering |

**Important:** IDs returned from live search are NOT real and cannot be used with other Seats.aero APIs (Get Trips, etc.). Live results are ephemeral.

## Pagination

All list endpoints use `skip` + `cursor`. On first call, omit both. From the response, save the `cursor` value. On subsequent calls, pass `cursor` and increment `skip` by the number of results received.

The `cursor` is a Unix timestamp. Treat it as opaque. Rare duplicates are possible across pages. Deduplicate by `ID`.

## Useful jq Filters

```bash
# Business class availability sorted by cheapest miles
... | jq '[.data[] | select(.JAvailable == true) | {date: .Date, origin: .Route.OriginAirport, dest: .Route.DestinationAirport, miles: (.JMileageCost | tonumber), seats: .JRemainingSeats, airlines: .JAirlines, source: .Source, direct: .JDirect}] | sort_by(.miles)'

# Saver vs dynamic detection: if miles < threshold, likely saver
# AA: J saver ~57.5K for transatlantic, dynamic 100K+
# United: J saver ~60-80K for transatlantic, dynamic 100K+
... | jq '[.data[] | select(.JAvailable == true) | {date: .Date, miles: (.JMileageCost | tonumber), source: .Source, type: (if (.JMileageCost | tonumber) < 80000 then "likely_saver" else "dynamic" end)}]'

# Economy availability with 2+ seats
... | jq '[.data[] | select(.YAvailable == true and .YRemainingSeats >= 2) | {date: .Date, origin: .Route.OriginAirport, dest: .Route.DestinationAirport, miles: (.YMileageCost | tonumber), seats: .YRemainingSeats, source: .Source}] | sort_by(.miles)'

# All available cabins for a date range
... | jq '[.data[] | {date: .Date, origin: .Route.OriginAirport, dest: .Route.DestinationAirport, source: .Source, economy: (if .YAvailable then .YMileageCost else null end), business: (if .JAvailable then .JMileageCost else null end), first: (if .FAvailable then .FMileageCost else null end)}]'

# Direct flights only in business
... | jq '[.data[] | select(.JAvailable == true and .JDirect == true) | {date: .Date, miles: .JMileageCost, airlines: .JAirlines, source: .Source}]'

# Check data freshness (stale = potential phantom)
... | jq '[.data[] | {date: .Date, source: .Source, last_seen: .ComputedLastSeen}]'
```

## Workflow: Trip Planning Search

1. **Cached Search** across multiple airports and date ranges to see what's available
2. **Compare programs**: check which `source` has the cheapest miles for the same route
3. **Identify saver vs dynamic**: low prices (e.g., 57.5K J for AA transatlantic) = saver. High prices (100K+) = dynamic.
4. **Always pull Trip Details** on promising availability IDs — do not stop at the search summary. The search summary (`JMileageCost`) only shows the cheapest itinerary. Trip details show all available options including Standard/dynamic tiers that the summary hides. This is mandatory for any search involving 2+ travelers.
5. **Apply the layover filter** (see below) before presenting results.
6. **Verify freshness**: check `ComputedLastSeen`. If stale (hours old), the availability may be phantom.
7. **Cross-reference**: check the airline's own site or call to confirm before transferring points
8. **Use booking_links** from trip response to book directly on each program's site
9. Cross-reference with AwardWallet balances to confirm enough points

## Layover Quality Filter

After pulling trip details, always calculate layover time for every itinerary. **Flag any layover over 3 hours.** Do not silently present a bad-layover itinerary as the recommendation just because it's cheapest.

When the cheapest option has a layover over 3 hours:
1. Show it with an explicit flag: "⚠️ 8h layover in FRA"
2. Automatically surface the next cheapest itinerary with a layover under 3 hours alongside it
3. Let the user decide whether the points savings justify the wait — never make that call silently

**Why this matters:** Saver inventory often has the cheapest price but worst routings (long layovers, odd connections). Standard inventory typically costs 20-30% more in miles but offers significantly better itineraries. The cheapest award is not always the best award.

```bash
# Calculate layover duration from trip segments
# TotalDuration = full trip (gate to gate including layovers)
# Sum of individual segment durations = pure flight time
# Layover = TotalDuration - sum(segment durations)
# Flag if any single layover exceeds 180 minutes

curl -s -H "Partner-Authorization: $SEATS_AERO_API_KEY" \
  "https://seats.aero/partnerapi/trips/{id}" | jq '
  .data[] | {
    miles: .MileageCost,
    flights: .FlightNumbers,
    total_min: .TotalDuration,
    segments: [.AvailabilitySegments[] | {
      flight: .FlightNumber,
      from: .OriginAirport,
      to: .DestinationAirport,
      departs: .DepartsAt,
      arrives: .ArrivesAt
    }]
  }
'
```

## Why Results May Be Empty

1. **No saver space released.** Most programs only show saver awards to partners. Check the airline's own site.
2. **Elite/status restrictions.** Some seats only visible to elite members or cardholders.
3. **Route not monitored.** If the route isn't in Get Routes, cached search won't have it. Live search can check any route.
4. **Search window limits.** Airlines release awards at different advance windows. Check [release dates tool](https://seats.aero/tools/releases).
5. **Already booked.** Award space changes constantly. Set alerts for notification when it opens.

## Specialized Tools (Web UI Only)

These tools are available on the seats.aero website but not via the Partner API:

- **Alaska Upgrade Finder** ([seats.aero/alaska/upgrades](https://seats.aero/alaska/upgrades)): Find confirmable upgrade space for Alaska elites using Atmos Gold Guest Upgrade certificates. Dedicated tool for scanning upgrade availability.
- **Etihad First Class Finder** ([seats.aero/etihad/first](https://seats.aero/etihad/first)): Dedicated tracker for newly available Etihad First Class seats. Etihad F is rare and highly sought after. This tool surfaces new availability faster than general search.
- **Price History**: Fare trends over time are available on the web UI but not via API. Use the `seats-aero-web` skill (Patchright browser automation) to access price history charts.

## Alert Features

When creating alerts on seats.aero:

- **Time filters**: Departure and arrival time ranges are available as alert filters. Useful for avoiding red-eyes or ensuring morning arrivals.
- **Cabin, route, and program filters**: Standard alert parameters.
- Alerts notify via email or push when matching availability appears.
- With a Pro sign-in, the `seats-aero` MCP can create, review, and expire alerts. Get the user's approval before creating or expiring one.

## Third-Party Integrations

Pro account holders can connect seats.aero to third-party apps via the "Connect seats.aero" button on the website.

- **aeroconnections.app** (by @wavydavy): Visualization tool that shows available connections from specific airports. Log in with your Pro account to see current award space mapped visually. Useful for exploring routing options you wouldn't think to search.

## Notes

- All times in responses are local airport times.
- `TotalTaxes` is in cents (divide by 100 for dollars).
- `MileageCost` in availability objects is a string. In trip objects it's an integer.
- `AllianceCost` in trip objects shows what booking through an alliance partner would cost.
- Dynamic pricing filters are on by default. Pass `include_filtered=true` to see everything.
- Availability data is cached, not live. Check `ComputedLastSeen` for freshness.
- Pro users: 1,000 API calls/day. Failed live searches don't count.
- Free users can only search 30 days ahead. Pro unlocks 60+ days.
- Post-search filters (max points, stops, duration, etc.) now apply directly to flight detail results, not just the search results list.

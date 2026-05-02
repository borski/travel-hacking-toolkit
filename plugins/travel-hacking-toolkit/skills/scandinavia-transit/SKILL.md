---
name: scandinavia-transit
description: Search trains, buses, and ferries in Norway (Entur), Sweden (ResRobot), and Denmark (Rejseplanen). Intra-Scandinavia ground transport with schedules and Danish fare pricing.
category: destinations
summary: Trains, buses, ferries in Norway, Sweden, and Denmark. Includes Danish fare/zone pricing.
api_key: Entur + Trafiklab + Rejseplanen
license: MIT
---

# Scandinavia Transit Skill

Search ground transport (trains, buses, ferries) within Norway, Sweden, and Denmark using their national transit APIs.

**Sources:**
- [Entur (Norway)](https://developer.entur.org) — Open GraphQL API for all Norwegian transit
- [ResRobot (Sweden)](https://www.trafiklab.se/api/trafiklab-apis/resrobot-v21/) — REST API via Trafiklab for all Swedish transit
- [Rejseplanen (Denmark)](https://labs.rejseplanen.dk) — REST API (HAFAS) for all Danish transit including pricing

## Norway: Entur (Journey Planner v3)

Open GraphQL API. No key needed (but a client name header is required). Covers ALL Norwegian transit: Vy trains, buses, ferries, trams, metro. 60+ operators.

### Trip Search (Oslo to Bergen example)

```bash
curl -s -X POST "https://api.entur.io/journey-planner/v3/graphql" \
  -H "Content-Type: application/json" \
  -H "ET-Client-Name: $ENTUR_CLIENT_NAME" \
  -d '{"query": "{ trip(from: {place: \"NSR:StopPlace:59872\"}, to: {place: \"NSR:StopPlace:548\"}, numTripPatterns: 5) { tripPatterns { startTime duration legs { mode expectedStartTime expectedEndTime fromPlace { name } toPlace { name } line { publicCode name authority { name } } } } } }"}' | jq '.data.trip.tripPatterns[] | {start: .startTime, duration_min: (.duration / 60), legs: [.legs[] | {mode: .mode, from: .fromPlace.name, to: .toPlace.name, line: .line.publicCode, operator: .line.authority.name, depart: .expectedStartTime, arrive: .expectedEndTime}]}'
```

### Find Stop IDs

Stop IDs use the format `NSR:StopPlace:XXXXX`. Find them via the Geocoder:

```bash
curl -s "https://api.entur.io/geocoder/v1/autocomplete?text=Oslo%20S&size=3" \
  -H "ET-Client-Name: $ENTUR_CLIENT_NAME" | jq '[.features[] | {name: .properties.name, id: .properties.id, type: .properties.layer}]'
```

### Key Stop IDs

| City | Stop ID | Name |
|------|---------|------|
| Oslo S | NSR:StopPlace:59872 | Oslo S |
| Bergen | NSR:StopPlace:548 | Bergen stasjon |
| Stavanger | NSR:StopPlace:4130 | Stavanger |
| Trondheim | NSR:StopPlace:41742 | Trondheim S |
| Bodo | NSR:StopPlace:49484 | Bodo stasjon |

Use the Geocoder to find any stop. Works for airports, ferry terminals, bus stops too.

### Departure Board

```bash
curl -s -X POST "https://api.entur.io/journey-planner/v3/graphql" \
  -H "Content-Type: application/json" \
  -H "ET-Client-Name: $ENTUR_CLIENT_NAME" \
  -d '{"query": "{ stopPlace(id: \"NSR:StopPlace:59872\") { name estimatedCalls(numberOfDepartures: 10) { expectedDepartureTime destinationDisplay { frontText } serviceJourney { journeyPattern { line { publicCode name transportMode } } } } } }"}' | jq '.data.stopPlace | {name: .name, departures: [.estimatedCalls[] | {time: .expectedDepartureTime, destination: .destinationDisplay.frontText, line: .serviceJourney.journeyPattern.line.publicCode, mode: .serviceJourney.journeyPattern.line.transportMode}]}'
```

### Notes
- GraphQL API. POST only. One endpoint: `https://api.entur.io/journey-planner/v3/graphql`
- Set `ET-Client-Name` header on all requests.
- No rate limit key, but respectful usage expected.
- Schema explorer: https://api.entur.io/graphql-explorer/journey-planner-v3
- Covers some cross-border routes into Sweden via Vy and SJ Nord.

## Sweden: ResRobot v2.1

REST API via Trafiklab. Covers ALL Swedish transit: SJ trains, regional buses, ferries, metro, commuter rail.

### Authentication

`RESROBOT_API_KEY` in `.env`. Use `accessId` query parameter. Free key at [trafiklab.se](https://www.trafiklab.se). 30,000 calls/month.

### Trip Search (Stockholm to Gothenburg)

```bash
curl -s "https://api.resrobot.se/v2.1/trip?originId=740000001&destId=740000002&format=json&accessId=$RESROBOT_API_KEY" | jq '[.Trip[] | {start: .LegList.Leg[0].Origin.time, date: .LegList.Leg[0].Origin.date, duration: .duration, legs: [.LegList.Leg[] | {mode: .type, name: .name, from: .Origin.name, to: .Destination.name, depart: .Origin.time, arrive: .Destination.time}]}] | .[0:5]'
```

### Find Stop IDs

```bash
curl -s "https://api.resrobot.se/v2.1/location.name?input=Stockholm&format=json&accessId=$RESROBOT_API_KEY" | jq '[.stopLocationOrCoordLocation[] | .StopLocation | {name: .name, id: .extId}] | .[0:5]'
```

### Key Stop IDs

| City | Stop ID | Name |
|------|---------|------|
| Stockholm C | 740000001 | Stockholm Centralstation |
| Gothenburg C | 740000002 | Goteborg Centralstation |
| Malmo C | 740000003 | Malmo Centralstation |
| Uppsala | 740000025 | Uppsala Centralstation |
| Linkoping | 740000009 | Linkoping Centralstation |

### Trip Parameters

| Param | Required | Description |
|-------|----------|-------------|
| `originId` | Yes | Departure stop ID |
| `destId` | Yes | Arrival stop ID |
| `date` | No | YYYY-MM-DD (default today) |
| `time` | No | HH:MM (default now) |
| `format` | No | `json` or `xml` |
| `numTrips` | No | Number of results (default 5) |
| `products` | No | Bitmask for transport types |

### Notes
- REST API. Base: `https://api.resrobot.se/v2.1/`
- Includes cross-border Oresund trains to Copenhagen.
- No pricing data. Schedule/route only.

## Denmark: Rejseplanen API 2.0

REST API (HAFAS v2.50.4.1). Covers ALL Danish transit: DSB InterCity/InterCityLyn, S-Tog, Metro, regional trains, buses, express buses, night buses, ferries, Flextur. **Unique: includes fare/zone pricing data.**

Docs: https://labs.rejseplanen.dk (login required). XSD schemas: https://www.rejseplanen.dk/api/xsd

### Authentication

`REJSEPLANEN_API_KEY` in `.env`. Pass as `accessId` query parameter. Apply at [labs.rejseplanen.dk](https://labs.rejseplanen.dk). 50,000 calls/month free (non-commercial).

### Common Parameters

| Param | Description |
|-------|-------------|
| `accessId` | **Required.** API key. |
| `format` | `json` or `xml`. Always use `format=json`. |
| `lang` | Default `da`. Use `lang=en` for English. |

### Product Bitmask

| Value | Product | Description |
|-------|---------|-------------|
| 1 | IC | InterCity |
| 2 | ICL | InterCityLyn (express) |
| 4 | Re | Regional train |
| 8 | Other | ECE, Eurostar, RailJet, Togbus, DSB Udland |
| 16 | S-Tog | Copenhagen commuter rail |
| 32 | Bus | Local bus |
| 64 | ExpressBus | Express bus (250S, X-bus) |
| 128 | NightBus | Natbus |
| 256 | Flextur | Demand-responsive transport |
| 1024 | Metro | Copenhagen Metro |

Trains only = `products=31`. All transit = omit param.

### Key Stop IDs

| Stop | extId | Name |
|------|-------|------|
| København H | 8600626 | København H |
| CPH Lufthavn | 8600858 | CPH Lufthavn |
| Odense St. | 8600512 | Odense St. |
| Aarhus H | 8600053 | Aarhus H |
| Aalborg St. | 8600020 | Aalborg St. |
| Svendborg St. | 8600551 | Svendborg St. |
| Svendborg Færgehavn | 100200261 | Svendborg Færgehavn |
| Ærøskøbing Havn (færge) | 100200222 | Ærøskøbing Havn (færge) |

---

### Location Endpoints

#### location.name (Search by Name)

```bash
curl -s "https://www.rejseplanen.dk/api/location.name?accessId=$REJSEPLANEN_API_KEY&input=København&format=json&type=S" | jq '[.stopLocationOrCoordLocation[] | .StopLocation | {name: .name, id: .extId, lat: .lat, lon: .lon}] | .[0:10]'
```

| Param | Required | Description |
|-------|----------|-------------|
| `input` | Yes | Search query |
| `type` | No | `S` (stops), `A` (addresses), `P` (POI), or combine |
| `maxNo` | No | Max results (default 10, max 1000) |
| `products` | No | Product bitmask filter |
| `r`, `refCoordLat`, `refCoordLong` | No | Radius + reference coordinate for distance ranking |

#### location.nearbystops (Stops Near Coordinate)

```bash
curl -s "https://www.rejseplanen.dk/api/location.nearbystops?accessId=$REJSEPLANEN_API_KEY&originCoordLat=55.672793&originCoordLong=12.564590&r=500&format=json" | jq '[.stopLocationOrCoordLocation[] | .StopLocation | {name: .name, id: .extId, dist: .dist}] | .[0:10]'
```

Requires `originCoordLat`/`originCoordLong`. Optional: `r` (radius, default 1000m), `maxNo`, `type`, `products`.

#### location.details

Single location details by full HAFAS ID (URL-encoded).

#### location.data

Locations in a numeric ID range (`llId` to `urId`).

#### location.search

Filtered location search. Same params as `location.name` plus additional filters.

#### location.boundingbox

All stops in a geographic box (`llLat`/`llLon` to `urLat`/`urLon`).

#### addresslookup

Addresses near a coordinate. Reverse geocoding. Requires `originCoordLat`/`originCoordLong`.

---

### Trip Planning Endpoints

#### trip (Route Planning)

```bash
curl -s "https://www.rejseplanen.dk/api/trip?accessId=$REJSEPLANEN_API_KEY&originId=8600626&destId=8600551&date=2026-08-28&time=08:00&format=json&lang=en" | jq '[.TripList.Trip[] | {duration: .duration, legs: [.LegList.Leg[] | {name: .name, type: .type, from: .Origin.name, to: .Destination.name, depTime: .Origin.time, arrTime: .Destination.time, track: .Origin.track}]}] | .[0:3]'
```

| Param | Required | Description |
|-------|----------|-------------|
| `originId` | Yes* | Origin stop extId |
| `destId` | Yes* | Destination stop extId |
| `originCoordLat/Long` | Yes* | Origin by coordinate (alt to originId) |
| `destCoordLat/Long` | Yes* | Destination by coordinate (alt to destId) |
| `date` | No | YYYY-MM-DD |
| `time` | No | HH:MM |
| `searchForArrival` | No | `1` = search by arrival time |
| `numF` | No | Forward results (1-6) |
| `numB` | No | Backward results (0-3) |
| `maxChange` | No | Max transfers (0-11) |
| `products` | No | Product bitmask |
| `operators` | No | Comma-separated operator codes |
| `lines` | No | Line filter |
| `via` | No | Via stop ID |
| `avoid` | No | Avoid stop ID |
| `passlist` | No | `1` = include intermediate stops |
| `tariff` | No | `1` = include fare/zone pricing |
| `poly` | No | `1` = include polyline |
| `context` | No | Scroll token for paging |
| `originWalk/Bike/Car` | No | Access mode distance |
| `destWalk/Bike/Car` | No | Egress mode distance |
| `rtMode` | No | `FULL`, `INFOS`, `OFF`, `REALTIME`, `SERVER_DEFAULT` |

#### interval (Interval Trip Search)

All departures in a time window. Same params as `trip`.

#### recon (Trip Reconstruction)

Reconstruct trip from `ctxRecon` token. Params: `ctx` (required), `poly`, `passlist`, `tariff`.

#### reachability (All Reachable Stops)

All stops reachable within time/transfer budget. Params: `originId` or coordinates, `duration` (1-1439 min), `maxChange` (0-11), `forward`, `products`.

---

### Departure and Arrival Boards

Default duration: 60 minutes.

#### departureBoard / arrivalBoard

```bash
curl -s "https://www.rejseplanen.dk/api/departureBoard?accessId=$REJSEPLANEN_API_KEY&id=8600626&date=2026-08-28&time=08:00&format=json&lang=en" | jq '[.DepartureBoard.Departure[] | {name: .name, time: .time, direction: .direction, track: .track, rtTime: .rtTime}] | .[0:10]'
```

Params: `id` (required), `date`, `time`, `duration` (0-1439), `maxJourneys`, `products`, `operators`, `passlist`.

#### multiDepartureBoard / multiArrivalBoard

Multiple stations in one call. Pass multiple `id` params.

#### nearbyDepartureBoard / nearbyArrivalBoard

Stations near a coordinate. Params: `originCoordLat/Long`, `r` (default 1000m), `maxStops` (default 30).

---

### Line and Journey Endpoints

#### lineinfo

Line details on a date. Requires `lineId`, `date`.

#### linesched

Full schedule for a line on a date. Requires `lineId`, `date`.

#### linesearch

All lines by operator. Requires `operators` (comma-separated, from `datainfo`).

#### linematch

Match lines by pattern string.

#### trainSearch

Find journeys by train name. Returns first/last stop only.

#### journeyDetail

Full stop list for a journey. Requires `id` (journey ref from trip/board). Optional: `fromId`/`toId`, `poly`, `rtMode`.

#### journeyMatch

Like `trainSearch` but full details for first match only.

#### journeypos

Real-time vehicle positions in bounding box. Requires `llLat/llLon/urLat/urLon`.

---

### Tariff / Pricing Endpoints

Denmark uses zone-based pricing via Rejsekort. Unique in Scandinavia.

| Endpoint | Purpose |
|----------|---------|
| `trip` with `tariff=1` | Inline pricing in trip results |
| `spPrice` | Season pass price by origin/destination |
| `spPriceForZones` | Price per day for zone count in fare set |
| `spDailyZonalPrices` | Full zone price matrix, all passenger types |
| `spPriceReconstruction` | Price from trip reconstruction context |
| `spRefund` | Season pass refund calculation |
| `spCheck` | Season pass validation (SELF system) |
| `spZoneCheck` | Check zone connectivity and metro zones |
| `stRoutes` | Tariff routes between origin/destination |
| `stRoutesAddon` | Tariff routes from single origin |
| `stStops` | Tariff zones and stops (mode=DSB) |
| `trfStop` | Default stop for a zone |
| `convertZones` | Tariff details for context |
| `zoneFromCoordinate` | Zone lookup by lat/lon |

---

### Travel Detail Endpoints

#### gisroute

Walking/cycling route details from trip result. Requires `ctx` (GIS reference).

#### himsearch

Real-time disruption messages. Filterable by products, operators, lines, dates, stops.

---

### System Information

#### datainfo

All operators, products, categories. Use to discover operator codes.

```bash
curl -s "https://www.rejseplanen.dk/api/datainfo?accessId=$REJSEPLANEN_API_KEY&format=json" | jq '[.DataInfo.operators.Operator[] | {name: .name, id: .id}] | .[0:20]'
```

#### tti

Timetable data pool info: ID, creation date, type (ST/ADR/POI), validity period.

---

### Response Structure

- `extId`: Numeric stop ID (use for queries). `id` is the full HAFAS string.
- `rtTime`/`rtDate`: Real-time actual/predicted times (when different from scheduled `time`/`date`).
- Leg `type`: `JNY` (journey), `WALK` (walking), `TRSF` (transfer).
- `JourneyDetailRef`: Use with `journeyDetail` for full stop list.

---

## Cross-Border Routes

| Route | Covered By | Notes |
|-------|------------|-------|
| Oslo to Stockholm | Entur + ResRobot | SJ trains, ~6 hours |
| Malmö to Copenhagen | ResRobot + Rejseplanen | Øresund trains, 35 min |
| Gothenburg to Oslo | Entur + ResRobot | Vy/SJ, ~4 hours |
| Stockholm to Copenhagen | ResRobot | SJ/DSB, ~5 hours via Malmö |
| Copenhagen to Malmö | Rejseplanen | Øresund trains from Danish side |

## When to Use

Load this skill when:
- Planning train/bus/ferry routes between Scandinavian cities
- Checking schedules and durations for ground transport
- Finding stop IDs for trip planning
- Comparing train vs flight for intra-Scandinavia legs
- Looking up Danish transit fares/zones
- Checking real-time disruptions (`himsearch`)
- Tracking live vehicle positions (`journeypos`)

Do not:
- Use for booking (search/schedule only)
- Use for flights (use Seats.aero, SerpAPI, or Duffel)
- Expect pricing from Entur or ResRobot (only Rejseplanen has pricing)

---

## Search Workflows

### 1. "How do I get from A to B?"

**Step 1:** Pick API by country (Norway=Entur, Sweden=ResRobot, Denmark=Rejseplanen, cross-border=both).

**Step 2:** Find stop IDs:

```bash
# Norway
curl -s "https://api.entur.io/geocoder/v1/autocomplete?text=Flåm&size=3" \
  -H "ET-Client-Name: $ENTUR_CLIENT_NAME" | jq '[.features[] | {name: .properties.name, id: .properties.id}]'

# Sweden
curl -s "https://api.resrobot.se/v2.1/location.name?input=Malmö&format=json&accessId=$RESROBOT_API_KEY" | jq '[.stopLocationOrCoordLocation[] | .StopLocation | {name: .name, id: .extId}] | .[0:5]'

# Denmark
curl -s "https://www.rejseplanen.dk/api/location.name?accessId=$REJSEPLANEN_API_KEY&input=Svendborg&format=json&type=S&lang=en" | jq '[.stopLocationOrCoordLocation[] | .StopLocation | {name: .name, id: .extId}] | .[0:5]'
```

**Step 3:** Trip search with `date` and `time`. **Step 4 (Denmark):** Add `tariff=1` for pricing.

### 2. "What trains leave from X?"

```bash
curl -s "https://www.rejseplanen.dk/api/departureBoard?accessId=$REJSEPLANEN_API_KEY&id=8600626&duration=120&products=31&format=json&lang=en" | jq '[.DepartureBoard.Departure[] | {time: .time, name: .name, direction: .direction, track: .track}]'
```

### 3. "What's near me?"

```bash
curl -s "https://www.rejseplanen.dk/api/location.nearbystops?accessId=$REJSEPLANEN_API_KEY&originCoordLat=55.6736&originCoordLong=12.5681&r=500&format=json&lang=en" | jq '[.stopLocationOrCoordLocation[] | .StopLocation | {name: .name, id: .extId, dist: .dist}]'
```

Or `nearbyDepartureBoard` to skip stop lookup.

### 4. "What ferry to Ærø?"

```bash
curl -s "https://www.rejseplanen.dk/api/trip?accessId=$REJSEPLANEN_API_KEY&originId=100200261&destId=100200222&date=2026-08-28&time=08:00&format=json&lang=en" | jq '[.TripList.Trip[] | {legs: [.LegList.Leg[] | {name: .name, from: .Origin.name, to: .Destination.name, depTime: .Origin.time, arrTime: .Destination.time}]}] | .[0:5]'
```

### 5. "I know the train number."

`trainSearch` to find it, then `journeyDetail` with the ref for full stops.

### 6. "What can I reach in 2 hours?"

```bash
curl -s "https://www.rejseplanen.dk/api/reachability?accessId=$REJSEPLANEN_API_KEY&originId=8600626&duration=120&maxChange=2&format=json" | jq '.'
```

### 7. "Any disruptions?"

```bash
curl -s "https://www.rejseplanen.dk/api/himsearch?accessId=$REJSEPLANEN_API_KEY&format=json&lang=en" | jq '.'
```

### 8. Multi-country trips

Search from both ends. Øresund trains appear in both ResRobot and Rejseplanen.

### Tips

- Always `format=json`. Always `lang=en` for Rejseplanen.
- Use `extId` (numeric) for queries, not the long HAFAS `id` string.
- Check `rtTime`/`rtDate` for delays.
- `passlist=1` shows intermediate stops.
- `maxChange=0` for direct connections only.
- Page with `numF`/`numB` or `context` scroll tokens.
- Product bitmask is additive. Omit for all types.

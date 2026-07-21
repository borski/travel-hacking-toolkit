---
name: flight-search-strategy
description: Canonical multi-source flight search strategy. Source priority (Duffel, Ignav, Google Flights, Skiplagged, Kiwi, Seats.aero, Southwest), parallel workflow, market selection for international price arbitrage.
category: reference
summary: The canonical multi-source search workflow. Source priority (Duffel > Ignav > Google Flights > others), market selection for international routes, source accuracy hierarchy, common failure modes.
---

# Flight Search Strategy

## Search ALL Sources for EVERY Flight Search

This is not a pick-one list. Each source returns different results, different prices, and different airlines. Missing a source means missing options. The priority order determines which price to trust when sources disagree, not which sources to skip.

| Priority | Source | Strengths | Blind Spots |
|----------|--------|-----------|-------------|
| 1 | **Duffel** (skill) | Most accurate cash prices. Real GDS per-fare-class data. Bookable. | No Southwest. No award pricing. Offers expire in 15-30 min. |
| 2 | **Ignav** (skill) | Fast REST API. Market selection for price arbitrage. Free. | No Southwest. No award pricing. |
| 3 | **Google Flights** (skill, agent-browser) | Covers ALL airlines including Southwest cash prices. Free. Economy/business comparison. | Prices can be inflated vs GDS. No points pricing. |
| 4 | **Skiplagged** (MCP) | Hidden city fares. Zero config. | No Southwest. Can be noisy on small markets. |
| 5 | **Kiwi.com** (MCP) | Virtual interlining (creative cross-airline routings). Zero config. | Returns garbage on small markets. No Southwest. |
| 6 | **Seats.aero** (skill) | Award flight availability across 25+ programs. The crown jewel for points. | Cached data, not live. No cash prices. No Southwest. |
| 7 | **SerpAPI** (skill, optional) | Google Hotels search. Destination discovery (Google Travel Explore). | NOT for flights (inflated prices). Hotels and "where should I go?" only. |
| 8 | **Southwest** (skill, Patchright) | Fare classes, points pricing, Companion Pass. All 4 fare classes, cash + points. | Pre-built Docker image: `ghcr.io/borski/sw-fares`. Or local Patchright (headed mode). ~20s per search. |

## The Standard Flight Search Workflow

**Run ALL of these in parallel:** Duffel + Ignav + Google Flights + Skiplagged + Kiwi.

Skiplagged and Kiwi are keyless MCP servers — they are available in every properly launched session. Attempt the tool call before ever claiming MCP is unavailable, and never substitute improvised browser scraping for these sources (see `fallback-and-resilience`).

Always add Seats.aero for award comparison. Always run the Southwest skill if SW flies the route.

Don't skip sources. Don't assume one source has everything. Present the combined results with the best options highlighted regardless of which source found them.

**For a single unified comparison, use the `compare-flights` skill** which orchestrates all of the above in parallel and applies transfer partner optimization.

## Round Trip vs One-Way Construction

When the trip has a return date, price BOTH constructions — proactively, without being asked:

1. **The round-trip fare** on every source (Duffel, Ignav, Kiwi, Skiplagged, and Google Flights all quote returns).
2. **Two one-ways**, searched independently — which also surfaces the mixed construction (outbound on carrier A, return on carrier B) that round-trip searches can't see.

Run all of it in the same parallel batch; it's two extra searches, not a second pass.

Which wins is route-dependent, so never assume:

- **Round trips often win internationally** on legacy carriers, where return fares are discounted relative to two one-ways.
- **One-way pairs often win domestically**, on ULCCs, and anywhere Southwest flies (SW prices every leg as a one-way). They also buy flexibility: each leg can be changed or canceled independently.
- **Mixed-carrier pairs** frequently beat both when outbound and return are priced by different airlines' sale calendars.

Present the verdict explicitly with the delta: "Round trip $842 vs best one-way pair $918 — book the round trip, saves $76" (or the reverse). If the gap is under ~$50, mention the flexibility advantage of separate tickets before recommending the round trip.

## For Southwest Specifically

Use the southwest skill:

```bash
docker run --rm ghcr.io/borski/sw-fares --origin SJC --dest DEN --depart 2026-05-15 --points
```

Or:

```bash
python3 skills/southwest/scripts/search_fares.py --origin SJC --dest DEN --depart 2026-05-15 --points
```

Returns all 4 fare classes (Wanna Get Away, WGA+, Anytime, Business Select), cash and points pricing.

The google-flights skill is a faster fallback for SW cash prices only (no fare class breakdown, no points pricing).

## Monitoring Existing Southwest Reservations

```bash
docker run --rm -e SW_USERNAME -e SW_PASSWORD \
  ghcr.io/borski/sw-fares change --conf ABC123 --first Jane --last Doe --json
```

Logs in, selects both legs, and shows fare diffs for every available flight. Negative diffs = savings opportunity. Use `--list` to discover all upcoming confirmation numbers. Read-only. Never modifies reservations.

## Market Selection Strategy

Different country markets return different prices for the same route. Searching from Thailand (`&gl=TH`) vs the US (`&gl=US`) can save hundreds of dollars.

**Always try multiple markets for international flights:**

1. **Departure country market first** (e.g., `&gl=US` for flights from the US)
2. **Destination country market** (e.g., `&gl=JP` for flights to Japan)
3. **Ask the user before trying more** (e.g., third countries, VPN markets)

This applies to:
- **google-flights** via the `&gl=XX` URL parameter
- **ignav** via the `market` field in the search payload

**Duffel and SerpAPI don't support market selection.**

## Source Accuracy Hierarchy

When sources disagree on cash prices:

**Duffel > Airline website > SerpAPI > Skiplagged/Kiwi**

1. **Duffel returns real GDS prices per fare class.** These are bookable. Tested: Duffel showed $271 basic / $325 main. SerpAPI showed $541 for the same flight. The gap was consistent across multiple itineraries.
2. **SerpAPI (Google Flights) inflates prices.** Often shows "main cabin" or bundled fares, not the cheapest bookable fare class. Useful for Google Hotels and destination discovery, but do not trust it as the sole source for flight cash prices.
3. **Kiwi returns garbage on small markets.** Filter hard or skip Kiwi for domestic routes to small airports.

## Common Failure Modes

- Running only one source and missing better options on others.
- Trusting SerpAPI prices as bookable (they're often inflated).
- Skipping Southwest because "no GDS has it" — exactly why you need the SW skill.
- Skipping Seats.aero because the user "doesn't have those points" — they may have them via transfer, see the `partner-awards` skill.
- Single-market search on international routes (always try at least 2 markets).

---
name: flight-search-strategy
description: The canonical strategy for flight searches. Covers source priority across all skills (Duffel, Ignav, Google Flights, Skiplagged, Kiwi, Seats.aero, Southwest), parallel search workflow, market selection for international routes (different country markets return different prices), and how to combine cash + award results. Load whenever running a flight search, designing a parallel search plan, or deciding which sources to query for a specific route. Triggers on "search flights", "flight search", "find flights", "compare flights", "cheapest flight to", "award and cash", "which sources should I check", "market selection", "international flight pricing", or any flight-discovery task.
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

Always add Seats.aero for award comparison. Always run the Southwest skill if SW flies the route.

Don't skip sources. Don't assume one source has everything. Present the combined results with the best options highlighted regardless of which source found them.

**For a single unified comparison, use the `compare-flights` skill** which orchestrates all of the above in parallel and applies transfer partner optimization.

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

---
name: compare-flights
description: Unified flight comparison across all sources. Searches cash prices (Duffel, Ignav), award availability (seats.aero), and portal pricing (Chase UR, Amex MR) in parallel. Applies transfer partner optimization automatically. Outputs one comparison table with recommendations.
category: orchestration
summary: Unified flight comparison across ALL sources in parallel. Auto-applies transfer optimization.
api_key: Uses individual skill keys
---

# Compare Flights

Search every available source for a route and present one unified comparison. Combines cash pricing, award availability, portal pay-with-points, and transfer partner optimization into a single table.

**This is an orchestration skill.** It tells the agent which tools to run and how to combine results. No standalone script.

**Companion reference skills.** Load these for deeper context:
- `flight-search-strategy` — full source priority, market selection, source accuracy hierarchy
- `points-valuations` — CPP rules, floor/ceiling, surcharge programs, transfer bonuses
- `partner-awards` — alliance + bilateral partnership reachability
- `lessons-learned` — Seats.aero workflow, Southwest specifics, Companion Pass math
- `fallback-and-resilience` — what to do when a source fails
- `transfer-bonuses` — current active transfer bonuses (live data); changes effective ratios when computing options 4-7 of the comparison table
- `stopovers` — when an itinerary has a long layover or multi-city, check if a stopover-allowing program priced lower than separate one-ways
- `round-the-world` — for 3+ stop multi-region itineraries, RTW products may beat sum-of-parts award pricing

## When to Use

- "Find me the best way to get from SFO to CDG in August"
- "Should I pay cash or use points for this flight?"
- "Compare all options for SFO to NRT business class"
- Any flight search where the user wants the full picture

## Sources

Run these in parallel where possible. **Never fail silently.** If a source errors, report it in the output so the user knows what's missing.

### Cash Prices (run in parallel)

| Source | Skill | Speed | Notes |
|--------|-------|-------|-------|
| Duffel | `duffel` | ~3s | Primary. Real GDS fares with fare classes. No Southwest. |
| Ignav | `ignav` | ~2s | Fast REST API. Good for price comparison. Booking links. |
| Google Flights | `google-flights` | ~10s | Browser-automated. All airlines including Southwest cash. Good cross-check. |
| Skiplagged | web search | ~5s | Hidden city ticketing. Often finds significantly cheaper fares. Search `skiplagged.com/flights/{origin}/{dest}/{date}`. |
| Kiwi.com | web search | ~5s | Creative routings, self-transfer combos, multi-city. Search `kiwi.com`. |
| Southwest | `southwest` | ~20s | Patchright, Docker only. Points + cash for all 4 fare classes. Only needed when SW flies the route. |

**Skiplagged and Kiwi:** Use web search (tavily or exa) to find their prices. They don't have MCP skills but their URLs are predictable. Always note that Skiplagged fares have restrictions (can't check bags, must use the "missed" connection city as destination).

**Southwest:** Run the `southwest` skill if SW flies the route. Include SW Rapid Rewards points in the comparison table as a separate currency. The `lessons-learned` skill has the full details on SW specifics (fare class requirements, Companion Pass math, GDS gap).

**SerpAPI is optional.** Only use if the user asks for Google Hotels or destination discovery.

### Award Availability

| Source | Skill | Speed | Notes |
|--------|-------|-------|-------|
| Seats.aero | `seats-aero` | ~5s | Cached award availability across 25+ programs. Primary award source. |

### Portal Pay-With-Points (run in parallel, Docker required)

| Source | Skill | Speed | Notes |
|--------|-------|-------|-------|
| Chase UR | `chase-travel` | ~45s | Points Boost detection. 1.5x CSR multiplier at checkout. |
| Amex MR | `amex-travel` | ~45s | IAP discount detection on Platinum. |

Portal searches are slower (require browser login). Run them in parallel with each other, but don't block on them. Start cash + award searches first, present those results, then append portal results when ready.

**Only run portal searches if the user has the relevant card or asks for portal pricing.** Don't run Chase if they don't have a Sapphire card.

## Workflow

### Step 1: Gather All Prices

Run searches in parallel. Track which sources succeeded and which failed.

```
PARALLEL GROUP 1 (fast, ~3-5s):
  - Duffel: cash prices with fare classes
  - Ignav: cash prices with booking links
  - Seats.aero: award availability by program
  - Skiplagged: hidden city fares (web search)
  - Kiwi.com: creative routings (web search)

PARALLEL GROUP 2 (browser-automated, ~10-45s, Docker):
  - Google Flights: all airlines including Southwest cash
  - Southwest: points + cash for all fare classes (if SW flies the route)
  - Chase Travel: UR portal pricing + Points Boost
  - Amex Travel: MR portal pricing + IAP discounts
```

For each source, capture:
- Source name
- Status: "ok" | "error: {reason}" | "skipped: {reason}"
- Results count
- Data

### Step 2: Apply Transfer Partner Optimization

For every seats.aero award result, calculate the effective cost in each transferable currency using `data/transfer-partners.json`:

```
For each award (e.g., United business at 88,000 miles):
  1. Look up which currencies transfer to United: Chase UR (1:1), Bilt (1:1)
  2. Calculate effective cost: 88,000 / 1.0 = 88,000 UR or 88,000 Bilt
  3. Calculate opportunity cost using data/points-valuations.json:
     88,000 UR × 1.7cpp floor = $1,496 equivalent
```

**Include ALL viable transfer paths**, not just the cheapest. The user may have more points in one currency than another.

### Step 3: Calculate Portal CPP

Chase portal quotes at 1.0 cpp in listings. The CSR 1.5x is applied at checkout:

```
Listed: 539,683 points for a $5,397 flight
Effective: 539,683 ÷ 1.5 = 359,789 UR points actually deducted
True CPP: $5,397 / 359,789 = 1.5 cpp (by definition)
```

For Points Boost offers, the boost price replaces the standard:
```
Boost: 269,841 points for a $5,397 flight
Effective: 269,841 ÷ 1.5 = 179,894 UR points
True CPP: $5,397 / 179,894 = 3.0 cpp (excellent)
```

Amex portal is 1 cpp for flights (1 MR = 1 cent). IAP fares are discounted cash prices:
```
Standard: $5,044 = 504,400 MR points
IAP: $4,381 = 438,100 MR points (saves 66,300 MR)
```

### Step 4: Present Unified Table

**Always use markdown tables.** One table with all options sorted by effective cost.

#### Example: SFO → CDG Business Class, Aug 11

| # | Option | Source | Price | Points | Currency | CPP | Rating |
|---|--------|--------|-------|--------|----------|-----|--------|
| 1 | Cash (lowest) | Duffel | $4,200 | — | — | — | — |
| 2 | Flying Blue via Chase UR | seats.aero | $120 tax | 55,000 | Chase UR | 7.4 | Excellent |
| 3 | Aeroplan via Chase UR | seats.aero | $200 tax | 70,000 | Chase UR | 5.7 | Excellent |
| 4 | Chase Portal (Boost) | chase-travel | — | 180,000 | Chase UR | 3.0 | Excellent |
| 5 | Chase Portal (standard) | chase-travel | — | 360,000 | Chase UR | 1.5 | Baseline |
| 6 | Amex Portal (IAP) | amex-travel | — | 438,100 | Amex MR | 1.0 | Poor |
| 7 | Amex Portal (standard) | amex-travel | — | 504,400 | Amex MR | 0.83 | Poor |

#### Example: SFO → LAX Economy, Aug 11

| # | Option | Source | Price | Points | Currency | CPP | Rating |
|---|--------|--------|-------|--------|----------|-----|--------|
| 1 | SW Wanna Get Away | southwest | $79 | 5,200 | SW RR | 1.52 | Good |
| 2 | Cash (lowest) | Duffel | $89 | — | — | — | — |
| 3 | SW WGA+ | southwest | $119 | 8,400 | SW RR | 1.42 | Fair |
| 4 | United via Chase UR | seats.aero | $5.60 tax | 5,000 | Chase UR | 1.67 | Good |
| 5 | Chase Portal | chase-travel | — | 8,900 | Chase UR | 1.5 | Baseline |
| 6 | SW Anytime | southwest | $219 | 16,800 | SW RR | 1.30 | Fair |

Note: SW points values shown use direct redemption CPP. If the user has Companion Pass, effective CPP doubles (two tickets for the points price of one).

**Sources checked:**
- ✅ Duffel: 45 results
- ✅ Ignav: 38 results
- ✅ Skiplagged: 3 hidden city options
- ✅ Kiwi.com: 12 creative routings
- ✅ Seats.aero: 12 award options
- ✅ Southwest: 4 fare classes (WGA $79/5.2K, WGA+ $119/8.4K, Anytime $219/16.8K, BizSelect $289/22.1K)
- ✅ Chase Travel: 300 results (3 with Points Boost)
- ✅ Amex Travel: 292 results (IAP available)
- ✅ Google Flights: 52 results

### Step 5: Recommendation

After the table, always provide:

1. **Best overall value:** Which option gives the most CPP
2. **Best convenience:** Which is easiest to book (online vs call, instant transfer vs wait)
3. **Cash vs points verdict:** Using the trip-calculator framework:
   - If cash < opportunity cost of best award → "Pay cash"
   - If cash > opportunity cost → "Use points"
4. **Transfer warning:** "Don't transfer until you confirm availability. Transfers are usually instant but can take 48h."
5. **Balance check:** If the user's balances are known (from AwardWallet or prior context), flag if they don't have enough points

## Error Handling

**NEVER fail silently.** Every source must report its status.

If a source fails:
```
- ❌ Duffel: API error (rate limit exceeded). Cash prices from Ignav only.
- ❌ Chase Travel: Login failed (2FA timeout). No portal pricing available.
```

If ALL cash sources fail, say so explicitly. Don't present award-only results without noting the missing cash comparison.

If seats.aero returns no availability, say "No award availability found" instead of silently omitting the award section.

## Data Files Used

| File | Purpose |
|------|---------|
| `data/transfer-partners.json` | Credit card → loyalty program transfer ratios |
| `data/points-valuations.json` | CPP floor/ceiling for calculating opportunity cost |
| `data/partner-awards.json` | Cross-alliance booking options (VA→ANA, EY→AA, etc.) |

## Limitations

- Portal searches require Docker and login credentials. Skip if not configured.
- Seats.aero shows cached availability (up to 24h old). Live search via seats-aero-web is local only.
- Transfer ratios are from `transfer-partners.json`. Verify against issuer before large transfers.
- Chase portal prices don't include the 1.5x CSR multiplier. The skill adjusts automatically.
- Southwest is NOT in Duffel, Ignav, or seats.aero. Use Google Flights skill if SW pricing needed.

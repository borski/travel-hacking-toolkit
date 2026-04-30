---
name: round-the-world
description: Reference for round-the-world (RTW), Pacific Circle, Asia-Pacific Circle, and regional distance-based award products across all alliances. Auto-load when the user asks about RTW tickets, multi-stop global itineraries, Star Alliance RTW, oneworld Explorer, oneworld Global Explorer, Pacific Circle, Asia-Pacific circles, distance-based award charts (Aeroplan, JAL, Cathay, Iberia), or considers a long itinerary that might benefit from RTW pricing.
category: reference
summary: RTW + Pacific Circle + Asia-Pacific Circle + regional distance-award reference. 13 active programs, 4 discontinued.
---

# Round the World, Circle Pacific, and Distance-Based Awards

The RTW universe is collapsing. Four programs ended in the last 18 months: ANA Star RTW (June 2025), Singapore KrisFlyer Star RTW (May 2024), SkyTeam Go Round (2024-25), Singapore KrisFlyer Pacific Circle (likely 2024-25). What's left is concentrated in Star Alliance, oneworld, and a few regional distance-based programs.

This skill provides:
- Comprehensive coverage of every active RTW and Circle product
- Historical charts for discontinued programs (so the agent doesn't get fooled by stale blog posts)
- Distance-based regional alternatives that often beat RTW pricing for shorter trips
- Decision rules for picking the right product

**Data file:** `data/rtw-awards.json`. Contains 17 programs with confidence markers (VERIFIED / LIKELY) and primary-source citations.
**Distance helper:** `scripts/calc_distance.py` (haversine, supports cumulative multi-segment routes, with built-in distance-band lookups for Star Alliance / Qantas / oneworld Global Explorer).

## Quick Decision Tree

```
Want to actually circle the globe?
  └→ Want to pay cash? → oneworld Explorer (3-6 continents, online bookable, $3,599-6,899 economy)
  └→ Want to use miles?
       ├→ Star Alliance RTW (online bookable; Special Business 26k mi for ~$7,000-7,400 J ← steal)
       ├→ Lufthansa M&M (fixed 195k Y / 400k J / 540k F miles, phone only)
       └→ Qantas oneworld Classic Reward RTW (35k mi cap, 132,400/318,000 Y/J pts)

Want to circle the Pacific Rim only?
  ├→ Star Alliance Circle Pacific (online via member; 22k or 26k mi)
  └→ oneworld Circle Pacific (travel agent only)

Want a multi-carrier oneworld trip but not full RTW?
  ├→ Cathay Asia Miles oneworld multi-carrier (13 distance bands; cheapest J at 60k mi <1000mi)
  ├→ JAL Mileage Bank multi-carrier (10 bands; sweet spot 25k Y / 48k J <4000mi)
  └→ Qantas oneworld Classic (separate from its RTW config)

Just want regional flights cheap?
  ├→ Aeroplan distance-based (NA: 6k Y starting <500mi; Atlantic: 32.5k Y starting <4000mi)
  └→ Iberia Plus Avios (intra-Europe: 3,500 Y under 650mi off-peak)
```

## Active Products

### Star Alliance RTW — `staralliance.com/tnc-rtw`

The most flexible RTW still on the market. Three fare types:

| Fare type        | Distance bands (mi)        | Cabins              | Stopovers | Notes |
|------------------|----------------------------|---------------------|-----------|-------|
| Normal RTW       | 29k / 34k / 39k            | Y / W / J / F       | 2-15      | Globally available |
| Special Economy  | 26k / 29k / 34k / 39k      | Y                   | 3-12      | NOT from Japan |
| Special Business | 26k                        | J                   | 5         | NOT from Japan; ~$7,000-7,400 USD; **the steal** |

**Rules:**
- Origin/destination same country
- Single direction (E or W)
- Each Traffic Conference crossed once
- Up to 16 segments, 5 surface sectors
- Min stay 10 days, max 1 year
- Reroute fee $125, cancel fee $150
- Purchase ≥72 hrs before first departure

**Pricing in miles:** Star Alliance RTW tickets are priced in cash USD/local currency, then redeemable for member-program miles. United MileagePlus, Aeroplan, Lufthansa M&M, Avianca LifeMiles all support the redemption with their own mile costs. Compare programs.

### Star Alliance Circle Pacific — `staralliance.com/tnc-cp`

Same product family as RTW but constrained to Pacific Rim:
- 22,000 or 26,000 mi distance bands
- Must touch Asia, North America, **and** South West Pacific
- 3-15 stopovers
- 7 days min, 6 months max
- Reroute $75, cancel 10% of fare
- Customer Service or member airline only (not online self-service)

### oneworld Explorer — `rtw.oneworld.com`

Continent-based (not distance-based). Online bookable.

| Continents | Economy USD | Business | First |
|-----------|-------------|----------|-------|
| 3         | $3,599      | TBD      | TBD   |
| 4         | $4,999      | TBD      | TBD   |
| 5         | $5,699      | TBD      | TBD   |
| 6         | $6,899      | TBD      | TBD   |

**Rules:** 16 max segments, 2-15 stopovers. Premium economy upgrades available.

### oneworld Global Explorer — `rtw.oneworld.com`

Distance-based alternative to Explorer. 39,000-mile cap. **Travel agent only** (not bookable on rtw.oneworld.com self-service).

### oneworld Circle Pacific — `rtw.oneworld.com`

Pacific-bordering circle product. 4 regions: Asia (incl. Indian subcontinent + Central Asian -stans), Australia, New Zealand & SW Pacific, North America. **Travel agent only.** Specific cap and pricing not surfaced publicly.

### Lufthansa Miles & More RTW — `miles-and-more.com`

Fixed-mile pricing, no distance bands:

| Cabin    | Miles   |
|----------|---------|
| Economy  | 195,000 |
| Business | 400,000 |
| First    | 540,000 |

**Rules:** Up to 10 segments, 7 stopovers. Must cross Atlantic AND Pacific. Min 10 days between first/last intercontinental flight. Phone only.

### Qantas oneworld Classic Reward (RTW config) — `qantas.com`

| Cabin    | Points  |
|----------|---------|
| Economy  | 132,400 |
| Business | 318,000 |

**Rules:** 35,000 mi distance cap. Must combine 2+ oneworld carriers. Bookable online or phone (US: 800-227-4220). Fuel surcharges apply.

### Cathay Asia Miles oneworld Multi-Carrier — `flights.cathaypacific.com`

13 distance bands (post-May 2026 chart):

| Band | Max mi | Y      | J       | F       |
|------|--------|--------|---------|---------|
| 1    | 1,000  | 30,000 | 60,000  | 75,000  |
| 5    | 7,500  | 60,000 | 125,000 | 165,000 |
| 9    | 22,000 | 110,000| 215,000 | 280,000 |
| 13   | 50,000 | 160,000| 280,000 | 380,000 |

**Rules:** 2 stopovers + 2 transfers max. Must combine 2+ oneworld carriers (excluding Cathay).

### JAL Mileage Bank Single-Partner — `jal.co.jp/jp/en/jalmile/use/partner_air/p_jmb/jmb_mile.html`

Use this when flying ONE partner airline (not JAL, not multi-carrier oneworld). 13 distance bands.

| Band | Max mi | Y      | W      | J       | F       |
|------|--------|--------|--------|---------|---------|
| 1    | 1,000  | 12,000 | 17,000 | 24,000  | 36,000  |
| 5    | 7,000  | 35,000 | 45,000 | 60,000  | 90,000  |
| 9    | 22,000 | 95,000 | 115,000| 160,000 | 240,000 |
| 13   | 50,000 | 150,000| 180,000| 210,000 | 330,000 |

**Caveats:** F not available on MH, AF, KE, EK. F priced at business cost on AA 2-class + AS + HA. Fuel surcharges apply. IATA TPM distance.

### JAL Mileage Bank oneworld Multi-Carrier — `jal.co.jp/jp/en/jalmile/use/partner_air/oneworld/miles.html`

10 distance bands. **Sweet spot at band 1.**

| Band | Max mi | Y       | J       | F       |
|------|--------|---------|---------|---------|
| 1    | 4,000  | 25,000  | 48,000  | 72,000  |
| 5    | 18,000 | 75,000  | 138,000 | 207,000 |
| 8    | 30,000 | 130,000 | 195,000 | 293,000 |
| 10   | 50,000 | 160,000 | 220,000 | 330,000 |

Examples: AA Flagship transcon JFK-LAX/SFO + return = ~5,000 mi RT = band 2 = 41k Y / 78k J. Or 25k Y / 48k J if it's a tight regional itinerary under 4,000 mi total.

### Aeroplan Flight Reward — `aircanada.com` (June 2026 chart)

Dynamic pricing on Air Canada + Select Partners (UA, EK, FZ, EY, Canadian North, Calm Air, Bearskin, PAL). Distance-based. "Starting at" is the floor; "Median" is realistic mid-point pricing.

**Within North America (4 distance bands):**
- ≤500 mi: 6,000 Y / 15,000 J starting
- ≤1,500 mi: 10,000 Y / 20,000 J
- ≤2,750 mi: 12,500 Y / 25,000 J
- >2,750 mi: 17,500 Y / 35,000 J

**North America ↔ Atlantic:**
- ≤4,000 mi: 32,500 Y / 60,000 J / 90,000 F
- ≤6,000 mi: 42,500 Y / 70,000 J / 100,000 F
- ≤8,000 mi: 55,000 Y / 80,000 J / 120,000 F
- >8,000 mi: 70,000 Y / 90,000 J / 130,000 F

**North America ↔ Pacific:**
- ≤6,000 mi: 32,500 Y / 65,000 J / 90,000 F
- ≤8,000 mi: 45,000 Y / 80,000 J / 110,000 F
- ≤10,000 mi: 50,000 Y / 95,000 J / 130,000 F
- >10,000 mi: 70,000 Y / 110,000 J / 150,000 F

Online bookable at aircanada.com. Best for short-haul NA: 6k Y starting under 500mi.

### Iberia Plus Avios (Club Iberia Plus) — `iberia.com/us/iberiaplus/purchase-flights-avios/`

**Distance-based on TOTAL TRIP miles** (not per-segment). Two charts: Iberia metal vs partner unified.

**Iberia Metal Off-Peak:**
| Max mi | Y      | W      | J      |
|--------|--------|--------|--------|
| 650    | 3,500  | -      | 9,750  |
| 1,150  | 7,000  | -      | 16,500 |
| 2,000  | 11,000 | -      | 23,250 |
| 4,000  | 18,000 | 35,000 | 51,750 |
| 7,000  | 27,000 | 51,000 | 84,750 |
| >7,000 | 41,000 | 71,000 | 97,000 |

**Partner Unified (oneworld + non-alliance):**
| Max mi  | Y       | W       | J       | F       |
|---------|---------|---------|---------|---------|
| 650     | 6,000   | 9,000   | 12,500  | 24,000  |
| 1,150   | 9,000   | 13,500  | 18,000  | 36,000  |
| 4,000   | 22,500  | 33,750  | 45,000  | 90,000  |
| 7,000   | 41,000  | 61,500  | 82,000  | 164,000 |
| 11,770  | 51,500  | 77,250  | 103,000 | 206,000 |

**Sweet spots:**
- US East Coast → MAD off-peak J: **40,500 Avios** + ~$100
- BCN ↔ MAD air bridge year-round: **9,000 Avios round-trip** economy
- AA Flagship First SFO/LAX-JFK: **103,000 Avios** + $20 RT

**Transfers from:** Amex MR (1:1), Chase UR (1:1), Bilt (1:1), Wells Fargo (1:1), Citi TYP (1:0.7, no fee).
**Avios pool combines with:** BA, Aer Lingus, Finnair, Qatar.
**Caveat:** Partner awards are **non-refundable**. Iberia metal awards have a EUR 25 change fee but are refundable.

### Aeromexico Club Premier RTW (LIKELY)

| Cabin    | Kilometers (NOT miles) |
|----------|------------------------|
| Economy  | 244,000                |
| Business | 352,000                |

Phone only (US: 800-237-6639). Difficult agents. Amex MR transfers 1:1.6. The only RTW survivor for SkyTeam-aligned travelers since SkyTeam Go Round was killed. Avoid unless SkyTeam alignment is required.

## Discontinued Products (reference)

The agent should NOT recommend any of these. They're preserved so stale blog posts about them don't get accepted.

- **ANA Star Alliance RTW** — discontinued 2025-06-23. Use Star Alliance RTW via United, Aeroplan, or Lufthansa M&M.
- **Singapore KrisFlyer Star Alliance RTW** — discontinued 2024-05-01.
- **Singapore KrisFlyer Pacific Circle** — likely discontinued ~2024-05-01.
- **SkyTeam Go Round** — retired 2024-2025.

## Distance Calculation

Use `scripts/calc_distance.py` to estimate great-circle distances:

```bash
# Single segment
python3 scripts/calc_distance.py SFO LAX

# Multi-segment cumulative (RTW or Circle Pacific)
python3 scripts/calc_distance.py JFK LHR FRA NRT HKG SYD LAX JFK --json
```

The helper handles 6,072 IATA airport codes (OpenFlights data) and computes haversine distances.

**Caveats:**
- **TPM vs great-circle:** JAL, Star Alliance, oneworld use IATA TPM (Ticketed Point Mileage). Aeroplan uses actual flown distance. TPM can differ from gcmap.com great-circle by a few percent and affects which distance band you fall into. Use calc_distance.py for an estimate, but verify with the airline before committing.
- **gcmap.com** (kgmap.com great-circle map service) is the authoritative external check.
- **MileCalc.com** offers TPM lookups but is client-side JS-rendered and not scrapable. Bookmark for manual checks.

## Key Decision Rules

(also encoded in `data/rtw-awards.json` `decision_rules`)

1. **Cheap business class RTW:** Star Alliance RTW Special Business at 26,000 mi → ~$7,000-7,400 USD for 5-stop J. Often the best $/business-class-seat in the market.

2. **For pure around-the-world goals:** Star Alliance RTW (most flexible, online bookable) or oneworld Explorer (continent-based, online via rtw.oneworld.com).

3. **For miles-only RTW:** Lufthansa M&M (fixed 400k J / 540k F) is most accessible. Qantas (35k mi cap, 318k for J) is cheaper for shorter band trips.

4. **For Pacific-Rim multi-stop:** Star Alliance Circle Pacific OR oneworld Circle Pacific (travel agent only) OR JAL multi-carrier (cheapest at 25k Y / 48k J under 4,000mi).

5. **For regional NA:** Aeroplan distance-based (6k Y starting <500mi) or Iberia partner chart for AA short hops (12k Y for under 650mi RT).

6. **For intra-Europe:** Iberia Plus on Iberia metal off-peak (3,500 Avios under 650mi). Cheapest intra-EU after BA Avios.

7. **Avoid:** Aeromexico Premier (kilometers, phone only, painful agents); Iberia partner awards (non-refundable, hassle); SkyTeam (no RTW product anymore).

8. **Stopover definition:** 24+ hour layover per most programs. Shorter is a connection.

9. **Purchase deadline:** Star Alliance RTW requires purchase ≥72 hours before first departure. oneworld Explorer similar. Plan ahead.

10. **Child pricing:** Star Alliance RTW: 75% for ages 2-11, 10% for infants without seat. Other programs vary.

## Cross-References

- **stopovers** skill: per-program stopover rules, including programs that DON'T allow stopovers (BA, AA, Delta, JetBlue, Iberia partner-style).
- **partner-awards** skill: who can ticket whom across alliances and bilateral partnerships.
- **alliances** skill: alliance membership and recent shifts.
- **transfer-partners** skill: which credit card points reach which RTW programs.
- **transfer-bonuses** skill: current promotional bonuses to apply when transferring to an RTW program. RTW awards take large transfers, so a 30% bonus saves real points.
- **points-valuations** skill: CPP rules to evaluate whether an RTW makes sense.
- **booking-guidance** skill: hold-before-transfer rules and phone-booking phone numbers.
- **award-holds** skill: per-program hold rules. Most RTW programs (Aeroplan, ANA discontinued, Lufthansa M&M) require phone booking and the hold-before-transfer pattern, but some (Star Alliance through Aeroplan, oneworld through AA) won't hold a multi-segment award. Critical to know before transferring large balances.

## Source Hierarchy

When sources disagree, use this priority:
1. **Airline's own award rules / chart PDF** (primary source)
2. **Frequent Miler** (most respected secondary; dives deep into devaluations)
3. **One Mile at a Time** (good for sweet spots and recent changes)
4. **Upgraded Points** (mainstream summary)
5. **The Points Guy** (often stale on charts; use for valuation only)

If primary is unavailable and secondaries disagree, mark the entry `confidence: LIKELY` and note the discrepancy in `notes`.

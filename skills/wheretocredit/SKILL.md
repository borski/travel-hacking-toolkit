---
name: wheretocredit
description: Look up frequent flyer mileage earning rates by airline and booking class via wheretocredit.com. Shows both redeemable miles and qualifying/status miles across 50+ loyalty programs. Use when crediting flights, comparing programs, or deciding where to credit a ticket.
category: loyalty
summary: Mileage earning rates by airline and booking class across 50+ programs.
api_key: None (free)
license: MIT
---

# Where to Credit

Look up mileage earning rates for any airline and booking class across 50+ frequent flyer programs. Covers both **redeemable miles** (the ones you spend) and **qualifying miles** (the ones that count toward elite status).

**Source:** [wheretocredit.com](https://www.wheretocredit.com) — No API key required. Data is scraped via webfetch.

## URL Patterns

All data lives at predictable URLs on wheretocredit.com:

### Airline booking class detail (PRIMARY)
```
https://www.wheretocredit.com/en/{IATA_CODE}/{BOOKING_CLASS}
```
Returns: cabin type, fare types, redeemable miles table, qualifying miles table.

Example: `https://www.wheretocredit.com/en/AY/Z` (Finnair class Z)

### Airline overview (all classes)
```
https://www.wheretocredit.com/en/{IATA_CODE}
```
Returns: list of all booking classes with cabin, fare types, and top earning program for each.

Example: `https://www.wheretocredit.com/en/AY` (all Finnair classes)

### Program overview (all partner airlines)
```
https://www.wheretocredit.com/en/programs/{PROGRAM_CODE}
```
Returns: list of all airlines that credit to this program.

Example: `https://www.wheretocredit.com/en/programs/AA` (AA AAdvantage partners)

## Common IATA Codes

| Code | Airline |
|------|---------|
| AA | American Airlines |
| AS | Alaska Airlines |
| AF | Air France |
| AY | Finnair |
| BA | British Airways |
| CX | Cathay Pacific |
| DL | Delta |
| EK | Emirates |
| IB | Iberia |
| JL | Japan Airlines |
| KL | KLM |
| LH | Lufthansa |
| NH | ANA |
| QF | Qantas |
| QR | Qatar Airways |
| SK | SAS |
| SQ | Singapore Airlines |
| TK | Turkish Airlines |
| UA | United Airlines |
| VS | Virgin Atlantic |

## Common Program Codes

| Code | Program |
|------|---------|
| AA | American Airlines AAdvantage |
| AS2 | Alaska/Hawaiian Atmos Rewards |
| AFB | Flying Blue (Air France/KLM) |
| BA2 | British Airways Club |
| CX | Cathay Marco Polo / Asia Miles |
| DL2 | Delta SkyMiles |
| IB2 | Iberia Plus |
| JL | Japan Airlines Mileage Bank |
| LH | Miles & More |
| QR | Qatar Privilege Club |
| SK | SAS EuroBonus |
| SQ | Singapore KrisFlyer |
| UA | United MileagePlus |
| VS | Virgin Atlantic Flying Club |

## Reading the Results

### Redeemable Miles Table
Shows the percentage of flown distance you earn as spendable miles.

| Column | Meaning |
|--------|---------|
| Base | Earning rate with no elite status |
| Tier 1 | First elite tier bonus |
| Tier 2 | Second elite tier bonus |
| Tier 3 | Third elite tier bonus |
| Tier 4 | Highest elite tier bonus |
| Minimum | Floor (e.g., "500 Miles" means you earn at least 500 regardless of distance) |
| Restriction | Limitations (e.g., "Countries Excluded: CU" = no earning on Cuba routes) |

### Qualifying Miles Table
Shows the percentage of flown distance that counts toward elite status.

Same column structure. Often different rates from redeemable. Some programs earn 0% qualifying on discounted fares even when they earn redeemable miles.

**Key distinction:** A flight can earn redeemable miles but zero qualifying miles. Always check BOTH tables.

### Tier Levels by Program

Programs use different names for their tiers. Map your status to the right tier column:

| Program | Base | Tier 1 | Tier 2 | Tier 3 | Tier 4 |
|---------|------|--------|--------|--------|--------|
| AA AAdvantage | Base | Gold | Platinum | Platinum Pro | Executive Platinum |
| Alaska Atmos | Base | MVP | MVP Gold | MVP Gold 75K | MVP Gold 100K |
| Delta SkyMiles | Base | Silver | Gold | Platinum | Diamond |
| United MileagePlus | Base | Silver | Gold | Platinum | 1K |
| Flying Blue | Base | Silver | Gold | Platinum | Ultimate |
| BA Executive Club | Base | Bronze | Silver | Gold | Gold Guest List |

## Traveler Profiles

Before using the decision algorithm, define each traveler's profile. You need:
- Which FF programs they have accounts in
- Their elite status tier in each program
- Which program is their "primary" (the one they're actively building status in)

Example profile:
```
Traveler: Alex
Programs: AA AAdvantage (Platinum, Tier 2), Alaska Atmos (Base), Flying Blue (Silver, Tier 1)
Primary: AA AAdvantage (retaining Platinum status)
```

**Only recommend programs someone has an account in.** Don't suggest crediting to Etihad Guest if nobody has one, unless the earning is dramatically better AND the program is useful for future redemptions.

## Decision Algorithm

When a flight is booked, run this logic to determine where to credit:

### Step 1: Gather inputs
- Operating airline IATA code (from ticket, NOT ticketing airline)
- Booking class letter (from ticket or fare details)
- Route distance in miles (estimate or look up)
- Which traveler(s) are on the ticket

### Step 2: Fetch earning rates
- Fetch `https://www.wheretocredit.com/en/{IATA}/{CLASS}`
- Extract redeemable AND qualifying rates for all of that traveler's programs

### Step 3: Calculate actual miles earned
For each reachable program, for each traveler:
```
raw_miles = route_distance × (base_rate + tier_bonus) / 100
actual_miles = max(raw_miles, minimum_floor)
```

If a program uses fare-price earning (e.g., "6 Miles/EUR"), calculate based on ticket price instead of distance.

### Step 4: Apply decision rules

**Rule 1: Short-haul floor advantage.** On flights under ~1,500 miles, programs with a 500+ mile minimum floor (like Alaska) can earn MORE than programs offering a percentage of distance. Calculate both and compare. At Base tier, Alaska's 500 floor beats 25% earning on any flight under 2,000 miles. At higher tiers with bonus percentages, the crossover point drops.

**Rule 2: Qualifying miles matter for status chasers.** If a traveler is actively building or retaining elite status, qualifying miles matter. If a flight earns qualifying miles on their primary program but not on the higher-earning alternative, flag the tradeoff.

**Rule 3: Highest redeemable wins (all else equal).** If qualifying miles are a wash or irrelevant, credit to whichever program earns the most spendable miles.

**Rule 4: Don't split for tiny differences.** If two programs are within 50 miles of each other, default to the traveler's primary program for simplicity.

### Step 5: Output the recommendation

Format:
```
✈️ {AIRLINE} {FLIGHT} ({CLASS}) · {ORIGIN}→{DEST} · ~{DISTANCE} mi

{Traveler} → Credit to {PROGRAM}: {MILES} redeemable miles ({QUALIFYING} qualifying)
  Why: {one sentence reason}
```

### Worked example (Finnair AY806, class Z, BGO→ARN, ~770 mi)

Traveler A: AA Platinum (Tier 2), Alaska Base
Traveler B: Alaska Base only

```
✈️ Finnair AY806 (Z) · BGO→ARN · ~770 mi

Traveler A → Credit to AA AAdvantage: ~308 redeemable (770 × 40%), ~193 qualifying (770 × 25%)
  Why: Tier 2 bonus pushes AA past Alaska's 500 floor. Qualifying miles help retain status.

Traveler B → Credit to Alaska Atmos: 500 redeemable (floor), 0 qualifying
  Why: 500 mile floor beats 25% of 770 (= 193). Only program available.
```

## Reference Workflows

### "What does class X earn on airline Y?"

1. Fetch `https://www.wheretocredit.com/en/{IATA}/{CLASS}`
2. Read both redeemable and qualifying tables
3. Note cabin type and fare types listed at the top

### "Which airlines credit to program X?"

1. Fetch `https://www.wheretocredit.com/en/programs/{CODE}`
2. Lists all partner airlines with links to their booking class charts

## Fare Type Mapping

Booking classes map to fare brands, but **every airline names them differently**. The wheretocredit page header shows which fare types apply for that airline.

Common patterns (names vary by carrier):
- **Full flex / Refundable** = fully flexible, changeable, refundable
- **Standard / Classic** = some flexibility, partial refund
- **Basic / Light / Saver** = restricted, limited changes
- **Ultra-basic / Superlight** = cheapest, most restrictions, often no checked bag

Examples: Finnair uses Superlight/Classic/Flex. SAS uses SAS Go Light/Go/Plus/Business. Norwegian uses LowFare/LowFare+/Flex. United uses Basic Economy/Economy/Economy Flex. Always check the specific airline's fare page for exact names.

The same booking class letter can map to different fare types on different airlines.

## Important Notes

- The calculator page requires JavaScript and won't work via webfetch
- Data is maintained by Travel-Dealz.com (took over from original WTC team)
- Some programs earn based on fare price (e.g., Finnair Plus: "6 Miles/EUR") rather than distance percentage
- Always check the "Restriction" column for country exclusions or other limitations
- Earning rates change. When in doubt, verify against the airline's own partner earning page

## When to Use

Load this skill when:
- Booking a flight and deciding which FF program to credit it to
- Comparing earning rates across programs for a specific airline/class
- Checking if a discounted fare earns qualifying miles
- Need to know tier bonus rates for elite status holders
- Any "where to credit" or "how many miles will I earn" question

Do not:
- Assume the calculator works via webfetch (it needs JS)
- Confuse redeemable miles with qualifying miles. Always specify which.
- Forget that operating carrier matters, not ticketing carrier

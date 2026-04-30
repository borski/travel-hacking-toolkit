---
name: trip-calculator
description: Compare the total cost of a trip using cash vs points. Factors in transfer ratios, taxes, fees, point valuations, and opportunity cost to recommend the best redemption strategy.
category: orchestration
summary: Cash vs points decision answered with math. Transfer ratios, taxes, opportunity cost.
api_key: None (free, local data)
---

# Trip Cost Calculator

"Should I pay cash or use points?" answered with math.

Compares the true cost of booking with cash versus each available points currency, accounting for transfer ratios, taxes/fees, and the opportunity cost of burning your points.

**No API key needed.** Uses local JSON data files plus flight/hotel search results.

## Data Files

| File | Purpose |
|------|---------|
| `data/points-valuations.json` | CPP valuations per program (floor/ceiling) |
| `data/transfer-partners.json` | Credit card → loyalty program transfer ratios |

## When to Use

- User has both cash prices (from Duffel/Ignav/Google Flights) and award prices (from seats.aero)
- User asks "should I pay cash or use points?"
- User wants to know the CPP of a specific redemption
- User is deciding between multiple booking strategies for a trip

## Core Concepts

### Cents Per Point (CPP)

The value you're getting per point when redeeming:

```
cpp = (cash_price - taxes_on_award) / points_needed × 100
```

A CPP **above** the floor valuation from `points-valuations.json` means you're getting above-average value. Below floor = poor redemption.

### Opportunity Cost

Points have value even when unspent. Burning 100K Chase UR at 1.7 cpp (floor) means you're "spending" $1,700 in future travel flexibility:

```
opportunity_cost = points_needed × floor_cpp / 100
```

If the cash price is lower than the opportunity cost, pay cash. If higher, use points.

### The Decision Framework

```
IF cash_price < opportunity_cost → PAY CASH (points are worth more saved)
IF cash_price > opportunity_cost → USE POINTS (good redemption)
IF cash_price ≈ opportunity_cost → PAY CASH (preserve flexibility)
```

The tie goes to cash because points maintain optionality.

## Workflow

### Step 1: Gather Prices

**Cash prices** (use one or more sources):
```
Duffel API → exact bookable fares
Ignav API → fast comparison prices
Google Flights → browser-based, includes Southwest
```

**Award prices** (use seats.aero):
```
Seats.aero API → cached availability across 25+ programs
Seats.aero web → live search (local Patchright only)
```

### Step 2: Calculate CPP for Each Award Option

For each award option with a corresponding cash price:

```
cpp = (cash_price_usd - award_taxes_usd) / award_miles × 100
```

Award taxes come from seats.aero trip details (`TotalTaxes` field, in cents) or estimate $5.60 per segment for domestic US, $50-$200 for international (varies wildly by carrier and routing).

### Step 3: Factor in Transfer Ratios

If using transferable points (Chase UR, Amex MR, etc.), the effective points cost changes:

```
effective_points = award_miles / transfer_ratio
effective_cpp = (cash_price - award_taxes) / effective_points × 100
```

Example: Flying Blue award at 50,000 miles via Capital One (1:1):
- Effective points: 50,000
- Cash price: $1,200, taxes: $100
- CPP: ($1,200 - $100) / 50,000 × 100 = **2.2 cpp**

Contrast: a separate Emirates award at 72,500 Skywards miles via Capital One (4:3 ratio, the worst Cap One transfer rate):
- Effective points needed: 72,500 / 0.75 = 96,667 Cap One miles
- Same $1,200 cash equivalent: ($1,200 - $100) / 96,667 × 100 = **1.14 cpp**. Worse than the Flying Blue path.

**Important: pick the best currency for the destination program.** Emirates Skywards has a 1:1 transfer from Bilt Rewards (no fee, instant). For the same Emirates redemption, 72,500 Bilt = 72,500 Skywards = ($1,200 - $100) / 72,500 × 100 = **1.52 cpp**. Always check `data/transfer-partners.json` for every transferable currency the user holds before recommending a transfer — Bilt's 1:1 to Emirates beats Capital One's 4:3 by a wide margin. The skill enforces this in Step 0 (load `transfer-partners` first to enumerate every viable path).

### Step 4: Compare Against Valuations

Load valuations from `points-valuations.json`:

```bash
jq -r '.credit_card_points.chase_ultimate_rewards | "Chase UR: floor \(.floor)cpp, ceiling \(.ceiling)cpp"' data/points-valuations.json
```

| Rating | CPP vs Floor | Meaning |
|--------|-------------|---------|
| Excellent | > ceiling | Exceptional redemption. Book it. |
| Good | > floor | Above average. Solid use of points. |
| Fair | 0.8× to 1× floor | Mediocre. Consider cash instead. |
| Poor | < 0.8× floor | Bad deal. Pay cash. |

### Step 5: Present Comparison

**Always use markdown tables.**

#### Flight: SFO → NRT Business Class, Aug 15

| Option | Program | Miles/Points | Taxes | Cash Equiv | CPP | Rating |
|--------|---------|-------------|-------|------------|-----|--------|
| Cash | — | — | — | $4,200 | — | — |
| United via Chase UR | United | 88,000 UR | $45 | $1,496 | 4.72 | Excellent |
| Aeroplan via Chase UR | Aeroplan | 75,000 UR | $120 | $1,275 | 5.44 | Excellent |
| Alaska via Bilt | Alaska | 55,000 Bilt | $30 | $935 | 7.58 | Excellent |
| Virgin Atlantic → ANA via Chase UR | VA | 52,500 UR | $200 | $893 | 7.62 | Excellent |

**Recommendation:**
- **Best value:** Virgin Atlantic at 7.62 cpp, but $200 in taxes and must call to book.
- **Best convenience:** Aeroplan at 5.44 cpp, bookable online, low taxes.
- **Cash price ($4,200) vs opportunity cost ($893-$1,496):** Points win decisively. Use points.

### Step 6: Round-Trip and Multi-Segment

For round trips, calculate each direction separately. Award pricing is usually one-way, cash pricing is often round-trip. Make sure you're comparing apples to apples:

```
If cash = round-trip $4,200:
  Compare against: outbound award + return award
  e.g., 75K out + 75K return = 150K total vs $4,200 cash
  CPP = ($4,200 - $240 taxes) / 150,000 = 2.64 cpp
```

## jq Recipes

### Get floor valuation for a currency

```bash
jq -r '.credit_card_points.chase_ultimate_rewards.floor' data/points-valuations.json
```

### Calculate opportunity cost

```bash
# 75,000 Chase UR points
POINTS=75000
FLOOR=$(jq -r '.credit_card_points.chase_ultimate_rewards.floor' data/points-valuations.json)
echo "$POINTS points × $FLOOR cpp = \$$(echo "$POINTS * $FLOOR / 100" | bc) opportunity cost"
```

### Full comparison for one route

```bash
# Cash: $4200 round trip. Award: 75000 Aeroplan each way, $120 taxes each way.
CASH=4200
MILES_ONEWAY=75000
TAXES_ONEWAY=120
TOTAL_MILES=$((MILES_ONEWAY * 2))
TOTAL_TAXES=$((TAXES_ONEWAY * 2))

echo "Cash: \$$CASH"
echo "Award: $TOTAL_MILES miles + \$$TOTAL_TAXES taxes"
echo "CPP: $(echo "scale=2; ($CASH - $TOTAL_TAXES) / $TOTAL_MILES * 100" | bc)"

# Opportunity cost at floor valuation
FLOOR=$(jq -r '.credit_card_points.chase_ultimate_rewards.floor' data/points-valuations.json)
echo "Opportunity cost: \$$(echo "scale=0; $TOTAL_MILES * $FLOOR / 100" | bc)"
```

## Hotel Comparison

The same framework works for hotels:

```
hotel_cpp = (cash_rate_per_night × nights) / total_points × 100
```

Hotel redemptions vary more than flights. Use `points-valuations.json` hotel section:
- Hyatt: floor 1.4 cpp (consistently best hotel currency)
- Hilton: floor 0.4 cpp (high point costs, low per-point value)
- Marriott: floor 0.6 cpp

For premium hotel programs (FHR, THC, Chase Edit), factor in the additional benefits (breakfast, upgrade, credit, late checkout) when comparing cash vs points. A $500/night FHR rate with $100 breakfast credit and potential suite upgrade might be worth more than the sticker price.

## Chase Travel Portal vs Transfer

Chase Sapphire Reserve uses dynamic Points Boost pricing in the Chase travel portal: roughly 1.5-2.0 cpp on select bookings, but **not a guaranteed floor on every booking**. The historical 1.5 cpp fixed multiplier is gone — current redemptions vary by route, date, and inventory. Always check the actual portal price before assuming a rate.

Rough decision rule, with the caveat that you must verify the actual portal quote:

```
If actual portal CPP > award CPP → portal wins
If award CPP > actual portal CPP → transfer to partner wins
```

Sapphire Preferred is similar (1.5-1.75 cpp typical via Points Boost). Amex portal is ~1.0 cpp for flights (1 cent per MR point). Capital One portal is ~0.75-1.0 cpp.

**Always pull the real portal quote** via the `chase-travel` or `amex-travel` skills before making a points-vs-portal recommendation. Don't assume the headline rate applies to your specific booking.

## Common Pitfalls

- **Ignoring taxes/fees on awards.** Some airlines (especially BA, Lufthansa, Singapore on own metal) add $500+ in fuel surcharges to award tickets. Always subtract taxes before calculating CPP.
- **Comparing one-way award to round-trip cash.** Make sure denominators match.
- **Forgetting transfer ratios.** 50K miles via Amex → Emirates at 5:4 costs 62,500 MR, not 50,000.
- **Not checking portal pricing.** Sometimes Chase/Amex portal pricing beats the transfer math.
- **Over-optimizing small differences.** If two options are within 0.5 cpp of each other, pick the one with better routing, lower taxes, or more flexibility.

## Notes

- Point valuations are subjective. The floor from `points-valuations.json` is the most defensible number.
- "Opportunity cost" assumes you WILL use those points eventually at floor value. If you're sitting on a huge balance with no plans, the real opportunity cost is lower.
- Currency devaluation risk matters for long-term holdings. Points are depreciating assets.
- Transfer bonuses can shift the math significantly. A 30% bonus on Chase → Flying Blue means 75K UR becomes 97.5K Flying Blue miles.

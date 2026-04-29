---
name: points-valuations
description: Reference for cents-per-point (cpp) valuations across all major loyalty programs, sourced from four publications with different bias profiles. Provides floor/ceiling rules for deciding when a redemption is good, mediocre, or exceptional. Load when computing cpp on award redemptions, deciding whether to burn points or pay cash, comparing portal rates against transfer-based bookings, or whenever the question "is this a good redemption?" comes up. Triggers on "cpp", "cents per point", "is this a good redemption", "points valuation", "floor cpp", "ceiling cpp", "TPG value", "OMAAT value", "View From The Wing", or any decision involving the relative value of points.
---

# Points Valuations

**Reference data:** `data/points-valuations.json`

Four sources are aggregated:
- **The Points Guy (TPG):** optimistic, has affiliate incentive to inflate
- **Upgraded Points:** moderate
- **One Mile at a Time (OMAAT):** conservative
- **View From The Wing (VFTW):** most conservative and theoretically rigorous

Each entry has:
- `floor` — conservative minimum (use this for decision-making)
- `ceiling` — optimistic maximum
- `sources` — individual values from each publication

## Decision Rules

- **Default to the floor for "should I burn points on this?" decisions.** If a redemption beats the ceiling, it's genuinely exceptional. Say so.
- **Below the floor is objectively poor value.** Flag it and suggest alternatives.
- **TPG systematically overvalues** (affiliate incentive). VFTW and OMAAT are more useful for real decisions.
- **When floor and ceiling are within 0.1cpp,** the value is well-established.
- **When floor and ceiling are 0.3cpp+ apart,** mention the range and let the user decide.

## Staleness Check

Look at `_meta.last_updated` in the data file. If it's more than 45 days old, re-fetch from the source URLs in `_meta.sources` and update the file. Programs devalue regularly, and stale valuations lead to bad recommendations.

## How to Compute CPP Correctly

```
CPP = (cash_price - taxes_and_fees_you_still_pay) * 100 / miles_required
```

This is the TOTAL out-of-pocket cost calculation, not just gross fare. Many award tickets still charge taxes, fuel surcharges, and carrier-imposed fees. These can be $5 on United or $800+ on British Airways. The cpp must reflect what you actually save.

## Surcharge-Heavy Programs (Watch Out)

Some programs pass through massive fuel surcharges on award tickets. The worst offenders:
- British Airways (especially on BA metal)
- Lufthansa
- SWISS
- Austrian
- Other European flag carriers

## Surcharge-Light Programs (Use These)

- United (on United metal)
- ANA
- Singapore (on own metal)
- Air Canada Aeroplan (on most partners)

A 50K mile award with $600 in surcharges is NOT the same value as 50K with $5.60 in taxes. Always flag the expected surcharge level when recommending an award.

## Transfer Bonuses Change Everything

Programs frequently run 20-50% transfer bonuses (e.g., "transfer Amex MR to Virgin Atlantic and get 30% bonus miles"). These are time-limited and change the optimal play entirely.

Search the web for "current transfer bonuses" or check https://thepointsguy.com/loyalty-programs/current-transfer-bonuses/ before making a final recommendation. A 30% bonus on a transfer can turn a mediocre redemption into an exceptional one.

## Portal Rates Are Dynamic

Chase Points Boost (launched June 2025) replaced fixed redemption rates with dynamic offers of 1.5 to 2.0cpp (Reserve) or 1.5 to 1.75cpp (Preferred). Not every booking qualifies. The only way to know the real portal rate is to check the portal.

For rough estimates:
- Chase: 1.5cpp default
- Amex/Capital One: 1.0cpp default

Always mention that the user should verify the portal price.

## Transfer Partners Often Beat the Portal

This is the whole game. If 60K miles via transfer gets you a flight that would cost 90K via the portal, that's the play. Make this comparison explicit.

## Opportunity Cost

Burning Chase UR on a 1.2cpp portal redemption is wasteful when you could transfer to Hyatt at 2.0cpp for hotels. Mention when points have better uses elsewhere.

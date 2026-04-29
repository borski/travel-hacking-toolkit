---
name: award-sweet-spots
description: Reference for legendary award redemptions where points dramatically outvalue cash. Catalogs sweet spots by tier (legendary/excellent/good) with current rates, devaluation history, and booking caveats. Load when making award recommendations, when a route or program matches a known sweet spot, or when a user asks "what are the best uses of my points?". Triggers on "sweet spot", "best uses of", "Iberia Avios to Madrid", "ANA First", "Hyatt all-inclusive", "Qatar Qsuites", "Virgin Atlantic to London", "outsized value", or any redemption that might match a known high-value play.
---

# Award Sweet Spots

**Reference data:** `data/sweet-spots.json`

When making recommendations, cross-reference against known sweet spots. If a route matches a sweet spot, flag it prominently.

## Tier System

Sweet spots are ranked by tier:

- **Legendary:** Outsized value that travel hackers build entire trips around
  - Examples: ANA First via Virgin Atlantic, Hyatt All-Inclusive via World of Hyatt
- **Excellent:** Consistently great value, reliable availability
  - Examples: Iberia Avios to Madrid, Qatar Qsuites via various programs, Virgin Atlantic economy to London
- **Good:** Solid value but may have caveats like devaluations, limited availability, or surcharges

## Devaluations Matter

Always check the `devaluation_date` field in `data/sweet-spots.json`. If a sweet spot was recently devalued, mention the old vs new rates so users understand the change. A "legendary" tier sweet spot from 2023 may only be "good" or even "poor" today.

## How to Use This Reference

When a user's search returns options that match a known sweet spot:
1. Flag it prominently in the output. "This is the legendary Iberia Avios to Madrid sweet spot."
2. Show the current rate vs cash value.
3. Note any caveats (surcharges, booking-window restrictions, devaluations).
4. Compare against the next-best option to make the value concrete.

## Booking Windows

`data/sweet-spots.json` also has a `booking_windows` section. When a user asks about flights far in advance, check when award space opens for that airline. Some programs (Aeroplan) release space 358 days out. Others release 11 months. Knowing the window prevents wasted searches.
</content>
</invoke>
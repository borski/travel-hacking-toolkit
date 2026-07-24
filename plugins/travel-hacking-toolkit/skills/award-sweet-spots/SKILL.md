---
name: award-sweet-spots
description: Catalog of high-value award redemptions where points dramatically outvalue cash. Tiered by legendary/excellent/good with current rates, devaluation history, and booking caveats. Includes Oceania and South Pacific plays (Australia, New Zealand, Tahiti, Fiji) and transatlantic business-class sweet spots.
category: reference
summary: Catalog of legendary, excellent, and good award redemptions with current rates and devaluation history.
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

## Oceania / South Pacific Sweet Spots

Getting to Australia, New Zealand, and the South Pacific on points is hard — demand is high, distances are long, and premium cabin space is scarce. Proven plays, ranked:

1. **Air New Zealand business via Virgin Atlantic** (Excellent) — 62.5K one-way from the US, 45K from Hawaii. The same flights United sells for 110K. Availability is the bottleneck: rare in advance, opens inside 30 days. Phone booking only. Reachable from Amex, Chase, Citi, Bilt, Wells Fargo, and Capital One (via Virgin Red).
2. **ANA Mileage Club business to Oceania** (Excellent) — roughly 68.5K+ one-way on ANA metal (seasonal, under the June 2025 chart; one-ways now bookable) with wide routing via Japan or direct on Air NZ. No fuel surcharges on United, Air Canada, or Air NZ. Limitation: reachable only from Amex MR (plus Marriott at a poor ratio). Verify current rates on ana.co.jp — avoid its still-hosted pre-June-2025 legacy chart pages.
3. **Aeroplan business to Oceania** (Good) — 75-115K one-way, but the killer feature is adding an **Asia stopover for +5K miles**, turning Australia into Asia + Australia. No fuel surcharges. Reachable from Amex, Chase, Capital One, Bilt.
4. **Air France LAX-Tahiti nonstop** (Good) — ~30K economy one-way on one of the few US-Tahiti nonstops. Business (~113K) is usually poor value; economy is the play. Watch for Flying Blue transfer bonuses.
5. **Atmos/Alaska to the South Pacific** (Good) — HNL-Kiritimati on Fiji Airways in the lowest distance band is a perennial steal, and HNL-Tahiti/Rarotonga on Hawaiian is cheap. Free stopover, no change/cancel fees. Reachable only from Bilt (plus Marriott).
6. **United MileagePlus business** (Good) — 85-100K on United metal, ~110K on partners. The most lenient routing rules, but partner space is almost always cheaper via Virgin Atlantic (62.5K) or ANA.

Oceania-specific warnings:

- **Availability is the real constraint** — points prices matter less if there are no seats. Search early and often for premium cabins.
- **Peak season is Dec-Feb** (Southern Hemisphere summer); award space is hardest then.
- **Air NZ via Virgin Atlantic** is the best value but hardest to find — realistic only inside ~30 days.
- **Surcharge traps:** BA Avios on Qantas metal carries heavy surcharges. Stick to each entry's no-surcharge carriers.

## Booking Windows

`data/sweet-spots.json` also has a `booking_windows` section. When a user asks about flights far in advance, check when award space opens for that airline. Some programs (Aeroplan) release space 358 days out. Others release 11 months. Knowing the window prevents wasted searches.

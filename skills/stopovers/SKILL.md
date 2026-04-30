---
name: stopovers
description: Per-program stopover rules for award redemptions. Critical for multi-city trip planning, getting two destinations for the price of one, and identifying which loyalty programs let you do this well. Includes the legendary Icelandair stopover (free 7-day stop in Reykjavik on every transatlantic itinerary), Aeroplan, Alaska Atmos, Flying Blue, Singapore KrisFlyer, Cathay Asia Miles, JAL, and the negative space (programs like BA, AA, Delta where stopovers don't exist). Each program has primary-source citations. Use when a user asks about stopovers, free stopovers, multi-city awards, two cities for the price of one, or which program allows X stopover. Triggers on stopover, stopover allowance, free stopover, stopover rules, multi-city award, two destinations one award, Iceland stopover, Reykjavik stopover, Aeroplan stopover, Alaska Mileage Plan stopover, Flying Blue free stopover, Singapore stopover, Excursionist Perk, ana stopover.
category: reference
summary: Per-program stopover rules for award redemptions. Includes Icelandair free stopover, Aeroplan, Alaska Atmos, Flying Blue, Singapore tiers, plus the negative space (BA, AA, Delta, JetBlue) that have no stopover programs.
allowed-tools: Bash(jq *), Read
---

# Stopover Rules per Loyalty Program

Reference data for which programs allow stopovers on award redemptions, how many, where, for how long, and at what cost. Sourced primarily from each airline's own award rules pages, cross-checked against Frequent Miler, OMAAT, Travel Miles 101, Prince of Travel, and Upgraded Points.

Data lives in [`data/stopovers.json`](../../data/stopovers.json). Refresh cadence is 90 days because stopover rules change rarely (much less often than transfer bonuses or program valuations).

## What Is a Stopover?

A planned interruption of a journey at a point between origin and destination. The IATA standard definition is:

- **More than 24 hours** for international itineraries
- **More than 4 hours** for domestic itineraries (US/Canada)

Each loyalty program defines its own rules within or beyond this baseline. Some programs let you stop for a week. Some let you stop for 365 days. Some don't allow stopovers at all.

The headline value: a free stopover lets you visit two destinations on a single award. Iceland on the way to Europe. Tokyo on the way to Bangkok. Singapore on the way to Sydney.

## When to Use This Skill

- User wants to plan a multi-city trip and asks "what's the best program for stopovers?"
- User asks about a specific program's stopover rule (e.g. "does Aeroplan allow stopovers?")
- Building a trip itinerary that could benefit from a free second destination
- Comparing programs for award redemption when stopover flexibility matters
- Identifying the cheapest "free vacation in Iceland" via Icelandair stopover
- Researching JetBlue + Icelandair partner award routings

## When NOT to Use

- Cash flight stopovers (most cash fares have layover rules but not "free stopover" perks; check the airline's fare conditions instead)
- Booking the actual itinerary (use the program's website or call the booking phone)
- Award holds (use `award-holds` skill — that's a different concept)
- Round-the-world tickets (use `round-the-world` skill — different framework with global routing rules)

## Quick Reference Table

The full data is in `data/stopovers.json`. Headlines:

### Programs That Allow Stopovers (positive)

| Program | Max Round-Trip | Max Days | Cost | Booking | Confidence |
|---------|----------------|----------|------|---------|------------|
| Aeroplan | 2 (1 per direction) | 45 | 5,000 pts | Online | VERIFIED |
| Alaska Atmos Rewards | 2 (1 per one-way) | unspecified | Free | Phone | VERIFIED |
| ANA Mileage Club | 1 | unspecified | Free | Online | LIKELY |
| Avianca LifeMiles | 1 | unspecified | Free | Online | LIKELY |
| Cathay Asia Miles | 2 | unspecified | Free | Online | VERIFIED |
| Copa ConnectMiles | 1 | unspecified | Free | Online | LIKELY |
| Etihad Guest | 1 | unspecified | Free | Phone | LIKELY |
| Flying Blue (AF/KLM) | unlimited | up to 365 | Free | Phone | VERIFIED |
| **Icelandair Saga Club** | **2 (transatlantic)** | **7** | **Free** | **Online** | **VERIFIED** |
| JAL Mileage Bank | 3 (partner only) | unspecified | Free | Phone | VERIFIED |
| Korean SKYPASS | 1 | unspecified | Free | Phone | LIKELY |
| Lufthansa Miles & More | 2 | unspecified | Free | Online | LIKELY |
| Qatar Privilege Club | 1 | unspecified | Free | Phone | UNVERIFIED |
| Singapore KrisFlyer | 1 (Saver) / 2 (Advantage) | 30 | Free | Online | VERIFIED |
| TAP Miles & Go | 1 (partners only) | unspecified | Free | Online | LIKELY |
| Turkish Miles & Smiles | 1 | unspecified | Free | Phone | LIKELY |
| United (Excursionist Perk) | DISCONTINUED Aug 2025 | — | — | — | VERIFIED |

### Programs That Do NOT Allow Stopovers (negative space)

These programs price each segment as its own award. Long layovers up to ~24 hours are still typically permitted but offer no perk.

- **British Airways Avios** — each segment priced separately
- **American Airlines AAdvantage** — long layovers up to 24h only
- **Delta SkyMiles** — long layovers up to 24h only
- **Iberia Plus Avios** — same as BA
- **Virgin Atlantic Flying Club** — no formal stopover program
- **JetBlue TrueBlue** — revenue-based, segment-priced

For full details, restrictions, recent changes, and primary sources for any program, query `data/stopovers.json`.

## The Iceland Callout

Icelandair's stopover program is **the single best free-vacation perk built into a flight ticket in commercial aviation.** Some specifics worth highlighting:

- **Free** at no additional airfare on every transatlantic Icelandair itinerary
- **Up to 7 nights** in Reykjavík (some Saga Premium fares allow longer)
- **Same rules** apply on cash bookings AND on award redemptions through Saga Club
- **70+ year history** — Icelandair has been doing this since their founding
- **Bookable via JetBlue TrueBlue partner award** (added 2024) — so transferable points programs like Bilt, Chase UR transfers etc. can reach this
- **No tricks** — book a transatlantic Icelandair flight, choose your stopover length when booking, done

When recommending stopover-friendly programs to a US-Europe traveler with flexible plans, this should usually be near the top of the list.

Primary source: [icelandair.com/flights/stopover](https://www.icelandair.com/flights/stopover/)

## Reading the Data File

```bash
# All programs that allow stopovers, sorted by max round-trip stopovers
jq '.programs[] | select(.category == "positive") |
    {name, max_rt: .max_stopovers_round_trip, surcharge: .surcharge_points, booking: .booking_method}' \
    data/stopovers.json | head -40

# Find programs that allow free phone-bookable stopovers
jq '.programs[] | select(.category == "positive" and .surcharge_points == 0 and .booking_method == "phone") |
    {name, max_rt: .max_stopovers_round_trip, restrictions: .restrictions}' \
    data/stopovers.json

# Programs that do NOT allow stopovers (negative space)
jq '.programs[] | select(.category == "negative") | {name, restrictions}' data/stopovers.json

# All sources/citations for a given program
jq '.programs[] | select(.id == "aeroplan") | .sources' data/stopovers.json

# Recently changed programs (last 24 months)
jq '.programs[] | select(.recent_changes != null) | {name, recent_changes}' data/stopovers.json

# Discontinued programs (e.g. United Excursionist)
jq '.programs[] | select(.discontinued == true) | {name, discontinued_date, restrictions}' data/stopovers.json
```

## Decision Rules

When a user is planning a trip and stopovers are relevant, follow these:

1. **Free Iceland stopover is the easiest second country for any US-Europe traveler.** It's built into the cash fare AND the award redemption. Mention it whenever the trip includes US/Canada to/from Europe.

2. **Map hub airports to programs.** Match the user's likely connecting hub to a program with stopover rights:
   - Tokyo (NRT/HND) → ANA, JAL, Singapore (transit), Korean partner
   - Hong Kong (HKG) → Cathay
   - Singapore (SIN) → Singapore KrisFlyer
   - Doha (DOH) → Qatar
   - Abu Dhabi (AUH) → Etihad
   - Istanbul (IST) → Turkish
   - Amsterdam (AMS) / Paris (CDG) → Flying Blue
   - Reykjavik (KEF) → Icelandair
   - Seoul (ICN) → Korean
   - Bogotá (BOG) → Avianca
   - Panama City (PTY) → Copa
   - Frankfurt (FRA) / Munich (MUC) → Lufthansa

3. **Alaska Atmos is the most generous Western program for partner stopovers** but requires phone booking. Allow 30+ minutes per call.

4. **Flying Blue allows unlimited stopovers** but requires phone booking. Some agents incorrectly say only AMS/CDG hub stopovers — cite the FAQ at [flyingblue.us/en/spend/flights/rewards](https://www.flyingblue.us/en/spend/flights/rewards) if pushed back on.

5. **Singapore KrisFlyer Saver awards** beat Advantage on cost but allow only 1 stopover round-trip vs 2.

6. **Turkish Miles & Smiles is famously hard** to book by phone but offers excellent Star Alliance pricing if you're patient.

7. **United Excursionist Perk is GONE** as of August 21, 2025. Don't recommend MileagePlus for stopover routing anymore.

8. **For BA Avios, AA AAdvantage, Delta SkyMiles** — these don't allow stopovers. Either book each segment as its own award (for the redemption price) or use a different program (e.g. Alaska Atmos for Cathay, Flying Blue for Delta metal).

9. **When in doubt, the program's own award rules page is canonical.** Frequent Miler, OMAAT, and Travel Miles 101 are cross-checks.

## Cross-References

- [`partner-awards`](../partner-awards/SKILL.md) — what you can book through a program (alliance + bilateral) before checking stopover rules
- [`alliances`](../alliances/SKILL.md) — alliance membership for the multi-carrier oneworld/Star/SkyTeam stopover rules
- [`booking-guidance`](../booking-guidance/SKILL.md) — phone numbers for programs that require phone booking (Flying Blue, Alaska, Turkish, Etihad, Qatar)
- [`transfer-partners`](../transfer-partners/SKILL.md) — transferable point currency that reaches the program for the stopover redemption
- [`transfer-bonuses`](../transfer-bonuses/SKILL.md) — current transfer promotions that may make a stopover-friendly program even cheaper

## Source Hierarchy (Per Research Integrity Protocol)

1. **The airline's own award rules page** — canonical when available
2. **Frequent Miler** — most respected secondary source for current accuracy
3. **OMAAT (One Mile at a Time)** — comprehensive guides, occasionally outdated
4. **Travel Miles 101** — accurate baseline reference
5. **Prince of Travel** — strong on Aeroplan and Alaska
6. **Upgraded Points / TPG / View From The Wing** — useful but often slower to update on devaluations

When sources disagree, the airline's own page wins. When the airline's page is silent or ambiguous, the most-recent Frequent Miler post wins. Never make up rules.

## Avoiding Fabrication

- The data file has confidence markers (VERIFIED / LIKELY / UNVERIFIED). When confidence is below VERIFIED, communicate that uncertainty to the user.
- If a user asks about a program not in the data file, say so honestly. Don't guess. Look it up via Frequent Miler or the airline's own page first.
- Stopover rules can quietly change. Note the `last_verified` date when you cite a rule. Anything older than 90 days should be re-verified before being recommended for an actual booking.

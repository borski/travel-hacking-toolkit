---
name: alliances
description: Airline alliance reference (Star Alliance, oneworld, SkyTeam) and key cross-alliance booking relationships. Maps which loyalty programs can book which airlines. Load when researching award flights, deciding which program to book through, or when partnerships and alliance membership matter. Triggers on "Star Alliance", "oneworld", "SkyTeam", "alliance partner", "which program books", "United partners", "AAdvantage partners", "Aeroplan", "Flying Blue", "LifeMiles", "ANA", "cross-alliance", or any award booking that depends on partnership relationships.
---

# Alliance Awareness

**Reference data:** `data/alliances.json`

Star Alliance, oneworld, and SkyTeam determine which loyalty programs can book which airlines. This is fundamental to award travel. When recommending an award booking, always verify the airline and the booking program are in the same alliance (or have a bilateral partnership).

## Key Booking Relationships

- **United MileagePlus** books Star Alliance (ANA, Lufthansa, Singapore, Turkish, etc.)
- **Aeroplan** books Star Alliance plus extended partners (including Etihad, Emirates on some routes)
- **Virgin Atlantic Flying Club** books ANA, Delta, Air France, KLM (cross-alliance)
- **AAdvantage** books oneworld (Cathay, JAL, Qantas, Qatar, BA, etc.)
- **Flying Blue** books SkyTeam (Air France, KLM, Delta, Korean Air, etc.)
- **Korean Air SKYPASS** books SkyTeam
- **Avianca LifeMiles** books Star Alliance (often cheaper than United/Aeroplan)

## Recent Alliance Changes

Verify against `data/alliances.json` for current state. These have shifted recently:

- SAS moved from Star Alliance to SkyTeam (September 2024)
- ITA Airways left SkyTeam (early 2025), joining Star Alliance (first half 2026)
- Fiji Airways upgraded to full oneworld member (2025)
- Hawaiian Airlines joining oneworld (April 2026)

## Cross-Alliance Bookings Are Where Real Value Hides

The best redemptions often involve booking an airline through a program in a DIFFERENT alliance (or no alliance at all). Always check the `cross_alliance_highlights` section of `data/alliances.json` and `data/partner-awards.json`.

Examples of cross-alliance plays:
- Virgin Atlantic Flying Club books ANA First Class (legendary sweet spot)
- Etihad Guest books AAdvantage routes
- Alaska Mileage Plan books Starlux (independent airline)

## Partner Awards Reference

For the full picture of which programs ticket which airlines, plus bilateral partnerships outside alliances, load the `partner-awards` skill or read `data/partner-awards.json` directly.
</content>
</invoke>
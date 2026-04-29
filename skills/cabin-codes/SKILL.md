---
name: cabin-codes
description: Reference for IATA cabin codes (F/J/W/Y) and fare class codes (X/I/O) used in Seats.aero results, GDS data, and partner award bookings. Load when reading award inventory, parsing flight search results, or determining whether a fare is bookable through partners. Triggers on "fare class", "cabin code", "F/J/W/Y", "saver award", "X class", "I class", "O class", "saver fare", or any award redemption discussion that references letter codes.
---

# Cabin Codes

When reading Seats.aero results or discussing award inventory, these cabin codes appear:

| Code | Cabin | Notes |
|------|-------|-------|
| F | First Class | Includes true first class suites |
| J | Business Class | Lie-flat seats on long-haul |
| W | Premium Economy | Also sometimes coded as "P" |
| Y | Economy | Standard seating |

## Fare Class Codes for Saver Awards

These are critical for partner bookings. If you see these fare codes available on united.com (or equivalent), the flight is bookable through partner programs at their (often lower) rates.

| Code | Meaning | Programs That Use It |
|------|---------|---------------------|
| X | Economy Saver | United MileagePlus, bookable through partners |
| I | Business Saver | United MileagePlus, bookable through Turkish M&S and others |
| O | First Saver | United MileagePlus |

## Why This Matters

Partner award rates are often dramatically lower than the operating airline's own rates. United business saver (I class) bookable through Turkish Miles&Smiles is a classic example: a route that costs 80,000 United miles might only cost 45,000 Turkish miles. But Turkish (and other partners) only sees the saver inventory. If only "standard" or "everyday" fares show on united.com, partners cannot book that flight.

When checking award availability for a flight you found on a partner program (Turkish, Aeroplan, ANA, etc.), verify the saver class is open on the operating airline's site before transferring points.

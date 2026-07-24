---
name: gardening
description: Audit and tend to existing travel reservations. Reads a user-provided reservations file, then systematically checks every booking for price drops, better cabin availability, improved routings, schedule changes, nearby airport alternatives, and award repricing opportunities. Invoke proactively on a regular cadence or when the user says "garden", "check my bookings", "audit reservations", "price drop", "better routing", "did my flight change", "tend reservations", "reservation maintenance", or "check my trips".
category: orchestration
summary: Audit existing reservations for price drops, better cabins, schedule changes, and improved routings.
api_key: Uses individual skill keys
---

# Reservation Gardening

**Concept:** "Gardening" (coined by Nicholas Kralev, popularized by View from the Wing) means regularly tending to your travel reservations — catching problems early and spotting opportunities to upgrade, rebook, or save money.

## Reservations File

The user points this skill at a file containing their current bookings. The file path is provided when invoking the skill (e.g., `~/trips/reservations.json` or `~/trips/reservations.yaml`).

**If no file path is provided, ask the user for it.**

### Expected File Format

The file should contain an array of reservations. Each reservation should include as much of the following as possible:

```json
[
  {
    "trip_name": "Sydney Vacation",
    "confirmation": "ABC123",
    "type": "flight",
    "booking_date": "2026-03-15",
    "program": "United MileagePlus",
    "paid_with": "points",
    "cost": { "miles": 85000, "taxes_usd": 45.60 },
    "cash_price_at_booking": 2340,
    "segments": [
      {
        "airline": "UA",
        "flight": "UA870",
        "origin": "SFO",
        "destination": "SYD",
        "date": "2026-09-12",
        "departure": "22:30",
        "arrival": "07:15+2",
        "cabin": "business",
        "fare_class": "I",
        "seat": "6A",
        "aircraft": "787-9"
      }
    ],
    "passengers": 2,
    "notes": "Booked with Chase UR transfer"
  },
  {
    "trip_name": "Sydney Vacation",
    "confirmation": "HTL-9876",
    "type": "hotel",
    "hotel_name": "Park Hyatt Sydney",
    "program": "World of Hyatt",
    "paid_with": "points",
    "cost": { "points": 30000, "per_night": true },
    "cash_price_at_booking": 850,
    "checkin": "2026-09-14",
    "checkout": "2026-09-18",
    "room_type": "King Deluxe",
    "guests": 2
  }
]
```

Flexible on format — YAML, JSON, CSV, or even markdown tables are fine. Parse whatever is provided.

## Gardening Checklist

For **every reservation** in the file, run through this checklist. Parallelize searches across reservations for speed.

### 1. Price Drop Detection (PRIORITY)

This is the user's #1 interest. For each booking:

**Cash bookings:**
- Search current cash prices on the SAME flights/dates using Duffel, Ignav, Google Flights, Skiplagged, and Kiwi
- Search **nearby airports** (within ~100 miles / reasonable driving distance) for the same dates
  - SFO → also check OAK, SJC
  - LAX → also check BUR, SNA, LGB, ONT
  - NYC → also check JFK, EWR, LGA
  - CHI → also check ORD, MDW
  - DCA → also check IAD, BWI
  - Use common sense for other cities
- Compare current price vs booked price
- Flag if current price is **≥10% lower** or **≥$50 cheaper** (whichever triggers first)
- Note the airline's rebooking/price-match policy (e.g., Southwest auto-refunds the difference; most US airlines allow free cancellation within 24hrs of booking; some credit cards have price protection)

**Award bookings:**
- Search current award availability on the same route/dates via Seats.aero and the booking program
- Check if the same flight is now available for **fewer miles**
- Check if a **better cabin** is now available at the same or similar mileage price
- Check if a **different program** now offers the same flight cheaper (cross-reference `data/sweet-spots.json`)
- For dynamic-pricing programs (United, Delta, Aeroplan on some partners), prices fluctuate — a drop is rebookable

**Hotels:**
- Search current rates on the same hotel via LiteAPI, Trivago, Skiplagged Hotels
- Check portal pricing (Chase UR, Amex) if the user has those currencies
- For award hotel stays, check if the points price dropped
- Flag cash rate drops and compare against the award value (cpp math)

### 2. Better Routing / Connection Check

For each flight:
- Search the same origin-destination pair on the same date for:
  - **Nonstop options** that may have opened up (if the booking has stops)
  - **Shorter connections** (if booked connection is >3 hours)
  - **Better connection airports** (avoiding known bad ones like ORD in winter, LHR T5-to-T3 transfers)
- Search **nearby origin/destination airports** for:
  - Better nonstop availability
  - Significantly cheaper fares
  - Better timing (red-eye vs daytime)
- Flag routes where the total travel time can be reduced by **≥1 hour**

### 3. Better Cabin Availability

For each flight booked in economy or premium economy:
- Check if **business or first class award space** has opened up on the same flight
- Check the price in the user's booking program AND alternative programs
- Calculate the **incremental cost** to upgrade (e.g., "upgrade from 38K economy to 85K business = 47K more miles, worth 3.2cpp against $1,500 cash fare difference")
- For paid tickets, check if paid upgrades, upgrade certificates, or mileage upgrades are available

For each flight already in business:
- Check if **first class** has opened up (especially on airlines with great F products: ANA, Singapore, Cathay, Emirates)

### 4. Schedule Change Detection

- If the user provides confirmation codes / PNRs, note that AwardWallet can monitor these automatically
- Flag any segments where the **departure time may have shifted** (search current schedules)
- Check for **aircraft type changes** (e.g., 787-9 → 737 is a significant downgrade; 777-300ER → A350 may change seat map)
- Warn about **seasonal schedule changes** if the trip is far out (airlines typically publish schedules in waves)

### 5. Seat Assignment Check

- If seats are listed in the reservation, verify the seat still makes sense for the aircraft type
- Flag if an aircraft swap may have invalidated the seat assignment
- Suggest using the `seatmaps` skill for detailed seat recommendations if relevant

## Output Format

Present results as a **per-reservation audit report**:

```
## 🌱 Gardening Report: [Trip Name]

### [Confirmation] — [Route] on [Date]

| Check | Status | Details |
|-------|--------|---------|
| Price | 🔴 DROP | Was $2,340, now $1,890 (-$450, -19%). Rebookable via United free cancel/rebook. |
| Nearby airports | 🟡 NOTE | OAK-SYD via AKL on Air NZ: $1,780 (-$560 vs SFO). Adds 2hr travel time to OAK. |
| Better cabin | 🟢 UPGRADE | First class opened up: 110K United (vs 85K booked in J). ANA F via VA would be 72.5K. |
| Routing | ✅ OK | Current routing is optimal. |
| Schedule | ✅ OK | No changes detected. |
| Seat | ⚠️ CHECK | Aircraft changed from 787-9 to 777-300ER. Seat 6A may not exist. Verify on seatmaps. |
```

### Summary Section

After all reservations, provide a **priority action list**:

```
## 🎯 Priority Actions

1. **REBOOK NOW** — SFO-SYD dropped $450. Free cancel/rebook on United. Save $900 for 2 passengers.
2. **CONSIDER** — ANA First opened up via Virgin Atlantic for 72.5K. Currently in J at 85K United. Better product, fewer miles, but phone booking required.
3. **VERIFY** — Aircraft swap on UA870. Check seat assignment.
```

## When to Garden

Recommend the user gardens their reservations:
- **Immediately after booking** — verify tickets issued, seats assigned, confirmation visible on operating airline
- **Monthly** for trips >30 days out
- **Weekly** for trips 7-30 days out
- **Daily** for trips <7 days out
- **After any airline schedule change announcement** (typically Mar/Apr and Sep/Oct)

## Tools to Use

Invoke these in parallel for each reservation:
- **Duffel / Ignav / Google Flights / Skiplagged / Kiwi** — current cash prices
- **Seats.aero** — current award availability
- **LiteAPI / Trivago / Skiplagged Hotels** — hotel price checks
- **AwardWallet** — pull latest itineraries and detect changes automatically
- **Seatmaps** — verify seat assignments after aircraft swaps

## AwardWallet Integration

AwardWallet is the best automated gardening tool available:
- It scrapes itineraries from loyalty accounts and emails
- It detects and alerts on schedule changes, aircraft swaps, seat changes, and class of service changes
- Recommend the user connect their accounts if not already done
- When running this skill, always pull fresh AwardWallet data first to catch changes the user may not know about

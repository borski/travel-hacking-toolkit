---
name: booking-guidance
description: Step-by-step guidance for booking award flights. Covers the hold-before-transfer rule, phone numbers for major programs, and partner award booking workflows.
category: reference
summary: The booking flow, hold-before-transfer rule, phone numbers for major programs.
---

# Booking Guidance

Finding the deal is half the battle. Telling the user how to actually book it is the other half. **Every recommendation should include a booking path.**

**Reference data:** `data/alliances.json` has booking details for major programs in `key_booking_relationships`.

## General Booking Flow

1. **Find availability** (Seats.aero, airline website, or MCP tool)
2. **Verify the program you want to book through** shows the same availability
3. **If transferring points:** get a HOLD on the award ticket FIRST, then transfer
4. **Transfer points** from credit card to loyalty program
5. **Call or go online** to complete the booking

## Critical Rule: Never Transfer Without a Hold

**Transfers are instant with most programs but IRREVERSIBLE.** If availability disappears between the transfer and the booking, points are stuck in the loyalty program.

The right order:
1. Find the award and put it on hold (24-72 hours typically) through the booking program
2. THEN transfer points from the credit card
3. THEN complete the booking against the held space

**Critical caveat: hold rules vary widely and change.** Always check the `award-holds` skill (data file `data/award-holds.json`) for current per-program rules. As of April 2026: AA holds 24h online (free), Lufthansa M&M 5 days, Flying Blue 3 days ($25 phone fee at ticketing), Cathay Asia Miles 2 days ($39 phone fee), Turkish 2 days, Virgin Atlantic 1-2 days (free, phone), Singapore agent-discretionary. Programs that DO NOT allow holds: United, Alaska, Delta, BA, Aeroplan, ANA, Qatar, Korean. The "hold first, transfer second" pattern works wherever a hold is available.

When holds aren't available, transfer in small batches if you're confident the space will hold (high seat counts, low-popularity dates), or accept the risk. Never transfer your full balance speculatively.

## Phone Numbers for Major Programs

Some awards must be booked by phone. Memorize or save these.

| Program | Phone | Online Booking? |
|---------|-------|-----------------|
| Virgin Atlantic (ANA awards) | 1-800-365-9500 | No (ANA must be by phone) |
| United MileagePlus | 1-800-864-8331 | Yes (united.com) |
| Aeroplan | 1-888-247-2262 | Yes (aircanada.com) |
| Turkish Miles&Smiles | 1-800-874-8875 | Yes (turkishairlines.com) |
| Korean Air SKYPASS | 1-800-438-5000 | No (partner awards by phone) |
| Flying Blue | 1-800-237-2747 | Yes (stopovers by phone) |
| AAdvantage | 1-800-882-8880 | Yes (aa.com) |
| Japan Airlines | 1-800-525-3663 | No (find space on ba.com or qantas.com, call JAL to book) |
| Iberia Avios | N/A | Yes (iberia.com) |
| Qatar Privilege Club | N/A | Yes (qatarairways.com) |
| Hyatt | N/A | Yes (hyatt.com or app) |

## When Phone Bookings Are Required

A partner award that's "hidden" (not bookable online) often requires a phone agent. Common cases:
- **ANA First/Business via Virgin Atlantic:** Must call. Agent searches space manually.
- **JAL via Alaska or AAdvantage:** Find space on ba.com (proxy), then call to book.
- **Korean Air partner awards:** Skypass partner awards are phone-only.
- **Stopovers on most programs:** Online tools rarely allow stopovers. Call.

## Tips for Phone Bookings

- **Have flight numbers, dates, and class ready.** Don't ask the agent to "look around."
- **HUCA (Hang Up, Call Again) is a real strategy.** Some agents are better than others. If one says "no space," try another.
- **Confirm the fare before agreeing.** Some programs charge surcharges that wreck the cpp math.
- **Get a booking reference (PNR).** Verify the ticket on the operating airline's site within 24 hours.

## Saver Inventory Verification

Many partner programs only see "saver" inventory on the operating carrier. If you find space on the operating airline's site but the partner program shows nothing, check the fare class. Saver classes are X (economy), I (business), O (first) on United. If the carrier only has standard or anytime class open, partners can't book it.

See the `cabin-codes` skill for the full mapping.

## Status Effects on Booking

Elite status with the booking program (or alliance partner) often unlocks longer hold windows, waived close-in booking fees, and priority on phone bookings. If the user has elite status, mention which benefits apply. If they don't and the question of getting status comes up, load the `status-match` skill — it covers the lifetime restrictions that punish wasted matches and the renewable card-based alternatives.

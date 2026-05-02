---
name: award-holds
description: Per-program rules for placing award flights on hold before transferring points. Covers programs with holds (AA, Lufthansa, Flying Blue, Cathay, Turkish, Virgin Atlantic) and those without. Includes transfer-speed reference.
category: reference
summary: Per-program rules for placing award flight tickets on hold. Covers 6 programs with reliable holds (AA 24h online, LH 5 days, FB 3 days, CX 2 days, Turkish 2 days, Virgin Atlantic 1-2 days), Singapore as agent-discretionary, and the negative space (UA/AS/DL/Aeroplan/BA/ANA/Qatar/Korean - most programs do not allow holds).
allowed-tools: Bash(jq *), Read
---

# Award Hold Policies per Loyalty Program

Reference data for which programs allow you to put an award flight ticket on hold, for how long, at what cost, and via what method (online vs phone). Critical for transferable-currency redemptions where transfers take minutes to days to clear.

Data lives in [`data/award-holds.json`](../../data/award-holds.json). Refresh cadence is 90 days because hold rules change rarely.

## Why Holds Matter

When you find an award seat but the points are sitting in a transferable currency (Amex MR, Chase UR, Citi TYP, Capital One, Bilt, Marriott Bonvoy), you need to transfer them to the loyalty program before booking. Transfer times range from instant (most Amex/Chase partners) to 4 days (Marriott Bonvoy to airline partners).

Without a hold, you risk losing the award seat while the transfer pends. **A hold removes the seats from the available pool for the duration**, guaranteeing they'll still be there when you ticket.

## When to Use This Skill

- User is planning a transferable-points booking and asks "can I hold this?"
- User is comparing programs to redeem the same partner award (e.g., Cathay first/business via AA vs Cathay Asia Miles)
- User asks about the AA 24-hour hold change vs the old 5-day policy
- Trip planning involves Marriott Bonvoy → airline transfers (4 days, must use a hold)
- Researching whether a specific program supports holds before committing to the redemption strategy

## When NOT to Use

- Stopover questions (use [`stopovers`](../stopovers/SKILL.md) skill)
- Cancellation/refund questions (different concept — that's about UNDOING a ticketed booking, not holding before booking)
- Award availability search (use [`seats-aero`](../seats-aero/SKILL.md))
- Routing-rule questions (use [`partner-awards`](../partner-awards/SKILL.md))

## Programs That Allow Holds (6 reliable + Singapore agent-discretionary)

| Program | Max Days | Hold Fee | Phone Fee | Online Self-Serve | Confidence |
|---------|----------|----------|-----------|-------------------|------------|
| American AAdvantage | 1 | $0 | $0 (free changes/cancels) | **Yes** | VERIFIED |
| Lufthansa Miles & More | 5 | $0 | $20 | No | VERIFIED |
| Air France/KLM Flying Blue | 3 | $0 | $25 | No | VERIFIED |
| Cathay Asia Miles | 2 | $0 | $39 | No | VERIFIED |
| Turkish Miles & Smiles | 2 | $0 | varies | No | LIKELY |
| Virgin Atlantic Flying Club | 1-2 | $0 | $0 | No | VERIFIED |
| Singapore KrisFlyer | agent discretion | $0 | $25 or 2,500 miles | No | LIKELY |

## Programs That Do NOT Allow Holds

These programs require you to have the points in your account at booking time. Plan transfers accordingly.

- United MileagePlus
- Delta SkyMiles
- Alaska Atmos Rewards (formerly Mileage Plan)
- Air Canada Aeroplan
- British Airways Executive Club
- Iberia Plus
- ANA Mileage Club
- Qatar Privilege Club
- Korean SKYPASS
- Etihad Guest (no published policy)

## Decision Rules

### Rule 1: AA AAdvantage is the universal hold tool

If the redemption is bookable through American AAdvantage, **use AA's online self-serve hold**. No phone call, no fee, no credit card needed. Click "Hold" on the booking confirmation page. 24-hour window.

This works for partner awards too: Cathay first/business, Qatar Qsuite, JAL First, Iberia, BA, Royal Air Maroc, etc.

### Rule 2: For Star Alliance partners, Lufthansa is the longest hold

5-day free hold via Miles & More phone line, $20 ticketing fee. Holds work for LH, SWISS, Austrian, Brussels, plus select Star Alliance partners. Ideal when you're transferring from Marriott Bonvoy (4-day transfer time).

### Rule 3: For SkyTeam partners, Flying Blue holds 3 days

$25 phone-booking fee. Partner award holds work but are agent-discretionary.

### Rule 4: Match transfer speed to program hold availability

| Transferable Currency | Transfer Speed | Need a Hold? |
|----------------------|----------------|--------------|
| Amex MR → most partners | Instant | No |
| Amex MR → ANA | 1-2 days | **Yes** |
| Amex MR → BA, Singapore, Cathay | Hours | Maybe |
| Chase UR → all partners | Instant | No |
| Capital One miles → most | Instant | No |
| Citi TYP → most | Hours | Maybe |
| Bilt → all partners | Instant | No |
| Marriott Bonvoy → airline | **4 days** | **YES, always** |

### Rule 5: When the redeeming program doesn't allow holds, redirect

Want a Cathay first/business via Alaska Atmos (no holds)? Book it via American AAdvantage instead (24h online hold, free) for the same award. Then transfer Bilt (1:1 instant), Citi TYP (1:1, 1-2 days), or Marriott Bonvoy (3:1 base ratio with a 5,000-mile bonus per 60K transferred, so 60K Bonvoy = 25K AAdvantage miles, 4-day delivery) to AAdvantage. AAdvantage does NOT partner with Amex MR or Chase UR.

Want a United partner award via MileagePlus (no holds)? Book it via Lufthansa Miles & More instead (5-day hold) when both programs ticket the same Star Alliance flight.

### Rule 6: The 5-day-hold era is over for AA

AA reduced holds from 5 days to 24 hours in late 2024. The 24-hour hold still beats UA, AS, DL (which have no holds), but if you're booking AA from Marriott Bonvoy (4 days), the hold won't survive the transfer. Use Lufthansa Miles & More instead, OR transfer Bonvoy in advance and book on the spot.

## Reading the Data File

```bash
# Programs that allow holds, sorted by max hold days
jq '.programs[] | select(.category == "positive") |
    {name, max_days: .max_hold_days, hold_fee: .hold_fee_usd,
     phone_fee: .phone_booking_fee_usd, online: .self_serve_online}' \
    data/award-holds.json | head -50

# Programs that do NOT allow holds
jq '.programs[] | select(.category == "negative") | {name, restrictions}' \
    data/award-holds.json

# Sources for a specific program
jq '.programs[] | select(.id == "american_aadvantage") | .sources' \
    data/award-holds.json

# Transfer-speed reference
jq '.transfer_speed_reference' data/award-holds.json
```

## Cross-References

- [`transfer-partners`](../transfer-partners/SKILL.md) — find which transferable currencies reach a given program
- [`transfer-bonuses`](../transfer-bonuses/SKILL.md) — current promotional bonuses on transfers
- [`partner-awards`](../partner-awards/SKILL.md) — which alliance / bilateral awards each program can ticket (so you know your hold options for a given award)
- [`booking-guidance`](../booking-guidance/SKILL.md) — phone numbers, the canonical "hold before transfer" workflow
- [`seats-aero`](../seats-aero/SKILL.md) — finding the award space to hold
- [`stopovers`](../stopovers/SKILL.md) — multi-segment / stopover awards have specific hold rules per program (some allow holds on online-only single-segment awards but not multi-segment ones requiring phone booking)
- [`round-the-world`](../round-the-world/SKILL.md) — RTW bookings have unique hold rules. Star Alliance RTW must be ticketed >=72 hours before first departure (effectively a hard purchase deadline, not a hold). Most other RTWs require phone booking and immediate ticketing.
- [`status-match`](../status-match/SKILL.md) — Elite tiers sometimes unlock waived close-in booking fees, priority on phone-booking queues, or other booking benefits. AA's hold policy applies equally to all members (24h online); other programs may grant elite-only hold privileges but verify per-program before assuming.

## Source Hierarchy (Per Research Integrity Protocol)

1. **The airline's own award rules / phone-line confirmation** — canonical
2. **Frugal Flyer's award-hold guide** — most current authoritative third-party list (canonical for the 6 reliable + Singapore agent-discretionary set)
3. **Upgraded Points award-hold table** — comprehensive 2025 update with phone numbers and fees
4. **Point.me, Frequent Miler, OMAAT** — corroborating reports
5. **Live and Let's Fly, 10xTravel** — for recent policy changes (e.g., the AA 5-day → 24-hour reduction)

When sources disagree (e.g., FF says Cathay = 2 days, UP says 3 days), the data file uses the more conservative number. Confidence markers reflect source agreement.

## Avoiding Fabrication

- Hold rules are agent-dependent in practice. The data file gives the published policy; actual behavior may vary by call.
- The 6 reliable + Singapore agent-discretionary list is canonical as of 2024 (Frugal Flyer). If a user reports a hold experience with a program NOT on the list (e.g., Etihad reports from years past), document it as anecdotal but don't update the data without primary-source confirmation.
- Phone numbers can change. Always verify the published phone number on the airline's site before recommending a call.

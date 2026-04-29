---
name: partner-awards
description: Reference for which loyalty programs can ticket which airlines, including alliance-based and bilateral partnerships. Cross-references credit card transferable currencies to booking programs. Load when verifying an award booking is bookable through a specific program, when finding cross-alliance value plays, or when calculating which currencies reach a desired airline. Triggers on "can I book X with Y miles", "partner award", "bilateral partnership", "which program books", "transfer to United", "transfer to Aeroplan", "cross-alliance", "extended partners", or any reachability question about award flights.
---

# Partner Awards

**Reference data:** `data/partner-awards.json`

When recommending award bookings, check this file to verify:
1. The booking program can actually ticket the airline you're recommending
2. Whether the partnership is alliance-based or bilateral
3. Cross-alliance highlights (VA→ANA, Etihad→AA, Alaska→Starlux, etc.)
4. Which credit card currencies can reach the booking program

## Cross-Alliance Bookings Are Where the Real Value Hides

The best redemptions often involve booking an airline through a program in a DIFFERENT alliance (or no alliance at all). Always check the `cross_alliance_highlights` section.

## Verification Is Mandatory, Not Optional

When recommending a transfer, ALWAYS verify the transfer path exists in `data/transfer-partners.json` BEFORE committing to the recommendation. If a user or your own reasoning suggests a transfer path not in the file, verify it before agreeing. The file may be stale, or the path may not exist.

This is a hard gate, not a soft check. Never accept a transfer path at face value.

## Reachability Workflow

When checking if a user can actually book an award flight:

1. **Identify the operating airline.** Star Alliance? oneworld? SkyTeam? Independent?
2. **List all programs that can ticket it.** Alliance partners + bilateral partners from `partner-awards.json`.
3. **For each program, check direct balance.** AwardWallet shows what the user has now.
4. **For each program with insufficient balance, check transfer paths.** `data/transfer-partners.json` lists every credit card currency → airline program path with the ratio.
5. **Effective balance = direct balance + max transferable in.** A user with 16K United miles but 145K Chase UR has 161K effective United miles (UR transfers 1:1 to United).
6. **Drop programs that are unreachable.** Only compare cpp on options the user can actually book.

## Common Failure Modes

- Assuming an airline "can't be booked with points" because the user has zero direct balance. Always check transfer reachability first.
- Recommending a transfer without verifying the path. Some routes that "seem like they should work" don't (e.g., Amex MR does NOT transfer to United).
- Missing cross-alliance plays. United metal flights can be booked via Turkish M&S, Avianca LifeMiles, Aeroplan, ANA, and others, often at very different rates.

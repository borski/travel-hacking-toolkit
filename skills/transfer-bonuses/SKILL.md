---
name: transfer-bonuses
description: Active credit card transfer bonuses from Amex, Chase, Capital One, Citi, Bilt, and Rove. Weekly-refreshed data with confidence markers. Use when pricing an award booking that involves a points transfer or deciding whether to wait for a better bonus.
category: reference
summary: Active credit card transfer bonuses with primary-source citations. Tells the agent the real effective ratio when transferring points during a promotion.
---

# Transfer Bonuses Skill

Authoritative reference for current credit card transfer bonuses. Reads from `data/transfer-bonuses.json`, which is refreshed weekly by `scripts/refresh-transfer-bonuses.py`. The script scrapes Frequent Miler (canonical) and cross-checks each bonus against AwardWallet. Each active bonus carries a confidence marker (`VERIFIED` if both FM and AwardWallet agree, `LIKELY` if only FM, `UNVERIFIED` if single weak source) per the toolkit's Research Integrity Protocol. TPG is sometimes consulted manually as a sanity check but is NOT scraped programmatically — TPG often shows expired bonuses as active.

## When to Use

- **Pricing an award booking that involves a transfer.** A 30% bonus to JAL changes the real cost of a oneworld booking through JAL by 23%. The math has to factor in the bonus.
- **Deciding whether to transfer now or wait.** If a bonus is expected to recur (see `frequent_recurring_bonuses_to_watch`), it may be worth waiting.
- **Sanity-checking whether a "good bonus" actually wins.** Hotel bonuses especially (Chase UR to IHG 70%, Chase UR to Marriott 50-70%) often look great in headlines but lose to the Chase Travel portal (dynamic Points Boost on CSR/CSP, ~1.5-2.0 cpp on select bookings; not a guaranteed floor). Always pull the actual portal quote and run the math against it, not against an assumed rate.
- **Identifying stackable bonuses.** Aeroplan Visa cardholders stack a 10% cardholder bonus on top of any Chase UR to Aeroplan promotion.

## When NOT to Use

- Transfer ratios in general (without an active bonus). Use [transfer-partners](../transfer-partners/SKILL.md) for the standard ratios.
- Points valuations (cpp by program). Use [points-valuations](../points-valuations/SKILL.md).
- Award flight availability. Use [seats-aero](../seats-aero/SKILL.md).
- Booking guidance and the hold-before-transfer rule. Use [booking-guidance](../booking-guidance/SKILL.md).

## Data File

`data/transfer-bonuses.json`. Schema (relevant fields):

| Field | Description |
|-------|-------------|
| `_meta.last_updated` | ISO date, last refresh |
| `_meta.staleness_days` | TTL in days; integrated with `scripts/check-data-freshness.sh` |
| `_meta.primary_sources` | Frequent Miler, AwardWallet (TPG consulted manually only) |
| `active_bonuses[].bonus_pct` | The bonus percentage (e.g., 30 for 30%) |
| `active_bonuses[].ratio` | Multiplier on standard ratio (1.30 = 30% bonus) |
| `active_bonuses[].standard_ratio` | Baseline transfer ratio (1.0 = 1:1, 0.75 = 4:3) |
| `active_bonuses[].effective_ratio` | Final ratio after bonus (`standard_ratio * ratio`) |
| `active_bonuses[].end_date_inclusive` | Last day the bonus is active |
| `active_bonuses[].confidence` | VERIFIED, LIKELY, or UNVERIFIED |
| `active_bonuses[].sources[]` | Direct URLs to primary source posts |
| `active_bonuses[].notes` | Strategic context, including "but you shouldn't" warnings |
| `expired_recently[]` | Bonuses that ended in the last 30 days. Useful for noticing TPG/AW staleness. |
| `frequent_recurring_bonuses_to_watch{}` | Bonuses that historically recur, with typical % and frequency. Use for "should I wait?" decisions. |
| `decision_rules{}` | Six concrete rules for how to factor bonuses into a transfer decision. |

## Refreshing the Data

Run weekly (or on-demand) via:

```bash
python3 scripts/refresh-transfer-bonuses.py
```

The script:

1. Scrapes Frequent Miler's current point transfer bonuses page (canonical source).
2. Cross-checks each bonus against AwardWallet.
3. Sets confidence based on cross-check results: VERIFIED if 2+ sources agree, LIKELY if only Frequent Miler.
4. Moves expired bonuses to `expired_recently[]`.
5. Updates `_meta.last_updated`.

`scripts/check-data-freshness.sh` flags this file as stale after 7 days.

If the script fails (Frequent Miler's HTML changed, network issue, etc.), fall back to manual update by visiting the two primary sources (Frequent Miler, AwardWallet) and editing the JSON by hand. TPG can be consulted as a sanity check but is not authoritative because it frequently shows expired bonuses as active. **NEVER fabricate a bonus**. Per the Research Integrity Protocol, if you cannot verify a bonus from a primary source, do not include it.

## Quick Reference Output Format

When the user asks "what bonuses are active right now?", read `data/transfer-bonuses.json` and produce a markdown table. Sample format (illustrative — pull live values from the data file, not from this example):

```
| From | To | Bonus | End Date | Effective Ratio | Confidence | Notes |
|------|----|-------|----------|-----------------|------------|-------|
| Amex MR | Hilton Honors | 20% | YYYY-MM-DD | 1:2.4 | VERIFIED | Skip unless specific Hilton stay; effective ~1.2 cpp |
| Chase UR | Aeroplan | 20% (30% w/ Aeroplan Visa) | YYYY-MM-DD | 1:1.20 (1.30) | VERIFIED | Star Alliance; no fuel surcharges; stackable |
| Chase UR | IHG | 70% | YYYY-MM-DD | 1:1.70 | VERIFIED | "But you shouldn't" - Chase Travel portal (dynamic Points Boost; verify actual quote) typically wins for IHG bookings |
| Capital One | JAL | 30% | YYYY-MM-DD | 1:0.975 | VERIFIED | Brings standard 4:3 to ~1:1; oneworld |
| Citi TYP | Leading Hotels | 25% | YYYY-MM-DD | 1:1.25 | LIKELY | Niche luxury; only useful for specific LHW stays |
```

(The table format and notes apply across program-pairs. The actual current end dates and effective ratios live in `data/transfer-bonuses.json` and update weekly via `scripts/refresh-transfer-bonuses.py`.)

Then below the table:

- Highlight any redemption the user has actively planned that this bonus accelerates.
- Mention stackable bonuses if applicable (e.g., Aeroplan Visa cardholder bonus).
- Flag the "but you shouldn't" cases with reasoning.
- If a recurring bonus is on the watch list and the user's timeline is flexible, suggest waiting.

## Computing Effective Cost

For any award redemption that requires a transfer, compute the effective cost both ways:

**Without bonus:**
```
points_required_in_card_currency = miles_required / standard_ratio
```

**With bonus:**
```
points_required_in_card_currency = miles_required / effective_ratio
```

**Example: book a 70k JAL business class award via Capital One during April 2026:**
- Standard: 70,000 / 0.75 = 93,333 Capital One miles
- With 30% bonus: 70,000 / 0.975 = 71,795 Capital One miles
- **Savings: ~21,538 miles** (~$398 at TPG's 1.85 cpp Capital One valuation; 21538 × 0.0185 = 398.45)

## Cross-References

- [transfer-partners](../transfer-partners/SKILL.md): standard transfer ratios (no bonus)
- [points-valuations](../points-valuations/SKILL.md): cpp floor per program; use to sanity-check whether a bonus actually beats portal/cash
- [booking-guidance](../booking-guidance/SKILL.md): the critical "hold before you transfer" rule
- [award-holds](../award-holds/SKILL.md): per-program hold rules. Critical because most major Western programs no longer offer holds, which makes timing transfers around bonus expirations more dangerous.
- [seats-aero](../seats-aero/SKILL.md): verify award availability before transferring
- [partner-awards](../partner-awards/SKILL.md): which programs ticket which airlines
- [stopovers](../stopovers/SKILL.md): if a bonus is active on a stopover-friendly program (e.g. Flying Blue, Aeroplan, Alaska), the effective value of a multi-stop redemption goes up further
- [round-the-world](../round-the-world/SKILL.md): RTW awards take large transfers; a 30% bonus on the right currency dramatically lowers the effective points cost

## Source Hierarchy

When sources disagree:

1. **Frequent Miler** is canonical. Their `current-point-transfer-bonuses` page is updated daily and is the most accurate near-realtime source.
2. **AwardWallet** is a strong cross-check. They list the same bonuses with similar accuracy but slightly less frequently updated.
3. **TPG** is a weaker source. Their page is updated monthly and frequently shows expired bonuses as "active." Use only for confirmation, not as primary.

If TPG shows a bonus that Frequent Miler doesn't, treat it as expired or never-existed unless you can verify from the original promotion source (the airline's own page).

## Avoiding Fabrication

This skill exists in part because LLMs are tempted to confidently invent transfer bonuses. **Never list a bonus that isn't in the data file.** If the data file is stale (`check-data-freshness.sh` reports STALE), refresh it before answering. If refresh fails, tell the user "the data file is stale and I can't refresh right now" rather than guessing.

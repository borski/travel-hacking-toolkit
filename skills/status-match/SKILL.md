---
name: status-match
description: Per-program status match and status challenge rules across airlines and hotels, including the critical lifetime-or-once-per-N-years restrictions that make a wasted match expensive. Distinguishes free direct matches (AA, United, Delta, Alaska, Hyatt, Marriott, Hilton) from paid concierge matches via statusmatch.com (Flying Blue, Lufthansa, Etihad, Aeroplan, Frontier, Spirit, etc.) with real fee data, and from renewable card-based status (Amex Platinum, Hyatt Card, Aspire). Auto-load when the user asks about status match, status challenge, "match my status," elite tier shortcut, Globalist Challenge, Marriott Platinum Challenge, fast-track status, statusmatch.com, statusmatcher.com, or considers switching loyalty programs. Triggers on status match, status challenge, match my status, elite shortcut, Globalist Challenge, Platinum Challenge, fast track elite, statusmatch, lifetime status match, once per lifetime, switch loyalty program.
category: reference
summary: Per-program status match rules with lifetime / once-per-N-years warnings, free vs paid concierge distinction, real fees, plus card-granted renewable status as the alternative.
allowed-tools: Bash(jq *)
---

# Status Match Reference

When a user wants to switch loyalty programs or shortcut to elite status, the question is rarely "can I match?" but "should I match?" The answer depends on three things this skill makes explicit: how often the program lets you do it, what it costs (free vs paid concierge), and whether a credit card already grants the tier you want.

**Reference data:** [`data/status-match.json`](../../data/status-match.json). Refresh cadence is 90 days because rules change occasionally but not weekly.

## Critical Rule: Lifetime Restrictions Punish Wasted Matches

**Many of the best status matches are once-per-lifetime or once-every-3-years.** A match wasted in the wrong year because the user doesn't have travel coming up is gone forever. Always read the `lifetime_warning` field before recommending an application.

The biggest offenders:

| Program | Restriction |
|---------|-------------|
| **Alaska Atmos Rewards** | **ONCE PER LIFETIME** (literally; from terms: "one status match for the lifetime of their account") |
| **Flying Blue (paid concierge)** | **ONCE PER LIFETIME** ("Only 1 match is allowed per person") |
| **United MileagePlus** | **ONCE EVERY 3 YEARS** (failed challenge can extend lockout to 5 years) |
| **Delta SkyMiles** | **ONCE EVERY 3 YEARS** (per official terms) |
| **AA AAdvantage Instant Status Pass** | **ONCE EVERY 2 YEARS** |
| **Hyatt Globalist Challenge** | **ONCE PER LIFETIME** (community-confirmed; not always re-offered) |
| **Marriott Platinum Challenge** | **ONCE PER LIFETIME** (when offered; targeted) |
| **Hilton Diamond Challenge** | **ONCE PER LIFETIME** (Gold via Amex Platinum is renewable separately) |

When the user is considering a match, the first question to answer is "do you have travel that uses this status in the next 6-12 months?" If no, **don't burn the match**. Card-based renewable status is the better fallback (see below).

## When to Use This Skill

- User asks about status match, status challenge, or "matching" elite tiers
- User considers switching airlines or hotel chains for loyalty
- User mentions a once-in-a-while opportunity (e.g., "I just got Hyatt Globalist with their challenge — can I do this again?")
- User mentions statusmatch.com or statusmatcher.com
- User asks how to get elite status without flying/staying as much
- User compares the cost of a paid concierge match vs the value of the perks

## When NOT to Use

- User has elite status already and just wants to use it (use [`booking-guidance`](../booking-guidance/SKILL.md))
- User wants to know which credit card grants which status (this skill covers that, but if the question is pure card recommendations, also reference [`points-valuations`](../points-valuations/SKILL.md))
- Award flight searching (use [`seats-aero`](../seats-aero/SKILL.md), [`compare-flights`](../compare-flights/SKILL.md))

## The Three Paths to Elite Status

### Path 1: Free Direct Status Match

The destination program offers the match for free, no third party. Best path when available.

| Program | Restriction | Initial | Challenge |
|---------|-------------|---------|-----------|
| AA AAdvantage | Once every 2 years | Trial | Yes (Loyalty Points) |
| United MileagePlus | Once every 3 years | 120 days | Yes (PQF + PQP) |
| Delta SkyMiles | Once every 3 years | 90 days | Yes (MQDs) |
| Alaska Atmos | **Once per lifetime** | 90 days | Yes (base points) |
| Hyatt Globalist Challenge | **Once per lifetime** (when offered) | varies | Yes (paid nights) |
| Marriott Platinum Challenge | Once per lifetime (when offered, targeted) | varies | Yes (paid nights) |
| Hilton Diamond Challenge | Once per lifetime | varies | Yes (paid nights) |
| IHG One Rewards | Varies by promo | varies | Sometimes |

For full details, see `direct_matches` section of `data/status-match.json`.

### Path 2: Paid Concierge via statusmatch.com

A third-party service (Loyalty Status Co) operates statusmatch.com and partners with specific airlines and hotels. They process your application for a fee. **The matches are real.** The trade-off is cash-for-status — only worth it if the perks for your travel exceed the fee.

| Program | US Fee Range (approx) | Lifetime Restriction |
|---------|----------------------|---------------------|
| Flying Blue (Air France/KLM) | USD $99-$199 | **Once per lifetime** |
| Lufthansa Miles & More | EUR €99 (free for HON Circle, Club Plus, Club Premium) | Once per promotion |
| Etihad Guest | Region-tiered, varies | Once per promotion |
| Air Canada Aeroplan | varies; Aeroplan Visa cardholders may be discounted | Once per promotion |
| Frontier | varies | Per promotion |
| Spirit Free Spirit | varies | Per promotion |
| Emirates Skywards | varies | Per promotion |
| Vietnam Airlines, Royal Jordanian, Air Astana, Star Alliance multi (Singapore, Swiss, Thai, TAP, Turkish, etc.) | varies | Per promotion |
| citizenM, GHA Discovery (hotels) | varies | Per promotion |

**Always check the destination subdomain's FAQ for current fees** (e.g., `flyingblue.statusmatch.com/faq`). Fees vary by source country and target tier.

For full details, see `paid_concierge` section of `data/status-match.json`.

### Path 3: Card-Granted Renewable Status

For mid-tier hotel status (Gold) and a few other tiers, holding a credit card grants the status automatically. This is **renewable for the life of the card** — no lifetime restriction, no challenge to complete.

| Card | Annual Fee | Status Granted |
|------|-----------|----------------|
| Amex Platinum / Business Platinum | $695 | Hilton Gold + Marriott Gold |
| Hilton Aspire | $550 | Hilton Diamond |
| Hilton Surpass | $150 | Hilton Gold (Diamond requires $40K spend) |
| World of Hyatt Card (Chase) | $95 | Hyatt Discoverist |
| Marriott Bonvoy Brilliant (Amex) | $650 | Marriott Platinum Elite |
| IHG One Rewards Premier (Chase) | $99 | IHG Platinum Elite |

**Decision rule:** if a credit card grants the tier you want and you'd hold the card anyway for other benefits, that beats a one-time match every time. Status match is best for tiers no card grants (most airline tiers; hotel Diamond/Titanium without spend gating).

For full details, see `card_based_status` section of `data/status-match.json`.

## Workflow

### Step 1: Identify what status the user actually wants

Ask if not already clear:
- Which program (AA, United, Hyatt, Marriott, etc.)?
- What tier (mid-tier benefits like Gold/Silver are very different from top-tier benefits like Platinum/Diamond/1K)?
- What's their current status they'd be matching FROM?

### Step 2: Check Path 3 first (card-based)

Query `card_based_status` in `data/status-match.json`. If a card already grants the equivalent tier and the user holds (or would hold) that card, recommend that path. **No status match needed.**

### Step 3: Check Path 1 (free direct match)

If no card grants it, query `direct_matches.airlines` or `direct_matches.hotels` for the destination program. Pull the lifetime restriction and challenge requirements.

**Critical: explicitly tell the user the lifetime restriction.** Example:

> "Alaska Atmos status match is **once per lifetime**. Their terms quote: 'one status match for the lifetime of their account.' If you don't have flying coming up that uses this status before Q4, hold off. Once you submit, you can never do this again."

### Step 4: If no free path exists, check Path 2 (paid concierge)

Query `paid_concierge.programs`. Pull the fee for the user's region and the lifetime restriction.

Compute whether the fee is worth it:

```
fee_in_usd = ... (from data file)
status_value_per_year = (lounge access cash value) + (free bag fees saved on N flights) + (upgrade probability * upgrade value) + (better redemption visibility)
break_even_years = fee_in_usd / status_value_per_year
```

If break-even is under 1 year of typical travel, recommend. If over 2-3 years (and the match isn't lifetime), reconsider.

### Step 5: Cross-check via community database

For grants/denials in the past 6 months, point at [statusmatcher.com](https://statusmatcher.com/). Useful for confirming the program is currently accepting matches and what proof is being accepted.

## Output Format

**Always use markdown tables.** When recommending a match, structure as:

| Field | Value |
|-------|-------|
| Program | Alaska Atmos Gold |
| Path | Direct Free Match |
| Initial validity | 90 days |
| Challenge | 10,000 base points on Alaska/Hawaiian flights in 90 days |
| Fee | Free |
| **Lifetime restriction** | **ONCE PER LIFETIME** |
| Source verified | Alaska primary source |

After the table, give the verdict:

> **Recommend / Hold / Skip.** Reasoning: ...

When the user is on the fence, surface the key question: "do you have flying/staying coming up in the next 6-12 months that uses this status?" If yes, go. If no, the match is worth more later.

## Useful jq Queries

```bash
# All programs that allow free direct matches
jq '.direct_matches.airlines | to_entries[] | select(.value.fee == "free") | {program: .value.program, lifetime: .value.lifetime_warning}' data/status-match.json

# All paid concierge programs with US fees
jq '.paid_concierge.programs | to_entries[] | {program: .value.program, us_fee: (.value.fees_by_region.us // .value.fees_summary // null)}' data/status-match.json

# All cards that grant hotel status
jq '.card_based_status | to_entries[] | select(.value.renewable_status != null) | {card: .value.card, annual_fee: .value.annual_fee_usd, status: [.value.renewable_status[] | .program + " " + .tier]}' data/status-match.json

# All ONCE PER LIFETIME programs (never miss this warning)
jq '[.direct_matches.airlines, .direct_matches.hotels, .paid_concierge.programs] | add | to_entries[] | select((.value.lifetime_warning // "") | test("LIFETIME"; "i")) | {program: .value.program, warning: .value.lifetime_warning, detail: .value.lifetime_warning_detail}' data/status-match.json
```

## Important Caveats

- **Recent activity proof.** Most matches require proof of current status (status card, activity within last 12 months). Lifetime/promotional/transferred status holders are typically NOT eligible to match FROM (you can't use Lifetime Marriott Platinum to match into Hilton Diamond).

- **Match into the highest tier you qualify for at time of application.** Several programs (Flying Blue specifically) cap your match to the tier you have when applying — you can't upgrade later if your source-program status improves.

- **Hotel matches usually require a "challenge."** A small number of paid stays in 90 days. Award stays, points stays, and OTA-booked stays typically don't count. Direct booking only.

- **Airline matches often require revenue spending.** PQP/MQD requirements during the trial period. Award flights and bonus points don't count.

- **Statusmatch.com is legitimate.** Some users mistake the paid concierge for a scam. It is not. Loyalty Status Co operates with formal partnerships with airlines/hotels. The matches granted are real status that works directly with the program afterward. The fee is the catch, not the legitimacy.

- **Apply timing matters.** Status earned through a match in late summer (post-July 1) often lasts 18+ months because it counts toward both the current and next program year. This is the highest-value timing for most airlines.

## Cross-References

- [`points-valuations`](../points-valuations/SKILL.md) — when computing whether elite status changes the CPP math (lounge value, upgrade probability, free bag fees saved)
- [`booking-guidance`](../booking-guidance/SKILL.md) — once you have status, how to actually use it for booking
- [`alliances`](../alliances/SKILL.md) — alliance benefits propagate; matched into oneworld Sapphire via Atmos Gold gets you sapphire benefits across all oneworld carriers
- [`partner-awards`](../partner-awards/SKILL.md) — status sometimes affects which partner awards are bookable through which program
- [`stopovers`](../stopovers/SKILL.md) — elite status sometimes unlocks better stopover treatment on certain programs
- [`award-holds`](../award-holds/SKILL.md) — some programs grant longer hold windows to elite members

## Source Hierarchy (Per Research Integrity Protocol)

1. **Airline/hotel program's own published terms** — primary source for direct matches (aa.com, delta.com, alaskaair.com, etc.)
2. **statusmatch.com FAQ pages** — primary source for paid concierge fees and rules (subdomain-specific FAQs)
3. **Frequent Miler, Upgraded Points, OMAAT** — secondary sources for landscape, current promos, decision-making frameworks
4. **statusmatcher.com community database** — verification of recent grants/denials, current acceptance patterns
5. **Reddit /r/awardtravel** — most current real-world reports

When sources disagree, primary sources win. When official terms are silent on lifetime restrictions, default to "treat as once per program cycle" and flag UNVERIFIED.

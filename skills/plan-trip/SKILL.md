---
name: plan-trip
description: Guided trip planning workflow. Asks destination, dates, travelers, class, and flexibility, then runs parallel flight/hotel search with cpp math and booking plan.
disable-model-invocation: true
category: orchestration
summary: Guided trip planner. The hero command for the toolkit.
license: MIT
---

# Plan Trip Skill

The user invoked this skill explicitly. Run a guided trip planning workflow that produces a concrete, opinionated recommendation with cents-per-point math, transfer paths, and a booking plan.

## How to run this

If the user already gave details in their prompt arguments, use those. Otherwise, ask in this order, one question at a time. Don't fire all the questions at once.

1. **Where?** Destination(s). Accept regions ("Scandinavia"), cities ("Tokyo"), or specific airports.
2. **When?** Departure month or date range. Note flexibility: "exact dates" vs "any week in March" matters a lot for award availability.
3. **Who?** Number of travelers, ages if children/infants. The toolkit supports infant pricing and seat configurations.
4. **What class?** Economy / premium economy / business / first. Default to economy if unstated.
5. **Trip length?** Number of nights at destination if applicable.
6. **Points or cash?** Three valid answers: "best of both" (default), "points only" (treat cash as last resort), "cash only" (skip award search).

After question 6, confirm the plan back to the user in one sentence and start the workflow.

## The workflow

Once you have the inputs:

1. **Load lessons-learned** first. Non-optional. Other skills depend on it.
2. **Load flight-search-strategy** for the canonical parallel search plan.
3. **Pull balances** via the awardwallet skill if the user's intent is points or "best of both" AND if balances aren't already in this session's context. Skip the pull if you already know them.
4. **Run cash search in parallel** via duffel, ignav, google-flights, and the relevant free MCPs (Skiplagged, Kiwi).
5. **Run award search in parallel** via seats-aero across ALL programs (never filter to one program upfront — see lessons-learned).
6. **Cross-reference** with transfer-partners and transfer-bonuses to find the cheapest currency you actually have.
7. **Apply points-valuations** to compute cents-per-point on each award option.
8. **Surface anything from award-sweet-spots** that matches this route.
9. **Check stopovers** if the destination involves a connection. Multi-city trips might unlock "two destinations for the price of one" via Aeroplan, Alaska, or Flying Blue.
10. **Show the math** in a markdown table. One row per option, ranked. Columns: program, miles cost, cash co-pay, total $ value, cpp, hold-before-transfer rule, recommendation.
11. **Pick a winner** with one-sentence reasoning.
12. **Show booking next steps** via booking-guidance: which program to call, hold rules, transfer timing, phone numbers if needed.

## Hotels and ground transit

If the trip is more than just flights, mention these as available next steps in your closing summary (not as a question):
- Hotels via compare-hotels (FHR/THC/Edit/Booking/Trivago/Airbnb/TaW)
- Stopover side trips via stopovers + the relevant transit skill (scandinavia-transit, etc.)
- Atlas Obscura suggestions for unique places at the destination

Don't dump all of these at once. Lead with the flight recommendation. Mention hotels/activities as concrete follow-up actions the user can ask for next.

## Output style

- Markdown tables for results
- Bold the winning option
- Always show cpp on award redemptions
- Cite the source skill for each piece of data ("via seats-aero", "via awardwallet")
- End with a "Next steps" section listing concrete follow-up commands the user can issue. Examples: "Next steps: I can check specific dates around X, search hotels at Y, look up sweet-spot redemptions you're not using." This must be a declarative statement, NOT a question. Don't write "Want me to..." or "Should I..." (the system prompt's PRE-OUTPUT GATE bans those patterns).

## Don't do this

- Don't dump 12 options. Pick 3-5 and rank.
- Don't assume the user has every API key. If a key is missing, say so and tell them what's still searchable. Cash flights work without any keys at all.
- Don't transfer points speculatively. The booking-guidance skill enforces "hold before transfer" rules. Respect them.

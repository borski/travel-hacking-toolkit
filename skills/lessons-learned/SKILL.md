---
name: lessons-learned
description: Hard-won knowledge from real travel-hacking searches. Captures specific failure modes, source-accuracy rankings, Southwest and Companion Pass nuances, small-market caveats, Duffel limitations, and the mandatory Seats.aero workflow that prevents the most common mistake (filtering too early). Load before any award flight search to avoid repeating documented mistakes, when results seem off, or when working with sources that have known quirks. Triggers on "Seats.aero workflow", "search all sources", "Southwest is special", "Companion Pass math", "small market", "Duffel limits", "Kiwi garbage", "Skiplagged blocked", "data files vs reality", "lessons learned", or any moment that calls for institutional knowledge.
---

# Lessons Learned

Hard-won knowledge from actual searches. Reference these before making the same mistakes.

## Seats.aero: Search ALL Sources, Show ALL Results

When searching Seats.aero, **NEVER filter by source on the initial search.** Always pull ALL programs first.

### The Mandatory Workflow

For any route:

1. **Search Seats.aero with NO source filter.** Pull ALL programs. Show full results sorted by cheapest.
2. **For EVERY program in results, trace the full reachability chain:**
   a. Direct balance? (Check AwardWallet if connected)
   b. Transfer path? (Check `data/transfer-partners.json` for EVERY currency: Amex MR, Chase UR, Bilt, Capital One)
   c. Alliance chain? Identify the operating airline's alliance (`data/alliances.json`), then find ALL programs in that alliance or with bilateral partnerships (`data/partner-awards.json`), then check which of THOSE programs are reachable via transfer.
   d. Cross-alliance? Check `data/partner-awards.json` `cross_alliance_highlights` and bilateral partners.
3. **For reachable programs with NO cached Seats.aero data,** check the program's website directly (airfrance.com, united.com, etc.)
4. **Present the COMPLETE picture:** every option, reachable or not, with the transfer chain spelled out.
5. **Only THEN compare award vs cash.**

### Common Failure Mode

Seeing an airline in results, checking one or two obvious programs, declaring awards "unreachable" or "bad value," and recommending cash. You MUST trace every possible chain through alliances and bilateral partnerships. If the operating airline is in an alliance, EVERY program that books that alliance is a potential path.

### "No Cached Availability" Is Not the Final Word

It means Seats.aero hasn't scraped it recently. When a reachable program shows no cached results, search the airline's website directly before declaring awards dead.

## Never Trust Data Files Over Reality

Data files are reference material, not gospel. Airline partnerships change constantly. When a user says a booking path works that your data doesn't show, verify on the actual booking website FIRST before pushing back. The website is the source of truth. Your files are a cache. If the data file disagrees with reality, update the data file.

## Source Accuracy Hierarchy

**Duffel > Airline website > SerpAPI > Skiplagged/Kiwi**

1. **Duffel returns real GDS prices per fare class.** These are bookable. Tested: Duffel showed $271 basic / $325 main. SerpAPI showed $541 for the same flight. The gap was consistent across multiple itineraries.
2. **SerpAPI (Google Flights) inflates prices.** Google Flights often shows "main cabin" or bundled fares, not the cheapest bookable fare class. Useful for Google Hotels and destination discovery, but do not trust it as the sole source for flight cash prices.
3. **Kiwi returns garbage on small markets.** Filter hard or skip Kiwi for domestic routes to small airports.

## Southwest Is Special

1. **Southwest is NOT in any GDS.** Duffel, Skiplagged, Kiwi, and Seats.aero will never return SW flights. The only sources are: the Southwest website directly or user-provided screenshots.
2. **SerpAPI does return SW prices** but they're often inflated like all SerpAPI flight prices. Treat as directional only.
3. **SW Companion Pass math is different from everything else.** With CP, you buy ONE ticket and the companion flies free. The cash comparison is the Choice fare for one ticket (not two Basic fares). Points comparison: total points covers both travelers. This changes cpp calculations significantly.
4. **Cash SW flights require Choice fare (or higher) for the companion to fly free.** Wanna Get Away (Basic) does NOT qualify. Critical detail.
5. **SW points pricing must come from southwest.com.** No third-party source has it.

## Companion Pass CPP Math

The correct formula when Companion Pass is in play:

```
Total cash value = choice_fare_cash × 2 passengers
CPP = total_cash_value / total_points × 100
```

One ticket's worth of points buys travel for two people. Always frame it as "points bought $X of travel for 2 people."

## Small Market Airports

Small airports have limited award availability. Seats.aero cached data will be sparse. When searching small markets:

1. **Duffel for cash prices** (works fine, GDS has the inventory)
2. **Don't bother with Seats.aero cached search** (data too sparse)
3. **Check airline-specific award pricing** via the program's website if needed
4. **SW Companion Pass often wins** on small domestic markets because the points cost is low and CP doubles the value

## Layover and Time Preferences

Ask the user for their preferences on the first search. Key questions:

- Minimum and maximum layover time
- Earliest acceptable departure time
- Red-eye tolerance
- Lounge access (changes how long layovers feel)

Store their answers and apply to all subsequent searches in the session.

## Duffel Limitations

- **No Southwest.** SW is not in any GDS. Period.
- **No award pricing.** Duffel shows cash fares only. Use Seats.aero for award availability.
- **Offers expire in 15-30 minutes.** Don't cache Duffel results across sessions.
- **60 requests per 60 seconds rate limit.** Parallel searches are fine but don't go crazy.
- **Returns multiple fare classes for the same flight.** This is a feature. You'll see basic economy at one price and main cabin at another for the same routing. Use the cheapest bookable class for cpp comparison unless the user specifies a fare preference.
</content>
</invoke>
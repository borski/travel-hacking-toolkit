---
name: bilt
description: Search Bilt Rewards travel portal for cash and Bilt Points pricing on flights. Flight search is a public REST API with no auth. Hotel search now requires a login and is unavailable, including the Home Away From Home (HaFH) data.
category: portals
summary: Bilt Rewards travel portal. Flight search works unauthenticated and returns Southwest. 1.25 cpp on Bilt Points. Hotel endpoints went behind auth in Nov 2026.
api_key: None for flights. Hotels require an authenticated session (not supported).
allowed-tools: Bash(curl *), Bash(jq *)
---

# Bilt Travel Portal Search

Search [Bilt Rewards](https://www.bilt.com) travel portal via its REST API. Returns both cash prices in USD and Bilt Points cost.

## ⚠️ Status (verified Nov 5, 2026)

| Endpoint | Status |
|---|---|
| `/public/travel/flights/search` | ✅ **Works, no auth.** Returns Southwest. |
| `/public/travel/hotels/*` | ❌ **401 `AUTHENTICATION_REQUIRED`.** |
| `/public/travel/cars/auto-complete` | ✅ Still public (autocomplete only) |

**The hotel endpoints are gone.** Every `/public/travel/hotels/*` path now returns:

```json
{"error":{"source":"travel-svc","code":"AUTHENTICATION_REQUIRED","message":"Authentication is required for this request."}}
```

This is not a header, User-Agent, or Origin problem. It was checked with browser-like headers and it still 401s. Reading bilt.com's own JS bundles confirms the cause: the hotel endpoints are now declared `auth:!0` (auth required) and have moved off the `/public/` prefix to `/travel/hotels/search` and `/travel/hotels/auto-complete`. Only `/public/travel/cars/auto-complete` is still declared `auth:!1`.

**So there is no unauthenticated path to Bilt hotel rates, HaFH flags, or hotel points pricing.** The hotel sections below are kept for reference and for the day Bilt reopens them, but they will fail today. For hotel work use [premium-hotels](../premium-hotels/SKILL.md), [serpapi](../serpapi/SKILL.md), or Trivago/LiteAPI instead, and get Bilt hotel pricing from a screenshot of the app.

## Important: Bilt is Whitelabel Duffel

Bilt's travel search is built directly on top of [Duffel](https://duffel.com). All evidence points to a complete white-label arrangement, not a partial integration:

- Flight offer IDs are `off_XXX`, slices `sli_XXX`, segments `seg_XXX`, aircraft `arc_XXX`, airlines `arl_XXX`. All Duffel ID patterns.
- Carrier and aircraft logos served from `assets.duffel.com`.
- Hotel loyalty program logos served from `assets.duffel.com/img/stays/loyalty-programmes`. So hotels are Duffel Stays.
- JWT `organisation_id: org_0000AaALZyFQ...` is a Duffel auth pattern.
- Field names match Duffel exactly: `marketingCarrier`, `operatingCarrier`, `cabinClassMarketingName`, `fareBasisCode`, `isNDC`, `ndcRedirectUrl`, `totalEmissionsKg`, `slices[].segments[].passengers[].baggages[]`.

**What Bilt adds on top of Duffel:**
- `totalPointsRequired` (Bilt Points cost at the fixed 1.25 cpp portal rate)
- `isHafh` (Home Away From Home flag on hotels)
- `loyaltyProgram.reference` (brand affiliation surfacing for hotels)
- A few Bilt-specific filter fields

**What this means for the toolkit:**
- For **cash-only flight searches**, prefer the [duffel skill](../duffel/SKILL.md). It uses an authenticated Duffel API key, returns the same data faster, and supports more parameters (multi-city, time windows, max connections, supplier_timeout tuning).
- For **Bilt Points context** (CPP, comparing portal cost to award alternatives, Bilt redemption math), use this skill. The points pricing is exclusive to Bilt's endpoint.
- For **Home Away From Home property research**, use this skill. The `isHafh` flag is Bilt-specific and surfaces the $300+ benefits properties.

## Why It Matters

- **1.25 cpp** standard redemption rate on Bilt Points (1 USD = 80 points). One of the better fixed portal rates.
- **Home Away From Home (HaFH)** is Bilt's premium hotel program. Gold and Platinum members get $300+ in benefits per stay (daily breakfast for two, $100 property credit, room upgrades on arrival, early check-in / late check-out, dedicated Virtuoso Travel Advisor).
- **Bilt Points transfer 1:1** to Hyatt, Marriott, Hilton, IHG, United, AA, Air Canada Aeroplan, Air France/KLM, Virgin Atlantic, Cathay, Turkish, and more — so this portal is a 1.25 cpp "bottom-of-the-barrel" comparison point for transfer-partner award searches.
- **Flights are Duffel-backed.** Same response shape as the [duffel skill](../duffel/SKILL.md). Same airlines, same fare classes, same segment structure.
- **Bilt returns Southwest. Your own Duffel key probably does not.** See the Southwest section below. This is currently the single best reason to call Bilt for a cash flight search.
- **No auth needed for flight search.** Browser automation, login, 2FA all unnecessary. Just curl. (Hotels are a different story, see Status above.)

## When to Use

- Comparing Bilt portal pricing to seats.aero awards
- Computing CPP for Bilt Points redemptions
- Finding HaFH properties for Bilt Gold/Platinum benefit stacking
- Sanity-checking cash vs points decision when Bilt Points are involved
- As a "redemption floor" reference: if award flights cost more than the portal price, the portal wins

## When NOT to Use

- **Any hotel search.** The endpoints are behind auth. See Status above.
- **Booking flights or hotels.** This skill finds offers only. Booking requires login + Bilt Mastercard. Out of scope.
- **Award flight search.** Use [seats-aero](../seats-aero/SKILL.md) for award availability across loyalty programs.

Note the old guidance here said to prefer [duffel](../duffel/SKILL.md) for cash-only flight searches. That is no longer automatic: Duffel and Bilt return different carrier sets even though Bilt is whitelabel-Duffel. Run both.

## Bilt Points Valuation

| Metric | Value | Notes |
|--------|-------|-------|
| Portal redemption rate | 1.25 cpp | $1 = 80 points (standard, fixed) |
| Cash → points formula | `points = round(usd / 0.0125)` | Reverse-derived from observed responses |
| TPG valuation (transfers) | 2.05 cpp | When transferred to optimal partners |

**Decision rule:** If transferring Bilt Points to a partner program would yield more than 1.25 cpp, transfer. If not, use the portal.

## API Base

```
https://api.biltrewards.com/public/travel
```

Standard JSON responses. Flight endpoints need no API key. Hotel endpoints return 401 (see Status above).

## Hotel Search (❌ BROKEN, 401s as of Nov 5, 2026)

Everything in this section returns `AUTHENTICATION_REQUIRED`. Kept for reference only.

### Step 1: Look up location searchId

```bash
curl -s "https://api.biltrewards.com/public/travel/hotels/auto-complete?query=New+York" \
  | jq '.searchResults[0].locationSuggestion'
```

Returns:
```json
{
  "name": "New York",
  "country": {"name": "USA", "code": "US"},
  "region": {"name": "NY", "code": null},
  "searchId": "ChIJOwg_06VPwokRYv534QaPC8g"
}
```

The `searchId` is a Google Places ID. You can also pass `searchType: HOTEL_SEARCH` results to search a specific property.

### Step 2: Search hotels

```bash
curl -s "https://api.biltrewards.com/public/travel/hotels/search" \
  --get \
  --data-urlencode "checkInDate=2026-08-15" \
  --data-urlencode "checkOutDate=2026-08-18" \
  --data-urlencode "numGuestAdults=2" \
  --data-urlencode "numRooms=1" \
  --data-urlencode "searchId=ChIJOwg_06VPwokRYv534QaPC8g" \
  | jq '.hotelResults | length'
```

Returns 100 to 200 hotels typically. Synchronous, no polling needed.

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `checkInDate` | YYYY-MM-DD | Required |
| `checkOutDate` | YYYY-MM-DD | Required |
| `numGuestAdults` | int | Required, 1+ |
| `numRooms` | int | Required, 1+ |
| `searchId` | string | Google Places ID from auto-complete |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `childrenAges` | csv ints | E.g. `5,8` for two children aged 5 and 8 |
| `hotelId` | string | Search a specific `acc_XXX` property |

### Hotel response shape

```
{
  stayDetails: { checkInDate, checkOutDate, numRooms, numGuestAdults, childrenAges },
  hotelResults: [
    {
      id: "acc_XXX",
      name: "Park Hyatt New York",
      rating: 5,                      // star rating
      description: "...",
      isHafh: true,                   // Home Away From Home flag
      loyaltyProgram: {               // brand affiliation, if any
        name: "World of Hyatt",
        reference: "world_of_hyatt",
        logoUrl: "..."
      },
      address: { street, city, stateProvince, countryCode, postalCode },
      geolocation: { latitude, longitude },
      amenities: [{ description, category }, ...],
      images: [{ url }, ...],
      lowestRateDetails: {
        usdAmounts: { total },        // cash total in USD
        points: 319681,               // Bilt Points cost
        dueAtHotelAmount, dueAtHotelCurrency,
        ...
      }
    }
  ],
  filterDetails: { ... }
}
```

### Hotel detail (room rates)

```bash
curl -s "https://api.biltrewards.com/public/travel/hotels/acc_0000AWPt2s3aNc1GpC5bmU?checkInDate=2026-08-15&checkOutDate=2026-08-18&numGuestAdults=2&numRooms=1" \
  | jq '.hotelDetails | {name, isHafh, rates: .roomTypes[0]}'
```

Returns `hotelDetails` with full property info plus `roomTypes` containing each available rate.

### Useful jq filters

```bash
# Top 10 cheapest hotels with HaFH flag and CPP rounded to 2 decimals
curl -s "$URL" | jq '
  [.hotelResults[]
   | select(.lowestRateDetails.usdAmounts.total != null)
   | {name, isHafh, rating,
      cash: .lowestRateDetails.usdAmounts.total,
      points: .lowestRateDetails.points,
      cpp: (((.lowestRateDetails.usdAmounts.total / .lowestRateDetails.points) * 100) * 100 | round / 100),
      brand: .loyaltyProgram.name}]
  | sort_by(.cash) | .[0:10]'

# Only HaFH properties (worth $300+ benefits if Gold/Platinum)
curl -s "$URL" | jq '
  [.hotelResults[]
   | select(.isHafh == true)
   | {name, rating, cash: .lowestRateDetails.usdAmounts.total, points: .lowestRateDetails.points}]
  | sort_by(.cash)'
```

## Flight Search (✅ works, no auth)

### ⚠️ Bilt returns Southwest. Run it on every domestic search.

**VERIFIED Nov 5, 2026, SJC→SAN 2026-11-13.** Bilt returned **418 Southwest offers** across all four fare brands (Basic, Choice, Choice Preferred, Choice Extra), `isNDC: false`, with real fare basis codes. The **same query against a personal Duffel API key returned zero WN offers.**

Both are Duffel. Southwest content is enabled per Duffel organisation, and Bilt's org has it. So "Southwest is not in any GDS or API" is no longer true in general, and the right statement is: *your* Duffel key may not have Southwest, but Bilt's does.

**Spot-check against southwest.com:** every SJC→SAN nonstop matched to the cent. Bilt $238.40 / $268.40 / $293.40 / $308.40 against southwest.com's rounded-up $239 / $269 / $294 / $309. Bilt is quoting the real fares, not an inflated resale.

What this does and does not replace:
- ✅ Fast, keyless cash fares for all four SW fare brands. No Patchright, no Docker, no 20-second scrape.
- ❌ **No points pricing for Southwest.** `totalPointsRequired` is the *Bilt* points cost at 1.25 cpp, not Rapid Rewards. For RR points and Companion Pass math you still need the [southwest](../southwest/SKILL.md) skill.

### ⚠️ Bilt silently expands origin and destination to the whole metro area

**This will burn you.** A search for `origin=SJC` also returns SFO and OAK departures, with no flag on the offer saying so. On the test search the cheapest "SJC" Southwest fare was $188.40, which turned out to be **SFO→SAN**, while actual SJC was $238.40. That is a $50 difference that silently answers a different question than the one asked.

**Always filter on the segment's own IATA code before reporting a price:**

```bash
jq '[.data.offers[] | select(.slices[0].segments[0].origin.iataCode == "SJC")]' results.json
```

Treat the extra airports as a feature once you know it is happening. It is a free nearby-airport comparison, but it has to be reported as "SFO is $50 cheaper than SJC," never as "SJC is $188."

### Step 1: Submit search

```bash
curl -s "https://api.biltrewards.com/public/travel/flights/search" \
  --get \
  --data-urlencode "departureDate=2026-08-15" \
  --data-urlencode "returnDate=2026-08-22" \
  --data-urlencode "origin=SFO" \
  --data-urlencode "destination=NRT" \
  --data-urlencode "adults=1" \
  --data-urlencode "cabinClass=business"
```

Returns:
```json
{
  "data": {
    "id": "orq_0000B5mQkPhO7VxuWClhZI",
    "totalBatches": 35,
    "remainingBatches": 35,
    "createdAt": "...",
    "clientKey": "..."
  }
}
```

### Step 2: Poll for results

```bash
curl -s "https://api.biltrewards.com/public/travel/flights/search/$ID"
```

`remainingBatches` ticks down to 0 over 5 to 15 seconds. The response includes the `offers` array as soon as the first batch returns. Poll every 3 to 5 seconds until `remainingBatches == 0` for the complete result set.

```bash
# Polling loop
for i in 1 2 3 4 5; do
  RESP=$(curl -s "https://api.biltrewards.com/public/travel/flights/search/$ID")
  REMAINING=$(echo "$RESP" | jq -r '.data.remainingBatches')
  echo "Poll $i: $REMAINING batches remaining"
  [ "$REMAINING" = "0" ] && break
  sleep 4
done
echo "$RESP" | jq '.data.offers | length'
```

### Required parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `departureDate` | YYYY-MM-DD | Required |
| `origin` | IATA airport code | Required |
| `destination` | IATA airport code | Required |
| `adults` | int | Required, 1+ |

### Optional parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `returnDate` | YYYY-MM-DD | Round-trip, omit for one-way |
| `cabinClass` | string | `economy`, `premium_economy`, `business`, `first` |
| `children` | int | Number of children (with `childrenAges`) |
| `infants` | int | Lap infants |

### Flight response shape

Same as Duffel (Bilt is whitelabel-Duffel). Each offer:

```
{
  id: "off_XXX",
  totalAmount: 1606.60,        // cash total
  totalCurrency: "USD",
  baseAmount: 1132.00,
  taxAmount: 474.60,
  totalPointsRequired: 128528,  // Bilt Points cost
  totalPointsRequiredWithCredits: null,  // applicable airline credits, if any
  expiresAt: "2026-04-29T08:51:40Z",
  owner: {
    name: "KLM", iataCode: "KL", logoSymbolUrl, conditionsOfCarriageUrl
  },
  isNDC: false,
  passengers: [{ type, loyaltyProgrammeAccounts, id }],
  conditions: { refundBeforeDeparture, changeBeforeDeparture },
  slices: [
    {
      id: "sli_XXX",
      duration: "P1DT4H40M",   // ISO 8601 duration
      fareBrandName: "Standard",
      origin: { iataCode, name, cityName, timeZone },
      destination: { iataCode, name, cityName, timeZone },
      segments: [
        {
          id, duration, departingAt, arrivingAt,
          origin: {...}, destination: {...},
          marketingCarrier: { name, iataCode, ... },
          operatingCarrier: { name, iataCode, ... },
          marketingCarrierFlightNumber: "0606",
          aircraft: { name: "Boeing 787-10", iataCode: "781" },
          stops: [],
          passengers: [
            {
              passengerId,
              fareBasisCode: "THA79NMP",
              cabinClassMarketingName: "ECONOMY",
              baggages: [{ type: "checked"|"carry_on", quantity }]
            }
          ]
        }
      ]
    }
  ]
}
```

### Useful jq filters

```bash
# Top 5 cheapest offers with CPP calculation (rounded to 2 decimals)
echo "$RESP" | jq '
  [.data.offers[]
   | {airline: .owner.name,
      cash: .totalAmount,
      points: .totalPointsRequired,
      cpp: (((.totalAmount / .totalPointsRequired) * 100) * 100 | round / 100),
      stops: ([.slices[].segments | length] | map(. - 1)),
      route: ([.slices[] | (.origin.iataCode + " -> " + .destination.iataCode)])}]
  | sort_by(.cash) | .[0:5]'

# Group by airline, show cheapest per carrier
echo "$RESP" | jq '
  [.data.offers[]
   | {airline: .owner.name, cash: .totalAmount, points: .totalPointsRequired}]
  | group_by(.airline)
  | map({airline: .[0].airline, cheapest: (min_by(.cash))})'

# Filter to nonstop only
echo "$RESP" | jq '
  [.data.offers[]
   | select(([.slices[].segments | length] | add) == ([.slices | length]))
   | {airline: .owner.name, cash: .totalAmount, points: .totalPointsRequired}]'
```

## Output Format

**Always use markdown tables.** When showing both flights and hotels, separate tables.

### Hotels

| Hotel | Stars | HaFH | Brand | Cash | Points | CPP |
|-------|-------|------|-------|------|--------|-----|
| Park Hyatt New York | 5 | yes | Hyatt | $3,996 | 319,681 | 1.25 |
| The St. Regis NY | 5 | no | Marriott | $4,210 | 336,800 | 1.25 |

### Flights (one-way SFO to NRT)

| Airline | Stops | Duration | Cash | Points | CPP |
|---------|-------|----------|------|--------|-----|
| Air Canada | 1 (YVR) | 14h 5m | $871 | 69,720 | 1.25 |
| KLM | 1 (AMS) | 28h 40m | $1,607 | 128,528 | 1.25 |

After tables: highlight the cheapest, flag any HaFH stays the user qualifies for (Bilt Gold or Platinum status required), and call out anything where CPP is wildly off (would indicate a special promo or a points-only "boost" rate).

## Comparison Workflow

For a complete trip cost analysis:

1. **Bilt Points balance** via [awardwallet](../awardwallet/SKILL.md). Note: Bilt is in AwardWallet.
2. **Award alternatives** via [seats-aero](../seats-aero/SKILL.md). Compare to portal price at 1.25 cpp.
3. **Transfer partners** via [transfer-partners](../transfer-partners/SKILL.md). If a partner program redeems Bilt Points at >1.25 cpp, transfer instead of using portal.
4. **Other portals** via [chase-travel](../chase-travel/SKILL.md) (dynamic Points Boost on CSR/CSP, ~1.5-2.0 cpp on select bookings, not a guaranteed floor) and [amex-travel](../amex-travel/SKILL.md) (~1.0 cpp on flights). Pull actual portal quotes, not assumed rates.
5. **HaFH benefits** add ~$300+ in value per stay if the user has Bilt Gold or Platinum status. Apply this when computing effective rate. **Ask for a screenshot**, since the API no longer returns the HaFH flag.

## Important Notes

- **Filter offers by segment IATA code.** Bilt expands to nearby airports without saying so. See the metro-expansion warning in Flight Search.
- **Southwest is in Bilt's results but not necessarily in your own Duffel key's.** Run both on domestic routes.
- **`totalPointsRequired` is always Bilt Points at 1.25 cpp.** It is never the airline's own award price. Do not present it as Rapid Rewards, AAdvantage, or anything else.
- **`isHafh: true`** identified Home Away From Home properties, roughly 200 to 300 luxury hotels worldwide. No longer reachable, the hotel endpoints are behind auth.
- **Bilt has no transfer fees.** Unlike some portal-points conversions, Bilt → partner transfers are 1:1 instant.
- **Booking requires the Bilt card.** Most premium benefits (HaFH, Rent Day points multipliers, status) are gated by holding the Bilt Mastercard.
- **Stellate (`bilt-rewards.stellate.sh`)** is Bilt's CMS endpoint, not a search backend. It serves marketing copy and benefit descriptions.
- **If hotels start working again,** the unauthenticated paths to retry are `/public/travel/hotels/auto-complete` and `/public/travel/hotels/search`. The authenticated replacements are `/travel/hotels/auto-complete` and `/travel/hotels/search`.

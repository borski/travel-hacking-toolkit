---
name: premium-hotels
description: Search Amex Fine Hotels & Resorts (FHR), The Hotel Collection (THC), and Chase Sapphire Reserve Hotel Collection (Chase Edit) properties by city. Compare credits, benefits, and stacking opportunities across programs.
category: hotels
summary: Search 4,659 Amex FHR/THC + Chase Edit hotels by city. Stacking opportunities.
api_key: None (local data)
---

# Premium Hotel Programs

Search 4,659 premium hotel properties across three credit card programs. Find which hotels offer complimentary benefits, compare credits, and identify stacking opportunities where a hotel appears in multiple programs.

**No API key needed.** All data is local JSON files in `data/`.

## When to Use

- User asks "what FHR hotels are in Stockholm?"
- Comparing hotel options for a trip and want to maximize card benefits
- Looking for hotels where Amex FHR + Chase Edit credits stack
- Checking if a specific hotel is in any premium program

## Programs

| Program | Card Required | Key Benefits | Properties |
|---------|--------------|--------------|------------|
| **FHR** (Fine Hotels & Resorts) | Amex Platinum | $600/yr Plat credit (2x $300 semi-annual), $100 property credit, daily breakfast for 2, 12pm checkin, guaranteed 4pm checkout, room upgrade, wifi | 1,807 |
| **THC** (The Hotel Collection) | Amex Platinum | $600/yr Plat credit (2x $300 semi-annual, shared with FHR), $100 property credit, 12pm checkin, room upgrade, late checkout (2-night min) | 1,299 |
| **Chase Edit** (Sapphire Reserve) | Chase Sapphire Reserve | $500/yr statement credit (2x $250), $100 property credit, daily breakfast, wifi, room upgrade, early/late checkout. Select Hotels add $250 one-time 2026 credit + 10x points. | 1,553 |

### Stacking

Hotels in BOTH FHR/THC AND Chase Edit can stack benefits. Book through one program and use the other card's credits separately. Look for hotels that appear in multiple programs. Use [awardhelper.com/csr-hotels](https://www.awardhelper.com/csr-hotels) to find stackable properties.

## Chase Sapphire Reserve Hotel Credits (2026)

**The Edit credit: $500/yr** (two separate $250 credits, usable anytime during the calendar year). Two-night minimum, prepaid through Chase Travel. Each stay also gets the $100 property credit + daily breakfast + room upgrade. Points Boost gives 2cpp when redeeming UR at Edit hotels. **Always compare Chase Travel rates against direct booking.**

**Select Hotels credit: $250 one-time (2026 only).** Prepaid 2+ night stay at: IHG, Minor Hotels, Montage, Omni, Pan Pacific, Pendry, or Virgin Hotels. Booked through Chase Travel. Expires Dec 31, 2026. Earns hotel loyalty points AND elite night credits on the full purchase amount.

**Stacking strategy:** Properties that are both Edit hotels AND one of the 7 Select Hotels brands can trigger BOTH credits on a single stay ($250 Edit + $250 Select = $500 back).

**Budget option:** Use the $250 Select Hotels credit at affordable IHG properties (Holiday Inn, Holiday Inn Express). A 2-night prepaid stay around $250 total gets nearly fully covered by the credit alone.

## Amex Platinum Hotel Credit Mechanics (FHR or THC)

**$600 annual total, split $300 per half-year (Jan-Jun and Jul-Dec).** Use it or lose it, does not roll over. Prepaid bookings through Amex Travel with Platinum or Business Platinum. FHR and THC share the same $600 pool.

- **FHR = 1-night minimum.** THC = 2-night minimum.
- **Credit triggers on booking/prepayment, not stay date.** Book in June for a September trip and the H1 credit still fires.
- **5x MR points still earned** on Amex Travel bookings that trigger the credit.
- **No enrollment needed.** Just book through Amex Travel and pay with your Platinum.
- **Can split across multiple bookings** if a stay costs less than $300 per half.
- **Cancellation = clawback** unless you rebook before the credit expires.
- **Elite status recognition is hit or miss** through Amex Travel. Plug in loyalty numbers anyway.
- **MaxFHR.com** is a great tool for finding the cheapest FHR/THC properties by date and destination.
- **Always compare Amex Travel rates against booking direct.** Portal rates can be higher.

## Searching by City

### FHR and THC (coordinate-based)

FHR and THC properties have lat/lng coordinates. Search by bounding box around a city.

**Find properties near a city** (adjust lat/lng and radius as needed):

```bash
# Stockholm (59.33, 18.07) - search within ~0.15 degrees (~15km)
LAT=59.33; LNG=18.07; R=0.15
jq --argjson lat $LAT --argjson lng $LNG --argjson r $R \
  '[.properties[] | select(
    .coordinates.lat > ($lat - $r) and .coordinates.lat < ($lat + $r) and
    .coordinates.lng > ($lng - $r) and .coordinates.lng < ($lng + $r)
  ) | {name, program, credit}]' data/fhr-properties.json

jq --argjson lat $LAT --argjson lng $LNG --argjson r $R \
  '[.properties[] | select(
    .coordinates.lat > ($lat - $r) and .coordinates.lat < ($lat + $r) and
    .coordinates.lng > ($lng - $r) and .coordinates.lng < ($lng + $r)
  ) | {name, program, credit}]' data/thc-properties.json
```

### Chase Edit (text-based)

Chase Edit properties have text locations, not coordinates. Search by name or location text.

```bash
# Stockholm
jq '[.properties[] | select(
  (.location // "" | test("Stockholm|Sweden"; "i")) or
  (.name // "" | test("Stockholm"; "i"))
) | {name, location}]' data/chase-edit-properties.json
```

### Common City Coordinates

| City | Lat | Lng | Radius |
|------|-----|-----|--------|
| Oslo | 59.91 | 10.75 | 0.15 |
| Bergen | 60.39 | 5.32 | 0.1 |
| Stockholm | 59.33 | 18.07 | 0.15 |
| Copenhagen | 55.68 | 12.57 | 0.15 |
| Paris | 48.86 | 2.35 | 0.15 |
| London | 51.51 | -0.13 | 0.2 |
| Tokyo | 35.68 | 139.76 | 0.2 |
| New York | 40.71 | -74.01 | 0.15 |
| San Francisco | 37.77 | -122.42 | 0.15 |
| Las Vegas | 36.17 | -115.14 | 0.15 |

For cities not listed, use the coordinates from the route context or look up on Google Maps.

## Combined Search (Recommended Workflow)

For any city, run all three searches and combine into one table. Flag properties in multiple programs.

```bash
# Example: Oslo
LAT=59.91; LNG=10.75; R=0.15

# FHR
FHR=$(jq --argjson lat $LAT --argjson lng $LNG --argjson r $R \
  '[.properties[] | select(
    .coordinates.lat > ($lat - $r) and .coordinates.lat < ($lat + $r) and
    .coordinates.lng > ($lng - $r) and .coordinates.lng < ($lng + $r)
  ) | {name, program: "FHR", credit}]' data/fhr-properties.json)

# THC
THC=$(jq --argjson lat $LAT --argjson lng $LNG --argjson r $R \
  '[.properties[] | select(
    .coordinates.lat > ($lat - $r) and .coordinates.lat < ($lat + $r) and
    .coordinates.lng > ($lng - $r) and .coordinates.lng < ($lng + $r)
  ) | {name, program: "THC", credit}]' data/thc-properties.json)

# Chase Edit
CHASE=$(jq '[.properties[] | select(
  (.location // "" | test("Oslo|Norway"; "i")) or
  (.name // "" | test("Oslo"; "i"))
) | {name, program: "Chase Edit", credit: "See Chase portal for current credit"}]' data/chase-edit-properties.json)

# Combine
echo "$FHR" "$THC" "$CHASE" | jq -s 'add | group_by(.name) | map({
  name: .[0].name,
  programs: [.[] | .program] | join(" + "),
  credits: [.[] | select(.credit != null) | .credit] | join(" | "),
  stacking: (length > 1)
}) | sort_by(.name)'
```

## Output Format

**Always use markdown tables.** Flag stacking opportunities.

| Hotel | Programs | Credits | Stacking? |
|-------|----------|---------|-----------|
| The Thief | FHR | US$100 property credit | No |
| Sommerro | FHR + Chase Edit | US$100 property credit | **YES** |
| Amerikalinjen | THC | $100 dining/spa credit (2+ nights) | No |
| Grand Hotel Oslo | Chase Edit | See Chase portal | No |

### After the table

- Flag which hotels appear in multiple programs (stacking opportunity)
- Note the key benefit differences: FHR includes breakfast + upgrade + late checkout. THC is credit only on 2+ nights. Chase Edit varies.
- If booking through FHR or THC, mention the Amex Platinum $600 annual hotel credit (split 2x $300 semi-annual, FHR/THC share the pool)
- If booking through Chase Edit, mention the $500 annual hotel credit (split 2x $250) and whether "Select Hotels" $250 one-time 2026 credit also applies for stacking
- Link to Amex reservation page if available in the data

## Data Sources

- `data/fhr-properties.json` (1,807 properties, coordinates + Amex reservation links + Google Travel price calendar links + credit details)
- `data/thc-properties.json` (1,299 properties, coordinates + Amex reservation links)
- `data/chase-edit-properties.json` (1,553 properties, text locations, 190 tagged `budget_friendly` from "Potentially Cheaper Ones" category)

**Data source:** 美卡指南 (US Card Guide) Google My Maps, maintained by Scott. To refresh, re-pull the KML files:
- FHR/THC: `https://www.google.com/maps/d/kml?mid=1HygPCP9ghtDptTNnpUpd_C507Mq_Fhec&forcekml=1`
- Chase Edit: `https://www.google.com/maps/d/kml?mid=1Ickidw1Z6ACres9EnbM2CmPObYsuijM&forcekml=1`

Property lists change periodically. Always verify current availability on the Amex or Chase booking portal before making decisions.

## Notes

- A hotel can be in both FHR AND THC. This is rare but possible. The data reflects what Amex lists.
- Chase Edit "Select Hotels" are a subset with enhanced benefits (10x points + $250 one-time credit). Not all Chase Edit properties are Select Hotels.
- FHR benefits apply even when paying the standard rate. No special rate needed.
- THC $100 credit requires a minimum 2-night stay.
- Some properties have seasonal availability in these programs.

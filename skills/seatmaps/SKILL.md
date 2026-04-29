---
name: seatmaps
description: Look up aircraft seat maps, cabin dimensions, and seat recommendations via SeatMaps.com and AeroLOPA. Search by flight number or airline+aircraft. Uses agent-browser for data extraction.
category: flights
summary: Aircraft seat maps, cabin dimensions, seat recommendations.
api_key: None (requires agent-browser)
allowed-tools: Bash(agent-browser *)
---

# Seat Maps

Look up aircraft seat maps, cabin dimensions (pitch, width, recline), seat recommendations, and flight reviews. Uses [SeatMaps.com](https://seatmaps.com) (browser automation) as the primary data source and [AeroLOPA](https://www.aerolopa.com/) as a visual complement.

**Requires `agent-browser` CLI.** Install: `npm install -g agent-browser && agent-browser install`

## When to Use

- User wants to know the best seats on a specific flight
- Comparing cabin configurations across aircraft variants
- Checking seat pitch, width, recline for a cabin class
- Identifying seats near galleys, lavatories, or exits
- Verifying which aircraft variant operates a specific route
- Looking up seat map ratings and flight reviews

## When NOT to Use

- **Booking seats.** Find information only. Do not select or purchase seats.
- **Real-time availability.** Seat maps show the aircraft layout, not which seats are currently open.

## Two Sources, Different Strengths

| Feature | SeatMaps.com | AeroLOPA |
|---------|-------------|----------|
| Flight number search | Yes | No |
| Seat recommendations | Yes (color coded) | No (information only) |
| Cabin dimensions | Yes (pitch/width/recline) | Sometimes |
| Window alignment | No | Yes (to-scale drawings) |
| 360° cabin views | Some aircraft | No |
| Seat ratings | Yes (user reviews) | Coming 2026 |
| Aircraft variants | Yes (tabs) | Yes |

**Default workflow:** Search SeatMaps first (data extraction). Link to AeroLOPA for visual window alignment detail when the user wants geeky precision.

## Search by Flight Number (Primary Workflow)

Use agent-browser to search SeatMaps by flight number. This identifies the aircraft type and loads the correct seat map automatically.

### Step 1: Navigate and switch to flight number search

```bash
agent-browser open "https://seatmaps.com/"
agent-browser wait --load networkidle

# Switch to flight number search mode
agent-browser snapshot -i
# Find and click "Search by flight#" toggle
agent-browser click @eN  # ref for "Search by flight#" generic element
```

### Step 2: Fill search form

```bash
# Type airline name in AIRLINE field
agent-browser fill @eAIRLINE "Air France"
agent-browser wait 2000

# Click the autocomplete suggestion (e.g., "(AF) Air France")
agent-browser snapshot -i
agent-browser click @eSUGGESTION  # ref for the correct airline suggestion

# Enter flight number (digits only, no airline code)
agent-browser fill @eFLIGHT "83"

# Optional: change date if needed
# agent-browser fill @eDATE "15-Aug-26"

# Click FIND
agent-browser click @eFIND
agent-browser wait 5000
```

### Step 3: Extract cabin data AND screenshots

After navigation, get both the structured data and visual seat map:

```bash
# Get structured data (cabin specs, ratings, reviews)
agent-browser snapshot -c

# Take full-page screenshot (captures everything: cabin photos, specs, reviews)
agent-browser screenshot --full seatmap-full.png

# Scroll to the interactive seat map and take viewport screenshots
# The seat map is an iframe that renders visually in screenshots
agent-browser scroll up 5000
agent-browser scroll down 400
agent-browser wait 1000
agent-browser screenshot seatmap-map-top.png      # First/Business section

agent-browser scroll down 600
agent-browser screenshot seatmap-map-middle.png    # Premium Economy section

agent-browser scroll down 600
agent-browser screenshot seatmap-map-bottom.png    # Economy section
```

**Screenshots capture the color-coded interactive seat map.** Each seat is color-coded:
- **Dark blue** = Standard seat
- **Green** = More comfort (extra legroom, quiet area, good window alignment)
- **Olive/yellow-green** = Some issues (limited recline, misaligned window)
- **Yellow** = Mixed features (extra legroom BUT near lavatory)
- **Red** = Reduced comfort (no recline, galley noise, narrow)

Read the screenshots to identify specific good/bad seats by row and letter, then recommend the best options.

The results page also contains:
- **Aircraft type** in the page heading (e.g., "Air France Boeing 777-300ER")
- **Variant tabs** (e.g., V.1 through V.5) showing different configurations
- **Per-cabin data** in a DescriptionList:
  - Seats count
  - Pitch (inches)
  - Width (inches)
  - Recline (degrees)
- **Aircraft overview** text with seat configuration summary
- **Seat map rating** (e.g., "4.49 out of 5, based on 389 reviews")
- **Flight reviews** with links to external reviews (OMAAT, Sam Chui, etc.)
- **Codeshare airlines** list

### Step 4: Check other variants (if multiple)

Click variant tabs to compare configurations:

```bash
agent-browser click @eVARIANT  # ref for "777-300ER V.2" tab
agent-browser wait 2000
agent-browser snapshot -c
```

## Direct URL Search (Fast Path)

When you already know the airline and aircraft, skip the form and navigate directly:

```
https://seatmaps.com/airlines/{iata-code}-{airline-name-slug}/{aircraft-slug}/
```

### URL Pattern Examples

| Airline | Aircraft | URL |
|---------|----------|-----|
| Air France | 777-300ER | `seatmaps.com/airlines/af-air-france/boeing-777-300er/` |
| KLM | 737-800 | `seatmaps.com/airlines/kl-klm/boeing-737-800/` |
| SAS | A350-900 | `seatmaps.com/airlines/sk-sas/airbus-a350-900/` |
| United | 787-9 | `seatmaps.com/airlines/ua-united/boeing-787-9/` |
| Delta | A330-900 | `seatmaps.com/airlines/dl-delta/airbus-a330-900neo/` |

### Airline page (fleet listing)

```
https://seatmaps.com/airlines/{iata-code}-{airline-name-slug}/
```

This lists all aircraft types the airline operates with links to each seat map.

## AeroLOPA Links

AeroLOPA doesn't have predictable URLs or flight number search. Use their homepage to browse:

```
https://www.aerolopa.com/
```

When presenting results, include the AeroLOPA link for the airline so users can find the to-scale visual map with window alignment:

```
For geeky detail (window positions, to-scale layout): https://www.aerolopa.com/
Search for [Airline] [Aircraft] on the page.
```

## Output Format

**Always use markdown tables.**

### Cabin comparison (single aircraft)

| Cabin | Seats | Pitch | Width | Recline |
|-------|-------|-------|-------|---------|
| First | 4 | 79" | 24" | 180° |
| Business | 58 | 61" | 21" | 180° |
| Premium Economy | 28 | 38" | 19" | 124° |
| Economy | 206 | 32" | 17" | 118° |

### After the table

- Note which variant is shown (e.g., "V.1 of 5 variants")
- Flag if the aircraft has notably good or bad ratings
- Link to the SeatMaps page for the interactive seat map
- Link to AeroLOPA for visual window alignment detail
- Mention relevant flight reviews if available
- If multiple variants exist, note key differences (e.g., "V.2 has no First Class, 42 J seats instead of 58")

### Variant comparison (when relevant)

| Variant | Config | First | Business | Prem Econ | Economy | Total |
|---------|--------|-------|----------|-----------|---------|-------|
| V.1 | 4/58/28/206 | 4 | 58 | 28 | 206 | 296 |
| V.2 | 0/42/0/315 | — | 42 | — | 315 | 357 |

## Seat Map Key (Color Coding)

SeatMaps uses these categories on their interactive map:

| Color | Meaning |
|-------|---------|
| Standard | Normal seat, no issues |
| More comfort | Extra legroom, window alignment, quiet location |
| Some issues | Minor concern (e.g., limited recline, misaligned window) |
| Mixed features | Tradeoffs (e.g., extra legroom but near lavatory) |
| Reduced comfort | Avoid if possible (e.g., no recline, galley noise, narrow) |

The interactive seat map in the iframe shows individual seat colors. Click seats on the SeatMaps website to see per-seat notes.

## Notes

- SeatMaps identifies the correct aircraft variant for a flight number on a given date
- Aircraft assignments can change. Check closer to departure for accuracy.
- AeroLOPA is rebuilding their site (launching 2026) with seat ratings, heat maps, and favorites
- SeatGuru (TripAdvisor) shut down permanently. SeatMaps and AeroLOPA are the replacements.
- SeatMaps has a paid API via Quicket GmbH (sandbox.quicket.io/redoc) for enterprise use. The browser automation approach works for individual lookups.

---
name: southwest
description: Search Southwest Airlines for flight prices, points pricing, and fare classes via Patchright (undetected Playwright). Use when user asks about Southwest flights, fare classes, SW points pricing, or Companion Pass value. Southwest is NOT in any GDS or API. This skill and google-flights are the only ways to get SW data. Triggers on "southwest", "SW flights", "wanna get away", "companion pass", "southwest points", "basic vs choice".
allowed-tools: Bash(python3 *), Bash(docker *)
---

# Southwest Airlines Search

Search southwest.com via Patchright (undetected Playwright fork). Southwest is the only major US airline not in any GDS, API, or flight search tool. This skill is the only way to get SW-specific data: fare classes, points pricing, and Companion Pass qualification.

**Requires Patchright** (undetected Playwright fork). Standard Playwright and agent-browser are detected and blocked by SW. Patchright patches the browser fingerprint to bypass detection.

**Must run headed (headless=False).** SW detects headless browsers even with Patchright. On macOS, a Chrome window briefly appears and closes. For background operation with no popup, use Docker:

```bash
# Search new flights (default, no login needed)
docker run --rm ghcr.io/borski/sw-fares --origin SJC --dest DEN --depart 2026-05-15
docker run --rm ghcr.io/borski/sw-fares --origin SJC --dest DEN --depart 2026-05-15 --return 2026-05-18 --points --json

# Check existing reservation for price drops (requires SW login)
docker run --rm -e SW_USERNAME -e SW_PASSWORD \
  ghcr.io/borski/sw-fares change --conf ABC123 --first Jane --last Doe --json

# List all upcoming trips
docker run --rm -e SW_USERNAME -e SW_PASSWORD \
  ghcr.io/borski/sw-fares change --list --json

# Build locally
docker build -t sw-fares skills/southwest/
```

The Docker image uses xvfb to create a virtual display inside the container. Patchright runs "headed" against xvfb, bypassing SW's headless detection without opening any windows on your machine.

```bash
# Install
pip install patchright && patchright install chromium

# Search cash fares
python3 scripts/search_fares.py --origin SJC --dest DEN --depart 2026-05-15

# Search cash + points
python3 scripts/search_fares.py --origin SJC --dest DEN --depart 2026-05-15 --return 2026-05-18 --points

# JSON output
python3 scripts/search_fares.py --origin SJC --dest DEN --depart 2026-05-15 --points --json
```

**Key implementation details learned the hard way:**
- Navigate to southwest.com homepage FIRST, then to the results URL. Direct URL without homepage warmup gets blocked.
- Use `fareType=POINTS` URL parameter for points pricing. Don't try to click the Points toggle on the page.
- Use a fresh persistent browser context (temp dir) each run to avoid fingerprint accumulation.
- Extract text from `[role='main']` NOT `<main>`. The `<main>` element contains the booking form. `[role='main']` contains the flight results.
- Flight blocks can be parsed by splitting on `# \d+` patterns and ending at `View seats`.
- Always dismiss the cookie banner first. It blocks interactions.

## Prerequisites

```bash
pip install patchright && patchright install chromium
```

Or use Docker (no local install needed):
```bash
# Pre-built image (fastest)
docker pull ghcr.io/borski/sw-fares:latest

# Or build locally
docker build -t sw-fares skills/southwest/
```

## When to Use

- User asks about Southwest flights or fares
- Need points pricing (not available anywhere else)
- Need fare class breakdown (Basic, Choice, Choice Preferred, Choice Extra)
- Calculating Companion Pass value
- Comparing SW points vs cash vs other airlines

## When NOT to Use

- **Just need SW cash prices**: Use google-flights skill instead (faster)
- **Completing purchases**: Find flights only. Do not book.
- **Non-Southwest airlines**: Use duffel, ignav, google-flights, or other skills

## Southwest Fare Classes

| Fare | Points | Cash | Companion Pass | Change/Cancel | Bags |
|------|--------|------|----------------|---------------|------|
| Basic (Wanna Get Away) | Lowest | Lowest | **NO** | Credit only | 2 free |
| Choice (Wanna Get Away Plus) | Low | Low | **YES** | Transferable credit | 2 free |
| Choice Preferred (Anytime) | High | High | **YES** | Refundable | 2 free |
| Choice Extra (Business Select) | Highest | Highest | **YES** | Refundable + priority | 2 free |

**Critical for Companion Pass:** Only Choice and above qualify. Basic does NOT. This changes the CPP math significantly.

## Companion Pass CPP Formula

When CP is in play, one ticket buys travel for two:

```
Total cash value = qualifying_fare_cash x 2 passengers
CPP = total_cash_value / total_points x 100
```

Always frame as "points bought $X of travel for 2 people."

## Search: Use the Script

**Do NOT try to automate the SW booking form manually.** It's fragile and the form's React state doesn't cooperate with browser automation. Use the script instead, which navigates directly to the results URL.

```bash
# Local (opens a Chrome window briefly)
python3 skills/southwest/scripts/search_fares.py --origin SJC --dest DEN --depart 2026-05-15

# With return date and points
python3 skills/southwest/scripts/search_fares.py --origin SJC --dest DEN --depart 2026-05-15 --return 2026-05-18 --points

# JSON output for programmatic use
python3 skills/southwest/scripts/search_fares.py --origin SJC --dest DEN --depart 2026-05-15 --points --json

# Docker (no Chrome window, no display needed)
docker run --rm ghcr.io/borski/sw-fares --origin SJC --dest DEN --depart 2026-05-15 --return 2026-05-18 --points
```

The script handles everything: homepage warmup, cookie dismissal, result extraction, points toggle.

## How the Script Works

1. Launches Patchright (undetected Playwright) in headed mode with a fresh browser profile
2. Visits southwest.com homepage first to establish a normal browsing session
3. Navigates to the results URL with `fareType=USD` for cash or `fareType=POINTS` for points
4. Waits 15 seconds for SW's React app to render flight data
5. Extracts flight text from `[role='main']` (NOT `<main>` which is the booking form)
6. Parses flight blocks by splitting on `# \d+` patterns
7. Cleans up the browser and temp profile

**Why fareType in the URL instead of clicking the Points toggle:** The Points label on the results page is in a different frame context than the flight cards. Clicking it via Playwright is unreliable. Using the URL parameter loads points results directly. Two page loads (cash + points) is more reliable than one load + a toggle click.

**Why [role='main'] not main:** SW has two content areas. The `<main>` HTML element contains the booking form. The `[role='main']` ARIA attribute marks the flight results. Using the wrong one returns zero flights.

## Output Format

**Always use markdown tables.** Show both cash and points in separate tables.

### Cash Prices

| Flight | Depart | Arrive | Stops | Duration | Basic | Choice | Ch Pref | Ch Extra |
|--------|--------|--------|-------|----------|-------|--------|---------|----------|
| #104 | 6:00AM | 9:35AM | Nonstop | 2h 35m | $277 | $317 | $387 | $432 |
| #1681 | 7:40PM | 11:05PM | Nonstop | 2h 25m | $209 | $249 | $319 | $364 |
| #481/3780 | 6:35AM | 12:05PM | 1 stop via PHX | 4h 30m | $219 | $259 | $329 | $374 |

### Points Prices

| Flight | Depart | Arrive | Stops | Duration | Basic | Choice | Ch Pref | Ch Extra |
|--------|--------|--------|-------|----------|-------|--------|---------|----------|
| #104 | 6:00AM | 9:35AM | Nonstop | 2h 35m | 23,500 +$5.60 | 27,000 +$5.60 | 33,000 +$5.60 | 36,500 +$5.60 |

### After Tables

- Calculate CPP for each fare class: `cash_price / points x 100`
- Flag which fares qualify for Companion Pass (Choice and above)
- If CP is in play, show the 2-pax value
- Compare against other airline options if available

## Troubleshooting

- **"No flights found"**: SW may have flagged the IP from too many automated requests. Wait a few minutes and try again, or try Docker (different network stack).
- **Chrome window pops up**: Expected in local mode. Use Docker for no popup.
- **Script hangs**: SW's page can take up to 20 seconds to render. The 15-second wait is usually enough but slow connections may need more.
- **"Oops" error page**: Retry after a short wait. SW's site can be flaky.

## Limitations

- **Headed mode required.** SW detects and blocks headless browsers, even with Patchright's stealth patches. Docker+xvfb is the workaround for background operation.
- **No codeshare data.** SW doesn't codeshare with anyone.
- **~20 seconds per search.** Homepage warmup + page render time. Slower than API sources.
- **Prices change frequently.** SW uses dynamic pricing. Results are point-in-time.
- **One-way searches only return departing flights.** For round-trip, the script fetches departure fares. Return flight fare search would require a second URL load (future enhancement).

## Change Flight Price Monitor (check_change.py)

**READ-ONLY script. NEVER modifies, changes, or cancels any flight.**

Logs into southwest.com, looks up an existing reservation, and reads the Change Flight page to check if prices have dropped below what was paid.

### Docker Usage (No Popup Window)

```bash
# Set your SW credentials however you like (env vars, 1Password, etc.)
export SW_USERNAME="your_username"
export SW_PASSWORD="your_password"

# List all upcoming trips (auto-discover confirmation numbers)
docker run --rm -e SW_USERNAME -e SW_PASSWORD \
  ghcr.io/borski/sw-fares change --list --json

# Check a specific reservation for price drops
docker run --rm -e SW_USERNAME -e SW_PASSWORD \
  ghcr.io/borski/sw-fares change --conf ABC123 --first Jane --last Doe --json

# Local (opens Chrome window, for debugging only)
SW_USERNAME=your_user SW_PASSWORD=your_pass \
  python3 scripts/check_change.py --conf ABC123 --first Jane --last Doe --debug
```

### Important: Use Legal Names

SW bookings use the legal name on the reservation, not nicknames. Use the exact first and last name that appears on the booking.

### How It Works

1. Logs into southwest.com via header login flyout
2. For `--list`: clicks My Account, expands accordion for each trip, extracts confirmation numbers
3. For `--conf`: navigates to Change Flight page, fills lookup form, selects both legs, clicks "Explore options"
4. Reads the change results page which shows **fare differences** for every available flight:
   - `CURRENT FLIGHT` = your booked flight (Basic cell shows "CURRENT", no change)
   - `+2,000` = this flight costs 2,000 points MORE than what you paid
   - `-2,000` = this flight costs 2,000 points LESS (savings, rebook opportunity)
   - `Unavail` = fare class sold out
5. Flags any flight with a negative diff as a savings opportunity

### Safety Guardrails

1. **DANGEROUS_LABELS blocklist**: "change this flight", "confirm", "cancel", "book", "purchase", etc.
2. **is_dangerous_click()** check on every button click after the login and lookup phases
3. **extract_results()** is read-only. Zero clicks after the leg selection + "Explore options" step
4. The script selects legs and views alternatives but NEVER selects a replacement flight or confirms any change

### Verified Working Selectors (Apr 5, 2026)

**Login flyout:**
- Trigger: `button:has-text('Log in')`
- Username: `input[aria-label*='Account']`
- Password: `input[name='password']`
- Submit: `button[type='submit']:has-text('Log in')`

**Change flight lookup form:**
- Confirmation: `input[id*='confirmationNumber']`
- First name: `input#passengerFirstName`
- Last name: `input#passengerLastName`
- Submit: `button#form-mixin--submit-button` (text: "Continue")

**Leg selection:**
- Checkboxes: `label:has(input[type='checkbox'])` (visible labels, hidden inputs)
- Continue: `button#form-mixin--submit-button` (text: "Explore options")

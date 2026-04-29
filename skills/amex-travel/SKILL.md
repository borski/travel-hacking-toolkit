---
name: amex-travel
description: Search the American Express travel portal via Patchright (undetected Playwright fork) for cash prices, Membership Rewards points pricing, International Airline Program (IAP) discounts, and Fine Hotels & Resorts / The Hotel Collection (FHR/THC) benefits. Use when comparing pay-with-points portal pricing to award flights or other options, checking MR balance impact, researching FHR or THC properties for stacking with Amex Platinum credits, or when the user wants Amex-specific portal inventory. Triggers on "Amex travel portal", "MR points", "Membership Rewards portal", "FHR", "Fine Hotels and Resorts", "The Hotel Collection", "THC", "International Airline Program", "IAP", or any pay-with-points comparison involving Amex.
---

# Amex Travel Portal Search

Search the American Express travel portal for flights and hotels via Patchright. Returns cash prices, MR points pricing, International Airline Program (IAP) discounts, and Fine Hotels & Resorts / The Hotel Collection benefits.

**Requires Patchright** (undetected Playwright fork). Amex blocks standard Playwright and agent-browser.

**Must run headed (headless=False).** Amex detects headless browsers. On macOS, a Chrome window briefly appears. For background operation, use Docker.

## Prerequisites

```bash
pip install patchright && patchright install chromium
```

Or use Docker (no local install needed):
```bash
docker pull ghcr.io/borski/amex-travel:latest
# or build locally:
docker build -t amex-travel skills/amex-travel/
```

## When to Use

- Compare Amex portal MR pricing against cash and award prices
- Find IAP (International Airline Program) discounted fares on Platinum
- Find FHR and THC hotels with benefits ($100 credit, breakfast, upgrade)
- Compare portal redemption value against transfer-to-airline value

## When NOT to Use

- **Completing purchases.** Find flights and hotels only. Do not book.
- **Non-Platinum cards.** IAP fares and FHR benefits require the Platinum Card.

## Usage

### Flight Search

```bash
# Local (opens a Chrome window briefly)
python3 scripts/search_flights.py --origin SFO --dest CDG --depart 2026-08-11

# Round-trip business
python3 scripts/search_flights.py --origin SFO --dest CDG --depart 2026-08-11 --return 2026-09-02 --cabin business

# JSON output
python3 scripts/search_flights.py --origin SFO --dest CDG --depart 2026-08-11 --json

# Docker
docker run --rm \
    -v ~/.amex-travel-profiles:/profiles \
    -e AMEX_USERNAME -e AMEX_PASSWORD \
    amex-travel script /app/search_flights.py \
    --origin SFO --dest CDG --depart 2026-08-11 --cabin business --json
```

### Hotel Search

```bash
# Local
python3 scripts/search_flights.py --hotel --dest "Oslo" --checkin 2026-08-13 --checkout 2026-08-15

# Docker
docker run --rm \
    -v ~/.amex-travel-profiles:/profiles \
    -e AMEX_USERNAME -e AMEX_PASSWORD \
    amex-travel script /app/search_flights.py \
    --hotel --dest "Oslo" --checkin 2026-08-13 --checkout 2026-08-15 --json
```

### Record Mode (API Discovery)

Capture network traffic during a manual search:

```bash
python3 scripts/search_flights.py --record
```

### Offline Debug (Hotels)

Save and re-parse hotel results without re-running the browser:

```bash
# Save page HTML after hotel search
python3 scripts/search_flights.py --hotel --dest "Paris" --checkin 2026-08-11 --checkout 2026-08-15 --save-html /tmp/amex-hotels.json

# Re-parse locally (instant, no browser)
python3 scripts/search_flights.py --parse-html /tmp/amex-hotels.json
```

## 2FA Flow

Amex uses email OTP for 2FA. After first login with "Add This Device", subsequent runs skip 2FA from the same profile.

**How it works:** When 2FA is triggered, the script prints `2FA_CODE_NEEDED` to stdout and `2FA REQUIRED` to stderr, then polls for the code. It will wait up to 2 minutes.

**For agents:** When you see `2FA_CODE_NEEDED` in the script output, **ask the user** for the verification code Amex just emailed them. Once they provide it, write it to the code file:

```bash
echo "123456" > /tmp/amex-2fa-code.txt
```

The script picks up the file automatically and continues login.

**Command hook (optional, for full automation):** Set `AMEX_2FA_COMMAND` to a command that blocks until it has the code, then prints it to stdout. The script runs this instead of polling the file.

After first login with "Add This Device", 2FA is skipped on repeat runs from the same profile.

## How It Works

### Flight Search Architecture

1. **Auth:** Cookie injection from saved profile. Falls back to fresh login with email 2FA.
2. **Form filling:** DOM-based search form automation (airport autocomplete, calendar picker, cabin selector)
3. **Login gate:** After form submission, Amex redirects through a login interstitial. Script handles re-authentication automatically.
4. **Data extraction:** Flight results are server-side rendered into `window.appData` (a 627KB Redux store). Script parses this JSON blob for all flight data.
5. **IAP detection:** Platinum Card holders see `PEP` (IAP) fare types alongside `PUB` (public) fares. IAP fares are typically 10-15% cheaper for front-of-cabin international flights.

### Hotel Search Architecture

1. **Form filling:** Same DOM-based approach as flights
2. **Login gate:** Handled automatically
3. **Data extraction:** Hotels render as a Next.js app with NO `window.appData`. Script parses the DOM using `data-testid="hotel-offer-card"` elements.
4. **FHR/THC detection:** Identified via `data-testid="offer-banner"` text ("Fine Hotels and Resorts" or "The Hotel Collection")
5. **Benefits extraction:** FHR/THC cards show benefits (breakfast, credit, upgrade) as `data-testid="offer-amenities-item"` elements

### Data Structure

Flight results (from `window.appData.flightSearch.itineraries[]`):
- `pricing_information[]` with `fare_type` = `PEP` (IAP) or `PUB` (public)
- `total_price.cents` (cash), `total_price_in_points` (MR points = 1 cent per point)
- `segment.legs[]` with carrier, times, duration, cabin, equipment, amenities
- `segment.seats_left`, `is_refundable`, `cancellation_policy`

Hotel results (from DOM parsing):
- Hotel name, stars, city, distance
- TripAdvisor rating and review count
- Per-night price and total price
- MR points cost
- FHR/THC membership with specific benefits
- Standard amenities (wifi, breakfast, parking)

## International Airline Program (IAP)

Platinum Card benefit. Lower fares on premium cabin seats for international flights on select airlines. Shows as a separate `PEP` fare type alongside `PUB` (public fare).

- Typically 10-15% savings on business/first class
- Not available on all routes or airlines
- Only visible when logged in with a Platinum Card

## Output Format

**Always use markdown tables.**

### Flights

| # | Airline | Route | Stops | Duration | Cash | IAP Cash | Points | Seats |
|---|---------|-------|-------|----------|------|----------|--------|-------|
| 1 | Turkish | SFO-IST-CDG | 1 | 20h 10m | $5,044 | $4,381 | 438,113 | 3 |

### Hotels

| # | Hotel | Program | Stars | Per Night | Total | Points | Benefits |
|---|-------|---------|-------|-----------|-------|--------|----------|
| 1 | Hotel Continental | FHR | 5 | $471 | $942 | 94,200 | Breakfast, $100 credit, upgrade, 4pm checkout |

### After Tables
- Flag IAP savings (show % discount)
- Note FHR/THC benefits and how they offset the rate
- Calculate effective CPP for MR redemptions (1 point = 1 cent at Amex portal)
- Compare against transfer-to-airline value
- Mention the $600/yr Platinum hotel credit ($300 per half-year, shared between FHR and THC)

## Cabin Codes

| CLI Value | Amex Code | Description |
|-----------|-----------|-------------|
| `economy` | `ECONOMY` | Standard economy |
| `premium` | `PREMIUM_ECONOMY` | Premium economy |
| `business` | `BUSINESS` | Business class |
| `first` | `FIRST` | First class |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `AMEX_USERNAME` | Yes | Amex online account username |
| `AMEX_PASSWORD` | Yes | Amex online account password |
| `AMEX_PROFILE` | No | Browser profile directory (default: `~/.amex-travel-profiles/default`) |
| `AMEX_2FA_COMMAND` | No | Command that blocks until email code is ready, prints to stdout |

## Troubleshooting

- **Login gate after search:** Normal. Amex always redirects through a login interstitial after form submission. The script handles this automatically.
- **No appData found (flights):** The page may not have fully loaded. Script waits for the Redux store to populate. Check if login succeeded.
- **Empty hotel results:** Hotels use DOM parsing, not appData. If the DOM structure changed, the `data-testid` selectors may need updating.
- **Calendar picker fails:** Amex uses `div[role="button"]` for calendar days (not `<button>`). The script uses class patterns `automation-date-picker-month-{year}-{month}` to find the right month container.
- **2FA code rejected:** Amex codes expire quickly. Make sure the code is fresh (not an old one from a previous login).

## Limitations

- **Headed mode required.** Amex detects headless. Docker+xvfb is the workaround.
- **~45 seconds per search.** Login + form fill + login gate + results load.
- **Hotel results via DOM only.** No API interception available for hotels (Next.js app with empty `__NEXT_DATA__`). Parser depends on `data-testid` attributes.
- **Device trust helps.** After "Add This Device" on first login, 2FA is skipped for that profile. Keep profiles persistent via Docker volume mounts.

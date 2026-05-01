---
name: chase-travel
description: Search Chase UR travel portal via Patchright for cash prices, points pricing, Points Boost offers, and Chase Edit hotel benefits. Use for pay-with-points portal comparison on Sapphire Reserve/Preferred.
category: portals
summary: Chase UR portal for flights, hotels, Points Boost, Edit benefits. Requires Sapphire.
api_key: None (requires Patchright)
docker_image: ghcr.io/borski/chase-travel
---

# Chase Travel Portal Search

Search the Chase Ultimate Rewards travel portal for flights and hotels via Patchright. Returns cash prices, UR points pricing, Points Boost offers, and Chase Edit hotel benefits.

**Requires Patchright** (undetected Playwright fork). Chase blocks standard Playwright and agent-browser.

**Must run headed (headless=False).** Chase detects headless browsers. On macOS, a Chrome window briefly appears. For background operation, use Docker.

## Prerequisites

```bash
pip install patchright && patchright install chromium
```

Or use Docker (no local install needed):
```bash
docker pull ghcr.io/borski/chase-travel:latest
# or build locally:
docker build -t chase-travel skills/chase-travel/
```

## When to Use

- Compare UR portal pricing against cash and award prices
- Check Points Boost offers (1.5x to 2.0x cpp on select bookings)
- Find Chase Edit hotels with $100 property credit + daily breakfast
- Compare pay-with-points vs transfer-to-airline value

## When NOT to Use

- **Completing purchases.** Find flights and hotels only. Do not book.
- **Non-Chase cards.** This skill requires a Sapphire Reserve or Sapphire Preferred card.

## Card Selection

The script automatically selects the **Sapphire Reserve** card from the account selector (dynamic Points Boost pricing on travel; ~1.5-2.0 cpp typical on CSR but not a guaranteed floor; Edit hotels). Falls back to **Sapphire Preferred** if no Reserve found. Only these cards show Edit hotel benefits and travel portal pricing.

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
    -v ~/.chase-travel-profiles:/profiles \
    -v /tmp:/tmp/host \
    -e CHASE_USERNAME -e CHASE_PASSWORD \
    ghcr.io/borski/chase-travel script /scripts/search_flights.py \
    --origin SFO --dest CDG --depart 2026-08-11 --cabin business --json
```

### Hotel Search

```bash
# Local
python3 scripts/search_flights.py --hotel --dest "Paris" --checkin 2026-08-11 --checkout 2026-08-15

# Docker
docker run --rm \
    -v ~/.chase-travel-profiles:/profiles \
    -v /tmp:/tmp/host \
    -e CHASE_USERNAME -e CHASE_PASSWORD \
    ghcr.io/borski/chase-travel script /scripts/search_flights.py \
    --hotel --dest "Oslo" --checkin 2026-08-13 --checkout 2026-08-15 --json
```

### Record Mode (API Discovery)

Capture network traffic during a manual search. Useful for debugging or discovering new API endpoints.

```bash
# Local only (needs interactive browser)
python3 scripts/record_search.py
```

## 2FA Flow

Chase uses SMS for 2FA. On first login, you must complete 2FA manually. After that, device trust persists (2FA skipped on subsequent runs from the same profile).

**How it works:** When 2FA is triggered, the script prints `2FA_CODE_NEEDED` to stdout and `2FA REQUIRED` to stderr, then polls for the code. It will wait up to 3 minutes.

**For agents:** When you see `2FA_CODE_NEEDED` in the script output, **ask the user** for the SMS code Chase just sent to their phone. Once they provide it, write it to the code file:

```bash
echo "12345678" > /tmp/chase-2fa-code.txt
```

The script picks up the file automatically and continues login.

**Command hook (optional, for full automation):** Set `CHASE_2FA_COMMAND` to a command that blocks until it has the code, then prints it to stdout. The script runs this instead of polling the file.

**Docker:** Use `-v /tmp:/tmp/host` to share the temp directory. The script checks both `/tmp/host/chase-2fa-code.txt` and `/tmp/chase-2fa-code.txt`.

After first successful login with device trust, 2FA is skipped on repeat runs.

## How It Works

### Flight Search Architecture

1. **Auth:** Patchright handles login, 2FA, cookie persistence, and card selection. Account identifier auto-extracted from portal URL.
2. **Session:** `POST` to `v1/session/create` establishes the CXL travel session. Identifiers auto-extracted from cookies.
3. **Search API:** `POST` to Chase's internal CTE API creates a flight search session (returns `sessionId`)
4. **Results:** Browser navigates to `travelsecure.chase.com/results/flights/outbound?ssid={sessionId}&cnxtoken={redirectionToken}`. Script intercepts API responses via `page.on('response')` to capture `legwiseResults` JSON
5. **Pagination:** Shadow DOM "Show more" button (`<orxe-button>`) clicked via JS to load all flights (10 at a time)
6. **Points Boost:** Shadow DOM toggle (`<orxe-toggle class="points-offer">`) activated. Boost card carousel parsed for discounted point prices

### Hotel Search Architecture

1. **Search API:** `POST` to Chase's hotel search endpoint creates session
2. **Results:** Browser navigates to results page. Script intercepts `hotel/v1.0/search/results` API responses
3. **Edit Detection:** Hotels with `prm[].c == "Signature Amenities"` are Edit properties. Benefits extracted from embedded JSON
4. **Boost Detection:** Hotels with `rwd[].rdp.rcm.t.ofr.d == "Points offer applied"` have Points Boost
5. **Pagination:** Same shadow DOM pattern as flights

### Data Structure

Flight results include:
- Cash price, points price, and cash+points hybrid pricing
- Points Boost offers with original vs boosted point costs
- Fare family (Economy, Basic Economy, Business Standard, Business Flex, etc.)
- Flight segments with carrier, times, duration, stops, equipment
- Refundability and change policies

Hotel results include:
- Cash price per night and total
- Points price
- Edit program membership with specific benefits (breakfast, credit, upgrade)
- Points Boost availability and rate
- Star rating, address, amenities, refundability

## Output Format

**Always use markdown tables.**

### Flights

| # | Airline | Route | Stops | Duration | Cash | Points | Boost | CPP |
|---|---------|-------|-------|----------|------|--------|-------|-----|
| 1 | Air France | SFO-CDG | Nonstop | 10h 40m | $5,397 | 539,683 | 269,841 | 2.0 |

### Hotels

| # | Hotel | Program | Per Night | Total | Points | Benefits |
|---|-------|---------|-----------|-------|--------|----------|
| 1 | Sommerro | EDIT, BOOST | $408 | $816 | 81,600 | Breakfast, $100 credit, upgrade |

### After Tables
- Note which hotels are Edit (include benefits)
- Calculate CPP for points redemptions
- Flag Points Boost offers with effective cpp
- Compare against direct booking prices when possible
- Pull the actual Points Boost quote at checkout. CSR pricing is dynamic, not a fixed multiplier.

## Portal Pricing Notes

- Chase portal pricing on CSR is dynamic Points Boost. The historical static 1.5x multiplier is gone. Each booking quotes a specific points price; effective cpp typically falls in the 1.5-2.0 cpp range on CSR but is not a guaranteed floor on every booking.
- **Points Boost** offers appear as separate cards with discounted point prices (typically 1.5x to 2.0x cpp effective).
- `cash_plus_points` pricing uses all available UR points plus cash for the remainder.
- Chase sessions don't persist across browser close. Every Docker run needs fresh login (but 2FA is skipped if device is trusted).

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `CHASE_USERNAME` | Yes | Chase online banking username |
| `CHASE_PASSWORD` | Yes | Chase online banking password |
| `CHASE_2FA_COMMAND` | No | Command that blocks until SMS code is ready, prints to stdout |
| `CHASE_PROFILE` | No | Browser profile directory (default: `~/.chase-travel-profiles/default`) |

## Troubleshooting

- **"Access Denied" on login page in Docker:** Chase blocks `secure01ea.chase.com` from Docker. The script uses `chase.com` homepage login instead (different auth endpoint, works in Docker).
- **Video modal blocks clicks:** Script includes a MutationObserver that auto-removes the modal. If it persists, the observer handles re-renders.
- **CSRF errors on direct API calls:** The travelsecure.chase.com results API requires CSRF tokens managed by the React app. The script uses response interception instead of direct API calls, which sidesteps CSRF entirely.
- **No flights found:** Chase may not have loaded results yet. The script waits for the API response via interception, so this shouldn't happen. Check if login succeeded.

## Limitations

- **Headed mode required.** Chase detects headless. Docker+xvfb is the workaround.
- **~30 seconds per search.** Login + portal navigation + search + results load.
- **Sessions die on browser close.** No persistent sessions. Every run needs login (2FA skipped after first trust).
- **React controlled inputs.** Form automation is unreliable. The script uses API calls for search creation, not form filling.

---
name: ticketsatwork
description: Search TicketsAtWork (corporate employee perks platform run by Entertainment Benefits Group) for hotels, rental cars, and ticket / attraction deals via Patchright (undetected Playwright). Use when the user has a TaW corporate account and wants to compare against retail / portal / direct prices. TaW often beats portals by 10-30% on the same property + dates. Triggers on "TaW", "TicketsAtWork", "EBG", "tickets at work", "corporate perks", or whenever comparing hotel / car / theme park options for a trip.
category: hotels
summary: TicketsAtWork (EBG) corporate-perks portal. Hotels, theme park tickets, attractions, live events. Often beats portals by 10-30%.
api_key: None (requires TaW account + Patchright)
docker_image: ghcr.io/borski/ticketsatwork
allowed-tools: Bash(docker *), Bash(python3 *)
---

# TicketsAtWork

Scrapes inventory from [ticketsatwork.com](https://www.ticketsatwork.com), a corporate employee perks platform operated by Entertainment Benefits Group (EBG). Members access negotiated rates through their employer's account.

**No public API.** Patchright (undetected Playwright fork) is required because TaW is behind bot protection that blocks `requests`, vanilla Playwright, and headless Chrome.

## Why TaW matters for travel hacking

TaW aggregates inventory from EBG's negotiated wholesale pool (similar inventory feeds as Costco Travel, AAA, etc.). On the same property + dates, TaW often beats:
- The hotel's direct booking
- Booking.com / Hotels.com / Expedia
- Chase Travel (UR portal) and Amex Travel (MR portal)
- Even Amex FHR / THC and Chase Edit on properties not in those programs

Discount badges are typically genuine: the "Save $X" amount is computed against the hotel's published rate at search time.

**Tradeoff:** No portal credits, no card-program elite benefits, no points earning on the stay. You earn TaW "Funlife" loyalty points usable at ~1 cpp on future TaW bookings only.

## Capabilities

| Subcommand | What it does | Status |
|------------|--------------|--------|
| `hotels` | Hotel search by city + date range. Returns ~10-200+ properties with prices, savings vs strike rate, lat/lng, ratings, distance | Stable |
| `cars` | Rental car search by pickup location + date/time range | **Experimental.** TaW resolves the autocomplete latlng but not always the airport code their car backend needs. Some valid-looking searches return "no cars at this location" even for major airports. See "Known limitations" below. |
| `tickets` | Browse a category landing page (e.g. `disneyland`, `wdw`, `usf`) or keyword-search via Reflektion | Stable. Returns deal title, savings claim, description, image, detail URL. **Prices are not on the listing**, they appear on the detail page. |

## Prerequisites

- Docker running locally (for the published image) OR Patchright installed locally (`pip install patchright && patchright install chromium`)
- A TaW account (created via your employer's TaW URL or corporate code)
- TaW email + password set as `TAW_USER` and `TAW_PASS` environment variables

## Authentication

Form-based email + password. The skill submits the login form via JavaScript directly. Each script run uses a fresh browser profile, so each run logs in fresh.

The visible "Sign in / Register" UI requires modal interactions that Patchright handles unreliably (cookie banner overlap, modal trigger visibility issues). The login form (`#member_login_form`) is in the DOM at all times, so we set values via JS and click the form's submit button.

## Docker Usage

```bash
docker pull ghcr.io/borski/ticketsatwork:latest

# Hotels
docker run --rm -e TAW_USER -e TAW_PASS \
  ghcr.io/borski/ticketsatwork hotels \
  --city "Carlsbad, CA" --checkin 2027-03-04 --checkout 2027-03-07 \
  --rooms 1 --adults 2 --json

# Tickets / attractions (category)
docker run --rm -e TAW_USER -e TAW_PASS \
  ghcr.io/borski/ticketsatwork tickets \
  --category disneyland --json

# Tickets / attractions (keyword)
docker run --rm -e TAW_USER -e TAW_PASS \
  ghcr.io/borski/ticketsatwork tickets \
  --keyword "universal studios" --json

# Live events in destination cities (concerts, theater, sports)
docker run --rm -e TAW_USER -e TAW_PASS \
  ghcr.io/borski/ticketsatwork tickets \
  --section events --json

# Rental cars (experimental)
docker run --rm -e TAW_USER -e TAW_PASS \
  ghcr.io/borski/ticketsatwork cars \
  --pickup "San Diego Airport, CA" \
  --pickup-date 2026-06-15 --pickup-time 12:00 \
  --dropoff-date 2026-06-18 --dropoff-time 12:00 \
  --age 30 --json
```

## Local Usage (opens a Chrome window briefly)

```bash
# Hotels
TAW_USER=you@example.com TAW_PASS=yourpass \
  python3 scripts/search_hotels.py --city "Carlsbad, CA" \
  --checkin 2027-03-04 --checkout 2027-03-07 --json

# Tickets
TAW_USER=you@example.com TAW_PASS=yourpass \
  python3 scripts/browse_tickets.py --category disneyland --json

# Cars
TAW_USER=you@example.com TAW_PASS=yourpass \
  python3 scripts/search_cars.py \
  --pickup "San Diego Airport, CA" \
  --pickup-date 2026-06-15 --pickup-time 12:00 \
  --dropoff-date 2026-06-18 --dropoff-time 12:00 --json
```

## Hotels: arguments and output

### Arguments

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--city` | yes |  | City or address. Goes into the destination autocomplete. |
| `--checkin` | yes |  | Check-in date in `YYYY-MM-DD`. |
| `--checkout` | yes |  | Check-out date in `YYYY-MM-DD`. |
| `--rooms` | no | 1 | Number of rooms. |
| `--adults` | no | 2 | Adults per room. |
| `--children` | no | 0 | Children per room. |
| `--json` | no | off | Structured JSON instead of a human-readable table. |
| `--debug` | no | off | Save screenshots + HTML at each step to `/output` (Docker) or `/tmp/taw_debug/` (local). |
| `--raw-html-out` | no |  | Write the raw results HTML to a file for offline analysis. |

### Output schema (JSON mode)

```json
{
  "city": "Carlsbad, CA",
  "checkin": "2027-03-04",
  "checkout": "2027-03-07",
  "rooms": 1,
  "adults": 2,
  "children": 0,
  "display_pages": 14,
  "listing_count": 134,
  "listings": [
    {
      "id": "hotel_NNNNNN_x",
      "name": "Property Display Name",
      "name_normalized": "property display name",
      "rating": 4.5,
      "guest_rating": 9.0,
      "price_per_night_usd": 184,
      "total_price_usd": 746,
      "strike_price_usd": 1122,
      "savings_usd": 375.68,
      "loyalty_points": 1492,
      "distance_miles": 0.89,
      "distance_label": "0.89 miles from the center of Carlsbad",
      "property_type": "hotel",
      "lat": 33.121,
      "lng": -117.310,
      "tripadvisor": 0.0,
      "room_id": "...",
      "rate_code": "...",
      "featured": false,
      "discount_ranking": 717.95,
      "detail_url": "https://www.ticketsatwork.com/tickets/hotels.php?sub=details&id=NNNNNN_x"
    }
  ]
}
```

Field notes:
- `rating` = property star rating (0.0 - 5.0).
- `guest_rating` = post-stay review average (0.0 - 10.0).
- `total_price_usd` = all-in for the stay (taxes/fees included; "All fees included" shown in UI).
- `strike_price_usd` = published comparison rate (what you'd pay direct or non-discount channel).
- `savings_usd` = `strike_price_usd - total_price_usd` per the badge.
- `loyalty_points` = TaW Funlife points earned from this booking.
- `discount_ranking` = TaW's internal discount-magnitude score (bigger = bigger savings vs comp rate).

### Pagination behavior

TaW renders **all matching hotels in the initial DOM** and uses `simple-pagination` (jQuery) to chunk visually. There are no additional listings to fetch; one parse covers the full result set. The `display_pages` field reflects what TaW shows the user, not what the script needs to walk.

## Tickets: arguments and output

### Arguments

Use exactly one of `--category` or `--keyword`:

| Flag | Description |
|------|-------------|
| `--category SLUG` | Category slug like `disneyland`, `wdw`, `usf`, `seaworld`. See category list below. |
| `--keyword TEXT` | Free-text keyword. Uses Reflektion site search. On Enter, TaW often redirects directly to the most relevant category landing page. |
| `--json` | Structured JSON output. |
| `--debug` | Save screenshots + HTML. |
| `--raw-html-out` | Write the raw landing page HTML to a file. |

### Common category slugs

These are stable category landing pages (`/tickets/pages.php?sub=<slug>`):

| Slug | Page |
|------|------|
| `wdw` | Walt Disney World |
| `disneyland` | Disneyland Resort (California) |
| `disneyland-paris` | Disneyland Paris |
| `usf` | Universal Orlando |
| `ush` | Universal Studios Hollywood |
| `seaworld` | SeaWorld parks |
| `busch-gardens-parks` | Busch Gardens parks |
| `sesame-place` | Sesame Place parks |
| `all-theme-parks-attractions` | Combined theme parks + attractions index |

For other categories, navigate `/tickets/index.php` in a browser, find the category, copy the `?sub=` slug from the URL.

### Output schema

```json
{
  "category": "disneyland",
  "keyword": null,
  "landed_url": "https://www.ticketsatwork.com/tickets/pages.php?sub=disneyland",
  "deal_count": 6,
  "deals": [
    {
      "type": "ticket",
      "filter_entity_id": "4704",
      "title": "Disneyland Resort - California",
      "subtitle": "Save up to $65 on Multi-Day Tickets",
      "description": "Explore 1-5 Day Disneyland Resort theme park tickets...",
      "image_url": "https://www.ticketsatwork.com/common_resources/...",
      "detail_url": "https://www.ticketsatwork.com/tickets/packages.php?sub=packages&action=view&id=4704"
    }
  ]
}
```

`type` is `ticket` (a TaW package, prices appear on the detail page) or `url` (an external link, often to a hotel detail).

**Pricing note:** Most category pages don't show prices in the listing. The `subtitle` field contains the savings claim ("Save up to $65", "Tickets from $48 Per Day"); exact pricing requires following `detail_url`.

## Cars: arguments and known limitations

### Arguments

| Flag | Required | Default | Description |
|------|----------|---------|-------------|
| `--pickup` | yes |  | Pickup location. Airport names work best. |
| `--dropoff` | no | same as pickup | Dropoff location. |
| `--pickup-date` | yes |  | `YYYY-MM-DD`. |
| `--pickup-time` | no | `12:00` | `HH:MM` 24h. Must be `:00` or `:30` boundary. |
| `--dropoff-date` | yes |  | `YYYY-MM-DD`. |
| `--dropoff-time` | no | `12:00` | Same format. |
| `--age` | no | 30 | Driver age. TaW supports 20-25 with surcharge, 25+ standard. |

### Known limitations

The TaW car results page uses Handlebars templates that get filled by an XHR call to TaW's car backend. Even with the autocomplete-resolved latlng, **the airport code that the backend needs is sometimes not populated** by the autocomplete widget callback. The script backfills the visible input value into the hidden value field, but TaW's car API may require an additional `pickup_code` field that we're not setting.

Symptom: the car results page renders the skeleton, then shows "Sorry, there are no cars available at this location for your selected dates and time" even for major airports on near-term dates.

**Workaround if you need cars urgently:** open `ticketsatwork.com` in a regular browser, do the search manually, see the offers. Then if you want price comparison data scripted, this skill does still surface what TaW's hotel and ticket inventory looks like programmatically.

The script is wired and parses car cards correctly when the page renders them; the gap is in passing the right pickup-code metadata through the form. PRs welcome.

## When to use

- Comparing hotel rates for a specific destination + dates against direct / portal / Booking
- After narrowing to a hotel via Trivago / Google Hotels, check if TaW has the chosen property cheaper
- Discovering which theme-park / attraction discounts TaW currently offers (the discounts rotate seasonally)
- Verifying a "this is the best deal" claim before booking through Chase Travel / Amex Travel / direct

## When NOT to use

- The hotel is in Amex FHR / THC and the user wants the property credit + breakfast (the program stack usually beats TaW's nightly savings)
- The user wants hotel-program elite credits or points (TaW bookings don't credit Marriott Bonvoy, Hilton Honors, etc.)
- The user needs a flexible/refundable rate (TaW rates are often non-refundable; check the property detail page)
- Bookings where elite-status benefits matter more than rate

## Implementation gotchas (for future maintainers)

These are documented for future work. The scripts already handle them.

### Login via JS, not modal

The visible "Sign in / Register" button opens a modal containing the real login form. The trigger is sometimes invisible to Patchright (overlay z-index, OneTrust banner). The form is in the DOM regardless. We set values directly via JS and click submit.

```javascript
const form = document.querySelector('#member_login_form');
const emailEl = form.querySelector('input[name="login_email"]');
const passEl = form.querySelector('input[name="login_password"]');
// ...set values, dispatch input/change events, click submit
```

### Destination autocomplete is jQuery UI + ElasticSearch

The destination input (`#place_name` for hotels, `#pickup_location` for cars) is decorative until a suggestion is clicked. Hidden lat/lng fields populate on click via the autocomplete's callback.

**Selectors (hotels):**
- Suggestion dropdown: `.ui-autocomplete.ebg-autocomplete .ui-menu-item:visible`
- Lat: `#place_lat`, Lng: `#place_lng`

**Selectors (cars):**
- Same dropdown class
- Visible: `#pickup_location`, `#dropoff_location`
- Hidden value: `#origin_search_value`, `#destination_search_value`
- Hidden latlng (combined): `#origin_lat_lng`, `#destination_lat_lng`

**Race condition:** First-type often misses. Retry up to 3 times, clearing the field each time. Each attempt waits up to 8s for the targets to populate.

**Cars-specific:** Latlng populates reliably; the canonical place value field doesn't always populate via callback. The script backfills it from the visible input text. This is enough for the form to submit but may not be enough for the car backend to resolve an airport code.

### Date inputs are readonly

`#check_in`, `#check_out`, `#pick_up_date`, `#drop_off_date` are `readonly="readonly"` and driven by jQuery datepicker. You cannot `fill()` them like normal inputs. Set `.value` via JS using the underlying `HTMLInputElement.value` setter.

**Date format:** `MM/DD/YY` (2-digit year).

### Hotel listings render after the shell

Results page shell loads first; listings render via XHR. Wait for at least one `<li id="hotel_..." data-name="...">` to be attached to the DOM. Without this, parse fires too early and returns 0 listings.

### Hotel listings are pre-rendered

The full result set is delivered in the initial response. Pagination is purely visual via `simple-pagination`. Don't waste time clicking page links; one parse on the initial render gets you everything.

### Cars use Handlebars templates filled later

Car results use a Handlebars-style template page. The page renders immediately with `{{var}}` placeholders, then a backend XHR fills in actual offers. Wait for `.rc-totals` content to no longer match `{{total}}` before parsing.

### Cookie banner

OneTrust banner appears on first visit and intercepts clicks. Dismiss via `button#onetrust-accept-btn-handler` or `button:has-text('Accept')` early in the flow.

### Tickets / category pages are static HTML

Unlike hotels and cars, category landing pages render their deal grid in the initial HTML response. No XHR wait needed. Cards are `<li class="grid-template-seen">` with `data-unq` (URL) and inline title/subtitle/description.

## Building the Docker image

```bash
cd skills/ticketsatwork
docker build -t ghcr.io/borski/ticketsatwork:latest .
docker push ghcr.io/borski/ticketsatwork:latest
```

The base image (`ghcr.io/borski/patchright-docker:latest`) is shared with `southwest`, `chase-travel`, `amex-travel`, and other Patchright-based skills.

## Privacy / safety

- **Do NOT book** through this skill. Price discovery only. Always click through to TaW in a real browser to complete a booking.
- TaW's terms of service may restrict automated access. The skill makes one search per invocation, doesn't aggressively crawl, and uses one page-load worth of work. Use for personal price comparison, not bulk scraping.
- Credentials are passed via env vars only. The skill never writes credentials to disk and never prints them to logs.
- **Debug output may contain personal data.** TaW embeds the logged-in user's email, employer, IP, and account hash in the result page HTML. The script never prints these, but `--debug` mode and `--raw-html-out` capture full page HTML which contains them. Don't share debug artifacts publicly.

## Future expansions

- **search-shopping** for gift cards, electronics, etc. (`/tickets/shopping.php?sub=...`)
- **search-packages** for vacation bundles (`/tickets/packages.php?sub=packages&action=view&id=N`)
- **fix-cars** to resolve the airport-code population issue
- **with-prices** mode for tickets that follows each `detail_url` to extract pricing (slow, multi-page)

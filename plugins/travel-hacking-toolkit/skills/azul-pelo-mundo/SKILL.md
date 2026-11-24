---
name: azul-pelo-mundo
description: Search Azul Fidelidade points prices on Azul Pelo Mundo (azulpelomundo.voeazul.com.br) via Patchright browser automation. Prices Azul plus partner flights (TAP, United, Emirates and others) in Azul points and points + cash, with taxes in BRL. No login needed. Use when the user holds Azul / TudoAzul points or transfers Esfera, Livelo or card points to Azul, or asks for Brazilian award flights. Trigger phrases include Azul pontos, TudoAzul, Azul Fidelidade, Azul Pelo Mundo, emitir com pontos Azul, award from Brazil.
category: loyalty
summary: Azul Fidelidade points + points-and-cash pricing (Azul, TAP, United and partners) via Patchright. No login.
api_key: None (requires Patchright)
---

# Azul Pelo Mundo (Azul Fidelidade points)

Search [Azul Pelo Mundo](https://azulpelomundo.voeazul.com.br/) for flights
priced in **Azul Fidelidade points**. It covers Azul's own network plus partner
airlines (TAP, United, Emirates, Turkish, Copa and others) and returns, for each
itinerary, the full points price, the "pontos + dinheiro" (points + cash)
combinations, taxes in BRL, checked-bag allowance and the cash fare for
comparison.

This fills a gap: Seats.aero does not cover Azul Fidelidade, and Brazilian users
frequently hold Azul points directly or via transfers from Esfera, Livelo and
bank cards.

**No login required.** Searching is public. The site sits behind **Akamai Bot
Manager** and its JSON endpoint (`/api/availability`) needs a **reCAPTCHA token
minted by the page itself**, so plain HTTP gets `403` / `reCAPTCHA token is
required`. The script loads the public results URL in a real headed browser
(Patchright, same approach as the `vrbo` skill) and captures the
`/api/availability` response the page fetches for itself. It never calls the
endpoint directly or mints tokens.

## Prerequisites

```bash
pip install patchright && patchright install chromium
```

Or use Docker (headed via Xvfb):

```bash
docker build -t azul-pelo-mundo skills/azul-pelo-mundo/
```

## When to Use

- The user has Azul points, or Esfera / Livelo / card points they can transfer to Azul
- "Quanto custa em pontos Azul?", "emitir com pontos", award flights out of Brazil
- Comparing Azul points against LATAM Pass or Avios for the same trip
- Partner awards bookable with Azul points (TAP to Europe, United to the US)

## When NOT to Use

- **Completing a booking.** Return prices and the search URL only; never select a flight or pay.
- **Cash fares.** Use the normal flight sources; the cash fare here is only for computing value per point.
- **Programs other than Azul Fidelidade.** For LATAM Pass, Avios and others use their own sites or `seats-aero`.

## Usage

```bash
# One-way, 1 adult
python3 skills/azul-pelo-mundo/scripts/search_azul.py \
  --origin GRU --dest LIS --depart 2027-03-10 --json

# Round trip, 2 adults + 1 lap infant
python3 skills/azul-pelo-mundo/scripts/search_azul.py \
  --origin GRU --dest LIS --depart 2027-03-10 --return 2027-03-24 \
  --adults 2 --infants 1 --json

# Docker
docker run --rm azul-pelo-mundo --origin GRU --dest LIS --depart 2027-03-10 --json
```

| Flag | Default | Notes |
|------|---------|-------|
| `--origin` / `--dest` | required | IATA airport codes. |
| `--depart` | required | `YYYY-MM-DD`. |
| `--return` | none | `YYYY-MM-DD`; omit for one-way. |
| `--adults` / `--children` / `--infants` | 1 / 0 / 0 | Children are 2-11, infants are lap infants under 2. |
| `--cabin` | `ECONOMY` | `ECONOMY`, `BUSINESS` or `FIRST`. |
| `--limit` | 20 | Max itineraries returned, cheapest first. |
| `--retries` | 3 | Attempts before giving up on the bot wall. |
| `--json` | off | Emit JSON (use this for orchestration). |

## Output

```json
{
  "source": "azul-pelo-mundo",
  "searchUrl": "https://azulpelomundo.voeazul.com.br/flights/RT/GRU/LIS/...",
  "pointsArePerAdult": true,
  "count": 12,
  "itineraries": [
    {
      "tripType": "ROUND_TRIP",
      "fareType": "PUBLIC",
      "marketingCarrier": "TP",
      "operatingCarriers": ["TP"],
      "stops": 0,
      "points": 450000,
      "outboundPoints": 203000,
      "returnPoints": 247000,
      "pointsPlusCash": {
        "outbound": [{"points": 162500, "cashBRL": 620}],
        "return": [{"points": 198000, "cashBRL": 755}]
      },
      "feesBRL": 629.22,
      "cashFareBRL": {"ADULT": 6067.66, "INFANT": 600.48},
      "cashValueCentsPerPoint": 1.35,
      "checkedBags": 0,
      "outbound": {"departure": "10/03/2027 16:20", "arrival": "11/03/2027 05:15", "segments": ["..."]},
      "inbound": {"departure": "24/03/2027 12:20", "arrival": "24/03/2027 18:35", "segments": ["..."]}
    }
  ]
}
```

Reading the numbers:

- **`points` is per adult** (verified: the same itinerary shows the same points
  for 1 adult and for 2 adults + 1 infant). Multiply by the number of adults
  for the party total; check the child and infant price on the site before booking.
- **Round trips** are outbound + return. The site lists the outbound price
  first and the return price on the next screen; `points` is their sum, and the
  points + cash combos are listed per leg.
- **`fareType`**: `AWARD` is partner award inventory (e.g. United `XUAAWARD`) and
  has no public cash fare, so `cashValueCentsPerPoint` is `null`. `PUBLIC` means a
  cash fare converted to points; compare its value per point against the
  `points-valuations` floor before recommending it.
- **`feesBRL`** are the taxes you still pay in cash on top of the points, for
  the **whole party** (verified: United GRU-MCO round trip shows R$ 200.95 for
  1 adult and R$ 508.45 for 2 adults + 1 infant). Unlike `points`, do not
  multiply it by the number of adults.
- **`checkedBags: 0`** is common on `PUBLIC` fares (e.g. Avianca basic), while
  partner `AWARD` fares usually include 1 bag. Always show it next to the price.

## Tests

```bash
python3 -m unittest discover -s skills/azul-pelo-mundo/tests -v
```

The tests cover URL building, input validation, block detection and response
parsing using trimmed live payloads. No browser or network is needed. The
browser path has to be verified with a real search.

## Known fragility

- **Status: experimental.** In the first live test (Nov 2026, residential
  connection, local Patchright) the site loaded but `/api/availability` answered
  `HTTP 403` to the automated browser, so no prices were captured. The same
  search works in a regular browser, and the parser is verified against
  responses captured there. When the script exits 1, it prints the results URL:
  open it in a normal browser and read the points from the page.
- **Akamai and reCAPTCHA are IP-sensitive.** Datacenter, CI and VPN IPs are often
  blocked. Run headed on a residential connection and space searches a few
  minutes apart. On failure the script exits 1 with a clear message.
- **The results URL layout** was captured from the live site and may change.
  If searches suddenly return nothing, repeat a search in a normal browser and
  update `build_results_url`.

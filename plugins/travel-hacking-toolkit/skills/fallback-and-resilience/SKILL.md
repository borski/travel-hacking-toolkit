---
name: fallback-and-resilience
description: What to do when a tool fails, an API hits a rate limit, or a site blocks scraping. Maps every primary tool to its best fallback so a single failure doesn't block the search.
category: reference
summary: What to do when each tool fails. Tool-by-tool fallback paths.
---

# Fallback and Resilience

Tools go down. APIs break. Have a backup plan for every search.

| Primary Tool | When It Fails | Fallback |
|-------------|---------------|----------|
| Duffel | API error or timeout | Ignav, Google Flights skill, Skiplagged |
| Ignav | API error | Duffel, Google Flights skill, Skiplagged |
| Google Flights | agent-browser error | Duffel, Ignav, Skiplagged |
| Skiplagged | 502/timeout (Cloudflare issues) | Kiwi.com MCP, Duffel, Ignav |
| Kiwi.com | Server error | Skiplagged MCP, Duffel |
| Seats.aero | API error or stale data | Check airline website directly, use Duffel for GDS inventory |
| Southwest | SW rate limiting or bot detection | Wait a few minutes and retry. Use Docker (`ghcr.io/borski/sw-fares`) if running locally fails. Google Flights skill for SW cash prices as a fast fallback. |
| SerpAPI | Rate limit (100/mo free) | Trivago for hotels, web search for destination discovery |
| Trivago | Server error | LiteAPI for hotels, SerpAPI Google Hotels |
| LiteAPI | Auth error (401) | Trivago MCP, SerpAPI Google Hotels |
| Airbnb | Scraping blocked | Suggest user check airbnb.com directly |
| AwardWallet | API error | Ask user for their balances directly |
| Ferryhopper | Server error | SerpAPI or web search for ferry routes |
| Atlas Obscura | Script error | Web search for "unusual things to do in [destination]" |
| Chase Travel | Login failure or CSRF issues | Use Duffel/Ignav for cash prices. Note that Points Boost and Edit detection are Chase-only. |
| Amex Travel | Login failure or form changes | Use Duffel/Ignav for cash prices. Note that IAP fares and FHR/THC detection are Amex-only. |
| Deutsche Bahn (db-vendo) | Library error or bahn.de outage | SerpAPI Google Travel Explore, web search for "DB train [origin] [dest]", or fall back to confirming flight options instead. |
| Wikipedia airports | API rate limit (rare) or page missing | Web search "[airport name] airlines destinations" returns the same data via Google. |
| Fare tool says "no results" | Could be no availability OR no service | **Use `wikipedia-airports` to confirm whether the route is flown at all.** If Wikipedia lists the destination as served, fare tools have no availability on that date. If Wikipedia doesn't list it, the route doesn't exist. Saves you from asking the user to retry searches that can never succeed. |

## General Rules

- **If an MCP server returns an error,** try the curl-based skill equivalent (or vice versa).
- **If a paid API hits its rate limit,** switch to a free alternative.
- **Never give up after one tool fails.** Always try at least one fallback.
- **Tell the user which source you used.** "Skiplagged was down, so I checked Kiwi.com instead."

## IP Allowlist Errors (Common First-Time Failure)

Several APIs in the toolkit enforce IP allowlists on the developer key. If you see one of these error signatures, do NOT rabbit-hole on auth or quotas. Suggest the user whitelist their IP first.

| API | Error Signature | Whitelist Page |
|---|---|---|
| AwardWallet | `{"error": "access_denied", "code": "IP_DENIED"}` | https://business.awardwallet.com/profile/api |
| TripAdvisor | `User is not authorized to access this resource with an explicit deny` | https://www.tripadvisor.com/developers |

Diagnostic flow when an API call fails with an auth-shaped error on first use:

1. Run `curl ifconfig.me` to get the user's current outbound IP.
2. Check if the failure signature matches an IP allowlist (table above or similar phrasing like "explicit deny" / "IP_DENIED" / "not whitelisted").
3. Tell the user: "This looks like an IP allowlist issue, not a key issue. Add `<their IP>` at <provider page>, wait 1-5 min for AWS edge cache propagation, then retry."
4. While they whitelist, gracefully degrade: continue without that data source, noting it's pending. Don't block the rest of the workflow.
5. Multi-IP gotcha: residential CGNAT, VPN exits, hotel wifi, and travel locations all need separate entries. If they hit the same error from a new network, the IP changed.

## "No Cached Availability" Is Not the Final Word

When Seats.aero returns no results for a route + program combination, that means Seats.aero has not scraped it recently. It does NOT mean the award is unbookable. When a reachable program shows no cached results, search the airline's website directly before declaring awards dead.

## Patchright-Based Skills (Southwest, AA, Chase, Amex, TaW)

These hit websites directly with an undetected browser. Common failure modes:
- **Login form changed.** The site updated its DOM. Selectors break. Update the skill.
- **2FA loop.** Some skills (AA, Amex) handle email 2FA. Make sure 2FA delivery method is set correctly in the account.
- **Bot detection.** If you get "unusual activity" or CAPTCHA pages, the persistent profile may be flagged. Try a fresh profile or wait an hour.
- **Headless detection.** Patchright runs headed. If running locally fails, use the Docker image (xvfb provides virtual display).

## Docker Image Failures

If `docker pull ghcr.io/borski/...` fails:
- **`unauthorized`:** Run `docker logout ghcr.io` then retry. Or login with a GitHub PAT that has `read:packages`. Or build locally with `docker build -t <tag> skills/<skill>/`.
- **Network timeout:** Retry with `--platform linux/amd64` if you're on ARM and getting checksum mismatches.

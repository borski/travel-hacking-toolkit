---
name: fallback-and-resilience
description: Reference for what to do when a tool fails, an API hits a rate limit, or a website blocks scraping. Maps every primary tool to its best fallback so a single tool failure does not block the user. Load when an MCP returns an error, a curl command times out, a docker image fails to pull, a Patchright login is rejected, or a search returns no results suspiciously. Triggers on "tool failed", "API error", "rate limit", "fallback", "Skiplagged 502", "Kiwi server error", "Cloudflare blocked", "Seats.aero stale", "tried X but it failed", or any tool failure context.
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

## General Rules

- **If an MCP server returns an error,** try the curl-based skill equivalent (or vice versa).
- **If a paid API hits its rate limit,** switch to a free alternative.
- **Never give up after one tool fails.** Always try at least one fallback.
- **Tell the user which source you used.** "Skiplagged was down, so I checked Kiwi.com instead."

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

---
name: awardwallet
description: Query AwardWallet for loyalty program balances, elite status, and transaction history. Use when checking points inventory, airline status, or planning trips on points.
category: loyalty
summary: All loyalty balances, elite status, history.
api_key: AwardWallet Business
license: MIT
---

# AwardWallet Skill

Query loyalty program balances, elite status, and transaction history via the AwardWallet Business Account Access API.

**Source:** [business.awardwallet.com](https://business.awardwallet.com) — Requires a Business account.

## Authentication

Set these in your `.env` file:
- `AWARDWALLET_API_KEY` — Get from https://business.awardwallet.com/profile/api
- `AWARDWALLET_USER_ID` — Your connected user ID. Find it via the List Connected Users endpoint below.

All requests use the `X-Authentication` header.

> **First-time setup gotcha:** AwardWallet enforces an IP allowlist on Business API keys. Without your IP whitelisted, every call returns `{"error": "access_denied", "code": "IP_DENIED"}`. **Whitelist before troubleshooting.**
>
> - **Where to whitelist:** https://business.awardwallet.com/profile/api
> - **How to find your IP:** `curl ifconfig.me`
> - **Multi-IP:** home, office, hotspot, VPN exit nodes, and any travel locations each need their own entry. Easiest is to whitelist a /24 if you're on a stable residential ISP.

### Error signatures

| Response | Meaning | Fix |
|---|---|---|
| `{"error": "access_denied", "code": "IP_DENIED"}` | IP not on allowlist | Whitelist current IP at the developer portal |
| `Unauthorized` / 401 | Bad key | Regenerate key |
| Empty `accounts` array | User ID wrong or no connections | Verify `AWARDWALLET_USER_ID` |

## API Base

```
https://business.awardwallet.com/api/export/v1
```

## Quick Start: Get All Balances

```bash
curl -s -H "X-Authentication: $AWARDWALLET_API_KEY" \
  "https://business.awardwallet.com/api/export/v1/connectedUser/$AWARDWALLET_USER_ID" | jq '.accounts'
```

### Response Fields

Each account object contains:

| Field | Description |
|-------|-------------|
| `accountId` | Unique ID for deep dive |
| `code` | Provider code (e.g., "united", "chase", "amex") |
| `displayName` | Human name (e.g., "United Airlines (MileagePlus)") |
| `kind` | Category: Airlines, Hotels, Credit Cards, etc. |
| `balance` | Formatted balance string |
| `balanceRaw` | Numeric balance |
| `properties` | Array with status, account number, expiration, etc. |
| `history` | Last 10 transactions (call `/account/{id}` for full history) |
| `errorCode` | 1 = successfully updated, 2 = invalid creds, etc. |

### Useful jq Filters

All filters below assume the curl output is piped in. Replace `...` with the full curl command above.

```bash
# Just airline balances with status
... | jq '[.accounts[] | select(.kind == "Airlines") | {name: .displayName, balance: .balanceRaw, status: ((.properties // [])[] | select(.kind == 3) | .value) // "none"}]'

# Just hotel balances with status
... | jq '[.accounts[] | select(.kind == "Hotels") | {name: .displayName, balance: .balanceRaw, status: ((.properties // [])[] | select(.kind == 3) | .value) // "none"}]'

# Just credit card / transferable points
... | jq '[.accounts[] | select(.kind == "Credit Cards") | {name: .displayName, balance: .balanceRaw}]'

# All balances sorted by amount (descending), non-zero only
... | jq '[.accounts[] | {name: .displayName, kind: .kind, balance: .balanceRaw} | select(.balance > 0)] | sort_by(-.balance)'

# Elite status across all programs
... | jq '[.accounts[] | {name: .displayName, status: ((.properties // [])[] | select(.kind == 3) | .value) // null} | select(.status != null)]'

# Accounts with errors (need password update, etc.)
... | jq '[.accounts[] | select(.errorCode != 1) | {name: .displayName, error: .errorCode}]'

# Combined summary for trip planning (airlines + transferable points, non-zero, sorted)
... | jq '[.accounts[] | select((.kind == "Airlines" or .kind == "Credit Cards") and .balanceRaw > 0) | {name: .displayName, kind: .kind, balance: .balanceRaw, status: ((.properties // [])[] | select(.kind == 3) | .value) // null}] | sort_by(-.balance)'
```

## Deep Dive: Full Account History

For full transaction history (beyond last 10):

```bash
curl -s -H "X-Authentication: $AWARDWALLET_API_KEY" \
  "https://business.awardwallet.com/api/export/v1/account/{accountId}" | jq '.account[0].history'
```

## Travel Timeline

Get saved itineraries for a connected user:

```bash
curl -s -H "X-Authentication: $AWARDWALLET_API_KEY" \
  -X POST \
  -H "Content-Type: application/json" \
  -d '{"start": "2026-01-01", "end": "2027-01-01"}' \
  "https://business.awardwallet.com/api/export/v1/travel-timeline/$AWARDWALLET_USER_ID" | jq '.itineraries'
```

## List All Supported Providers

```bash
curl -s -H "X-Authentication: $AWARDWALLET_API_KEY" \
  "https://business.awardwallet.com/api/export/v1/providers/list" | jq '.'
```

## Account Property Kinds

When parsing `properties` arrays, these `kind` values are standardized:

| Kind | Meaning |
|------|---------|
| 1 | Account number |
| 2 | Expiration |
| 3 | Elite status |
| 4 | Lifetime points |
| 5 | Member since |
| 6 | Expiring balance |
| 7 | YTD Miles/Points |
| 8 | YTD Segments |
| 9 | Next elite level |
| 10 | Points needed to next level |
| 11 | Segments needed to next level |
| 12 | Name |
| 13 | Last activity |
| 14 | Points needed for next reward |
| 15 | Status expiration |
| 16 | Points to retain status |
| 17 | Segments to retain status |
| 18 | Alliance elite level |
| 19 | Status miles/points |

## Error Codes

| Code | Meaning |
|------|---------|
| 0 | Never updated |
| 1 | Success |
| 2 | Invalid credentials |
| 3 | Locked out |
| 4 | Provider error or user action needed |
| 5 | Provider disabled by AwardWallet |
| 6 | Parse failure |
| 7 | Password missing |
| 8 | Disabled to prevent lockouts |
| 9 | Success with warning |
| 10 | Security question needed |
| 11 | Timed out |

## Workflow: Trip Planning Summary

When planning a trip, run this workflow:

1. Pull all accounts
2. Filter to Airlines and Credit Cards (transferable points)
3. Show a clean summary: program name, balance, elite status
4. Note any accounts with errors that might need updating
5. Cross reference with transfer partners for the destination

## Notes

- History in user/member detail responses is capped at 10 records. Use `/account/{id}` for full history.
- `balanceRaw` is the numeric value. `balance` is formatted with commas.
- Connected users control their own access level. If data seems limited, they may have restricted sharing.
- SubAccounts exist for programs like Capital One where one login has multiple cards. Check `subAccounts` array.

---
name: american-airlines
description: Check American Airlines AAdvantage balance, elite status, and loyalty points via Patchright. Handles email 2FA with 6-box code entry. Uses persistent browser profiles to skip 2FA on subsequent runs.
---

# American Airlines AAdvantage

Check AAdvantage award miles balance, elite status (Gold/Platinum/Platinum Pro/Executive Platinum), loyalty points, and million miler status. Uses Patchright (undetected Playwright fork) because AA blocks standard browser automation.

**Requires Patchright.** AA.com blocks vanilla Playwright and agent-browser.

## Prerequisites

```bash
pip install patchright && patchright install chromium
```

Or use Docker (no local install needed):
```bash
docker build -t aa-check skills/american-airlines/
```

## Usage

Pass credentials via environment variables or flags. If you use a secrets manager (1Password, Vault, etc.), inject them however you normally would.

```bash
# Environment variables
AA_USERNAME=your_aa_number AA_PASSWORD=your_password \
  python3 scripts/check_balance.py --json

# Flags
python3 scripts/check_balance.py --username YOUR_AA_NUMBER --password YOUR_PASSWORD --json

# Docker
docker run --rm -e AA_USERNAME=your_aa_number -e AA_PASSWORD=your_password aa-check --json
```

## 2FA Handling

AA requires email verification on first login from a new device. The script waits up to 120 seconds for the code.

**You (the agent) do NOT have access to the user's email.** AA sends the 2FA code to the account holder's email address. When the script hits 2FA, you **MUST ask the user** for the 6-digit code. This is not optional. Do not try to read their email. Do not guess. Do not skip. Ask them, wait for the answer, then write it to the code file.

### Agent workflow

1. Run the script in the background (`nohup ... &`, `disown`)
2. Poll stderr for `"2FA REQUIRED"` to confirm the code was sent
3. **Ask the user** for the 6-digit code AA emailed them
4. Write the code to the code file: `echo "123456" > /tmp/aa-2fa-code.txt`
5. Wait for the script to complete and read stdout for the JSON result

### Persistent profiles (skip 2FA on repeat runs)

Use `--profile name` to save browser cookies. After the first successful 2FA, subsequent runs with the same profile skip 2FA entirely. Profiles are stored at `~/.aa-browser-profiles/{name}/`. Sessions last hours, not days.

```bash
# First run: will need 2FA
python3 scripts/check_balance.py --profile user1 --json

# Later runs: same profile, no 2FA
python3 scripts/check_balance.py --profile user1 --json
```

### Code input methods

- **File (default):** Script polls `/tmp/aa-2fa-code.txt` every 2 seconds. Write the 6-digit code there.
- **Direct flag:** `--code 123456` if you already have the code before running.
- **Custom file path:** `--code-file /path/to/code.txt`

## Output

```json
{
  "username": "XXXXXXX",
  "status": "completed",
  "miles": 123425,
  "elite_status": "Platinum Pro",
  "loyalty_points": 180,
  "name": "John Doe",
  "aadvantage_number": "XXXXXXX",
  "million_miler": 19328,
  "member_since": "Aug 23, 2011"
}
```

| Field | Description |
|-------|-------------|
| `miles` | Award miles balance (redeemable) |
| `elite_status` | Gold, Platinum, Platinum Pro, or Executive Platinum (null if none) |
| `loyalty_points` | Current year loyalty points (reset March 1) |
| `million_miler` | Lifetime miles toward Million Miler status |
| `member_since` | Account creation date |

## When to Use

- Checking AA miles balance (AwardWallet doesn't support AA)
- Verifying elite status tier and expiration
- Tracking loyalty points toward next status level
- Comparing AA award availability against balance (combine with seats-aero)

## When NOT to Use

- **Booking flights.** Read-only. Does not modify anything.
- **Other airlines.** Use AwardWallet for airlines it supports.

## Implementation Notes

- AA uses 6 separate input boxes for 2FA codes (one digit per box). The script types each digit individually with auto-advance.
- Cookie consent banners are removed via JS before interacting with the Verify button.
- The Verify button requires Tab+Enter to submit (neither JS `.click()` nor Playwright `.click()` produce a trusted pointer event that AA's React app accepts).
- `headless=False` is required. AA detects headless browsers even with Patchright. Docker uses xvfb for a virtual display.

## Limitations

- **2FA on first use per profile.** No way around it. AA sends an email code.
- **Session expiry.** Persistent profiles last hours, not days. Long gaps between runs may require 2FA again.
- **Headed mode required.** Opens a Chrome window locally. Use Docker for no popup.

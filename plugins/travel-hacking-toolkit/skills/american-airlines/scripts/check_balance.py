#!/usr/bin/env python3
"""Check American Airlines AAdvantage balance and elite status via Patchright.

Read-only. Logs in, reads the dashboard, outputs balance and status.
Handles email 2FA with 6-box code entry.
Uses a persistent browser profile so 2FA is only needed once per device.

Usage:
    python3 check_balance.py --username USER --password PASS --json
    python3 check_balance.py --username USER --password PASS --code 123456 --json

Environment variables (alternative to flags):
    AA_USERNAME     - AAdvantage number or login
    AA_PASSWORD     - Account password
    AA_2FA_COMMAND  - Optional: command to get email 2FA code (blocks, prints to stdout)
"""

import argparse
import json
import os
import re
import sys
import time


def log(msg):
    print(f"[aa] {msg}", file=sys.stderr)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Check AA AAdvantage balance and status"
    )
    parser.add_argument(
        "--username", default=os.environ.get("AA_USERNAME"), help="AA login"
    )
    parser.add_argument(
        "--password", default=os.environ.get("AA_PASSWORD"), help="AA password"
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output", help="Output JSON"
    )
    parser.add_argument("--profile", default="default", help="Browser profile name")
    parser.add_argument(
        "--code", default=None, help="2FA code (if known ahead of time)"
    )
    parser.add_argument(
        "--code-file", default="/tmp/aa-2fa-code.txt", help="File to read 2FA code from"
    )
    return parser.parse_args()


def wait_for_code(code_file, timeout=120):
    """Wait for a 2FA code via command hook or file polling."""
    import subprocess

    # Command hook: run a custom command that blocks until it has the code
    hook_cmd = os.environ.get("AA_2FA_COMMAND", "").strip()
    if hook_cmd:
        log("Running 2FA command hook...")
        try:
            result = subprocess.run(
                hook_cmd, shell=True, capture_output=True, text=True, timeout=timeout
            )
            code = result.stdout.strip()
            if code and len(code) == 6 and code.isdigit():
                log(f"Got 2FA code from hook: {code[:2]}****")
                return code
            log(f"Hook returned invalid code: {code[:10] if code else '(empty)'}")
        except Exception as e:
            log(f"2FA hook failed: {e}")

    # File polling fallback
    if os.path.exists(code_file):
        os.remove(code_file)

    log(f"2FA REQUIRED. Write 6-digit code to: {code_file}")
    log(f"Waiting up to {timeout}s for code...")

    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(code_file):
            with open(code_file, "r") as f:
                code = f.read().strip()
            if code and len(code) == 6 and code.isdigit():
                os.remove(code_file)
                return code
        time.sleep(2)
    return None


def dismiss_cookie_banner(page):
    """Remove cookie consent overlay via JS so it doesn't block clicks."""
    page.evaluate("""
        // OneTrust banner
        document.querySelectorAll('[class*="onetrust"], [id*="onetrust"]').forEach(el => el.remove());
        // Generic cookie banners
        document.querySelectorAll('[class*="cookie-banner"], [id*="cookie-banner"]').forEach(el => el.remove());
        // Backdrop overlays
        document.querySelectorAll('.onetrust-pc-dark-filter, [class*="overlay"]').forEach(el => {
            if (el.style && (el.style.position === 'fixed' || el.style.position === 'absolute')) {
                el.remove();
            }
        });
    """)
    log("Cleared cookie/consent overlays via JS")


def enter_2fa_code(page, code):
    """Enter 2FA code into AA's 6-box input and submit."""
    dismiss_cookie_banner(page)
    page.wait_for_timeout(500)

    # AA uses 6 separate input boxes, one digit per box.
    # They auto-advance on input. Click first box, type all digits.
    code_inputs = page.query_selector_all('input[type="text"]')
    visible_inputs = [el for el in code_inputs if el.is_visible()]
    log(f"Found {len(visible_inputs)} visible text inputs")

    if len(visible_inputs) >= 6:
        visible_inputs[0].click()
        page.wait_for_timeout(500)
        # Type each digit with delay for auto-advance
        for digit in code:
            page.keyboard.press(digit)
            page.wait_for_timeout(150)
        log(f"Typed code digit-by-digit across 6 boxes")
    elif len(visible_inputs) >= 1:
        visible_inputs[0].click()
        page.wait_for_timeout(300)
        for digit in code:
            page.keyboard.press(digit)
            page.wait_for_timeout(150)
        log(f"Typed code into {len(visible_inputs)} input(s)")
    else:
        log("ERROR: No visible text inputs found for 2FA code")
        return False

    # Wait for Verify button to enable
    page.wait_for_timeout(1500)
    dismiss_cookie_banner(page)

    # Click Verify button using Playwright's native click (produces trusted pointer events)
    verify_clicked = False

    # Get button coordinates via JS, then click at those coordinates
    coords = page.evaluate("""
        const buttons = Array.from(document.querySelectorAll('button, [role="button"]'));
        const verify = buttons.find(b => b.textContent.includes('Verify'));
        if (verify) {
            const rect = verify.getBoundingClientRect();
            ({x: rect.x + rect.width / 2, y: rect.y + rect.height / 2});
        } else {
            null;
        }
    """)

    if coords:
        page.mouse.click(coords["x"], coords["y"])
        log(f"Clicked Verify at ({coords['x']:.0f}, {coords['y']:.0f})")
        verify_clicked = True
    else:
        # Fallback: Tab from last code input to Verify button and press Enter
        log("No Verify button found via JS. Trying Tab+Enter...")
        page.keyboard.press("Tab")
        page.wait_for_timeout(200)
        page.keyboard.press("Tab")
        page.wait_for_timeout(200)
        page.keyboard.press("Enter")
        log("Submitted via Tab+Enter")

    return True


def is_on_2fa_page(page):
    """Check if the current page is the 2FA verification page."""
    try:
        url = page.url
        if "login.aa.com" not in url:
            return False
        # Check body text for verification indicators
        body = page.text_content("body") or ""
        lower = body.lower()
        if "verification code" in lower or "verify" in lower:
            return True
        # Check for 6 text inputs (code boxes)
        inputs = page.query_selector_all('input[type="text"]')
        visible = [el for el in inputs if el.is_visible()]
        if len(visible) >= 6:
            return True
    except Exception:
        pass
    return False


def wait_for_post_login(page, timeout=15000):
    """Wait for either 2FA page or successful login redirect."""
    log("Waiting for login response...")
    start = time.time()
    while (time.time() - start) * 1000 < timeout:
        # Check if we hit 2FA
        if is_on_2fa_page(page):
            return "2fa"
        # Check if we're logged in (redirected away from login)
        url = page.url
        if "login.aa.com" not in url and "aa.com" in url:
            return "logged_in"
        page.wait_for_timeout(1000)
    # Final check
    if is_on_2fa_page(page):
        return "2fa"
    return "unknown"


def extract_account_data(page, result):
    """Extract miles, status, and other data from the account page."""
    log("Extracting account data...")
    body = page.text_content("body") or ""

    # Use JS to extract structured data via DOM elements (not text regex)
    data = page.evaluate("""
        const result = {};
        const body = document.body.textContent || '';

        // Strategy: walk the DOM tree and find labeled sections.
        // AA's account page has three panels with specific content.

        // Award miles: find element containing "Award miles" or "Award Miles" label,
        // then get the large number nearby
        const allElements = Array.from(document.querySelectorAll('*'));

        // Find award miles by looking for the number displayed near "Award Miles" text
        for (const el of allElements) {
            const text = el.textContent.trim();
            if (text === 'Award miles balance' || text === 'Award Miles') {
                // The number is likely a sibling or nearby element
                const parent = el.closest('div, section, td') || el.parentElement;
                if (parent) {
                    const nums = parent.textContent.match(/([\\d,]{3,})/g);
                    if (nums) {
                        // Take the largest number (award miles balance)
                        const values = nums.map(n => parseInt(n.replace(/,/g, '')));
                        result.miles = String(Math.max(...values));
                    }
                }
                break;
            }
        }

        // Fallback: regex on body
        if (!result.miles) {
            const m = body.match(/Award\\s*miles\\s*(?:balance)?[\\s:]*(\\d[\\d,]*)/i);
            if (m) result.miles = m[1].replace(/,/g, '');
        }

        // Status: look for "AAdvantage [tier]®" with "Valid through" nearby
        const statusMatch = body.match(/AAdvantage\\s*(Executive Platinum|Platinum Pro|Platinum|Gold)[®™]?[\\s\\S]{0,30}Valid through/i);
        if (statusMatch) {
            result.status = statusMatch[1];
        } else {
            // Broader match
            const sm = body.match(/AAdvantage\\s*(Executive Platinum|Platinum Pro|Platinum|Gold)[®™]/i);
            if (sm) result.status = sm[1];
        }

        // Loyalty Points: find the element containing "Loyalty Points" label,
        // get the number that's its own element (not part of the tracker)
        for (const el of allElements) {
            const text = el.textContent.trim();
            if (text === 'Loyalty Points' || text.match(/^Loyalty Points/)) {
                // Look at previous sibling or parent for the number
                let prev = el.previousElementSibling;
                if (prev) {
                    const num = prev.textContent.trim().replace(/,/g, '');
                    if (/^\\d+$/.test(num)) {
                        result.lp = num;
                        break;
                    }
                }
                // Try parent and find the standalone number
                const parent = el.closest('div, section') || el.parentElement;
                if (parent) {
                    // Get direct child text nodes / elements with just numbers
                    for (const child of parent.children) {
                        const t = child.textContent.trim().replace(/,/g, '');
                        if (/^\\d+$/.test(t) && !child.textContent.includes('Award') && !child.textContent.includes('miles')) {
                            result.lp = t;
                            break;
                        }
                    }
                }
                break;
            }
        }

        // Fallback LP: regex looking for small number before "Loyalty Points"
        if (!result.lp) {
            // Match all "N Loyalty Points" occurrences, take the smallest (likely actual LP, not tracker)
            const lpMatches = [...body.matchAll(/(\\d[\\d,]*)\\s*Loyalty\\s*Points/gi)];
            if (lpMatches.length > 0) {
                const values = lpMatches.map(m => ({raw: m[1], val: parseInt(m[1].replace(/,/g, ''))}));
                const smallest = values.reduce((a, b) => a.val < b.val ? a : b);
                result.lp = String(smallest.val);
            }
        }

        // AAdvantage number: look for #XXXXX pattern
        const aaMatch = body.match(/#(\\w{5,})/);
        if (aaMatch) result.aa_number = aaMatch[1];

        // Member since
        const sinceMatch = body.match(/member since[:\\s]*(\\w+ \\d+,? \\d{4})/i);
        if (sinceMatch) result.member_since = sinceMatch[1];

        // Million Miler
        const mmMatch = body.match(/Million Miler[:\\s]*(\\d[\\d,]*)/i);
        if (mmMatch) result.million_miler = mmMatch[1].replace(/,/g, '');

        // Name: look for text before "Citi" or "card member"
        const nameMatch = body.match(/([A-Z][a-z]+ [A-Z][a-z]+\\w*)\\s*\\n?\\s*(?:Citi|AAdvantage|card member)/);
        if (nameMatch) result.name = nameMatch[1];

        result;
    """)

    log(f"JS extraction: {json.dumps(data)}")

    if data.get("miles"):
        result["miles"] = int(data["miles"])
        log(f"Found award miles: {result['miles']:,}")

    if data.get("status"):
        result["elite_status"] = data["status"]
        log(f"Found status: {result['elite_status']}")

    if data.get("lp"):
        result["loyalty_points"] = int(data["lp"])
        log(f"Found loyalty points: {result['loyalty_points']:,}")

    if data.get("aa_number"):
        result["aadvantage_number"] = data["aa_number"]

    if data.get("million_miler"):
        result["million_miler"] = int(data["million_miler"])

    if data.get("member_since"):
        result["member_since"] = data["member_since"]

    if data.get("name"):
        result["name"] = data["name"]

    # Fallback: regex on body text if JS extraction missed miles
    if result["miles"] is None:
        for pattern in [
            r"Award\s*miles\s*(?:balance)?[\s:]*([\d,]+)",
            r"([\d,]+)\s*Award\s*[Mm]iles",
        ]:
            match = re.search(pattern, body, re.IGNORECASE)
            if match:
                val = int(match.group(1).replace(",", ""))
                if val > 100:
                    result["miles"] = val
                    log(f"Found award miles (fallback): {val:,}")
                    break

    return body


def main():
    args = parse_args()
    if not args.username or not args.password:
        print("Error: username and password required", file=sys.stderr)
        sys.exit(1)

    log(f"Credentials loaded (user length: {len(args.username)})")

    try:
        from patchright.sync_api import sync_playwright
    except ImportError:
        print(
            "Error: pip install patchright && patchright install chromium",
            file=sys.stderr,
        )
        sys.exit(1)

    profile_dir = os.path.expanduser(f"~/.aa-browser-profiles/{args.profile}")
    os.makedirs(profile_dir, exist_ok=True)
    log(f"Using profile: {profile_dir}")

    result = {
        "username": args.username,
        "status": "failed",
        "miles": None,
        "elite_status": None,
        "loyalty_points": None,
        "name": None,
    }

    with sync_playwright() as p:
        # Use system Chrome if available, fall back to bundled Chromium (Docker)
        launch_args = dict(
            user_data_dir=profile_dir,
            headless=False,
            viewport={"width": 1280, "height": 800},
        )
        # Check if system Chrome exists
        chrome_paths = [
            "/opt/google/chrome/chrome",
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        ]
        has_chrome = any(os.path.exists(p_) for p_ in chrome_paths)
        if has_chrome:
            launch_args["channel"] = "chrome"
        ctx = p.chromium.launch_persistent_context(**launch_args)
        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        try:
            # Step 1: Homepage
            log("Navigating to aa.com...")
            page.goto("https://www.aa.com/", wait_until="networkidle", timeout=30000)

            if "Access Denied" in page.title():
                result["error"] = "Bot detection blocked access"
                _output(result, args.json_output)
                return

            # Check if already logged in
            body = page.text_content("body") or ""
            already_logged_in = "Log out" in body or "Sign out" in body

            if not already_logged_in:
                # Step 2: Login
                log("Clicking login...")
                for sel in [
                    "text=Log in",
                    'a[href*="login"]',
                    'button:has-text("Log in")',
                ]:
                    btn = page.query_selector(sel)
                    if btn and btn.is_visible():
                        btn.click()
                        break
                page.wait_for_timeout(3000)

                # Step 3: Fill credentials
                log("Filling credentials...")
                for sel in [
                    "input#loginId",
                    'input[name="loginId"]',
                    'input[type="text"]',
                ]:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        page.fill(sel, args.username)
                        log(f"Filled username via: {sel}")
                        break

                for sel in [
                    "input#password",
                    'input[name="password"]',
                    'input[type="password"]',
                ]:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        page.fill(sel, args.password)
                        log(f"Filled password via: {sel}")
                        break

                # Submit
                submitted = False
                for sel in [
                    'button[type="submit"]',
                    'button:has-text("Log in")',
                    'button:has-text("Sign in")',
                    'input[type="submit"]',
                ]:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        page.click(sel)
                        log(f"Submitted via: {sel}")
                        submitted = True
                        break
                if not submitted:
                    page.keyboard.press("Enter")
                    log("Submitted via Enter key")

                # Step 4: Wait for response (2FA or success)
                login_result = wait_for_post_login(page, timeout=15000)
                log(f"Login result: {login_result}")

                if login_result == "2fa":
                    log("2FA page detected")

                    # Get the code
                    code = args.code
                    if not code:
                        code = wait_for_code(args.code_file)
                    if not code:
                        result["status"] = "2fa_required"
                        result["error"] = "2FA code not provided"
                        _output(result, args.json_output)
                        return

                    # Enter the code
                    if not enter_2fa_code(page, code):
                        result["error"] = "Failed to enter 2FA code"
                        _output(result, args.json_output)
                        return

                    # Wait for 2FA to complete
                    log("Waiting for 2FA verification...")
                    page.wait_for_timeout(8000)

                    # Check if still on 2FA page (code rejected)
                    if is_on_2fa_page(page):
                        log("Still on 2FA page. Code may have been rejected.")
                        page.screenshot(path="/tmp/aa-debug.png", full_page=True)
                        result["error"] = (
                            "2FA code rejected or Verify button not clicked"
                        )
                        result["status"] = "2fa_failed"
                        _output(result, args.json_output)
                        return

                    log(f"Post-2FA URL: {page.url}")

                elif login_result == "unknown":
                    log("Login state unclear, continuing anyway...")

            # Step 5: Navigate to account summary
            log("Navigating to account summary...")
            page.goto(
                "https://www.aa.com/aadvantage-program/profile/account-summary",
                wait_until="networkidle",
                timeout=25000,
            )
            page.wait_for_timeout(5000)

            # Check if we got redirected back to login (not authenticated)
            if "login.aa.com" in page.url:
                log("Redirected to login. Authentication failed.")
                page.screenshot(path="/tmp/aa-debug.png", full_page=True)
                result["error"] = "Not authenticated after login flow"
                _output(result, args.json_output)
                return

            # Step 6: Extract data
            body = extract_account_data(page, result)

            if result["miles"] is not None:
                result["status"] = "completed"
            else:
                log("Could not extract miles. Taking debug screenshot...")
                page.screenshot(path="/tmp/aa-debug.png", full_page=True)
                log(f"Current URL: {page.url}")
                log(f"Page text (first 1500 chars): {body[:1500]}")
                result["status"] = "partial"
                result["error"] = "Could not parse miles balance"

        except Exception as e:
            log(f"Error: {e}")
            result["status"] = "error"
            result["error"] = str(e)
        finally:
            ctx.close()

    _output(result, args.json_output)


def _output(result, as_json):
    if as_json:
        print(json.dumps(result, indent=2))
    else:
        if result["status"] == "completed":
            print(f"Account: {result.get('aadvantage_number', result['username'])}")
            if result.get("name"):
                print(f"Name: {result['name']}")
            print(f"Miles: {result['miles']:,}")
            if result.get("elite_status"):
                print(f"Status: {result['elite_status']}")
            if result.get("loyalty_points"):
                print(f"Loyalty Points: {result['loyalty_points']:,}")
        elif result["status"] == "2fa_required":
            print(f"2FA required. Write 6-digit code to /tmp/aa-2fa-code.txt")
        else:
            print(f"Failed: {result.get('error', 'unknown')}")


if __name__ == "__main__":
    main()

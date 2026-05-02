#!/usr/bin/env python3
"""
Amex Travel portal search via Patchright.

Submits search form, follows redirects through Amex login gate,
then extracts window.appData (627KB Redux store) from the results page.
All flight/hotel data is server-side rendered into this single JSON blob.

Usage:
    # Flight search (local, pops up Chrome window)
    python3 search_flights.py --origin SFO --dest CDG --depart 2026-08-11

    # Round-trip business
    python3 search_flights.py --origin SFO --dest CDG --depart 2026-08-11 --return 2026-09-02 --cabin business

    # Hotel search
    python3 search_flights.py --hotel --dest "Paris" --checkin 2026-08-11 --checkout 2026-08-15

    # Record mode: capture network traffic during manual search
    python3 search_flights.py --record

    # JSON output
    python3 search_flights.py --origin SFO --dest CDG --depart 2026-08-11 --json

Environment:
    AMEX_USERNAME   - Amex online username
    AMEX_PASSWORD   - Amex online password
    AMEX_PROFILE     - Profile directory (default: ~/.amex-travel-profiles/default)
    AMEX_2FA_COMMAND - Optional: command to run to get email 2FA code (blocks until code ready, returns on stdout)
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path


# Amex Travel URLs
AMEX_LOGIN_URL = "https://www.americanexpress.com/en-us/account/login"
AMEX_TRAVEL_URL = "https://www.americanexpress.com/en-us/travel"
AMEX_FLIGHTS_URL = "https://www.americanexpress.com/en-us/travel/flights"
AMEX_HOTELS_URL = "https://www.americanexpress.com/en-us/travel/hotels"


# ============================================================
# Auth helpers
# ============================================================


def get_profile_dir():
    env_dir = os.environ.get("AMEX_PROFILE")
    if env_dir:
        return env_dir
    return str(Path.home() / ".amex-travel-profiles" / "default")


def get_cookie_path():
    # In Docker, cookies are mounted at /profiles/cookies.json
    if Path("/profiles/cookies.json").exists():
        return "/profiles/cookies.json"
    profile = get_profile_dir()
    return os.path.join(os.path.dirname(profile), "cookies.json")


def save_cookies(context, path):
    cookies = context.cookies()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(cookies, f, indent=2)
    print(f"Saved {len(cookies)} cookies to {path}", file=sys.stderr)


def inject_cookies(context, path):
    if not os.path.exists(path):
        return False
    with open(path) as f:
        cookies = json.load(f)
    if not cookies:
        return False
    amex_cookies = [
        c
        for c in cookies
        if "americanexpress.com" in c.get("domain", "")
        or "amextravel.com" in c.get("domain", "")
    ]
    if amex_cookies:
        context.add_cookies(amex_cookies)
        print(f"Injected {len(amex_cookies)} Amex cookies", file=sys.stderr)
        return True
    return False


def is_logged_in(page):
    url = page.url.lower()
    if "/login" in url or "/logon" in url:
        return False
    try:
        text = page.inner_text("body")[:3000].lower()
        if "log out" in text or "sign out" in text:
            return True
        if "membership rewards" in text and any(c.isdigit() for c in text[:500]):
            return True
        if "/travel" in url and (
            "search" in text or "flights" in text or "hotels" in text
        ):
            return True
    except Exception:
        pass
    return False


def wait_for_2fa_code(timeout=120):
    """Wait for 2FA code via command hook or file polling.

    If AMEX_2FA_COMMAND is set, runs it and uses stdout as the code.
    Otherwise falls back to polling /tmp/amex-2fa-code.txt.
    """
    # Command hook: run a custom command that blocks until it has the code
    hook_cmd = os.environ.get("AMEX_2FA_COMMAND", "").strip()
    if hook_cmd:
        print(f"Running 2FA command hook...", file=sys.stderr)
        try:
            result = subprocess.run(
                hook_cmd, shell=True, capture_output=True, text=True, timeout=timeout
            )
            code = result.stdout.strip()
            if code:
                print(f"Got 2FA code from hook: {code[:2]}****", file=sys.stderr)
                return code
            print(
                "2FA hook returned empty, falling back to file polling", file=sys.stderr
            )
        except Exception as e:
            print(
                f"2FA hook failed: {e}, falling back to file polling", file=sys.stderr
            )

    # File-based code exchange
    code_file = "/tmp/amex-2fa-code.txt"
    try:
        with open("/tmp/amex-2fa-status.txt", "w") as f:
            f.write("CODE_NEEDED")
    except OSError:
        pass
    print("2FA_CODE_NEEDED", flush=True)
    print("2FA REQUIRED: Write code to /tmp/amex-2fa-code.txt", file=sys.stderr)

    start = time.time()
    while time.time() - start < timeout:
        if os.path.exists(code_file):
            with open(code_file) as f:
                code = f.read().strip()
            if code:
                try:
                    os.remove(code_file)
                except OSError:
                    pass
                return code
        time.sleep(2)
    return None


def handle_2fa(page):
    try:
        text = page.inner_text("body")[:3000].lower()
    except Exception:
        return True

    is_2fa = (
        "verification code" in text
        or "confirm your identity" in text
        or "one-time password" in text
        or ("enter" in text and "code" in text and "verify" in text)
    )
    if not is_2fa:
        return True

    print("2FA detected. Selecting email method...", file=sys.stderr)

    for sel in [
        'button:has-text("email")',
        '[data-testid*="email"]',
        'label:has-text("email")',
    ]:
        btn = page.query_selector(sel)
        if btn:
            btn.click()
            time.sleep(3)
            break

    for label in ["Send", "Continue", "Next", "Send Code"]:
        btn = page.query_selector(f'button:has-text("{label}")')
        if btn and btn.is_visible():
            btn.click()
            time.sleep(5)
            break

    code = wait_for_2fa_code()
    if not code:
        print("ERROR: No 2FA code within timeout.", file=sys.stderr)
        return False

    print(f"Got 2FA code: {code[:2]}****", file=sys.stderr)

    for sel in [
        "#question-value",
        "input[name*='code']",
        "input[type='tel']",
        "input[id*='code']",
        "input[id*='verification']",
    ]:
        inp = page.query_selector(sel)
        if inp:
            inp.click()
            time.sleep(0.3)
            inp.type(code, delay=50)
            break

    time.sleep(1)

    for sel in [
        'button:has-text("Verify")',
        'button:has-text("Submit")',
        'button[type="submit"]',
    ]:
        btn = page.query_selector(sel)
        if btn:
            btn.click()
            break
    else:
        page.keyboard.press("Enter")

    time.sleep(10)

    try:
        body = page.inner_text("body")[:2000].lower()
        if "add this device" in body or "remember" in body or "trust" in body:
            for label in ["Add This Device", "Yes", "Remember", "Trust"]:
                btn = page.query_selector(f'button:has-text("{label}")')
                if btn and btn.is_visible():
                    btn.click()
                    time.sleep(5)
                    break
    except Exception:
        pass

    return is_logged_in(page)


def login(page, context, username, password, cookie_path):
    if inject_cookies(context, cookie_path):
        page.goto(AMEX_FLIGHTS_URL, timeout=30000)
        time.sleep(8)
        # Check if we're actually on the flights page or got redirected to login
        url = page.url.lower()
        if "/login" not in url and "/logon" not in url:
            if is_logged_in(page):
                print("Logged in via saved cookies", file=sys.stderr)
                return True
        # Cookies didn't work for travel portal
        print(
            "Saved cookies expired or not valid for travel portal, fresh login",
            file=sys.stderr,
        )

    page.goto(AMEX_LOGIN_URL, timeout=30000)
    time.sleep(5)

    for sel in ["#eliloUserID", 'input[name="UserID"]', 'input[id*="user"]']:
        inp = page.query_selector(sel)
        if inp:
            inp.fill(username)
            break
    else:
        print("ERROR: No username input", file=sys.stderr)
        return False

    time.sleep(0.5)

    for sel in ["#eliloPassword", 'input[name="Password"]', 'input[type="password"]']:
        inp = page.query_selector(sel)
        if inp:
            inp.fill(password)
            break
    else:
        print("ERROR: No password input", file=sys.stderr)
        return False

    time.sleep(0.5)

    btn = page.query_selector("#loginSubmit") or page.query_selector(
        'button[type="submit"]'
    )
    if btn:
        btn.click()
    else:
        page.keyboard.press("Enter")

    time.sleep(10)

    if not handle_2fa(page):
        return False

    if is_logged_in(page):
        save_cookies(context, cookie_path)
        return True

    url = page.url.lower()
    if "/dashboard" in url or "/account" in url or "/summary" in url:
        save_cookies(context, cookie_path)
        return True

    return False


# ============================================================
# Search via form submission + window.appData extraction
# ============================================================


# ============================================================
# Travel portal login gate (separate from main Amex login)
# ============================================================


def _handle_travel_login_gate(page, username=None, password=None):
    """Handle the travel portal login interstitial.

    After submitting a search, Amex redirects through /account/travel/login
    which requires re-authentication even if already logged into americanexpress.com.
    This is a separate auth gate for the iSeatz/amextravel.com backend.
    """
    url = page.url.lower()
    if "/login" not in url and "/logon" not in url:
        return True

    print("  Handling travel portal login gate...", file=sys.stderr)

    if not username or not password:
        username = os.environ.get("AMEX_USERNAME", "")
        password = os.environ.get("AMEX_PASSWORD", "")

    if not username or not password:
        print("  ERROR: No credentials for travel login gate", file=sys.stderr)
        return False

    # Fill username
    filled_user = False
    for sel in [
        "#eliloUserID",
        'input[name="UserID"]',
        'input[id*="user" i]',
        'input[id*="userId" i]',
        'input[type="text"]',
    ]:
        inp = page.query_selector(sel)
        if inp and inp.is_visible():
            inp.fill(username)
            filled_user = True
            print("  Filled username on interstitial", file=sys.stderr)
            break

    if not filled_user:
        # Maybe it's a different kind of gate (just a continue button)
        for label in ["Continue", "Proceed", "Log In", "Sign In"]:
            btn = page.query_selector(
                f'button:has-text("{label}"), a:has-text("{label}")'
            )
            if btn and btn.is_visible():
                btn.click()
                print(f"  Clicked '{label}' on interstitial", file=sys.stderr)
                page.wait_for_timeout(5000)
                return "/login" not in page.url.lower()
        print("  WARNING: No username field or continue button found", file=sys.stderr)
        # Dump what we see
        try:
            text = page.inner_text("body")[:2000]
            print(f"  Page text: {text[:300]}", file=sys.stderr)
        except Exception:
            pass
        return False

    page.wait_for_timeout(500)

    # Fill password
    for sel in [
        "#eliloPassword",
        'input[name="Password"]',
        'input[type="password"]',
    ]:
        inp = page.query_selector(sel)
        if inp and inp.is_visible():
            inp.fill(password)
            print("  Filled password on interstitial", file=sys.stderr)
            break

    page.wait_for_timeout(500)

    # Submit
    btn = page.query_selector("#loginSubmit") or page.query_selector(
        'button[type="submit"]'
    )
    if btn:
        btn.click()
    else:
        page.keyboard.press("Enter")

    print("  Submitted interstitial login. Waiting...", file=sys.stderr)
    page.wait_for_timeout(10000)

    # Handle 2FA if triggered
    if not handle_2fa(page):
        print("  WARNING: 2FA on interstitial may have failed", file=sys.stderr)

    # Check if we made it through
    url = page.url.lower()
    if "/login" not in url:
        print("  Travel login gate passed!", file=sys.stderr)
        return True

    print(f"  Still on login page: {url[:100]}", file=sys.stderr)
    return False


# ============================================================
# DOM form filling helpers
# ============================================================


def _fill_airport_field(page, selector, code):
    """Type airport code into an input and pick the first autocomplete suggestion."""
    inp = page.query_selector(selector)
    if not inp:
        # Try broader selectors
        for alt in [
            f'input[placeholder*="airport"]',
            f'input[placeholder*="city"]',
            f'input[aria-label*="airport"]',
        ]:
            inp = page.query_selector(alt)
            if inp:
                break
    if not inp:
        print(f"  WARNING: Airport input not found: {selector}", file=sys.stderr)
        return False

    inp.click()
    page.wait_for_timeout(300)
    # Clear existing value
    page.evaluate(
        """(sel) => {
        const el = document.querySelector(sel);
        if (el) { el.value = ''; el.dispatchEvent(new Event('input', {bubbles: true})); }
    }""",
        selector,
    )
    page.wait_for_timeout(300)
    inp.type(code, delay=80)
    page.wait_for_timeout(2500)  # Wait for autocomplete dropdown

    # Click the first autocomplete suggestion
    for suggestion_sel in [
        '[role="option"]:first-child',
        'li[role="option"]:first-child',
        ".autocomplete-suggestion:first-child",
        '[class*="suggestion"]:first-child',
        '[data-testid*="suggestion"]',
        '[class*="dropdown"] li:first-child',
        '[class*="Dropdown"] li:first-child',
    ]:
        suggestion = page.query_selector(suggestion_sel)
        if suggestion and suggestion.is_visible():
            suggestion.click()
            print(f"  Picked suggestion for {code}", file=sys.stderr)
            page.wait_for_timeout(500)
            return True

    # Fallback: press Enter to accept first suggestion or use typed value
    print(f"  No suggestion found, pressing Enter for {code}", file=sys.stderr)
    page.keyboard.press("Enter")
    page.wait_for_timeout(500)
    return True


def _parse_date(date_str):
    """Parse YYYY-MM-DD into (year, month, day) ints."""
    parts = date_str.split("-")
    return int(parts[0]), int(parts[1]), int(parts[2])


MONTH_NAMES = [
    "",
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
]


def _pick_date_from_calendar(page, target_date):
    """Navigate the Amex calendar popup and click the target date.

    Assumes the calendar is already open. Navigates forward/back to the
    target month, then clicks the day button.
    """
    year, month, day = _parse_date(target_date)
    target_month_name = MONTH_NAMES[month]

    # Amex calendar uses div[role="button"] with class pattern:
    #   automation-date-picker-month-{year}-{month}
    # Days inside are div[role="button"] with class _calendarDay_ and text = day number.
    # Standard <button> selectors won't work. Use JS clicks.

    page.wait_for_timeout(500)

    # First, scroll the calendar to the target month by clicking "Next Month"
    # Look for the target month container
    month_sel = f'[class*="automation-date-picker-month-{year}-{month}"]'

    for nav_attempt in range(14):
        month_container = page.query_selector(month_sel)
        if month_container:
            break

        # Click next month button (it's a div, not a button, so use JS)
        scrolled = page.evaluate("""() => {
            // Look for "Next Month" text or arrow buttons in the calendar
            const btns = document.querySelectorAll('[class*="date-picker"] [role="button"], [class*="date-picker"] button, [class*="calendar"] button');
            for (const b of btns) {
                const text = b.textContent?.trim() || '';
                const label = b.getAttribute('aria-label') || '';
                if (text.includes('Next Month') || label.includes('next') || label.includes('Next')) {
                    b.click();
                    return true;
                }
            }
            // Try any element with "next" in class
            const nexts = document.querySelectorAll('[class*="next"], [class*="Next"]');
            for (const n of nexts) {
                if (n.offsetParent !== null) { n.click(); return true; }
            }
            return false;
        }""")
        if not scrolled:
            print(f"  Nav attempt {nav_attempt}: no next button found", file=sys.stderr)
        page.wait_for_timeout(600)

    # Now find and click the day within the month container
    clicked = page.evaluate(
        """(args) => {
        const [year, month, day] = args;
        const monthSel = `[class*="automation-date-picker-month-${year}-${month}"]`;
        const container = document.querySelector(monthSel);
        if (!container) return 'no_container';

        // Find day elements (div[role="button"] with _calendarDay_ class)
        const days = container.querySelectorAll('[role="button"]');
        for (const d of days) {
            const text = d.textContent?.trim();
            if (text === String(day)) {
                d.click();
                return 'clicked';
            }
        }
        return 'no_day';
    }""",
        [year, month, day],
    )

    if clicked == "clicked":
        print(f"  Selected {target_month_name} {day}, {year}", file=sys.stderr)
        page.wait_for_timeout(500)
        return True

    print(f"  WARNING: Calendar pick failed: {clicked}", file=sys.stderr)
    return False


def _fill_date_field(page, trigger_selector, target_date):
    """Click a date trigger button, then pick the date from the calendar popup."""
    trigger = page.query_selector(trigger_selector)
    if not trigger:
        print(
            f"  WARNING: Date trigger not found: {trigger_selector}",
            file=sys.stderr,
        )
        return False

    # Wait for the button to become enabled (React may need time after airport fill)
    for wait_i in range(10):
        try:
            enabled = page.evaluate(
                "(sel) => { const el = document.querySelector(sel); return el && !el.disabled; }",
                trigger_selector,
            )
            if enabled:
                break
        except Exception:
            pass
        page.wait_for_timeout(1000)
        if wait_i == 4:
            print("  Waiting for date picker to enable...", file=sys.stderr)

    # Try normal click first, fall back to JS click
    try:
        trigger.click(timeout=5000)
    except Exception:
        print("  Date button disabled, trying JS click...", file=sys.stderr)
        page.evaluate(
            "(sel) => document.querySelector(sel)?.click()",
            trigger_selector,
        )

    page.wait_for_timeout(1500)

    # Verify calendar opened by looking for calendar elements
    calendar = page.query_selector(
        '[class*="calendar"], [class*="Calendar"], [role="grid"], [class*="datepicker"]'
    )
    if not calendar:
        # Try clicking the label instead
        label_id = trigger_selector.replace(
            "button#date-picker-popup-button-", "input-"
        )
        label = page.query_selector(f"label#{label_id}")
        if label:
            print("  Trying label click to open calendar...", file=sys.stderr)
            label.click()
            page.wait_for_timeout(1500)

    return _pick_date_from_calendar(page, target_date)


def search_flights_dom(
    page,
    origin,
    dest,
    depart,
    return_date=None,
    cabin="Economy",
    username=None,
    password=None,
):
    """Fill the visible Amex Travel search form and submit it.

    Returns appData from the results page, or None on failure.
    """
    # Always navigate directly to flights page (most reliable)
    if "/travel/flights" not in page.url.lower():
        page.goto(AMEX_FLIGHTS_URL, timeout=30000)
        page.wait_for_timeout(8000)

    # Debug: dump current page state
    current_url = page.url
    print(f"  On page: {current_url[:100]}", file=sys.stderr)

    # If we're stuck on a login gate, we can't fill the form
    if "/login" in current_url.lower():
        print("  ERROR: Still on login gate. Cannot fill search form.", file=sys.stderr)
        return None

    # Dump visible form elements for debugging
    try:
        inputs = page.evaluate(
            """() => {
            const els = document.querySelectorAll('input, select, button');
            return Array.from(els).slice(0, 60).map(el => ({
                tag: el.tagName,
                type: el.type || '',
                name: el.name || '',
                id: el.id || '',
                ariaLabel: el.getAttribute('aria-label') || '',
                placeholder: el.placeholder || '',
                text: el.textContent?.trim().slice(0, 50) || '',
                visible: el.offsetParent !== null
            }));
        }"""
        )
        visible = [i for i in inputs if i.get("visible")]
        # Show form inputs
        form_els = [i for i in visible if i["tag"] != "BUTTON" or i.get("text")]
        print(
            f"  Found {len(visible)} visible elements ({len(form_els)} with content):",
            file=sys.stderr,
        )
        for inp in form_els[:20]:
            label = (
                inp.get("ariaLabel")
                or inp.get("placeholder")
                or inp.get("text", "")[:30]
            )
            print(
                f'    <{inp["tag"].lower()} type={inp["type"]} id={inp["id"][:50]} label="{label}">',
                file=sys.stderr,
            )
    except Exception as e:
        print(f"  Form element dump failed: {e}", file=sys.stderr)

    # Dump date-related and search elements specifically
    try:
        extras = page.evaluate(
            """() => {
            const all = document.querySelectorAll('*');
            const found = [];
            for (const el of all) {
                const id = el.id || '';
                const al = el.getAttribute('aria-label') || '';
                const txt = el.textContent?.trim().slice(0, 40) || '';
                const tag = el.tagName;
                const role = el.getAttribute('role') || '';
                const cls = el.className?.toString?.().slice(0, 60) || '';
                // Look for date-related, search, or depart/return elements
                const match = (id + al + cls).toLowerCase();
                if (match.includes('date') || match.includes('depart') ||
                    match.includes('return') || match.includes('calendar') ||
                    (match.includes('search') && !match.includes('header')) ||
                    al.toLowerCase().includes('search flight')) {
                    if (el.offsetParent !== null || el.offsetHeight > 0) {
                        found.push({tag, id: id.slice(0, 60), ariaLabel: al, role, text: txt, cls: cls.slice(0, 60)});
                    }
                }
            }
            return found.slice(0, 30);
        }"""
        )
        if extras:
            print(f"  Date/search elements ({len(extras)}):", file=sys.stderr)
            for el in extras[:20]:
                print(
                    f'    <{el["tag"].lower()} id="{el["id"]}" '
                    f'aria-label="{el["ariaLabel"]}" role="{el["role"]}" '
                    f'class="{el["cls"][:40]}" text="{el["text"][:30]}">',
                    file=sys.stderr,
                )
    except Exception as e:
        print(f"  Date element dump failed: {e}", file=sys.stderr)

    # 1. Trip type
    if not return_date:
        try:
            page.select_option('select[aria-label="Trip type dropdown"]', "One Way")
            page.wait_for_timeout(500)
        except Exception:
            # Try clicking a radio/tab for One Way
            ow = page.query_selector(
                'label:has-text("One Way"), button:has-text("One Way")'
            )
            if ow:
                ow.click()
                page.wait_for_timeout(500)

    # 2. Cabin class (Amex uses uppercase values: ECONOMY, BUSINESS, etc.)
    cabin_map = {
        "Economy": "ECONOMY",
        "Premium Economy": "PREMIUM_ECONOMY",
        "Business": "BUSINESS",
        "First": "FIRST",
    }
    cabin_val = cabin_map.get(cabin, cabin.upper())
    sel = page.query_selector(
        '#flight-class-dropdown, select[aria-label="Flight class dropdown"]'
    )
    if sel:
        try:
            sel.select_option(cabin_val, timeout=3000)
            print(f"  Cabin set to {cabin_val}", file=sys.stderr)
            page.wait_for_timeout(500)
        except Exception as e:
            print(f"  WARNING: Cabin select failed ({e})", file=sys.stderr)

    # 3. Origin airport (id based, aria-label is empty on Amex)
    print(f"  Filling origin: {origin}", file=sys.stderr)
    _fill_airport_field(
        page,
        'input[id*="locationsInput_departure"]',
        origin,
    )

    # 4. Destination airport
    print(f"  Filling destination: {dest}", file=sys.stderr)
    _fill_airport_field(
        page,
        'input[id*="locationsInput_destination"]',
        dest,
    )

    # 5. Departure date
    print(f"  Picking departure date: {depart}", file=sys.stderr)
    _fill_date_field(page, 'button[aria-label="Depart"]', depart)

    # 6. Return date (if round-trip)
    if return_date:
        print(f"  Picking return date: {return_date}", file=sys.stderr)
        # The return date trigger might already be visible after picking depart
        # Or the calendar might stay open for range selection
        page.wait_for_timeout(500)
        _fill_date_field(page, 'button[aria-label="Return"]', return_date)

    # 7. Close any open calendar overlay (Escape or click outside)
    page.keyboard.press("Escape")
    page.wait_for_timeout(1000)

    # 8. Click Search (use JS click to bypass any remaining overlays)
    search_clicked = page.evaluate("""() => {
        const btn = document.querySelector('button[aria-label="Search flights"]')
            || document.querySelector('#axp-travel-search-flights_searchButton');
        if (btn) { btn.click(); return true; }
        return false;
    }""")
    if search_clicked:
        print("  Clicked Search flights", file=sys.stderr)
    else:
        print("  WARNING: Search button not found, pressing Enter", file=sys.stderr)
        page.keyboard.press("Enter")

    # 8. Wait for results page (redirect through login gate)
    print("Waiting for results page...", file=sys.stderr)
    login_handled = False
    for i in range(60):
        page.wait_for_timeout(3000)
        url = page.url.lower()
        if "amextravel.com/flight-search" in url:
            print(f"  On results page ({(i + 1) * 3}s)", file=sys.stderr)
            break
        if ("/login" in url or "/logon" in url) and not login_handled:
            if i == 0:
                print(
                    "  Login interstitial detected. Attempting re-auth...",
                    file=sys.stderr,
                )
            # The travel portal has its own login gate. Try to fill credentials.
            _handle_travel_login_gate(page, username=username, password=password)
            login_handled = True
            page.wait_for_timeout(5000)
            continue
        if i % 5 == 4:
            print(f"  Waiting... URL: {url[:80]} ({(i + 1) * 3}s)", file=sys.stderr)

    # 9. Wait for React hydration
    page.wait_for_timeout(10000)

    # 10. Extract appData
    return extract_app_data(page)


def search_hotels_dom(
    page, dest, checkin, checkout, guests=2, username=None, password=None
):
    """Fill the Amex Travel hotel search form and submit it.

    Returns appData from the results page, or None on failure.
    """
    # Navigate to hotels page
    page.goto(AMEX_HOTELS_URL, timeout=30000)
    page.wait_for_timeout(8000)

    # Destination (hotel page uses same combobox pattern as flights)
    print(f"  Filling destination: {dest}", file=sys.stderr)
    _fill_airport_field(
        page,
        'input[id*="locationsInput"]',
        dest,
    )

    # Check-in date
    print(f"  Picking check-in date: {checkin}", file=sys.stderr)
    _fill_date_field(page, 'button[aria-label="Check-in"]', checkin)

    # Close calendar before picking check-out
    page.keyboard.press("Escape")
    page.wait_for_timeout(1000)

    # Check-out date
    print(f"  Picking check-out date: {checkout}", file=sys.stderr)
    _fill_date_field(page, 'button[aria-label="Check-out"]', checkout)

    # Close calendar before clicking search
    page.keyboard.press("Escape")
    page.wait_for_timeout(1000)

    # Guests (if not default 2)
    if guests != 2:
        for guest_sel in [
            'select[aria-label*="guest" i]',
            'button[aria-label*="guest" i]',
            'select[aria-label*="traveler" i]',
        ]:
            el = page.query_selector(guest_sel)
            if el:
                try:
                    el.select_option(str(guests))
                except Exception:
                    el.click()
                break

    # Search (JS click to bypass any remaining overlays)
    # Hotel search button: id="axp-travel-search-hotels_searchButton"
    # aria-label="Login and search hotels" (NOT "Search hotels")
    search_clicked = page.evaluate("""() => {
        const btn = document.querySelector('#axp-travel-search-hotels_searchButton')
            || document.querySelector('button[aria-label*="search hotels" i]')
            || document.querySelector('[id*="searchButton"]');
        if (btn) { btn.click(); return true; }
        return false;
    }""")
    if search_clicked:
        print("  Clicked Search hotels", file=sys.stderr)
    else:
        print("  WARNING: Search button not found, pressing Enter", file=sys.stderr)
        page.keyboard.press("Enter")

    # Wait for results page (hotel search goes through login gate then to amextravel.com)
    print("Waiting for hotel results...", file=sys.stderr)
    login_handled = False
    for i in range(60):
        page.wait_for_timeout(3000)
        url = page.url.lower()
        # Check for hotel results (two possible portals)
        if (
            "amextravel.com/hotel" in url
            or "accommodations/search-results" in url
            or "travel.americanexpress.com" in url
            and "book" in url
        ):
            print(f"  On hotel results page ({(i + 1) * 3}s)", file=sys.stderr)
            break
        # Also check if appData is already available on current page
        if i > 5:
            has_data = page.evaluate("""() => {
                return !!(window.appData && (window.appData.hotelSearchResults || window.appData.hotelSearch));
            }""")
            if has_data:
                print(
                    f"  Hotel appData found on current page ({(i + 1) * 3}s)",
                    file=sys.stderr,
                )
                break
        # Handle login gate
        if ("/login" in url or "/logon" in url) and not login_handled:
            print(
                "  Login interstitial detected. Attempting re-auth...",
                file=sys.stderr,
            )
            _handle_travel_login_gate(page, username=username, password=password)
            login_handled = True
            page.wait_for_timeout(5000)
            continue
        if i % 5 == 4:
            print(f"  Waiting... URL: {url[:80]} ({(i + 1) * 3}s)", file=sys.stderr)

    # Wait for rendering
    page.wait_for_timeout(10000)

    # Extract appData
    return extract_app_data_hotels(page)


def extract_app_data_hotels(page, timeout=90):
    """Extract hotel data from results page.

    Hotels may use travel.americanexpress.com (new portal) or amextravel.com (old portal).
    The new portal may NOT have window.appData. Try multiple extraction methods.
    """
    print("Extracting hotel data...", file=sys.stderr)
    current_url = page.url.lower()
    print(f"  Results URL: {current_url[:120]}", file=sys.stderr)

    # Method 1: Try window.appData (works for amextravel.com portal)
    for attempt in range(min(timeout // 5, 6)):
        try:
            result = page.evaluate(
                """() => {
                if (window.appData && window.appData.hotelSearchResults) {
                    return JSON.stringify(window.appData);
                }
                if (window.appData && window.appData.hotelSearch) {
                    return JSON.stringify(window.appData);
                }
                return null;
            }"""
            )
            if result:
                data = json.loads(result)
                print("  Extracted hotel data from window.appData", file=sys.stderr)
                return data
        except Exception:
            pass
        time.sleep(5)

    # Method 2: Scan all window variables for hotel data
    print("  No window.appData. Scanning page state...", file=sys.stderr)
    try:
        state_info = page.evaluate("""() => {
            const found = {};
            // Check common React/Redux state holders
            const checks = ['__NEXT_DATA__', '__NUXT__', 'appData', '__APP_DATA__',
                           '__INITIAL_STATE__', '__PRELOADED_STATE__', '__data'];
            for (const key of checks) {
                if (window[key]) {
                    const s = JSON.stringify(window[key]);
                    found[key] = s.length;
                }
            }
            // Check for any large window properties (likely app state)
            for (const key of Object.keys(window)) {
                try {
                    const val = window[key];
                    if (val && typeof val === 'object' && !Array.isArray(val)) {
                        const s = JSON.stringify(val);
                        if (s && s.length > 10000) {
                            found[key] = s.length;
                        }
                    }
                } catch(e) {}
            }
            return found;
        }""")
        if state_info:
            print(f"  Window state vars: {json.dumps(state_info)}", file=sys.stderr)

            # Try to extract the largest one that might contain hotel data
            for key, size in sorted(state_info.items(), key=lambda x: -x[1]):
                if size > 5000:
                    try:
                        data_str = page.evaluate(f"() => JSON.stringify(window.{key})")
                        data = json.loads(data_str)
                        # Check if it has anything hotel-related
                        data_text = data_str[:5000].lower()
                        if (
                            "hotel" in data_text
                            or "accommodation" in data_text
                            or "property" in data_text
                        ):
                            print(
                                f"  Found hotel data in window.{key} ({size} chars)",
                                file=sys.stderr,
                            )
                            return {"_source": key, "_raw": data}
                    except Exception:
                        continue
    except Exception as e:
        print(f"  State scan error: {e}", file=sys.stderr)

    # Method 3: Extract hotel-offer-card elements directly from DOM
    print("  Trying hotel-offer-card DOM extraction...", file=sys.stderr)
    try:
        offer_cards = page.evaluate("""() => {
            const cards = document.querySelectorAll('[data-testid="hotel-offer-card"]');
            return Array.from(cards).map(el => {
                // Extract structured data via data-testid attributes first
                const priceEl = el.querySelector('[data-testid="offer-prices-current-price"]');
                const totalEl = el.querySelector('[data-testid="offer-prices-total-price"]');
                const pointsEl = el.querySelector('[data-testid="offer-prices-total-points"]');
                const titleEl = el.querySelector('[data-testid="hotel-card-content-title"]');
                const starEl = el.querySelector('[data-testid="hotel-card-star-rating"]');
                const taBtn = el.querySelector('[data-testid="tripadvisor-reviews-button"]');
                const earnEl = el.querySelector('[data-testid="earn-points-info-badge"]');
                const selectBtn = el.querySelector('[data-testid^="hotel-offer-button-"]');

                return {
                    testid: 'hotel-offer-card',
                    text: el.innerText?.substring(0, 4000) || '',
                    // Structured fields (more reliable than text parsing)
                    s_name: titleEl?.textContent?.trim() || '',
                    s_price_per_night: priceEl?.textContent?.trim() || '',
                    s_total_price: totalEl?.textContent?.trim() || '',
                    s_points: pointsEl?.textContent?.trim() || '',
                    s_star_info: starEl?.textContent?.trim() || '',
                    s_ta_reviews: taBtn?.textContent?.trim() || '',
                    s_earn: earnEl?.textContent?.trim() || '',
                    s_select_label: selectBtn?.getAttribute('aria-label') || '',
                };
            });
        }""")
        if offer_cards and len(offer_cards) > 0:
            print(
                f"  Found {len(offer_cards)} hotel-offer-card elements", file=sys.stderr
            )
            return {"_source": "dom_offer_cards", "_offer_cards": offer_cards}
    except Exception as e:
        print(f"  DOM offer card extraction error: {e}", file=sys.stderr)

    # Method 4: Raw text fallback
    print("  Trying raw text fallback...", file=sys.stderr)
    try:
        hotels_text = page.inner_text("body")
        hotel_count = hotels_text.lower().count("per night")
        print(f"  Page has ~{hotel_count} 'per night' mentions", file=sys.stderr)
        if hotel_count > 0:
            return {"_source": "dom", "_raw_text": hotels_text}
    except Exception as e:
        print(f"  DOM scrape error: {e}", file=sys.stderr)

    # Method 5: Try HTML parsing for embedded data
    return _extract_app_data_from_html(page)


def parse_hotels(app_data):
    """Parse hotel results from appData or DOM extraction.

    Handles multiple data sources:
    - DOM offer cards (travel.americanexpress.com, Next.js)
    - window.appData (amextravel.com, iSeatz)
    - Raw text fallback
    """
    hotels = []
    source = app_data.get("_source", "")

    # Source: DOM hotel-offer-card elements
    if source == "dom_offer_cards":
        offer_cards = app_data.get("_offer_cards", [])
        print(
            f"  Parsing {len(offer_cards)} hotel-offer-card elements...",
            file=sys.stderr,
        )
        for card in offer_cards:
            hotel = _parse_offer_card_text(card.get("text", ""))
            if hotel and hotel.get("name"):
                hotels.append(hotel)
        print(f"  Parsed {len(hotels)} hotels", file=sys.stderr)
        return hotels

    # Source: raw text fallback
    if source == "dom":
        raw_text = app_data.get("_raw_text", "")
        if raw_text:
            return _parse_hotels_from_text(raw_text)

    # Source: window.appData (iSeatz portal)
    for key in ["hotelSearchResults", "hotelSearch", "hotels"]:
        data = app_data.get(key, {})
        if not data:
            continue
        for list_key in ["results", "hotels", "properties", "items"]:
            items = data.get(list_key, [])
            if isinstance(items, list) and items:
                for item in items:
                    hotel = _extract_hotel_fields(item)
                    if hotel.get("name"):
                        hotels.append(hotel)
                if hotels:
                    return hotels
        if isinstance(data, list):
            for item in data:
                hotel = _extract_hotel_fields(item)
                if hotel.get("name"):
                    hotels.append(hotel)
            if hotels:
                return hotels

    return hotels


def _extract_hotel_fields(item):
    """Extract hotel fields from a result item, handling various schemas."""
    hotel = {}

    # Name
    for k in ["name", "hotel_name", "hotelName", "property_name", "n"]:
        v = item.get(k)
        if v:
            hotel["name"] = v
            break

    # Location
    for k in ["address", "location", "addr"]:
        v = item.get(k)
        if v:
            hotel["address"] = v if isinstance(v, str) else str(v)
            break

    # Rating
    for k in ["rating", "star_rating", "starRating", "stars"]:
        v = item.get(k)
        if v is not None:
            hotel["rating"] = v
            break

    # Price
    for k in ["price", "rate", "total_price", "nightly_rate"]:
        v = item.get(k)
        if v is not None:
            if isinstance(v, dict):
                hotel["price_cents"] = v.get("cents", v.get("amount", 0))
                hotel["price_usd"] = (
                    hotel["price_cents"] / 100
                    if hotel["price_cents"] > 100
                    else hotel["price_cents"]
                )
            else:
                hotel["price_usd"] = float(v) if v else 0
            break

    # Points
    for k in ["points", "total_price_in_points", "points_price"]:
        v = item.get(k)
        if v is not None:
            hotel["points"] = int(v) if v else 0
            break

    # FHR / Premium
    for k in ["is_fhr", "isFhr", "fhr", "fine_hotel", "premium", "has_fhr_benefits"]:
        v = item.get(k)
        if v:
            hotel["is_fhr"] = True
            break

    # THC
    for k in ["is_thc", "theHotelCollection", "hotel_collection"]:
        v = item.get(k)
        if v:
            hotel["is_thc"] = True
            break

    # Benefits
    for k in ["benefits", "amenities", "perks", "fhr_benefits"]:
        v = item.get(k)
        if v:
            hotel["benefits"] = v
            break

    # Image
    for k in ["image", "thumbnail", "photo", "img"]:
        v = item.get(k)
        if v:
            hotel["image"] = v if isinstance(v, str) else v.get("url", "")
            break

    # Refundable
    for k in ["is_refundable", "refundable", "cancellation_policy"]:
        v = item.get(k)
        if v is not None:
            hotel["refundable"] = v
            break

    # Pass through any unrecognized but interesting fields
    for k in ["id", "hotel_id", "provider", "source"]:
        v = item.get(k)
        if v:
            hotel[k] = v

    return hotel


def print_hotel_table(hotels, mr_balance=None):
    """Print hotels as markdown table."""
    if mr_balance:
        print(f"MR Points Balance: {mr_balance:,}\n")

    fhr_hotels = [h for h in hotels if h.get("is_fhr")]
    thc_hotels = [h for h in hotels if h.get("is_thc") and not h.get("is_fhr")]
    other_hotels = [h for h in hotels if not h.get("is_fhr") and not h.get("is_thc")]

    for label, group in [
        ("FINE HOTELS + RESORTS (FHR)", fhr_hotels),
        ("THE HOTEL COLLECTION (THC)", thc_hotels),
        ("STANDARD", other_hotels),
    ]:
        if not group:
            continue

        print(f"\n### {label}\n")
        print("| # | Hotel | Rating | Cash/Night | Points | Refundable | Benefits |")
        print("|---|-------|--------|------------|--------|------------|----------|")

        for i, h in enumerate(group[:30], 1):
            rating = h.get("rating", "")
            if rating:
                rating = f"{rating}*"
            price = f"${h['price_usd']:,.0f}" if h.get("price_usd") else "?"
            points = f"{h['points']:,}" if h.get("points") else ""
            refund = (
                "Yes"
                if h.get("refundable")
                else "No"
                if h.get("refundable") is False
                else "?"
            )
            benefits = ""
            if h.get("benefits"):
                if isinstance(h["benefits"], list):
                    benefits = "; ".join(str(b)[:40] for b in h["benefits"][:3])
                else:
                    benefits = str(h["benefits"])[:80]

            print(
                f"| {i} | {h.get('name', '?')} | {rating} | {price} "
                f"| {points} | {refund} | {benefits} |"
            )

    print(
        f"\n{len(hotels)} hotels total ({len(fhr_hotels)} FHR, {len(thc_hotels)} THC)"
    )


def extract_app_data(page, timeout=90):
    """Extract window.appData from the results page.

    The Amex Travel results page (powered by iSeatz/Expedia) renders ALL search
    results into a single window.appData Redux store in a <script> tag.
    This is 400-700KB of JSON with the complete flight/hotel data.
    """
    print("Extracting window.appData...", file=sys.stderr)

    for attempt in range(timeout // 5):
        try:
            result = page.evaluate(
                """() => {
                if (window.appData && window.appData.flightSearch &&
                    window.appData.flightSearch.itineraries &&
                    window.appData.flightSearch.itineraries.length > 0) {
                    return JSON.stringify(window.appData);
                }
                if (window.appData && window.appData.hotelSearchResults &&
                    Object.keys(window.appData.hotelSearchResults).length > 0) {
                    return JSON.stringify(window.appData);
                }
                return null;
            }"""
            )
            if result:
                data = json.loads(result)
                return data
        except Exception as e:
            if "circular" in str(e).lower():
                # Fall back to HTML parsing
                return _extract_app_data_from_html(page)
            if attempt % 3 == 2:
                print(
                    f"  Waiting for appData... ({(attempt + 1) * 5}s)", file=sys.stderr
                )

        time.sleep(5)

    # Final fallback: parse from HTML
    return _extract_app_data_from_html(page)


def _extract_app_data_from_html(page):
    """Extract window.appData by parsing the HTML source."""
    print("Extracting appData from HTML source...", file=sys.stderr)
    try:
        html = page.content()
        scripts = re.findall(r"<script[^>]*>(.*?)</script>", html, re.DOTALL)
        for s in scripts:
            s = s.strip()
            if s.startswith("window.appData"):
                json_str = s[len("window.appData") :].strip().lstrip("=").strip()
                # Find matching closing brace
                depth = 0
                end = 0
                for i, c in enumerate(json_str):
                    if c == "{":
                        depth += 1
                    elif c == "}":
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break
                if end > 0:
                    data = json.loads(json_str[:end])
                    fs = data.get("flightSearch", {})
                    itins = fs.get("itineraries", [])
                    print(
                        f"Extracted appData from HTML ({len(json_str[:end])} chars, {len(itins)} flights)",
                        file=sys.stderr,
                    )
                    return data
    except Exception as e:
        print(f"HTML parsing error: {e}", file=sys.stderr)
    return None


def parse_flights(app_data):
    """Parse flight results from appData into clean structure."""
    fs = app_data.get("flightSearch", {})
    itins = fs.get("itineraries", [])
    airports = fs.get("airports", {})
    airlines = fs.get("airlines", {})

    flights = []
    for it in itins:
        seg = it.get("segment", {})
        legs = seg.get("legs", [])

        # Build segments list
        segments = []
        for leg in legs:
            ft = leg.get("flight_time_range", {})
            segments.append(
                {
                    "flight_number": f"{leg.get('marketing_airline_code', '')}{leg.get('flight_number', '')}",
                    "origin": leg.get("departure_airport_id", ""),
                    "destination": leg.get("arrival_airport_id", ""),
                    "depart": ft.get("from", ""),
                    "arrive": ft.get("to", ""),
                    "duration": leg.get("flight_duration", ""),
                    "airline_code": leg.get("marketing_airline_code", ""),
                    "operating_code": leg.get("operating_airline_code", ""),
                    "equipment": leg.get("equipment", {}).get("description", ""),
                    "cabin": leg.get("cabin_type", ""),
                    "amenities": leg.get("amenities", []),
                }
            )

        # Parse pricing (PEP = IAP discount, PUB = public)
        pricing = {}
        for pi in it.get("pricing_information", []):
            fare_type = pi.get("fare_type", "PUB")
            tp = pi.get("total_price", {})
            pricing[fare_type] = {
                "cash_cents": tp.get("cents", 0),
                "cash_usd": tp.get("cents", 0) / 100,
                "currency": tp.get("currency", "USD"),
                "points": pi.get("total_price_in_points", 0),
                "base_cents": pi.get("base_price", {}).get("cents", 0),
                "refundable": pi.get("is_refundable", False),
                "cancellation": pi.get("cancellation_policy", ""),
                "basic_economy": pi.get("basic_economy", False),
            }

        # Determine best price
        iap_price = pricing.get("PEP", {})
        pub_price = pricing.get("PUB", {})
        best = iap_price if iap_price else pub_price

        flight = {
            "airline": seg.get("marketed_by", ""),
            "duration": seg.get("duration", ""),
            "duration_seconds": seg.get("duration_in_seconds", 0),
            "stops": len(legs) - 1,
            "stop_cities": seg.get("airport_ids", [])[1:-1]
            if len(seg.get("airport_ids", [])) > 2
            else [],
            "segments": segments,
            "seats_left": seg.get("seats_left", 0),
            "has_iap": it.get("has_iap_fares", False),
            "has_platinum": it.get("has_platinum_member_fares", False),
            "mixed_cabin": seg.get("mixed_cabin_class", False),
            "cash_usd": best.get("cash_usd", 0),
            "points": best.get("points", 0),
            "pricing": pricing,
        }
        flights.append(flight)

    return flights


def format_duration(iso_dur):
    """Convert PT20H10M to 20h 10m."""
    m = re.match(r"PT(?:(\d+)H)?(?:(\d+)M)?", iso_dur or "")
    if m:
        h = m.group(1) or "0"
        mins = m.group(2) or "0"
        return f"{h}h {mins}m"
    return iso_dur or ""


def format_time(dt_str):
    """Convert 2026-08-11T12:55:00 to 12:55pm."""
    m = re.match(r"\d{4}-\d{2}-\d{2}T(\d{2}):(\d{2})", dt_str or "")
    if m:
        h, mins = int(m.group(1)), m.group(2)
        ampm = "am" if h < 12 else "pm"
        h12 = h % 12 or 12
        return f"{h12}:{mins}{ampm}"
    return dt_str or ""


def print_flight_table(flights, mr_balance=None):
    """Print flights as markdown table."""
    if mr_balance:
        print(f"MR Points Balance: {mr_balance:,}\n")

    iap_flights = [f for f in flights if f["has_iap"]]
    regular_flights = [f for f in flights if not f["has_iap"]]

    for label, group in [
        ("INTERNATIONAL AIRLINE PROGRAM (Platinum Benefit)", iap_flights),
        ("STANDARD FARES", regular_flights),
    ]:
        if not group:
            continue

        print(f"\n### {label}\n")
        print(
            "| # | Airline | Stops | Duration | Depart | Arrive | Cash | Points | Seats | IAP Savings |"
        )
        print(
            "|---|---------|-------|----------|--------|--------|------|--------|-------|-------------|"
        )

        for i, f in enumerate(group[:50], 1):
            seg0 = f["segments"][0] if f["segments"] else {}
            seg_last = f["segments"][-1] if f["segments"] else {}

            stops_str = "Nonstop" if f["stops"] == 0 else f"{f['stops']} stop"
            if f["stop_cities"]:
                stops_str += f" ({','.join(f['stop_cities'])})"

            # IAP savings
            savings = ""
            if f["has_iap"] and "PEP" in f["pricing"] and "PUB" in f["pricing"]:
                pub = f["pricing"]["PUB"]["cash_usd"]
                iap = f["pricing"]["PEP"]["cash_usd"]
                if pub > 0:
                    savings = f"-${pub - iap:,.0f} ({(pub - iap) / pub * 100:.0f}%)"

            print(
                f"| {i} | {f['airline']} | {stops_str} | {format_duration(f['duration'])} "
                f"| {format_time(seg0.get('depart', ''))} "
                f"| {format_time(seg_last.get('arrive', ''))} "
                f"| ${f['cash_usd']:,.0f} | {f['points']:,} | {f['seats_left'] or '?'} "
                f"| {savings} |"
            )

    total_iap = len(iap_flights)
    total = len(flights)
    print(f"\n{total} flights total, {total_iap} with IAP discount")


# ============================================================
# Main
# ============================================================


def _save_page_html(page, filepath):
    """Save full page HTML, text, and testid elements to a file for offline parsing."""
    print(f"Saving page HTML to {filepath}...", file=sys.stderr)
    save_data = {}
    try:
        save_data["url"] = page.url
        save_data["html"] = page.content()
        save_data["text"] = page.inner_text("body")
        # Extract all data-testid elements with their text content
        testids = page.evaluate("""() => {
            const els = document.querySelectorAll('[data-testid]');
            return Array.from(els).map(el => ({
                testid: el.getAttribute('data-testid'),
                tag: el.tagName.toLowerCase(),
                text: el.innerText?.substring(0, 2000) || '',
                childCount: el.children.length,
                classes: (typeof el.className === 'string' ? el.className : '').substring(0, 200)
            }));
        }""")
        save_data["testid_elements"] = testids
        # Extract hotel cards specifically
        hotel_cards = page.evaluate("""() => {
            const cards = document.querySelectorAll('[data-testid*="hotel-card"]');
            return Array.from(cards).map(el => ({
                testid: el.getAttribute('data-testid'),
                tag: el.tagName.toLowerCase(),
                outerHTML: el.outerHTML?.substring(0, 5000) || '',
                text: el.innerText?.substring(0, 2000) || ''
            }));
        }""")
        save_data["hotel_cards"] = hotel_cards
        # Also grab hotels-list container
        hotels_list = page.evaluate("""() => {
            const list = document.querySelector('[data-testid="hotels-list"]');
            if (!list) return null;
            return {
                childCount: list.children.length,
                innerHTML: list.innerHTML?.substring(0, 50000) || '',
                text: list.innerText?.substring(0, 20000) || ''
            };
        }""")
        save_data["hotels_list"] = hotels_list
    except Exception as e:
        print(f"  Save error: {e}", file=sys.stderr)

    with open(filepath, "w") as f:
        json.dump(save_data, f, indent=2, default=str)

    stats = {k: len(str(v)) for k, v in save_data.items()}
    print(f"  Saved: {json.dumps(stats)}", file=sys.stderr)
    print(
        f"  {len(save_data.get('testid_elements', []))} testid elements",
        file=sys.stderr,
    )
    print(
        f"  {len(save_data.get('hotel_cards', []))} hotel card elements",
        file=sys.stderr,
    )


def _parse_html_offline(filepath, is_hotel=False, json_output=False):
    """Parse a previously saved HTML file without needing a browser.

    This enables rapid iteration on parsers without 60-90s browser restarts.
    """
    print(f"Parsing saved HTML from {filepath}...", file=sys.stderr)
    with open(filepath) as f:
        data = json.load(f)

    print(f"  URL: {data.get('url', '?')}", file=sys.stderr)
    print(f"  {len(data.get('testid_elements', []))} testid elements", file=sys.stderr)
    print(f"  {len(data.get('hotel_cards', []))} hotel card elements", file=sys.stderr)

    if is_hotel:
        hotels = _parse_hotels_from_saved(data)
        if json_output:
            output = {
                "total_hotels": len(hotels),
                "fhr_count": sum(1 for h in hotels if h.get("is_fhr")),
                "thc_count": sum(1 for h in hotels if h.get("is_thc")),
                "hotels": hotels,
            }
            print(json.dumps(output, indent=2, default=str))
        else:
            if hotels:
                print_hotel_table(hotels)
            else:
                print("No hotels parsed. Dumping diagnostics...", file=sys.stderr)
                _dump_hotel_diagnostics(data)
    else:
        # For flights, try to find appData in the saved HTML
        html = data.get("html", "")
        app_data = _extract_app_data_from_html_string(html)
        if app_data:
            flights = parse_flights(app_data)
            if json_output:
                print(json.dumps({"flights": flights}, indent=2, default=str))
            else:
                print_flight_table(flights)
        else:
            print("No appData found in saved HTML.", file=sys.stderr)


def _parse_hotels_from_saved(data):
    """Parse hotel data from saved HTML dump.

    The hotel results page (travel.americanexpress.com) is a Next.js app
    without window.appData. Hotels are rendered in DOM with data-testid attributes.

    Primary data source: testid_elements array (structured by testid).
    hotel-offer-card contains ALL data per hotel in predictable text layout.
    """
    hotels = []

    # Method 1: Use testid_elements (most reliable)
    els = data.get("testid_elements", [])
    if els:
        offer_cards = [e for e in els if e.get("testid") == "hotel-offer-card"]
        if offer_cards:
            print(
                f"  Parsing {len(offer_cards)} hotel-offer-card elements...",
                file=sys.stderr,
            )
            for card in offer_cards:
                hotel = _parse_offer_card_text(card.get("text", ""))
                if hotel and hotel.get("name"):
                    hotels.append(hotel)
            if hotels:
                return hotels

    # Method 2: Fall back to hotel_cards
    hotel_cards = data.get("hotel_cards", [])
    if hotel_cards:
        offer_cards = [c for c in hotel_cards if c.get("testid") == "hotel-offer-card"]
        if offer_cards:
            print(
                f"  Parsing {len(offer_cards)} hotel-offer-card elements (from hotel_cards)...",
                file=sys.stderr,
            )
            for card in offer_cards:
                hotel = _parse_offer_card_text(card.get("text", ""))
                if hotel and hotel.get("name"):
                    hotels.append(hotel)
            if hotels:
                return hotels

    # Method 3: Full page text
    full_text = data.get("text", "")
    if full_text and "per night" in full_text.lower():
        print(f"  Falling back to full page text parsing...", file=sys.stderr)
        return _parse_hotels_from_text(full_text)

    return []


def _parse_offer_card_text(card_data):
    """Parse a hotel-offer-card into structured data.

    Accepts either a string (legacy text-only) or a dict with structured fields
    from data-testid DOM extraction plus fallback text.
    """
    hotel = {}

    # Handle both dict (new structured extraction) and string (legacy)
    if isinstance(card_data, dict):
        text = card_data.get("text", "")
        # Use structured fields when available (more reliable than text parsing)
        if card_data.get("s_name"):
            hotel["name"] = card_data["s_name"]
        if card_data.get("s_price_per_night"):
            try:
                hotel["price_per_night"] = float(
                    card_data["s_price_per_night"].replace("$", "").replace(",", "")
                )
            except (ValueError, TypeError):
                pass
        if card_data.get("s_total_price"):
            try:
                hotel["total_price"] = float(
                    card_data["s_total_price"].replace("$", "").replace(",", "")
                )
            except (ValueError, TypeError):
                pass
        if card_data.get("s_points"):
            try:
                pts_str = card_data["s_points"].replace(",", "").strip()
                hotel["points"] = int(pts_str)
            except (ValueError, TypeError):
                pass
        if card_data.get("s_earn") and "5x" in card_data["s_earn"].lower():
            hotel["earn_rate"] = "5x"
    else:
        text = card_data

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    if not lines and not hotel:
        return hotel

    text_lower = text.lower()

    # FHR / THC detection
    if "fine hotels and resorts" in text_lower:
        hotel["is_fhr"] = True
    if "hotel collection" in text_lower:
        hotel["is_thc"] = True

    # Find hotel name: first line that looks like a name (not a banner, not earn points)
    skip_patterns = [
        "fine hotels",
        "hotel collection",
        "earn",
        "points",
        "amenities",
        "all benefits",
        "view",
        "select hotel",
        "average room",
        "total price",
        "membership rewards",
        "per night",
        "taxes and fees",
        "price details",
        "lowest rate",
    ]
    for line in lines:
        ll = line.lower()
        if len(line) < 3:
            continue
        if line.startswith("$") or line.startswith("was"):
            continue
        if re.match(r"^\d", line) and ("star" not in ll):
            continue
        if any(p in ll for p in skip_patterns):
            continue
        if re.match(r"^(or|based on|trip advisor)", ll):
            continue
        # Star rating line (not the name)
        if re.match(r"^\d\.?\d?-star", ll):
            continue
        hotel["name"] = line
        break

    # Star rating and location: "X-star hotel|City|Distance"
    star_match = re.search(r"(\d\.?\d?)-star hotel\|([^|]+)\|([^\n]+)", text)
    if star_match:
        hotel["stars"] = float(star_match.group(1))
        hotel["city"] = star_match.group(2).strip()
        hotel["distance"] = star_match.group(3).strip()

    # TripAdvisor rating
    ta_match = re.search(r"Trip Advisor rating (\d\.?\d?) of 5", text)
    if ta_match:
        hotel["tripadvisor_rating"] = float(ta_match.group(1))

    ta_reviews = re.search(r"Based on (\d[\d,]*) reviews", text)
    if ta_reviews:
        hotel["tripadvisor_reviews"] = int(ta_reviews.group(1).replace(",", ""))

    # Per night price: first $XXX.XX pattern
    price_match = re.search(r"\$([\d,]+\.\d{2})\s*\n\s*average room per night", text)
    if not price_match:
        price_match = re.search(r"\$([\d,]+\.\d{2})\s*\n\s*Avg room", text)
    if price_match:
        hotel["price_per_night"] = float(price_match.group(1).replace(",", ""))

    # Total price
    total_match = re.search(r"\$([\d,]+\.\d{2})\s*\n\s*Total price", text)
    if total_match:
        hotel["total_price"] = float(total_match.group(1).replace(",", ""))

    # Points (number on its own line before "Membership Rewards")
    points_match = re.search(r"\n\s*([\d,]+)\s*\n\s*Membership Rewards", text)
    if points_match:
        hotel["points"] = int(points_match.group(1).replace(",", ""))

    # Old price (sale)
    old_match = re.search(r"was\s*\n\s*\$([\d,]+\.\d{2})", text)
    if old_match:
        hotel["old_price_per_night"] = float(old_match.group(1).replace(",", ""))

    # Benefits (for FHR/THC): look for USD$XXX or $XXX Credit lines
    if hotel.get("is_fhr") or hotel.get("is_thc"):
        benefits = []
        for line in lines:
            ll = line.lower().strip()
            # Benefit lines typically start with USD$, $XXX Credit, or describe a perk
            if re.match(r"^usd\$\d+", ll) or re.match(r"^\$\d+.*credit", ll):
                benefits.append(line.strip())
            elif any(
                kw in ll
                for kw in [
                    "complimentary",
                    "daily breakfast",
                    "room upgrade",
                    "late checkout",
                    "early check-in",
                    "welcome amenity",
                    "property credit",
                    "food and beverage",
                    "spa credit",
                ]
            ):
                benefits.append(line.strip())
        if benefits:
            hotel["benefits"] = benefits

    # Amenities (for standard hotels)
    if not hotel.get("is_fhr") and not hotel.get("is_thc"):
        amenities_match = re.search(
            r"Amenities\s*\n(.+?)(?:\n\s*\$|\n\s*was)", text, re.DOTALL
        )
        if amenities_match:
            amenities = [
                a.strip() for a in amenities_match.group(1).split("\n") if a.strip()
            ]
            if amenities:
                hotel["amenities"] = amenities

    # Earn rate
    if "5x points" in text_lower or "5 times points" in text_lower:
        hotel["earn_rate"] = "5x"

    # Calculate CPP if we have both cash and points
    if hotel.get("points") and hotel.get("total_price") and hotel["points"] > 0:
        hotel["cpp"] = round(hotel["total_price"] / hotel["points"] * 100, 2)

    return hotel

    # First substantial line is usually the hotel name
    for line in lines:
        if len(line) > 3 and not line.startswith("$") and not re.match(r"^\d", line):
            hotel["name"] = line
            break

    # Look for FHR/THC markers
    text_lower = text.lower()
    if "fine hotels" in text_lower or "fhr" in text_lower:
        hotel["is_fhr"] = True
    if "hotel collection" in text_lower or "thc" in text_lower:
        hotel["is_thc"] = True

    # Price: look for $X,XXX or $XXX pattern
    price_match = re.search(r"\$[\d,]+(?:\.\d{2})?", text)
    if price_match:
        price_str = price_match.group().replace("$", "").replace(",", "")
        try:
            hotel["price_usd"] = float(price_str)
        except ValueError:
            pass

    # Points: look for X,XXX pts or X,XXX points
    points_match = re.search(r"([\d,]+)\s*(?:pts|points)", text, re.IGNORECASE)
    if points_match:
        try:
            hotel["points"] = int(points_match.group(1).replace(",", ""))
        except ValueError:
            pass

    # Per night indicator
    if "per night" in text_lower:
        hotel["_has_pricing"] = True

    # Rating: X.X or X stars
    rating_match = re.search(r"(\d\.?\d?)\s*(?:star|out of)", text, re.IGNORECASE)
    if rating_match:
        try:
            hotel["rating"] = float(rating_match.group(1))
        except ValueError:
            pass

    # Refundable
    if "refundable" in text_lower:
        hotel["refundable"] = "non" not in text_lower.split("refundable")[0][-5:]

    # Benefits (look for common FHR/THC benefit keywords)
    benefits = []
    benefit_keywords = [
        "breakfast",
        "credit",
        "upgrade",
        "late checkout",
        "early check-in",
        "welcome amenity",
        "complimentary",
    ]
    for line in lines:
        line_lower = line.lower()
        if any(kw in line_lower for kw in benefit_keywords):
            benefits.append(line.strip())
    if benefits:
        hotel["benefits"] = benefits

    return hotel


def _parse_hotels_from_text(text):
    """Parse hotels from raw page text by splitting on hotel boundaries."""
    hotels = []
    # Split on "per night" as boundary (each hotel block ends with pricing)
    blocks = re.split(r"(?=\$[\d,]+(?:\.\d{2})?\s*(?:per night|/night))", text)

    for block in blocks:
        if not block.strip():
            continue
        hotel = _parse_hotel_card_text(block)
        if hotel.get("name") and (hotel.get("price_usd") or hotel.get("_has_pricing")):
            hotels.append(hotel)

    return hotels


def _extract_app_data_from_html_string(html):
    """Extract window.appData from raw HTML string."""
    marker = "window.appData = "
    idx = html.find(marker)
    if idx < 0:
        return None

    start = idx + len(marker)
    # Find matching closing brace
    depth = 0
    i = start
    while i < len(html):
        c = html[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(html[start : i + 1])
                except json.JSONDecodeError:
                    return None
        i += 1
    return None


def _dump_hotel_diagnostics(data):
    """Print diagnostic info about saved hotel data."""
    # Show testid patterns
    testids = data.get("testid_elements", [])
    testid_counts = {}
    for el in testids:
        tid = el.get("testid", "")
        # Get the prefix (before any number)
        prefix = re.sub(r"-?\d+$", "", tid)
        testid_counts[prefix] = testid_counts.get(prefix, 0) + 1

    print("\n  data-testid patterns:", file=sys.stderr)
    for prefix, count in sorted(testid_counts.items(), key=lambda x: -x[1])[:20]:
        print(f"    {prefix}: {count}", file=sys.stderr)

    # Show hotel card samples
    cards = data.get("hotel_cards", [])
    if cards:
        print(f"\n  First 3 hotel-card elements:", file=sys.stderr)
        for card in cards[:3]:
            print(f"    testid={card.get('testid')}", file=sys.stderr)
            print(f"    text={card.get('text', '')[:200]}", file=sys.stderr)
            print(f"    ---", file=sys.stderr)

    # Show hotels-list info
    hl = data.get("hotels_list")
    if hl:
        print(f"\n  hotels-list: {hl.get('childCount')} children", file=sys.stderr)
        print(f"    text preview: {hl.get('text', '')[:500]}", file=sys.stderr)
    else:
        print("\n  No hotels-list container found", file=sys.stderr)

    # Count "per night" in full text
    full_text = data.get("text", "")
    pn_count = full_text.lower().count("per night")
    print(f"\n  'per night' in page text: {pn_count} occurrences", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(description="Amex Travel portal search")
    parser.add_argument("--origin", help="Origin airport code (e.g., SFO)")
    parser.add_argument("--dest", help="Destination airport code or city name")
    parser.add_argument("--depart", help="Departure date (YYYY-MM-DD)")
    parser.add_argument("--return", dest="return_date", help="Return date (YYYY-MM-DD)")
    parser.add_argument(
        "--cabin",
        default="Economy",
        help="Cabin class: economy, premium economy, business, first",
    )
    parser.add_argument(
        "--passengers", type=int, default=1, help="Number of passengers"
    )
    parser.add_argument(
        "--hotel", action="store_true", help="Search hotels instead of flights"
    )
    parser.add_argument("--checkin", help="Hotel check-in date (YYYY-MM-DD)")
    parser.add_argument("--checkout", help="Hotel check-out date (YYYY-MM-DD)")
    parser.add_argument("--guests", type=int, default=2, help="Number of hotel guests")
    parser.add_argument(
        "--json", action="store_true", dest="json_output", help="JSON output"
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="Record network traffic for API discovery",
    )
    parser.add_argument(
        "--save-html",
        metavar="FILE",
        help="Save full page HTML + text to FILE after results load (for offline parsing)",
    )
    parser.add_argument(
        "--parse-html",
        metavar="FILE",
        help="Parse a previously saved HTML file locally (no browser needed)",
    )
    args = parser.parse_args()

    # Normalize cabin class (accept any case)
    cabin_map = {
        "economy": "Economy",
        "premium economy": "Premium Economy",
        "premium_economy": "Premium Economy",
        "premiumeconomy": "Premium Economy",
        "business": "Business",
        "first": "First",
    }
    if args.cabin:
        normalized = cabin_map.get(args.cabin.lower().strip())
        if not normalized:
            parser.error(
                f"Unknown cabin class: {args.cabin}. Use: economy, premium economy, business, first"
            )
        args.cabin = normalized

    # Offline HTML parsing mode (no browser needed)
    if args.parse_html:
        _parse_html_offline(args.parse_html, args.hotel, args.json_output)
        sys.exit(0)

    if not args.record:
        if not args.hotel:
            if not args.origin or not args.dest or not args.depart:
                parser.error("Flight search requires --origin, --dest, and --depart")
        else:
            if not args.dest or not args.checkin or not args.checkout:
                parser.error("Hotel search requires --dest, --checkin, and --checkout")

    username = os.environ.get("AMEX_USERNAME", "")
    password = os.environ.get("AMEX_PASSWORD", "")
    if not username or not password:
        print("ERROR: AMEX_USERNAME and AMEX_PASSWORD required", file=sys.stderr)
        sys.exit(1)

    cookie_path = get_cookie_path()
    in_docker = os.path.exists("/.dockerenv") or os.environ.get("DOCKER", "")

    if in_docker:
        import tempfile

        profile_dir = tempfile.mkdtemp(prefix="amex-")
    else:
        profile_dir = get_profile_dir()

    os.makedirs(profile_dir, exist_ok=True)

    from patchright.sync_api import sync_playwright

    with sync_playwright() as p:
        try:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                channel="chrome" if not in_docker else None,
                headless=False,
                viewport={"width": 1400, "height": 900},
                args=["--disable-blink-features=AutomationControlled"],
            )
        except Exception:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                headless=False,
                viewport={"width": 1400, "height": 900},
                args=["--disable-blink-features=AutomationControlled"],
            )

        page = ctx.pages[0] if ctx.pages else ctx.new_page()

        if not login(page, ctx, username, password, cookie_path):
            print("ERROR: Login failed", file=sys.stderr)
            ctx.close()
            sys.exit(1)

        # Record mode
        if args.record:
            print(
                "Recording network traffic. Do your search in the browser window.",
                file=sys.stderr,
            )
            captured = {"requests": [], "responses": []}

            capture_domains = [
                "amextravel.com",
                "expedia.com",
                "iseatz.com",
                "prebooking.americanexpress.com",
                "tlsonline.americanexpress.com",
                "apigw.americanexpress.com",
                "tulipssmartfill.americanexpress.com",
            ]
            skip_patterns = [
                ".css",
                ".png",
                ".jpg",
                ".svg",
                ".woff",
                ".ico",
                ".gif",
                "dynatrace",
                "datadoghq",
                "brilliantcollector",
                "facebook.com",
                "flashtalking",
                "doubleclick",
                "googletag",
                "demdex",
                "omns.americanexpress",
                "ucmapi.americanexpress",
                "session-replay",
                "omtrdc",
            ]

            def on_req(req):
                url = req.url.lower()
                if any(s in url for s in skip_patterns):
                    return
                if any(d in url for d in capture_domains):
                    try:
                        pd = req.post_data
                    except Exception:
                        pd = None
                    captured["requests"].append(
                        {
                            "url": req.url,
                            "method": req.method,
                            "post_data": pd,
                            "resource_type": req.resource_type,
                        }
                    )
                    print(f">>> {req.method} {req.url[:140]}", file=sys.stderr)

            def on_resp(resp):
                url = resp.url.lower()
                if any(s in url for s in skip_patterns):
                    return
                if any(d in url for d in capture_domains):
                    try:
                        body = resp.text()
                    except Exception:
                        body = ""
                    captured["responses"].append(
                        {
                            "url": resp.url,
                            "status": resp.status,
                            "body": body if len(body) < 500000 else body[:50000],
                        }
                    )
                    print(
                        f"<<< {resp.status} {resp.url[:140]} ({len(body)}b)",
                        file=sys.stderr,
                    )

            page.on("request", on_req)
            page.on("response", on_resp)

            page.goto(AMEX_FLIGHTS_URL, timeout=30000)
            page.wait_for_timeout(5000)

            print(
                "\nREADY. Do your search. Create /tmp/amex-record-done.txt when done.",
                file=sys.stderr,
            )
            for _ in range(120):
                if os.path.exists("/tmp/amex-record-done.txt"):
                    os.remove("/tmp/amex-record-done.txt")
                    break
                page.wait_for_timeout(5000)
                with open("/tmp/amex-network-capture.json", "w") as f:
                    json.dump(captured, f, indent=2, default=str)
                print(
                    f"  [{len(captured['requests'])}req/{len(captured['responses'])}res]",
                    file=sys.stderr,
                )

            save_cookies(ctx, cookie_path)
            ctx.close()

            with open("/tmp/amex-network-capture.json", "w") as f:
                json.dump(captured, f, indent=2, default=str)
            print(
                f"Saved {len(captured['requests'])} req, {len(captured['responses'])} resp",
                file=sys.stderr,
            )
            sys.exit(0)

        # Navigate to travel page
        if "/travel" not in page.url.lower():
            page.goto(AMEX_FLIGHTS_URL, timeout=30000)
            page.wait_for_timeout(5000)

        # Extract MR balance from page text
        mr_balance = None
        try:
            text = page.inner_text("body")[:5000]
            matches = re.findall(r"([\d,]+)\s*pts", text)
            if matches:
                mr_balance = max(int(m.replace(",", "")) for m in matches)
                print(f"MR Points Balance: {mr_balance:,}", file=sys.stderr)
        except Exception:
            pass

        if args.hotel:
            # Hotel search via DOM form filling
            print(
                f"Searching hotels: {args.dest}, {args.checkin} to {args.checkout}...",
                file=sys.stderr,
            )

            app_data = search_hotels_dom(
                page,
                args.dest,
                args.checkin,
                args.checkout,
                guests=args.guests,
                username=username,
                password=password,
            )

            # Save HTML for offline iteration if requested
            if args.save_html:
                _save_page_html(page, args.save_html)

            if not app_data:
                print("ERROR: Could not extract hotel appData", file=sys.stderr)
                # Dump raw page text for debugging
                try:
                    raw = page.inner_text("body")[:5000]
                    print(f"Page text preview: {raw[:500]}", file=sys.stderr)
                except Exception:
                    pass
                save_cookies(ctx, cookie_path)
                ctx.close()
                sys.exit(1)

            hotels = parse_hotels(app_data)

            if args.json_output:
                output = {
                    "mr_balance": mr_balance,
                    "total_hotels": len(hotels),
                    "fhr_count": sum(1 for h in hotels if h.get("is_fhr")),
                    "thc_count": sum(1 for h in hotels if h.get("is_thc")),
                    "hotels": hotels,
                    # Include raw keys for debugging if no hotels parsed
                    "raw_keys": list(app_data.keys()) if not hotels else [],
                }
                print(json.dumps(output, indent=2, default=str))
            else:
                if hotels:
                    print_hotel_table(hotels, mr_balance=mr_balance)
                else:
                    print("No hotels parsed from appData.", file=sys.stderr)
                    print(
                        f"appData top-level keys: {list(app_data.keys())}",
                        file=sys.stderr,
                    )
                    # Print any hotel-related keys for debugging
                    for k in app_data:
                        if "hotel" in k.lower():
                            v = app_data[k]
                            print(
                                f"  {k}: {type(v).__name__} ({len(str(v))} chars)",
                                file=sys.stderr,
                            )

            save_cookies(ctx, cookie_path)
            ctx.close()
            sys.exit(0)

        # Flight search via DOM form filling
        print(
            f"Searching flights: {args.origin} -> {args.dest}, {args.depart}"
            + (f" to {args.return_date}" if args.return_date else "")
            + f", {args.cabin}...",
            file=sys.stderr,
        )

        app_data = search_flights_dom(
            page,
            args.origin,
            args.dest,
            args.depart,
            return_date=args.return_date,
            cabin=args.cabin,
            username=username,
            password=password,
        )

        # Save HTML for offline iteration if requested
        if args.save_html:
            _save_page_html(page, args.save_html)

        if not app_data:
            print("ERROR: Could not extract appData", file=sys.stderr)
            save_cookies(ctx, cookie_path)
            ctx.close()
            sys.exit(1)

        flights = parse_flights(app_data)

        if args.json_output:
            output = {
                "mr_balance": mr_balance,
                "total_flights": len(flights),
                "iap_flights": sum(1 for f in flights if f["has_iap"]),
                "flights": flights,
            }
            print(json.dumps(output, indent=2, default=str))
        else:
            print_flight_table(flights, mr_balance=mr_balance)

        save_cookies(ctx, cookie_path)
        ctx.close()


if __name__ == "__main__":
    main()

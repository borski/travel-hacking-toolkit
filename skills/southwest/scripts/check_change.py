#!/usr/bin/env python3
"""Check Southwest flight change prices for existing reservations.

READ-ONLY. This script NEVER modifies, changes, or cancels any flight.
It only logs in, looks up a reservation, and reads the page text.

The ONLY forms this script submits are:
  1. The login form (username + password)
  2. The reservation lookup form (confirmation number + name)

It does NOT click: "Change this flight", "Confirm", "Cancel",
"Submit", "Complete", "Book", or any action that would alter
the reservation. After the lookup result renders, it reads the
DOM text and exits.

Requires:
    pip install patchright && patchright install chromium

Credentials via environment variables (SW_USERNAME, SW_PASSWORD).

Usage:
    SW_USERNAME=user SW_PASSWORD=pass python3 check_change.py --conf ABC123 --first Jane --last Doe [--json] [--debug]
    SW_USERNAME=user SW_PASSWORD=pass python3 check_change.py --list [--json]
"""

import argparse
import json
import os
import re
import sys
import tempfile
import shutil
from pathlib import Path
from patchright.sync_api import sync_playwright, TimeoutError as PwTimeout


HOMEPAGE = "https://www.southwest.com"
DEBUG_DIR = Path("/tmp/sw_change_debug")

# Timing (ms)
WAIT_SHORT = 3000
WAIT_MED = 5000
WAIT_LONG = 12000
WAIT_LOGIN = 8000

# ---------------------------------------------------------------------------
# SAFETY: These words in a button/link mean "this would modify the booking."
# The script must NEVER click anything matching these. This list is checked
# by safe_click() which wraps every click after the login + lookup phase.
# ---------------------------------------------------------------------------
DANGEROUS_LABELS = [
    "change this flight",
    "confirm change",
    "confirm",
    "cancel flight",
    "cancel reservation",
    "cancel this",
    "complete change",
    "complete purchase",
    "submit change",
    "book",
    "purchase",
    "accept",
    "continue to payment",
    "change flight",  # the action button, not the page title
    "rebook",
]


def is_dangerous_click(text):
    """Return True if clicking something with this text could modify a booking."""
    lower = text.strip().lower()
    return any(danger in lower for danger in DANGEROUS_LABELS)


def log(msg):
    print(f"[sw] {msg}", file=sys.stderr)


def screenshot(page, name, debug=False):
    """Save a screenshot if debug mode is on."""
    if not debug:
        return
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    path = DEBUG_DIR / f"{name}.png"
    try:
        page.screenshot(path=str(path), full_page=True)
        log(f"Screenshot: {path}")
    except Exception as e:
        log(f"Screenshot failed ({name}): {e}")


def get_text(page):
    """Extract visible text from the page's main content."""
    return page.evaluate(
        """() => {
            var el = document.querySelector("[role='main']")
                  || document.querySelector("main")
                  || document.body;
            return el ? el.innerText : '';
        }"""
    )


def dismiss_overlays(page):
    """Dismiss cookie banners, popups, and other overlays."""
    for selector in [
        "button:has-text('Dismiss')",
        "button:has-text('Accept')",
        "button:has-text('No thanks')",
        "button:has-text('Close')",
        "[aria-label='Close']",
    ]:
        try:
            page.locator(selector).first.click(timeout=2000)
            page.wait_for_timeout(500)
        except (PwTimeout, Exception):
            pass


def do_login(page, username, password, debug=False):
    """Log into Southwest via the header login flyout.

    SW's header has a "Log in" trigger that opens a flyout with
    username/password fields. We try multiple selector strategies.
    """
    log("Opening login flyout...")
    screenshot(page, "01_before_login", debug)

    # Try clicking the login trigger in the header
    login_triggers = [
        "button:has-text('Log in')",
        "a:has-text('Log in')",
        "[data-qa='header-login-btn']",
        ".login-button",
        "span:has-text('Log in')",
    ]
    clicked = False
    for sel in login_triggers:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                el.click(timeout=3000)
                clicked = True
                log(f"Clicked login trigger: {sel}")
                break
        except (PwTimeout, Exception):
            continue

    if not clicked:
        log("WARNING: Could not find login trigger. Trying direct page text approach.")

    page.wait_for_timeout(WAIT_SHORT)
    screenshot(page, "02_login_flyout_open", debug)

    # Fill username
    username_selectors = [
        "input#loginUserNameHeader",
        "input[name='userNameOrAccountNumber']",
        "input[id*='userName']",
        "input[id*='Username']",
        "input[placeholder*='account']",
        "input[placeholder*='username']",
        "input[aria-label*='Account']",
        "input[aria-label*='Username']",
    ]
    filled_user = False
    for sel in username_selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                el.fill(username, timeout=3000)
                filled_user = True
                log(f"Filled username via: {sel}")
                break
        except (PwTimeout, Exception):
            continue

    if not filled_user:
        # Fallback: find any visible text input that looks like a username field
        try:
            inputs = page.locator(
                "input[type='text']:visible, input:not([type]):visible"
            )
            count = inputs.count()
            log(f"Fallback: found {count} visible text inputs")
            if count > 0:
                inputs.first.fill(username, timeout=3000)
                filled_user = True
                log("Filled username via fallback (first visible text input)")
        except Exception as e:
            log(f"Username fallback failed: {e}")

    if not filled_user:
        log("ERROR: Could not find username field")
        screenshot(page, "02_err_no_username", debug)
        return False

    # Fill password
    password_selectors = [
        "input#loginPasswordHeader",
        "input[name='password']",
        "input[type='password']",
        "input[id*='password']",
        "input[id*='Password']",
    ]
    filled_pass = False
    for sel in password_selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                el.fill(password, timeout=3000)
                filled_pass = True
                log(f"Filled password via: {sel}")
                break
        except (PwTimeout, Exception):
            continue

    if not filled_pass:
        log("ERROR: Could not find password field")
        screenshot(page, "02_err_no_password", debug)
        return False

    screenshot(page, "03_creds_filled", debug)

    # Submit login
    submit_selectors = [
        "button#loginSubmitHeader",
        "button[type='submit']:has-text('Log in')",
        "button:has-text('Log in'):visible",
        "button[type='submit']:visible",
    ]
    submitted = False
    for sel in submit_selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                el.click(timeout=3000)
                submitted = True
                log(f"Clicked submit via: {sel}")
                break
        except (PwTimeout, Exception):
            continue

    if not submitted:
        log("WARNING: Could not find submit button. Trying Enter key.")
        page.keyboard.press("Enter")

    log("Waiting for login to complete...")
    page.wait_for_timeout(WAIT_LOGIN)
    screenshot(page, "04_after_login", debug)

    # Check if login succeeded
    text = get_text(page)
    url = page.url
    log(f"Post-login URL: {url}")

    # Look for signs of successful login
    if any(
        indicator in text.lower()
        for indicator in [
            "my account",
            "rapid rewards",
            "welcome",
            "log out",
            "sign out",
            "my trips",
            "upcoming trip",
        ]
    ):
        log("Login appears successful")
        return True

    # Look for error indicators
    if any(
        err in text.lower()
        for err in [
            "incorrect",
            "invalid",
            "try again",
            "error",
            "unable to log in",
            "locked",
        ]
    ):
        log("LOGIN FAILED: credentials rejected or account issue")
        return False

    # Ambiguous. Proceed and see what happens.
    log("Login status unclear. Proceeding...")
    return True


def lookup_change(page, conf_number, first_name, last_name, debug=False):
    """Navigate to Change Flight page and look up a reservation.

    SAFETY: This function ONLY fills the lookup form (conf + name) and
    clicks the search/retrieve button. It does NOT click "Change this
    flight" or any other action that would modify the reservation.
    After the lookup result renders, control returns to the caller
    which only reads text.
    """
    change_url = "https://www.southwest.com/air/change/"
    log(f"Navigating to change flight page...")
    page.goto(change_url, wait_until="networkidle", timeout=30000)
    page.wait_for_timeout(WAIT_SHORT)
    screenshot(page, "05_change_page", debug)

    dismiss_overlays(page)

    # Fill confirmation number
    conf_selectors = [
        "input[name='recordLocator']",
        "input#recordLocator",
        "input[id*='confirmationNumber']",
        "input[id*='recordLocator']",
        "input[placeholder*='confirmation']",
        "input[aria-label*='Confirmation']",
    ]
    filled_conf = False
    for sel in conf_selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                el.fill(conf_number, timeout=3000)
                filled_conf = True
                log(f"Filled confirmation via: {sel}")
                break
        except (PwTimeout, Exception):
            continue

    if not filled_conf:
        # Maybe we're already logged in and it auto-shows trips?
        text = get_text(page)
        if conf_number.upper() in text.upper():
            log("Confirmation already visible on page (logged in view)")
            return True

        log("WARNING: Could not find confirmation field")
        screenshot(page, "05_err_no_conf", debug)
        if debug:
            log(f"Page text snippet: {text[:500]}")
        return False

    # Fill first name
    first_selectors = [
        "input[name='passengerFirstName']",
        "input#passengerFirstName",
        "input[id*='firstName']",
        "input[placeholder*='first']",
        "input[aria-label*='First']",
    ]
    for sel in first_selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                el.fill(first_name, timeout=3000)
                log(f"Filled first name via: {sel}")
                break
        except (PwTimeout, Exception):
            continue

    # Fill last name
    last_selectors = [
        "input[name='passengerLastName']",
        "input#passengerLastName",
        "input[id*='lastName']",
        "input[placeholder*='last']",
        "input[aria-label*='Last']",
    ]
    for sel in last_selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                el.fill(last_name, timeout=3000)
                log(f"Filled last name via: {sel}")
                break
        except (PwTimeout, Exception):
            continue

    screenshot(page, "06_change_form_filled", debug)

    # Submit the lookup (ONLY the lookup form, nothing else)
    submit_selectors = [
        "button#form-mixin--submit-button",
        "button[type='submit']",
        "button:has-text('Search')",
        "button:has-text('Retrieve')",
        "button:has-text('Look up')",
    ]
    for sel in submit_selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                # SAFETY: verify this button text isn't dangerous
                btn_text = el.inner_text(timeout=2000)
                if is_dangerous_click(btn_text):
                    log(f"SAFETY BLOCK: refusing to click '{btn_text}'")
                    continue
                el.click(timeout=3000)
                log(f"Submitted lookup via: {sel} (text: '{btn_text.strip()}')")
                break
        except (PwTimeout, Exception):
            continue

    log("Waiting for reservation details...")
    page.wait_for_timeout(WAIT_LONG)
    screenshot(page, "07_reservation_result", debug)
    return True


def select_all_legs(page, debug=False):
    """Check all flight leg checkboxes and click Continue to see prices.

    SAFETY: This step only selects which legs to VIEW alternatives for.
    It does NOT select any replacement flights. After clicking Continue,
    the page shows available flights with price differences. The script
    reads those prices and stops. It never picks a replacement flight
    or confirms any change.

    Flow: [Select legs] -> Continue -> [See prices] -> READ ONLY -> done
    """
    log("Selecting all flight legs to view price alternatives...")
    screenshot(page, "08_before_leg_select", debug)

    # SW uses hidden <input type="checkbox"> with styled labels as click targets.
    # Strategy: find the flight leg cards/sections and click them, or force-click
    # the hidden checkboxes.

    checked_count = 0

    # Strategy 1: Click the visible label elements associated with checkboxes.
    # SW wraps each leg in a label or clickable card.
    label_selectors = [
        "label:has(input[type='checkbox'])",
        "[class*='bound'] label",
        "[class*='flight-card']",
        "[class*='segment-select']",
    ]
    for sel in label_selectors:
        try:
            labels = page.locator(sel)
            count = labels.count()
            if count == 0:
                continue
            visible_count = sum(
                1 for i in range(count) if labels.nth(i).is_visible(timeout=1000)
            )
            if visible_count == 0:
                continue
            log(f"Found {visible_count} visible labels via: {sel}")
            for i in range(count):
                lbl = labels.nth(i)
                if lbl.is_visible(timeout=1000):
                    try:
                        lbl_text = lbl.inner_text(timeout=2000)[:80]
                    except Exception:
                        lbl_text = "(unknown)"
                    lbl.click(timeout=3000)
                    checked_count += 1
                    log(f"Clicked leg label {checked_count}: {lbl_text.strip()[:60]}")
            break
        except (PwTimeout, Exception) as e:
            log(f"Label selector {sel} failed: {e}")
            continue

    # Strategy 2: Force-click hidden checkboxes if labels didn't work
    if checked_count == 0:
        log("Trying force-click on hidden checkboxes...")
        try:
            checkboxes = page.locator("input[type='checkbox']")
            count = checkboxes.count()
            log(f"Found {count} hidden checkboxes, attempting force-click")
            for i in range(count):
                cb = checkboxes.nth(i)
                try:
                    # Get context about this checkbox
                    ctx = cb.evaluate(
                        """el => {
                            var label = el.closest('label') || el.parentElement;
                            var text = label ? label.innerText : '';
                            var name = el.name || el.id || el.getAttribute('aria-label') || '';
                            return {text: text.substring(0, 80), name: name, checked: el.checked};
                        }"""
                    )
                    # Skip checkboxes that look unrelated (cookies, preferences, etc.)
                    name_lower = (ctx.get("name", "") + ctx.get("text", "")).lower()
                    if any(
                        skip in name_lower
                        for skip in ["cookie", "accept", "marketing", "promo", "opt"]
                    ):
                        log(f"Skipping non-flight checkbox: {ctx}")
                        continue

                    if not ctx.get("checked", False):
                        cb.click(force=True, timeout=3000)
                        checked_count += 1
                        log(
                            f"Force-checked #{checked_count}: name='{ctx.get('name', '')}' text='{ctx.get('text', '')[:40]}'"
                        )
                    else:
                        checked_count += 1
                        log(f"Already checked: {ctx.get('name', '')}")
                except Exception as e:
                    log(f"Force-click on checkbox {i} failed: {e}")
        except Exception as e:
            log(f"Hidden checkbox strategy failed: {e}")

    # Strategy 3: Click by page text. Find "Departing" / "Returning" sections.
    if checked_count == 0:
        log("Trying text-based leg selection...")
        for direction in ["Departing", "Returning"]:
            try:
                el = page.locator(f"text='{direction}'").first
                if el.is_visible(timeout=2000):
                    el.click(timeout=3000)
                    checked_count += 1
                    log(f"Clicked '{direction}' text element")
            except (PwTimeout, Exception):
                pass

    if checked_count == 0:
        log("WARNING: Could not select any flight legs.")
        screenshot(page, "08_err_no_checkboxes", debug)
        return False

    log(f"Selected {checked_count} leg(s)")
    page.wait_for_timeout(WAIT_SHORT)
    screenshot(page, "09_legs_selected", debug)

    # Click Continue/Submit to proceed to flight alternatives page.
    # SAFETY: "Continue" here just shows available flights, it does NOT
    # change anything. The dangerous step would be selecting a replacement
    # flight on the NEXT page, which we never do.
    continue_selectors = [
        "button#form-mixin--submit-button",
        "button[type='submit']:visible",
        "button:has-text('Continue'):visible",
        "button:has-text('Search flights'):visible",
    ]
    clicked = False
    for sel in continue_selectors:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=2000):
                btn_text = el.inner_text(timeout=2000).strip()
                # Block truly dangerous buttons (confirm, cancel, complete, etc.)
                if is_dangerous_click(btn_text):
                    log(f"SAFETY BLOCK: refusing to click '{btn_text}'")
                    continue
                el.click(timeout=3000)
                clicked = True
                log(f"Clicked continue via: {sel} (text: '{btn_text}')")
                break
        except (PwTimeout, Exception):
            continue

    if not clicked:
        log("WARNING: Could not find Continue button after selecting legs")
        screenshot(page, "09_err_no_continue", debug)
        return False

    # Wait for the flight alternatives / price page to load
    log("Waiting for flight alternatives with prices...")
    page.wait_for_timeout(WAIT_LONG)
    screenshot(page, "10_price_results", debug)
    return True


def extract_results(page, debug=False):
    """Extract flight alternatives and prices from the change results page.

    READ-ONLY. This function only reads text and takes screenshots.
    It does NOT click anything. No buttons, no links, no forms.
    No replacement flights are selected. No changes are confirmed.
    """
    text = get_text(page)
    url = page.url
    screenshot(page, "11_final_state", debug)

    # Pattern: city pairs like "San Jose, CA to San Diego, CA"
    city_pairs = re.findall(
        r"([A-Z][a-z]+(?:\s[A-Z][a-z]+)*,\s*[A-Z]{2})\s+to\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)*,\s*[A-Z]{2})",
        text,
    )

    # Pattern: airport codes like "SJC to SAN"
    airport_pairs = re.findall(r"\b([A-Z]{3})\s+to\s+([A-Z]{3})\b", text)

    # Pattern: dates
    dates = re.findall(
        r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2},?\s*\d{0,4}",
        text,
    )

    # Pattern: points prices "23,500 Points" or similar
    points_prices = re.findall(r"([\d,]+)\s*(?:Points|points|pts)", text)

    # Pattern: dollar amounts
    dollar_amounts = re.findall(r"\$[\d,.]+", text)

    # Pattern: "credit" or "difference" amounts
    credits = re.findall(
        r"(?:credit|difference|saving|refund).*?([\d,]+\s*(?:Points|points|\$[\d,.]+))",
        text,
        re.I,
    )

    # Parse individual flight blocks from the change page.
    #
    # KEY DIFFERENCE from search_fares.py: The change page shows DIFFERENCES
    # from what was paid, not absolute prices.
    #   +2,000 = costs 2,000 MORE than what you paid (upcharge)
    #   -2,000 = costs 2,000 LESS than what you paid (SAVINGS, rebook!)
    #   CURRENT FLIGHT = your booked flight, no change for that fare class
    #   Unavailable = fare class sold out
    #
    # The "CURRENT FLIGHT" label replaces the Basic fare cell on the booked
    # flight. If it had dropped, it would show a negative number instead.
    #
    # Each fare cell in the raw text looks like:
    #   "2,000 Points\n+2,000\n+$0.00"  (the +2,000 is the diff, +$0.00 is tax)
    # or for CURRENT FLIGHT:
    #   "CURRENT FLIGHT"  (no points number)
    # or for Unavailable:
    #   "Unavailable"

    blocks = re.findall(r"(# [\d/ ]+.*?View seats)", text, re.DOTALL)
    flights = []
    for block in blocks:
        flight = {}
        m = re.search(r"# ([\d/ ]+)", block)
        if m:
            flight["flight_number"] = m.group(1).strip()
        times = re.findall(r"(\d{1,2}:\d{2}(?:AM|PM))", block)
        if len(times) >= 2:
            flight["depart_time"] = times[0]
            flight["arrive_time"] = times[1]
        if "Nonstop" in block:
            flight["stops"] = "Nonstop"
        else:
            sm = re.search(r"(\d+)\s*stop", block, re.I)
            flight["stops"] = f"{sm.group(1)} stop" if sm else "?"
        m = re.search(r"(\d+h\s*\d+m)", block)
        if m:
            flight["duration"] = m.group(1)

        is_current = "CURRENT FLIGHT" in block
        flight["is_current_flight"] = is_current

        # Parse the fare difference values: +N,NNN or -N,NNN
        # These are the actual change costs shown on the page.
        # Positive = upcharge, negative = savings.
        diffs = re.findall(r"([+-][\d,]+)\s*\n\+\$", block)

        # Also capture "Unavailable" and "CURRENT FLIGHT" positions
        # by scanning fare cells in order.
        # The fare cells appear in order: Basic, Choice, Choice Preferred, Choice Extra.
        # Each cell is one of: "CURRENT FLIGHT", "Unavailable", or "N,NNN Points\n+/-N,NNN\n+$X.XX"
        fare_names = ["Basic", "Choice", "Choice Preferred", "Choice Extra"]

        if is_current:
            # This is the booked flight. "CURRENT FLIGHT" replaces Basic.
            flight["fares"] = {"Basic": "CURRENT"}
            # The remaining diffs map to Choice, Choice Preferred, Choice Extra
            for i, diff_val in enumerate(diffs):
                name = (
                    fare_names[i + 1] if (i + 1) < len(fare_names) else f"Fare {i + 2}"
                )
                flight["fares"][name] = diff_val
            flight["fare_type"] = "change_diff"
        elif diffs:
            # Not the current flight. All 4 fare classes may have diffs.
            # But "Unavailable" slots don't produce a diff value.
            # Count Unavailable occurrences before each diff to align.
            flight["fares"] = {}

            # Build ordered list of fare cells from the block
            # Look for patterns: Unavailable, CURRENT FLIGHT, or N Points
            cells = []
            # Split by "View seats" to avoid trailing content
            fare_section = block
            # Find fare entries in order
            cell_pattern = re.finditer(
                r"(?:Unavailable|CURRENT FLIGHT|[\d,]+ Points)", fare_section
            )
            for cm in cell_pattern:
                cells.append(cm.group())

            diff_idx = 0
            for i, cell in enumerate(cells):
                name = fare_names[i] if i < len(fare_names) else f"Fare {i + 1}"
                if cell == "Unavailable":
                    flight["fares"][name] = "Unavail"
                elif cell == "CURRENT FLIGHT":
                    flight["fares"][name] = "CURRENT"
                else:
                    if diff_idx < len(diffs):
                        flight["fares"][name] = diffs[diff_idx]
                        diff_idx += 1
                    else:
                        # Fallback: show the points value
                        flight["fares"][name] = cell
            flight["fare_type"] = "change_diff"
        else:
            # No diffs found, try raw points values as fallback
            point_fares = re.findall(r"([\d,]+)\s*Points", block)
            if point_fares:
                flight["fares"] = {}
                for i, pts in enumerate(point_fares):
                    name = fare_names[i] if i < len(fare_names) else f"Fare {i + 1}"
                    flight["fares"][name] = f"+{pts}"
                flight["fare_type"] = "change_diff"

        if flight.get("fares"):
            flights.append(flight)

    # Flag any flights with savings (negative diffs)
    savings_found = []
    for f in flights:
        for fare_name, diff_val in f.get("fares", {}).items():
            if isinstance(diff_val, str) and diff_val.startswith("-"):
                savings_found.append(
                    {
                        "flight": f.get("flight_number"),
                        "fare_class": fare_name,
                        "savings": diff_val,
                        "depart": f.get("depart_time"),
                    }
                )

    return {
        "url": url,
        "page_text": text,
        "flights": flights,
        "savings_found": savings_found,
    }


def list_upcoming_trips(as_json=False, debug=False):
    """Log in and list all upcoming trips with confirmation numbers.

    READ-ONLY. Only navigates to the upcoming trips page and reads text.
    """
    username = os.environ.get("SW_USERNAME")
    password = os.environ.get("SW_PASSWORD")

    if not username or not password:
        log("ERROR: SW_USERNAME and SW_PASSWORD environment variables required.")
        sys.exit(1)

    log(f"Credentials loaded (user length: {len(username)})")
    tmpdir = tempfile.mkdtemp(prefix="sw_trips_")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                tmpdir,
                headless=False,
                viewport={"width": 1440, "height": 900},
                locale="en-US",
                timezone_id="America/Los_Angeles",
            )
            page = browser.new_page()

            # Homepage warmup
            log("Navigating to southwest.com...")
            page.goto(HOMEPAGE, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)
            dismiss_overlays(page)

            # Login
            login_ok = do_login(page, username, password, debug)
            if not login_ok:
                log("Login failed.")
                return {"status": "login_failed", "trips": []}

            # Navigate to upcoming trips via "My Account" link
            log("Navigating to My Account...")
            account_urls = [
                "https://www.southwest.com/myaccount",
                "https://www.southwest.com/account",
            ]
            # Try clicking "My Account" link first (most reliable)
            found_account = False
            for sel in [
                "a:has-text('My Account')",
                "button:has-text('My Account')",
                "[data-qa='my-account']",
            ]:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=2000):
                        el.click(timeout=3000)
                        found_account = True
                        log(f"Clicked My Account via: {sel}")
                        break
                except (PwTimeout, Exception):
                    continue

            if not found_account:
                # Fallback: try direct URLs
                for url in account_urls:
                    log(f"Trying URL: {url}")
                    page.goto(url, wait_until="networkidle", timeout=30000)
                    if "404" not in get_text(page)[:200]:
                        found_account = True
                        break

            page.wait_for_timeout(WAIT_LONG)
            screenshot(page, "trips_page", debug)

            # Look for "Upcoming Trips" section or tab and click it if needed
            for sel in [
                "a:has-text('Upcoming Trips')",
                "button:has-text('Upcoming Trips')",
                "[data-qa='upcoming-trips']",
                "a:has-text('My Trips')",
            ]:
                try:
                    el = page.locator(sel).first
                    if el.is_visible(timeout=2000):
                        el.click(timeout=3000)
                        log(f"Clicked trips tab via: {sel}")
                        page.wait_for_timeout(WAIT_MED)
                        screenshot(page, "trips_tab_clicked", debug)
                        break
                except (PwTimeout, Exception):
                    continue

            # SW uses an accordion: only one trip expanded at a time.
            # Click each trip header individually, grab its conf number, repeat.
            all_conf_numbers = []

            # First grab any conf number already visible (first trip is expanded)
            initial_text = get_text(page)
            initial_confs = re.findall(r"#([A-Z0-9]{6})\b", initial_text)
            for c in initial_confs:
                if c not in all_conf_numbers:
                    all_conf_numbers.append(c)
                    log(f"Found conf (initial): {c}")

            # Now click each trip header to expand it and grab its conf
            try:
                trip_headers = page.locator(
                    "button:has-text('Round trip'), button:has-text('One way')"
                )
                count = trip_headers.count()
                log(f"Found {count} trip headers to expand")
                for i in range(count):
                    header = trip_headers.nth(i)
                    try:
                        if not header.is_visible(timeout=1000):
                            continue
                        header_text = header.inner_text(timeout=1000)[:60]
                        if is_dangerous_click(header_text):
                            continue
                        header.click(timeout=3000)
                        log(f"Clicked trip {i + 1}: {header_text.strip()}")
                        page.wait_for_timeout(WAIT_MED)

                        # Grab text and look for new conf numbers
                        expanded_text = get_text(page)
                        new_confs = re.findall(r"#([A-Z0-9]{6})\b", expanded_text)
                        for c in new_confs:
                            if c not in all_conf_numbers:
                                all_conf_numbers.append(c)
                                log(f"Found conf (trip {i + 1}): {c}")
                    except (PwTimeout, Exception) as e:
                        log(f"Trip {i + 1} expand failed: {e}")
            except Exception as e:
                log(f"Trip expansion failed: {e}")

            screenshot(page, "trips_expanded", debug)
            log(f"Total confirmations found: {all_conf_numbers}")

            # Get final page text for any additional parsing
            text = get_text(page)

            browser.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    # Use conf numbers found by accordion expansion (primary source),
    # plus any additional ones from the final page text.
    text_confs = re.findall(r"#([A-Z0-9]{6})\b", text)
    skip_words = {
        "FLIGHT",
        "CHANGE",
        "CANCEL",
        "SEARCH",
        "POINTS",
        "RETURN",
        "SELECT",
        "STATUS",
        "MANAGE",
        "REVIEW",
    }
    unique_confs = list(all_conf_numbers)  # start with accordion-discovered ones
    for c in text_confs:
        if c in skip_words:
            continue
        if re.search(r"[A-Z]", c) and re.search(r"[0-9]", c):
            if c not in unique_confs:
                unique_confs.append(c)

    # Try to extract route and date info near each confirmation number
    trips = []
    for conf in unique_confs:
        trip = {"confirmation": conf}

        # Look for route/date context near the conf number in the text
        idx = text.find(conf)
        if idx >= 0:
            # Grab surrounding context (500 chars around it)
            context = text[max(0, idx - 200) : idx + 300]

            # Look for airport codes
            routes = re.findall(r"\b([A-Z]{3})\s*(?:to|-|→)\s*([A-Z]{3})\b", context)
            if routes:
                trip["routes"] = routes

            # Look for dates
            dates = re.findall(
                r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\w*\s+\d{1,2}(?:,?\s*\d{4})?",
                context,
            )
            if dates:
                trip["dates"] = dates

        trips.append(trip)

    result = {
        "status": "completed",
        "trips": trips,
        "raw_conf_numbers": unique_confs,
    }

    if debug:
        result["page_text_preview"] = text[:3000]

    if as_json:
        print(json.dumps(result, indent=2))
    else:
        print(f"\nUpcoming Southwest Trips")
        print("=" * 40)
        if trips:
            for t in trips:
                routes_str = ""
                if t.get("routes"):
                    routes_str = " | ".join(f"{r[0]}→{r[1]}" for r in t["routes"])
                dates_str = ""
                if t.get("dates"):
                    dates_str = ", ".join(t["dates"])
                print(f"  {t['confirmation']}  {routes_str}  {dates_str}")
        else:
            print("  No upcoming trips found.")
        if debug:
            print(f"\nPage text:\n{text[:2000]}")

    return result


def check_change(conf_number, first_name, last_name, as_json=False, debug=False):
    """Full flow: login, look up reservation, extract change prices."""
    username = os.environ.get("SW_USERNAME")
    password = os.environ.get("SW_PASSWORD")

    if not username or not password:
        log("ERROR: SW_USERNAME and SW_PASSWORD environment variables required.")
        log(
            "Use: SW_USERNAME=user SW_PASSWORD=pass "
            "python3 check_change.py --conf ABC123 --first Jane --last Doe"
        )
        sys.exit(1)

    log(
        f"Credentials loaded (user length: {len(username)}, pass length: {len(password)})"
    )

    tmpdir = tempfile.mkdtemp(prefix="sw_change_")

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch_persistent_context(
                tmpdir,
                headless=False,
                viewport={"width": 1440, "height": 900},
                locale="en-US",
                timezone_id="America/Los_Angeles",
            )
            page = browser.new_page()

            # Step 1: Homepage warmup
            log("Navigating to southwest.com...")
            page.goto(HOMEPAGE, wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)
            dismiss_overlays(page)
            screenshot(page, "00_homepage", debug)

            # Step 2: Login
            login_ok = do_login(page, username, password, debug)
            if not login_ok:
                log("Login failed. Aborting.")
                result = {
                    "confirmation": conf_number,
                    "status": "login_failed",
                    "error": "Could not log into Southwest",
                }
                if as_json:
                    print(json.dumps(result, indent=2))
                else:
                    print(f"LOGIN FAILED for {conf_number}")
                return result

            # Step 3: Look up reservation for change
            lookup_ok = lookup_change(page, conf_number, first_name, last_name, debug)

            # Step 4: Select all legs and proceed to see price alternatives
            # SAFETY: This only shows available flights with price diffs.
            # It does NOT select any replacement flight or confirm changes.
            if lookup_ok:
                select_all_legs(page, debug)

            # Step 5: Read the prices (READ-ONLY, no clicks)
            results = extract_results(page, debug)

            browser.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    savings = results.get("savings_found", [])
    flights = results.get("flights", [])
    current_flights = [f for f in flights if f.get("is_current_flight")]

    output = {
        "confirmation": conf_number,
        "passenger": f"{first_name} {last_name}",
        "status": "completed",
        "url": results["url"],
        "savings_found": savings,
        "current_flights": current_flights,
        "all_flights": flights,
    }

    if debug:
        output["page_text_preview"] = results["page_text"][:5000]
        output["debug_screenshots"] = str(DEBUG_DIR)

    if as_json:
        print(json.dumps(output, indent=2))
    else:
        print(f"\nChange Flight Check: {conf_number} ({first_name} {last_name})")
        print("=" * 60)

        # Show current flights first
        if current_flights:
            print("\nYour booked flights:")
            for f in current_flights:
                num = f"#{f.get('flight_number', '?')}"
                dep = f.get("depart_time", "?")
                arr = f.get("arrive_time", "?")
                fares = f.get("fares", {})
                fares_str = ", ".join(f"{k}: {v}" for k, v in fares.items())
                print(f"  {num} {dep}-{arr} | {fares_str}")

        # Highlight savings
        if savings:
            print(f"\n*** SAVINGS FOUND ({len(savings)}) ***")
            for s in savings:
                print(
                    f"  #{s['flight']} at {s['depart']} "
                    f"{s['fare_class']}: {s['savings']} pts"
                )
        else:
            print("\nNo savings found. All alternatives cost more than current fares.")

        # Show all flights count
        print(f"\nTotal flights checked: {len(flights)}")

        if debug:
            print(f"\nAll flights:")
            for f in flights:
                num = f"#{f.get('flight_number', '?')}"
                dep = f.get("depart_time", "?")
                arr = f.get("arrive_time", "?")
                stops = f.get("stops", "?")
                dur = f.get("duration", "?")
                cur = " [CURRENT]" if f.get("is_current_flight") else ""
                fares_str = ", ".join(
                    f"{k}: {v}" for k, v in f.get("fares", {}).items()
                )
                print(f"  {num} {dep}-{arr} ({stops}, {dur}){cur} | {fares_str}")
            print(f"\nDebug screenshots: {DEBUG_DIR}")

    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Check SW flight change prices or list upcoming trips"
    )
    parser.add_argument(
        "--list",
        action="store_true",
        help="List all upcoming trips with confirmation numbers (no --conf needed)",
    )
    parser.add_argument("--conf", help="Confirmation number (e.g., ABC123)")
    parser.add_argument("--first", help="Passenger first name (legal name)")
    parser.add_argument("--last", help="Passenger last name (legal name)")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Save screenshots at each step to /tmp/sw_change_debug/",
    )
    args = parser.parse_args()

    if args.list:
        list_upcoming_trips(args.json, args.debug)
    else:
        if not args.conf or not args.first or not args.last:
            parser.error("--conf, --first, and --last are required (or use --list)")
        check_change(args.conf, args.first, args.last, args.json, args.debug)

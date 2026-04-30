#!/usr/bin/env python3
"""
Chase Travel portal search via API + Patchright auth.

Uses the internal Chase Travel API discovered via network recording.
Patchright handles login/auth only. All searches go through API calls
made within the authenticated browser context (no form automation).

Usage:
    # Flight search (local, pops up Chrome window)
    python3 search_flights.py --origin SFO --dest CDG --depart 2026-08-11

    # Round-trip
    python3 search_flights.py --origin SFO --dest CDG --depart 2026-08-11 --return 2026-09-02

    # Business class
    python3 search_flights.py --origin SFO --dest CDG --depart 2026-08-11 --cabin business

    # Hotel search
    python3 search_flights.py --hotel --dest "Paris" --checkin 2026-08-11 --checkout 2026-08-15

    # JSON output
    python3 search_flights.py --origin SFO --dest CDG --depart 2026-08-11 --json

    # Docker (no window)
    docker run --rm \
        -v ~/.chase-travel-profiles:/profiles \
        -v /tmp:/tmp/host \
        -e CHASE_USERNAME -e CHASE_PASSWORD \
        ghcr.io/borski/patchright-docker script /scripts/search_flights.py \
        --origin SFO --dest CDG --depart 2026-08-11

Environment:
    CHASE_USERNAME    - Chase online username
    CHASE_PASSWORD    - Chase online password
    CHASE_2FA_COMMAND - Optional: command to get SMS 2FA code (blocks, prints to stdout)
    CHASE_PROFILE     - Profile directory (default: /profiles or ~/.chase-travel-profiles/default)
"""

import argparse
import base64
import json
import os
import re
import sys
import time
from pathlib import Path

# Chase Travel API base URLs
SECURE_BASE = "https://secure.chase.com/svc/wr/profile/l4/gateway/chase-travel/loyalty/bank-rewards/cte-app/v1"
TRAVEL_BASE = "https://travelsecure.chase.com/api/air/v1.0"

# Account identifier (auto-extracted from portal URL during card selection)
_CARD_AI = ""


def _portal_url(path="travel"):
    """Build a portal URL with the current AI parameter."""
    base = f"https://ultimaterewardspoints.chase.com/{path}"
    return f"{base}?AI={_CARD_AI}" if _CARD_AI else base


def _find_sapphire_link(page):
    """Find the Sapphire Reserve or Preferred card link on the account selector page.

    Looks for <a> elements whose accessible text or aria-label contains
    'sapphire reserve' or 'sapphire preferred'. Falls back to any credit card link.
    """
    # Try by accessible text in parent li
    for keyword in ["sapphire reserve", "sapphire preferred"]:
        link = page.evaluate(f"""() => {{
            const items = document.querySelectorAll('li.list-item--navigational, mds-list-item');
            for (const item of items) {{
                const text = (item.querySelector('.accessible-text')?.textContent
                    || item.getAttribute('image-alt-text')
                    || item.getAttribute('navigational-accessible-description')
                    || item.innerText || '').toLowerCase();
                if (text.includes('{keyword}')) {{
                    const a = item.querySelector('a.list-item__navigational');
                    const href = a?.href || item.getAttribute('href') || '';
                    if (a) {{ a.click(); return 'clicked-a|' + href; }}
                    if (item.getAttribute('href')) {{ item.click(); return 'clicked-item|' + href; }}
                }}
            }}
            return null;
        }}""")
        if link:
            # Extract AI from the href if present
            parts = link.split("|", 1)
            href = parts[1] if len(parts) > 1 else ""
            ai_match = re.search(r"[?&]AI=(\d+)", href)
            if ai_match:
                global _CARD_AI
                _CARD_AI = ai_match.group(1)
            print(f"  Found {keyword} ({parts[0]})", file=sys.stderr)
            return True  # Already clicked

    # Fallback: any card link
    card = page.query_selector(
        'a[aria-label*="CREDIT CARD"], a.list-item__navigational'
    )
    return card


import subprocess


# ============================================================
# Auth helpers
# ============================================================


def get_profile_dir():
    """Get browser profile directory."""
    env_dir = os.environ.get("CHASE_PROFILE")
    if env_dir:
        return env_dir
    if Path("/profiles/default").exists():
        return "/profiles/default"
    if Path("/profiles").exists():
        return "/profiles/default"
    return str(Path.home() / ".chase-travel-profiles" / "default")


def get_cookie_path():
    """Get cookie file path."""
    profile = get_profile_dir()
    return os.path.join(os.path.dirname(profile), "cookies.json")


def save_cookies(context, path):
    """Export cookies from browser context to JSON file."""
    cookies = context.cookies()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(cookies, f, indent=2)
    print(f"Saved {len(cookies)} cookies to {path}", file=sys.stderr)


def inject_cookies(context, path):
    """Inject saved cookies into browser context."""
    if not os.path.exists(path):
        return False
    with open(path) as f:
        cookies = json.load(f)
    if not cookies:
        return False
    chase_cookies = [c for c in cookies if "chase.com" in c.get("domain", "")]
    if chase_cookies:
        context.add_cookies(chase_cookies)
        print(f"Injected {len(chase_cookies)} Chase cookies", file=sys.stderr)
        return True
    return False


def is_logged_in(page):
    """Check if we're logged into Chase."""
    url = page.url.lower()
    if "logoff" in url or "logon" in url:
        return False
    # /auth/dashboard is logged in; /auth/logon is not
    if "/auth/" in url and "dashboard" not in url:
        return False
    if "dashboard" in url:
        return True
    if "account-selector" in url:
        return True
    if "ultimaterewardspoints.chase.com" in url:
        return True
    if "accounts.chase.com" in url:
        return True
    text = page.inner_text("body")[:2000].lower()
    return "sign out" in text and ("accounts" in text or "points" in text)


def wait_for_2fa_code(timeout=180):
    """Wait for 2FA SMS code via env var or file polling."""
    # Command hook: run a custom command that blocks until it has the code
    hook_cmd = os.environ.get("CHASE_2FA_COMMAND", "").strip()
    if hook_cmd:
        print("Running 2FA command hook...", file=sys.stderr)
        try:
            result = subprocess.run(
                hook_cmd, shell=True, capture_output=True, text=True, timeout=timeout
            )
            code = result.stdout.strip()
            if code:
                print(f"Got 2FA code from hook: {code[:2]}****", file=sys.stderr)
                return code
        except Exception as e:
            print(f"2FA hook failed: {e}", file=sys.stderr)

    host_path = "/tmp/host/chase-2fa-code.txt"
    local_path = "/tmp/chase-2fa-code.txt"

    for status_path in ["/tmp/host/chase-2fa-status.txt", "/tmp/chase-2fa-status.txt"]:
        try:
            with open(status_path, "w") as f:
                f.write("CODE_NEEDED")
        except OSError:
            pass

    print("2FA_CODE_NEEDED", flush=True)
    print("2FA REQUIRED: Chase sent an SMS code.", file=sys.stderr)
    print("Write code to /tmp/chase-2fa-code.txt", file=sys.stderr)

    start = time.time()
    while time.time() - start < timeout:
        for code_file in [host_path, local_path]:
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
    """Handle Chase 2FA flow. Returns True on success."""
    text = page.inner_text("body")[:2000].lower()

    is_2fa = (
        "confirm your identity" in text
        or "let's make sure it's you" in text
        or "enter your code" in text
        or ("verify" in text and "verification" in text)
    )
    if not is_2fa:
        return True

    print("2FA detected. Selecting SMS method...", file=sys.stderr)

    sms_btn = page.query_selector("mds-list-item#sms")
    if sms_btn:
        page.evaluate("document.querySelector('mds-list-item#sms').click()")
        time.sleep(3)

    # Select SECOND phone number (first doesn't send reliably)
    phone_radio = page.query_selector("#eligibleTextContacts-input-1")
    if not phone_radio:
        phone_radio = page.query_selector("#eligibleTextContacts-input-0")
    if phone_radio:
        phone_radio.click()
        time.sleep(1)

    next_btn = page.query_selector('button:has-text("Next")')
    if next_btn:
        next_btn.click()
        time.sleep(5)

    code = wait_for_2fa_code()
    if not code:
        print("ERROR: No 2FA code provided within timeout.", file=sys.stderr)
        return False

    print(f"Got 2FA code: {code[:2]}****{code[-2:]}", file=sys.stderr)

    otp_input = page.query_selector("#otpInput-input")
    if not otp_input:
        for sel in [
            "input[name='otp-input']",
            "input[name*='otp']",
            "input[name*='code']",
            "input[type='password']",
            "input[type='tel']",
            "#otpcode",
            "input[id*='otp']",
            "input[id*='code']",
        ]:
            otp_input = page.query_selector(sel)
            if otp_input:
                break

    if otp_input:
        otp_input.click()
        time.sleep(0.3)
        otp_input.type(code, delay=50)
    else:
        print("ERROR: Could not find OTP input field", file=sys.stderr)
        return False

    time.sleep(1)

    next_btn = page.query_selector('button:has-text("Next")')
    if not next_btn:
        next_btn = page.query_selector('button:has-text("Verify")')
    if not next_btn:
        next_btn = page.query_selector('button[type="submit"]')
    if next_btn:
        next_btn.click()
    else:
        page.keyboard.press("Enter")

    time.sleep(12)

    body = page.inner_text("body")[:2000].lower()
    if "remember" in body or "trust" in body or "don't ask" in body:
        for label in ["Yes", "Remember", "Trust", "Don't ask again"]:
            btn = page.query_selector(f'button:has-text("{label}")')
            if btn and btn.is_visible():
                btn.click()
                time.sleep(5)
                break

    logged_in = is_logged_in(page)
    if not logged_in:
        print(f"Post-2FA URL: {page.url}", file=sys.stderr)
    return logged_in


def login(page, context, username, password, cookie_path):
    """Log into Chase. Returns True on success."""
    in_docker = os.path.exists("/.dockerenv") or os.environ.get("DOCKER", "")

    # Try cookie injection first
    if inject_cookies(context, cookie_path):
        page.goto(_portal_url(), timeout=30000)
        time.sleep(5)
        for _ in range(5):
            if any(x in page.url.lower() for x in ["logoff", "logon", "/auth/"]):
                print("Cookie session expired", file=sys.stderr)
                break
            if is_logged_in(page):
                print("Logged in via saved cookies", file=sys.stderr)
                return True
            time.sleep(2)
        print("Saved cookies expired, doing fresh login", file=sys.stderr)

    if in_docker:
        page.goto("https://www.chase.com", timeout=30000)
        time.sleep(5)
        page.fill("#userId-text-input-field", username)
        time.sleep(0.5)
        page.fill("#password-text-input-field", password)
        time.sleep(0.5)
        page.query_selector("button#signin-button").click()
    else:
        page.goto(
            "https://secure01ea.chase.com/web/auth/#/logon/logon/chaseOnline",
            timeout=30000,
        )
        time.sleep(3)
        page.fill("#userId-input-field-input", username)
        time.sleep(0.5)
        page.fill("#password-input-field-input", password)
        time.sleep(0.5)
        page.evaluate('document.getElementById("rememberMe").checked = true')
        time.sleep(0.5)
        page.click("button#signin-button")

    time.sleep(12)

    if not handle_2fa(page):
        return False

    if is_logged_in(page):
        save_cookies(context, cookie_path)
        return True

    if "accounts" in page.url.lower() or "dashboard" in page.url.lower():
        save_cookies(context, cookie_path)
        return True

    return False


# ============================================================
# Portal session setup
# ============================================================


def _extract_ai_from_url(url):
    """Extract the AI (account identifier) parameter from a Chase URL."""
    m = re.search(r"[?&]AI=(\d+)", url)
    return m.group(1) if m else ""


def navigate_to_portal(page):
    """Navigate to travel portal and establish session.

    Returns the AI (account identifier) string on success, or None on failure.
    The AI is auto-extracted from the URL after card selection.
    """
    global _CARD_AI

    # Handle account selector if present
    if "account-selector" in page.url.lower():
        print("Account selector detected, clicking CSR card...", file=sys.stderr)
        time.sleep(3)
        result = _find_sapphire_link(page)
        if result and result is not True:
            result.click()
        time.sleep(8)

    print(f"Current URL: {page.url}", file=sys.stderr)

    # Extract AI from current URL if already present
    ai = _extract_ai_from_url(page.url)

    print("Navigating to UR account selector...", file=sys.stderr)
    page.goto("https://ultimaterewardspoints.chase.com/account-selector", timeout=30000)
    time.sleep(8)

    # Handle account selector
    if "account-selector" in page.url.lower():
        print("Selecting Sapphire card...", file=sys.stderr)
        result = _find_sapphire_link(page)
        if result and result is not True:
            result.click()
        time.sleep(8)
        # After clicking, wait for redirect and try to extract AI
        for _ in range(5):
            ai = _extract_ai_from_url(page.url)
            if ai or "account-selector" not in page.url.lower():
                break
            time.sleep(2)

    # Extract AI from URL after card selection
    if not ai:
        ai = _extract_ai_from_url(page.url)

    # Update global _CARD_AI so session/create and other calls can use it
    if ai:
        _CARD_AI = ai
        print(f"Account identifier (AI): {ai}", file=sys.stderr)
    elif _CARD_AI:
        ai = _CARD_AI

    # Navigate to the travel portal on secure.chase.com (embedded).
    # API calls must be same-origin with secure.chase.com, so the standalone
    # ultimaterewardspoints.chase.com portal won't work for fetch() calls.
    dashboard_travel = "https://secure.chase.com/web/auth/dashboard#/dashboard/travel"
    page.goto(dashboard_travel, timeout=30000)
    time.sleep(8)

    # Dismiss video modal
    page.evaluate("""
        document.querySelectorAll('.chase-travel-modal-wrapper, .modal-background, [class*="modal-backdrop"]').forEach(el => el.remove());
        const observer = new MutationObserver((mutations) => {
            for (const m of mutations) {
                for (const node of m.addedNodes) {
                    if (node.nodeType === 1 && (
                        node.classList?.contains('chase-travel-modal-wrapper') ||
                        node.classList?.contains('modal-background') ||
                        node.querySelector?.('.chase-travel-modal-wrapper, .modal-background')
                    )) { node.remove(); }
                }
            }
        });
        observer.observe(document.body, { childList: true, subtree: true });
    """)
    time.sleep(2)

    # Wait for page to settle
    time.sleep(5)

    # Check if we're on the portal (standalone or embedded in dashboard)
    url = page.url
    on_standalone = "ultimaterewardspoints.chase.com" in url
    on_embedded = "dashboard" in url and "travel" in url

    if not on_standalone and not on_embedded:
        # Try navigating to embedded portal on secure.chase.com
        print(f"Not on portal yet ({url}), retrying via dashboard...", file=sys.stderr)
        page.goto(
            "https://secure.chase.com/web/auth/dashboard#/dashboard/travel",
            timeout=30000,
        )
        time.sleep(10)
        url = page.url
        on_standalone = "ultimaterewardspoints.chase.com" in url
        on_embedded = "dashboard" in url and "travel" in url

    # Last chance to extract AI from wherever we ended up
    if not ai:
        ai = _extract_ai_from_url(page.url)
        if ai:
            _CARD_AI = ai

    if "logon" in url.lower() or "logoff" in url.lower():
        print(f"Redirected to login: {url}", file=sys.stderr)
        return None

    if not on_standalone and not on_embedded:
        print(f"WARNING: Not on travel portal. URL: {url}", file=sys.stderr)
        return None

    # Verify we have the cxlPayload cookie (needed for API calls)
    cxl = extract_cxl_payload(page)
    if cxl:
        print(f"Portal session established (cxlPayload found)", file=sys.stderr)
    else:
        print(
            "WARNING: No cxlPayload cookie found. API calls may fail.", file=sys.stderr
        )

    portal_type = "standalone" if on_standalone else "embedded"
    print(f"On travel portal ({portal_type}): {url[:80]}", file=sys.stderr)
    return ai or True


def extract_cxl_payload(page):
    """Extract the cxlPayload from cookies for session info.

    The cookie value can be either:
    - Plain base64-encoded JSON (original format from Chase)
    - A JWT (header.payload.signature) where the payload is base64url-encoded JSON
    """
    cookies = page.context.cookies()
    for c in cookies:
        if c.get("name") == "chaseTravel-cxlPayload":
            try:
                import urllib.parse

                value = urllib.parse.unquote(c["value"])

                # Check if it's a JWT (three dot-separated parts)
                if value.count(".") == 2:
                    # JWT: decode the payload (second part)
                    payload_b64 = value.split(".")[1]
                    # base64url to base64
                    payload_b64 = payload_b64.replace("-", "+").replace("_", "/")
                    padding = 4 - len(payload_b64) % 4
                    if padding != 4:
                        payload_b64 += "=" * padding
                    decoded = base64.b64decode(payload_b64).decode("utf-8")
                    return json.loads(decoded)

                # Plain base64-encoded JSON
                padding = 4 - len(value) % 4
                if padding != 4:
                    value += "=" * padding
                decoded = base64.b64decode(value).decode("utf-8")
                return json.loads(decoded)
            except Exception as e:
                print(f"WARNING: Could not decode cxlPayload: {e}", file=sys.stderr)
                print(f"  Raw value: {c['value'][:100]}...", file=sys.stderr)
    return None


def extract_session_identifiers(page):
    """Extract identifiers needed for session/create from cookies.

    Returns dict with enterprisePartyIdentifier, onlineProfileIdentifier,
    productCode, or None if not found.

    Sources (in priority order):
    1. cxlPayload cookie (cnx-eci, cnx-pi, cnx-rpc)
    2. PC_1_0 cookie (ECI, pfid, RPC)
    """
    # Source 1: cxlPayload (already decoded by extract_cxl_payload)
    cxl = extract_cxl_payload(page)
    if cxl:
        eci = cxl.get("cnx-eci", "")
        opi = cxl.get("cnx-pi", "")
        rpc = cxl.get("cnx-rpc", "")
        if eci and opi and rpc:
            print(
                f"Session identifiers from cxlPayload: ECI={eci}, OPI={opi}, RPC={rpc}",
                file=sys.stderr,
            )
            return {
                "enterprisePartyIdentifier": eci,
                "onlineProfileIdentifier": int(opi) if opi.isdigit() else opi,
                "productCode": rpc,
            }

    # Source 2: PC_1_0 cookie (pipe-delimited key=value pairs)
    cookies = page.context.cookies()
    for c in cookies:
        if c.get("name") == "PC_1_0":
            try:
                import urllib.parse

                value = urllib.parse.unquote(c["value"])
                parts = dict(p.split("=", 1) for p in value.split("|") if "=" in p)
                eci = parts.get("ECI", "")
                opi = parts.get("pfid", "")
                rpc = parts.get("RPC", "").split(",")[0]  # First product code
                if eci and opi and rpc:
                    print(
                        f"Session identifiers from PC_1_0: ECI={eci}, OPI={opi}, RPC={rpc}",
                        file=sys.stderr,
                    )
                    return {
                        "enterprisePartyIdentifier": eci,
                        "onlineProfileIdentifier": int(opi) if opi.isdigit() else opi,
                        "productCode": rpc,
                    }
            except Exception as e:
                print(f"WARNING: Could not parse PC_1_0 cookie: {e}", file=sys.stderr)

    print(
        "WARNING: Could not extract session identifiers from cookies",
        file=sys.stderr,
    )
    return None


def create_travel_session(page):
    """Create a CXL travel session via the session/create API.

    This call is required before navigating to travelsecure.chase.com.
    Without it, the results page returns HTTP 400.

    Returns the session response dict, or None on failure.
    """
    ids = extract_session_identifiers(page)
    if not ids:
        print(
            "ERROR: Cannot create travel session without identifiers", file=sys.stderr
        )
        return None

    session_body = {
        "enterprisePartyIdentifier": ids["enterprisePartyIdentifier"],
        "digitalAccountIdentifier": int(_CARD_AI) if _CARD_AI else 0,
        "channel": "DESKTOP",
        "accountType": "CREDIT",
        "productCode": ids["productCode"],
        "onlineProfileIdentifier": ids["onlineProfileIdentifier"],
        "v2ReceptionDeskIndicator": True,
    }

    session_url = f"{SECURE_BASE}/session/create"
    print(f"Creating travel session...", file=sys.stderr)

    result = api_fetch(page, session_url, "POST", session_body)
    if result:
        redir_token = result.get("redirectionToken", "")
        api_token = result.get("apiToken", "")
        print(f"Travel session created", file=sys.stderr)

        # The apiToken is a JWT that becomes the new cxlPayload cookie.
        # Set it so travelsecure.chase.com can read the updated session.
        if api_token:
            import urllib.parse

            encoded_token = urllib.parse.quote(api_token, safe="")
            page.context.add_cookies(
                [
                    {
                        "name": "chaseTravel-cxlPayload",
                        "value": encoded_token,
                        "domain": ".chase.com",
                        "path": "/",
                    }
                ]
            )
    else:
        print(
            "WARNING: session/create failed. Results page may return 400.",
            file=sys.stderr,
        )

    return result


def get_ur_balance(page):
    """Extract UR points balance from the portal page."""
    try:
        text = page.inner_text("body")[:5000]
        # Look for points balance pattern
        matches = re.findall(r"([\d,]+)\s*(?:points|pts)", text, re.IGNORECASE)
        if matches:
            # Return the largest number (likely the balance, not a price)
            balances = [int(m.replace(",", "")) for m in matches]
            return max(balances)
    except Exception:
        pass
    return None


# ============================================================
# API calls via page.evaluate(fetch)
# ============================================================


def api_fetch(page, url, method="GET", body=None, extra_headers=None):
    """Make an API call from within the browser context.
    Returns parsed JSON or None on error."""
    headers = {
        "Content-Type": "application/json; charset=UTF-8",
        "x-jpmc-csrf-token": "NONE",
        "Accept": "application/json",
    }
    if extra_headers:
        headers.update(extra_headers)

    headers_json = json.dumps(headers)

    if body:
        js = f"""
        async () => {{
            const resp = await fetch("{url}", {{
                method: "{method}",
                headers: {headers_json},
                credentials: "include",
                body: JSON.stringify({json.dumps(body)})
            }});
            if (!resp.ok) return {{ __error: true, status: resp.status, text: await resp.text().catch(() => "") }};
            return await resp.json();
        }}
        """
    else:
        js = f"""
        async () => {{
            const resp = await fetch("{url}", {{
                method: "{method}",
                headers: {headers_json},
                credentials: "include"
            }});
            if (!resp.ok) return {{ __error: true, status: resp.status, text: await resp.text().catch(() => "") }};
            return await resp.json();
        }}
        """
    try:
        result = page.evaluate(js)
        if isinstance(result, dict) and result.get("__error"):
            print(f"API error: {result.get('status')} {url[:80]}", file=sys.stderr)
            print(f"  Response: {result.get('text', '')[:200]}", file=sys.stderr)
            return None
        return result
    except Exception as e:
        print(f"API call failed: {e}", file=sys.stderr)
        return None


def autosuggest_airport(page, query):
    """Look up an airport code via the Chase autosuggest API.
    Returns dict with code, locationId, name, etc."""
    url = f"{SECURE_BASE}/autosuggest/search"
    body = {
        "sq": {"st": query, "sf": ["departure-airport"]},
        "sel": False,
        "rec": None,
        "c": "flights",
    }
    result = api_fetch(page, url, "POST", body)
    if not result:
        return None

    # Parse response: {"s": [{...}], "wrn": []}
    # Keys are abbreviated: n=name, cd=code, lId=locationId, cn=cityName,
    # cc=countryCode, c=country, sc=stateCode, t=type, tzi.tz=timeZone
    suggestions = result.get("s", result.get("suggestions", []))
    if not isinstance(suggestions, list) or not suggestions:
        print(f"Autosuggest: no results for '{query}'", file=sys.stderr)
        return None

    # Convert abbreviated format to the full format the search API expects
    for s in suggestions:
        code = s.get("cd", s.get("code", ""))
        if code.upper() == query.upper():
            return _normalize_airport(s)

    # Return first result if no exact match
    return _normalize_airport(suggestions[0])


def _normalize_airport(s):
    """Convert autosuggest abbreviated format to full search payload format."""
    tz = ""
    if s.get("tzi"):
        tz = s["tzi"].get("tz", "")
    return {
        "code": s.get("cd", s.get("code", "")),
        "type": "Airport",
        "name": s.get("n", s.get("name", "")),
        "shortName": s.get("n", s.get("shortName", "")),
        "country": s.get("c", s.get("country", "")),
        "cityName": s.get("cn", s.get("cityName", "")),
        "stateCode": s.get("sc", ""),
        "countryCode": s.get("cc", s.get("countryCode", "")),
        "locationId": s.get("lId", s.get("locationId", "")),
        "timeZone": tz,
    }


def build_airport_payload(code, suggest_data=None):
    """Build airport payload for search request.
    Uses autosuggest data if available, otherwise builds minimal payload."""
    if suggest_data and suggest_data.get("locationId"):
        return suggest_data

    # Known airports (fallback if autosuggest fails)
    KNOWN = {
        "SFO": {
            "code": "SFO",
            "type": "Airport",
            "name": "SFO - San Francisco, CA",
            "shortName": "SFO - San Francisco",
            "country": "United States Of America",
            "cityName": "San Francisco",
            "stateCode": "CA",
            "countryCode": "US",
            "locationId": "640707",
            "timeZone": "Pacific Standard Time",
        },
        "CDG": {
            "code": "CDG",
            "type": "Airport",
            "name": "CDG - Paris (CDG-Roissy-Charles de Gaulle)",
            "shortName": "CDG - Paris (CDG-Roissy-Charles de Gaulle)",
            "country": "France",
            "cityName": "Paris (CDG-Roissy-Charles de Gaulle)",
            "countryCode": "FR",
            "locationId": "640054",
            "timeZone": "Romance Standard Time",
        },
        "SJC": {
            "code": "SJC",
            "type": "Airport",
            "name": "SJC - San Jose, CA",
            "shortName": "SJC - San Jose",
            "country": "United States Of America",
            "cityName": "San Jose",
            "stateCode": "CA",
            "countryCode": "US",
            "locationId": "640698",
            "timeZone": "Pacific Standard Time",
        },
        "NRT": {
            "code": "NRT",
            "type": "Airport",
            "name": "NRT - Tokyo (NRT-Narita)",
            "shortName": "NRT - Tokyo (NRT-Narita)",
            "country": "Japan",
            "cityName": "Tokyo (NRT-Narita)",
            "countryCode": "JP",
            "locationId": "640600",
            "timeZone": "Tokyo Standard Time",
        },
        "OSL": {
            "code": "OSL",
            "type": "Airport",
            "name": "OSL - Oslo",
            "shortName": "OSL - Oslo",
            "country": "Norway",
            "cityName": "Oslo",
            "countryCode": "NO",
            "locationId": "640554",
            "timeZone": "Romance Standard Time",
        },
        "AMS": {
            "code": "AMS",
            "type": "Airport",
            "name": "AMS - Amsterdam",
            "shortName": "AMS - Amsterdam",
            "country": "Netherlands",
            "cityName": "Amsterdam",
            "countryCode": "NL",
            "locationId": "640010",
            "timeZone": "Romance Standard Time",
        },
    }
    if code.upper() in KNOWN:
        return KNOWN[code.upper()]

    # Minimal fallback
    return {
        "code": code.upper(),
        "type": "Airport",
        "name": f"{code.upper()}",
        "shortName": code.upper(),
        "locationId": "",
    }


def search_flights_api(
    page, origin, dest, depart_date, return_date=None, cabin="Economy", passengers=1
):
    """Search flights via the Chase Travel API.

    Strategy:
    1. Look up airports via autosuggest API
    2. Create CXL travel session via session/create (required for travelsecure)
    3. Submit flight search via secure.chase.com API (gets ssid)
    4. Set up response interceptor BEFORE navigating to results page
    5. Navigate to travelsecure.chase.com/results (Angular app loads data via API)
    6. Capture the legwiseOfferResults/legwiseResults responses as they come through
    7. Parse structured JSON data from the intercepted responses

    Returns (ssid, results_data) or (None, None) on error.
    """

    # Step 1: Autosuggest to get locationIds
    print(f"Looking up airports: {origin}, {dest}...", file=sys.stderr)
    origin_data = autosuggest_airport(page, origin)
    dest_data = autosuggest_airport(page, dest)

    origin_payload = build_airport_payload(origin, origin_data)
    dest_payload = build_airport_payload(dest, dest_data)

    print(
        f"  Origin: {origin_payload.get('name', origin)} (locationId={origin_payload.get('locationId', '?')})",
        file=sys.stderr,
    )
    print(
        f"  Dest:   {dest_payload.get('name', dest)} (locationId={dest_payload.get('locationId', '?')})",
        file=sys.stderr,
    )

    # Step 2: Build search payload
    journeys = [
        {
            "departure": origin_payload,
            "arrival": dest_payload,
            "travelDate": {"date": depart_date, "timeWindow": 0},
        }
    ]

    journey_type = "oneway"
    if return_date:
        journey_type = "roundtrip"
        journeys.append(
            {
                "departure": dest_payload,
                "arrival": origin_payload,
                "travelDate": {"date": return_date, "timeWindow": 0},
            }
        )

    search_body = {
        "currency": "USD",
        "journeys": journeys,
        "passengers": [{"count": passengers, "type": "Adult"}],
        "filters": {
            "connection": {"nonStopOnly": False, "maximumConnectingPoints": 3},
            "airlines": {"allow": [], "onlineConnectionOnly": False},
            "unrestrictedFaresOnly": False,
            "refundableOnly": False,
            "brandedFares": True,
            "upsell": False,
            "timeFilters": [],
            "excludeBasicEconomy": False,
        },
        "journeyType": journey_type,
        "cabinType": cabin,
        "isMixAndMatch": True,
    }

    # Step 2.5: Create travel session (required before navigating to results)
    session_result = create_travel_session(page)

    # Step 3: Submit search
    search_url = f"{SECURE_BASE}/flight/search/{journey_type}"
    print(
        f"Searching {journey_type} flights: {origin} -> {dest}, {depart_date}"
        + (f" to {return_date}" if return_date else "")
        + f", {cabin}...",
        file=sys.stderr,
    )

    search_result = api_fetch(page, search_url, "POST", search_body)
    if not search_result:
        print("ERROR: Flight search API call failed", file=sys.stderr)
        return None, None

    # Extract session ID
    ssid = search_result.get("sessionId") or search_result.get("ssid")
    if not ssid:
        redirect_url = search_result.get("redirectUrl", search_result.get("url", ""))
        if "ssid=" in str(redirect_url):
            ssid = re.search(r"ssid=([^&]+)", str(redirect_url)).group(1)
    if not ssid:
        print(
            f"Search response (looking for ssid): {json.dumps(search_result)[:500]}",
            file=sys.stderr,
        )
        time.sleep(3)
        current_url = page.url
        if "ssid=" in current_url:
            ssid = re.search(r"ssid=([^&]+)", current_url).group(1)
    if not ssid:
        print(
            "ERROR: Could not extract session ID from search response", file=sys.stderr
        )
        return None, search_result

    print(f"Got session ID: {ssid}", file=sys.stderr)

    # Step 4: Set up response interceptor BEFORE navigating to results
    captured_responses = []

    def on_response(response):
        url = response.url.lower()
        # Capture the actual results API responses
        keywords = [
            "legwiseresults",
            "legwiseofferresults",
            "legwiseresult",
            "search/result",
            "facet",
        ]
        if any(k in url for k in keywords):
            try:
                body = response.text()
                if body and len(body) > 10:
                    data = json.loads(body)
                    captured_responses.append(
                        {
                            "url": response.url,
                            "status": response.status,
                            "data": data,
                        }
                    )
                    print(
                        f"  Captured: {response.url.split('/')[-1]} ({response.status}, {len(body)}b)",
                        file=sys.stderr,
                    )
            except Exception as e:
                print(f"  Response parse error: {e}", file=sys.stderr)

    page.on("response", on_response)

    # Also log ALL responses from travelsecure for debugging
    def on_any_response(response):
        url = response.url
        if "travelsecure" in url or "chase-travel" in url:
            status = response.status
            path = (
                url.split("?")[0].split("chase.com")[-1]
                if "chase.com" in url
                else url[:80]
            )
            if status >= 400 or "api/" in url.lower():
                print(f"  [{status}] {path}", file=sys.stderr)

    page.on("response", on_any_response)

    # Step 5: Navigate to results page
    # cnxtoken comes from session/create's redirectionToken (NOT the CSRF-Token in cxlPayload)
    cnx_token = ""
    if session_result and isinstance(session_result, dict):
        cnx_token = session_result.get("redirectionToken", "")
    if not cnx_token:
        # Fallback to CSRF-Token from cxlPayload (may not work)
        cxl = extract_cxl_payload(page)
        cnx_token = cxl.get("CSRF-Token", "") if cxl else ""
        if cnx_token:
            print(
                "  WARNING: Using CSRF-Token as cnxtoken (session/create had no redirectionToken)",
                file=sys.stderr,
            )

    results_url = f"https://travelsecure.chase.com/results/flights/outbound?ssid={ssid}&cnx-onprem=false"
    if cnx_token:
        results_url += f"&cnxtoken={cnx_token}"

    print(f"Navigating to results page...", file=sys.stderr)

    # Ensure cxlPayload cookie is on .chase.com domain for travelsecure
    all_cookies = page.context.cookies()
    cxl_cookie = None
    for c in all_cookies:
        if "cxlPayload" in c.get("name", ""):
            cxl_cookie = c
            break

    # If cxlPayload is on secure.chase.com, copy it to .chase.com for travelsecure
    if (
        cxl_cookie
        and "secure" in cxl_cookie.get("domain", "")
        and "travelsecure" not in cxl_cookie.get("domain", "")
    ):
        print("  Copying cxlPayload to .chase.com domain...", file=sys.stderr)
        page.context.add_cookies(
            [
                {
                    "name": cxl_cookie["name"],
                    "value": cxl_cookie["value"],
                    "domain": ".chase.com",
                    "path": "/",
                }
            ]
        )

    page.goto(results_url, timeout=60000)
    print(f"  Landed on: {page.url[:100]}", file=sys.stderr)

    # Step 6: Wait for results to load.
    # Chase returns TWO key responses:
    #   - legwiseOfferResults: cheapest offer per itinerary (smaller, comes first or second)
    #   - legwiseResults: full itineraries with all fare options (larger, the one we want)
    # Order varies between runs. Wait for BOTH, then use legwiseResults.
    print("Waiting for results to load...", file=sys.stderr)
    first_page = None

    for i in range(30):
        time.sleep(2)

        # Prefer legwiseResults (full data) over legwiseOfferResults (summary)
        best_response = None
        best_count = 0
        for resp in captured_responses:
            data = resp.get("data", {})
            itins = data.get("itineraries", data.get("results", []))
            if isinstance(itins, list) and len(itins) > 0:
                url = resp.get("url", "").lower()
                is_full = "legwiseresults" in url and "offerresults" not in url
                count = len(itins)
                # Prefer legwiseResults. If both are available, pick the one with more data.
                if is_full or count > best_count:
                    best_response = data
                    best_count = count
                    if is_full:
                        break  # legwiseResults is always preferred

        if best_response and best_count > 0:
            first_page = best_response
            print(
                f"Page 1: {best_count} results via API interception ({(i + 1) * 2}s)",
                file=sys.stderr,
            )
            break

        # Check DOM as progress indicator
        try:
            text = page.inner_text("body")[:1500].lower()
            if "sorry" in text and "unavailable" in text:
                print(f"Error on page: {text[:200]}", file=sys.stderr)
                break
            if i % 5 == 4:
                if "departure time" in text or "pts" in text:
                    print(
                        f"  Page has content but no API response yet... ({(i + 1) * 2}s)",
                        file=sys.stderr,
                    )
        except Exception:
            pass

        if i % 5 == 4:
            print(f"  Still loading... ({(i + 1) * 2}s)", file=sys.stderr)

    if not first_page:
        page.remove_listener("response", on_response)
        print(
            "API interception returned no results. Trying DOM scrape...",
            file=sys.stderr,
        )
        # Wait for Angular custom elements to render (they load AFTER initial page)
        # page.inner_text("body") always returns "Sorry, something went wrong" (140 chars)
        # but flight cards render on top via shadow DOM. Poll for them.
        # Cards are INSIDE shadow DOM so we must traverse shadow roots to find them.
        print("  Waiting for flight cards to render...", file=sys.stderr)
        FIND_CARDS_JS = """() => {
            function findAll(root, selector) {
                let results = [...root.querySelectorAll(selector)];
                root.querySelectorAll('*').forEach(el => {
                    if (el.shadowRoot) {
                        results = results.concat(findAll(el.shadowRoot, selector));
                    }
                });
                return results;
            }
            return findAll(document, 'orxe-flight-itinerary-card').length;
        }"""
        for attempt in range(30):  # up to 60 seconds
            card_count = page.evaluate(FIND_CARDS_JS)
            if card_count > 0:
                print(
                    f"  Found {card_count} flight cards after {(attempt + 1) * 2}s",
                    file=sys.stderr,
                )
                time.sleep(3)  # let remaining cards finish rendering
                break
            time.sleep(2)
        else:
            print("  No flight cards appeared after 60s", file=sys.stderr)

        # Try DOM element extraction (flight data is in custom elements, not inner_text)
        results = scrape_results_from_dom(page)
        if results:
            itins = results.get("itineraries", results.get("results", []))
            print(
                f"Got {len(itins) if isinstance(itins, list) else 0} results via DOM scrape",
                file=sys.stderr,
            )
        else:
            print("No results found.", file=sys.stderr)
            ss = (
                "/tmp/host/chase-results-debug.png"
                if os.path.isdir("/tmp/host")
                else "/tmp/chase-results-debug.png"
            )
            try:
                page.screenshot(path=ss, full_page=True)
                print(f"Debug screenshot: {ss}", file=sys.stderr)
            except Exception:
                pass
        return ssid, results

    # Step 7: Paginate to get all results.
    # Chase uses infinite scroll. Scrolling to bottom triggers the React app
    # to make another legwiseResults API call. Keep the response listener active
    # and scroll repeatedly until no more results come.
    all_itineraries = list(first_page.get("itineraries", first_page.get("results", [])))
    total_count = first_page.get(
        "resultCount", first_page.get("totalResults", len(all_itineraries))
    )
    page_num = 1

    print(
        f"Total available: {total_count}. Loading more via scroll...", file=sys.stderr
    )

    max_pages = 30  # Safety limit: 30 pages * 10 = 300 flights max
    while len(all_itineraries) < total_count and page_num < max_pages:
        page_num += 1
        prev_count = len(captured_responses)

        # Click "Show more" button. It's an <orxe-button> with shadow DOM:
        # Outer: <orxe-button orxe-id="see-more-button" class="see-more-button">
        # Shadow: <button id="button-id" aria-label="Show more">
        clicked = False
        try:
            clicked = page.evaluate("""
                (() => {
                    const btn = document.querySelector('orxe-button.see-more-button');
                    if (btn && btn.shadowRoot) {
                        const inner = btn.shadowRoot.querySelector('button#button-id');
                        if (inner) { inner.click(); return true; }
                    }
                    // Fallback: try orxe-id
                    const btn2 = document.querySelector('[orxe-id="see-more-button"]');
                    if (btn2 && btn2.shadowRoot) {
                        const inner = btn2.shadowRoot.querySelector('button');
                        if (inner) { inner.click(); return true; }
                    }
                    return false;
                })()
            """)
        except Exception:
            pass

        if not clicked:
            # Fallback: regular selectors
            for sel in [
                'button:has-text("Show more")',
                'button[aria-label="Show more"]',
                ".see-more-button",
            ]:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        el.click()
                        clicked = True
                        break
                except Exception:
                    continue

        if not clicked:
            print(
                f"  No 'Show more' button found after page {page_num - 1} ({len(all_itineraries)} total)",
                file=sys.stderr,
            )
            break

        if page_num <= 3 or page_num % 5 == 0:
            print(f"  Clicked 'Show more' (page {page_num})...", file=sys.stderr)

        # Wait for new API response
        got_new = False
        for _ in range(12):
            time.sleep(1)
            if len(captured_responses) > prev_count:
                got_new = True
                break

        if not got_new:
            print(
                f"  No new results after click ({len(all_itineraries)} total)",
                file=sys.stderr,
            )
            break

        if not got_new:
            # Try clicking explicit "Show more" / "Load more" buttons
            clicked = False
            for next_sel in [
                'button:has-text("Show more")',
                'button:has-text("Load more")',
                'button:has-text("View more")',
                'button:has-text("Show all")',
                '[class*="load-more"]',
                '[class*="show-more"]',
            ]:
                try:
                    btn = page.query_selector(next_sel)
                    if btn and btn.is_visible():
                        btn.click()
                        print(f"  Clicked: {next_sel}", file=sys.stderr)
                        clicked = True
                        time.sleep(5)
                        break
                except Exception:
                    continue

            if clicked:
                # Check for new response after button click
                for _ in range(5):
                    time.sleep(1)
                    if len(captured_responses) > prev_count:
                        got_new = True
                        break

            if not got_new:
                print(
                    f"  No more results after page {page_num - 1} ({len(all_itineraries)} total)",
                    file=sys.stderr,
                )
                break

        # Extract new itineraries from the latest response(s)
        for resp in captured_responses[prev_count:]:
            data = resp.get("data", {})
            new_itins = data.get("itineraries", data.get("results", []))
            if isinstance(new_itins, list) and new_itins:
                all_itineraries.extend(new_itins)
                print(
                    f"  Page {page_num}: +{len(new_itins)} results (total: {len(all_itineraries)})",
                    file=sys.stderr,
                )
    page_num = 1

    print(f"Total available: {total_count}. Fetching more pages...", file=sys.stderr)

    max_pages = 10  # Safety limit: 10 pages * 10 results = 100 flights max
    while len(all_itineraries) < total_count and page_num < max_pages:
        page_num += 1
        prev_count = len(captured_responses)

        # Scroll to bottom to trigger lazy loading / pagination
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)

        # Also look for and click explicit pagination buttons
        for next_sel in [
            'button:has-text("Show more")',
            'button:has-text("Load more")',
            'button:has-text("View more")',
            'button[aria-label*="next" i]',
            'button[aria-label*="Next" i]',
            'a:has-text("Next")',
            '[class*="pagination"] button:last-child',
            '[class*="load-more"]',
        ]:
            try:
                btn = page.query_selector(next_sel)
                if btn and btn.is_visible():
                    btn.click()
                    print(f"  Clicked pagination: {next_sel}", file=sys.stderr)
                    break
            except Exception:
                continue

        # Wait for new response
        got_new = False
        for _ in range(10):
            time.sleep(1)
            if len(captured_responses) > prev_count:
                got_new = True
                break

        if not got_new:
            print(f"  No more pages after page {page_num - 1}", file=sys.stderr)
            break

        # Extract new itineraries from the latest response
        for resp in captured_responses[prev_count:]:
            data = resp.get("data", {})
            new_itins = data.get("itineraries", data.get("results", []))
            if isinstance(new_itins, list) and new_itins:
                all_itineraries.extend(new_itins)
                print(
                    f"  Page {page_num}: +{len(new_itins)} results (total: {len(all_itineraries)})",
                    file=sys.stderr,
                )

    page.remove_listener("response", on_response)

    # Build merged results
    results = dict(first_page)
    results["itineraries"] = all_itineraries
    results["resultCount"] = len(all_itineraries)

    print(
        f"Got {len(all_itineraries)} results total across {page_num} page(s)",
        file=sys.stderr,
    )

    return ssid, results


def _parse_boost_cards(page):
    """Parse Points Boost offers from the card carousel section text.

    The boost section text (between "Points Boost" heading and "departure flights")
    contains structured card data. Each card has:
    - Date (e.g., "Aug 11")
    - Departure/arrival times (verbose: "Departure time is 12:55 pm")
    - Airline name
    - Route with verbose labels ("SFO‐CDG")
    - Duration and stops
    - Fare class
    - Cash price, boosted points, original (was) points
    """
    try:
        section = page.evaluate("""
            (() => {
                const body = document.body.innerText;
                const start = body.indexOf('Points Boost');
                if (start === -1) return '';
                const end = body.indexOf('departure flights', start);
                if (end === -1) return body.substring(start, start + 15000);
                return body.substring(start, end);
            })()
        """)

        if not section or "was" not in section:
            return None

        # Split into individual card blocks.
        # Each card ends with "was N pts" followed by "\xa0was N points".
        # Split on the date line that starts each new card: "Aug 11", "Sep 02", etc.
        blocks = re.split(
            r"\n(?=(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+\d{1,2}\n)",
            section,
        )

        flights = []
        known_carriers = [
            "Air Canada",
            "Air France",
            "United Airlines",
            "Delta Air Lines",
            "Lufthansa",
            "American Airlines",
            "British Airways",
            "KLM",
            "Swiss",
            "Condor",
            "WestJet",
            "Turkish Airlines",
            "Iberia",
            "TAP",
            "SAS",
            "Finnair",
            "Singapore Airlines",
            "Brussels Airlines",
        ]

        for block in blocks:
            if "was" not in block or "pts" not in block:
                continue

            lines = [l.strip() for l in block.split("\n") if l.strip()]
            f = {"has_boost": True}

            for line in lines:
                # Skip verbose location labels
                if line.startswith("Departure location is") or line.startswith(
                    "Destination location is"
                ):
                    continue

                # Departure time: "Departure time is 12:55 pm" or "12:55 pm ‐"
                dep = re.match(
                    r"^(?:Departure time is\s+)?(\d{1,2}:\d{2}\s*[ap]m)",
                    line,
                    re.IGNORECASE,
                )
                if dep and "depart_time" not in f:
                    f["depart_time"] = dep.group(1)
                    continue

                # Arrival time: "Destination time is 06:05 pm" or "06:05 pm"
                arr = re.match(
                    r"^(?:Destination time is\s+)?(\d{1,2}:\d{2}\s*[ap]m)$",
                    line,
                    re.IGNORECASE,
                )
                if arr and "depart_time" in f and "arrive_time" not in f:
                    f["arrive_time"] = arr.group(1)
                    continue

                # Carrier
                for carrier in known_carriers:
                    if line == carrier or carrier.lower() in line.lower():
                        f["carrier_name"] = carrier
                        break

                # Route: "SFO‐CDG" (with Unicode dash)
                route = re.search(r"([A-Z]{3})\s*[‐\-]\s*([A-Z]{3})", line)
                if route:
                    f["origin"] = route.group(1)
                    f["destination"] = route.group(2)

                # Duration: "20h 10m"
                dur = re.match(r"^(\d+h\s*\d+m)$", line)
                if dur:
                    f["duration"] = dur.group(1)

                # Stops
                if (
                    re.match(r"^\d+\s+stop", line, re.IGNORECASE)
                    or "nonstop" in line.lower()
                ):
                    f["stops_text"] = line

                # Cash price: "$5,045 or"
                cash = re.match(r"^\$([0-9,]+)", line)
                if cash and "cash_price" not in f:
                    f["cash_price"] = float(cash.group(1).replace(",", ""))

                # Boosted points: "252,206 pts"
                pts = re.match(r"^([0-9,]+)\s*pts", line)
                if pts and "points_price" not in f:
                    f["points_price"] = int(pts.group(1).replace(",", ""))

                # Original price: "was 504,413 pts"
                was = re.search(r"was\s+([0-9,]+)\s*pts", line)
                if was:
                    f["base_points"] = int(was.group(1).replace(",", ""))

                # Fare class
                fare_kw = [
                    "business",
                    "economy",
                    "first",
                    "premium",
                    "promotional",
                    "restricted",
                    "flexi",
                    "lowest",
                ]
                if (
                    any(kw in line.lower() for kw in fare_kw)
                    and len(line) < 50
                    and "fare family" not in line.lower()
                ):
                    f["brand"] = line

            # Calculate savings and CPP
            if f.get("points_price") and f.get("base_points"):
                f["boost_savings_pct"] = round(
                    (1 - f["points_price"] / f["base_points"]) * 100, 1
                )
            if f.get("cash_price") and f.get("points_price"):
                f["cpp"] = round(f["cash_price"] / f["points_price"] * 100, 2)

            if f.get("points_price") and f.get("carrier_name"):
                flights.append(f)

        if not flights:
            return None

        # Dedup by carrier + depart_time (carousel may repeat cards)
        seen = set()
        unique = []
        for f in flights:
            key = f"{f.get('carrier_name', '')}_{f.get('depart_time', '')}_{f.get('points_price', '')}"
            if key not in seen:
                seen.add(key)
                unique.append(f)
        flights = unique

        print(f"  Parsed {len(flights)} unique boost offers", file=sys.stderr)
        for f in flights:
            print(
                f"    {f.get('carrier_name', '?')}: ${f.get('cash_price', 0):,.0f} / "
                f"{f.get('points_price', 0):,} pts (was {f.get('base_points', 0):,}) "
                f"{f.get('boost_savings_pct', 0)}% off",
                file=sys.stderr,
            )

        # Convert to standard itinerary format
        itineraries = []
        for f in flights:
            itin = {
                "journeys": [
                    {
                        "segments": [
                            {
                                "flight": {
                                    "marketingCarrier": {
                                        "code": "",
                                        "name": f.get("carrier_name", ""),
                                    },
                                    "operatingCarrier": {
                                        "code": "",
                                        "name": f.get("carrier_name", ""),
                                    },
                                    "departure": {
                                        "airport": {"code": f.get("origin", "")},
                                        "dateTime": f.get("depart_time", ""),
                                    },
                                    "arrival": {
                                        "airport": {"code": f.get("destination", "")},
                                        "dateTime": f.get("arrive_time", ""),
                                    },
                                    "durationInMinutes": 0,
                                    "flightNumber": "",
                                }
                            }
                        ],
                    }
                ],
                "fareOptions": [
                    {
                        "displayPrice": {
                            "total": {
                                "payable": {
                                    "options": {
                                        "cashOnly": {"value": f.get("cash_price", 0)},
                                        "pointsOnly": {
                                            "value": f.get("points_price", 0),
                                            "baseValue": f.get("base_points", 0),
                                        },
                                        "cashAndPoints": {
                                            "cash": {"value": 0},
                                            "points": {"value": 0},
                                        },
                                    }
                                }
                            }
                        },
                        "fareFamily": {"name": f.get("brand", ""), "attributes": {}},
                        "hasDynamicBurnOffer": True,
                    }
                ],
            }
            itineraries.append(itin)

        return {
            "itineraries": itineraries,
            "resultCount": len(itineraries),
            "boost_source": "cards",
        }

    except Exception as e:
        print(f"  Boost card parse error: {e}", file=sys.stderr)
        return None

        # Debug: show first 3 card texts
        for i, card in enumerate(cards_data[:3]):
            print(f"  Card {i + 1}: {card.get('text', '')[:150]!r}", file=sys.stderr)

        # Parse card text into structured data
        # Format from screenshot: "Aug 11\n08:10 am - 10:20 am\nAir Canada\nSFO-CDG • 17h 10m • 1 stop...\nBusiness Lowest\n$5,416 or\n270,760 pts  was 541,519 pts"
        flights = []
        for card in cards_data:
            text = card.get("text", "")
            lines = [l.strip() for l in text.split("\n") if l.strip()]

            flight = {"has_boost": True}

            for line in lines:
                # Cash price
                cash_match = re.search(r"\$([0-9,]+)", line)
                if cash_match and "cash_price" not in flight:
                    flight["cash_price"] = float(cash_match.group(1).replace(",", ""))

                # Boosted points price (the discounted one)
                pts_match = re.match(r"^([0-9,]+)\s*pts", line)
                if pts_match:
                    flight["points_price"] = int(pts_match.group(1).replace(",", ""))

                # Original (was) price
                was_match = re.search(r"was\s+([0-9,]+)\s*pts", line)
                if was_match:
                    flight["base_points"] = int(was_match.group(1).replace(",", ""))

                # Time range
                time_match = re.match(
                    r"(\d{1,2}:\d{2}\s*[ap]m)\s*-\s*(\d{1,2}:\d{2}\s*[ap]m)", line
                )
                if time_match:
                    flight["depart_time"] = time_match.group(1)
                    flight["arrive_time"] = time_match.group(2)

                # Route and stops
                route_match = re.search(
                    r"([A-Z]{3})\s*-\s*([A-Z]{3})\s*•\s*(\d+h\s*\d+m)\s*•\s*(.*?)$",
                    line,
                )
                if route_match:
                    flight["origin"] = route_match.group(1)
                    flight["destination"] = route_match.group(2)
                    flight["duration"] = route_match.group(3)
                    flight["stops_text"] = route_match.group(4).strip()

                # Carrier
                known_carriers = [
                    "Air Canada",
                    "Air France",
                    "United",
                    "Delta",
                    "Lufthansa",
                    "American",
                    "British Airways",
                    "KLM",
                    "Swiss",
                    "Condor",
                    "WestJet",
                    "Iberia",
                    "TAP",
                    "SAS",
                    "Finnair",
                    "LOT",
                ]
                for carrier in known_carriers:
                    if carrier.lower() in line.lower():
                        flight["carrier_name"] = carrier
                        break

                # Fare class
                if (
                    "business" in line.lower()
                    or "economy" in line.lower()
                    or "first" in line.lower()
                ):
                    flight["brand"] = line

            # Calculate boost savings
            if flight.get("points_price") and flight.get("base_points"):
                savings_pct = round(
                    (1 - flight["points_price"] / flight["base_points"]) * 100, 1
                )
                flight["boost_savings_pct"] = savings_pct

            # Calculate CPP
            if flight.get("cash_price") and flight.get("points_price"):
                flight["cpp"] = round(
                    flight["cash_price"] / flight["points_price"] * 100, 2
                )

            if flight.get("points_price"):
                flights.append(flight)

        if not flights:
            return None

        # Convert to standard itinerary format
        itineraries = []
        for f in flights:
            itin = {
                "journeys": [
                    {
                        "segments": [
                            {
                                "flight": {
                                    "marketingCarrier": {
                                        "code": "",
                                        "name": f.get("carrier_name", ""),
                                    },
                                    "operatingCarrier": {
                                        "code": "",
                                        "name": f.get("carrier_name", ""),
                                    },
                                    "departure": {
                                        "airport": {"code": f.get("origin", "")},
                                        "dateTime": f.get("depart_time", ""),
                                    },
                                    "arrival": {
                                        "airport": {"code": f.get("destination", "")},
                                        "dateTime": f.get("arrive_time", ""),
                                    },
                                    "durationInMinutes": 0,
                                    "flightNumber": "",
                                }
                            }
                        ],
                    }
                ],
                "fareOptions": [
                    {
                        "displayPrice": {
                            "total": {
                                "payable": {
                                    "options": {
                                        "cashOnly": {"value": f.get("cash_price", 0)},
                                        "pointsOnly": {
                                            "value": f.get("points_price", 0),
                                            "baseValue": f.get("base_points", 0),
                                        },
                                        "cashAndPoints": {
                                            "cash": {"value": 0},
                                            "points": {"value": 0},
                                        },
                                    }
                                }
                            }
                        },
                        "fareFamily": {
                            "name": f.get("brand", ""),
                            "attributes": {},
                        },
                        "hasDynamicBurnOffer": True,
                    }
                ],
            }
            itineraries.append(itin)

        return {
            "itineraries": itineraries,
            "resultCount": len(itineraries),
            "boost_source": "cards",
        }

    except Exception as e:
        print(f"  Boost card parse error: {e}", file=sys.stderr)
        return None


def search_with_boost(page, ssid):
    """Toggle Points Boost on the results page and capture boosted pricing.

    Points Boost is a Chase-specific feature that gives a better dynamic CPP
    on select flights (typically ~1.5-2.0c on CSR). It appears as a radio button
    or toggle on the results page. Pull the actual quote from the portal.

    Returns boosted results data or None if boost isn't available.
    """
    print("Checking for Points Boost...", file=sys.stderr)

    # Look for Points Boost toggle/radio
    # The Points Boost UI has two parts:
    # 1. A card carousel at the top showing boosted flight offers with discounted points
    # 2. A toggle switch labeled "Points Boost only" in the filter bar
    # The toggle is a styled switch (not a standard checkbox/radio).

    # Extract the boost section text. The section sits between the "Points Boost"
    # heading and the "N departure flights" results header. Contains a carousel
    # of ~3-10 boost offers showing airline, route, times, cash, boosted pts, original pts.
    boost_cards = []
    boost_section_text = ""

    # First, scroll the boost carousel to the end so ALL cards are in the DOM.
    # The carousel only shows ~3 cards at a time. Clicking the right arrow
    # loads more into the DOM.
    try:
        for _ in range(10):  # Click right arrow up to 10 times
            arrow = page.query_selector(
                'button[aria-label*="next" i], button[aria-label*="right" i], '
                '[class*="carousel"] button:last-child, [class*="arrow-right"], '
                '[class*="next-arrow"]'
            )
            # Only click arrows that are INSIDE the boost section (not results pagination)
            if arrow and arrow.is_visible():
                # Check it's near the top of the page (boost section), not in results
                box = arrow.bounding_box()
                if box and box.get("y", 999) < 600:  # Boost carousel is near the top
                    arrow.click()
                    time.sleep(0.5)
                else:
                    break
            else:
                break
    except Exception:
        pass

    try:
        boost_section_text = page.evaluate("""
            (() => {
                const body = document.body.innerText;
                const start = body.indexOf('Points Boost');
                if (start === -1) return '';
                const end = body.indexOf('departure flights', start);
                if (end === -1) return body.substring(start, start + 10000);
                return body.substring(start, end);
            })()
        """)
        if (
            boost_section_text
            and "was" in boost_section_text
            and "pts" in boost_section_text
        ):
            # Split into individual cards by the "was X pts" pattern (end of each card)
            import re as _re

            # Each card ends with "was N pts" (and possibly "was N points" after)
            parts = _re.split(r"(was\s+[\d,]+\s*pts)", boost_section_text)
            # Reassemble: each card = text chunk + its "was X pts" delimiter
            cards_raw = []
            for i in range(0, len(parts) - 1, 2):
                card_text = parts[i] + parts[i + 1]
                if len(card_text) > 20:
                    cards_raw.append(card_text.strip())
            # Dedup by first 80 chars
            seen = set()
            for c in cards_raw:
                key = c[:80]
                if key not in seen:
                    seen.add(key)
                    boost_cards.append({"text": c})
            if boost_cards:
                print(
                    f"  Found {len(boost_cards)} Points Boost offers", file=sys.stderr
                )
    except Exception:
        pass

    # The toggle is a custom web component <orxe-toggle> with shadow DOM.
    # Outer: <orxe-toggle class="points-offer" orxe-id="resultHeaderContainer--radarFlight-toggle">
    # Shadow: <button id="toggle-button" role="switch" aria-label="Points Boost only" aria-checked="false">
    # Must pierce shadow DOM to click the actual button.

    boost_el = None

    # Method 1: JS shadow DOM piercing (most reliable)
    try:
        found = page.evaluate("""
            (() => {
                const toggle = document.querySelector('orxe-toggle.points-offer');
                if (toggle && toggle.shadowRoot) {
                    const btn = toggle.shadowRoot.querySelector('button#toggle-button[role="switch"]');
                    if (btn) return {found: true, checked: btn.getAttribute('aria-checked')};
                }
                return {found: false};
            })()
        """)
        if found and found.get("found"):
            boost_el = "shadow"  # marker that we'll click via JS
            print(
                f"  Found boost toggle in shadow DOM (currently: {found.get('checked', '?')})",
                file=sys.stderr,
            )
    except Exception:
        pass

    # Method 2: Fallback CSS selectors (in case shadow DOM structure changes)
    if not boost_el:
        for sel in [
            "orxe-toggle.points-offer",
            '[orxe-id*="radarFlight-toggle"]',
            'button[role="switch"][aria-label*="Boost" i]',
            'button[role="switch"][aria-label*="boost" i]',
        ]:
            try:
                el = page.query_selector(sel)
                if el and el.is_visible():
                    boost_el = el
                    print(f"  Found boost element: {sel}", file=sys.stderr)
                    break
            except Exception:
                continue

    if not boost_el:
        # Check page text for boost availability
        try:
            text = page.inner_text("body")[:8000].lower()
            if "points boost" not in text and "boost" not in text:
                print("  No Points Boost available on this route.", file=sys.stderr)
                return None
        except Exception:
            return None

        # Boost IS on the page. If we have cards, parse them directly.
        if boost_cards:
            print(
                "  Toggle not found, but extracting boost data from cards...",
                file=sys.stderr,
            )
            return _parse_boost_cards(page)

        # Last resort: screenshot for debugging
        ss = (
            "/tmp/host/chase-boost-debug.png"
            if os.path.isdir("/tmp/host")
            else "/tmp/chase-boost-debug.png"
        )
        try:
            page.screenshot(path=ss)
            print(
                f"  Boost on page but can't interact. Screenshot: {ss}", file=sys.stderr
            )
        except Exception:
            pass
        return None

    # If we have boost cards already, parse them as fallback data
    card_results = None
    if boost_cards:
        print("  Extracting boost data from visible cards...", file=sys.stderr)
        card_results = _parse_boost_cards(page)
        # If we can't click the toggle, cards are all we have
        if not boost_el:
            return card_results

    # Set up response interceptor for boosted results
    boost_responses = []

    def on_boost_response(response):
        url = response.url.lower()
        if "legwiseresults" in url or "legwiseofferresults" in url:
            try:
                body = response.text()
                if body and len(body) > 10:
                    data = json.loads(body)
                    boost_responses.append(data)
                    print(f"  Captured boost results ({len(body)}b)", file=sys.stderr)
            except Exception:
                pass

    page.on("response", on_boost_response)

    # Click the boost toggle
    if boost_el == "shadow":
        # Shadow DOM: click via JS
        try:
            page.evaluate("""
                (() => {
                    const toggle = document.querySelector('orxe-toggle.points-offer');
                    if (toggle && toggle.shadowRoot) {
                        const btn = toggle.shadowRoot.querySelector('button#toggle-button');
                        if (btn) btn.click();
                    }
                })()
            """)
            print("  Clicked Points Boost toggle (shadow DOM)", file=sys.stderr)
        except Exception as e:
            print(f"  Failed to click boost toggle: {e}", file=sys.stderr)
            page.remove_listener("response", on_boost_response)
            return card_results if boost_cards else None
    else:
        try:
            boost_el.click()
            print("  Clicked Points Boost toggle", file=sys.stderr)
        except Exception:
            try:
                page.evaluate("arguments[0].click()", boost_el)
                print("  Clicked Points Boost toggle (JS)", file=sys.stderr)
            except Exception as e:
                print(f"  Failed to click boost: {e}", file=sys.stderr)
                page.remove_listener("response", on_boost_response)
                return card_results if boost_cards else None

    # Wait for boosted results
    time.sleep(8)
    for i in range(10):
        if boost_responses:
            break
        time.sleep(2)

    page.remove_listener("response", on_boost_response)

    if boost_responses:
        # API returned new results after toggle
        result = boost_responses[-1]
        itins = result.get("itineraries", result.get("results", []))
        count = len(itins) if isinstance(itins, list) else 0
        print(f"  Got {count} boosted results via API", file=sys.stderr)
        return result

    # Toggle was client-side filtering (no new API call).
    # The card carousel data is more reliable than DOM scraping the filtered list.
    # Use cards if we have them.
    if card_results and card_results.get("resultCount", 0) > 0:
        count = card_results.get("resultCount", 0)
        print(f"  Using card carousel data: {count} boost offers", file=sys.stderr)
        return card_results

    # Fall back to DOM scraping the filtered page
    print("  No card data. Scraping filtered page...", file=sys.stderr)
    time.sleep(5)
    filtered = scrape_results_from_page(page)
    if filtered:
        itins = filtered.get("itineraries", [])
        if itins:
            print(
                f"  Got {len(itins)} boost-filtered results from DOM", file=sys.stderr
            )
            return filtered

    print("  Boost toggle clicked but no results captured", file=sys.stderr)
    return None


def search_hotels_api(
    page, destination, checkin, checkout, guests=2, rooms=1, max_hotels=100
):
    """Search hotels via the Chase Travel portal.

    Strategy (same as flights):
    1. Autosuggest destination via secure.chase.com CTE API
    2. Create hotel search session via secure.chase.com hotel/search
    3. Set up response interception
    4. Navigate to travelsecure.chase.com/results/hotels?h.s.sid={sid}
    5. Capture POST /api/hotel/v1.0/search/results responses
    6. Extract hotel data from "h" array in response

    API discovered via network recording Apr 6 2026.
    """
    from datetime import datetime

    # Step 1: Autosuggest the destination
    # Same CTE endpoint as flights, but with c="hotels"
    print(f"Looking up hotel destination: {destination}...", file=sys.stderr)

    dest_data = None
    for sf_val in [None, ["hotel-destination"], ["city"]]:
        sq = {"st": destination}
        if sf_val:
            sq["sf"] = sf_val
        suggest = api_fetch(
            page,
            f"{SECURE_BASE}/autosuggest/search",
            "POST",
            {"sq": sq, "sel": False, "rec": None, "c": "hotels"},
        )
        if suggest and not suggest.get("__error"):
            items = suggest.get("s", [])
            if isinstance(items, list) and items:
                dest_data = items[0]
                name = dest_data.get("n", dest_data.get("cn", destination))
                print(f"  Found: {name}", file=sys.stderr)
                break

    if not dest_data:
        print(
            f"WARNING: Could not resolve hotel destination '{destination}'",
            file=sys.stderr,
        )
        return None

    # Step 2: Create hotel search session
    # Payload format from network capture: dates as MM/DD/YYYY,
    # destination data from autosuggest response
    print(
        f"Searching hotels in {destination}: {checkin} to {checkout}, {guests} guests...",
        file=sys.stderr,
    )

    # Parse dates (input: YYYY-MM-DD)
    ci = datetime.strptime(checkin, "%Y-%m-%d")
    co = datetime.strptime(checkout, "%Y-%m-%d")

    # Build destination object from autosuggest data
    dstn = {
        "adr": {
            "cc": dest_data.get("cc", ""),
            "n": dest_data.get("n", destination),
            "cn": dest_data.get("cn", destination),
        },
        "b": {
            "lat": dest_data.get("lat", 0),
            "lng": dest_data.get("lng", 0),
            "t": dest_data.get("t", "City"),
        },
        "loc": {
            "id": dest_data.get("lId", ""),
            "t": dest_data.get("t", "City"),
        },
        "c": dest_data.get("cd", ""),
    }
    # Add timezone if present
    tzi = dest_data.get("tzi")
    if tzi:
        dstn["tzi"] = tzi

    search_body = {
        "cur": "USD",
        "sq": {
            "sp": {
                "s": ci.strftime("%m/%d/%Y"),
                "e": co.strftime("%m/%d/%Y"),
            },
            "dstn": dstn,
            "g": {"adt": guests, "ca": []},
            "ftr": {"n": [None], "p": None, "rt": []},
            "st": "Hotels",
        },
    }

    # Create travel session (required before navigating to results)
    session_result = create_travel_session(page)

    result = api_fetch(page, f"{SECURE_BASE}/hotel/search", "POST", search_body)

    ssid = None
    if result and not result.get("__error"):
        # The API may return the sid directly or in a redirect URL
        ssid = result.get("sid") or result.get("sessionId") or result.get("searchId")
        if not ssid:
            # Check response text for session ID pattern
            result_str = json.dumps(result)
            m = re.search(r"([0-9a-f-]{36}-HLNXT[^\"&\s]+)", result_str)
            if m:
                ssid = m.group(1)

    if not ssid:
        # Try intercepting the redirect from the portal
        # Navigate to Stays tab and capture the hotel search POST
        print("No session ID from API. Trying portal navigation...", file=sys.stderr)

        captured_hotel_posts = []

        def on_hotel_req(request):
            if "hotel" in request.url.lower() and request.method == "POST":
                if (
                    "search" in request.url.lower()
                    and "results" not in request.url.lower()
                ):
                    captured_hotel_posts.append(request.url)

        def on_hotel_nav(response):
            url = response.url
            if "h.s.sid=" in url:
                m = re.search(r"h\.s\.sid=([^&]+)", url)
                if m:
                    import urllib.parse

                    captured_hotel_posts.append(
                        "SID:" + urllib.parse.unquote(m.group(1))
                    )

        page.on("request", on_hotel_req)
        page.on("response", on_hotel_nav)

        page.goto(_portal_url(), timeout=30000)
        page.wait_for_timeout(10000)

        page.remove_listener("request", on_hotel_req)
        page.remove_listener("response", on_hotel_nav)

        for item in captured_hotel_posts:
            if item.startswith("SID:"):
                ssid = item[4:]
                print(
                    f"  Got hotel session ID from navigation: {ssid}", file=sys.stderr
                )
                break

    if ssid:
        print(f"  Hotel session ID: {ssid}", file=sys.stderr)
    else:
        print("ERROR: Could not get hotel search session ID", file=sys.stderr)
        return None

    # Step 3: Set up response interception (same pattern as flights)
    # Chase makes TWO hotel results API calls:
    # 1. Unfiltered (all hotels, first page of ~10)
    # 2. Filtered with bf.f3=true (Edit/Boost hotels only, typically 10-30)
    # We capture both and paginate whichever the caller needs.
    captured_hotel_responses = []

    def on_hotel_response(response):
        url_lower = response.url.lower()
        if "hotel" in url_lower and "search/results" in url_lower:
            try:
                body_text = response.text()
                if body_text and len(body_text) > 500:
                    data = json.loads(body_text)
                    if "h" in data and isinstance(data["h"], list):
                        pg = data.get("pg", {})
                        total = pg.get("tr", len(data["h"]))
                        captured_hotel_responses.append(data)
                        print(
                            f"  Captured: {len(data['h'])} hotels (total={total}, {len(body_text)}b)",
                            file=sys.stderr,
                        )
            except (json.JSONDecodeError, Exception):
                pass

    page.on("response", on_hotel_response)

    # Step 4: Navigate to hotel results page
    import urllib.parse

    encoded_sid = urllib.parse.quote(ssid, safe="")
    results_url = f"https://travelsecure.chase.com/results/hotels?h.s.sid={encoded_sid}&cnx-onprem=false"

    # Add cnxtoken from session/create (required, same as flights)
    cnx_token = ""
    if session_result and isinstance(session_result, dict):
        cnx_token = session_result.get("redirectionToken", "")
    if not cnx_token:
        cxl = extract_cxl_payload(page)
        cnx_token = cxl.get("CSRF-Token", "") if cxl else ""
    if cnx_token:
        results_url += f"&cnxtoken={cnx_token}"

    print(f"Navigating to hotel results...", file=sys.stderr)
    page.goto(results_url, timeout=60000)

    # Step 5: Wait for initial hotel results (Chase fires 2 API calls)
    print("Waiting for hotel results...", file=sys.stderr)

    # Wait for at least 2 responses (unfiltered + Edit-filtered)
    for i in range(30):
        page.wait_for_timeout(2000)
        if len(captured_hotel_responses) >= 2:
            break
        if captured_hotel_responses and i >= 5:
            break  # At least one response after 10s
        if i % 5 == 4:
            print(f"  Still loading... ({(i + 1) * 2}s)", file=sys.stderr)

    if not captured_hotel_responses:
        page.remove_listener("response", on_hotel_response)
        print("No hotel results captured.", file=sys.stderr)
        ss = (
            "/tmp/host/chase-hotels-debug.png"
            if os.path.isdir("/tmp/host")
            else "/tmp/chase-hotels-debug.png"
        )
        try:
            page.screenshot(path=ss, full_page=True)
            print(f"Debug screenshot: {ss}", file=sys.stderr)
        except Exception:
            pass
        return None

    # Separate unfiltered vs filtered responses by pg.tr (total results)
    # Unfiltered has the higher total (e.g., 1165), filtered has lower (e.g., 16)
    sorted_responses = sorted(
        captured_hotel_responses,
        key=lambda r: r.get("pg", {}).get("tr", 0),
        reverse=True,
    )
    unfiltered = sorted_responses[0]
    unfiltered_total = unfiltered.get("pg", {}).get("tr", len(unfiltered.get("h", [])))

    # If we have a filtered (Edit) response, it's the one with fewer total results
    edit_response = None
    if len(sorted_responses) > 1:
        candidate = sorted_responses[-1]
        candidate_total = candidate.get("pg", {}).get("tr", 0)
        if candidate_total < unfiltered_total:
            edit_response = candidate
            print(
                f"Got {len(candidate.get('h', []))} Edit/Boost hotels, {unfiltered_total} total available",
                file=sys.stderr,
            )

    # Merge all initial hotels (deduplicate by id)
    all_hotels = {}
    for resp_data in captured_hotel_responses:
        for h in resp_data.get("h", []):
            hid = h.get("id", "")
            if hid and hid not in all_hotels:
                all_hotels[hid] = h

    initial_count = len(all_hotels)
    print(f"Got {initial_count} unique hotels (initial)", file=sys.stderr)

    # Get total from page text as fallback
    total_count = unfiltered_total
    try:
        page_text = page.evaluate("document.body.innerText")
        m = re.search(r"Showing\s+\d+\s+of\s+(\d+)\s+results", page_text)
        if m:
            page_total = int(m.group(1))
            if page_total > total_count:
                total_count = page_total
    except Exception:
        pass

    # Step 6: Paginate via "Show more" button (same shadow DOM as flights)
    target = total_count
    if max_hotels and max_hotels > 0:
        target = min(total_count, max_hotels)

    if target > initial_count:
        print(
            f"Total available: {total_count}. Fetching up to {target}...",
            file=sys.stderr,
        )

    page_num = 1
    max_pages = 120  # Safety limit
    while len(all_hotels) < target and page_num < max_pages:
        page_num += 1
        prev_count = len(captured_hotel_responses)

        # Click shadow DOM "Show more" button
        clicked = False
        try:
            clicked = page.evaluate("""
                (() => {
                    const btn = document.querySelector('orxe-button.see-more-button');
                    if (btn && btn.shadowRoot) {
                        const inner = btn.shadowRoot.querySelector('button#button-id');
                        if (inner) { inner.click(); return true; }
                    }
                    const btn2 = document.querySelector('[orxe-id="see-more-button"]');
                    if (btn2 && btn2.shadowRoot) {
                        const inner = btn2.shadowRoot.querySelector('button');
                        if (inner) { inner.click(); return true; }
                    }
                    return false;
                })()
            """)
        except Exception:
            pass

        if not clicked:
            for sel in [
                'button:has-text("Show more")',
                'button[aria-label="Show more"]',
                ".see-more-button",
            ]:
                try:
                    el = page.query_selector(sel)
                    if el and el.is_visible():
                        el.click()
                        clicked = True
                        break
                except Exception:
                    continue

        if not clicked:
            print(
                f"  No 'Show more' button ({len(all_hotels)} hotels total)",
                file=sys.stderr,
            )
            break

        if page_num <= 3 or page_num % 10 == 0:
            print(f"  Clicked 'Show more' (page {page_num})...", file=sys.stderr)

        # Wait for new API response
        got_new = False
        for _ in range(12):
            page.wait_for_timeout(1000)
            if len(captured_hotel_responses) > prev_count:
                got_new = True
                break

        if not got_new:
            print(
                f"  No new results after click ({len(all_hotels)} hotels total)",
                file=sys.stderr,
            )
            break

        # Merge new hotels
        for resp_data in captured_hotel_responses[prev_count:]:
            for h in resp_data.get("h", []):
                hid = h.get("id", "")
                if hid and hid not in all_hotels:
                    all_hotels[hid] = h

        if page_num <= 3 or page_num % 10 == 0:
            print(f"  {len(all_hotels)} hotels so far...", file=sys.stderr)

    page.remove_listener("response", on_hotel_response)
    print(f"Final: {len(all_hotels)} hotels", file=sys.stderr)

    # Return merged result with all hotels
    result = unfiltered.copy()
    result["h"] = list(all_hotels.values())
    result["pg"]["tr"] = total_count
    return result


# ============================================================
# Result parsing and display
# ============================================================


def scrape_results_from_dom(page):
    """Extract flight results from DOM elements (custom Angular components).

    The travelsecure.chase.com results page uses custom elements with shadow DOM.
    inner_text("body") can't reach the flight data, but querySelectorAll can find
    the light DOM elements that contain airline, time, price, and points data.
    """
    results = page.evaluate("""() => {
        // Traverse shadow DOM to find elements
        function deepQueryAll(root, selector) {
            let results = [...root.querySelectorAll(selector)];
            root.querySelectorAll('*').forEach(el => {
                if (el.shadowRoot) {
                    results = results.concat(deepQueryAll(el.shadowRoot, selector));
                }
            });
            return results;
        }
        function deepQuery(root, selector) {
            let result = root.querySelector(selector);
            if (result) return result;
            const allEls = root.querySelectorAll('*');
            for (const el of allEls) {
                if (el.shadowRoot) {
                    result = deepQuery(el.shadowRoot, selector);
                    if (result) return result;
                }
            }
            return null;
        }

        const flights = [];
        const cards = deepQueryAll(document, 'orxe-flight-itinerary-card');
        if (cards.length === 0) return null;

        // Helper: query within a node, piercing shadow DOM
        function dq(root, sel) {
            let r = root.querySelector(sel);
            if (r) return r;
            for (const el of root.querySelectorAll('*')) {
                if (el.shadowRoot) {
                    r = dq(el.shadowRoot, sel);
                    if (r) return r;
                }
            }
            return null;
        }
        function dqAll(root, sel) {
            let results = [...root.querySelectorAll(sel)];
            for (const el of root.querySelectorAll('*')) {
                if (el.shadowRoot) {
                    results = results.concat(dqAll(el.shadowRoot, sel));
                }
            }
            return results;
        }

        cards.forEach(card => {
            const flight = {};

            // Airline name
            const airlineEl = dq(card, '[orxe-id="journeySummary--airlineName-span"]');
            flight.airline = airlineEl ? airlineEl.textContent.trim() : '';

            // Times (first two .time-suffix spans in journey summary)
            const timeEls = dqAll(card, '.time-suffix');
            const times = timeEls.map(t => t.textContent.trim().replace(/[‐\\-]\\s*$/, '').trim());
            flight.depart_time = times[0] || '';
            flight.arrive_time = times[1] || '';

            // Duration
            const durEl = dq(card, '.journey-duration');
            flight.duration = durEl ? durEl.textContent.trim() : '';

            // Stops
            const stopEl = dq(card, '[orxe-id="journeySummary--stop-info"]');
            flight.stops = stopEl ? stopEl.textContent.trim() : '';

            // Route (departure and destination codes)
            const depCode = dq(card, '[orxe-id="journeySummary--departureCode-span"]');
            const arrCode = dq(card, '[orxe-id="journeySummary--destinationCode-span"]');
            if (!depCode && !arrCode) {
                const routeSpans = dqAll(card, '.journey-info span[aria-hidden="true"]');
                const codes = routeSpans.map(s => s.textContent.trim()).filter(t => /^[A-Z]{3}/.test(t));
                flight.origin = codes[0] ? codes[0].replace(/[^A-Z]/g, '') : '';
                flight.destination = codes[1] ? codes[1].replace(/[^A-Z]/g, '') : '';
            } else {
                flight.origin = depCode ? depCode.textContent.trim().replace(/[^A-Z]/g, '') : '';
                flight.destination = arrCode ? arrCode.textContent.trim().replace(/[^A-Z]/g, '') : '';
            }

            // Code share
            const codeShare = dq(card, '[orxe-id="journeySummary--codeShareText-div"]');
            flight.codeshare = codeShare ? codeShare.textContent.trim() : '';

            // Points Boost indicator
            flight.has_boost = !!dq(card, '.points-offer-text-container');

            // Fare options (each carousel item is a fare class)
            flight.fares = [];
            const fareItems = dqAll(card, 'orxe-desktop-carousel-item[orxe-id="brand-fare-details"]');
            fareItems.forEach(item => {
                const fare = {};
                const nameEl = dq(item, '.fare-name');
                fare.name = nameEl ? nameEl.textContent.trim() : '';

                const priceEl = dq(item, '[orxe-id="fareOptionTile--fare-span"]');
                fare.cash = priceEl ? priceEl.textContent.trim() : '';

                // Points: check both div and span variants
                const ptDiv = dq(item, '[orxe-id="fareOptionTile--point-div"]');
                const ptSpan = dq(item, '[orxe-id="fareOptionTile--point-span"]');
                const ptEl = ptSpan || ptDiv;
                fare.points = ptEl ? ptEl.textContent.trim().replace(/\\s*points?$/i, '').trim() : '';

                // Boost: "was X pts" original price
                const baseEl = dq(item, '[orxe-id="fareOptionTile--basePoint-span"]') || dq(item, '.brand-fare-base-points');
                fare.was_points = baseEl ? baseEl.textContent.trim() : '';

                fare.is_boost = !!(ptSpan && dq(item, '.points-offer-container'));

                flight.fares.push(fare);
            });

            flights.push(flight);
        });

        // Result count (also in shadow DOM)
        const countEl = deepQuery(document, '[orxe-id="resultHeaderContainer--flightResultCount"]');
        const count = countEl ? countEl.textContent.trim() : '';

        // Points Boost shelf
        const boostShelf = [];
        const shelfItems = deepQueryAll(document, 'app-shelf-card');
        shelfItems.forEach(item => {
            const boost = {};
            const dateEl = dq(item, '.journey-date');
            boost.date = dateEl ? dateEl.textContent.trim() : '';
            const airEl = dq(item, '.journey-header');
            boost.airline = airEl ? airEl.textContent.trim() : '';
            const routeEl = dq(item, '.flight-info');
            boost.route = routeEl ? routeEl.textContent.trim() : '';
            const priceEl = dq(item, '.brand-fare-price');
            boost.cash = priceEl ? priceEl.textContent.trim() : '';
            const ptsEl = dq(item, '.brand-fare-points-offer');
            boost.points = ptsEl ? ptsEl.textContent.trim() : '';
            const wasEl = dq(item, '.brand-fare-base-points');
            boost.was_points = wasEl ? wasEl.textContent.trim() : '';
            const fareEl = dq(item, '.brand-name');
            boost.fare = fareEl ? fareEl.textContent.trim() : '';
            boostShelf.push(boost);
        });

        return {
            count: count,
            flights: flights,
            boost_shelf: boostShelf
        };
    }""")

    if not results or not results.get("flights"):
        print("DOM element extraction found no flights", file=sys.stderr)
        # Debug: check what elements exist (piercing shadow DOM)
        debug = page.evaluate("""() => {
            function countDeep(root, sel) {
                let n = root.querySelectorAll(sel).length;
                root.querySelectorAll('*').forEach(el => {
                    if (el.shadowRoot) n += countDeep(el.shadowRoot, sel);
                });
                return n;
            }
            return {
                cards: countDeep(document, 'orxe-flight-itinerary-card'),
                summaries: countDeep(document, 'orxe-flight-journey-summary'),
                fares: countDeep(document, '[orxe-id="fareOptionTile--fare-span"]'),
                any_orxe: countDeep(document, '[orxe-id]'),
                shadow_roots: document.querySelectorAll('*').length,
                body_len: document.body.innerText.length,
                body_preview: document.body.innerText.substring(0, 200)
            };
        }""")
        print(f"  Debug: {debug}", file=sys.stderr)
        return None

    print(
        f"  DOM extraction: {results['count']}, {len(results['flights'])} flights, {len(results.get('boost_shelf', []))} boost offers",
        file=sys.stderr,
    )

    # Convert to the format expected by the rest of the code
    return {
        "itineraries": results["flights"],
        "boost_shelf": results.get("boost_shelf", []),
        "count": results["count"],
    }


def scrape_results_from_page(page):
    """Scrape flight results from the travelsecure page DOM.

    Handles two text formats:
    1. Standard results: clean time patterns like "12:55 pm"
    2. Boost-filtered results: verbose labels like "Departure time is 12:55 PM"

    Both formats have: times, carrier, route (SFO‐CDG), duration, stops,
    fare class, cash price, points price, and optionally "was X pts".
    """
    try:
        text = page.inner_text("body")
        if not text:
            print("Page has no text content", file=sys.stderr)
            return None

        # Check for results - look for any flight indicator
        text_lower = text.lower()
        has_results = any(
            [
                "departure time" in text_lower,
                "departure flights" in text_lower,
                "showing" in text_lower and "results" in text_lower,
                ("pts" in text_lower and "stop" in text_lower),
                re.search(r"\d{1,2}:\d{2}\s*[ap]m", text_lower) and "pts" in text_lower,
            ]
        )
        if not has_results:
            print("Page doesn't appear to have flight results", file=sys.stderr)
            print(
                f"  Text length: {len(text)}, first 200: {text[:200]}", file=sys.stderr
            )
            return None

        # Parse flight blocks from the page text
        flights = []
        lines = text.split("\n")
        current = {}

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Detect departure time - both formats:
            #   "12:55 pm" (standalone) or "Departure time is 12:55 PM" (verbose)
            time_match = re.match(
                r"^(?:Departure time is\s+)?(\d{1,2}:\d{2}\s*[AP]?[ap]?[Mm]?)(?:\s*[‐-]\s*)?$",
                line,
                re.IGNORECASE,
            )
            if time_match and not current.get("depart_time"):
                if current.get("carrier_name"):
                    flights.append(current)
                current = {"depart_time": time_match.group(1).strip()}
                continue

            # Detect time range on one line: "12:55 PM - 06:05 PM"
            range_match = re.match(
                r"^(\d{1,2}:\d{2}\s*[AP]M)\s*[‐-]\s*(\d{1,2}:\d{2}\s*[AP]M)",
                line,
                re.IGNORECASE,
            )
            if range_match and not current.get("depart_time"):
                if current.get("carrier_name"):
                    flights.append(current)
                current = {
                    "depart_time": range_match.group(1).strip(),
                    "arrive_time": range_match.group(2).strip(),
                }
                continue

            # Detect arrival time - both formats:
            #   "06:05 pm" (standalone) or "Destination time is 06:05 PM" (verbose)
            if current.get("depart_time") and not current.get("arrive_time"):
                arr_match = re.match(
                    r"^(?:Destination time is\s+)?(\d{1,2}:\d{2}\s*[AP]?[ap]?[Mm]?)$",
                    line,
                    re.IGNORECASE,
                )
                if arr_match:
                    current["arrive_time"] = arr_match.group(1).strip()
                    continue

            # Skip verbose labels
            if line.startswith("Departure time is") or line.startswith(
                "Destination time is"
            ):
                continue
            if line.startswith("Departure location is") or line.startswith(
                "Destination location is"
            ):
                continue

            # Carrier name (after times, before route)
            if current.get("depart_time") and not current.get("carrier_name"):
                known_carriers = [
                    "Air France",
                    "Air Canada",
                    "United Airlines",
                    "Delta Air Lines",
                    "Lufthansa",
                    "American Airlines",
                    "British Airways",
                    "KLM",
                    "Swiss",
                    "Condor",
                    "WestJet",
                    "Turkish Airlines",
                    "Iberia",
                    "TAP",
                    "SAS",
                    "Finnair",
                    "Singapore Airlines",
                    "Brussels Airlines",
                    "LOT Polish Airlines",
                    "ITA Airways",
                    "Aer Lingus",
                ]
                for carrier in known_carriers:
                    if (
                        carrier.lower() == line.lower()
                        or carrier.lower() in line.lower()
                    ):
                        current["carrier_name"] = carrier
                        break
                if current.get("carrier_name"):
                    continue

            # Airport codes (SFO‐CDG or SFO-CDG pattern, with or without verbose labels)
            airport_match = re.search(r"([A-Z]{3})\s*[‐\-]\s*([A-Z]{3})", line)
            if airport_match:
                current["origin"] = airport_match.group(1)
                current["destination"] = airport_match.group(2)
                continue

            # Duration (e.g., "20h 10m" or "14h 10m")
            dur_match = re.match(r"^(\d+h\s*\d+m)$", line)
            if dur_match:
                current["duration"] = dur_match.group(1)
                continue

            # Stops
            if (
                re.match(r"^\d+\s+stop", line.lower())
                or "nonstop" in line.lower()
                or "non-stop" in line.lower()
            ):
                current["stops_text"] = line
                continue

            # "was X pts" (original price before boost)
            was_match = re.search(r"was\s+([0-9,]+)\s*pts", line)
            if was_match:
                current["base_points"] = int(was_match.group(1).replace(",", ""))
                current["has_boost"] = True
                continue

            # Cash price (e.g., "$5,045" or "$5,045 or")
            price_match = re.match(r"^\$([0-9,]+)", line)
            if price_match:
                price = float(price_match.group(1).replace(",", ""))
                # Take the LOWEST cash price per flight (first fare option)
                if "cash_price" not in current or price < current["cash_price"]:
                    current["cash_price"] = price
                continue

            # Points price (e.g., "252,206 pts")
            pts_match = re.match(r"^([0-9,]+)\s*pts", line)
            if pts_match:
                pts = int(pts_match.group(1).replace(",", ""))
                # Take the LOWEST points price per flight
                if "points_price" not in current or pts < current["points_price"]:
                    current["points_price"] = pts
                continue

            # Fare family
            fare_keywords = [
                "business",
                "economy",
                "first",
                "premium",
                "promotional",
                "restricted",
                "flexi",
                "lowest",
                "standard",
                "flex",
            ]
            if any(kw in line.lower() for kw in fare_keywords) and len(line) < 50:
                current["brand"] = line
                continue

        # Don't forget the last flight
        if current.get("carrier_name"):
            flights.append(current)

        if not flights:
            return None

        # Check for Points Boost
        has_boost = "points boost" in text.lower()

        # Convert to standard format
        itineraries = []
        for f in flights:
            cash = f.get("cash_price", 0)
            points = f.get("points_price", 0)
            cpp = round(cash / points * 100, 2) if points > 0 and cash > 0 else 0

            itin = {
                "journeys": [
                    {
                        "segments": [
                            {
                                "flight": {
                                    "marketingCarrier": {
                                        "code": "",
                                        "name": f.get("carrier_name", ""),
                                    },
                                    "operatingCarrier": {
                                        "code": "",
                                        "name": f.get("carrier_name", ""),
                                    },
                                    "departure": {
                                        "airport": {"code": f.get("origin", "")},
                                        "dateTime": f.get("depart_time", ""),
                                    },
                                    "arrival": {
                                        "airport": {"code": f.get("destination", "")},
                                        "dateTime": f.get("arrive_time", ""),
                                    },
                                    "durationInMinutes": 0,
                                    "flightNumber": "",
                                }
                            }
                        ],
                    }
                ],
                "fareOptions": [
                    {
                        "displayPrice": {
                            "total": {
                                "payable": {
                                    "options": {
                                        "cashOnly": {"value": cash},
                                        "pointsOnly": {"value": points, "baseValue": 0},
                                        "cashAndPoints": {
                                            "cash": {"value": 0},
                                            "points": {"value": 0},
                                        },
                                    }
                                }
                            }
                        },
                        "fareFamily": {"name": f.get("brand", ""), "attributes": {}},
                        "hasDynamicBurnOffer": has_boost,
                    }
                ],
            }
            itineraries.append(itin)

        return {
            "itineraries": itineraries,
            "resultCount": len(itineraries),
            "scraped": True,
        }

    except Exception as e:
        print(f"Scrape error: {e}", file=sys.stderr)
        return None


def parse_flight_results(results):
    """Parse flight results into a clean list of flights."""
    if not results or not results.get("itineraries"):
        return []

    flights = []
    for itin in results["itineraries"]:
        for journey in itin.get("journeys", []):
            segments = journey.get("segments", [])
            if not segments:
                continue

            # Build flight info
            first_seg = segments[0]
            last_seg = segments[-1]
            flight_info = first_seg.get("flight", {})

            # Carrier info
            carrier = flight_info.get("marketingCarrier", {})
            op_carrier = flight_info.get("operatingCarrier", {})

            # Times
            depart = flight_info.get("departure", {})
            arrive = (
                last_seg.get("flight", {}).get("arrival", {})
                if len(segments) > 1
                else flight_info.get("arrival", {})
            )

            # Build segment list for connections
            seg_list = []
            total_duration = 0
            for seg in segments:
                sf = seg.get("flight", {})
                seg_list.append(
                    {
                        "carrier": sf.get("marketingCarrier", {}).get("code", ""),
                        "flight_number": sf.get("flightNumber", ""),
                        "origin": sf.get("departure", {})
                        .get("airport", {})
                        .get("code", ""),
                        "dest": sf.get("arrival", {})
                        .get("airport", {})
                        .get("code", ""),
                        "depart_time": sf.get("departure", {}).get("dateTime", ""),
                        "arrive_time": sf.get("arrival", {}).get("dateTime", ""),
                        "duration": sf.get("durationInMinutes", 0),
                        "aircraft": sf.get("optionalData", {}).get("aircraftName", ""),
                    }
                )
                total_duration += sf.get("durationInMinutes", 0)

            stops = len(segments) - 1
            stop_cities = []
            if stops > 0:
                for i, seg in enumerate(segments[:-1]):
                    sf = seg.get("flight", {})
                    stop_cities.append(
                        sf.get("arrival", {}).get("airport", {}).get("code", "")
                    )

            flight = {
                "carrier_code": carrier.get("code", ""),
                "carrier_name": carrier.get("name", ""),
                "operating_carrier": op_carrier.get("name", ""),
                "flight_numbers": "/".join(
                    s["carrier"] + s["flight_number"] for s in seg_list
                ),
                "origin": depart.get("airport", {}).get("code", ""),
                "destination": arrive.get("airport", {}).get("code", ""),
                "depart_time": depart.get("dateTime", ""),
                "arrive_time": arrive.get("dateTime", ""),
                "duration_minutes": total_duration,
                "stops": stops,
                "stop_cities": stop_cities,
                "segments": seg_list,
                "fare_options": [],
            }

            # Parse fare options
            for fo in itin.get("fareOptions", []):
                dp = (
                    fo.get("displayPrice", {})
                    .get("total", {})
                    .get("payable", {})
                    .get("options", {})
                )
                cash = dp.get("cashOnly", {}).get("value", 0)
                points = dp.get("pointsOnly", {}).get("value", 0)
                base_points = dp.get("pointsOnly", {}).get("baseValue", 0)
                cash_and_pts = dp.get("cashAndPoints", {})

                fare_family = fo.get("fareFamily", {})
                has_boost = fo.get("hasDynamicBurnOffer", False)

                # Calculate CPP
                cpp = 0
                if points > 0 and cash > 0:
                    cpp = round(cash / points * 100, 2)

                # Calculate boost savings
                boost_savings_pct = 0
                if (
                    has_boost
                    and base_points > 0
                    and points > 0
                    and points < base_points
                ):
                    boost_savings_pct = round((1 - points / base_points) * 100, 1)

                fare_opt = {
                    "brand": fare_family.get("name", "Unknown"),
                    "cabin": fo.get("cabinType", ""),
                    "cash_price": cash,
                    "points_price": points,
                    "base_points": base_points,
                    "cash_plus_points": {
                        "cash": cash_and_pts.get("cash", {}).get("value", 0),
                        "points": cash_and_pts.get("points", {}).get("value", 0),
                    },
                    "has_boost": has_boost,
                    "boost_savings_pct": boost_savings_pct,
                    "cpp": cpp,
                    "attributes": fare_family.get("attributes", {}),
                }
                flight["fare_options"].append(fare_opt)

            flights.append(flight)

    return flights


def format_duration(minutes):
    """Format minutes as Xh Ym."""
    if not minutes:
        return "?"
    h = minutes // 60
    m = minutes % 60
    return f"{h}h {m:02d}m"


def format_time(dt_str):
    """Extract time from datetime string like 2026-08-11T12:55."""
    if not dt_str:
        return "?"
    match = re.search(r"T(\d{2}:\d{2})", dt_str)
    return match.group(1) if match else dt_str


def format_price(amount):
    """Format dollar amount."""
    if not amount:
        return "N/A"
    return f"${amount:,.0f}"


def format_points(amount):
    """Format points amount."""
    if not amount:
        return "N/A"
    return f"{amount:,.0f}"


def print_flight_table(flights, show_json=False):
    """Print flights in markdown table format."""
    if show_json:
        print(json.dumps(flights, indent=2))
        return

    if not flights:
        print("No flights found.")
        return

    # Find cheapest by cash and points
    cheapest_cash = min(
        (f["fare_options"][0]["cash_price"] for f in flights if f["fare_options"]),
        default=0,
    )
    cheapest_pts = min(
        (f["fare_options"][0]["points_price"] for f in flights if f["fare_options"]),
        default=0,
    )

    print(f"\n{'=' * 80}")
    print(f"Found {len(flights)} flights")
    print(f"{'=' * 80}\n")

    # Table header
    print(
        "| # | Airline | Flight | Stops | Duration | Depart | Arrive | Cash | Points | CPP | Boost |"
    )
    print(
        "|---|---------|--------|-------|----------|--------|--------|------|--------|-----|-------|"
    )

    for i, f in enumerate(flights, 1):
        stops_str = (
            "Nonstop"
            if f["stops"] == 0
            else f"{f['stops']} stop{'s' if f['stops'] > 1 else ''}"
        )
        if f["stop_cities"]:
            stops_str += f" ({','.join(f['stop_cities'])})"

        # Use cheapest fare option
        fo = f["fare_options"][0] if f["fare_options"] else {}
        cash = fo.get("cash_price", 0)
        points = fo.get("points_price", 0)
        cpp = fo.get("cpp", 0)
        boost = "BOOST" if fo.get("has_boost") else ""
        if fo.get("boost_savings_pct"):
            boost = f"BOOST {fo['boost_savings_pct']}% off"

        # Markers
        cash_str = format_price(cash)
        pts_str = format_points(points)
        if cash == cheapest_cash and cash > 0:
            cash_str += " *"
        if points == cheapest_pts and points > 0:
            pts_str += " *"

        print(
            f"| {i} | {f['carrier_name'][:15]} | {f['flight_numbers'][:12]} | {stops_str[:20]} | "
            f"{format_duration(f['duration_minutes'])} | {format_time(f['depart_time'])} | "
            f"{format_time(f['arrive_time'])} | {cash_str} | {pts_str} | {cpp:.1f}c | {boost} |"
        )

    # Summary
    print(f"\n* = cheapest option")
    if any(fo.get("has_boost") for f in flights for fo in f.get("fare_options", [])):
        print("BOOST = Points Boost active (dynamic, typically 1.5-2.0 cpp; pull actual quote)")

    # Show fare options for cheapest flight
    if flights:
        cheapest = min(
            flights,
            key=lambda f: (
                f["fare_options"][0]["cash_price"]
                if f["fare_options"]
                else float("inf")
            ),
        )
        if len(cheapest.get("fare_options", [])) > 1:
            print(
                f"\nFare options for cheapest ({cheapest['carrier_name']} {cheapest['flight_numbers']}):"
            )
            for fo in cheapest["fare_options"]:
                boost_tag = " [BOOST]" if fo["has_boost"] else ""
                print(
                    f"  {fo['brand']}: {format_price(fo['cash_price'])} / {format_points(fo['points_price'])} pts "
                    f"({fo['cpp']:.1f}cpp){boost_tag}"
                )


# ============================================================
# Main
# ============================================================


def parse_chase_hotels(raw_data):
    """Parse raw Chase hotel API JSON into clean structured output.

    Input: raw API response with 'h' array of hotel objects.
    Output: list of parsed hotel dicts with human-readable fields.
    """
    if not raw_data or "h" not in raw_data:
        return []

    hotels = []
    for h in raw_data["h"]:
        hotel = {
            "id": h.get("id", ""),
            "name": h.get("n", ""),
            "distance_miles": float(h.get("dst", 0)),
            "refundable": h.get("rfd") == "Refundable",
        }

        # Content / metadata
        cnt = h.get("cnt", {})
        if cnt:
            hotel["star_rating"] = cnt.get("rt")
            adr = cnt.get("adr", {})
            city = adr.get("ct", {}).get("n", "")
            line1 = adr.get("l1", "")
            country = adr.get("cc", "")
            hotel["address"] = f"{line1}, {city}, {country}".strip(", ")
            hotel["city"] = city
            hotel["country"] = country

            tar = cnt.get("tar", {})
            if tar:
                hotel["tripadvisor_rating"] = tar.get("rt")
                hotel["tripadvisor_reviews"] = tar.get("cnt", 0)

            geo = cnt.get("geo", {})
            if geo:
                hotel["latitude"] = geo.get("lat")
                hotel["longitude"] = geo.get("lng")

            amn = cnt.get("amn", [])
            hotel["amenities"] = [a.get("n", "") for a in amn if a.get("n")]

        # Pricing from rewards array
        rwds = h.get("po", {}).get("rwd", [])
        for rwd in rwds:
            pcf = rwd.get("rdp", {}).get("rs", {}).get("pcf", {})
            factor = pcf.get("f", 0)
            base_factor = pcf.get("bf", 0)
            rcm = rwd.get("rdp", {}).get("rcm", {})
            total = rcm.get("t", {})
            per_night = rcm.get("pn", {})
            ofr = total.get("ofr", {})

            if factor == 0 and base_factor == 0:
                continue  # Skip zero/hybrid entry

            # Cash price from fare data
            fare = rwd.get("f", {})
            if fare and not hotel.get("cash_total"):
                hotel["cash_total"] = fare.get("ta", 0)
                nights = max(
                    1,
                    round(
                        fare.get("ta", 0)
                        / max(
                            1,
                            per_night.get("pbl", {}).get("c", 0)
                            or per_night.get("pbl", {}).get("p", 0) * base_factor
                            or 1,
                        )
                    ),
                )
                if nights > 0 and fare.get("ta", 0) > 0:
                    hotel["cash_per_night"] = round(fare["ta"] / nights, 2)
                    hotel["nights"] = nights

            if factor > base_factor and ofr.get("d") == "Points offer applied":
                # Boost pricing
                hotel["boost_points_total"] = int(total.get("pbl", {}).get("p", 0))
                hotel["boost_points_per_night"] = int(
                    per_night.get("pbl", {}).get("p", 0)
                )
                hotel["boost_factor"] = factor
                hotel["has_boost"] = True
                if hotel.get("cash_total") and hotel["boost_points_total"] > 0:
                    hotel["boost_cpp"] = round(
                        hotel["cash_total"] / hotel["boost_points_total"] * 100, 2
                    )
            elif factor == base_factor and factor > 0:
                # Standard pricing
                hotel["points_total"] = int(total.get("pbl", {}).get("p", 0))
                hotel["points_per_night"] = int(per_night.get("pbl", {}).get("p", 0))
                if hotel.get("cash_total") and hotel["points_total"] > 0:
                    hotel["cpp"] = round(
                        hotel["cash_total"] / hotel["points_total"] * 100, 2
                    )

        # Edit detection (Signature Amenities in prm array)
        prm = h.get("prm", [])
        for p in prm:
            if p.get("c") == "Signature Amenities":
                hotel["is_edit"] = True
                try:
                    benefits_json = json.loads(p.get("d", "{}"))
                    hotel["edit_benefits"] = [
                        b.get("short", b.get("complete", ""))
                        for b in benefits_json.get("benefits", [])
                        if b.get("short") or b.get("complete")
                    ]
                except (json.JSONDecodeError, TypeError):
                    hotel["edit_benefits"] = []

        hotels.append(hotel)

    return hotels


def main():
    parser = argparse.ArgumentParser(description="Chase Travel portal search")
    parser.add_argument("--origin", help="Origin airport code (e.g., SFO)")
    parser.add_argument("--dest", help="Destination airport code or city name")
    parser.add_argument("--depart", help="Departure date (YYYY-MM-DD)")
    parser.add_argument("--return", dest="return_date", help="Return date (YYYY-MM-DD)")
    parser.add_argument(
        "--cabin",
        default="Economy",
        choices=["Economy", "PremiumEconomy", "Business", "First"],
        help="Cabin class",
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
        "--max-hotels",
        type=int,
        default=100,
        help="Max hotels to fetch (default 100, 0=all)",
    )
    parser.add_argument(
        "--json", action="store_true", dest="json_output", help="JSON output"
    )
    parser.add_argument(
        "--record",
        action="store_true",
        help="Record network traffic (for discovering hotel API)",
    )
    args = parser.parse_args()

    # Validate args
    if not args.hotel:
        if not args.origin or not args.dest or not args.depart:
            parser.error("Flight search requires --origin, --dest, and --depart")
    else:
        if not args.dest or not args.checkin or not args.checkout:
            parser.error("Hotel search requires --dest, --checkin, and --checkout")

    username = os.environ.get("CHASE_USERNAME", "")
    password = os.environ.get("CHASE_PASSWORD", "")
    if not username or not password:
        print("ERROR: CHASE_USERNAME and CHASE_PASSWORD required", file=sys.stderr)
        sys.exit(1)

    cookie_path = get_cookie_path()
    in_docker = os.path.exists("/.dockerenv") or os.environ.get("DOCKER", "")

    if in_docker:
        # Docker: use a temp dir for the browser profile (macOS profiles crash Linux Chromium).
        # Cookies are shared via the mounted /profiles/cookies.json file.
        import tempfile

        profile_dir = tempfile.mkdtemp(prefix="chase-")
    else:
        profile_dir = get_profile_dir()

    os.makedirs(profile_dir, exist_ok=True)

    from patchright.sync_api import sync_playwright

    with sync_playwright() as p:
        # Launch browser
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

        # Login
        if not login(page, ctx, username, password, cookie_path):
            print("ERROR: Login failed", file=sys.stderr)
            ctx.close()
            sys.exit(1)

        # Navigate to portal
        if not navigate_to_portal(page):
            print("ERROR: Could not reach travel portal", file=sys.stderr)
            ctx.close()
            sys.exit(1)

        # Get UR balance
        balance = get_ur_balance(page)
        if balance:
            print(f"UR Points Balance: {balance:,}", file=sys.stderr)

        # Record mode: capture network traffic for API discovery
        if args.record:
            print(
                "Recording network traffic. Do your search in the browser window.",
                file=sys.stderr,
            )
            captured = {"requests": [], "responses": []}

            def on_req(req):
                url = req.url.lower()
                if any(
                    k in url for k in ["hotel", "stay", "search", "/api/", "flight"]
                ):
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
                    print(f">>> {req.method} {req.url[:100]}", file=sys.stderr)

            def on_resp(resp):
                url = resp.url.lower()
                if any(
                    k in url for k in ["hotel", "stay", "search", "/api/", "flight"]
                ):
                    try:
                        body = resp.text()
                    except Exception:
                        body = ""
                    captured["responses"].append(
                        {
                            "url": resp.url,
                            "status": resp.status,
                            "body": body if len(body) < 100000 else body[:5000],
                        }
                    )
                    print(
                        f"<<< {resp.status} {resp.url[:100]} ({len(body)}b)",
                        file=sys.stderr,
                    )

            page.on("request", on_req)
            page.on("response", on_resp)

            # Navigate to stays tab
            page.goto(_portal_url(), timeout=30000)
            page.wait_for_timeout(5000)

            print(
                "\nREADY. Do your search. Create /tmp/chase-record-done.txt when done.",
                file=sys.stderr,
            )
            for _ in range(60):
                if os.path.exists("/tmp/chase-record-done.txt"):
                    os.remove("/tmp/chase-record-done.txt")
                    break
                # MUST use page.wait_for_timeout, NOT time.sleep.
                # time.sleep blocks Python but doesn't pump Playwright's event loop,
                # so page.on("request"/"response") callbacks never fire.
                # page.wait_for_timeout processes browser events during the wait.
                page.wait_for_timeout(5000)
                with open("/tmp/chase-network-capture.json", "w") as f:
                    json.dump(captured, f, indent=2, default=str)
                print(
                    f"  [{len(captured['requests'])}req/{len(captured['responses'])}res]",
                    file=sys.stderr,
                )

            save_cookies(ctx, cookie_path)
            ctx.close()

            # Final save AFTER close (close flushes remaining events)
            with open("/tmp/chase-network-capture.json", "w") as f:
                json.dump(captured, f, indent=2, default=str)

            print(
                f"Saved {len(captured['requests'])} requests, {len(captured['responses'])} responses to /tmp/chase-network-capture.json",
                file=sys.stderr,
            )
            sys.exit(0)

        # Search
        if args.hotel:
            raw_results = search_hotels_api(
                page,
                args.dest,
                args.checkin,
                args.checkout,
                args.guests,
                max_hotels=args.max_hotels,
            )
            hotels = parse_chase_hotels(raw_results) if raw_results else []
            if args.json_output:
                print(
                    json.dumps({"hotels": hotels}, indent=2)
                    if hotels
                    else '{"error": "no results"}'
                )
            else:
                if hotels:
                    print(json.dumps({"hotels": hotels}, indent=2))
                else:
                    print(
                        "No hotel results. Try --record mode to discover the hotel API endpoint."
                    )
        else:
            ssid, results = search_flights_api(
                page,
                args.origin,
                args.dest,
                args.depart,
                args.return_date,
                args.cabin,
                args.passengers,
            )
            if results:
                flights = parse_flight_results(results)

                # Check for Points Boost pricing
                boost_flights = None
                if ssid:
                    boost_results = search_with_boost(page, ssid)
                    if boost_results:
                        boost_flights = parse_flight_results(boost_results)

                if args.json_output:
                    output = {
                        "standard": flights,
                        "boost": boost_flights,
                        "ur_balance": balance,
                    }
                    print(json.dumps(output, indent=2))
                else:
                    print_flight_table(flights)
                    if boost_flights:
                        print(f"\n{'=' * 80}")
                        print("POINTS BOOST PRICING")
                        print(f"{'=' * 80}\n")
                        print_flight_table(boost_flights)
            else:
                print("No flight results.", file=sys.stderr)
                if args.json_output:
                    print('{"error": "no results"}')

        # Save cookies for next run
        save_cookies(ctx, cookie_path)
        ctx.close()


if __name__ == "__main__":
    main()

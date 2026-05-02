"""Shared TicketsAtWork helpers used across search_hotels, search_cars,
browse_tickets, etc.

All scripts go through the same login flow and most use the same kind of
jQuery UI + ElasticSearch autocomplete widget for location selection.
"""

import html
import sys
from datetime import datetime
from pathlib import Path
from patchright.sync_api import sync_playwright, TimeoutError as PwTimeout


def unescape(text):
    """Decode HTML entities (&amp; &quot; etc.) and trim whitespace.
    Returns None for None/empty input.
    """
    if not text:
        return None
    return html.unescape(text).strip() or None


HOMEPAGE = "https://www.ticketsatwork.com"
# When running in Docker, the host typically mounts /output. Locally, fall
# back to /tmp/taw_debug. The script picks /output if it's a writable dir.
import os as _os
if _os.path.isdir("/output") and _os.access("/output", _os.W_OK):
    DEBUG_DIR = Path("/output")
else:
    DEBUG_DIR = Path("/tmp/taw_debug")


def log(msg, prefix="taw"):
    print(f"[{prefix}] {msg}", file=sys.stderr)


def shot(page, name, debug=False):
    if not debug:
        return
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        page.screenshot(path=str(DEBUG_DIR / f"{name}.png"), full_page=True)
        log(f"shot: {DEBUG_DIR / f'{name}.png'}")
    except Exception as e:
        log(f"shot {name} failed: {e}")


def dump_html(page, name, debug=False):
    if not debug:
        return
    DEBUG_DIR.mkdir(parents=True, exist_ok=True)
    try:
        (DEBUG_DIR / f"{name}.html").write_text(page.content())
        log(f"html: {DEBUG_DIR / f'{name}.html'}")
    except Exception as e:
        log(f"dump {name} failed: {e}")


def dismiss_cookies(page):
    """Click through OneTrust cookie banner if present."""
    for sel in [
        "button#onetrust-accept-btn-handler",
        "button:has-text('Accept')",
        "button:has-text('Got it')",
    ]:
        try:
            el = page.locator(sel).first
            if el.is_visible(timeout=1500):
                el.click(timeout=2000)
                page.wait_for_timeout(500)
                log(f"dismissed cookie: {sel}")
                return
        except Exception:
            pass


def login(page, user, password, debug=False):
    """Log into TaW. Returns True on success.

    The visible "Sign in / Register" button is unreliable under automation
    (modal triggers, cookie banner overlap). #member_login_form is in the
    DOM at all times; we set values via JS and click the form's submit
    button directly.
    """
    log("loading homepage...")
    page.goto(HOMEPAGE, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(5000)
    dismiss_cookies(page)
    shot(page, "common_01_homepage", debug)

    log("submitting login via JS...")
    result = page.evaluate(
        """([user, pw]) => {
            const form = document.querySelector('#member_login_form');
            if (!form) return {ok: false, why: 'form not found'};
            const emailEl = form.querySelector('input[name="login_email"]');
            const passEl = form.querySelector('input[name="login_password"]');
            if (!emailEl || !passEl) return {ok: false, why: 'inputs not found'};
            const setVal = (el, v) => {
                const proto = Object.getPrototypeOf(el);
                const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
                setter.call(el, v);
                el.dispatchEvent(new Event('input', {bubbles: true}));
                el.dispatchEvent(new Event('change', {bubbles: true}));
            };
            setVal(emailEl, user);
            setVal(passEl, pw);
            const submit = form.querySelector('button[type="submit"]');
            if (submit) {
                submit.click();
                return {ok: true, method: 'submit.click'};
            }
            form.submit();
            return {ok: true, method: 'form.submit'};
        }""",
        [user, password],
    )
    log(f"login JS result: {result}")
    if not result.get("ok"):
        return False

    log("waiting for login to complete...")
    page.wait_for_timeout(7000)
    shot(page, "common_02_after_login", debug)
    log(f"post-login URL: {page.url}")
    return True


def fill_autocomplete(page, input_selector, lat_selector, lng_selector, query,
                     attempts=3, debug=False, label="autocomplete"):
    """Type into a TaW jQuery UI autocomplete input and click the first
    suggestion. Verifies that the associated lat/lng hidden fields populate.

    Returns True on success.

    Race-condition prone on cold sessions, so retries up to `attempts` times,
    clearing the field each retry. Each attempt waits up to 8s for lat/lng
    to populate before considering it a failure.
    """
    for attempt in range(1, attempts + 1):
        log(f"{label} attempt {attempt}: typing '{query}' into {input_selector}")
        place = page.locator(input_selector)
        place.click(timeout=3000)

        # Clear field and any prior lat/lng state via JS
        page.evaluate(
            """([inSel, latSel, lngSel]) => {
                const clear = (sel) => {
                    const el = document.querySelector(sel);
                    if (!el) return;
                    const proto = Object.getPrototypeOf(el);
                    Object.getOwnPropertyDescriptor(proto, 'value').set.call(el, '');
                    el.dispatchEvent(new Event('input', {bubbles: true}));
                };
                clear(inSel);
                clear(latSel);
                clear(lngSel);
            }""",
            [input_selector, lat_selector, lng_selector],
        )
        page.wait_for_timeout(500)

        place.type(query, delay=80, timeout=10000)
        page.wait_for_timeout(3500)
        shot(page, f"common_autocomplete_a{attempt}", debug)

        # Wait for the dropdown
        try:
            page.wait_for_selector(
                ".ui-autocomplete.ebg-autocomplete .ui-menu-item:visible",
                timeout=10000,
            )
            first = page.locator(
                ".ui-autocomplete.ebg-autocomplete .ui-menu-item"
            ).first
            first.click(timeout=3000)
            log(f"{label}: clicked first suggestion")
        except Exception as e:
            log(f"{label}: dropdown click failed: {e}")

        # Wait for lat/lng to populate
        try:
            page.wait_for_function(
                """([latSel, lngSel]) => {
                    const lat = document.querySelector(latSel)?.value || '';
                    const lng = document.querySelector(lngSel)?.value || '';
                    return lat !== '' && lng !== '';
                }""",
                arg=[lat_selector, lng_selector],
                timeout=8000,
            )
        except PwTimeout:
            log(f"{label}: lat/lng didn't populate within 8s")

        lat = page.evaluate(
            f"() => document.querySelector('{lat_selector}')?.value || ''"
        )
        lng = page.evaluate(
            f"() => document.querySelector('{lng_selector}')?.value || ''"
        )
        log(f"{label}: lat={lat!r} lng={lng!r}")
        if lat and lng:
            return True

        log(f"{label} attempt {attempt} failed; retrying...")
        page.wait_for_timeout(2000)

    return False


def fmt_date_taw(date_iso):
    """Convert YYYY-MM-DD to MM/DD/YY (TaW's expected date format)."""
    dt = datetime.strptime(date_iso, "%Y-%m-%d")
    return dt.strftime("%m/%d/%y")


def to_int(s):
    if s is None or s == "":
        return None
    try:
        return int(str(s).replace(",", "").split(".")[0])
    except (ValueError, AttributeError):
        return None


def to_float(s):
    if s is None or s == "":
        return None
    try:
        return float(str(s).replace(",", ""))
    except (ValueError, AttributeError):
        return None


def make_browser_context(p, tmpdir):
    """Standard Patchright launch options shared across all TaW scripts."""
    return p.chromium.launch_persistent_context(
        tmpdir,
        headless=False,
        viewport={"width": 1440, "height": 900},
        locale="en-US",
        timezone_id="America/Los_Angeles",
    )

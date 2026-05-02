#!/usr/bin/env python3
"""
Record a Chase Travel flight search by capturing network traffic.

1. Logs in automatically
2. Opens the flights page, dismisses modal
3. Prints READY - you do the search manually in the browser
4. Captures all API requests/responses
5. When flight results appear, saves the captured data

Usage:
    export CHASE_USERNAME=... CHASE_PASSWORD=...
    python3 record_search.py
"""

import json
import os
import sys
import time
from pathlib import Path

# Reuse login logic from main script
from search_flights import (
    get_cookie_path,
    get_profile_dir,
    inject_cookies,
    is_logged_in,
    login,
    save_cookies,
)


def main():
    profile_dir = get_profile_dir()
    cookie_path = get_cookie_path()
    os.makedirs(profile_dir, exist_ok=True)

    username = os.environ.get("CHASE_USERNAME", "")
    password = os.environ.get("CHASE_PASSWORD", "")
    if not username or not password:
        print("ERROR: CHASE_USERNAME and CHASE_PASSWORD required", file=sys.stderr)
        sys.exit(1)

    from patchright.sync_api import sync_playwright

    captured_requests = []
    captured_responses = []

    with sync_playwright() as p:
        # Local mode with system Chrome for device trust
        try:
            ctx = p.chromium.launch_persistent_context(
                user_data_dir=profile_dir,
                channel="chrome",
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

        # Set up network capture BEFORE login
        def on_request(request):
            url = request.url.lower()
            # Capture travel/flight related API calls
            if any(
                kw in url
                for kw in [
                    "flight",
                    "search",
                    "travel",
                    "offer",
                    "fare",
                    "itinerar",
                    "availability",
                    "/api/",
                    "graphql",
                ]
            ):
                try:
                    post_data = request.post_data
                except Exception:
                    post_data = "<binary>"
                entry = {
                    "url": request.url,
                    "method": request.method,
                    "post_data": post_data,
                    "headers": dict(request.headers),
                    "resource_type": request.resource_type,
                    "timestamp": time.time(),
                }
                captured_requests.append(entry)
                print(
                    f">>> {request.method} {request.url[:120]} [{request.resource_type}]",
                    file=sys.stderr,
                )

        def on_response(response):
            url = response.url.lower()
            if any(
                kw in url
                for kw in [
                    "flight",
                    "search",
                    "offer",
                    "fare",
                    "itinerar",
                    "availability",
                    "/api/",
                    "graphql",
                ]
            ):
                try:
                    body = response.text()
                except Exception:
                    body = "<binary or failed>"
                entry = {
                    "url": response.url,
                    "status": response.status,
                    "headers": dict(response.headers),
                    "body_preview": body[:5000]
                    if isinstance(body, str)
                    else str(body)[:5000],
                    "body_full": body
                    if isinstance(body, str) and len(body) < 50000
                    else None,
                    "timestamp": time.time(),
                }
                captured_responses.append(entry)
                print(
                    f"<<< {response.status} {response.url[:120]} ({len(body) if isinstance(body, str) else '?'} bytes)",
                    file=sys.stderr,
                )

        page.on("request", on_request)
        page.on("response", on_response)

        # Login
        if not login(page, ctx, username, password, cookie_path):
            print("ERROR: Login failed", file=sys.stderr)
            ctx.close()
            sys.exit(1)

        print("Login succeeded.", file=sys.stderr)

        # Handle account selector
        if "account-selector" in page.url.lower():
            time.sleep(3)
            card_link = page.query_selector(
                'a[aria-label*="CREDIT CARD"], a.list-item__navigational'
            )
            if card_link:
                card_link.click()
                time.sleep(8)

        # Navigate to flights
        from search_flights import FLIGHTS_URL

        page.goto(FLIGHTS_URL, timeout=30000)
        time.sleep(8)

        # Kill modal aggressively
        page.evaluate("""
            document.querySelectorAll('.chase-travel-modal-wrapper, .modal-background').forEach(el => el.remove());
            const obs = new MutationObserver(muts => {
                for (const m of muts) {
                    for (const n of m.addedNodes) {
                        if (n.nodeType === 1 && (n.classList?.contains('chase-travel-modal-wrapper') ||
                            n.classList?.contains('modal-background') ||
                            n.querySelector?.('.chase-travel-modal-wrapper, .modal-background'))) {
                            n.remove();
                        }
                    }
                }
            });
            obs.observe(document.body, {childList: true, subtree: true});
        """)
        time.sleep(1)

        print("\n" + "=" * 60, file=sys.stderr)
        print("READY! Do the flight search in the browser window.", file=sys.stderr)
        print("", file=sys.stderr)
        print("Search for:", file=sys.stderr)
        print("  SFO -> CDG", file=sys.stderr)
        print("  Aug 11 -> Sep 2", file=sys.stderr)
        print("  Business class, Round-trip", file=sys.stderr)
        print("", file=sys.stderr)
        print("I'm capturing all network traffic.", file=sys.stderr)
        print("When results load, press ENTER here to save.", file=sys.stderr)
        print("=" * 60 + "\n", file=sys.stderr)

        # Wait for signal file or timeout.
        # Create /tmp/chase-record-done.txt to stop, or wait 180s.
        print(
            "Create /tmp/chase-record-done.txt when results are showing.",
            file=sys.stderr,
        )
        print("Or wait 180s for auto-save.\n", file=sys.stderr)

        # Save captures every 10s in case of crash
        for tick in range(36):  # 36 * 5s = 180s
            if os.path.exists("/tmp/chase-record-done.txt"):
                print("Done signal received!", file=sys.stderr)
                os.remove("/tmp/chase-record-done.txt")
                break
            # Save interim capture
            if captured_requests or captured_responses:
                with open("/tmp/chase-network-capture.json", "w") as f:
                    json.dump(
                        {
                            "requests": captured_requests,
                            "responses": captured_responses,
                            "interim": True,
                        },
                        f,
                        indent=2,
                        default=str,
                    )
            time.sleep(5)

        # Take final screenshot
        page.screenshot(path="/tmp/chase-recorded-results.png", full_page=True)
        print("Screenshot saved: /tmp/chase-recorded-results.png", file=sys.stderr)

        # Save captured data
        save_cookies(ctx, cookie_path)

        output = {
            "requests": captured_requests,
            "responses": captured_responses,
            "final_url": page.url,
            "page_text_preview": page.inner_text("body")[:3000],
        }

        with open("/tmp/chase-network-capture.json", "w") as f:
            json.dump(output, f, indent=2, default=str)

        print(
            f"\nCaptured {len(captured_requests)} requests, {len(captured_responses)} responses",
            file=sys.stderr,
        )
        print("Saved to /tmp/chase-network-capture.json", file=sys.stderr)

        # Also print summary
        print("\n=== API CALLS ===", file=sys.stderr)
        for req in captured_requests:
            if req["resource_type"] in ("xhr", "fetch"):
                print(
                    f"  {req['method']} {req['url'][:150]}",
                    file=sys.stderr,
                )
                if req.get("post_data"):
                    print(
                        f"    POST: {req['post_data'][:300]}",
                        file=sys.stderr,
                    )

        ctx.close()


if __name__ == "__main__":
    main()

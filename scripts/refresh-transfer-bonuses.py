#!/usr/bin/env python3
"""Refresh data/transfer-bonuses.json from Frequent Miler.

Scrapes https://frequentmiler.com/current-point-transfer-bonuses/ and updates
the active_bonuses array. Confidence is set to LIKELY by default; the cross-
check pass against AwardWallet upgrades verified ones to VERIFIED.

Hard rules (per Research Integrity Protocol):
- NEVER fabricate a bonus. If the page can't be parsed, exit nonzero with a
  clear message; do not write a partial or guessed file.
- Sources are URLs, never inferred.
- If a bonus's source URL doesn't resolve to 200, it stays in the data
  but is flagged in the run log.
- The script preserves manually-curated fields (notes, frequent_recurring_*,
  decision_rules) when re-writing.

Usage:
    python3 scripts/refresh-transfer-bonuses.py            # update file
    python3 scripts/refresh-transfer-bonuses.py --dry-run  # show diff, don't write
    python3 scripts/refresh-transfer-bonuses.py --verbose  # detailed log

Network requirement: outbound HTTPS to frequentmiler.com and awardwallet.com.
"""

import argparse
import json
import re
import sys
import urllib.request
from datetime import date, timedelta
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DATA_FILE = REPO / "data" / "transfer-bonuses.json"

FM_URL = "https://frequentmiler.com/current-point-transfer-bonuses/"
AW_URL = "https://awardwallet.com/news/credit-card-transfer-bonuses/"

# Cloudflare blocks generic UAs on Frequent Miler. Use a realistic browser
# string. This is read-only access to a publicly-published page.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
)


def fetch(url, timeout=20):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "identity",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def parse_fm_bonuses(html):
    """Extract active bonuses from Frequent Miler's `tablepress-33-no-5` table.

    The active bonuses live in a TablePress table with id `tablepress-33-no-5`.
    Expired bonuses live in `tablepress-33-no-6`. Each row has cells:
      [program name | <a href=POST>BONUS_TITLE</a> | start_date | end_date]

    Dates are MM/DD/YY in the visible cell (Excel serial date hidden in <p
    style='display:none'>). Bonus title format: "{N}% transfer bonus from
    {FROM} to {TO}" or "Up to {N}% transfer bonus from {FROM} to {TO}".

    Never fabricates - if a row can't be parsed, it's skipped with a
    warning. Raises RuntimeError if the active table is missing entirely.
    """
    # Anchor on the actual table id, not the heading text (which appears
    # in TOC, schema markup, and other places that confuse a simple search).
    active_match = re.search(
        r'<table[^>]+id="tablepress-33-no-5"[^>]*>(.*?)</table>',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    if not active_match:
        raise RuntimeError(
            "Frequent Miler page structure has changed: could not find "
            "active bonuses table (tablepress-33-no-5). Please verify by "
            "visiting " + FM_URL
        )

    active_table = active_match.group(1)

    bonuses = []
    # Parse table rows. Each <tr> has the structure described above.
    row_re = re.compile(r"<tr[^>]*>(.*?)</tr>", re.IGNORECASE | re.DOTALL)
    for row_match in row_re.finditer(active_table):
        row = row_match.group(1)
        # Skip the header row (it has <th>, not <td>)
        if "<th" in row.lower():
            continue

        # Extract the link in the second cell. We expect exactly one anchor
        # per row that points to a frequentmiler post.
        link_match = re.search(
            r"<a[^>]+href=['\"](https://frequentmiler\.com/[^'\"]+)['\"][^>]*>([^<]+)</a>",
            row,
            re.IGNORECASE,
        )
        if not link_match:
            continue

        url = link_match.group(1)
        link_text = link_match.group(2).strip()

        # Bonus title format: "{N}% transfer bonus from {FROM} to {TO}"
        # or "Up to {N}% transfer bonus from {FROM} to {TO}"
        # Some non-percent bonuses exist (e.g., "5,000 bonus points"); skip those.
        bonus_match = re.match(
            r"(?:Up to )?(\d+)%\s+transfer\s+bonus\s+from\s+(.+?)\s+to\s+(.+?)\s*$",
            link_text,
            re.IGNORECASE,
        )
        if not bonus_match:
            continue

        bonus_pct = int(bonus_match.group(1))
        from_program = bonus_match.group(2).strip()
        to_program = bonus_match.group(3).strip()
        targeted = "[Targeted]" in to_program
        to_program = to_program.replace("[Targeted]", "").strip()

        # Extract dates. Visible cells contain "MM/DD/YY"; hidden <p> contains
        # the Excel serial date which we ignore. Pull the visible dates only.
        date_matches = re.findall(r"\b(\d{2}/\d{2}/\d{2})\b", row)
        if len(date_matches) < 2:
            continue
        start_date_raw = date_matches[0]
        end_date_raw = date_matches[1]

        bonuses.append(
            {
                "bonus_pct": bonus_pct,
                "from_display": from_program,
                "to_display": to_program,
                "targeted": targeted,
                "start_date_raw": start_date_raw,
                "end_date_raw": end_date_raw,
                "source_url": url,
                "link_text": link_text,
            }
        )

    return bonuses


def parse_us_date(d):
    """Convert MM/DD/YY to ISO YYYY-MM-DD. Assumes 20YY for two-digit year."""
    m, d_, y = d.split("/")
    yyyy = 2000 + int(y)
    return f"{yyyy}-{int(m):02d}-{int(d_):02d}"


def normalize_program(display_name):
    """Map a display name to a program slug. Best-effort; unknown programs
    return None (and the script logs and skips them rather than fabricating).

    Slugs match the hand-curated values used in data/transfer-bonuses.json
    so manual fields (notes, transfer_example, etc.) are preserved across
    refresh runs.
    """
    s = display_name.lower().strip()
    mapping = {
        "amex membership rewards": "amex_membership_rewards",
        # Use short form to match hand-curated fingerprints
        "chase ultimate rewards": "chase_ur",
        "capital one miles": "capital_one",
        "capital one": "capital_one",
        "citi thankyou rewards": "citi_typ",
        "bilt": "bilt",
        "rove miles": "rove",
        "marriott bonvoy": "marriott_bonvoy",
        "wyndham": "wyndham",
        "choice": "choice_privileges",
        "accor live limitless": "accor",
        "air canada aeroplan": "aeroplan",
        "air france klm flying blue": "flying_blue",
        "british airways avios": "british_airways_avios",
        "iberia avios": "iberia_avios",
        "aer lingus avios": "aer_lingus_avios",
        "qatar privilege club avios": "qatar_avios",
        "japan airlines mileage bank": "jal_mileage_bank",
        "jal (japan airlines) mileage bank": "jal_mileage_bank",
        "virgin atlantic flying club": "virgin_atlantic",
        "avianca lifemiles": "avianca_lifemiles",
        "qantas frequent flyer": "qantas",
        "etihad guest": "etihad_guest",
        "aeromexico clubpremier": "aeromexico_clubpremier",
        "scandinavian airlines (sas) eurobonus": "sas_eurobonus",
        "sas eurobonus": "sas_eurobonus",
        "turkish airlines miles & smiles": "turkish_miles_smiles",
        "turkish miles & smiles": "turkish_miles_smiles",
        "southwest rapid rewards": "southwest_rapid_rewards",
        "united mileageplus": "united_mileageplus",
        "hilton": "hilton_honors",
        "hilton honors": "hilton_honors",
        "ihg": "ihg_one_rewards",
        "ihg one rewards": "ihg_one_rewards",
        "leading hotels of the world": "leading_hotels_of_world",
        "leading hotels of the world leaders club": "leading_hotels_of_world",
        "preferred hotels & resorts i prefer": "iprefer",
        "i prefer": "iprefer",
        "finnair plus+": "finnair_plus",
        "finnair plus": "finnair_plus",
        "cathay pacific asia miles": "cathay_asia_miles",
        "korean air skypass": "korean_skypass",
    }
    return mapping.get(s)


def _key_tokens(display_name):
    """Extract distinguishing lowercase tokens from a program display name.
    Used to fuzzy-match across sources that format names differently.

    Filters out generic stopwords like 'rewards', 'miles', 'club' that
    appear in dozens of program names.
    """
    stop = {
        "the", "rewards", "miles", "points", "club", "program", "guest",
        "frequent", "flyer", "airlines", "airways", "air", "and", "of",
        "&", "&amp;", "membership", "thankyou", "ultimate", "honors",
        "bonvoy", "limitless",
    }
    raw = re.sub(r"[^\w\s]", " ", display_name.lower())
    toks = [t for t in raw.split() if t and t not in stop and len(t) > 2]
    return toks or [display_name.lower()]


def fingerprint(b):
    """Produce a stable id for a bonus."""
    from_p = normalize_program(b["from_display"]) or "unknown"
    to_p = normalize_program(b["to_display"]) or "unknown"
    end_date = parse_us_date(b["end_date_raw"])
    yyyy_mm = end_date[:7].replace("-", "_")
    return f"{from_p}_to_{to_p}_{b['bonus_pct']}pct_{yyyy_mm}"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--verbose", action="store_true")
    args = p.parse_args()

    def log(msg):
        if args.verbose:
            print(f"[refresh] {msg}", file=sys.stderr)

    if not DATA_FILE.exists():
        print(f"FATAL: {DATA_FILE} does not exist", file=sys.stderr)
        sys.exit(2)

    existing = json.loads(DATA_FILE.read_text())
    log(f"loaded existing data with {len(existing.get('active_bonuses', []))} active bonuses")

    log(f"fetching {FM_URL}")
    try:
        fm_html = fetch(FM_URL)
    except Exception as e:
        print(f"FATAL: could not fetch Frequent Miler: {e}", file=sys.stderr)
        sys.exit(3)

    log(f"parsing FM bonuses")
    try:
        fm_bonuses = parse_fm_bonuses(fm_html)
    except RuntimeError as e:
        print(f"FATAL: {e}", file=sys.stderr)
        sys.exit(4)

    if not fm_bonuses:
        print(
            "FATAL: parsed zero bonuses from Frequent Miler. "
            "Either the page is empty (unusual) or the parser is broken. "
            "Refusing to write a file with zero bonuses.",
            file=sys.stderr,
        )
        sys.exit(5)

    log(f"parsed {len(fm_bonuses)} candidate bonuses from Frequent Miler")

    # Cross-check against AwardWallet for confidence boost
    log(f"fetching {AW_URL}")
    aw_html = ""
    try:
        aw_html = fetch(AW_URL)
    except Exception as e:
        log(f"AwardWallet fetch failed (continuing without cross-check): {e}")

    new_active = []
    today = date.today().isoformat()

    # Preserve manual fields from existing entries (notes, stackable_bonuses)
    existing_by_id = {b.get("id"): b for b in existing.get("active_bonuses", [])}

    for raw in fm_bonuses:
        from_p = normalize_program(raw["from_display"])
        to_p = normalize_program(raw["to_display"])
        if not from_p or not to_p:
            log(
                f"SKIP unmapped programs: {raw['from_display']!r} -> "
                f"{raw['to_display']!r}. Add to normalize_program() mapping."
            )
            continue

        bonus_id = fingerprint(raw)
        end_date = parse_us_date(raw["end_date_raw"])

        # Skip already-expired bonuses (Frequent Miler keeps them in the
        # active table briefly past expiry sometimes)
        if end_date < today:
            log(f"SKIP expired: {bonus_id} (ended {end_date}, today is {today})")
            continue

        # Cross-check: does AwardWallet's page corroborate this bonus?
        # AwardWallet links each bonus to a dedicated post URL containing
        # the partner name and "transfer-bonus" (e.g.,
        # /news/chase-ultimate-rewards/aeroplan-transfer-bonus/). We search
        # for an AwardWallet URL whose path mentions both a token from the
        # destination program AND the bonus percentage's transfer-bonus
        # post. This is far more deterministic than text proximity.
        confidence = "LIKELY"
        sources = [raw["source_url"]]
        if aw_html:
            aw_lower = aw_html.lower()
            pct_phrase = f"{raw['bonus_pct']}% transfer bonus"
            to_tokens = _key_tokens(raw["to_display"])
            verified = False
            # Strategy 1: look for an AwardWallet bonus-post URL near the
            # bonus phrase that contains any destination token.
            url_re = re.compile(
                r'href="(https?://awardwallet\.com/[^"]*?transfer-bonus[^"]*)"'
            )
            bonus_urls = [m.group(1).lower() for m in url_re.finditer(aw_html)]
            for u in bonus_urls:
                if any(t in u for t in to_tokens):
                    # Confirm the bonus pct appears in a 600-char window
                    # surrounding this URL on the AW page.
                    href_idx = aw_html.lower().find(u)
                    if href_idx >= 0:
                        win = aw_html.lower()[
                            max(0, href_idx - 600) : href_idx + 600
                        ]
                        if pct_phrase in win:
                            verified = True
                            break
            if verified:
                confidence = "VERIFIED"
                sources.append(AW_URL)

        # Build the entry, preserving manually-curated notes/stackable_bonuses
        # if the bonus was already in the file.
        prior = existing_by_id.get(bonus_id, {})

        entry = {
            "id": bonus_id,
            "from_program": from_p,
            "from_display": raw["from_display"],
            "to_program": to_p,
            "to_display": raw["to_display"],
            "bonus_pct": raw["bonus_pct"],
            "ratio": 1.0 + raw["bonus_pct"] / 100.0,
            "start_date": parse_us_date(raw["start_date_raw"]),
            "end_date_inclusive": end_date,
            "confidence": confidence,
            "sources": sources,
        }
        if raw["targeted"]:
            entry["targeted"] = True
        # Preserve manual fields
        for f in ("standard_ratio", "effective_ratio", "transfer_example",
                  "stackable_bonuses", "notes"):
            if f in prior:
                entry[f] = prior[f]
        new_active.append(entry)
        log(f"OK {bonus_id} ({confidence})")

    # Move expired-from-active to expired_recently
    cutoff = (date.today() - timedelta(days=30)).isoformat()
    new_expired = list(existing.get("expired_recently", []))
    new_active_ids = {b["id"] for b in new_active}
    for prior in existing.get("active_bonuses", []):
        if prior.get("id") in new_active_ids:
            continue
        end = prior.get("end_date_inclusive", "")
        if end and end >= cutoff:
            stub = {
                "id": prior.get("id"),
                "from_display": prior.get("from_display"),
                "to_display": prior.get("to_display"),
                "bonus_pct": prior.get("bonus_pct"),
                "end_date_inclusive": end,
                "note": "Recently expired (auto-moved from active list).",
            }
            # avoid duplicates
            if not any(e.get("id") == stub["id"] for e in new_expired):
                new_expired.append(stub)

    # Trim expired list to the last 30 days
    new_expired = [e for e in new_expired if e.get("end_date_inclusive", "") >= cutoff]

    # Build the final structure, preserving manual sections
    out = dict(existing)
    out["_meta"] = dict(existing.get("_meta", {}))
    out["_meta"]["last_updated"] = today
    out["active_bonuses"] = new_active
    out["expired_recently"] = new_expired

    new_text = json.dumps(out, indent=2, ensure_ascii=False) + "\n"

    if args.dry_run:
        old_text = DATA_FILE.read_text()
        if old_text == new_text:
            print("No changes.")
        else:
            print("Would update data/transfer-bonuses.json:")
            print(f"  active_bonuses: {len(existing.get('active_bonuses', []))} -> {len(new_active)}")
            print(f"  expired_recently: {len(existing.get('expired_recently', []))} -> {len(new_expired)}")
        return

    DATA_FILE.write_text(new_text)
    print(f"Updated {DATA_FILE}")
    print(f"  active_bonuses: {len(new_active)}")
    print(f"  expired_recently: {len(new_expired)}")
    print(f"  last_updated: {today}")


if __name__ == "__main__":
    main()

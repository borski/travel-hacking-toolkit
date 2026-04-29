#!/usr/bin/env python3
"""Refresh FHR / THC / Chase Edit hotel property data from upstream KML.

Source: 美卡指南 (US Card Guide) Google My Maps, maintained by Scott.

  FHR + THC: https://www.google.com/maps/d/kml?mid=1HygPCP9ghtDptTNnpUpd_C507Mq_Fhec&forcekml=1
  Chase Edit: https://www.google.com/maps/d/kml?mid=1Ickidw1Z6ACres9EnbM2CmPObYsuijM&forcekml=1

The KML structure has multiple "Folder" elements. Each Folder is a "layer" in
Google My Maps. Each Folder contains many Placemark elements (one per hotel).

Layer assignment:
  FHR/THC KML:
    Folder name "FHR"  -> data/fhr-properties.json
    Folder name "THC"  -> data/thc-properties.json
  Chase Edit KML:
    Any folder        -> data/chase-edit-properties.json
    Folder "Potentially Cheaper Ones" -> tag those properties as budget_friendly

Output schema is preserved from the existing JSON files so the rest of the
toolkit keeps working without changes.

Usage:
  python3 scripts/refresh-hotel-data.py            # write data/*.json files
  python3 scripts/refresh-hotel-data.py --dry-run  # show counts, write nothing
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"

NS = {"kml": "http://www.opengis.net/kml/2.2"}

FHR_THC_URL = "https://www.google.com/maps/d/kml?mid=1HygPCP9ghtDptTNnpUpd_C507Mq_Fhec&forcekml=1"
CHASE_URL = "https://www.google.com/maps/d/kml?mid=1Ickidw1Z6ACres9EnbM2CmPObYsuijM&forcekml=1"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "travel-hacking-toolkit/refresh-hotel-data"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def parse_placemark(pm: ET.Element) -> dict[str, Any] | None:
    """Extract a single hotel record from a <Placemark>."""
    name_el = pm.find("kml:name", NS)
    if name_el is None or not (name_el.text or "").strip():
        return None
    name = (name_el.text or "").strip()

    description = ""
    desc_el = pm.find("kml:description", NS)
    if desc_el is not None and desc_el.text:
        description = desc_el.text

    coordinates = None
    coords_el = pm.find(".//kml:Point/kml:coordinates", NS)
    if coords_el is not None and coords_el.text:
        # Format is "lon,lat,alt"
        parts = coords_el.text.strip().split(",")
        if len(parts) >= 2:
            try:
                lng = float(parts[0])
                lat = float(parts[1])
                coordinates = {"lng": lng, "lat": lat}
            except ValueError:
                pass

    record: dict[str, Any] = {"name": name}
    if coordinates is not None:
        record["coordinates"] = coordinates
        record["location"] = f"[{coordinates['lat']}, {coordinates['lng']}]"

    # Scott's KML uses simple "Field: value<br>" lines in <description>.
    # Parse that into structured fields. Map known field names to our schema.
    fields = parse_description_fields(description)

    # Field mapping from KML key -> output key. Keep extras as-is via lower_snake.
    if "Program" in fields:
        record["program"] = fields["Program"]
    if "Credit" in fields:
        record["credit"] = fields["Credit"]
    if "Price_Calendar" in fields:
        record["price_calendar"] = fields["Price_Calendar"]
    if "Amex_Reservation" in fields:
        record["amex_reservation"] = fields["Amex_Reservation"]

    # Some Placemarks include a free-form `location:` line (Chase Edit uses this
    # for text locations like "RENDEZVOUS BAY, ANGUILLA"). Coordinates take
    # precedence; use the text form only when no coordinates are present.
    if coordinates is None and "location" in {k.lower() for k in fields}:
        for k, v in fields.items():
            if k.lower() == "location":
                record["location"] = v
                break

    # Carry through other useful Amex perks (FreeBreakfast, FreeWiFi, etc) so
    # consumers can use them. Keep them in a benefits sub-object so the top
    # level stays clean.
    benefits = {}
    for key in ("EarlyCheckin", "FreeBreakfast", "FreeWiFi", "LateCheckout", "RoomUpgrade", "DiningCredit", "SpaCredit", "ResortCredit"):
        if key in fields:
            benefits[snake_case(key)] = fields[key]
    if benefits:
        record["benefits"] = benefits

    return record


def parse_description_fields(description: str) -> dict[str, str]:
    """Parse `Key: value<br>Key: value<br>...` into a dict."""
    if not description:
        return {}
    parts = re.split(r"<br\s*/?>", description, flags=re.IGNORECASE)
    fields: dict[str, str] = {}
    for part in parts:
        m = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*:\s*(.+?)\s*$", part)
        if m:
            fields[m.group(1)] = m.group(2).strip()
    return fields


def snake_case(name: str) -> str:
    """Convert CamelCase / PascalCase to snake_case."""
    s = re.sub(r"(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", s).lower()


def parse_kml(xml_bytes: bytes) -> dict[str, list[dict[str, Any]]]:
    """Return a mapping of folder-name -> list of hotel records."""
    root = ET.fromstring(xml_bytes)
    folders: dict[str, list[dict[str, Any]]] = {}

    # Walk every Folder/Placemark pair while preserving folder grouping.
    for folder in root.iter("{http://www.opengis.net/kml/2.2}Folder"):
        folder_name_el = folder.find("kml:name", NS)
        if folder_name_el is None:
            continue
        folder_name = (folder_name_el.text or "").strip()
        records: list[dict[str, Any]] = []
        for pm in folder.findall("kml:Placemark", NS):
            rec = parse_placemark(pm)
            if rec:
                records.append(rec)
        if records:
            folders.setdefault(folder_name, []).extend(records)

    # KMLs without an explicit Folder for everything also have top-level Placemarks.
    top_level = []
    for pm in root.findall(".//kml:Document/kml:Placemark", NS):
        rec = parse_placemark(pm)
        if rec:
            top_level.append(rec)
    if top_level:
        folders.setdefault("__top_level__", []).extend(top_level)

    return folders


def write_fhr_thc(folders: dict[str, list[dict[str, Any]]], dry_run: bool) -> tuple[int, int]:
    today = date.today().isoformat()

    # Folder names from Scott's Google My Maps. We match loosely so renames
    # do not silently break the refresh.
    def find_folder(*needles: str) -> list[dict[str, Any]]:
        for name, records in folders.items():
            lower = name.lower()
            if all(needle.lower() in lower for needle in needles):
                return records
        return []

    fhr_records = find_folder("fine hotels")
    if not fhr_records:
        fhr_records = find_folder("fhr")
    for r in fhr_records:
        r.setdefault("program", "FHR")

    thc_records = find_folder("hotel collection")
    if not thc_records:
        thc_records = find_folder("thc")
    for r in thc_records:
        r.setdefault("program", "THC")

    fhr_payload = {
        "_meta": {
            "source": "Google My Maps (美卡指南/Scott USCF)",
            "source_url": "https://www.google.com/maps/d/viewer?mid=1HygPCP9ghtDptTNnpUpd_C507Mq_Fhec",
            "last_updated": today,
            "staleness_days": 90,
            "count": len(fhr_records),
        },
        "properties": fhr_records,
    }
    thc_payload = {
        "_meta": {
            "source": "Google My Maps (美卡指南/Scott USCF)",
            "source_url": "https://www.google.com/maps/d/viewer?mid=1HygPCP9ghtDptTNnpUpd_C507Mq_Fhec",
            "last_updated": today,
            "staleness_days": 90,
            "count": len(thc_records),
        },
        "properties": thc_records,
    }

    if not dry_run:
        (DATA_DIR / "fhr-properties.json").write_text(json.dumps(fhr_payload, indent=2) + "\n")
        (DATA_DIR / "thc-properties.json").write_text(json.dumps(thc_payload, indent=2) + "\n")

    return len(fhr_records), len(thc_records)


def write_chase_edit(folders: dict[str, list[dict[str, Any]]], dry_run: bool) -> int:
    today = date.today().isoformat()

    all_records: list[dict[str, Any]] = []
    budget_set: set[str] = set()
    for folder_name, records in folders.items():
        if "cheaper" in folder_name.lower() or "budget" in folder_name.lower():
            for r in records:
                budget_set.add(r["name"])
        all_records.extend(records)

    # Deduplicate by name and merge budget tag in.
    deduped: dict[str, dict[str, Any]] = {}
    for r in all_records:
        existing = deduped.get(r["name"])
        if existing:
            for k, v in r.items():
                existing.setdefault(k, v)
        else:
            deduped[r["name"]] = dict(r)
        if r["name"] in budget_set:
            deduped[r["name"]]["budget_friendly"] = True

    final = list(deduped.values())
    payload = {
        "_meta": {
            "source": "Google My Maps (美卡指南/Scott USCF)",
            "source_url": "https://www.google.com/maps/d/viewer?mid=1Ickidw1Z6ACres9EnbM2CmPObYsuijM",
            "last_updated": today,
            "staleness_days": 90,
            "count": len(final),
            "note": f"{sum(1 for r in final if r.get('budget_friendly'))} properties tagged budget_friendly from 'Potentially Cheaper Ones' layer",
        },
        "properties": final,
    }

    if not dry_run:
        (DATA_DIR / "chase-edit-properties.json").write_text(json.dumps(payload, indent=2) + "\n")

    return len(final)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="show counts but do not write files")
    args = ap.parse_args()

    print(f"Fetching FHR/THC KML...", flush=True)
    fhr_thc_xml = fetch(FHR_THC_URL)
    print(f"  ok ({len(fhr_thc_xml)} bytes)")

    print(f"Fetching Chase Edit KML...", flush=True)
    chase_xml = fetch(CHASE_URL)
    print(f"  ok ({len(chase_xml)} bytes)")

    print("Parsing FHR/THC...")
    fhr_thc_folders = parse_kml(fhr_thc_xml)
    print(f"  folders: {sorted(fhr_thc_folders.keys())}")

    print("Parsing Chase Edit...")
    chase_folders = parse_kml(chase_xml)
    print(f"  folders: {sorted(chase_folders.keys())}")

    fhr_count, thc_count = write_fhr_thc(fhr_thc_folders, args.dry_run)
    chase_count = write_chase_edit(chase_folders, args.dry_run)

    print()
    print(f"FHR    : {fhr_count}")
    print(f"THC    : {thc_count}")
    print(f"Chase Edit: {chase_count}")
    if args.dry_run:
        print("(dry-run, no files written)")
    else:
        print(f"Wrote: data/fhr-properties.json, data/thc-properties.json, data/chase-edit-properties.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
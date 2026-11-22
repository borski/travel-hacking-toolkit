#!/usr/bin/env python3
"""Refresh top 1,000 global downhill ski resorts dataset.

Sources:
  - OpenSkiData (OpenStreetMap + Skimap.org, ODbL):
      https://tiles.openskimap.org/csv/ski_areas.csv
  - OurAirports (Public Domain):
      https://davidmegginson.github.io/ourairports-data/airports.csv

Does NOT modify data/airport-coordinates.json.

Usage:
  python3 scripts/refresh-ski-data.py            # write data/ski-resorts.json
  python3 scripts/refresh-ski-data.py --dry-run  # print stats, write nothing
  python3 scripts/refresh-ski-data.py --no-cache # force re-download of CSVs
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = REPO_ROOT / "data"
CACHE_DIR = Path("/tmp/ski-data-cache")

OPENSKIDATA_URL = "https://tiles.openskimap.org/csv/ski_areas.csv"
OURAIRPORTS_URL = "https://davidmegginson.github.io/ourairports-data/airports.csv"

EARTH_RADIUS_MILES = 3958.7613
EARTH_RADIUS_KM = 6371.0088
TOP_N = 1000

# Curated multi-resort pass affiliations (substring/normalized-name matching).
# Covers major North American, European, Japanese, and Southern Hemisphere networks.
PASS_RESORTS: dict[str, list[str]] = {
    "epic": [
        "vail", "beaver creek", "breckenridge", "keystone", "crested butte",
        "park city", "heavenly", "northstar", "kirkwood", "stevens pass",
        "whistler blackcomb", "stowe", "okemo", "mount snow", "mount sunapee",
        "hunter mountain", "attitash", "wildcat", "crotched", "liberty mountain",
        "roundtop", "whitetail", "jack frost", "big boulder", "seven springs",
        "hidden valley", "laurel mountain", "afton alps", "mt brighton",
        "alpine valley", "boston mills", "brandywine", "mad river mountain",
        "paoli peaks", "snow creek", "wilmot", "telluride", "sun valley",
        "snowbasin", "fernies", "fernie", "kicking horse", "kimberley",
        "nakiska", "mont-sainte-anne", "stoneham",
        "perisher", "falls creek", "hotham", "hakuba", "rusutsu",
        "andermatt", "sedrun", "disentis", "crans-montana", "verbier",
        "les 3 vallees", "courchevel", "meribel", "val thorens",
        "skirama dolomiti", "madonna di campiglio", "ski arlberg", "st. anton",
        "lech", "zurs",
    ],
    "ikon": [
        "aspen", "snowmass", "steamboat", "winter park", "copper mountain",
        "eldora", "arapahoe basin", "palisades tahoe", "mammoth mountain",
        "june mountain", "big bear", "snow summit", "bear mountain",
        "stratton", "sugarbush", "killington", "pico", "sunday river",
        "sugarloaf", "loon mountain", "snowshoe", "tremblant", "blue mountain",
        "jackson hole", "big sky", "sun valley", "schweitzer", "taos",
        "deer valley", "solitude", "brighton", "alta", "snowbird",
        "crystal mountain", "the summit at snoqualmie", "mt. bachelor",
        "banff", "sunshine village", "lake louise", "mt. norquay",
        "revelstoke", "cypress mountain", "red mountain", "panorama",
        "chamonix", "zermatt", "st. moritz", "corviglia", "kitzbuhel",
        "ischgl", "dolomiti superski", "cortina d'ampezzo", "val gardena",
        "alta badia", "kronplatz", "grandvalira", "niseko", "arai", "shiga kogen",
        "coronet peak", "the remarkables", "mt hutt", "thredbo", "mt buller",
        "valle nevado", "sierra nevada", "st. anton",
    ],
    "mountain_collective": [
        "alta", "snowbird", "aspen", "snowmass", "banff", "sunshine village",
        "lake louise", "big sky", "chamonix", "coronet peak", "the remarkables",
        "grand targhee", "jackson hole", "mammoth mountain", "mt buller",
        "niseko", "panorama", "revelstoke", "snowbasin", "sugarloaf",
        "sun valley", "taos", "thredbo", "valle nevado", "arapahoe basin",
        "sunday river", "megève", "bromont", "le massif", "marmot basin",
    ],
    "indy": [
        "jay peak", "bolton valley", "magic mountain", "cannon mountain",
        "waterville valley", "pats peak", "saddleback", "berkshire east",
        "catamount", "greek peak", "brundage", "tamarack", "silver mountain",
        "49 degrees north", "mission ridge", "white pass", "hoodoo",
        "mt. ashland", "dodge ridge", "china peak", "bear valley",
        "powder mountain", "beaver mountain", "eagle point", "brian head",
        "loveland", "monarch", "sunlight", "granby ranch", "powderhorn",
        "red lodge", "bridger bowl", "castle mountain", "apex mountain",
        "whitewater", "manning park", "sasquatch", "appi", "geto kogen",
        "tazawa", "kiroro", "innsbruck", "pila",
    ],
    "dolomiti_superski": [
        "cortina d'ampezzo", "kronplatz", "plan de corones", "alta badia",
        "val gardena", "alpe di siusi", "val di fassa", "carezza", "arabba",
        "marmolada", "3 cime", "tre cime", "val di fiemme", "obereggen",
        "san martino di castrozza", "gitschberg", "jochtal", "alpe lusia",
        "san pellegrino", "civetta",
    ],
    "superskicard": [
        "kitzbühel", "kitzbuhel", "skiwelt", "saalbach", "hinterglemm",
        "zell am see", "kaprun", "schladming", "flachau", "obertauern",
        "bad gastein", "hochkonig", "hochkönig", "st. johann", "fieberbrunn",
        "lofer", "steinplatte", "werfenweng", "grossarl", "großarl",
    ],
    "snow_card_tirol": [
        "sölden", "soelden", "ischgl", "st. anton", "obergurgl", "hochgurgl",
        "mayrhofen", "hintertux", "zillertal", "serfaus", "fiss", "ladis",
        "kitzbühel", "kitzbuhel", "skiwelt", "stubai", "pitztal", "kaunertal",
        "kuehtai", "kühtai", "axamer lizum", "patscherkofel", "hochzillertal",
    ],
    "magic_pass": [
        "saas-fee", "saas fee", "grimentz", "zinal", "st-luc", "chandolin",
        "anzère", "anzere", "ovronnaz", "leysin", "les diablerets", "villars",
        "gryon", "champery", "morgins", "gstaad", "adelboden", "lenk",
        "meiringen", "engelberg", "melchsee-frutt", "sörenberg", "moléson",
    ],
    "ski_amade": [
        "ski amadé", "ski amade", "schladming", "planai", "flachau", "wagrain",
        "st. johann", "zauchensee", "bad gastein", "bad hofgastein", "dorfgastein",
        "grossarl", "großarl", "hochkönig", "hochkonig", "maria alm",
        "altenmarkt", "radstadt", "obertauern",
    ],
    "trois_vallees": [
        "les trois vallées", "les trois vallees", "les 3 vallées", "les 3 vallees",
        "courchevel", "méribel", "meribel", "val thorens", "les menuires",
        "saint-martin-de-belleville", "orelle",
    ],
    "portes_du_soleil": [
        "portes du soleil", "avoriaz", "morzine", "les gets", "châtel",
        "chatel", "champéry", "champery", "morgins", "torgon",
    ],
    "mont_blanc_unlimited": [
        "chamonix", "les houches", "courmayeur", "megève", "megeve",
        "saint-gervais", "verbier",
    ],
}

BUDGET_COUNTRIES = {
    "Bulgaria", "Romania", "Poland", "Slovakia", "Czechia", "Czech Republic",
    "Ukraine", "Georgia", "Russia", "Kazakhstan", "Turkey", "Bosnia and Herzegovina",
    "Serbia", "Montenegro", "North Macedonia", "Slovenia", "Croatia", "China",
    "Iran", "Lebanon", "Morocco",
}
EURO_MID_COUNTRIES = {
    "Austria", "France", "Italy", "Germany", "Spain", "Andorra", "Norway",
    "Sweden", "Finland", "United Kingdom", "Japan", "South Korea",
}


def download_file(url: str, dest: Path, no_cache: bool = False) -> Path:
    """Download url to dest if missing or no_cache is True."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and not no_cache:
        return dest
    print(f"Downloading {url} ...", file=sys.stderr)
    req = urllib.request.Request(url, headers={"User-Agent": "travel-hacking-toolkit/1.0"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        dest.write_bytes(resp.read())
    return dest


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> tuple[float, float]:
    """Return (crow_flies_km, crow_flies_mi) between two lat/lon points."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return EARTH_RADIUS_KM * c, EARTH_RADIUS_MILES * c


def to_int(val: str, default: int = 0) -> int:
    try:
        return int(round(float(val)))
    except (ValueError, TypeError):
        return default


def to_float(val: str) -> float | None:
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def match_passes(name: str) -> list[str]:
    norm = name.lower().strip()
    matched = []
    for pass_id, keywords in PASS_RESORTS.items():
        if any(kw in norm for kw in keywords):
            matched.append(pass_id)
    return matched


def estimate_price_tier(country: str, passes: list[str], size_score: int) -> str:
    """Estimate 1-day walk-up adult lift ticket tier ($ to $$$$)."""
    primary_country = country.split(";")[0].split(",")[0].strip()
    if primary_country in {"United States", "Canada"}:
        if any(p in passes for p in ("epic", "ikon", "mountain_collective")) or size_score >= 380:
            return "$$$$"
        if "indy" in passes or size_score >= 140:
            return "$$$"
        return "$$"
    if primary_country == "Switzerland":
        return "$$$" if size_score >= 350 or "ikon" in passes or "epic" in passes else "$$"
    if primary_country in {"Australia", "New Zealand"}:
        return "$$$" if any(p in passes for p in ("epic", "ikon", "mountain_collective")) else "$$"
    if primary_country == "Japan":
        return "$$" if any(p in passes for p in ("epic", "ikon", "mountain_collective")) or size_score >= 250 else "$"
    if primary_country in BUDGET_COUNTRIES:
        return "$"
    if primary_country in EURO_MID_COUNTRIES:
        return "$$" if size_score >= 120 else "$"
    return "$$"


def infer_season(lat: float, max_elev: int, name: str) -> tuple[str, str, bool]:
    hemisphere = "north" if lat >= 0 else "south"
    glacier = "glacier" in name.lower() or "gletscher" in name.lower() or "glaciar" in name.lower() or max_elev >= 3300
    if hemisphere == "south":
        season = "Jun-Oct" if max_elev >= 1800 else "Jun-Sep"
    else:
        if glacier and max_elev >= 3200:
            season = "Oct-May"
        elif max_elev >= 2600:
            season = "Nov-May"
        elif max_elev >= 1700:
            season = "Nov-Apr"
        else:
            season = "Dec-Mar"
    return hemisphere, season, glacier


def load_airports(path: Path) -> list[dict[str, Any]]:
    airports = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("scheduled_service") != "yes":
                continue
            atype = row.get("type", "")
            if atype not in ("large_airport", "medium_airport"):
                continue
            iata = (row.get("iata_code") or "").strip().upper()
            if not re.fullmatch(r"[A-Z]{3}", iata):
                continue
            lat = to_float(row.get("latitude_deg", ""))
            lon = to_float(row.get("longitude_deg", ""))
            if lat is None or lon is None:
                continue
            airports.append({
                "iata": iata,
                "name": row.get("name", "").strip(),
                "municipality": row.get("municipality", "").strip(),
                "country": row.get("iso_country", "").strip(),
                "type": atype,
                "lat": lat,
                "lon": lon,
            })
    return airports


def load_resorts(path: Path) -> list[dict[str, Any]]:
    candidates = []
    with path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row.get("has_downhill") != "yes":
                continue
            status = (row.get("status") or "").strip().lower()
            if status and status != "operating":
                continue
            name = (row.get("name") or "").strip()
            if not name:
                continue
            lat = to_float(row.get("lat", ""))
            lon = to_float(row.get("lng", ""))
            if lat is None or lon is None:
                continue

            lift_count = to_int(row.get("lift_count", ""))
            run_km = to_int(row.get("downhill_distance_km", ""))
            vertical_m = to_int(row.get("vertical_m", ""))
            min_elev = to_int(row.get("min_elevation_m", ""))
            max_elev = to_int(row.get("max_elevation_m", ""))

            # Require at least 1 lift or meaningful vertical/run distance to skip micro-hills
            if lift_count == 0 and run_km == 0 and vertical_m < 100:
                continue

            size_score = lift_count * 10 + run_km * 2 + (vertical_m // 25)
            country = (row.get("countries") or "").strip()
            region = (row.get("regions") or "").strip()
            localities = (row.get("localities") or "").strip()
            websites = [w for w in (row.get("websites") or "").split() if w.startswith("http")]
            passes = match_passes(name)
            hemisphere, season, glacier = infer_season(lat, max_elev, name)
            price_tier = estimate_price_tier(country, passes, size_score)

            candidates.append({
                "id": row.get("id", "").strip(),
                "name": name,
                "country": country,
                "region": region,
                "locality": localities,
                "hemisphere": hemisphere,
                "typical_season": season,
                "lat": round(lat, 5),
                "lon": round(lon, 5),
                "base_elevation_m": min_elev,
                "summit_elevation_m": max_elev,
                "vertical_m": vertical_m,
                "lift_count": lift_count,
                "run_km": run_km,
                "size_score": size_score,
                "glacier": glacier,
                "passes": passes,
                "price_tier": price_tier,
                "website": websites[0] if websites else "",
                "openskimap_url": row.get("openskimap", "").strip(),
            })

    candidates.sort(key=lambda r: (r["size_score"], r["lift_count"], r["vertical_m"]), reverse=True)
    return candidates[:TOP_N]


def attach_nearest_airports(resorts: list[dict[str, Any]], airports: list[dict[str, Any]]) -> None:
    for r in resorts:
        rlat, rlon = r["lat"], r["lon"]
        scored = []
        for a in airports:
            # Fast bounding-box prefilter (~10 deg ~ 1100 km)
            if abs(a["lat"] - rlat) > 12.0:
                continue
            km, mi = haversine(rlat, rlon, a["lat"], a["lon"])
            scored.append((km, mi, a))
        if not scored:
            for a in airports:
                km, mi = haversine(rlat, rlon, a["lat"], a["lon"])
                scored.append((km, mi, a))
        scored.sort(key=lambda x: x[0])

        nearest = []
        has_large = False
        for km, mi, a in scored[:3]:
            if a["type"] == "large_airport":
                has_large = True
            nearest.append({
                "iata": a["iata"],
                "name": a["name"],
                "city": a["municipality"],
                "country": a["country"],
                "type": a["type"],
                "crow_flies_km": round(km),
                "crow_flies_mi": round(mi),
            })
        if not has_large:
            for km, mi, a in scored[3:]:
                if a["type"] == "large_airport":
                    nearest.append({
                        "iata": a["iata"],
                        "name": a["name"],
                        "city": a["municipality"],
                        "country": a["country"],
                        "type": a["type"],
                        "crow_flies_km": round(km),
                        "crow_flies_mi": round(mi),
                    })
                    break
        r["nearest_airports"] = nearest


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh top 1,000 global ski resorts dataset.")
    parser.add_argument("--dry-run", action="store_true", help="Print stats without writing data/ski-resorts.json")
    parser.add_argument("--no-cache", action="store_true", help="Re-download CSV sources")
    args = parser.parse_args()

    ski_csv = download_file(OPENSKIDATA_URL, CACHE_DIR / "ski_areas.csv", no_cache=args.no_cache)
    airports_csv = download_file(OURAIRPORTS_URL, CACHE_DIR / "airports.csv", no_cache=args.no_cache)

    airports = load_airports(airports_csv)
    resorts = load_resorts(ski_csv)
    attach_nearest_airports(resorts, airports)

    north = sum(1 for r in resorts if r["hemisphere"] == "north")
    south = len(resorts) - north
    with_passes = sum(1 for r in resorts if r["passes"])
    print(
        f"Loaded {len(airports)} commercial airports; selected top {len(resorts)} resorts "
        f"(north={north}, south={south}, with_pass={with_passes}).",
        file=sys.stderr,
    )

    if args.dry_run:
        for r in resorts[:5]:
            hub = r["nearest_airports"][0]
            print(f"  {r['name']} ({r['country']}) score={r['size_score']} -> {hub['iata']} ({hub['crow_flies_mi']} mi crow-flies)", file=sys.stderr)
        return

    payload = {
        "_meta": {
            "last_updated": date.today().isoformat(),
            "staleness_days": 180,
            "description": (
                "Top 1,000 global downhill ski resorts ranked by deterministic size_score "
                "(lifts, downhill km, vertical), with hemisphere/seasonality, multi-resort pass "
                "affiliations, approximate 1-day lift ticket price_tier ($ <$70, $$ $70-120, "
                "$$$ $120-200, $$$$ $200+), and crow-flies distances to nearest commercial airports."
            ),
            "source": "OpenSkiData (https://openskidata.org, ODbL), OurAirports (https://ourairports.com, Public Domain)",
            "license": "ODbL",
            "schema_notes": {
                "crow_flies_km": "Great-circle (haversine) straight-line distance in km, NOT driving distance",
                "crow_flies_mi": "Great-circle (haversine) straight-line distance in miles, NOT driving distance",
                "size_score": "Integer composite: lift_count * 10 + run_km * 2 + vertical_m // 25",
            },
        },
        "resorts": resorts,
    }

    out_path = DATA_DIR / "ski-resorts.json"
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    size_kb = out_path.stat().st_size // 1024
    print(f"Wrote {out_path} ({size_kb} KB).", file=sys.stderr)


if __name__ == "__main__":
    main()

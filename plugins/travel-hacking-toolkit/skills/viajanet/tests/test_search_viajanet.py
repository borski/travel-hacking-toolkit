#!/usr/bin/env python3
"""Unit tests for the viajanet skill's pure logic.

The `patchright` import in search_viajanet.py is lazy (inside `search()`), so
importing the module is safe without a browser.

Run:
    python3 -m unittest discover -s skills/viajanet/tests
"""

import importlib.util
import unittest
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "search_viajanet.py"
_spec = importlib.util.spec_from_file_location("search_viajanet", _SCRIPT)
vn = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vn)


def _seg(frm, dep, to, arr, flight):
    return {
        "departure": {"airportCode": frm, "date": dep},
        "arrival": {"airportCode": to, "date": arr},
        "flightId": flight,
    }


NO_CHECKED_BAG = {
    "quantity": 0, "baggageInfoType": "NOT_INCLUDED_WITH_UPSELLING",
    "backpackType": "INCLUDED", "carryonType": "NOT_INCLUDED",
}


def _route(segs, total, stops, bags):
    return {
        "segments": segs,
        "departure": segs[0]["departure"], "arrival": segs[-1]["arrival"],
        "airlines": ["DM"], "stopsCount": stops, "totalDuration": total,
        "baggageInfo": bags,
    }


# Trimmed from a live GRU-YYZ ViajaNet response (Arajet via PUJ, 2027-10-01 / 2027-10-16).
SEARCH = {
    "items": [
        {"item": {
            "validatingCarrier": "DM",
            "airlines": ["DM"],
            "clusterType": "VIRTUAL_INTERLINING_2OW",
            "priceDetail": {
                "currencyCode": "BRL",
                "mainFare": {"amount": 3540},
                "items": [
                    {"type": "ADULTS", "amount": 1230},
                    {"type": "TAXES_AND_CHARGES", "amount": 2310},
                ],
            },
            "routeChoices": [
                {"type": "OUTBOUND", "selectedRouteIndex": 1, "routes": [_route([
                    _seg("GRU", "2027-10-01T23:55:00-03:00", "PUJ", "2027-10-02T06:00:00-04:00", "DM6021"),
                    _seg("PUJ", "2027-10-02T07:10:00-04:00", "YYZ", "2027-10-02T11:40:00-04:00", "DM5802"),
                ], "12:45", 1, NO_CHECKED_BAG)]},
                {"type": "INBOUND", "routes": [_route([
                    _seg("YYZ", "2027-10-16T12:40:00-04:00", "PUJ", "2027-10-16T17:00:00-04:00", "DM5803"),
                    _seg("PUJ", "2027-10-16T19:00:00-04:00", "GRU", "2027-10-17T03:10:00-03:00", "DM6086"),
                ], "13:30", 1, NO_CHECKED_BAG)]},
            ],
        }},
        {"item": {
            "validatingCarrier": "AC", "airlines": ["AC"], "clusterType": "",
            "priceDetail": {"currencyCode": "BRL", "mainFare": {"amount": 9050}, "items": []},
            "routeChoices": [{"type": "OUTBOUND", "routes": [_route([
                _seg("GRU", "2027-10-01T21:35:00-03:00", "YYZ", "2027-10-02T06:40:00-04:00", "AC91"),
            ], "10:05", 0, {"quantity": 1, "carryonType": "INCLUDED", "backpackType": "INCLUDED"})]}],
        }},
        {"item": {"priceDetail": {}}},
    ]
}


class BuildUrlTests(unittest.TestCase):
    def test_round_trip(self):
        self.assertEqual(
            vn.build_results_url("viajanet", "GRU", "YYZ", "2027-10-01", "2027-10-16", 2, 0, 1),
            "https://www.viajanet.com.br/shop/flights/results/roundtrip/GRU/YYZ/2027-10-01/2027-10-16/2/0/1",
        )

    def test_one_way_on_decolar(self):
        self.assertEqual(
            vn.build_results_url("decolar", "GRU", "YYZ", "2027-10-01"),
            "https://www.decolar.com/shop/flights/results/oneway/GRU/YYZ/2027-10-01/1/0/0",
        )


class ValidationTests(unittest.TestCase):
    def test_iata(self):
        self.assertEqual(vn.validate_iata("yyz"), "YYZ")
        with self.assertRaises(ValueError):
            vn.validate_iata("TORONTO")

    def test_date(self):
        with self.assertRaises(ValueError):
            vn.validate_date("01/10/2027")


class ParseSearchTests(unittest.TestCase):
    def setUp(self):
        self.rows = vn.parse_search(SEARCH)

    def test_sorted_and_skips_unpriced(self):
        self.assertEqual([r["totalBRL"] for r in self.rows], [3540, 9050])

    def test_price_breakdown(self):
        row = self.rows[0]
        self.assertEqual(row["fareBRL"], 1230)
        self.assertEqual(row["taxesBRL"], 2310)
        self.assertEqual(row["validatingCarrier"], "DM")

    def test_separate_tickets_flagged(self):
        self.assertTrue(self.rows[0]["separateTickets"])
        self.assertFalse(self.rows[1]["separateTickets"])

    def test_legs(self):
        out, back = self.rows[0]["outbound"], self.rows[0]["inbound"]
        self.assertEqual(out["departure"], "2027-10-01 23:55")
        self.assertEqual(out["via"], ["PUJ"])
        self.assertEqual(out["flights"], ["DM6021", "DM5802"])
        self.assertEqual(back["arrival"], "2027-10-17 03:10")
        self.assertIsNone(self.rows[1]["inbound"])

    def test_bags(self):
        self.assertEqual(self.rows[0]["outbound"]["bags"], {
            "checked": 0, "carryOn": False, "personalItem": True, "checkedPurchasable": True,
        })
        self.assertEqual(self.rows[1]["outbound"]["bags"]["checked"], 1)

    def test_empty(self):
        self.assertEqual(vn.parse_search({}), [])
        self.assertEqual(vn.parse_search(None), [])


class BlockMarkerTests(unittest.TestCase):
    def test_markers(self):
        self.assertTrue(vn.text_has_block_marker("Access Denied"))
        self.assertFalse(vn.text_has_block_marker("Passagens aéreas"))


if __name__ == "__main__":
    unittest.main()

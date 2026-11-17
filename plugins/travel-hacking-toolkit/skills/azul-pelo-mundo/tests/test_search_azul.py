#!/usr/bin/env python3
"""Unit tests for the azul-pelo-mundo skill's pure logic.

The `patchright` import in search_azul.py is lazy (inside `search()`), so
importing the module is safe without a browser.

Run:
    python3 -m unittest discover -s skills/azul-pelo-mundo/tests
"""

import importlib.util
import unittest
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "search_azul.py"
_spec = importlib.util.spec_from_file_location("search_azul", _SCRIPT)
azul = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(azul)


def _group(num, orig, dest, carrier="TP"):
    return {
        "flightNumber": num, "origin": orig, "destination": dest,
        "departureDate": "10/03/2027", "departureTime": "16:20",
        "arrivalDate": "11/03/2027", "arrivalTime": "05:15",
        "marketingCarrier": carrier, "operatingCarrier": carrier,
    }


# Trimmed from a live GRU-LIS round-trip response (2027-03-10 / 2027-03-24).
ROUND_TRIP = {
    "data": {
        "departureFlights": {"flights": [{
            "id": 14, "departureDate": "10/03/2027", "departureTime": "16:20",
            "finalArrivalDate": "11/03/2027", "finalArrivalTime": "05:15",
            "operatingCarriers": ["TP"], "marketingCarrier": "TP",
            "connection": 0, "elapsedFlightTime": "0955", "fareOriginType": "PUBLIC",
            "baggage": [{"quantity": 0}], "hasLowAvailability": False,
            "points": {"value": 203000},
            "prices": [
                {"passenger": "ADULT", "value": 2735.79},
                {"passenger": "INFANT", "value": 270.74},
            ],
            "ranges": [{"points": 162500, "amount": 620, "level": 1}],
            "recommendations": [{"returnFlights": [{"id": 14, "categories": [{
                "prices": [
                    {"passenger": "ADULT", "value": 3331.87},
                    {"passenger": "INFANT", "value": 329.74},
                ],
                "points": {"value": 247000},
                "ranges": [{"points": 198000, "amount": 755, "level": 1}],
                "fee": {"total": {"value": 629.22}},
                "baggageRule": {"quantity": 0},
            }]}]}],
            "flightGroup": [_group(82, "GRU", "LIS")],
        }]},
        "returnFlights": {"flights": [{
            "id": 14, "departureDate": "24/03/2027", "departureTime": "12:20",
            "finalArrivalDate": "24/03/2027", "finalArrivalTime": "18:35",
            "flightGroup": [_group(87, "LIS", "GRU")],
        }]},
    }
}

# Trimmed from a live GRU-IND one-way United award response.
ONE_WAY_AWARD = {
    "data": {
        "departureFlights": {"flights": [
            {
                "id": 9, "departureDate": "21/11/2026", "departureTime": "22:25",
                "finalArrivalDate": "22/11/2026", "finalArrivalTime": "10:20",
                "operatingCarriers": ["UA"], "marketingCarrier": "UA",
                "connection": 1, "fareOriginType": "AWARD",
                "baggage": [{"quantity": 1}],
                "prices": [{"passenger": "ADULT", "value": 0.0}],
                "points": {"value": 122000},
                "ranges": [{"points": 98000, "amount": 375}, {"points": None, "amount": 1}],
                "recommendations": [{"returnFlights": None, "fee": {"total": {"value": 350.32}}}],
                "flightGroup": [_group(860, "GRU", "IAD", "UA"), _group(3561, "IAD", "IND", "UA")],
            },
            {
                "id": 10, "operatingCarriers": ["UA"], "connection": 1,
                "points": {"value": 99000}, "prices": [],
                "recommendations": [{"fee": {"total": {"value": 300.0}}}],
                "flightGroup": [],
            },
            {"id": 11, "points": {"value": None}, "flightGroup": []},
        ]},
    }
}


class BuildUrlTests(unittest.TestCase):
    def test_round_trip_url(self):
        url = azul.build_results_url("GRU", "LIS", "2027-03-10", "2027-03-24", 2, 0, 1)
        self.assertEqual(
            url,
            "https://azulpelomundo.voeazul.com.br/flights/RT/GRU/LIS/-/-/"
            "2027-03-10/2027-03-24/2/0/1/0/0/ALL/F/ECONOMY/-/-/-/-/A/-",
        )

    def test_one_way_url(self):
        url = azul.build_results_url("GRU", "IND", "2026-11-21", None, 1, 1, 0)
        self.assertIn("/flights/OW/GRU/IND/-/-/2026-11-21/-/1/1/0/", url)


class ValidationTests(unittest.TestCase):
    def test_iata(self):
        self.assertEqual(azul.validate_iata(" gru "), "GRU")
        with self.assertRaises(ValueError):
            azul.validate_iata("GRUU")

    def test_date(self):
        self.assertEqual(azul.validate_date("2027-03-10"), "2027-03-10")
        with self.assertRaises(ValueError):
            azul.validate_date("10/03/2027")


class BlockMarkerTests(unittest.TestCase):
    def test_recaptcha_message_is_block(self):
        self.assertTrue(azul.text_has_block_marker('{"description":"reCAPTCHA token is required"}'))

    def test_normal_page_is_not_block(self):
        self.assertFalse(azul.text_has_block_marker("Selecione o voo de ida"))
        self.assertFalse(azul.text_has_block_marker(""))


class ParseRoundTripTests(unittest.TestCase):
    def setUp(self):
        self.rows = azul.parse_availability(ROUND_TRIP)

    def test_round_trip_sums_both_legs(self):
        self.assertEqual(len(self.rows), 1)
        row = self.rows[0]
        self.assertEqual(row["tripType"], "ROUND_TRIP")
        self.assertEqual(row["outboundPoints"], 203000)
        self.assertEqual(row["returnPoints"], 247000)
        self.assertEqual(row["points"], 450000)
        self.assertEqual(row["feesBRL"], 629.22)
        self.assertEqual(row["cashFareBRL"]["ADULT"], 6067.66)
        self.assertEqual(row["cashFareBRL"]["INFANT"], 600.48)
        self.assertEqual(row["pointsPlusCash"], {
            "outbound": [{"points": 162500, "cashBRL": 620}],
            "return": [{"points": 198000, "cashBRL": 755}],
        })

    def test_inbound_is_linked(self):
        inbound = self.rows[0]["inbound"]
        self.assertEqual(inbound["departure"], "24/03/2027 12:20")
        self.assertEqual(inbound["segments"][0]["flight"], "TP87")

    def test_cents_per_point(self):
        self.assertEqual(azul.cents_per_point(self.rows[0]), 1.35)


class ParseOneWayTests(unittest.TestCase):
    def setUp(self):
        self.rows = azul.parse_availability(ONE_WAY_AWARD)

    def test_drops_rows_without_points_and_sorts(self):
        self.assertEqual([r["points"] for r in self.rows], [99000, 122000])

    def test_award_row_fields(self):
        row = self.rows[1]
        self.assertEqual(row["tripType"], "ONE_WAY")
        self.assertEqual(row["fareType"], "AWARD")
        self.assertEqual(row["feesBRL"], 350.32)
        self.assertEqual(row["stops"], 1)
        self.assertEqual(row["checkedBags"], 1)
        self.assertEqual([s["flight"] for s in row["outbound"]["segments"]], ["UA860", "UA3561"])
        self.assertEqual(row["pointsPlusCash"], [{"points": 98000, "cashBRL": 375}])

    def test_award_has_no_cash_comparison(self):
        self.assertIsNone(azul.cents_per_point(self.rows[1]))

    def test_empty_payload(self):
        self.assertEqual(azul.parse_availability({}), [])
        self.assertEqual(azul.parse_availability(None), [])


if __name__ == "__main__":
    unittest.main()

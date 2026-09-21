#!/usr/bin/env python3
"""Offline unit tests for amex-travel form-filling logic.

The `patchright` import in search_flights.py is lazy (inside the browser
functions), so importing the module is safe. These tests exercise the pure
control flow of the May-2026 UI fixes with a fake page/element — no browser.

Run:
    python3 -m unittest discover -s skills/amex-travel/tests
"""

import importlib.util
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPT = os.path.join(_HERE, "..", "scripts", "search_flights.py")
_spec = importlib.util.spec_from_file_location("amex_search_flights", _SCRIPT)
sf = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sf)


class FakeElement:
    def __init__(self, *, visible=True, select_raises=False):
        self._visible = visible
        self._select_raises = select_raises
        self.clicked = False
        self.selected = None

    def is_visible(self):
        return self._visible

    def click(self):
        self.clicked = True

    def type(self, text, delay=0):
        pass

    def select_option(self, value, timeout=0):
        if self._select_raises:
            raise Exception("Element is not a <select> element")
        self.selected = value


class FakeKeyboard:
    def __init__(self):
        self.pressed = []

    def press(self, key):
        self.pressed.append(key)


class FakePage:
    """query_selector consults `handlers`: a list of (predicate, element).
    First predicate whose `substr` is in the selector string wins."""

    def __init__(self, handlers):
        self.handlers = handlers  # list of (substr, element)
        self.keyboard = FakeKeyboard()
        self.wait_selector_calls = []

    def query_selector(self, selector):
        for substr, el in self.handlers:
            if substr in selector:
                return el
        return None

    def wait_for_timeout(self, ms):
        pass

    def wait_for_selector(self, selector, state=None, timeout=0):
        self.wait_selector_calls.append(selector)
        return object()

    def evaluate(self, *args, **kwargs):
        pass


class SetCabinTests(unittest.TestCase):
    def test_native_select_path(self):
        el = FakeElement(select_raises=False)
        page = FakePage([("flight-class-dropdown", el)])
        self.assertTrue(sf._set_cabin(page, "Business", "BUSINESS"))
        self.assertEqual(el.selected, "BUSINESS")  # used native select
        self.assertFalse(el.clicked)               # did not need the click path

    def test_custom_component_click_fallback(self):
        trigger = FakeElement(select_raises=True)   # not a native <select>
        option = FakeElement(visible=True)
        # trigger matches the dropdown selector; option matches has-text("Business")
        page = FakePage([("flight-class-dropdown", trigger), ('has-text("Business")', option)])
        self.assertTrue(sf._set_cabin(page, "Business", "BUSINESS"))
        self.assertTrue(trigger.clicked)   # opened the custom dropdown
        self.assertTrue(option.clicked)    # clicked the matching option

    def test_missing_dropdown_returns_false(self):
        page = FakePage([])  # nothing matches
        self.assertFalse(sf._set_cabin(page, "Business", "BUSINESS"))


class FillAirportFieldTests(unittest.TestCase):
    def test_clicks_option_not_enter(self):
        inp = FakeElement(visible=True)
        option = FakeElement(visible=True)
        # input matches the given selector; option matches listbox/option selectors
        page = FakePage([("locationsInput", inp), ('role="option"', option)])
        self.assertTrue(sf._fill_airport_field(page, 'input[id*="locationsInput_departure"]', "SFO"))
        self.assertTrue(option.clicked)          # clicked the autocomplete option
        self.assertEqual(page.keyboard.pressed, [])  # did NOT fall back to Enter

    def test_enter_fallback_when_no_option(self):
        inp = FakeElement(visible=True)
        page = FakePage([("locationsInput", inp)])  # no option element present
        self.assertTrue(sf._fill_airport_field(page, 'input[id*="locationsInput_departure"]', "SFO"))
        self.assertEqual(page.keyboard.pressed, ["Enter"])  # last-resort Enter


class RaisingPage(FakePage):
    def query_selector(self, selector):
        raise Exception("page crashed")


class CaptchaDetectionTests(unittest.TestCase):
    def test_detects_captcha_marker(self):
        page = FakePage([("captcha", FakeElement())])
        self.assertTrue(sf._captcha_present(page))

    def test_no_captcha(self):
        page = FakePage([])
        self.assertFalse(sf._captcha_present(page))

    def test_page_error_is_not_a_captcha(self):
        self.assertFalse(sf._captcha_present(RaisingPage([])))

    def test_sentinel_printed_on_stdout(self):
        import contextlib
        import io

        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            sf._emit_human_login_needed("captcha on the travel portal login gate")
        self.assertIn("AMEX_HUMAN_LOGIN_NEEDED", out.getvalue())


# Real card maps captured live from the new travel.americanexpress.com
# results page (July 2026), trimmed to the fields the interpreter reads.
ALASKA_INSIDER_CARD = {
    "flight-route-container": "Economy Flight type Flight length 1 hour 31 minutes",
    "offer-card-stop": "Non stop Non-stop",
    "offer-card-flight-duration": "1h 31m",
    "AS-airline-img": "Airline company",
    "Alaska Airlines, Inc.-airline-code": "Alaska Airlines, Inc.",
    "departure-date": "3:51 pm",
    "SFO-departure-airport-code": "SFO",
    "arrival-data": "5:22 pm",
    "LAX-arrival-airport-code": "LAX",
    "flight-average-price": "Total Price From 11,441*",
    "departure-selection-flight-total-price": "was",
    "offer-card-insider-fares": "$125.40",
    "departure-selection-flight-total-price-points": (
        "or was 12,540 points, now it's 11,441, *, footnote Membership Rewards points"
    ),
    "offer-card-strike-through": "12,540",
}

DELTA_IAP_CARD = {
    "private-fare-banner-PEP12,EXP20-program-subheader": (
        "Enjoy special access to Platinum Member Airfares through Amex Travel."
    ),
    "offer-card-stop": "Non stop Non-stop",
    "offer-card-flight-duration": "1h 32m",
    "DL-airline-img": "Airline company",
    "Delta Air Lines-airline-code": "Delta Air Lines",
    "departure-date": "11:54 am",
    "SFO-departure-airport-code": "SFO",
    "arrival-data": "1:26 pm",
    "LAX-arrival-airport-code": "LAX",
    "flight-average-price": "Total Price From $121.01 12,101",
    "departure-selection-flight-total-price": "It was $125.40 now it's $121.01 One Way Total",
    "offer-card-strike-through": "$125.40 12,540",
}


class OfferCardInterpreterTests(unittest.TestCase):
    def test_alaska_insider_fare(self):
        f = sf._interpret_offer_card(ALASKA_INSIDER_CARD)
        self.assertEqual(f["airline"], "Alaska Airlines, Inc.")
        self.assertEqual(f["segments"][0]["origin"], "SFO")
        self.assertEqual(f["segments"][0]["destination"], "LAX")
        self.assertEqual(f["segments"][0]["airline_code"], "AS")
        self.assertEqual(f["stops"], 0)
        self.assertEqual(f["cash_usd"], 125.40)
        self.assertEqual(f["points"], 11441)          # discounted insider points
        self.assertTrue(f["insider_fare"])
        self.assertTrue(f["points_discount"])          # 12,540 -> 11,441
        self.assertFalse(f["has_iap"])                 # no cash discount = not IAP

    def test_delta_iap_fare(self):
        f = sf._interpret_offer_card(DELTA_IAP_CARD)
        self.assertEqual(f["airline"], "Delta Air Lines")
        self.assertTrue(f["has_iap"])
        self.assertEqual(f["cash_usd"], 121.01)        # IAP (PEP) price
        self.assertEqual(f["pricing"]["PUB"]["cash_usd"], 125.40)
        self.assertEqual(f["pricing"]["PEP"]["cash_usd"], 121.01)
        self.assertEqual(f["points"], 12101)
        self.assertEqual(f["duration"], "1h 32m")

    def test_sparse_card_does_not_crash(self):
        f = sf._interpret_offer_card({"offer-card-flight-duration": "2h 5m"})
        self.assertEqual(f["cash_usd"], 0)
        self.assertEqual(f["points"], 0)
        self.assertEqual(f["stops"], 0)
        self.assertFalse(f["has_iap"])


class CredentialGuardTests(unittest.TestCase):
    def test_unresolved_secret_reference(self):
        self.assertTrue(sf._unresolved_secret("secret://Vault/item/username"))
        self.assertTrue(sf._unresolved_secret('"vault://item/username"'))
        self.assertFalse(sf._unresolved_secret("actual_username"))
        self.assertFalse(sf._unresolved_secret(""))
        self.assertFalse(sf._unresolved_secret(None))

    def test_sentinel_printed_on_stdout(self):
        import contextlib
        import io

        out = io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            sf._emit_bad_credentials("AMEX_USERNAME is an unresolved secret reference")
        self.assertIn("AMEX_BAD_CREDENTIALS", out.getvalue())


class HotelTextFallbackTests(unittest.TestCase):
    """The raw-text hotel parser used when no structured cards are found."""

    def test_parses_a_hotel_block(self):
        text = (
            "$1,250.00 per night\n"
            "Hotel Bel-Air\n"
            "Fine Hotels + Resorts\n"
            "12,500 points\n"
            "Complimentary breakfast for two\n"
        )
        hotels = sf._parse_hotels_from_text(text)
        self.assertEqual(len(hotels), 1)
        hotel = hotels[0]
        self.assertEqual(hotel["name"], "Hotel Bel-Air")
        self.assertTrue(hotel["is_fhr"])
        self.assertEqual(hotel["price_usd"], 1250.0)
        self.assertEqual(hotel["points"], 12500)
        self.assertEqual(hotel["benefits"], ["Complimentary breakfast for two"])

    def test_block_without_pricing_is_skipped(self):
        self.assertEqual(sf._parse_hotels_from_text("Some Hotel\n"), [])


if __name__ == "__main__":
    unittest.main()

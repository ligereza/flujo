import unittest
from flujo.rd.panel import _norm_link_value, _venue_link_key


class TestNormLinkValue(unittest.TestCase):
    def test_normalize_accents(self):
        self.assertEqual(_norm_link_value("Teatro Ñuñoa"), "teatro nunoa")

    def test_normalize_empty_string(self):
        self.assertEqual(_norm_link_value(""), "")

    def test_normalize_none(self):
        self.assertEqual(_norm_link_value(None), "")

    def test_normalize_special_characters(self):
        self.assertEqual(_norm_link_value("Café-concierto!"), "cafe concierto")

    def test_normalize_multiple_spaces(self):
        self.assertEqual(_norm_link_value("  Casa  Blanca  "), "casa blanca")


class TestVenueLinkKey(unittest.TestCase):
    def test_empty_string(self):
        self.assertEqual(_venue_link_key(""), "")

    def test_none_value(self):
        self.assertEqual(_venue_link_key(None), "")

    def test_needs_confirmation_returns_empty(self):
        self.assertEqual(_venue_link_key("needs_confirmation"), "")
        self.assertEqual(_venue_link_key("Needs_Confirmation"), "")

    def test_removes_double_dash_annotation(self):
        self.assertEqual(
            _venue_link_key("Teatro Caupolicán -- confirmado por el usuario"),
            "teatro caupolican"
        )

    def test_removes_parentheses(self):
        self.assertEqual(
            _venue_link_key("Movistar Arena (confirmado)"),
            "movistar arena"
        )

    def test_removes_chile_suffix(self):
        self.assertEqual(
            _venue_link_key("Movistar Arena chile"),
            "movistar arena"
        )

    def test_removes_chile_suffix_with_leading_annotation(self):
        self.assertEqual(
            _venue_link_key("Teatro Caupolicán -- confirmado por el usuario chile"),
            "teatro caupolican"
        )

    def test_accents_removed(self):
        self.assertEqual(_venue_link_key("Teatro Ñuñoa"), "teatro nunoa")

    def test_combined_normalization(self):
        self.assertEqual(
            _venue_link_key("Teatro Ñuñoa -- confirmado por el usuario (Santiago) Chile"),
            "teatro nunoa"
        )


if __name__ == "__main__":
    unittest.main()

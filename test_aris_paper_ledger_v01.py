#!/usr/bin/env python3
import unittest

from aris_paper_ledger_v01 import validate_cycle


def valid_cycle():
    return {
        "profit_percent": 0.5,
        "paper_start_units": 100.0,
        "paper_end_units": 100.5,
        "executable": True,
        "capacity_verified": True,
        "quote_synchronized": True,
        "quotes_fresh": True,
        "contains_transfer": False,
        "paper_legs": [
            {"within_top_of_book_capacity": True, "within_capacity_buffer": True},
            {"within_top_of_book_capacity": True, "within_capacity_buffer": True},
            {"within_top_of_book_capacity": True, "within_capacity_buffer": True},
        ],
    }


class PaperLedgerValidationTests(unittest.TestCase):
    def test_accepts_consistent_executable_cycle(self):
        self.assertEqual(validate_cycle(valid_cycle()), (True, "validated"))

    def test_rejects_profit_mismatch(self):
        cycle = valid_cycle()
        cycle["paper_end_units"] = 100.4
        self.assertEqual(validate_cycle(cycle), (False, "profit_mismatch"))

    def test_rejects_stale_quotes(self):
        cycle = valid_cycle()
        cycle["quotes_fresh"] = False
        self.assertEqual(validate_cycle(cycle), (False, "quotes_fresh"))

    def test_rejects_excessive_book_utilization(self):
        cycle = valid_cycle()
        cycle["paper_legs"][1]["within_capacity_buffer"] = False
        self.assertEqual(validate_cycle(cycle), (False, "leg_capacity_buffer"))

    def test_rejects_insufficient_leg_capacity(self):
        cycle = valid_cycle()
        cycle["paper_legs"][1]["within_top_of_book_capacity"] = False
        self.assertEqual(validate_cycle(cycle), (False, "leg_capacity"))


if __name__ == "__main__":
    unittest.main()

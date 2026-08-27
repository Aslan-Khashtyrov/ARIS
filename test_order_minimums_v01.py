#!/usr/bin/env python3
import unittest

from aris_cycle_engine_v01 import simulate_route
from aris_paper_ledger_v01 import validate_cycle


def edge(minimum):
    return {
        "kind": "TRADE",
        "exchange": "test",
        "pair": "BTC/USDT",
        "src": "test:USDT",
        "dst": "test:BTC",
        "side": "BUY",
        "rate": 0.01,
        "capacity_src": 1000.0,
        "minimum_src": minimum,
        "min_base": 0.0001,
        "min_quote": minimum,
        "qty_step": 0.0001,
    }


def paper_cycle(minimum_order_met=True):
    start, end = 100.0, 100.4
    leg = {
        "within_top_of_book_capacity": True,
        "within_capacity_buffer": True,
        "minimum_order_met": minimum_order_met,
    }
    return {
        "profit_percent": (end / start - 1.0) * 100.0,
        "paper_start_units": start,
        "paper_end_units": end,
        "executable": True,
        "capacity_verified": True,
        "minimum_order_verified": minimum_order_met,
        "quote_synchronized": True,
        "quotes_fresh": True,
        "contains_transfer": False,
        "paper_legs": [dict(leg) for _ in range(3)],
    }


class MinimumOrderTests(unittest.TestCase):
    def test_exact_exchange_minimum_is_allowed(self):
        result = simulate_route(10.0, [edge(10.0)])
        self.assertTrue(result["minimum_order_verified"])
        self.assertTrue(result["legs"][0]["minimum_order_met"])

    def test_below_exchange_minimum_is_rejected(self):
        result = simulate_route(9.99, [edge(10.0)])
        self.assertFalse(result["minimum_order_verified"])
        self.assertFalse(result["legs"][0]["minimum_order_met"])

    def test_paper_ledger_accepts_verified_minimums(self):
        self.assertEqual(validate_cycle(paper_cycle()), (True, "validated"))

    def test_paper_ledger_rejects_unverified_minimums(self):
        valid, reason = validate_cycle(paper_cycle(False))
        self.assertFalse(valid)
        self.assertEqual(reason, "minimum_order_verified")


if __name__ == "__main__":
    unittest.main()

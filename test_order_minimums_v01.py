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
        "order_price": 100.0,
    }


def paper_cycle(minimum_order_met=True, quantity_step_verified=True):
    start, end = 100.0, 100.4
    leg = {
        "within_top_of_book_capacity": True,
        "within_capacity_buffer": True,
        "minimum_order_met": minimum_order_met,
        "quantity_step_verified": quantity_step_verified,
    }
    return {
        "profit_percent": (end / start - 1.0) * 100.0,
        "paper_start_units": start,
        "paper_end_units": end,
        "executable": True,
        "capacity_verified": True,
        "minimum_order_verified": minimum_order_met,
        "quantity_step_verified": quantity_step_verified,
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

    def test_quantity_is_rounded_down_to_exchange_step(self):
        rounded_edge = {
            "kind": "TRADE",
            "exchange": "binance",
            "pair": "BTC/USDT",
            "src": "binance:BTC",
            "dst": "binance:USDT",
            "side": "SELL",
            "rate": 1.0,
            "capacity_src": 100.0,
            "minimum_src": 0.0,
            "min_base": 0.0,
            "min_quote": 0.0,
            "qty_step": 0.1,
            "order_price": 1.0,
        }
        result = simulate_route(1.09, [rounded_edge])
        leg = result["legs"][0]
        self.assertAlmostEqual(leg["amount_submitted"], 1.0)
        self.assertAlmostEqual(leg["unspent_source_units"], 0.09)
        self.assertAlmostEqual(result["end_units_before_buffer"], 1.0)
        self.assertTrue(result["quantity_step_verified"])

    def test_paper_ledger_accepts_verified_minimums(self):
        self.assertEqual(validate_cycle(paper_cycle()), (True, "validated"))

    def test_paper_ledger_rejects_unverified_step(self):
        valid, reason = validate_cycle(paper_cycle(quantity_step_verified=False))
        self.assertFalse(valid)
        self.assertEqual(reason, "quantity_step_verified")

    def test_paper_ledger_rejects_unverified_minimums(self):
        valid, reason = validate_cycle(paper_cycle(False))
        self.assertFalse(valid)
        self.assertEqual(reason, "minimum_order_verified")


if __name__ == "__main__":
    unittest.main()

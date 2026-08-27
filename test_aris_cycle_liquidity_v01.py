#!/usr/bin/env python3
import unittest

from aris_cycle_engine_v01 import MAX_BOOK_UTILIZATION_PERCENT, simulate_route


def route(capacity=100.0):
    return [
        {"kind": "TRADE", "exchange": "test", "pair": "A/B", "side": "SELL", "src": "test:A", "dst": "test:B", "rate": 1.0, "capacity_src": capacity},
        {"kind": "TRADE", "exchange": "test", "pair": "B/C", "side": "SELL", "src": "test:B", "dst": "test:C", "rate": 1.0, "capacity_src": capacity},
        {"kind": "TRADE", "exchange": "test", "pair": "C/A", "side": "SELL", "src": "test:C", "dst": "test:A", "rate": 1.0, "capacity_src": capacity},
    ]


class CycleLiquidityBufferTests(unittest.TestCase):
    def test_threshold_is_conservative(self):
        self.assertEqual(MAX_BOOK_UTILIZATION_PERCENT, 80.0)

    def test_accepts_exactly_eighty_percent(self):
        result = simulate_route(80.0, route())
        self.assertTrue(result["capacity_verified"])
        self.assertTrue(all(leg["within_capacity_buffer"] for leg in result["legs"]))

    def test_rejects_above_eighty_percent(self):
        result = simulate_route(80.01, route())
        self.assertFalse(result["capacity_verified"])
        self.assertTrue(all(leg["within_top_of_book_capacity"] for leg in result["legs"]))
        self.assertFalse(result["legs"][0]["within_capacity_buffer"])

    def test_reports_headroom(self):
        result = simulate_route(25.0, route())
        self.assertAlmostEqual(result["legs"][0]["capacity_headroom_percent"], 75.0)


if __name__ == "__main__":
    unittest.main()

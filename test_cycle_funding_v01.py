#!/usr/bin/env python3
import unittest

import aris_cycle_collector_v01 as collector


class CycleFundingTests(unittest.TestCase):
    def test_explicit_start_is_used(self):
        cycle = {"start": "binance:USDT", "route": [{"src": "binance:BTC"}]}
        self.assertEqual(collector.cycle_wallet(cycle), "binance:USDT")

    def test_first_leg_fallback_is_used(self):
        cycle = {"route": [{"src": "okx:USDT"}]}
        self.assertEqual(collector.cycle_wallet(cycle), "okx:USDT")

    def test_only_funded_start_is_eligible(self):
        funded = {"binance:USDT", "bybit:USDT", "okx:USDT"}
        self.assertTrue(collector.is_paper_funded({"start": "bybit:USDT"}, funded))
        self.assertFalse(collector.is_paper_funded({"start": "okx:BTC"}, funded))
        self.assertFalse(collector.is_paper_funded({"start": "okx:USD"}, funded))


if __name__ == "__main__":
    unittest.main()

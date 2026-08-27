#!/usr/bin/env python3
import unittest

import aris_cycle_collector_v01 as collector


class MarketUniverseTests(unittest.TestCase):
    def test_core_exchanges_are_monitored(self):
        self.assertEqual(set(collector.health), {"binance", "bybit", "okx", "coinbase", "kraken"})

    def test_expanded_assets_are_enabled(self):
        required = {"BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "AVAX", "DOT", "LINK", "LTC", "BCH", "TRX"}
        self.assertTrue(required.issubset(collector.UNIVERSE))

    def test_multiple_quote_currencies_are_enabled(self):
        required = {"USD", "USDT", "USDC", "EUR", "GBP", "DAI", "FDUSD"}
        self.assertTrue(required.issubset(collector.UNIVERSE))


if __name__ == "__main__":
    unittest.main()

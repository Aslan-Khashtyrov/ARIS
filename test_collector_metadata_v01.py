#!/usr/bin/env python3
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import aris_cycle_collector_v01 as collector


class PublicProductMetadataTests(unittest.TestCase):
    def test_bybit_spot_uses_base_precision_as_quantity_step(self):
        payload = {
            "result": {
                "list": [{
                    "symbol": "BTCUSDT",
                    "baseCoin": "BTC",
                    "quoteCoin": "USDT",
                    "status": "Trading",
                    "lotSizeFilter": {
                        "minOrderQty": "0.00001",
                        "minOrderAmt": "5",
                        "basePrecision": "0.000001",
                    },
                }]
            }
        }
        with patch.object(collector, "request_json", return_value=payload):
            product = collector.discover_bybit()["BTCUSDT"]
        self.assertEqual(float(product["qty_step"]), 0.000001)
        self.assertEqual(float(product["min_quote"]), 5.0)

    def test_bybit_recovers_public_filters_from_last_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot = root / "quotes.json"
            cache = root / "cache.json"
            snapshot.write_text(json.dumps({
                "quotes": [{
                    "exchange": "bybit",
                    "symbol": "BTCUSDT",
                    "base": "BTC",
                    "quote": "USDT",
                    "min_base": 0.00001,
                    "min_quote": 5.0,
                    "qty_step": 0.000001,
                }]
            }), encoding="utf-8")
            with (
                patch.object(collector, "SNAPSHOT", snapshot),
                patch.object(collector, "BYBIT_PRODUCTS_CACHE", cache),
                patch.object(collector, "request_json", side_effect=OSError("network unavailable")),
            ):
                product = collector.discover_bybit()["BTCUSDT"]
            self.assertEqual(product["filter_source"], "BYBIT_LAST_PUBLIC_SNAPSHOT")
            self.assertTrue(cache.exists())
            self.assertEqual(float(product["qty_step"]), 0.000001)

    def test_okx_recovers_public_filters_from_last_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot = root / "quotes.json"
            cache = root / "cache.json"
            snapshot.write_text(json.dumps({
                "quotes": [{
                    "exchange": "okx",
                    "symbol": "BTC-USDT",
                    "base": "BTC",
                    "quote": "USDT",
                    "min_base": 0.00001,
                    "min_quote": 0.0,
                    "qty_step": 0.00000001,
                }]
            }), encoding="utf-8")
            with (
                patch.object(collector, "SNAPSHOT", snapshot),
                patch.object(collector, "OKX_PRODUCTS_CACHE", cache),
                patch.object(collector, "request_json", side_effect=OSError("network unavailable")),
            ):
                product = collector.discover_okx()["BTC-USDT"]
            self.assertEqual(product["filter_source"], "OKX_LAST_PUBLIC_SNAPSHOT")
            self.assertTrue(cache.exists())
            self.assertEqual(float(product["qty_step"]), 0.00000001)

    def test_binance_recovers_public_filters_from_last_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            snapshot = root / "quotes.json"
            cache = root / "cache.json"
            snapshot.write_text(json.dumps({
                "quotes": [{
                    "exchange": "binance",
                    "symbol": "BTCUSDT",
                    "base": "BTC",
                    "quote": "USDT",
                    "min_base": 0.00001,
                    "min_quote": 5.0,
                    "qty_step": 0.00001,
                }]
            }), encoding="utf-8")
            with (
                patch.object(collector, "SNAPSHOT", snapshot),
                patch.object(collector, "BINANCE_PRODUCTS_CACHE", cache),
                patch.object(collector, "request_json", side_effect=OSError("network unavailable")),
            ):
                product = collector.discover_binance()["BTCUSDT"]
            self.assertEqual(product["filter_source"], "BINANCE_LAST_PUBLIC_SNAPSHOT")
            self.assertTrue(cache.exists())
            self.assertEqual(float(product["qty_step"]), 0.00001)


if __name__ == "__main__":
    unittest.main()

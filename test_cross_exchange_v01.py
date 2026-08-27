#!/usr/bin/env python3
import time
import unittest

from aris_cross_exchange_v01 import analyze


class CrossExchangeTests(unittest.TestCase):
    def test_positive_route_after_fees(self):
        now = time.time()
        payload = {"quotes": [
            {"exchange": "binance", "base": "BTC", "quote": "USDT", "bid": 99.9, "ask": 100.0, "bid_size": 10, "ask_size": 10, "taker_fee": 0.001, "updated_at": now, "qty_step": 0.0001},
            {"exchange": "okx", "base": "BTC", "quote": "USDT", "bid": 100.5, "ask": 100.6, "bid_size": 10, "ask_size": 10, "taker_fee": 0.001, "updated_at": now, "qty_step": 0.0001},
        ]}
        result = analyze(payload, evaluation_time=now)
        self.assertEqual(result["routes_compared"], 2)
        self.assertEqual(result["positive_executable_routes"], 1)
        self.assertGreater(result["best_executable_route"]["net_profit_percent"], 0)

    def test_stale_route_is_not_executable(self):
        now = time.time()
        payload = {"quotes": [
            {"exchange": "binance", "base": "ETH", "quote": "USDT", "bid": 99.9, "ask": 100.0, "bid_size": 10, "ask_size": 10, "taker_fee": 0.001, "updated_at": now - 10},
            {"exchange": "bybit", "base": "ETH", "quote": "USDT", "bid": 101.0, "ask": 101.1, "bid_size": 10, "ask_size": 10, "taker_fee": 0.001, "updated_at": now - 10},
        ]}
        result = analyze(payload, evaluation_time=now)
        self.assertEqual(result["executable_routes"], 0)
        self.assertEqual(result["positive_executable_routes"], 0)

    def test_same_exchange_is_excluded(self):
        now = time.time()
        result = analyze({"quotes": [
            {"exchange": "okx", "base": "SOL", "quote": "USDT", "bid": 100, "ask": 101, "bid_size": 10, "ask_size": 10, "taker_fee": 0.001, "updated_at": now},
        ]}, evaluation_time=now)
        self.assertEqual(result["routes_compared"], 0)


if __name__ == "__main__":
    unittest.main()

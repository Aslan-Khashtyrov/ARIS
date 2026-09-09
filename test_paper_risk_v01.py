#!/usr/bin/env python3
from datetime import datetime
import unittest
from unittest.mock import patch

import aris_paper_ledger_v01 as ledger


def today_stamp(hour="10:00:00"):
    return f"{datetime.now().date().isoformat()}T{hour}"


class PaperRiskTests(unittest.TestCase):
    def test_trade_allocation_limit(self):
        with patch.object(ledger, "RISK_CONTROLS", {
            "maximum_trade_allocation_percent": 25.0,
            "maximum_trades_per_wallet_per_day": 20,
            "maximum_daily_drawdown_percent": 2.0,
        }):
            self.assertIsNone(ledger.risk_rejection([], "binance:USDT", 1000.0, 250.0))
            self.assertEqual(ledger.risk_rejection([], "binance:USDT", 1000.0, 250.01), "maximum_trade_allocation")

    def test_daily_trade_limit(self):
        rows = [{"wallet": "binance:USDT", "recorded_at": today_stamp(), "paper_profit_units": 1.0} for _ in range(20)]
        with patch.object(ledger, "RISK_CONTROLS", {
            "maximum_trade_allocation_percent": 25.0,
            "maximum_trades_per_wallet_per_day": 20,
            "maximum_daily_drawdown_percent": 2.0,
        }):
            with patch.object(ledger, "INITIAL_BALANCES", {"binance:USDT": 1000.0}):
                self.assertEqual(ledger.risk_rejection(rows, "binance:USDT", 1000.0, 100.0), "maximum_daily_trades")

    def test_daily_drawdown_limit(self):
        rows = [{"wallet": "okx:USDT", "recorded_at": today_stamp(), "paper_profit_units": -20.0}]
        with patch.object(ledger, "RISK_CONTROLS", {
            "maximum_trade_allocation_percent": 25.0,
            "maximum_trades_per_wallet_per_day": 20,
            "maximum_daily_drawdown_percent": 2.0,
        }):
            with patch.object(ledger, "INITIAL_BALANCES", {"okx:USDT": 1000.0}):
                self.assertEqual(ledger.risk_rejection(rows, "okx:USDT", 980.0, 100.0), "maximum_daily_drawdown")


if __name__ == "__main__":
    unittest.main()

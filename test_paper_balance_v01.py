#!/usr/bin/env python3
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import aris_paper_ledger_v01 as ledger


class PaperBalanceTests(unittest.TestCase):
    def test_wallet_summary_starts_funded(self):
        summary = ledger.build_summary([], dict(ledger.INITIAL_BALANCES))
        self.assertTrue(summary["wallet"]["enabled"])
        self.assertEqual(summary["wallet"]["equity_by_asset"]["USDT"], 3000.0)
        self.assertEqual(summary["paper_trades"], 0)
        self.assertEqual(summary["profit_by_asset"], {})

    def test_valid_cycle_requires_exact_recomputed_profit(self):
        start = 100.0
        end = 100.4
        cycle = {
            "profit_percent": 0.4,
            "paper_start_units": start,
            "paper_end_units": end,
            "executable": True,
            "capacity_verified": True,
            "minimum_order_verified": True,
            "quantity_step_verified": True,
            "quote_synchronized": True,
            "quotes_fresh": True,
            "contains_transfer": False,
            "paper_legs": [
                {"within_top_of_book_capacity": True, "within_capacity_buffer": True, "minimum_order_met": True, "quantity_step_verified": True}
                for _ in range(3)
            ],
        }
        self.assertEqual(ledger.validate_cycle(cycle), (True, "validated"))
        cycle["profit_percent"] = 0.5
        self.assertEqual(ledger.validate_cycle(cycle), (False, "profit_mismatch"))


    def test_confirmed_cycle_updates_balance_once(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            journal = root / "journal"
            journal.mkdir()
            signals = journal / "signals.jsonl"
            trade_leg = {
                "within_top_of_book_capacity": True,
                "within_capacity_buffer": True,
                "minimum_order_met": True,
                "quantity_step_verified": True,
            }
            cycle = {
                "start": "binance:USDT",
                "profit_percent": 0.4,
                "paper_start_units": 100.0,
                "paper_end_units": 100.4,
                "paper_asset": "USDT",
                "executable": True,
                "capacity_verified": True,
                "minimum_order_verified": True,
                "quantity_step_verified": True,
                "quote_synchronized": True,
                "quotes_fresh": True,
                "contains_transfer": False,
                "paper_legs": [dict(trade_leg) for _ in range(3)],
                "route": [
                    {"src": "binance:USDT", "dst": "binance:BTC", "kind": "TRADE"},
                    {"src": "binance:BTC", "dst": "binance:ETH", "kind": "TRADE"},
                    {"src": "binance:ETH", "dst": "binance:USDT", "kind": "TRADE"},
                ],
            }
            signal = {
                "detected_at": "2026-08-27T14:00:00",
                "real_trading": False,
                "confirmation_snapshots": 3,
                "cycle": cycle,
            }
            signals.write_text(json.dumps(signal) + "\n", encoding="utf-8")
            with (
                patch.object(ledger, "JOURNAL", journal),
                patch.object(ledger, "SIGNALS", signals),
                patch.object(ledger, "LEDGER", journal / "ledger.jsonl"),
                patch.object(ledger, "STATE", journal / "state.json"),
                patch.object(ledger, "SUMMARY", journal / "summary.json"),
                patch.object(ledger, "INITIAL_BALANCES", {"binance:USDT": 1000.0}),
            ):
                first = ledger.process_once()
                second = ledger.process_once()
            self.assertEqual(first["paper_trades"], 1)
            self.assertAlmostEqual(first["wallet"]["balances"]["binance:USDT"], 1000.4)
            self.assertEqual(second["paper_trades"], 1)
            self.assertEqual(second["added_this_cycle"], 0)


if __name__ == "__main__":
    unittest.main()

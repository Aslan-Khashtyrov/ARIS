#!/usr/bin/env python3
import unittest

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


if __name__ == "__main__":
    unittest.main()

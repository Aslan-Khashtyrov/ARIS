import sys
import types
import unittest

if "websocket" not in sys.modules:
    sys.modules["websocket"] = types.ModuleType("websocket")

import main as paper


class PaperStateValidationTests(unittest.TestCase):
    def test_safe_float_rejects_nonfinite_values(self):
        for value in (float("nan"), float("inf"), float("-inf"), "nan", "inf"):
            with self.subTest(value=value):
                self.assertIsNone(paper.safe_float(value))

    def test_loaded_state_rejects_nonfinite_and_malformed_values(self):
        bad_states = (
            {"balance_usdt": float("nan")},
            {"starting_balance_usdt": 0},
            {"trades": True},
            {"last_routes": {"BTC:Binance>OKX": float("inf")}},
            {"day": "not-a-date"},
        )
        for state in bad_states:
            with self.subTest(state=state):
                with self.assertRaises((TypeError, ValueError)):
                    paper.validate_paper_state(state)

    def test_valid_state_is_normalized(self):
        state = paper.validate_paper_state(
            {
                "starting_balance_usdt": 1000,
                "balance_usdt": 1001.25,
                "realized_pnl_usdt": 1.25,
                "trades": 2,
                "wins": 2,
                "losses": 0,
                "day": "2026-09-06",
                "day_start_balance_usdt": 1000,
                "last_routes": {"BTC:Binance>OKX": 123.5},
            }
        )
        self.assertEqual(state["balance_usdt"], 1001.25)
        self.assertEqual(state["trades"], 2)
        self.assertEqual(state["last_routes"]["BTC:Binance>OKX"], 123.5)

    def test_nonfinite_market_and_opportunity_are_ignored(self):
        key = ("Binance", "TEST")
        with paper.multi_lock:
            paper.multi_market.pop(key, None)
        paper.update_multi_books("Binance", {"TEST": (float("nan"), 1.0)})
        with paper.multi_lock:
            self.assertNotIn(key, paper.multi_market)

        invalid = {
            "asset": "BTC",
            "buy_exchange": "Binance",
            "sell_exchange": "OKX",
            "ask": 1.0,
            "bid": 1.1,
            "net_edge_percent": float("nan"),
            "final_multiplier": 1.01,
        }
        self.assertIsNone(paper.maybe_execute_paper_trade(invalid))


if __name__ == "__main__":
    unittest.main()

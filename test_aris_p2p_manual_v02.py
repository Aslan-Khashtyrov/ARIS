#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CALCULATOR = ROOT / "aris_p2p_manual_v01.py"
if not CALCULATOR.exists():
    CALCULATOR = ROOT / "aris_p2p_manual_v02.py"


class ManualP2PV02Tests(unittest.TestCase):
    def run_case(self, age_seconds: int) -> dict:
        quoted_at = (datetime.now() - timedelta(seconds=age_seconds)).isoformat(timespec="seconds")
        payload = {
            "config": {
                "capital_rub": 10000,
                "maximum_quote_age_seconds": 120,
                "minimum_net_percent": 0.3,
            },
            "buy_ads": [{
                "id": "buy", "price_rub": 80, "available_usdt": 1000,
                "min_rub": 100, "max_rub": 100000,
                "payment_methods": ["TEST_BANK"], "quoted_at": quoted_at,
            }],
            "sell_ads": [{
                "id": "sell", "price_rub": 81, "available_usdt": 1000,
                "min_rub": 100, "max_rub": 100000,
                "payment_methods": ["TEST_BANK"], "quoted_at": quoted_at,
            }],
        }
        with tempfile.TemporaryDirectory() as directory:
            directory = Path(directory)
            input_path = directory / "quotes.json"
            history_path = directory / "history.jsonl"
            input_path.write_text(json.dumps(payload), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(CALCULATOR), str(input_path), "--history", str(history_path)],
                cwd=ROOT, capture_output=True, text=True, check=True,
            )
            report = json.loads(proc.stdout)
            self.assertTrue(history_path.exists())
            self.assertEqual(len(history_path.read_text(encoding="utf-8").splitlines()), 1)
            return report

    def test_fresh_profitable_route_requires_manual_review(self):
        report = self.run_case(1)
        self.assertEqual(report["version"], "0.2")
        self.assertEqual(report["best_route"]["decision"], "REVIEW_MANUALLY")

    def test_stale_route_is_skipped(self):
        report = self.run_case(3600)
        self.assertEqual(report["best_route"]["decision"], "SKIP")
        self.assertIn("STALE_QUOTE", report["best_route"]["decision_reasons"])


if __name__ == "__main__":
    unittest.main()

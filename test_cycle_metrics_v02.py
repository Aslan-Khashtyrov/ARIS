#!/usr/bin/env python3
import unittest

from aris_cycle_metrics_v02 import continuity_stats


class ContinuityStatsTests(unittest.TestCase):
    def test_continuous_minute_samples(self):
        rows = [
            {"timestamp": "2026-08-27T10:00:00"},
            {"timestamp": "2026-08-27T10:01:00"},
            {"timestamp": "2026-08-27T10:02:00"},
        ]
        result = continuity_stats(rows)
        self.assertTrue(result["continuous_at_90_seconds"])
        self.assertEqual(result["maximum_gap_seconds"], 60.0)
        self.assertEqual(result["sample_coverage_percent"], 100.0)

    def test_gap_is_reported(self):
        rows = [
            {"timestamp": "2026-08-27T10:00:00"},
            {"timestamp": "2026-08-27T10:03:00"},
        ]
        result = continuity_stats(rows)
        self.assertFalse(result["continuous_at_90_seconds"])
        self.assertEqual(result["gaps_over_90_seconds"], 1)
        self.assertEqual(result["maximum_gap_seconds"], 180.0)


if __name__ == "__main__":
    unittest.main()

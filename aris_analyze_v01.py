from pathlib import Path
from datetime import datetime
import csv
import json
import statistics
import sys

ROOT = Path.home() / "Arbitrage"
HISTORY = ROOT / "journal" / "multi_history_v03.csv"
MODES = {
    "TAKER->TAKER": "taker_taker_percent",
    "MAKER->TAKER": "maker_taker_percent",
    "TAKER->MAKER": "taker_maker_percent",
    "MAKER->MAKER": "maker_maker_percent",
}

def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, round((len(ordered) - 1) * fraction)))
    return ordered[index]

def analyze():
    if not HISTORY.exists():
        return {"ok": False, "error": "multi_history_v03.csv not found"}
    buckets = {}
    timestamps = []
    row_count = 0
    invalid_rows = 0
    with HISTORY.open(newline="", encoding="utf-8", errors="replace") as handle:
        for row in csv.DictReader(handle):
            asset = (row.get("asset") or "").strip()
            if not asset:
                invalid_rows += 1
                continue
            row_count += 1
            if row.get("timestamp"):
                timestamps.append(row["timestamp"])
            for mode, field in MODES.items():
                try:
                    value = float(row[field])
                except (KeyError, TypeError, ValueError):
                    invalid_rows += 1
                    continue
                buckets.setdefault(asset, {}).setdefault(mode, []).append(value)
    assets = {}
    best = None
    for asset, modes in sorted(buckets.items()):
        assets[asset] = {}
        for mode, values in modes.items():
            positive = sum(v > 0 for v in values)
            summary = {
                "samples": len(values),
                "average_percent": round(statistics.fmean(values), 6),
                "median_percent": round(statistics.median(values), 6),
                "p95_percent": round(percentile(values, 0.95), 6),
                "best_percent": round(max(values), 6),
                "positive_samples": positive,
                "positive_rate_percent": round(positive * 100 / len(values), 2),
            }
            assets[asset][mode] = summary
            candidate = {"asset": asset, "mode": mode, **summary}
            if best is None or candidate["best_percent"] > best["best_percent"]:
                best = candidate
    taker_positive = sum(
        data["TAKER->TAKER"]["positive_samples"]
        for data in assets.values()
        if "TAKER->TAKER" in data
    )
    return {
        "ok": True,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "history_file": str(HISTORY),
        "rows": row_count,
        "invalid_values": invalid_rows,
        "window": {
            "first": min(timestamps) if timestamps else None,
            "last": max(timestamps) if timestamps else None,
        },
        "assets": assets,
        "global_best": best,
        "taker_taker_positive_samples": taker_positive,
        "interpretation": (
            "PAPER SIGNALS ONLY. Positive maker scenarios are not executable guarantees. "
            "Configured fees are assumptions and transfers, slippage, limits, funding, "
            "withdrawal delays and tax are not fully modeled."
        ),
        "real_trading": False,
    }

if __name__ == "__main__":
    report = analyze()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    sys.exit(0 if report.get("ok") else 1)

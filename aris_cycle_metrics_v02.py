#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import math
import time
from datetime import datetime
from pathlib import Path

ROOT = Path.home() / "Arbitrage"
JOURNAL = ROOT / "journal"
OPERATIONAL = JOURNAL / "operational_report_v01.json"
HISTORY = JOURNAL / "cycle_metrics_v02.csv"
SUMMARY = JOURNAL / "cycle_metrics_summary_v02.json"
INTERVAL = 60
SIGNAL_THRESHOLD = 0.30
MODEL_VERSION = "multileg-executable-v01"
FIELDS = [
    "timestamp",
    "model_version",
    "live_quotes",
    "cycles_checked",
    "executable_cycles_checked",
    "connected_exchanges",
    "best_raw_percent",
    "best_net_percent",
    "best_executable",
    "best_any_percent",
    "actionable_candidates",
]


def percentile(values, fraction):
    if not values:
        return None
    ordered = sorted(values)
    index = (len(ordered) - 1) * fraction
    lower, upper = math.floor(index), math.ceil(index)
    if lower == upper:
        return ordered[lower]
    return ordered[lower] * (upper - index) + ordered[upper] * (index - lower)


def as_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def read_rows():
    if not HISTORY.exists():
        return []
    with HISTORY.open(newline="", encoding="utf-8", errors="replace") as handle:
        return [
            row for row in csv.DictReader(handle)
            if row.get("model_version") == MODEL_VERSION
        ]


def atomic_json(path, payload):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def build_summary(rows):
    net = [value for row in rows if (value := as_float(row.get("best_net_percent"))) is not None]
    raw = [value for row in rows if (value := as_float(row.get("best_raw_percent"))) is not None]
    any_best = [value for row in rows if (value := as_float(row.get("best_any_percent"))) is not None]
    executable_counts = [as_int(row.get("executable_cycles_checked")) for row in rows]
    positive_raw = sum(value > 0 for value in raw)
    positive_net = sum(value > 0 for value in net)
    threshold_hits = sum(value >= SIGNAL_THRESHOLD for value in net)
    return {
        "ok": True,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "MONITORING_ONLY",
        "real_trading": False,
        "model_version": MODEL_VERSION,
        "samples": len(rows),
        "samples_with_executable_result": len(net),
        "window": {
            "first": rows[0]["timestamp"] if rows else None,
            "last": rows[-1]["timestamp"] if rows else None,
        },
        "best_raw_percent": max(raw) if raw else None,
        "best_net_percent": max(net) if net else None,
        "best_any_percent": max(any_best) if any_best else None,
        "median_net_percent": percentile(net, 0.50),
        "p95_net_percent": percentile(net, 0.95),
        "latest_executable_cycles_checked": executable_counts[-1] if executable_counts else 0,
        "positive_raw_samples": positive_raw,
        "positive_net_samples": positive_net,
        "positive_net_rate_percent": (positive_net / len(net) * 100) if net else 0,
        "signal_threshold_percent": SIGNAL_THRESHOLD,
        "threshold_hits": threshold_hits,
    }


def capture_once():
    payload = json.loads(OPERATIONAL.read_text(encoding="utf-8"))
    market = payload.get("market", {})
    timestamp = payload.get("generated_at") or datetime.now().isoformat(timespec="seconds")
    rows = read_rows()
    if rows and rows[-1].get("timestamp") == timestamp:
        summary = build_summary(rows)
        atomic_json(SUMMARY, summary)
        return summary
    row = {
        "timestamp": timestamp,
        "model_version": MODEL_VERSION,
        "live_quotes": market.get("live_quotes", 0),
        "cycles_checked": market.get("cycles_checked", 0),
        "executable_cycles_checked": market.get("executable_cycles_checked", 0),
        "connected_exchanges": len(market.get("connected_exchanges", [])),
        "best_raw_percent": market.get("best_raw_profit_percent"),
        "best_net_percent": market.get("best_profit_percent"),
        "best_executable": market.get("best_executable"),
        "best_any_percent": market.get("best_any_profit_percent"),
        "actionable_candidates": market.get("actionable_candidates", 0),
    }
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    new_file = not HISTORY.exists()
    with HISTORY.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow(row)
    rows.append({key: str(value) for key, value in row.items()})
    summary = build_summary(rows)
    atomic_json(SUMMARY, summary)
    return summary


def run_forever():
    while True:
        try:
            capture_once()
        except Exception as exc:
            atomic_json(SUMMARY, {
                "ok": False,
                "generated_at": datetime.now().isoformat(timespec="seconds"),
                "model_version": MODEL_VERSION,
                "error": f"{type(exc).__name__}: {exc}",
                "real_trading": False,
            })
        time.sleep(INTERVAL)


if __name__ == "__main__":
    print(json.dumps(capture_once(), ensure_ascii=False, indent=2))

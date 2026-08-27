#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path

ROOT = Path.home() / "Arbitrage"
JOURNAL = ROOT / "journal"
OUTPUT = JOURNAL / "operational_report_v01.json"
SOURCES = {
    "collector": (JOURNAL / "cycle_collector_status_v01.json", 30),
    "cycles": (JOURNAL / "cycle_report_v01.json", 30),
    "paper": (JOURNAL / "paper_ledger_summary_v01.json", 45),
    "foreman": (JOURNAL / "foreman_status_v01.json", 30),
}


def read_source(path, maximum_age):
    try:
        age = round(time.time() - path.stat().st_mtime, 1)
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {"ok": age <= maximum_age and bool(payload.get("ok")), "age_seconds": age, "maximum_age": maximum_age, "data": payload}
    except Exception as exc:
        return {"ok": False, "age_seconds": None, "maximum_age": maximum_age, "error": f"{type(exc).__name__}: {exc}", "data": {}}


def atomic_json(path, payload):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(temp, path)


def build_once():
    sources = {name: read_source(path, age) for name, (path, age) in SOURCES.items()}
    collector = sources["collector"]["data"]
    cycles = sources["cycles"]["data"]
    paper = sources["paper"]["data"]
    foreman = sources["foreman"]["data"]
    exchanges = collector.get("exchanges", {})
    disconnected = sorted(name for name, item in exchanges.items() if not item.get("connected"))
    stale = sorted(name for name, item in sources.items() if not item["ok"])
    signal_ready = bool(collector.get("confirmed_signal_ready"))
    if stale or disconnected:
        decision = "DEGRADED"
    elif signal_ready:
        decision = "PAPER_SIGNAL_READY"
    else:
        decision = "MONITORING"
    best_any = cycles.get("best_cycle") or {}
    best = cycles.get("best_executable_cycle") or {}
    report = {
        "ok": not stale and not disconnected,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "MONITORING_AND_PAPER_ONLY",
        "decision": decision,
        "reasons": (["stale:" + name for name in stale] + ["disconnected:" + name for name in disconnected]) or (["confirmed_paper_signal"] if signal_ready else ["no_confirmed_opportunity"]),
        "market": {
            "live_quotes": collector.get("live_quotes", 0),
            "cycles_checked": collector.get("cycles_checked", 0),
            "connected_exchanges": sorted(name for name, item in exchanges.items() if item.get("connected")),
            "best_profit_percent": best.get("profit_percent"),
            "best_raw_profit_percent": best.get("raw_profit_percent"),
            "best_executable": best.get("executable"),
            "best_quote_age_seconds": best.get("oldest_quote_age_seconds"),
            "maximum_quote_age_seconds": best.get("maximum_quote_age_seconds"),
            "best_quotes_fresh": best.get("quotes_fresh"),
            "best_any_profit_percent": best_any.get("profit_percent"),
            "best_any_executable": best_any.get("executable"),
            "executable_cycles_checked": cycles.get("executable_cycles_checked", 0),
            "positive_theoretical_cycles": cycles.get("positive_theoretical_cycles_checked", 0),
            "positive_simulated_cycles": cycles.get("positive_simulated_cycles_checked", 0),
            "positive_net_cycles": cycles.get("positive_net_cycles_checked", 0),
            "positive_executable_cycles": cycles.get("positive_executable_cycles_checked", 0),
            "signal_threshold_cycles": cycles.get("signal_threshold_cycles_checked", 0),
            "best_theoretical_raw_profit_percent": cycles.get("best_theoretical_raw_profit_percent"),
            "best_simulated_raw_profit_percent": cycles.get("best_simulated_raw_profit_percent"),
            "actionable_candidates": collector.get("actionable_candidates", 0),
            "candidate_streak": collector.get("candidate_streak", 0),
            "required_confirmations": collector.get("required_confirmations", 3),
            "fee_model": collector.get("fee_model"),
        },
        "paper": {
            "trades": paper.get("paper_trades", 0),
            "profit_by_asset": paper.get("profit_by_asset", {}),
            "minimum_profit_percent": paper.get("minimum_profit_percent"),
            "wallet": paper.get("wallet", {}),
        },
        "system": {
            "foreman_cycle": foreman.get("cycle"),
            "foreman_problems": foreman.get("problems", []),
            "source_freshness": {name: {"ok": item["ok"], "age_seconds": item["age_seconds"], "maximum_age": item["maximum_age"]} for name, item in sources.items()},
        },
        "safety": {"real_trading": False, "orders": False, "payments": False, "withdrawals": False, "api_secrets": False},
    }
    atomic_json(OUTPUT, report)
    return report


def run_forever():
    while True:
        try:
            build_once()
        except Exception as exc:
            atomic_json(OUTPUT, {"ok": False, "generated_at": datetime.now().isoformat(timespec="seconds"), "decision": "DEGRADED", "error": f"{type(exc).__name__}: {exc}", "real_trading": False})
        time.sleep(10)


if __name__ == "__main__":
    print(json.dumps(build_once(), ensure_ascii=False, indent=2))

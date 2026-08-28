#!/usr/bin/env python3
from __future__ import annotations
import hashlib
import json
import time
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path.home() / "Arbitrage"
JOURNAL = ROOT / "journal"
SOURCE = JOURNAL / "cross_exchange_positive_v01.jsonl"
LEDGER = JOURNAL / "cross_paper_ledger_v02.jsonl"
STATE = JOURNAL / "cross_paper_ledger_state_v02.json"
SUMMARY = JOURNAL / "cross_paper_ledger_summary_v02.json"
MODEL = "cross-shadow-paper-v02-cooldown"
MIN_NET_PERCENT = 0.05
MIN_CONFIRMATIONS = 3
MAX_QUOTE_STAKE = 100.0
ROUTE_COOLDOWN_SECONDS = 60

def atomic_json(path, payload):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)

def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def fingerprint(detected_at, route):
    identity = [detected_at, route.get("pair"), route.get("buy_exchange"), route.get("sell_exchange")]
    return hashlib.sha256(json.dumps(identity).encode()).hexdigest()

def existing_rows():
    rows = []
    if not LEDGER.exists():
        return rows
    for line in LEDGER.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return rows

def process_once():
    JOURNAL.mkdir(parents=True, exist_ok=True)
    state = read_json(STATE, {})
    processed = set(state.get("processed", []))
    rows = existing_rows()
    added = 0
    rejected = defaultdict(int)
    last_trade_by_route = {}
    for row in rows:
        route_key = "|".join((str(row.get("pair")), str(row.get("buy_exchange")), str(row.get("sell_exchange"))))
        try:
            last_trade_by_route[route_key] = max(last_trade_by_route.get(route_key, 0.0), datetime.fromisoformat(str(row.get("detected_at"))).timestamp())
        except Exception:
            pass
    if SOURCE.exists():
        for line in SOURCE.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                signal = json.loads(line)
            except json.JSONDecodeError:
                continue
            route = signal.get("route", {})
            key = fingerprint(signal.get("detected_at"), route)
            if key in processed:
                continue
            reason = None
            if signal.get("real_trading") is not False or route.get("real_trading") is not False:
                reason = "real_trading_guard"
            elif route.get("confirmed") is not True or int(route.get("consecutive_confirmations", 0) or 0) < MIN_CONFIRMATIONS:
                reason = "confirmations"
            elif route.get("executable") is not True or route.get("quotes_fresh") is not True or route.get("quote_synchronized") is not True:
                reason = "execution_quality"
            elif float(route.get("net_profit_percent", -999) or -999) < MIN_NET_PERCENT:
                reason = "profit_threshold"
            route_key = "|".join((str(route.get("pair")), str(route.get("buy_exchange")), str(route.get("sell_exchange"))))
            try:
                detected_ts = datetime.fromisoformat(str(signal.get("detected_at"))).timestamp()
            except Exception:
                detected_ts = 0.0
            if detected_ts and detected_ts - last_trade_by_route.get(route_key, -1e18) < ROUTE_COOLDOWN_SECONDS:
                reason = reason or "route_cooldown"
            stake = min(MAX_QUOTE_STAKE, float(route.get("paper_buy_cost", 0) or 0))
            if stake <= 0:
                reason = reason or "stake"
            processed.add(key)
            if reason:
                rejected[reason] += 1
                continue
            net_percent = float(route["net_profit_percent"])
            profit = stake * net_percent / 100.0
            record = {
                "fingerprint": key,
                "recorded_at": datetime.now().isoformat(timespec="seconds"),
                "detected_at": signal.get("detected_at"),
                "model": MODEL,
                "pair": route.get("pair"),
                "buy_exchange": route.get("buy_exchange"),
                "sell_exchange": route.get("sell_exchange"),
                "quote_asset": route.get("quote"),
                "paper_stake": stake,
                "paper_profit": profit,
                "net_profit_percent": net_percent,
                "consecutive_confirmations": route.get("consecutive_confirmations"),
                "funding_model": "PRE_FUNDED_PAIR_INVENTORY_REQUIRED",
                "wallet_mutated": False,
                "real_trading": False,
            }
            with LEDGER.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            rows.append(record)
            last_trade_by_route[route_key] = detected_ts
            added += 1
    profits = defaultdict(float)
    for row in rows:
        profits[str(row.get("quote_asset", ""))] += float(row.get("paper_profit", 0) or 0)
    atomic_json(STATE, {"processed": sorted(processed), "model": MODEL, "updated_at": datetime.now().isoformat(timespec="seconds")})
    summary = {
        "ok": True,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "model": MODEL,
        "mode": "SHADOW_PAPER_ONLY",
        "real_trading": False,
        "wallet_mutated": False,
        "funding_model": "PRE_FUNDED_PAIR_INVENTORY_REQUIRED",
        "minimum_net_profit_percent": MIN_NET_PERCENT,
        "minimum_confirmations": MIN_CONFIRMATIONS,
        "maximum_quote_stake": MAX_QUOTE_STAKE,
        "route_cooldown_seconds": ROUTE_COOLDOWN_SECONDS,
        "paper_trades": len(rows),
        "paper_profit_by_quote_asset": dict(sorted(profits.items())),
        "added_this_cycle": added,
        "rejected_this_cycle": sum(rejected.values()),
        "rejection_reasons": dict(sorted(rejected.items())),
    }
    atomic_json(SUMMARY, summary)
    return summary

def run_forever():
    while True:
        try:
            process_once()
        except Exception as exc:
            atomic_json(SUMMARY, {"ok": False, "error": f"{type(exc).__name__}: {exc}", "real_trading": False})
        time.sleep(5)

if __name__ == "__main__":
    print(json.dumps(process_once(), ensure_ascii=False, indent=2))

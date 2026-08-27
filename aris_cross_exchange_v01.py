#!/usr/bin/env python3
from __future__ import annotations

import json
import math
import time
from datetime import datetime
from pathlib import Path

ROOT = Path.home() / "Arbitrage"
JOURNAL = ROOT / "journal"
SNAPSHOT = JOURNAL / "cycle_quotes_v01.json"
REPORT = JOURNAL / "cross_exchange_report_v01.json"
MAX_QUOTE_AGE_SECONDS = 5.0
MAX_QUOTE_SKEW_SECONDS = 3.0
MAX_BOOK_UTILIZATION_PERCENT = 80.0
EXECUTION_BUFFER_PERCENT = 0.05
PAPER_QUOTE_STAKE = 100.0


def floor_step(value, step):
    if step <= 0:
        return value
    return math.floor((value + step * 1e-12) / step) * step


def common_quantity(value, *steps):
    result = value
    for step in steps:
        result = floor_step(result, float(step or 0))
    return max(0.0, result)


def analyze(payload, evaluation_time=None):
    now = time.time() if evaluation_time is None else float(evaluation_time)
    groups = {}
    for quote in payload.get("quotes", []):
        try:
            base = str(quote["base"]).upper()
            counter = str(quote["quote"]).upper()
            exchange = str(quote["exchange"]).lower()
            bid, ask = float(quote["bid"]), float(quote["ask"])
            bid_size = float(quote.get("bid_size", 0) or 0)
            ask_size = float(quote.get("ask_size", 0) or 0)
            fee = float(quote.get("taker_fee", 0) or 0)
            updated = float(quote.get("updated_at", 0) or 0)
        except (KeyError, TypeError, ValueError):
            continue
        if bid <= 0 or ask <= 0 or bid > ask or bid_size <= 0 or ask_size <= 0 or not 0 <= fee < 0.05:
            continue
        item = dict(quote)
        item.update({"base": base, "quote": counter, "exchange": exchange, "bid": bid, "ask": ask, "bid_size": bid_size, "ask_size": ask_size, "taker_fee": fee, "updated_at": updated})
        groups.setdefault((base, counter), []).append(item)

    comparisons = []
    for (base, counter), quotes in groups.items():
        for buy in quotes:
            for sell in quotes:
                if buy["exchange"] == sell["exchange"]:
                    continue
                skew = abs(buy["updated_at"] - sell["updated_at"])
                oldest_age = max(0.0, now - min(buy["updated_at"], sell["updated_at"]))
                raw_base = min(
                    PAPER_QUOTE_STAKE / buy["ask"],
                    buy["ask_size"] * MAX_BOOK_UTILIZATION_PERCENT / 100.0,
                    sell["bid_size"] * MAX_BOOK_UTILIZATION_PERCENT / 100.0,
                )
                quantity = common_quantity(raw_base, buy.get("qty_step", 0), sell.get("qty_step", 0))
                buy_cost = quantity * buy["ask"]
                sell_revenue = quantity * sell["bid"]
                net_revenue = sell_revenue * (1.0 - sell["taker_fee"])
                net_cost = buy_cost / max(1e-12, 1.0 - buy["taker_fee"])
                raw_percent = (sell["bid"] / buy["ask"] - 1.0) * 100.0
                net_before_buffer = (net_revenue / net_cost - 1.0) * 100.0 if net_cost > 0 else -100.0
                net_percent = net_before_buffer - EXECUTION_BUFFER_PERCENT
                minimum_ok = (
                    quantity > 0
                    and quantity + 1e-12 >= float(buy.get("min_base", 0) or 0)
                    and quantity + 1e-12 >= float(sell.get("min_base", 0) or 0)
                    and buy_cost + 1e-12 >= float(buy.get("min_quote", 0) or 0)
                    and sell_revenue + 1e-12 >= float(sell.get("min_quote", 0) or 0)
                )
                fresh = oldest_age <= MAX_QUOTE_AGE_SECONDS
                synchronized = skew <= MAX_QUOTE_SKEW_SECONDS
                executable = minimum_ok and fresh and synchronized and buy_cost > 0
                comparisons.append({
                    "pair": f"{base}/{counter}",
                    "base": base,
                    "quote": counter,
                    "buy_exchange": buy["exchange"],
                    "sell_exchange": sell["exchange"],
                    "buy_ask": buy["ask"],
                    "sell_bid": sell["bid"],
                    "raw_spread_percent": raw_percent,
                    "net_before_buffer_percent": net_before_buffer,
                    "execution_buffer_percent": EXECUTION_BUFFER_PERCENT,
                    "net_profit_percent": net_percent,
                    "paper_base_quantity": quantity,
                    "paper_buy_cost": buy_cost,
                    "paper_sell_revenue_after_fee": net_revenue,
                    "quote_skew_seconds": skew,
                    "oldest_quote_age_seconds": oldest_age,
                    "quotes_fresh": fresh,
                    "quote_synchronized": synchronized,
                    "minimum_order_verified": minimum_ok,
                    "executable": executable,
                    "real_trading": False,
                })

    comparisons.sort(key=lambda item: item["net_profit_percent"], reverse=True)
    executable = [item for item in comparisons if item["executable"]]
    positive_raw = [item for item in comparisons if item["raw_spread_percent"] > 0]
    positive_net = [item for item in executable if item["net_profit_percent"] > 0]
    return {
        "ok": True,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "CROSS_EXCHANGE_PAPER_ONLY",
        "real_trading": False,
        "pairs_compared": len(groups),
        "routes_compared": len(comparisons),
        "executable_routes": len(executable),
        "positive_raw_routes": len(positive_raw),
        "positive_executable_routes": len(positive_net),
        "best_route": comparisons[0] if comparisons else None,
        "best_executable_route": executable[0] if executable else None,
        "opportunities": positive_net[:50],
        "assumption": "Simultaneous pre-funded inventory on both exchanges; transfers are excluded.",
    }


def process_once():
    JOURNAL.mkdir(parents=True, exist_ok=True)
    if SNAPSHOT.exists():
        payload = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        report = analyze(payload)
    else:
        report = {"ok": True, "status": "WAITING_FOR_QUOTES", "real_trading": False}
    temp = REPORT.with_suffix(".json.tmp")
    temp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(REPORT)
    return report


def run_forever():
    while True:
        try:
            process_once()
        except Exception as exc:
            REPORT.write_text(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}", "real_trading": False}) + "\n", encoding="utf-8")
        time.sleep(15)


if __name__ == "__main__":
    print(json.dumps(process_once(), ensure_ascii=False, indent=2))

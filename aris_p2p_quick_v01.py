#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from aris_p2p_manual_v01 import evaluate, normalize_ad

VERSION = "0.2"
HISTORY = Path.home() / "Arbitrage" / "journal" / "p2p_manual_history_v01.jsonl"


def parse_quote_time(raw: str | None) -> datetime:
    if not raw:
        return datetime.now()
    value = raw.strip().replace("Z", "+00:00")
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def append_history(report: dict) -> None:
    HISTORY.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(report, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="A.R.I.S. quick manual P2P calculator")
    parser.add_argument("--buy", type=float, required=True, help="Purchase price in RUB per USDT")
    parser.add_argument("--sell", type=float, required=True, help="Sale price in RUB per USDT")
    parser.add_argument("--capital", type=float, required=True, help="Capital in RUB")
    parser.add_argument("--method", default="MANUAL", help="Payment method label")
    parser.add_argument("--buy-fee", type=float, default=0.0, help="Buy fee percent")
    parser.add_argument("--sell-fee", type=float, default=0.0, help="Sell fee percent")
    parser.add_argument("--fixed-cost", type=float, default=0.0, help="Other fixed costs in RUB")
    parser.add_argument("--minimum", type=float, default=0.3, help="Minimum net profit percent")
    parser.add_argument("--quoted-at", help="ISO timestamp when prices were observed; defaults to now")
    parser.add_argument("--max-age", type=float, default=120.0, help="Maximum quote age in seconds")
    args = parser.parse_args()

    if args.buy <= 0 or args.sell <= 0 or args.capital <= 0:
        raise ValueError("buy, sell and capital must be positive")
    if args.max_age <= 0:
        raise ValueError("max-age must be positive")

    now = datetime.now()
    quoted_at = parse_quote_time(args.quoted_at)
    age_seconds = max(0.0, (now - quoted_at).total_seconds())
    quote_fresh = age_seconds <= args.max_age

    capacity = max(args.capital / args.buy, args.capital / args.sell) * 2
    buy = normalize_ad({
        "id": "quick-buy", "platform": "manual", "merchant": "manual",
        "price_rub": args.buy, "available_usdt": capacity,
        "min_rub": 0, "max_rub": args.capital,
        "payment_methods": [args.method],
    }, "buy_ads", 0)
    sell = normalize_ad({
        "id": "quick-sell", "platform": "manual", "merchant": "manual",
        "price_rub": args.sell, "available_usdt": capacity,
        "min_rub": 0, "max_rub": args.capital * 2,
        "payment_methods": [args.method],
    }, "sell_ads", 0)
    config = {
        "capital_rub": args.capital,
        "buy_fee_percent": args.buy_fee,
        "sell_fee_percent": args.sell_fee,
        "fixed_cost_rub": args.fixed_cost,
        "minimum_net_percent": args.minimum,
        "require_shared_payment_method": True,
    }
    route = evaluate(buy, sell, config)
    threshold_met = bool(route and route["meets_threshold"])
    decision = "REVIEW_MANUALLY" if threshold_met and quote_fresh else "SKIP"
    reasons = []
    if not threshold_met:
        reasons.append("NET_PROFIT_BELOW_THRESHOLD")
    if not quote_fresh:
        reasons.append("STALE_QUOTE")

    report = {
        "ok": True,
        "version": VERSION,
        "generated_at": now.isoformat(timespec="seconds"),
        "mode": "QUICK_MANUAL_PAPER_ONLY",
        "real_trading": False,
        "quote": {
            "quoted_at": quoted_at.isoformat(timespec="seconds"),
            "age_seconds": round(age_seconds, 1),
            "maximum_age_seconds": args.max_age,
            "fresh": quote_fresh,
        },
        "input": {
            "buy_price_rub": args.buy,
            "sell_price_rub": args.sell,
            "capital_rub": args.capital,
            "payment_method": args.method,
            "buy_fee_percent": args.buy_fee,
            "sell_fee_percent": args.sell_fee,
            "fixed_cost_rub": args.fixed_cost,
            "minimum_net_percent": args.minimum,
        },
        "result": route,
        "decision": decision,
        "decision_reasons": reasons,
        "history_file": str(HISTORY),
        "warning": "Manual calculation only. Account, counterparty, platform, bank and legal risks require human verification.",
    }
    append_history(report)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
        sys.exit(1)

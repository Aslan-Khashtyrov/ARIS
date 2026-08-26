#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime

from aris_p2p_manual_v01 import evaluate, normalize_ad


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
    args = parser.parse_args()

    if args.buy <= 0 or args.sell <= 0 or args.capital <= 0:
        raise ValueError("buy, sell and capital must be positive")

    capacity = max(args.capital / args.buy, args.capital / args.sell) * 2
    buy = normalize_ad({
        "id": "quick-buy",
        "platform": "manual",
        "merchant": "manual",
        "price_rub": args.buy,
        "available_usdt": capacity,
        "min_rub": 0,
        "max_rub": args.capital,
        "payment_methods": [args.method],
    }, "buy_ads", 0)
    sell = normalize_ad({
        "id": "quick-sell",
        "platform": "manual",
        "merchant": "manual",
        "price_rub": args.sell,
        "available_usdt": capacity,
        "min_rub": 0,
        "max_rub": args.capital * 2,
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
    report = {
        "ok": True,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "QUICK_MANUAL_PAPER_ONLY",
        "real_trading": False,
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
        "decision": "REVIEW_MANUALLY" if route and route["meets_threshold"] else "SKIP",
        "warning": "Manual calculation only. Quote freshness, account, counterparty and bank risks require human verification.",
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
        sys.exit(1)

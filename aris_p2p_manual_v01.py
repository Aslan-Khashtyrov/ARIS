#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

VERSION = "0.1"
DEFAULT_MIN_NET_PERCENT = 0.30


def money(value: object, field: str) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if number < 0:
        raise ValueError(f"{field} must be non-negative")
    return number


def normalize_ad(raw: dict, side: str, index: int) -> dict:
    if not isinstance(raw, dict):
        raise ValueError(f"{side}[{index}] must be an object")
    price = money(raw.get("price_rub"), f"{side}[{index}].price_rub")
    available = money(raw.get("available_usdt"), f"{side}[{index}].available_usdt")
    minimum = money(raw.get("min_rub", 0), f"{side}[{index}].min_rub")
    maximum = money(raw.get("max_rub", price * available), f"{side}[{index}].max_rub")
    methods = raw.get("payment_methods", [])
    if isinstance(methods, str):
        methods = [methods]
    if not isinstance(methods, list):
        raise ValueError(f"{side}[{index}].payment_methods must be an array")
    methods = sorted({str(item).strip() for item in methods if str(item).strip()})
    return {
        "id": str(raw.get("id", f"{side}-{index + 1}")),
        "platform": str(raw.get("platform", "manual")),
        "price_rub": price,
        "available_usdt": available,
        "min_rub": minimum,
        "max_rub": maximum,
        "payment_methods": methods,
        "merchant": str(raw.get("merchant", "unknown")),
    }


def evaluate(buy: dict, sell: dict, config: dict) -> dict | None:
    shared = sorted(set(buy["payment_methods"]) & set(sell["payment_methods"]))
    if config.get("require_shared_payment_method", True) and not shared:
        return None

    requested = money(config.get("capital_rub", 10000), "config.capital_rub")
    buy_fee = money(config.get("buy_fee_percent", 0), "config.buy_fee_percent") / 100
    sell_fee = money(config.get("sell_fee_percent", 0), "config.sell_fee_percent") / 100
    fixed_cost = money(config.get("fixed_cost_rub", 0), "config.fixed_cost_rub")

    maximum_buy_rub = min(requested, buy["max_rub"], buy["available_usdt"] * buy["price_rub"])
    if maximum_buy_rub < buy["min_rub"] or maximum_buy_rub <= 0:
        return None

    usdt = maximum_buy_rub / buy["price_rub"]
    sell_capacity_rub = min(sell["max_rub"], sell["available_usdt"] * sell["price_rub"])
    usdt = min(usdt, sell_capacity_rub / sell["price_rub"])
    buy_cost = usdt * buy["price_rub"]
    gross_sell = usdt * sell["price_rub"]
    if buy_cost < buy["min_rub"] or gross_sell < sell["min_rub"]:
        return None

    total_cost = buy_cost * (1 + buy_fee) + fixed_cost
    net_return = gross_sell * (1 - sell_fee)
    net_profit = net_return - total_cost
    net_percent = (net_profit / total_cost * 100) if total_cost else 0
    threshold = money(config.get("minimum_net_percent", DEFAULT_MIN_NET_PERCENT), "config.minimum_net_percent")

    return {
        "buy_ad": buy["id"],
        "sell_ad": sell["id"],
        "buy_platform": buy["platform"],
        "sell_platform": sell["platform"],
        "payment_methods": shared,
        "amount_usdt": round(usdt, 6),
        "buy_cost_rub": round(buy_cost, 2),
        "sell_proceeds_rub": round(gross_sell, 2),
        "net_profit_rub": round(net_profit, 2),
        "net_profit_percent": round(net_percent, 4),
        "meets_threshold": net_percent >= threshold,
        "manual_confirmation_required": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="A.R.I.S. manual P2P spread evaluator")
    parser.add_argument("input", nargs="?", default="data/p2p_manual_quotes_v01.json")
    args = parser.parse_args()

    path = Path(args.input).expanduser()
    if not path.is_absolute():
        path = Path.home() / "Arbitrage" / path
    payload = json.loads(path.read_text(encoding="utf-8"))
    buys = [normalize_ad(item, "buy_ads", i) for i, item in enumerate(payload.get("buy_ads", []))]
    sells = [normalize_ad(item, "sell_ads", i) for i, item in enumerate(payload.get("sell_ads", []))]
    config = payload.get("config", {})

    routes = []
    for buy in buys:
        for sell in sells:
            route = evaluate(buy, sell, config)
            if route:
                routes.append(route)
    routes.sort(key=lambda item: item["net_profit_percent"], reverse=True)

    report = {
        "ok": True,
        "version": VERSION,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "MANUAL_INPUT_PAPER_ONLY",
        "real_trading": False,
        "input_file": str(path),
        "buy_ads": len(buys),
        "sell_ads": len(sells),
        "routes_checked": len(buys) * len(sells),
        "compatible_routes": len(routes),
        "actionable_routes": sum(1 for item in routes if item["meets_threshold"]),
        "best_route": routes[0] if routes else None,
        "routes": routes[:20],
        "warnings": [
            "Manual quotes can become stale before confirmation.",
            "Bank, platform, tax, account-freeze and counterparty risks require human review.",
            "No orders, messages, payments, transfers, deposits or withdrawals are performed.",
        ],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
        sys.exit(1)

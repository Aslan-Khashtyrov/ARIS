#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

VERSION = "0.2"
DEFAULT_MAX_AGE_SECONDS = 120.0
DEFAULT_MIN_NET_PERCENT = 0.30
HISTORY = Path.home() / "Arbitrage" / "journal" / "p2p_manual_history_v02.jsonl"


def number(value: object, field: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if result < 0:
        raise ValueError(f"{field} must be non-negative")
    return result


def parse_time(value: object, field: str) -> datetime:
    if not value:
        raise ValueError(f"{field} is required")
    try:
        parsed = datetime.fromisoformat(str(value).strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO timestamp") from exc
    if parsed.tzinfo is not None:
        parsed = parsed.astimezone().replace(tzinfo=None)
    return parsed


def normalize_ad(raw: dict, side: str, index: int, now: datetime, max_age: float) -> dict:
    if not isinstance(raw, dict):
        raise ValueError(f"{side}[{index}] must be an object")
    price = number(raw.get("price_rub"), f"{side}[{index}].price_rub")
    available = number(raw.get("available_usdt"), f"{side}[{index}].available_usdt")
    if price <= 0 or available <= 0:
        raise ValueError(f"{side}[{index}] price and available amount must be positive")
    minimum = number(raw.get("min_rub", 0), f"{side}[{index}].min_rub")
    maximum = number(raw.get("max_rub", price * available), f"{side}[{index}].max_rub")
    if maximum < minimum:
        raise ValueError(f"{side}[{index}].max_rub must be >= min_rub")
    methods = raw.get("payment_methods", [])
    if isinstance(methods, str):
        methods = [methods]
    if not isinstance(methods, list):
        raise ValueError(f"{side}[{index}].payment_methods must be an array")
    quoted_at = parse_time(raw.get("quoted_at"), f"{side}[{index}].quoted_at")
    age = max(0.0, (now - quoted_at).total_seconds())
    return {
        "id": str(raw.get("id", f"{side}-{index + 1}")),
        "platform": str(raw.get("platform", "manual")),
        "merchant": str(raw.get("merchant", "unknown")),
        "price_rub": price,
        "available_usdt": available,
        "min_rub": minimum,
        "max_rub": maximum,
        "payment_methods": sorted({str(v).strip() for v in methods if str(v).strip()}),
        "quoted_at": quoted_at.isoformat(timespec="seconds"),
        "age_seconds": round(age, 1),
        "fresh": age <= max_age,
    }


def evaluate(buy: dict, sell: dict, config: dict) -> dict | None:
    shared = sorted(set(buy["payment_methods"]) & set(sell["payment_methods"]))
    if config.get("require_shared_payment_method", True) and not shared:
        return None
    capital = number(config.get("capital_rub", 10000), "config.capital_rub")
    buy_fee = number(config.get("buy_fee_percent", 0), "config.buy_fee_percent") / 100
    sell_fee = number(config.get("sell_fee_percent", 0), "config.sell_fee_percent") / 100
    fixed_cost = number(config.get("fixed_cost_rub", 0), "config.fixed_cost_rub")
    maximum_buy = min(capital, buy["max_rub"], buy["available_usdt"] * buy["price_rub"])
    if maximum_buy <= 0 or maximum_buy < buy["min_rub"]:
        return None
    usdt = maximum_buy / buy["price_rub"]
    usdt = min(usdt, sell["available_usdt"], sell["max_rub"] / sell["price_rub"])
    buy_cost = usdt * buy["price_rub"]
    gross_sell = usdt * sell["price_rub"]
    if buy_cost < buy["min_rub"] or gross_sell < sell["min_rub"]:
        return None
    total_cost = buy_cost * (1 + buy_fee) + fixed_cost
    net_return = gross_sell * (1 - sell_fee)
    net_profit = net_return - total_cost
    net_percent = net_profit / total_cost * 100 if total_cost else 0.0
    threshold = number(config.get("minimum_net_percent", DEFAULT_MIN_NET_PERCENT), "config.minimum_net_percent")
    reasons = []
    if not buy["fresh"] or not sell["fresh"]:
        reasons.append("STALE_QUOTE")
    if net_percent < threshold:
        reasons.append("NET_PROFIT_BELOW_THRESHOLD")
    return {
        "buy_ad": buy["id"], "sell_ad": sell["id"],
        "buy_platform": buy["platform"], "sell_platform": sell["platform"],
        "payment_methods": shared, "amount_usdt": round(usdt, 6),
        "buy_cost_rub": round(buy_cost, 2), "sell_proceeds_rub": round(gross_sell, 2),
        "net_profit_rub": round(net_profit, 2), "net_profit_percent": round(net_percent, 4),
        "buy_quote_age_seconds": buy["age_seconds"], "sell_quote_age_seconds": sell["age_seconds"],
        "decision": "REVIEW_MANUALLY" if not reasons else "SKIP",
        "decision_reasons": reasons, "manual_confirmation_required": True,
    }


def append_history(report: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(report, ensure_ascii=False, separators=(",", ":")) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="A.R.I.S. manual P2P spread evaluator v0.2")
    parser.add_argument("input", nargs="?", default="data/p2p_manual_quotes_v01.json")
    parser.add_argument("--history", default=str(HISTORY))
    args = parser.parse_args()
    path = Path(args.input).expanduser()
    if not path.is_absolute():
        path = Path.home() / "Arbitrage" / path
    payload = json.loads(path.read_text(encoding="utf-8"))
    config = payload.get("config", {})
    max_age = number(config.get("maximum_quote_age_seconds", DEFAULT_MAX_AGE_SECONDS), "config.maximum_quote_age_seconds")
    if max_age <= 0:
        raise ValueError("config.maximum_quote_age_seconds must be positive")
    now = datetime.now()
    buys = [normalize_ad(v, "buy_ads", i, now, max_age) for i, v in enumerate(payload.get("buy_ads", []))]
    sells = [normalize_ad(v, "sell_ads", i, now, max_age) for i, v in enumerate(payload.get("sell_ads", []))]
    routes = [r for buy in buys for sell in sells if (r := evaluate(buy, sell, config))]
    routes.sort(key=lambda value: value["net_profit_percent"], reverse=True)
    report = {
        "ok": True, "version": VERSION, "generated_at": now.isoformat(timespec="seconds"),
        "mode": "MANUAL_INPUT_PAPER_ONLY", "real_trading": False,
        "input_file": str(path), "maximum_quote_age_seconds": max_age,
        "buy_ads": len(buys), "sell_ads": len(sells), "routes_checked": len(buys) * len(sells),
        "compatible_routes": len(routes),
        "actionable_routes": sum(r["decision"] == "REVIEW_MANUALLY" for r in routes),
        "best_route": routes[0] if routes else None, "routes": routes[:20],
        "warnings": ["Manual quotes can change before confirmation.", "Human review is always required.", "No financial action is performed."],
    }
    append_history(report, Path(args.history).expanduser())
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:
        print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False))
        sys.exit(1)

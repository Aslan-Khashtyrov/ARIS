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
SNAPSHOT = JOURNAL / "cycle_quotes_v01.json"
LEDGER = JOURNAL / "cross_inventory_low_risk_ledger_v01.jsonl"
STATE = JOURNAL / "cross_inventory_low_risk_state_v01.json"
SUMMARY = JOURNAL / "cross_inventory_low_risk_summary_v01.json"
MODEL = "cross-inventory-low-risk-v01"
EXCHANGES = ("binance", "bybit", "okx")
BASE_ASSET = "SOL"
QUOTE_ASSET = "USDT"
INITIAL_QUOTE_PER_EXCHANGE = 800.0
INITIAL_BASE_VALUE_PER_EXCHANGE = 200.0
MIN_NET_PERCENT = 0.05
MIN_CONFIRMATIONS = 3
MAX_QUOTE_STAKE = 50.0
ROUTE_COOLDOWN_SECONDS = 60
MIN_BASE_SHARE_PERCENT = 10.0
MAX_BASE_SHARE_PERCENT = 30.0

def atomic_json(path, payload):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)

def read_json(path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default

def quotes():
    payload = read_json(SNAPSHOT, {})
    result = {}
    for q in payload.get("quotes", []):
        if str(q.get("base", "")).upper() != BASE_ASSET or str(q.get("quote", "")).upper() != QUOTE_ASSET:
            continue
        exchange = str(q.get("exchange", "")).lower()
        try:
            bid, ask = float(q["bid"]), float(q["ask"])
        except Exception:
            continue
        if exchange in EXCHANGES and 0 < bid <= ask:
            result[exchange] = {"bid": bid, "ask": ask, "mid": (bid + ask) / 2.0}
    return result

def initialize():
    market = quotes()
    if any(ex not in market for ex in EXCHANGES):
        return None
    balances = {}
    initial_prices = {}
    for ex in EXCHANGES:
        price = market[ex]["ask"]
        initial_prices[ex] = price
        balances[f"{ex}:{QUOTE_ASSET}"] = INITIAL_QUOTE_PER_EXCHANGE
        balances[f"{ex}:{BASE_ASSET}"] = INITIAL_BASE_VALUE_PER_EXCHANGE / price
    now = datetime.now().isoformat(timespec="seconds")
    state = {
        "model": MODEL,
        "started_at": now,
        "initial_equity_usdt": 3000.0,
        "balances": balances,
        "initial_prices": initial_prices,
        "processed": [],
        "last_trade_by_route": {},
        "real_trading": False,
    }
    atomic_json(STATE, state)
    return state

def fingerprint(signal):
    route = signal.get("route", {})
    identity = [signal.get("detected_at"), route.get("pair"), route.get("buy_exchange"), route.get("sell_exchange")]
    return hashlib.sha256(json.dumps(identity).encode()).hexdigest()

def parse_time(value):
    try:
        return datetime.fromisoformat(str(value)).timestamp()
    except Exception:
        return 0.0

def existing_rows():
    rows = []
    if LEDGER.exists():
        for line in LEDGER.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows

def equity(balances, market):
    total = 0.0
    for ex in EXCHANGES:
        total += float(balances.get(f"{ex}:{QUOTE_ASSET}", 0.0))
        total += float(balances.get(f"{ex}:{BASE_ASSET}", 0.0)) * float(market.get(ex, {}).get("mid", 0.0))
    return total

def process_once():
    JOURNAL.mkdir(parents=True, exist_ok=True)
    state = read_json(STATE, {})
    if state.get("model") != MODEL:
        state = initialize()
    if not state:
        summary = {"ok": True, "status": "WAITING_FOR_SOL_USDT_QUOTES", "model": MODEL, "real_trading": False}
        atomic_json(SUMMARY, summary)
        return summary
    balances = {k: float(v) for k, v in state.get("balances", {}).items()}
    processed = set(state.get("processed", []))
    last_trade = {k: float(v) for k, v in state.get("last_trade_by_route", {}).items()}
    started_ts = parse_time(state.get("started_at"))
    added = 0
    rejected = defaultdict(int)
    rows = existing_rows()
    if SOURCE.exists():
        for line in SOURCE.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                signal = json.loads(line)
            except json.JSONDecodeError:
                continue
            route = signal.get("route", {})
            detected_ts = parse_time(signal.get("detected_at"))
            if detected_ts < started_ts:
                continue
            key = fingerprint(signal)
            if key in processed:
                continue
            processed.add(key)
            reason = None
            pair = str(route.get("pair", "")).upper()
            buy_ex = str(route.get("buy_exchange", "")).lower()
            sell_ex = str(route.get("sell_exchange", "")).lower()
            route_key = "|".join((pair, buy_ex, sell_ex))
            if signal.get("real_trading") is not False or route.get("real_trading") is not False:
                reason = "real_trading_guard"
            elif pair != f"{BASE_ASSET}/{QUOTE_ASSET}" or buy_ex not in EXCHANGES or sell_ex not in EXCHANGES:
                reason = "unfunded_pair"
            elif route.get("confirmed") is not True or int(route.get("consecutive_confirmations", 0) or 0) < MIN_CONFIRMATIONS:
                reason = "confirmations"
            elif route.get("executable") is not True or route.get("quotes_fresh") is not True or route.get("quote_synchronized") is not True:
                reason = "execution_quality"
            elif detected_ts - last_trade.get(route_key, -1e18) < ROUTE_COOLDOWN_SECONDS:
                reason = "route_cooldown"
            try:
                quantity = float(route.get("paper_base_quantity", 0) or 0)
                ask = float(route.get("buy_ask", 0) or 0)
                bid = float(route.get("sell_bid", 0) or 0)
                buy_fee = float(route.get("buy_taker_fee_percent", 0) or 0) / 100.0
                sell_fee = float(route.get("sell_taker_fee_percent", 0) or 0) / 100.0
            except Exception:
                quantity = ask = bid = 0.0
                buy_fee = sell_fee = 0.0
            if quantity <= 0 or ask <= 0 or bid <= 0:
                reason = reason or "invalid_amount"
            max_qty_stake = MAX_QUOTE_STAKE * (1.0 - buy_fee) / ask if ask > 0 else 0.0
            quantity = min(quantity, max_qty_stake)
            buy_cost = quantity * ask / max(1e-12, 1.0 - buy_fee)
            sell_revenue = quantity * bid * (1.0 - sell_fee)
            profit = sell_revenue - buy_cost
            net_percent = profit / buy_cost * 100.0 if buy_cost > 0 else -999.0
            buy_wallet = f"{buy_ex}:{QUOTE_ASSET}"
            sell_wallet = f"{sell_ex}:{BASE_ASSET}"
            if net_percent < MIN_NET_PERCENT:
                reason = reason or "profit_threshold"
            elif balances.get(buy_wallet, 0.0) + 1e-12 < buy_cost:
                reason = reason or "insufficient_quote_inventory"
            elif balances.get(sell_wallet, 0.0) + 1e-12 < quantity:
                reason = reason or "insufficient_base_inventory"
            # Keep each exchange funded on both sides by value, not merely by
            # a percentage of its initial token count. This prevents inventory
            # drift from concentrating nearly all account equity in SOL or USDT.
            minimum_share = MIN_BASE_SHARE_PERCENT
            maximum_base_share = MAX_BASE_SHARE_PERCENT
            buy_quote_after = balances.get(buy_wallet, 0.0) - buy_cost
            buy_base_after = balances.get(f"{buy_ex}:{BASE_ASSET}", 0.0) + quantity
            buy_equity_after = buy_quote_after + buy_base_after * ask
            buy_base_share_after = (
                buy_base_after * ask / buy_equity_after * 100.0
                if buy_equity_after > 0 else 100.0
            )
            sell_base_after = balances.get(sell_wallet, 0.0) - quantity
            sell_quote_after = balances.get(f"{sell_ex}:{QUOTE_ASSET}", 0.0) + sell_revenue
            sell_equity_after = sell_quote_after + sell_base_after * bid
            sell_base_share_after = (
                sell_base_after * bid / sell_equity_after * 100.0
                if sell_equity_after > 0 else 0.0
            )
            if reason is None and buy_base_share_after > maximum_base_share + 1e-9:
                reason = "quote_inventory_reserve"
            elif reason is None and sell_base_share_after < minimum_share - 1e-9:
                reason = "base_inventory_reserve"
            if reason:
                rejected[reason] += 1
                continue
            balances[buy_wallet] -= buy_cost
            balances[f"{buy_ex}:{BASE_ASSET}"] = balances.get(f"{buy_ex}:{BASE_ASSET}", 0.0) + quantity
            balances[sell_wallet] -= quantity
            balances[f"{sell_ex}:{QUOTE_ASSET}"] = balances.get(f"{sell_ex}:{QUOTE_ASSET}", 0.0) + sell_revenue
            last_trade[route_key] = detected_ts
            record = {
                "recorded_at": datetime.now().isoformat(timespec="seconds"),
                "detected_at": signal.get("detected_at"),
                "model": MODEL,
                "pair": pair,
                "buy_exchange": buy_ex,
                "sell_exchange": sell_ex,
                "base_quantity": quantity,
                "buy_cost_usdt": buy_cost,
                "sell_revenue_usdt": sell_revenue,
                "realized_profit_usdt": profit,
                "net_profit_percent": net_percent,
                "consecutive_confirmations": route.get("consecutive_confirmations"),
                "real_trading": False,
            }
            with LEDGER.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            rows.append(record)
            added += 1
    market = quotes()
    initial_prices = {k: float(v) for k, v in state.get("initial_prices", {}).items()}
    last_prices = {k: float(v) for k, v in state.get("last_prices", {}).items()}
    for ex, quote in market.items():
        mid = float(quote.get("mid", 0.0) or 0.0)
        if mid > 0:
            last_prices[ex] = mid
    valuation_market = {
        ex: {"mid": float(last_prices.get(ex) or initial_prices.get(ex) or 0.0)}
        for ex in EXCHANGES
    }
    realized = sum(float(row.get("realized_profit_usdt", 0) or 0) for row in rows)
    gross_turnover = sum(float(row.get("buy_cost_usdt", 0) or 0) for row in rows)
    profitable_trades = sum(1 for row in rows if float(row.get("realized_profit_usdt", 0) or 0) > 0)
    average_trade_profit = realized / len(rows) if rows else 0.0
    realized_return_percent = realized / gross_turnover * 100.0 if gross_turnover > 0 else 0.0
    current_equity = equity(balances, valuation_market)
    total_mark_to_market_pnl = current_equity - float(state.get("initial_equity_usdt", 3000.0))
    inventory_market_pnl = total_mark_to_market_pnl - realized
    inventory_by_exchange = {}
    rebalance_required = []
    for ex in EXCHANGES:
        quote_balance = float(balances.get(f"{ex}:{QUOTE_ASSET}", 0.0))
        base_balance = float(balances.get(f"{ex}:{BASE_ASSET}", 0.0))
        mid = float(valuation_market.get(ex, {}).get("mid", 0.0))
        base_value = base_balance * mid
        exchange_equity = quote_balance + base_value
        base_share = base_value / exchange_equity * 100.0 if exchange_equity > 0 else 0.0
        low_assets = []
        if base_share > MAX_BASE_SHARE_PERCENT + 1e-9:
            low_assets.append(QUOTE_ASSET)
        if base_share < MIN_BASE_SHARE_PERCENT - 1e-9:
            low_assets.append(BASE_ASSET)
        if low_assets:
            rebalance_required.append({"exchange": ex, "low_assets": low_assets})
        inventory_by_exchange[ex] = {
            "quote_balance_usdt": quote_balance,
            "base_balance_sol": base_balance,
            "base_value_usdt": base_value,
            "mark_to_market_equity_usdt": exchange_equity,
            "base_share_percent": base_share,
            "low_assets": low_assets,
        }
    state.update({
        "balances": balances,
        "processed": sorted(processed),
        "last_trade_by_route": last_trade,
        "last_prices": last_prices,
        "updated_at": datetime.now().isoformat(timespec="seconds"),
    })
    atomic_json(STATE, state)
    summary = {
        "ok": True,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "model": MODEL,
        "mode": "INVENTORY_PAPER_ONLY",
        "real_trading": False,
        "started_at": state.get("started_at"),
        "initial_equity_usdt": float(state.get("initial_equity_usdt", 3000.0)),
        "mark_to_market_equity_usdt": current_equity,
        "realized_arbitrage_profit_usdt": realized,
        "gross_arbitrage_turnover_usdt": gross_turnover,
        "average_trade_profit_usdt": average_trade_profit,
        "realized_return_on_turnover_percent": realized_return_percent,
        "profitable_trades": profitable_trades,
        "trade_win_rate_percent": profitable_trades / len(rows) * 100.0 if rows else 0.0,
        "total_mark_to_market_pnl_usdt": total_mark_to_market_pnl,
        "inventory_market_pnl_usdt": inventory_market_pnl,
        "pnl_explanation": "Total mark-to-market PnL = realized arbitrage PnL + inventory market/valuation PnL.",
        "paper_trades": len(rows),
        "balances": dict(sorted(balances.items())),
        "inventory_assets": [QUOTE_ASSET, BASE_ASSET],
        "minimum_net_profit_percent": MIN_NET_PERCENT,
        "minimum_confirmations": MIN_CONFIRMATIONS,
        "maximum_quote_stake": MAX_QUOTE_STAKE,
        "route_cooldown_seconds": ROUTE_COOLDOWN_SECONDS,
        "minimum_base_share_percent": MIN_BASE_SHARE_PERCENT,
        "maximum_base_share_percent": MAX_BASE_SHARE_PERCENT,
        "inventory_by_exchange": inventory_by_exchange,
        "rebalance_required": rebalance_required,
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

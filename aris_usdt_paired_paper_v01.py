#!/usr/bin/env python3
"""USDT-only paired paper executor. Never places real orders."""
from __future__ import annotations

import json
import os
import time
from datetime import datetime
from pathlib import Path

ROOT = Path.home() / "Arbitrage"
JOURNAL = ROOT / "journal"
SOURCE = JOURNAL / "cross_exchange_positive_v01.jsonl"
STATE = JOURNAL / "usdt_paired_paper_state_v01.json"
LEDGER = JOURNAL / "usdt_paired_paper_ledger_v01.jsonl"
SCREEN = JOURNAL / "usdt_paired_paper_screen_v01.log"
PIDFILE = ROOT / "guardian_state" / "usdt_paired_paper.pid"

MODEL = "usdt-paired-paper-v01"
START_BALANCE_USDT = 2999.161871185964
MIN_NET_PERCENT = 0.10
MAX_STAKE_USDT = 25.0
MIN_CONFIRMATIONS = 3
MAX_SIGNAL_AGE_SECONDS = 15.0


def now() -> str:
    return datetime.now().isoformat(timespec="seconds")


def parse_time(value: object) -> float:
    try:
        return datetime.fromisoformat(str(value)).timestamp()
    except Exception:
        return 0.0


def atomic_json(path: Path, payload: dict) -> None:
    tmp = path.with_name(f".{path.name}.{os.getpid()}.{time.time_ns()}.tmp")
    try:
        tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        os.replace(tmp, path)
    finally:
        try:
            tmp.unlink()
        except FileNotFoundError:
            pass


def read_state() -> dict:
    try:
        state = json.loads(STATE.read_text(encoding="utf-8"))
        if state.get("model") == MODEL:
            return state
    except Exception:
        pass
    state = {
        "model": MODEL,
        "started_at": now(),
        "started_ts": time.time(),
        "balance_usdt": START_BALANCE_USDT,
        "realized_profit_usdt": 0.0,
        "trades": 0,
        "processed": [],
        "real_trading": False,
    }
    atomic_json(STATE, state)
    return state


def append_screen(record: dict) -> None:
    block = (
        "\n[A.R.I.S. PAIRED PAPER TRADE]\n"
        f"TIME: {record['recorded_at']}\n"
        f"BUY : {record['stake_usdt']:.4f} USDT -> {record['base']}\n"
        f"AT  : {record['buy_exchange'].upper()} @ {record['buy_ask']:.10g}\n"
        f"SELL: {record['base']} -> {record['final_usdt']:.4f} USDT\n"
        f"AT  : {record['sell_exchange'].upper()} @ {record['sell_bid']:.10g}\n"
        f"NET : {record['profit_usdt']:+.6f} USDT ({record['net_percent']:+.4f}%)\n"
        f"BALANCE: {record['balance_usdt']:.6f} USDT\n"
        "STATUS: COMPLETED | HOLDINGS: USDT ONLY | REAL: NO\n"
    )
    with SCREEN.open("a", encoding="utf-8") as handle:
        handle.write(block)


def process_once() -> dict:
    JOURNAL.mkdir(parents=True, exist_ok=True)
    state = read_state()
    processed = set(state.get("processed", []))
    added = 0
    if SOURCE.exists():
        for line in SOURCE.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                signal = json.loads(line)
                route = signal["route"]
            except Exception:
                continue
            detected_at = str(signal.get("detected_at", ""))
            identity = "|".join((detected_at, str(route.get("pair")), str(route.get("buy_exchange")), str(route.get("sell_exchange"))))
            if identity in processed:
                continue
            processed.add(identity)
            detected_ts = parse_time(detected_at)
            if detected_ts < float(state.get("started_ts", 0)) or time.time() - detected_ts > MAX_SIGNAL_AGE_SECONDS:
                continue
            pair = str(route.get("pair", "")).upper()
            if not pair.endswith("/USDT"):
                continue
            if signal.get("real_trading") is not False or route.get("real_trading") is not False:
                continue
            if route.get("confirmed") is not True or int(route.get("consecutive_confirmations", 0) or 0) < MIN_CONFIRMATIONS:
                continue
            if not all(route.get(key) is True for key in ("executable", "quotes_fresh", "quote_synchronized", "minimum_order_verified")):
                continue
            net_percent = float(route.get("net_profit_percent", -999) or -999)
            if net_percent < MIN_NET_PERCENT:
                continue
            source_cost = float(route.get("paper_buy_cost", 0) or 0)
            source_final = float(route.get("paper_sell_revenue_after_fee", 0) or 0)
            if source_cost <= 0 or source_final <= source_cost:
                continue
            stake = min(MAX_STAKE_USDT, float(state["balance_usdt"]), source_cost)
            scale = stake / source_cost
            final_usdt = source_final * scale
            # The published route net percentage includes the execution buffer.
            buffered_final = stake * (1.0 + net_percent / 100.0)
            final_usdt = min(final_usdt, buffered_final)
            profit = final_usdt - stake
            if profit <= 0:
                continue
            state["balance_usdt"] = float(state["balance_usdt"]) + profit
            state["realized_profit_usdt"] = float(state["realized_profit_usdt"]) + profit
            state["trades"] = int(state["trades"]) + 1
            record = {
                "recorded_at": now(), "detected_at": detected_at, "model": MODEL,
                "pair": pair, "base": pair.split("/", 1)[0],
                "buy_exchange": str(route.get("buy_exchange")),
                "sell_exchange": str(route.get("sell_exchange")),
                "buy_ask": float(route.get("buy_ask")), "sell_bid": float(route.get("sell_bid")),
                "stake_usdt": stake, "final_usdt": final_usdt,
                "profit_usdt": profit, "net_percent": net_percent,
                "balance_usdt": state["balance_usdt"],
                "execution": "paired_atomic_template", "real_trading": False,
            }
            with LEDGER.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            append_screen(record)
            added += 1
    state["processed"] = sorted(processed)[-5000:]
    state["updated_at"] = now()
    atomic_json(STATE, state)
    return {"ok": True, "model": MODEL, "added": added, "trades": state["trades"],
            "balance_usdt": state["balance_usdt"], "profit_usdt": state["realized_profit_usdt"],
            "minimum_net_percent": MIN_NET_PERCENT, "real_trading": False}


def run_forever() -> None:
    while True:
        try:
            process_once()
        except Exception as exc:
            with SCREEN.open("a", encoding="utf-8") as handle:
                handle.write(f"{now()} ERROR {type(exc).__name__}: {exc}\n")
        time.sleep(1)


if __name__ == "__main__":
    if "--daemon" not in __import__("sys").argv:
        print(json.dumps(process_once(), ensure_ascii=False, indent=2))
    else:
        PIDFILE.parent.mkdir(parents=True, exist_ok=True)
        try:
            old_pid = int(PIDFILE.read_text(encoding="utf-8"))
            os.kill(old_pid, 0)
            print(f"paired paper daemon already running pid={old_pid}")
            raise SystemExit(0)
        except (OSError, ValueError, FileNotFoundError):
            pass
        pid = os.fork()
        if pid:
            print(f"paired paper daemon starting pid={pid}")
            raise SystemExit(0)
        os.setsid()
        null = os.open("/dev/null", os.O_RDWR)
        os.dup2(null, 0)
        os.dup2(null, 1)
        os.dup2(null, 2)
        PIDFILE.write_text(str(os.getpid()), encoding="utf-8")
        try:
            run_forever()
        finally:
            PIDFILE.unlink(missing_ok=True)

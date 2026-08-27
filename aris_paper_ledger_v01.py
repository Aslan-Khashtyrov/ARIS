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
SIGNALS = JOURNAL / "cycle_opportunities_v01.jsonl"
LEDGER = JOURNAL / "paper_ledger_v01.jsonl"
STATE = JOURNAL / "paper_ledger_state_v01.json"
SUMMARY = JOURNAL / "paper_ledger_summary_v01.json"
MIN_PROFIT_PERCENT = 0.30
MIN_CONFIRMATIONS = 3


def atomic_json(path, payload):
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temp.replace(path)


def fingerprint(signal):
    route = signal.get("cycle", {}).get("route", [])
    identity = {
        "detected_at": signal.get("detected_at"),
        "route": [(item.get("src"), item.get("dst"), item.get("kind")) for item in route],
    }
    return hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()


def load_processed():
    try:
        return set(json.loads(STATE.read_text(encoding="utf-8")).get("processed", []))
    except Exception:
        return set()


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


def build_summary(rows):
    totals = defaultdict(float)
    for row in rows:
        totals[row["asset"]] += float(row["paper_profit_units"])
    return {
        "ok": True,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "PAPER_ONLY",
        "real_trading": False,
        "paper_trades": len(rows),
        "profit_by_asset": dict(sorted(totals.items())),
        "minimum_profit_percent": MIN_PROFIT_PERCENT,
        "minimum_confirmations": MIN_CONFIRMATIONS,
    }


def validate_cycle(cycle):
    try:
        profit_percent = float(cycle.get("profit_percent", -999))
        start_units = float(cycle.get("paper_start_units", 0) or 0)
        end_units = float(cycle.get("paper_end_units", 0) or 0)
    except (TypeError, ValueError):
        return False, "invalid_numeric_fields"

    required_flags = {
        "executable": cycle.get("executable") is True,
        "capacity_verified": cycle.get("capacity_verified") is True,
        "minimum_order_verified": cycle.get("minimum_order_verified") is True,
        "quote_synchronized": cycle.get("quote_synchronized") is True,
        "quotes_fresh": cycle.get("quotes_fresh") is True,
        "no_transfer": cycle.get("contains_transfer") is False,
    }
    for name, valid in required_flags.items():
        if not valid:
            return False, name

    legs = cycle.get("paper_legs")
    if not isinstance(legs, list) or len(legs) < 3:
        return False, "paper_legs"
    if any(leg.get("within_top_of_book_capacity") is not True for leg in legs):
        return False, "leg_capacity"
    if any(leg.get("within_capacity_buffer") is not True for leg in legs):
        return False, "leg_capacity_buffer"
    if any(leg.get("minimum_order_met") is not True for leg in legs):
        return False, "leg_minimum_order"

    if start_units <= 0 or end_units <= 0:
        return False, "paper_amounts"
    recomputed = (end_units / start_units - 1.0) * 100.0
    if abs(recomputed - profit_percent) > 1e-6:
        return False, "profit_mismatch"
    return True, "validated"


def process_once():
    JOURNAL.mkdir(parents=True, exist_ok=True)
    processed = load_processed()
    added = 0
    rejected = defaultdict(int)
    if SIGNALS.exists():
        for line in SIGNALS.read_text(encoding="utf-8", errors="replace").splitlines():
            try:
                signal = json.loads(line)
            except json.JSONDecodeError:
                continue
            key = fingerprint(signal)
            if key in processed or signal.get("real_trading") is not False:
                continue
            cycle = signal.get("cycle", {})
            confirmations = int(signal.get("confirmation_snapshots", 0) or 0)
            profit_percent = float(cycle.get("profit_percent", -999))
            start_units = float(cycle.get("paper_start_units", 0) or 0)
            end_units = float(cycle.get("paper_end_units", 0) or 0)
            asset = str(cycle.get("paper_asset", "")).upper()
            valid_cycle, validation_reason = validate_cycle(cycle)
            if confirmations < MIN_CONFIRMATIONS:
                validation_reason = "confirmations"
                valid_cycle = False
            elif profit_percent < MIN_PROFIT_PERCENT:
                validation_reason = "profit_threshold"
                valid_cycle = False
            elif not asset:
                validation_reason = "asset"
                valid_cycle = False
            if not valid_cycle:
                rejected[validation_reason] += 1
                processed.add(key)
                continue
            record = {
                "fingerprint": key,
                "recorded_at": datetime.now().isoformat(timespec="seconds"),
                "detected_at": signal.get("detected_at"),
                "asset": asset,
                "paper_start_units": start_units,
                "paper_end_units": end_units,
                "paper_profit_units": end_units - start_units,
                "profit_percent": profit_percent,
                "confirmation_snapshots": confirmations,
                "capacity_start_units": cycle.get("capacity_start_units"),
                "route": cycle.get("route", []),
                "real_trading": False,
            }
            with LEDGER.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False) + "\n")
            processed.add(key)
            added += 1
    atomic_json(STATE, {"processed": sorted(processed), "updated_at": datetime.now().isoformat(timespec="seconds")})
    rows = existing_rows()
    summary = build_summary(rows)
    summary["added_this_cycle"] = added
    summary["rejected_this_cycle"] = sum(rejected.values())
    summary["rejection_reasons"] = dict(sorted(rejected.items()))
    summary["validation_model"] = "executable-paper-v04"
    atomic_json(SUMMARY, summary)
    return summary


def run_forever():
    while True:
        try:
            process_once()
        except Exception as exc:
            atomic_json(SUMMARY, {"ok": False, "time": datetime.now().isoformat(timespec="seconds"), "error": f"{type(exc).__name__}: {exc}", "real_trading": False})
        time.sleep(15)


if __name__ == "__main__":
    print(json.dumps(process_once(), ensure_ascii=False, indent=2))

from pathlib import Path
from datetime import datetime
import argparse
import json
import math
import sys

ROOT = Path.home() / "Arbitrage"
JOURNAL = ROOT / "journal"
SNAPSHOT = JOURNAL / "cycle_quotes_v01.json"
REPORT = JOURNAL / "cycle_report_v01.json"
ANCHORS = ("USDT", "USDC", "USD", "EUR", "RUB", "BTC")
MAX_LEGS = 4
MIN_PROFIT_PERCENT = 0.10
PAPER_STAKES = {"USD": 100.0, "USDT": 100.0, "USDC": 100.0, "EUR": 100.0, "RUB": 10000.0, "BTC": 0.001}
MIN_EXECUTABLE = {"USD": 25.0, "USDT": 25.0, "USDC": 25.0, "EUR": 25.0, "RUB": 2500.0, "BTC": 0.00025}
EXECUTION_BUFFER_PERCENT = 0.05
MAX_QUOTE_SKEW_SECONDS = 3.0

def trade_edges(quotes):
    edges = []
    for q in quotes:
        try:
            exchange = str(q["exchange"]).lower()
            base = str(q["base"]).upper()
            quote = str(q["quote"]).upper()
            bid = float(q["bid"])
            ask = float(q["ask"])
            bid_size = float(q.get("bid_size", 0) or 0)
            ask_size = float(q.get("ask_size", 0) or 0)
            fee = float(q.get("taker_fee", 0))
            quote_updated_at = float(q.get("updated_at", 0) or 0)
        except (KeyError, TypeError, ValueError):
            continue
        if min(bid, ask) <= 0 or bid > ask or not 0 <= fee < 1:
            continue
        base_node = f"{exchange}:{base}"
        quote_node = f"{exchange}:{quote}"
        edges.append({
            "kind": "TRADE", "exchange": exchange, "pair": f"{base}/{quote}",
            "src": base_node, "dst": quote_node,
            "rate": bid * (1 - fee), "capacity_src": bid_size,
            "side": "SELL", "fee": fee, "quote_updated_at": quote_updated_at,
        })
        edges.append({
            "kind": "TRADE", "exchange": exchange, "pair": f"{base}/{quote}",
            "src": quote_node, "dst": base_node,
            "rate": (1 / ask) * (1 - fee), "capacity_src": ask * ask_size,
            "side": "BUY", "fee": fee, "quote_updated_at": quote_updated_at,
        })
    return edges

def transfer_edges(transfers):
    edges = []
    for t in transfers:
        try:
            asset = str(t["asset"]).upper()
            source = str(t["from_exchange"]).lower()
            target = str(t["to_exchange"]).lower()
            fee_amount = float(t.get("fee_amount", 0))
            reference_amount = float(t["reference_amount"])
            delay = float(t.get("delay_seconds", 0))
            enabled = bool(t.get("enabled", False))
        except (KeyError, TypeError, ValueError):
            continue
        if not enabled or reference_amount <= fee_amount or delay < 0:
            continue
        edges.append({
            "kind": "TRANSFER", "asset": asset,
            "src": f"{source}:{asset}", "dst": f"{target}:{asset}",
            "rate": (reference_amount - fee_amount) / reference_amount,
            "capacity_src": reference_amount, "fee_amount": fee_amount,
            "delay_seconds": delay,
        })
    return edges

def find_cycles(edges, anchors=ANCHORS, max_legs=MAX_LEGS):
    adjacency = {}
    for edge in edges:
        adjacency.setdefault(edge["src"], []).append(edge)
    found = []
    start_nodes = [node for node in adjacency if node.split(":", 1)[1] in anchors]
    for start in start_nodes:
        stack = [(start, 1.0, float("inf"), [], {start})]
        while stack:
            node, amount, capacity, path, visited = stack.pop()
            if len(path) >= max_legs:
                continue
            for edge in adjacency.get(node, []):
                next_amount = amount * edge["rate"]
                next_capacity = min(capacity, edge.get("capacity_src", float("inf")) / amount if amount else 0)
                next_path = path + [edge]
                if edge["dst"] == start and len(next_path) >= 2:
                    profit = (next_amount - 1) * 100
                    trade_legs = [item for item in next_path if item["kind"] == "TRADE"]
                    quote_times = [item.get("quote_updated_at", 0) for item in trade_legs if item.get("quote_updated_at", 0) > 0]
                    timestamps_complete = len(quote_times) == len(trade_legs) and bool(trade_legs)
                    quote_skew = (max(quote_times) - min(quote_times)) if timestamps_complete else None
                    found.append({
                        "start": start,
                        "legs": len(next_path),
                        "profit_percent": profit,
                        "capacity_start_units": next_capacity,
                        "contains_transfer": any(item["kind"] == "TRANSFER" for item in next_path),
                        "quote_skew_seconds": quote_skew,
                        "maximum_quote_skew_seconds": MAX_QUOTE_SKEW_SECONDS,
                        "quote_synchronized": timestamps_complete and quote_skew <= MAX_QUOTE_SKEW_SECONDS,
                        "route": next_path,
                    })
                    continue
                if edge["dst"] not in visited:
                    stack.append((edge["dst"], next_amount, next_capacity, next_path, visited | {edge["dst"]}))
    unique = {}
    for cycle in found:
        signature = tuple((e["src"], e["dst"], e["kind"]) for e in cycle["route"])
        reverse = tuple(reversed(tuple((b, a, k) for a, b, k in signature)))
        key = min(signature, reverse)
        if key not in unique or cycle["profit_percent"] > unique[key]["profit_percent"]:
            unique[key] = cycle
    return sorted(unique.values(), key=lambda item: item["profit_percent"], reverse=True)

def simulate_route(start_units, route):
    amount = float(start_units)
    legs = []
    capacity_verified = True
    bottleneck = None
    highest_utilization = -1.0
    for index, edge in enumerate(route, start=1):
        capacity = float(edge.get("capacity_src", 0) or 0)
        tolerance = max(1e-12, abs(capacity) * 1e-12)
        within_capacity = capacity > 0 and amount <= capacity + tolerance
        utilization = (amount / capacity * 100) if capacity > 0 and math.isfinite(capacity) else None
        amount_out = amount * float(edge["rate"])
        leg = {
            "leg": index,
            "exchange": edge.get("exchange"),
            "pair": edge.get("pair"),
            "side": edge.get("side"),
            "src": edge["src"],
            "dst": edge["dst"],
            "amount_in": amount,
            "amount_out": amount_out,
            "capacity_src": capacity,
            "capacity_utilization_percent": utilization,
            "within_top_of_book_capacity": within_capacity,
            "quote_updated_at": edge.get("quote_updated_at"),
        }
        legs.append(leg)
        capacity_verified = capacity_verified and within_capacity
        if utilization is not None and utilization > highest_utilization:
            highest_utilization = utilization
            bottleneck = {
                "leg": index,
                "exchange": edge.get("exchange"),
                "pair": edge.get("pair"),
                "side": edge.get("side"),
                "capacity_utilization_percent": utilization,
            }
        amount = amount_out
    return {
        "legs": legs,
        "end_units_before_buffer": amount,
        "capacity_verified": capacity_verified,
        "bottleneck": bottleneck,
    }


def analyze(payload):
    edges = trade_edges(payload.get("quotes", [])) + transfer_edges(payload.get("transfers", []))
    cycles = find_cycles(edges)
    for cycle in cycles:
        start_asset = cycle["start"].split(":", 1)[1]
        requested = PAPER_STAKES.get(start_asset, 1.0)
        minimum = MIN_EXECUTABLE.get(start_asset, requested)
        start_units = max(0.0, min(requested, cycle["capacity_start_units"]))
        raw_profit = cycle["profit_percent"]
        conservative_profit = raw_profit - EXECUTION_BUFFER_PERCENT
        simulation = simulate_route(start_units, cycle["route"])
        cycle["raw_profit_percent"] = raw_profit
        cycle["execution_buffer_percent"] = EXECUTION_BUFFER_PERCENT
        cycle["profit_percent"] = conservative_profit
        cycle["paper_start_units"] = start_units
        cycle["paper_end_before_buffer_units"] = simulation["end_units_before_buffer"]
        cycle["paper_end_units"] = start_units * (1 + conservative_profit / 100)
        cycle["paper_profit_units"] = cycle["paper_end_units"] - start_units
        cycle["paper_asset"] = start_asset
        cycle["paper_legs"] = simulation["legs"]
        cycle["capacity_verified"] = simulation["capacity_verified"]
        cycle["bottleneck_leg"] = simulation["bottleneck"]
        cycle["minimum_executable_units"] = minimum
        cycle["executable"] = start_units >= minimum and simulation["capacity_verified"] and cycle["quote_synchronized"]
    cycles.sort(key=lambda item: item["profit_percent"], reverse=True)
    opportunities = [c for c in cycles if c["profit_percent"] >= MIN_PROFIT_PERCENT and c["executable"]]
    return {
        "ok": True,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": "PAPER_ONLY",
        "real_trading": False,
        "quotes": len(payload.get("quotes", [])),
        "edges": len(edges),
        "cycles_checked": len(cycles),
        "opportunities": opportunities[:50],
        "best_cycle": cycles[0] if cycles else None,
        "minimum_profit_percent": MIN_PROFIT_PERCENT,
        "execution_buffer_percent": EXECUTION_BUFFER_PERCENT,
        "maximum_quote_skew_seconds": MAX_QUOTE_SKEW_SECONDS,
        "minimum_executable": MIN_EXECUTABLE,
        "warnings": [
            "Top-of-book capacity must meet the configured minimum executable amount.",
            "A conservative execution buffer is deducted from raw profit.",
            "All trade-leg quotes must fit the configured timestamp-skew window.",
            "Order-book depth can change before all legs execute.",
            "Transfer routes are informational and include delay risk.",
            "No orders, payments, transfers or withdrawals are performed."
        ],
    }

def self_test():
    payload = {
        "quotes": [
            {"exchange":"test","base":"BTC","quote":"USDT","bid":100,"ask":101,"bid_size":10,"ask_size":10,"taker_fee":0,"updated_at":1000.0},
            {"exchange":"test","base":"ETH","quote":"BTC","bid":0.051,"ask":0.052,"bid_size":100,"ask_size":100,"taker_fee":0},
            {"exchange":"test","base":"ETH","quote":"USDT","bid":5.4,"ask":5.5,"bid_size":100,"ask_size":100,"taker_fee":0}
        ],
        "transfers": []
    }
    result = analyze(payload)
    assert result["cycles_checked"] > 0
    assert result["best_cycle"] is not None
    assert result["best_cycle"]["paper_legs"]
    assert result["best_cycle"]["capacity_verified"] is True
    assert result["best_cycle"]["bottleneck_leg"] is not None
    assert result["best_cycle"]["quote_synchronized"] is True
    return {"ok": True, "cycles_checked": result["cycles_checked"], "best_profit_percent": result["best_cycle"]["profit_percent"]}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        print(json.dumps(self_test(), ensure_ascii=False, indent=2))
        return 0
    JOURNAL.mkdir(parents=True, exist_ok=True)
    if not SNAPSHOT.exists():
        result = {"ok": True, "status": "WAITING_FOR_NORMALIZED_ORDER_BOOKS", "real_trading": False, "opportunities": []}
    else:
        result = analyze(json.loads(SNAPSHOT.read_text(encoding="utf-8")))
    REPORT.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0

if __name__ == "__main__":
    sys.exit(main())

from datetime import datetime
import json
import os
import csv
import threading
import time
import websocket

VERSION = "0.1.7"

COINBASE_URL = "wss://advanced-trade-ws.coinbase.com"
KRAKEN_URL = "wss://ws.kraken.com/v2"

MAX_PRICE_AGE_SECONDS = 5
RECONNECT_DELAY_SECONDS = 3
MAX_RECONNECT_DELAY_SECONDS = 30
SOCKET_RECV_TIMEOUT_SECONDS = 15
SCAN_INTERVAL_SECONDS = 1

# Estimated/public fee assumptions for monitoring.
# Replace these with the exact current fees from your own account tiers.
FEES = {
    "Coinbase": {
        "maker": 0.0040,  # 0.40%
        "taker": 0.0060,  # 0.60%
    },
    "Kraken": {
        "maker": 0.0040,  # 0.40%
        "taker": 0.0080,  # 0.80%
    },
}

SCENARIOS = [
    {
        "name": "TAKER->TAKER",
        "buy_fee_type": "taker",
        "sell_fee_type": "taker",
    },
    {
        "name": "MAKER->TAKER",
        "buy_fee_type": "maker",
        "sell_fee_type": "taker",
    },
    {
        "name": "MAKER->MAKER",
        "buy_fee_type": "maker",
        "sell_fee_type": "maker",
    },
]

TEST_CAPITAL_USD = [100, 500, 1000]

LOG_DIR = "journal"
OPPORTUNITIES_LOG = os.path.join(LOG_DIR, "opportunities.log")

SESSION_STATS_FILE = os.path.join(LOG_DIR, "session_stats.json")
MARKET_HISTORY_FILE = os.path.join(LOG_DIR, "market_history.csv")
EVENTS_LOG = os.path.join(LOG_DIR, "events.log")

HISTORY_SAVE_INTERVAL_SECONDS = 60
STATS_SAVE_INTERVAL_SECONDS = 60
RETENTION_DAYS = 30
MAX_JOURNAL_BYTES = 100 * 1024 * 1024

last_history_save = 0.0
last_stats_save = 0.0

market = {
    "coinbase": {"bid": None, "ask": None, "updated": 0.0},
    "kraken": {"bid": None, "ask": None, "updated": 0.0},
}

lock = threading.Lock()

stats_lock = threading.Lock()

stats = {
    "cycles": 0,
    "coinbase_reconnects": 0,
    "kraken_reconnects": 0,
    "gross_spread_sum": 0.0,
    "gross_spread_min": None,
    "gross_spread_max": None,
    "best_route": None,
    "best_gross_spread": None,
    "best_taker_taker_spread": None,
    "session_started": time.time(),
}


def record_reconnect(exchange):
    with stats_lock:
        key = f"{exchange}_reconnects"
        stats[key] += 1


def update_session_stats(route):
    taker_taker = route["scenarios"][0]["net_spread_percent"]

    with stats_lock:
        stats["cycles"] += 1
        stats["gross_spread_sum"] += route["gross_spread_percent"]

        if (
            stats["gross_spread_min"] is None
            or route["gross_spread_percent"] < stats["gross_spread_min"]
        ):
            stats["gross_spread_min"] = route["gross_spread_percent"]

        if (
            stats["gross_spread_max"] is None
            or route["gross_spread_percent"] > stats["gross_spread_max"]
        ):
            stats["gross_spread_max"] = route["gross_spread_percent"]

        if (
            stats["best_taker_taker_spread"] is None
            or taker_taker > stats["best_taker_taker_spread"]
        ):
            stats["best_taker_taker_spread"] = taker_taker
            stats["best_gross_spread"] = route["gross_spread_percent"]
            stats["best_route"] = (
                f"{route['buy_exchange']} -> "
                f"{route['sell_exchange']}"
            )


def get_session_stats():
    with stats_lock:
        snapshot = stats.copy()

    cycles = snapshot["cycles"]

    if cycles > 0:
        snapshot["gross_spread_avg"] = (
            snapshot["gross_spread_sum"] / cycles
        )
    else:
        snapshot["gross_spread_avg"] = None

    snapshot["uptime_seconds"] = (
        time.time() - snapshot["session_started"]
    )

    return snapshot


def format_uptime(seconds):
    seconds = int(seconds)
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)

    if hours:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    return f"{minutes:02d}:{secs:02d}"


def print_session_stats():
    s = get_session_stats()

    print("SESSION STATS:")
    print(
        f"  Uptime: {format_uptime(s['uptime_seconds'])} | "
        f"Cycles: {s['cycles']}"
    )
    print(
        f"  Reconnects: Coinbase {s['coinbase_reconnects']} | "
        f"Kraken {s['kraken_reconnects']}"
    )

    if s["cycles"] > 0:
        print(
            f"  Gross spread min/avg/max: "
            f"{s['gross_spread_min']:+.4f}% / "
            f"{s['gross_spread_avg']:+.4f}% / "
            f"{s['gross_spread_max']:+.4f}%"
        )

        print(
            f"  Best TAKER->TAKER: "
            f"{s['best_taker_taker_spread']:+.4f}% | "
            f"{s['best_route']}"
        )


def safe_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def update_market(exchange, bid, ask):
    bid = safe_float(bid)
    ask = safe_float(ask)

    if bid is None or ask is None:
        return

    if bid <= 0 or ask <= 0 or bid > ask:
        return

    with lock:
        market[exchange]["bid"] = bid
        market[exchange]["ask"] = ask
        market[exchange]["updated"] = time.time()


def coinbase_monitor():
    reconnect_delay = RECONNECT_DELAY_SECONDS

    while True:
        ws = None

        try:
            ws = websocket.create_connection(
                COINBASE_URL,
                timeout=20,
                enable_multithread=True,
            )
            ws.settimeout(SOCKET_RECV_TIMEOUT_SECONDS)

            ws.send(json.dumps({
                "type": "subscribe",
                "product_ids": ["BTC-USD"],
                "channel": "ticker",
            }))

            ws.send(json.dumps({
                "type": "subscribe",
                "channel": "heartbeats",
            }))

            print("[Coinbase] connected")
            reconnect_delay = RECONNECT_DELAY_SECONDS

            while True:
                try:
                    raw_message = ws.recv()
                except websocket.WebSocketTimeoutException:
                    ws.ping("keepalive")
                    continue

                if not raw_message:
                    raise ConnectionError("Coinbase connection closed")

                message = json.loads(raw_message)

                if message.get("channel") != "ticker":
                    continue

                for event in message.get("events", []):
                    for ticker in event.get("tickers", []):
                        update_market(
                            "coinbase",
                            ticker.get("best_bid"),
                            ticker.get("best_ask"),
                        )

        except Exception as error:
            record_reconnect("coinbase")
            log_event("Coinbase", "RECONNECT", type(error).__name__)
            print(
                f"[Coinbase] reconnecting in {reconnect_delay}s: "
                f"{type(error).__name__}"
            )
            time.sleep(reconnect_delay)
            reconnect_delay = min(
                reconnect_delay * 2,
                MAX_RECONNECT_DELAY_SECONDS,
            )

        finally:
            if ws is not None:
                try:
                    ws.close()
                except Exception:
                    pass


def kraken_monitor():
    reconnect_delay = RECONNECT_DELAY_SECONDS

    while True:
        ws = None

        try:
            ws = websocket.create_connection(
                KRAKEN_URL,
                timeout=20,
                enable_multithread=True,
            )
            ws.settimeout(SOCKET_RECV_TIMEOUT_SECONDS)

            ws.send(json.dumps({
                "method": "subscribe",
                "params": {
                    "channel": "ticker",
                    "symbol": ["BTC/USD"],
                    "event_trigger": "bbo",
                },
            }))

            print("[Kraken] connected")
            reconnect_delay = RECONNECT_DELAY_SECONDS

            while True:
                try:
                    raw_message = ws.recv()
                except websocket.WebSocketTimeoutException:
                    ws.ping("keepalive")
                    continue

                if not raw_message:
                    raise ConnectionError("Kraken connection closed")

                message = json.loads(raw_message)

                if message.get("channel") != "ticker":
                    continue

                data = message.get("data", [])
                if not data:
                    continue

                ticker = data[0]

                update_market(
                    "kraken",
                    ticker.get("bid"),
                    ticker.get("ask"),
                )

        except Exception as error:
            record_reconnect("kraken")
            log_event("Kraken", "RECONNECT", type(error).__name__)
            print(
                f"[Kraken] reconnecting in {reconnect_delay}s: "
                f"{type(error).__name__}"
            )
            time.sleep(reconnect_delay)
            reconnect_delay = min(
                reconnect_delay * 2,
                MAX_RECONNECT_DELAY_SECONDS,
            )

        finally:
            if ws is not None:
                try:
                    ws.close()
                except Exception:
                    pass


def get_snapshot():
    with lock:
        return {
            "coinbase": market["coinbase"].copy(),
            "kraken": market["kraken"].copy(),
        }


def prices_ready(snapshot):
    values = (
        snapshot["coinbase"]["bid"],
        snapshot["coinbase"]["ask"],
        snapshot["kraken"]["bid"],
        snapshot["kraken"]["ask"],
    )
    return all(value is not None for value in values)


def prices_fresh(snapshot):
    now = time.time()

    return (
        now - snapshot["coinbase"]["updated"] <= MAX_PRICE_AGE_SECONDS
        and now - snapshot["kraken"]["updated"] <= MAX_PRICE_AGE_SECONDS
    )


def calculate_base_route(buy_exchange, sell_exchange, buy_price, sell_price):
    gross_profit = sell_price - buy_price
    gross_spread = (gross_profit / buy_price) * 100

    return {
        "buy_exchange": buy_exchange,
        "sell_exchange": sell_exchange,
        "buy_price": buy_price,
        "sell_price": sell_price,
        "gross_profit_per_btc": gross_profit,
        "gross_spread_percent": gross_spread,
    }


def calculate_scenario(route, scenario):
    buy_fee_rate = FEES[route["buy_exchange"]][scenario["buy_fee_type"]]
    sell_fee_rate = FEES[route["sell_exchange"]][scenario["sell_fee_type"]]

    buy_cost_with_fee = route["buy_price"] * (1 + buy_fee_rate)
    sell_value_after_fee = route["sell_price"] * (1 - sell_fee_rate)

    net_profit = sell_value_after_fee - buy_cost_with_fee
    net_spread = (net_profit / buy_cost_with_fee) * 100

    return {
        "scenario_name": scenario["name"],
        "buy_fee_type": scenario["buy_fee_type"],
        "sell_fee_type": scenario["sell_fee_type"],
        "buy_fee_rate": buy_fee_rate,
        "sell_fee_rate": sell_fee_rate,
        "net_profit_per_btc": net_profit,
        "net_spread_percent": net_spread,
    }


def calculate_route_with_scenarios(
    buy_exchange,
    sell_exchange,
    buy_price,
    sell_price,
):
    route = calculate_base_route(
        buy_exchange,
        sell_exchange,
        buy_price,
        sell_price,
    )

    route["scenarios"] = [
        calculate_scenario(route, scenario)
        for scenario in SCENARIOS
    ]

    return route


def calculate_best_route(snapshot):
    cb = snapshot["coinbase"]
    kr = snapshot["kraken"]

    cb_to_kr = calculate_route_with_scenarios(
        "Coinbase",
        "Kraken",
        cb["ask"],
        kr["bid"],
    )

    kr_to_cb = calculate_route_with_scenarios(
        "Kraken",
        "Coinbase",
        kr["ask"],
        cb["bid"],
    )

    cb_score = cb_to_kr["scenarios"][0]["net_spread_percent"]
    kr_score = kr_to_cb["scenarios"][0]["net_spread_percent"]

    if cb_score >= kr_score:
        return cb_to_kr

    return kr_to_cb


def calculate_capital_result(route, scenario_result, capital_usd):
    buy_fee_rate = scenario_result["buy_fee_rate"]
    sell_fee_rate = scenario_result["sell_fee_rate"]

    btc_amount = capital_usd / (
        route["buy_price"] * (1 + buy_fee_rate)
    )

    gross_sale_value = btc_amount * route["sell_price"]
    sell_fee = gross_sale_value * sell_fee_rate
    final_usd = gross_sale_value - sell_fee

    net_profit = final_usd - capital_usd
    net_return_percent = (net_profit / capital_usd) * 100

    return {
        "capital_usd": capital_usd,
        "btc_amount": btc_amount,
        "final_usd": final_usd,
        "net_profit": net_profit,
        "net_return_percent": net_return_percent,
    }


def ensure_log_directory():
    os.makedirs(LOG_DIR, exist_ok=True)


def print_scenario_results(route):
    all_results = {}

    for scenario_result in route["scenarios"]:
        name = scenario_result["scenario_name"]

        print(
            f"{name}: "
            f"${scenario_result['net_profit_per_btc']:+,.2f} "
            f"({scenario_result['net_spread_percent']:+.4f}%)"
        )

        capital_results = []

        for capital in TEST_CAPITAL_USD:
            result = calculate_capital_result(
                route,
                scenario_result,
                capital,
            )
            capital_results.append(result)

            print(
                f"  ${capital:>4}: "
                f"{result['net_profit']:+.4f} USD "
                f"({result['net_return_percent']:+.4f}%)"
            )

        all_results[name] = capital_results

    return all_results


def log_opportunity(timestamp, route, scenario_results):
    profitable_scenarios = [
        scenario
        for scenario in route["scenarios"]
        if scenario["net_spread_percent"] > 0
    ]

    if not profitable_scenarios:
        return

    with open(OPPORTUNITIES_LOG, "a", encoding="utf-8") as log:
        for scenario in profitable_scenarios:
            capital_text = " | ".join(
                (
                    f"${result['capital_usd']:.0f}: "
                    f"${result['net_profit']:+.4f} "
                    f"({result['net_return_percent']:+.4f}%)"
                )
                for result in scenario_results[
                    scenario["scenario_name"]
                ]
            )

            log.write(
                f"{timestamp} | "
                f"{scenario['scenario_name']} | "
                f"BUY {route['buy_exchange']} "
                f"{route['buy_price']:.2f} | "
                f"SELL {route['sell_exchange']} "
                f"{route['sell_price']:.2f} | "
                f"GROSS_PER_BTC "
                f"{route['gross_profit_per_btc']:.2f} | "
                f"GROSS_SPREAD "
                f"{route['gross_spread_percent']:.4f}% | "
                f"NET_PER_BTC "
                f"{scenario['net_profit_per_btc']:.2f} | "
                f"NET_SPREAD "
                f"{scenario['net_spread_percent']:.4f}% | "
                f"CAPITAL_RESULTS {capital_text}\n"
            )



def journal_size_bytes():
    total = 0
    if not os.path.isdir(LOG_DIR):
        return total

    for root, _, files in os.walk(LOG_DIR):
        for name in files:
            path = os.path.join(root, name)
            try:
                total += os.path.getsize(path)
            except OSError:
                pass

    return total


def journal_size_mb():
    return journal_size_bytes() / (1024 * 1024)


def trim_text_file_to_recent_lines(path, keep_lines):
    if not os.path.exists(path):
        return

    try:
        with open(path, "r", encoding="utf-8") as file:
            lines = file.readlines()

        if len(lines) <= keep_lines:
            return

        with open(path, "w", encoding="utf-8") as file:
            file.writelines(lines[-keep_lines:])
    except OSError:
        pass


def enforce_storage_limit():
    if journal_size_bytes() <= MAX_JOURNAL_BYTES:
        return

    # Keep recent history first. Opportunity/event logs are much smaller.
    trim_text_file_to_recent_lines(
        MARKET_HISTORY_FILE,
        RETENTION_DAYS * 24 * 60 + 1,
    )
    trim_text_file_to_recent_lines(OPPORTUNITIES_LOG, 20000)
    trim_text_file_to_recent_lines(EVENTS_LOG, 10000)


def save_session_stats():
    s = get_session_stats()

    payload = {
        "version": VERSION,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "cycles": s["cycles"],
        "coinbase_reconnects": s["coinbase_reconnects"],
        "kraken_reconnects": s["kraken_reconnects"],
        "gross_spread_min": s["gross_spread_min"],
        "gross_spread_avg": s["gross_spread_avg"],
        "gross_spread_max": s["gross_spread_max"],
        "best_taker_taker_spread": s["best_taker_taker_spread"],
        "best_route": s["best_route"],
        "journal_size_mb": round(journal_size_mb(), 4),
    }

    tmp_path = SESSION_STATS_FILE + ".tmp"

    with open(tmp_path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    os.replace(tmp_path, SESSION_STATS_FILE)


def append_market_history(timestamp, snapshot, route):
    exists = os.path.exists(MARKET_HISTORY_FILE)

    best_taker = route["scenarios"][0]["net_spread_percent"]

    with open(
        MARKET_HISTORY_FILE,
        "a",
        encoding="utf-8",
        newline="",
    ) as file:
        writer = csv.writer(file)

        if not exists:
            writer.writerow([
                "timestamp",
                "coinbase_bid",
                "coinbase_ask",
                "kraken_bid",
                "kraken_ask",
                "buy_exchange",
                "sell_exchange",
                "gross_spread_percent",
                "taker_taker_net_percent",
            ])

        writer.writerow([
            timestamp,
            f"{snapshot['coinbase']['bid']:.2f}",
            f"{snapshot['coinbase']['ask']:.2f}",
            f"{snapshot['kraken']['bid']:.2f}",
            f"{snapshot['kraken']['ask']:.2f}",
            route["buy_exchange"],
            route["sell_exchange"],
            f"{route['gross_spread_percent']:.6f}",
            f"{best_taker:.6f}",
        ])


def log_event(exchange, event_type, detail=""):
    ensure_log_directory()

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open(EVENTS_LOG, "a", encoding="utf-8") as file:
        file.write(
            f"{timestamp} | {exchange} | {event_type} | {detail}\n"
        )


def maybe_persist(timestamp, snapshot, route):
    global last_history_save
    global last_stats_save

    now = time.time()

    if now - last_history_save >= HISTORY_SAVE_INTERVAL_SECONDS:
        append_market_history(timestamp, snapshot, route)
        last_history_save = now

    if now - last_stats_save >= STATS_SAVE_INTERVAL_SECONDS:
        save_session_stats()
        enforce_storage_limit()
        last_stats_save = now


def print_storage_status():
    print(
        f"  Storage used: {journal_size_mb():.2f} MB / "
        f"{MAX_JOURNAL_BYTES / (1024 * 1024):.0f} MB"
    )


def load_market_history():
    if not os.path.exists(MARKET_HISTORY_FILE):
        return []

    rows = []

    try:
        with open(
            MARKET_HISTORY_FILE,
            "r",
            encoding="utf-8",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            for row in reader:
                try:
                    rows.append({
                        "timestamp": row["timestamp"],
                        "buy_exchange": row["buy_exchange"],
                        "sell_exchange": row["sell_exchange"],
                        "gross_spread_percent": float(
                            row["gross_spread_percent"]
                        ),
                        "taker_taker_net_percent": float(
                            row["taker_taker_net_percent"]
                        ),
                    })
                except (KeyError, TypeError, ValueError):
                    continue

    except OSError:
        return []

    return rows


def analyze_history():
    rows = load_market_history()

    if not rows:
        print("HISTORY ANALYTICS: no saved market history yet.")
        print()
        return

    gross_values = [row["gross_spread_percent"] for row in rows]
    net_values = [row["taker_taker_net_percent"] for row in rows]

    best_gross = max(
        rows,
        key=lambda row: row["gross_spread_percent"],
    )

    best_net = max(
        rows,
        key=lambda row: row["taker_taker_net_percent"],
    )

    avg_gross = sum(gross_values) / len(gross_values)
    avg_net = sum(net_values) / len(net_values)

    positive_gross = sum(value > 0 for value in gross_values)
    positive_net = sum(value > 0 for value in net_values)

    # "Near break-even" is an observation threshold only.
    near_break_even = sum(value >= -0.10 for value in net_values)

    route_counts = {}

    for row in rows:
        route = (
            f"{row['buy_exchange']} -> "
            f"{row['sell_exchange']}"
        )
        route_counts[route] = route_counts.get(route, 0) + 1

    most_common_route = max(
        route_counts,
        key=route_counts.get,
    )

    print("=" * 72)
    print("HISTORY ANALYTICS")
    print("=" * 72)
    print(f"Saved observations: {len(rows)}")
    print(
        f"Gross spread avg: {avg_gross:+.4f}% | "
        f"positive: {positive_gross}/{len(rows)}"
    )
    print(
        f"TAKER->TAKER avg: {avg_net:+.4f}% | "
        f"profitable: {positive_net}/{len(rows)}"
    )
    print(
        f"Near break-even (-0.10% or better): "
        f"{near_break_even}/{len(rows)}"
    )
    print(
        f"Best gross: {best_gross['gross_spread_percent']:+.4f}% | "
        f"{best_gross['timestamp']} | "
        f"{best_gross['buy_exchange']} -> "
        f"{best_gross['sell_exchange']}"
    )
    print(
        f"Best TAKER->TAKER: "
        f"{best_net['taker_taker_net_percent']:+.4f}% | "
        f"{best_net['timestamp']} | "
        f"{best_net['buy_exchange']} -> "
        f"{best_net['sell_exchange']}"
    )
    print(
        f"Most common route: {most_common_route} "
        f"({route_counts[most_common_route]} observations)"
    )
    print("=" * 72)
    print()

def main():
    ensure_log_directory()
    analyze_history()

    threading.Thread(
        target=coinbase_monitor,
        daemon=True,
    ).start()

    threading.Thread(
        target=kraken_monitor,
        daemon=True,
    ).start()

    print("=" * 72)
    print(f"                         ARBITRAGE v{VERSION}")
    print("                     COINBASE <-> KRAKEN")
    print("=" * 72)
    print("MONITORING ONLY")
    print("REAL TRADING: DISABLED")
    print("VIRTUAL TRADING: DISABLED")
    print("TEST CAPITAL: CALCULATION ONLY")
    print()
    print("FEE ASSUMPTIONS:")
    print(
        f"Coinbase maker "
        f"{FEES['Coinbase']['maker'] * 100:.2f}% | "
        f"taker {FEES['Coinbase']['taker'] * 100:.2f}%"
    )
    print(
        f"Kraken   maker "
        f"{FEES['Kraken']['maker'] * 100:.2f}% | "
        f"taker {FEES['Kraken']['taker'] * 100:.2f}%"
    )
    print()
    print(
        "Test capital: "
        + ", ".join(f"${value}" for value in TEST_CAPITAL_USD)
    )
    print()
    print("Press CTRL+C to stop.")
    print()

    try:
        while True:
            snapshot = get_snapshot()

            if not prices_ready(snapshot):
                print("Waiting for all BID/ASK prices...")
                time.sleep(SCAN_INTERVAL_SECONDS)
                continue

            if not prices_fresh(snapshot):
                print("Waiting for fresh prices...")
                time.sleep(SCAN_INTERVAL_SECONDS)
                continue

            route = calculate_best_route(snapshot)

            cb = snapshot["coinbase"]
            kr = snapshot["kraken"]

            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            print("-" * 72)
            print(f"[{now}]")

            print(
                f"Coinbase BID ${cb['bid']:,.2f} | "
                f"ASK ${cb['ask']:,.2f}"
            )

            print(
                f"Kraken   BID ${kr['bid']:,.2f} | "
                f"ASK ${kr['ask']:,.2f}"
            )

            print(
                f"BEST ROUTE: BUY {route['buy_exchange']} "
                f"${route['buy_price']:,.2f} -> "
                f"SELL {route['sell_exchange']} "
                f"${route['sell_price']:,.2f}"
            )

            print(
                f"GROSS PER BTC: "
                f"${route['gross_profit_per_btc']:+,.2f} "
                f"({route['gross_spread_percent']:+.4f}%)"
            )

            print("SCENARIOS:")

            scenario_results = print_scenario_results(route)

            update_session_stats(route)
            print_session_stats()
            print_storage_status()
            maybe_persist(now, snapshot, route)

            best_scenario = max(
                route["scenarios"],
                key=lambda item: item["net_spread_percent"],
            )

            if best_scenario["net_spread_percent"] > 0:
                print(
                    "*** PROFITABLE SCENARIO FOUND: "
                    f"{best_scenario['scenario_name']} ***"
                )
            else:
                print("STATUS: NO PROFIT AFTER FEES")

            log_opportunity(
                now,
                route,
                scenario_results,
            )

            time.sleep(SCAN_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        print()
        print("Arbitrage monitor stopped.")


if __name__ == "__main__":
    main()

from datetime import datetime
import json
import os
import csv
import threading
import time
import websocket

VERSION = "0.1.8"

COINBASE_URL = "wss://advanced-trade-ws.coinbase.com"
KRAKEN_URL = "wss://ws.kraken.com/v2"

MAX_PRICE_AGE_SECONDS = 5
RECONNECT_DELAY_SECONDS = 3
MAX_RECONNECT_DELAY_SECONDS = 30
SOCKET_RECV_TIMEOUT_SECONDS = 15
SCAN_INTERVAL_SECONDS = 1

# Fee profiles. No API keys are required: ARIS uses the fee tier/rates you set.
# Defaults are conservative public rates; account-specific rates can be supplied
# via environment variables without storing secrets in this source file.
FEE_PROFILES = {
    "Coinbase": {
        "default": {
            "maker": 0.0040,  # 0.40%
            "taker": 0.0060,  # 0.60%
        },
    },
    "Kraken": {
        "tier_1": {
            "maker": 0.0040,  # 0.40%
            "taker": 0.0080,  # 0.80%
        },
    },
}

ACTIVE_FEE_PROFILE = {
    "Coinbase": os.environ.get("ARIS_COINBASE_FEE_PROFILE", "default"),
    "Kraken": os.environ.get("ARIS_KRAKEN_FEE_PROFILE", "tier_1"),
}


def env_rate(name, fallback):
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return fallback
    try:
        value = float(raw)
    except ValueError:
        print(f"[fees] invalid {name}={raw!r}; using default")
        return fallback
    if value < 0 or value > 0.05:
        print(f"[fees] out-of-range {name}={value}; using default")
        return fallback
    return value


def resolve_fee_profile(exchange):
    requested = ACTIVE_FEE_PROFILE[exchange]
    profiles = FEE_PROFILES[exchange]
    if requested not in profiles:
        fallback = next(iter(profiles))
        print(
            f"[fees] unknown {exchange} profile {requested!r}; "
            f"using {fallback!r}"
        )
        requested = fallback
    rates = profiles[requested].copy()

    prefix = exchange.upper()
    rates["maker"] = env_rate(
        f"ARIS_{prefix}_MAKER_FEE",
        rates["maker"],
    )
    rates["taker"] = env_rate(
        f"ARIS_{prefix}_TAKER_FEE",
        rates["taker"],
    )
    return requested, rates


COINBASE_FEE_PROFILE, COINBASE_FEES = resolve_fee_profile("Coinbase")
KRAKEN_FEE_PROFILE, KRAKEN_FEES = resolve_fee_profile("Kraken")

FEES = {
    "Coinbase": COINBASE_FEES,
    "Kraken": KRAKEN_FEES,
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
SESSION_HISTORY_CSV = os.path.join(LOG_DIR, "session_history.csv")
SESSION_STATS_JSON = os.path.join(LOG_DIR, "session_stats.json")

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

    if s["gross_spread_avg"] is not None:
        print(
            f"  Gross spread avg/min/max: "
            f"{s['gross_spread_avg']:+.4f}% / "
            f"{s['gross_spread_min']:+.4f}% / "
            f"{s['gross_spread_max']:+.4f}%"
        )

    if s["best_taker_taker_spread"] is not None:
        print(
            f"  Best TAKER->TAKER: "
            f"{s['best_taker_taker_spread']:+.4f}% | "
            f"Gross {s['best_gross_spread']:+.4f}% | "
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
            print(f"[Coinbase] error: {error}")
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
            print(f"[Kraken] error: {error}")
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


def calculate_base_route(
    buy_exchange,
    sell_exchange,
    buy_price,
    sell_price,
):
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
    buy_exchange = route["buy_exchange"]
    sell_exchange = route["sell_exchange"]

    buy_fee_rate = FEES[buy_exchange][scenario["buy_fee_type"]]
    sell_fee_rate = FEES[sell_exchange][scenario["sell_fee_type"]]

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


def append_history(timestamp, route):
    global last_history_save

    now_ts = time.time()
    if now_ts - last_history_save < HISTORY_SAVE_INTERVAL_SECONDS:
        return

    s = get_session_stats()
    taker_taker = route["scenarios"][0]

    file_exists = os.path.exists(SESSION_HISTORY_CSV)

    with open(
        SESSION_HISTORY_CSV,
        "a",
        newline="",
        encoding="utf-8",
    ) as handle:
        writer = csv.writer(handle)

        if not file_exists:
            writer.writerow([
                "timestamp",
                "buy_exchange",
                "sell_exchange",
                "buy_price",
                "sell_price",
                "gross_spread_percent",
                "taker_taker_net_spread_percent",
                "cycles",
                "coinbase_reconnects",
                "kraken_reconnects",
            ])

        writer.writerow([
            timestamp,
            route["buy_exchange"],
            route["sell_exchange"],
            f"{route['buy_price']:.8f}",
            f"{route['sell_price']:.8f}",
            f"{route['gross_spread_percent']:.8f}",
            f"{taker_taker['net_spread_percent']:.8f}",
            s["cycles"],
            s["coinbase_reconnects"],
            s["kraken_reconnects"],
        ])

    last_history_save = now_ts


def save_stats_json():
    global last_stats_save

    now_ts = time.time()
    if now_ts - last_stats_save < STATS_SAVE_INTERVAL_SECONDS:
        return

    s = get_session_stats()

    payload = {
        "version": VERSION,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "fee_profiles": {
            "Coinbase": COINBASE_FEE_PROFILE,
            "Kraken": KRAKEN_FEE_PROFILE,
        },
        "fees": FEES,
        "session": s,
    }

    temp_path = SESSION_STATS_JSON + ".tmp"

    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)

    os.replace(temp_path, SESSION_STATS_JSON)
    last_stats_save = now_ts


def rotate_large_file(path):
    if not os.path.exists(path):
        return

    if os.path.getsize(path) <= MAX_JOURNAL_BYTES:
        return

    suffix = datetime.now().strftime("%Y%m%d_%H%M%S")
    rotated = f"{path}.{suffix}"
    os.replace(path, rotated)


def cleanup_old_rotated_logs():
    cutoff = time.time() - (RETENTION_DAYS * 86400)

    for name in os.listdir(LOG_DIR):
        path = os.path.join(LOG_DIR, name)

        if not os.path.isfile(path):
            continue

        if name.startswith("opportunities.log."):
            if os.path.getmtime(path) < cutoff:
                try:
                    os.remove(path)
                except OSError:
                    pass


def maintain_journal():
    rotate_large_file(OPPORTUNITIES_LOG)
    rotate_large_file(SESSION_HISTORY_CSV)
    cleanup_old_rotated_logs()


def main():
    ensure_log_directory()

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
    print("FEE PROFILES:")
    print(
        f"Coinbase {COINBASE_FEE_PROFILE}: maker "
        f"{FEES['Coinbase']['maker'] * 100:.2f}% | "
        f"taker {FEES['Coinbase']['taker'] * 100:.2f}%"
    )
    print(
        f"Kraken   {KRAKEN_FEE_PROFILE}: maker "
        f"{FEES['Kraken']['maker'] * 100:.2f}% | "
        f"taker {FEES['Kraken']['taker'] * 100:.2f}%"
    )
    print()
    print(
        "Optional account-specific overrides: "
        "ARIS_COINBASE_MAKER_FEE, ARIS_COINBASE_TAKER_FEE, "
        "ARIS_KRAKEN_MAKER_FEE, ARIS_KRAKEN_TAKER_FEE"
    )
    print()
    print("Press CTRL+C to stop.")
    print()

    last_maintenance = 0.0

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
            update_session_stats(route)

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
                f"BEST: BUY {route['buy_exchange']} "
                f"${route['buy_price']:,.2f} -> "
                f"SELL {route['sell_exchange']} "
                f"${route['sell_price']:,.2f}"
            )
            print(
                f"GROSS PER BTC: "
                f"${route['gross_profit_per_btc']:+,.2f} "
                f"({route['gross_spread_percent']:+.4f}%)"
            )

            scenario_results = print_scenario_results(route)
            print_session_stats()

            log_opportunity(now, route, scenario_results)
            append_history(now, route)
            save_stats_json()

            current = time.time()
            if current - last_maintenance >= 60:
                maintain_journal()
                last_maintenance = current

            time.sleep(SCAN_INTERVAL_SECONDS)

    except KeyboardInterrupt:
        save_stats_json()
        print()
        print("Arbitrage monitor stopped.")


if __name__ == "__main__":
    main()

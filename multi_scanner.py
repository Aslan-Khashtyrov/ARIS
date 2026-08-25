import csv
import json
import os
import threading
import time
from datetime import datetime

import websocket

COINBASE_URL = "wss://advanced-trade-ws.coinbase.com"
KRAKEN_URL = "wss://ws.kraken.com/v2"

ASSETS = ["BTC", "ETH", "SOL", "XRP"]

COINBASE_PRODUCTS = [f"{x}-USD" for x in ASSETS]
KRAKEN_SYMBOLS = [f"{x}/USD" for x in ASSETS]

# Пока используем те же консервативные комиссии, что и основной Арбитражник.
TAKER_FEE = {
    "coinbase": 0.006,
    "kraken": 0.008,
}

CHECK_EVERY = 1
FRESH_AFTER = 20
SAVE_EVERY = 60

LOG_DIR = "journal"
HISTORY = os.path.join(LOG_DIR, "multi_history.csv")

lock = threading.Lock()

market = {
    asset: {
        "coinbase": {"bid": None, "ask": None, "updated": 0.0},
        "kraken": {"bid": None, "ask": None, "updated": 0.0},
    }
    for asset in ASSETS
}

def safe_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None

def update_market(asset, exchange, bid, ask):
    bid = safe_float(bid)
    ask = safe_float(ask)

    if bid is None or ask is None:
        return
    if bid <= 0 or ask <= 0 or bid > ask:
        return

    with lock:
        market[asset][exchange]["bid"] = bid
        market[asset][exchange]["ask"] = ask
        market[asset][exchange]["updated"] = time.time()

def coinbase_monitor():
    while True:
        ws = None
        try:
            ws = websocket.create_connection(
                COINBASE_URL,
                timeout=20,
                enable_multithread=True,
            )
            ws.settimeout(15)

            ws.send(json.dumps({
                "type": "subscribe",
                "product_ids": COINBASE_PRODUCTS,
                "channel": "ticker",
            }))

            ws.send(json.dumps({
                "type": "subscribe",
                "channel": "heartbeats",
            }))

            print("[Coinbase] connected")

            while True:
                try:
                    raw = ws.recv()
                except websocket.WebSocketTimeoutException:
                    ws.ping("keepalive")
                    continue

                if not raw:
                    raise ConnectionError("Coinbase connection closed")

                msg = json.loads(raw)

                if msg.get("channel") != "ticker":
                    continue

                for event in msg.get("events", []):
                    for ticker in event.get("tickers", []):
                        product = ticker.get("product_id")
                        if not product or not product.endswith("-USD"):
                            continue

                        asset = product.split("-")[0]
                        if asset not in market:
                            continue

                        update_market(
                            asset,
                            "coinbase",
                            ticker.get("best_bid"),
                            ticker.get("best_ask"),
                        )

        except Exception as e:
            print(f"[Coinbase] reconnect: {type(e).__name__}")
            time.sleep(3)

        finally:
            if ws is not None:
                try:
                    ws.close()
                except Exception:
                    pass

def kraken_monitor():
    while True:
        ws = None
        try:
            ws = websocket.create_connection(
                KRAKEN_URL,
                timeout=20,
                enable_multithread=True,
            )
            ws.settimeout(15)

            ws.send(json.dumps({
                "method": "subscribe",
                "params": {
                    "channel": "ticker",
                    "symbol": KRAKEN_SYMBOLS,
                    "event_trigger": "bbo",
                },
            }))

            print("[Kraken] connected")

            while True:
                try:
                    raw = ws.recv()
                except websocket.WebSocketTimeoutException:
                    ws.ping("keepalive")
                    continue

                if not raw:
                    raise ConnectionError("Kraken connection closed")

                msg = json.loads(raw)

                if msg.get("channel") != "ticker":
                    continue

                data = msg.get("data", [])
                for ticker in data:
                    symbol = ticker.get("symbol")
                    if not symbol or "/" not in symbol:
                        continue

                    asset = symbol.split("/")[0]
                    if asset not in market:
                        continue

                    update_market(
                        asset,
                        "kraken",
                        ticker.get("bid"),
                        ticker.get("ask"),
                    )

        except Exception as e:
            print(f"[Kraken] reconnect: {type(e).__name__}")
            time.sleep(3)

        finally:
            if ws is not None:
                try:
                    ws.close()
                except Exception:
                    pass

def route_result(asset, buy_exchange, sell_exchange):
    with lock:
        buy = market[asset][buy_exchange].copy()
        sell = market[asset][sell_exchange].copy()

    now = time.time()

    if (
        buy["ask"] is None
        or sell["bid"] is None
        or now - buy["updated"] > FRESH_AFTER
        or now - sell["updated"] > FRESH_AFTER
    ):
        return None

    buy_price = buy["ask"]
    sell_price = sell["bid"]

    gross = (sell_price / buy_price - 1.0) * 100

    # Точный расчёт для виртуального капитала $1:
    # покупка с taker fee -> продажа с taker fee.
    buy_fee = TAKER_FEE[buy_exchange]
    sell_fee = TAKER_FEE[sell_exchange]

    quantity = 1.0 / (buy_price * (1.0 + buy_fee))
    final_usd = quantity * sell_price * (1.0 - sell_fee)
    net = (final_usd - 1.0) * 100

    return {
        "asset": asset,
        "buy": buy_exchange,
        "sell": sell_exchange,
        "buy_price": buy_price,
        "sell_price": sell_price,
        "gross": gross,
        "net": net,
    }

def all_results():
    results = []

    for asset in ASSETS:
        a = route_result(asset, "coinbase", "kraken")
        b = route_result(asset, "kraken", "coinbase")

        if a:
            results.append(a)
        if b:
            results.append(b)

    return sorted(results, key=lambda x: x["net"], reverse=True)

def save_history(results):
    os.makedirs(LOG_DIR, exist_ok=True)

    exists = os.path.exists(HISTORY)

    with open(HISTORY, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        if not exists:
            writer.writerow([
                "timestamp",
                "asset",
                "buy_exchange",
                "sell_exchange",
                "buy_price",
                "sell_price",
                "gross_percent",
                "net_taker_taker_percent",
            ])

        now = datetime.now().isoformat(timespec="seconds")

        for r in results:
            writer.writerow([
                now,
                r["asset"],
                r["buy"],
                r["sell"],
                r["buy_price"],
                r["sell_price"],
                r["gross"],
                r["net"],
            ])

print("=" * 72)
print("ARBITRAGE MULTI SCANNER v0.1")
print("BTC / ETH / SOL / XRP")
print("COINBASE <-> KRAKEN")
print("MODE: MONITORING ONLY")
print("REAL TRADING: DISABLED")
print("=" * 72)

threading.Thread(target=coinbase_monitor, daemon=True).start()
threading.Thread(target=kraken_monitor, daemon=True).start()

last_save = 0.0

try:
    while True:
        results = all_results()

        print()
        print(datetime.now().strftime("[%Y-%m-%d %H:%M:%S]"))

        if not results:
            print("Waiting for fresh prices...")
        else:
            best_by_asset = {}

            for r in results:
                if r["asset"] not in best_by_asset:
                    best_by_asset[r["asset"]] = r

            for asset in ASSETS:
                r = best_by_asset.get(asset)

                if not r:
                    print(f"{asset:4} | waiting...")
                    continue

                print(
                    f"{asset:4} | "
                    f"{r['buy']:8} -> {r['sell']:8} | "
                    f"gross {r['gross']:+.4f}% | "
                    f"net {r['net']:+.4f}%"
                )

            best = results[0]

            print("-" * 72)
            print(
                f"BEST: {best['asset']} | "
                f"{best['buy']} -> {best['sell']} | "
                f"NET {best['net']:+.4f}%"
            )

            if best["net"] > 0:
                print("*** PAPER OPPORTUNITY AFTER TAKER FEES ***")
            else:
                print("NO PROFIT AFTER TAKER FEES")

            if time.time() - last_save >= SAVE_EVERY:
                save_history(results)
                last_save = time.time()

        time.sleep(CHECK_EVERY)

except KeyboardInterrupt:
    print("\nMulti Scanner stopped.")

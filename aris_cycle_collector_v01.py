from pathlib import Path
from datetime import datetime
import json
import threading
import time
import urllib.request
import websocket

ROOT = Path.home() / "Arbitrage"
JOURNAL = ROOT / "journal"
SNAPSHOT = JOURNAL / "cycle_quotes_v01.json"
STATUS = JOURNAL / "cycle_collector_status_v01.json"
CB_PRODUCTS_URL = "https://api.exchange.coinbase.com/products"
KRAKEN_PAIRS_URL = "https://api.kraken.com/0/public/AssetPairs"
CB_WS = "wss://advanced-trade-ws.coinbase.com"
KRAKEN_WS = "wss://ws.kraken.com/v2"
UNIVERSE = {"USD", "USDT", "USDC", "EUR", "BTC", "ETH", "SOL", "XRP"}
FEES = {"coinbase": 0.006, "kraken": 0.008}
FRESH_SECONDS = 15
SAVE_SECONDS = 5

lock = threading.Lock()
quotes = {}
health = {
    "coinbase": {"connected": False, "pairs": 0, "updates": 0, "error": None},
    "kraken": {"connected": False, "pairs": 0, "updates": 0, "error": None},
}

def request_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "ARIS-monitor/0.1"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))

def norm_asset(value):
    value = str(value).upper()
    return {"XBT": "BTC", "XDG": "DOGE"}.get(value, value)

def discover_coinbase():
    products = request_json(CB_PRODUCTS_URL)
    result = []
    for item in products:
        base = norm_asset(item.get("base_currency"))
        quote = norm_asset(item.get("quote_currency"))
        if base in UNIVERSE and quote in UNIVERSE and item.get("status") == "online" and not item.get("trading_disabled", False):
            result.append((item["id"], base, quote))
    return result

def discover_kraken():
    payload = request_json(KRAKEN_PAIRS_URL)
    result = []
    for item in payload.get("result", {}).values():
        wsname = item.get("wsname")
        if not wsname or "/" not in wsname:
            continue
        raw_base, raw_quote = wsname.split("/", 1)
        base, quote = norm_asset(raw_base), norm_asset(raw_quote)
        if base in UNIVERSE and quote in UNIVERSE:
            result.append((f"{base}/{quote}", base, quote))
    return sorted(set(result))

def update(exchange, symbol, base, quote, bid, ask, bid_size=0, ask_size=0):
    try:
        bid, ask = float(bid), float(ask)
        bid_size = float(bid_size or 0)
        ask_size = float(ask_size or 0)
    except (TypeError, ValueError):
        return
    if bid <= 0 or ask <= 0 or bid > ask:
        return
    with lock:
        quotes[(exchange, symbol)] = {
            "exchange": exchange,
            "symbol": symbol,
            "base": base,
            "quote": quote,
            "bid": bid,
            "ask": ask,
            "bid_size": max(0, bid_size),
            "ask_size": max(0, ask_size),
            "taker_fee": FEES[exchange],
            "updated_at": time.time(),
            "source": "LIVE_PUBLIC_MARKET_DATA",
        }
        health[exchange]["updates"] += 1

def coinbase_loop():
    while True:
        ws = None
        try:
            products = discover_coinbase()
            mapping = {symbol: (base, quote) for symbol, base, quote in products}
            with lock:
                health["coinbase"].update({"pairs": len(products), "error": None})
            if not products:
                raise RuntimeError("no supported Coinbase products")
            ws = websocket.create_connection(CB_WS, timeout=25, enable_multithread=True)
            ws.settimeout(20)
            ws.send(json.dumps({"type": "subscribe", "product_ids": list(mapping), "channel": "ticker"}))
            ws.send(json.dumps({"type": "subscribe", "channel": "heartbeats"}))
            with lock:
                health["coinbase"]["connected"] = True
            while True:
                try:
                    raw = ws.recv()
                except websocket.WebSocketTimeoutException:
                    ws.ping("keepalive")
                    continue
                message = json.loads(raw)
                if message.get("channel") != "ticker":
                    continue
                for event in message.get("events", []):
                    for ticker in event.get("tickers", []):
                        symbol = ticker.get("product_id")
                        if symbol not in mapping:
                            continue
                        base, quote = mapping[symbol]
                        update(
                            "coinbase", symbol, base, quote,
                            ticker.get("best_bid"), ticker.get("best_ask"),
                            ticker.get("best_bid_quantity") or ticker.get("best_bid_size"),
                            ticker.get("best_ask_quantity") or ticker.get("best_ask_size"),
                        )
        except Exception as exc:
            with lock:
                health["coinbase"].update({"connected": False, "error": f"{type(exc).__name__}: {exc}"})
            time.sleep(5)
        finally:
            if ws:
                try:
                    ws.close()
                except Exception:
                    pass

def kraken_loop():
    while True:
        ws = None
        try:
            products = discover_kraken()
            mapping = {symbol: (base, quote) for symbol, base, quote in products}
            with lock:
                health["kraken"].update({"pairs": len(products), "error": None})
            if not products:
                raise RuntimeError("no supported Kraken products")
            ws = websocket.create_connection(KRAKEN_WS, timeout=25, enable_multithread=True)
            ws.settimeout(20)
            ws.send(json.dumps({
                "method": "subscribe",
                "params": {"channel": "ticker", "symbol": list(mapping), "event_trigger": "bbo", "snapshot": True},
            }))
            with lock:
                health["kraken"]["connected"] = True
            while True:
                try:
                    raw = ws.recv()
                except websocket.WebSocketTimeoutException:
                    ws.ping("keepalive")
                    continue
                message = json.loads(raw)
                if message.get("channel") != "ticker":
                    continue
                for ticker in message.get("data", []):
                    symbol = ticker.get("symbol")
                    if symbol not in mapping:
                        continue
                    base, quote = mapping[symbol]
                    update(
                        "kraken", symbol, base, quote,
                        ticker.get("bid"), ticker.get("ask"),
                        ticker.get("bid_qty"), ticker.get("ask_qty"),
                    )
        except Exception as exc:
            with lock:
                health["kraken"].update({"connected": False, "error": f"{type(exc).__name__}: {exc}"})
            time.sleep(5)
        finally:
            if ws:
                try:
                    ws.close()
                except Exception:
                    pass

def write_atomic(path, payload):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)

def snapshot_loop():
    JOURNAL.mkdir(parents=True, exist_ok=True)
    while True:
        now = time.time()
        with lock:
            live = [dict(item) for item in quotes.values() if now - item["updated_at"] <= FRESH_SECONDS]
            state = json.loads(json.dumps(health))
        payload = {
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "mode": "LIVE_PUBLIC_MONITORING",
            "real_trading": False,
            "quotes": live,
            "transfers": [],
        }
        write_atomic(SNAPSHOT, payload)
        write_atomic(STATUS, {
            "ok": True,
            "generated_at": payload["generated_at"],
            "live_quotes": len(live),
            "exchanges": state,
            "real_trading": False,
        })
        time.sleep(SAVE_SECONDS)

def run_forever():
    threads = [
        threading.Thread(target=coinbase_loop, daemon=True, name="cycle-coinbase"),
        threading.Thread(target=kraken_loop, daemon=True, name="cycle-kraken"),
        threading.Thread(target=snapshot_loop, daemon=True, name="cycle-snapshot"),
    ]
    for thread in threads:
        thread.start()
    while True:
        time.sleep(60)

if __name__ == "__main__":
    run_forever()

from pathlib import Path
from datetime import datetime
import json
import threading
import time
import urllib.request
import websocket

from aris_cycle_engine_v01 import analyze as analyze_cycles

ROOT = Path.home() / "Arbitrage"
JOURNAL = ROOT / "journal"
SNAPSHOT = JOURNAL / "cycle_quotes_v01.json"
STATUS = JOURNAL / "cycle_collector_status_v01.json"
CYCLE_REPORT = JOURNAL / "cycle_report_v01.json"
SIGNALS = JOURNAL / "cycle_opportunities_v01.jsonl"
CB_PRODUCTS_URL = "https://api.exchange.coinbase.com/products"
KRAKEN_PAIRS_URL = "https://api.kraken.com/0/public/AssetPairs"
BINANCE_INFO_URL = "https://data-api.binance.vision/api/v3/exchangeInfo"
BINANCE_TICKERS_URL = "https://data-api.binance.vision/api/v3/ticker/bookTicker"
BYBIT_INFO_URL = "https://api.bybit.com/v5/market/instruments-info?category=spot"
BYBIT_TICKERS_URL = "https://api.bybit.com/v5/market/tickers?category=spot"
OKX_INFO_URL = "https://www.okx.com/api/v5/public/instruments?instType=SPOT"
OKX_TICKERS_URL = "https://www.okx.com/api/v5/market/tickers?instType=SPOT"
CB_WS = "wss://advanced-trade-ws.coinbase.com"
KRAKEN_WS = "wss://ws.kraken.com/v2"
UNIVERSE = {"USD", "USDT", "USDC", "EUR", "BTC", "ETH", "SOL", "XRP"}
FEES = {"coinbase": 0.006, "kraken": 0.008, "binance": 0.001, "bybit": 0.001, "okx": 0.001}
FRESH_SECONDS = 15
SAVE_SECONDS = 5
SIGNAL_PROFIT_PERCENT = 0.30
SIGNAL_CONFIRMATIONS = 3

lock = threading.Lock()
quotes = {}
health = {
    "coinbase": {"connected": False, "pairs": 0, "updates": 0, "error": None},
    "kraken": {"connected": False, "pairs": 0, "updates": 0, "error": None},
    "binance": {"connected": False, "pairs": 0, "updates": 0, "error": None},
    "bybit": {"connected": False, "pairs": 0, "updates": 0, "error": None},
    "okx": {"connected": False, "pairs": 0, "updates": 0, "error": None},
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

def rest_market_loop(exchange, discover, fetch_tickers, poll_seconds=2):
    while True:
        try:
            mapping = discover()
            with lock:
                health[exchange].update({"connected": True, "pairs": len(mapping), "error": None})
            if not mapping:
                raise RuntimeError(f"no supported {exchange} products")
            while True:
                for item in fetch_tickers():
                    symbol = item.get("symbol")
                    if symbol not in mapping:
                        continue
                    base, quote = mapping[symbol]
                    update(exchange, symbol, base, quote, item.get("bid"), item.get("ask"), item.get("bid_size"), item.get("ask_size"))
                time.sleep(poll_seconds)
        except Exception as exc:
            with lock:
                health[exchange].update({"connected": False, "error": f"{type(exc).__name__}: {exc}"})
            time.sleep(5)


def discover_binance():
    payload = request_json(BINANCE_INFO_URL)
    result = {}
    for item in payload.get("symbols", []):
        base, quote = norm_asset(item.get("baseAsset")), norm_asset(item.get("quoteAsset"))
        if base in UNIVERSE and quote in UNIVERSE and item.get("status") == "TRADING" and item.get("isSpotTradingAllowed", True):
            result[item["symbol"]] = (base, quote)
    return result


def fetch_binance_tickers():
    payload = request_json(BINANCE_TICKERS_URL)
    return [{"symbol": item.get("symbol"), "bid": item.get("bidPrice"), "ask": item.get("askPrice"), "bid_size": item.get("bidQty"), "ask_size": item.get("askQty")} for item in payload]


def discover_bybit():
    payload = request_json(BYBIT_INFO_URL)
    result = {}
    for item in payload.get("result", {}).get("list", []):
        base, quote = norm_asset(item.get("baseCoin")), norm_asset(item.get("quoteCoin"))
        if base in UNIVERSE and quote in UNIVERSE and item.get("status") == "Trading":
            result[item["symbol"]] = (base, quote)
    return result


def fetch_bybit_tickers():
    payload = request_json(BYBIT_TICKERS_URL)
    return [{"symbol": item.get("symbol"), "bid": item.get("bid1Price"), "ask": item.get("ask1Price"), "bid_size": item.get("bid1Size"), "ask_size": item.get("ask1Size")} for item in payload.get("result", {}).get("list", [])]


def discover_okx():
    payload = request_json(OKX_INFO_URL)
    result = {}
    for item in payload.get("data", []):
        base, quote = norm_asset(item.get("baseCcy")), norm_asset(item.get("quoteCcy"))
        if base in UNIVERSE and quote in UNIVERSE and item.get("state") == "live":
            result[item["instId"]] = (base, quote)
    return result


def fetch_okx_tickers():
    payload = request_json(OKX_TICKERS_URL)
    return [{"symbol": item.get("instId"), "bid": item.get("bidPx"), "ask": item.get("askPx"), "bid_size": item.get("bidSz"), "ask_size": item.get("askSz")} for item in payload.get("data", [])]


def write_atomic(path, payload):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)

def snapshot_loop():
    JOURNAL.mkdir(parents=True, exist_ok=True)
    last_signal_signature = None
    last_signal_time = 0.0
    candidate_signature = None
    candidate_streak = 0
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
        cycle_report = analyze_cycles(payload)
        write_atomic(CYCLE_REPORT, cycle_report)
        opportunities = cycle_report.get("opportunities", [])
        actionable = [item for item in opportunities if item.get("profit_percent", -999) >= SIGNAL_PROFIT_PERCENT]
        confirmed_signal_ready = False
        if actionable:
            best = actionable[0]
            signature = tuple((edge["src"], edge["dst"], edge["kind"]) for edge in best["route"])
            if signature == candidate_signature:
                candidate_streak += 1
            else:
                candidate_signature = signature
                candidate_streak = 1
            confirmed_signal_ready = candidate_streak >= SIGNAL_CONFIRMATIONS
            if confirmed_signal_ready and (signature != last_signal_signature or now - last_signal_time >= 60):
                record = {
                    "detected_at": payload["generated_at"],
                    "source": "LIVE_PUBLIC_MARKET_DATA",
                    "real_trading": False,
                    "confirmation_snapshots": candidate_streak,
                    "minimum_profit_percent": SIGNAL_PROFIT_PERCENT,
                    "cycle": best,
                }
                with SIGNALS.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                last_signal_signature = signature
                last_signal_time = now
        else:
            candidate_signature = None
            candidate_streak = 0
        write_atomic(STATUS, {
            "ok": True,
            "generated_at": payload["generated_at"],
            "live_quotes": len(live),
            "cycles_checked": cycle_report.get("cycles_checked", 0),
            "raw_opportunities": len(opportunities),
            "actionable_candidates": len(actionable),
            "candidate_streak": candidate_streak,
            "required_confirmations": SIGNAL_CONFIRMATIONS,
            "signal_profit_percent": SIGNAL_PROFIT_PERCENT,
            "confirmed_signal_ready": confirmed_signal_ready,
            "signals": 1 if confirmed_signal_ready else 0,
            "best_profit_percent": cycle_report.get("best_cycle", {}).get("profit_percent") if cycle_report.get("best_cycle") else None,
            "exchanges": state,
            "real_trading": False,
        })
        time.sleep(SAVE_SECONDS)

def run_forever():
    threads = [
        threading.Thread(target=coinbase_loop, daemon=True, name="cycle-coinbase"),
        threading.Thread(target=kraken_loop, daemon=True, name="cycle-kraken"),
        threading.Thread(target=rest_market_loop, args=("binance", discover_binance, fetch_binance_tickers), daemon=True, name="cycle-binance"),
        threading.Thread(target=rest_market_loop, args=("bybit", discover_bybit, fetch_bybit_tickers), daemon=True, name="cycle-bybit"),
        threading.Thread(target=rest_market_loop, args=("okx", discover_okx, fetch_okx_tickers), daemon=True, name="cycle-okx"),
        threading.Thread(target=snapshot_loop, daemon=True, name="cycle-snapshot"),
    ]
    for thread in threads:
        thread.start()
    while True:
        time.sleep(60)

if __name__ == "__main__":
    run_forever()

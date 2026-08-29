from pathlib import Path
from datetime import datetime
import json
import threading
import time
import urllib.parse
import urllib.request
import websocket

from aris_cycle_engine_v01 import analyze as analyze_cycles

ROOT = Path.home() / "Arbitrage"
JOURNAL = ROOT / "journal"
SNAPSHOT = JOURNAL / "cycle_quotes_v01.json"
STATUS = JOURNAL / "cycle_collector_status_v01.json"
CYCLE_REPORT = JOURNAL / "cycle_report_v01.json"
SIGNALS = JOURNAL / "cycle_opportunities_v01.jsonl"
PROFIT_AUDIT = JOURNAL / "cycle_profit_audit_v01.jsonl"
BINANCE_PRODUCTS_CACHE = JOURNAL / "binance_products_cache_v01.json"
BYBIT_PRODUCTS_CACHE = JOURNAL / "bybit_products_cache_v01.json"
OKX_PRODUCTS_CACHE = JOURNAL / "okx_products_cache_v01.json"
CB_PRODUCTS_URL = "https://api.exchange.coinbase.com/products"
KRAKEN_PAIRS_URL = "https://api.kraken.com/0/public/AssetPairs"
BINANCE_INFO_URL = "https://data-api.binance.vision/api/v3/exchangeInfo"
BINANCE_TICKERS_URL = "https://data-api.binance.vision/api/v3/ticker/bookTicker"
BINANCE_WS = "wss://data-stream.binance.vision:443/stream?streams="
BYBIT_INFO_URL = "https://api.bybit.com/v5/market/instruments-info?category=spot"
BYBIT_TICKERS_URL = "https://api.bybit.com/v5/market/tickers?category=spot"
BYBIT_WS = "wss://stream.bybit.com/v5/public/spot"
OKX_INFO_URL = "https://www.okx.com/api/v5/public/instruments?instType=SPOT"
OKX_TICKERS_URL = "https://www.okx.com/api/v5/market/tickers?instType=SPOT"
OKX_WS = "wss://ws.okx.com:8443/ws/v5/public"
CB_WS = "wss://advanced-trade-ws.coinbase.com"
KRAKEN_WS = "wss://ws.kraken.com/v2"
UNIVERSE = {"USD", "USDT", "USDC", "EUR", "GBP", "DAI", "FDUSD", "BTC", "ETH", "SOL", "XRP", "DOGE", "ADA", "AVAX", "DOT", "LINK", "LTC", "BCH", "TRX"}
FEE_SCHEDULE = ROOT / "aris_fee_schedule_v01.json"
CONFIG = ROOT / "aris_config_v01.json"
FRESH_SECONDS = 15
SAVE_SECONDS = 5
SIGNAL_PROFIT_PERCENT = 0.30
SIGNAL_CONFIRMATIONS = 3
DISCOVERY_REFRESH_SECONDS = 6 * 60 * 60
BINANCE_STALE_SECONDS = 30

lock = threading.Lock()
quotes = {}
health = {
    "coinbase": {"connected": False, "pairs": 0, "updates": 0, "error": None, "transport": "websocket"},
    "kraken": {"connected": False, "pairs": 0, "updates": 0, "error": None, "transport": "websocket"},
    "binance": {"connected": False, "pairs": 0, "updates": 0, "error": None, "transport": "websocket"},
    "bybit": {"connected": False, "pairs": 0, "updates": 0, "error": None, "transport": "websocket"},
    "okx": {"connected": False, "pairs": 0, "updates": 0, "error": None, "transport": "websocket"},
}

def load_fee_schedule():
    payload = json.loads(FEE_SCHEDULE.read_text(encoding="utf-8"))
    exchanges = payload.get("exchanges", {})
    required = {"coinbase", "kraken", "binance", "bybit", "okx"}
    if not required.issubset(exchanges):
        raise RuntimeError("fee schedule is incomplete")
    fees = {}
    for exchange in required:
        rate = float(exchanges[exchange]["taker"])
        if not 0 < rate < 0.05:
            raise RuntimeError(f"invalid taker fee for {exchange}")
        fees[exchange] = rate
    return payload, fees


FEE_INFO, FEES = load_fee_schedule()

def load_funded_paper_wallets():
    payload = json.loads(CONFIG.read_text(encoding="utf-8"))
    wallet = payload.get("paper_wallet", {})
    if wallet.get("enabled") is not True or wallet.get("real_money") is not False:
        return set()
    return {
        str(name)
        for name, amount in wallet.get("initial_balances", {}).items()
        if float(amount or 0) > 0
    }


def cycle_wallet(cycle):
    return str(cycle.get("start") or (cycle.get("route") or [{}])[0].get("src") or "")


def is_paper_funded(cycle, funded_wallets):
    return cycle_wallet(cycle) in funded_wallets


FUNDED_PAPER_WALLETS = load_funded_paper_wallets()

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

def product_details(mapping, symbol):
    item = mapping[symbol]
    if isinstance(item, dict):
        return item["base"], item["quote"], item
    base, quote = item
    return base, quote, {}


def update(exchange, symbol, base, quote, bid, ask, bid_size=0, ask_size=0, constraints=None):
    constraints = constraints or {}
    try:
        bid, ask = float(bid), float(ask)
        bid_size = float(bid_size or 0)
        ask_size = float(ask_size or 0)
        min_base = float(constraints.get("min_base", 0) or 0)
        min_quote = float(constraints.get("min_quote", 0) or 0)
        qty_step = float(constraints.get("qty_step", 0) or 0)
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
            "min_base": max(0, min_base),
            "min_quote": max(0, min_quote),
            "qty_step": max(0, qty_step),
            "order_filter_source": constraints.get("filter_source"),
            "taker_fee": FEES[exchange],
            "fee_status": FEE_INFO["exchanges"][exchange]["status"],
            "fee_verified_at": FEE_INFO["verified_at"],
            "fee_model": FEE_INFO["mode"],
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
    mapping = {}
    next_discovery = 0.0
    while True:
        try:
            current_time = time.time()
            if not mapping or current_time >= next_discovery:
                try:
                    discovered = discover()
                    if not discovered:
                        raise RuntimeError(f"no supported {exchange} products")
                    mapping = discovered
                    next_discovery = current_time + DISCOVERY_REFRESH_SECONDS
                except Exception:
                    if not mapping:
                        raise
                    next_discovery = current_time + 60
            updates = 0
            for item in fetch_tickers(mapping):
                symbol = item.get("symbol")
                if symbol not in mapping:
                    continue
                base, quote, constraints = product_details(mapping, symbol)
                update(exchange, symbol, base, quote, item.get("bid"), item.get("ask"), item.get("bid_size"), item.get("ask_size"), constraints)
                updates += 1
            if not updates:
                raise RuntimeError(f"no usable {exchange} tickers")
            with lock:
                health[exchange].update({"connected": True, "pairs": len(mapping), "error": None})
            time.sleep(poll_seconds)
        except Exception as exc:
            with lock:
                health[exchange].update({"connected": False, "error": f"{type(exc).__name__}: {exc}"})
            time.sleep(5)


def discover_binance():
    try:
        payload = request_json(BINANCE_INFO_URL)
        result = {}
        for item in payload.get("symbols", []):
            base, quote = norm_asset(item.get("baseAsset")), norm_asset(item.get("quoteAsset"))
            if base in UNIVERSE and quote in UNIVERSE and item.get("status") == "TRADING" and item.get("isSpotTradingAllowed", True):
                filters = {entry.get("filterType"): entry for entry in item.get("filters", [])}
                lot = filters.get("LOT_SIZE", {})
                notional = filters.get("NOTIONAL") or filters.get("MIN_NOTIONAL") or {}
                result[item["symbol"]] = {
                    "base": base,
                    "quote": quote,
                    "min_base": lot.get("minQty", 0),
                    "min_quote": notional.get("minNotional", 0),
                    "qty_step": lot.get("stepSize", 0),
                    "filter_source": "BINANCE_PUBLIC_EXCHANGE_INFO",
                }
        if result:
            write_atomic(BINANCE_PRODUCTS_CACHE, result)
            return result
        raise RuntimeError("empty Binance exchange info")
    except Exception:
        try:
            cached = json.loads(BINANCE_PRODUCTS_CACHE.read_text(encoding="utf-8"))
            if cached:
                return cached
        except Exception:
            pass
        snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        recovered = {}
        for quote in snapshot.get("quotes", []):
            if str(quote.get("exchange", "")).lower() != "binance":
                continue
            symbol = quote.get("symbol")
            if not symbol:
                continue
            recovered[symbol] = {
                "base": quote.get("base"),
                "quote": quote.get("quote"),
                "min_base": quote.get("min_base", 0),
                "min_quote": quote.get("min_quote", 0),
                "qty_step": quote.get("qty_step", 0),
                "filter_source": "BINANCE_LAST_PUBLIC_SNAPSHOT",
            }
        if recovered:
            write_atomic(BINANCE_PRODUCTS_CACHE, recovered)
            return recovered
        raise



def fetch_binance_tickers(mapping):
    query = urllib.parse.urlencode({"symbols": json.dumps(sorted(mapping), separators=(",", ":"))})
    payload = request_json(f"{BINANCE_TICKERS_URL}?{query}")
    return [{"symbol": item.get("symbol"), "bid": item.get("bidPrice"), "ask": item.get("askPrice"), "bid_size": item.get("bidQty"), "ask_size": item.get("askQty")} for item in payload]


def binance_loop():
    while True:
        ws = None
        active = set()
        candidates = {}
        try:
            candidates = discover_binance()
            if not candidates:
                raise RuntimeError("no supported Binance products")
            streams = "/".join(f"{symbol.lower()}@bookTicker" for symbol in sorted(candidates))
            url = BINANCE_WS + streams
            ws = websocket.create_connection(url, timeout=20, enable_multithread=True)
            last_market_update = time.monotonic()
            while True:
                try:
                    raw = ws.recv()
                except websocket.WebSocketTimeoutException:
                    if time.monotonic() - last_market_update >= BINANCE_STALE_SECONDS:
                        raise RuntimeError("Binance market data stale")
                    ws.ping("keepalive")
                    continue
                message = json.loads(raw)
                item = message.get("data", message)
                symbol = str(item.get("s", "")).upper()
                if symbol not in candidates:
                    continue
                base, quote, constraints = product_details(candidates, symbol)
                update(
                    "binance", symbol, base, quote,
                    item.get("b"), item.get("a"), item.get("B"), item.get("A"), constraints,
                )
                last_market_update = time.monotonic()
                active.add(symbol)
                with lock:
                    health["binance"].update({
                        "connected": True,
                        "pairs": len(candidates),
                        "active_pairs": len(active),
                        "error": None,
                        "transport": "websocket",
                    })
        except Exception as exc:
            fallback_updates = 0
            fallback_error = None
            if candidates:
                try:
                    for item in fetch_binance_tickers(candidates):
                        symbol = item.get("symbol")
                        if symbol not in candidates:
                            continue
                        base, quote, constraints = product_details(candidates, symbol)
                        update(
                            "binance", symbol, base, quote,
                            item.get("bid"), item.get("ask"),
                            item.get("bid_size"), item.get("ask_size"), constraints,
                        )
                        fallback_updates += 1
                except Exception as rest_exc:
                    fallback_error = f"{type(rest_exc).__name__}: {rest_exc}"
            with lock:
                if fallback_updates:
                    health["binance"].update({
                        "connected": True,
                        "pairs": len(candidates),
                        "active_pairs": fallback_updates,
                        "error": f"websocket reconnecting after {type(exc).__name__}",
                        "transport": "rest_fallback",
                    })
                else:
                    detail = f"{type(exc).__name__}: {exc}"
                    if fallback_error:
                        detail += f"; REST fallback failed: {fallback_error}"
                    health["binance"].update({
                        "connected": False,
                        "pairs": len(active),
                        "error": detail,
                    })
            time.sleep(1 if fallback_updates else 5)
        finally:
            if ws:
                try:
                    ws.close()
                except Exception:
                    pass

def discover_bybit():
    try:
        payload = request_json(BYBIT_INFO_URL)
        result = {}
        for item in payload.get("result", {}).get("list", []):
            base, quote = norm_asset(item.get("baseCoin")), norm_asset(item.get("quoteCoin"))
            if base in UNIVERSE and quote in UNIVERSE and item.get("status") == "Trading":
                lot = item.get("lotSizeFilter", {})
                result[item["symbol"]] = {
                    "base": base,
                    "quote": quote,
                    "min_base": lot.get("minOrderQty", 0),
                    "min_quote": lot.get("minOrderAmt", 0),
                    "qty_step": lot.get("qtyStep") or lot.get("basePrecision", 0),
                    "filter_source": "BYBIT_PUBLIC_INSTRUMENTS_INFO",
                }
        if result:
            write_atomic(BYBIT_PRODUCTS_CACHE, result)
            return result
        raise RuntimeError("empty Bybit instruments")
    except Exception:
        try:
            cached = json.loads(BYBIT_PRODUCTS_CACHE.read_text(encoding="utf-8"))
            if cached:
                return cached
        except Exception:
            pass
        snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        recovered = {}
        for quote in snapshot.get("quotes", []):
            if str(quote.get("exchange", "")).lower() != "bybit":
                continue
            symbol = quote.get("symbol")
            if not symbol:
                continue
            recovered[symbol] = {
                "base": quote.get("base"),
                "quote": quote.get("quote"),
                "min_base": quote.get("min_base", 0),
                "min_quote": quote.get("min_quote", 0),
                "qty_step": quote.get("qty_step", 0),
                "filter_source": "BYBIT_LAST_PUBLIC_SNAPSHOT",
            }
        if recovered:
            write_atomic(BYBIT_PRODUCTS_CACHE, recovered)
            return recovered
        raise

def fetch_bybit_tickers(mapping):
    payload = request_json(BYBIT_TICKERS_URL)
    return [{"symbol": item.get("symbol"), "bid": item.get("bid1Price"), "ask": item.get("ask1Price"), "bid_size": item.get("bid1Size"), "ask_size": item.get("ask1Size")} for item in payload.get("result", {}).get("list", [])]


def bybit_loop():
    while True:
        ws = None
        try:
            mapping = discover_bybit()
            if not mapping:
                raise RuntimeError("no supported Bybit products")
            ws = websocket.create_connection(BYBIT_WS, timeout=25, enable_multithread=True)
            ws.settimeout(20)
            topics = [f"orderbook.1.{symbol}" for symbol in sorted(mapping)]
            for batch_index in range(0, len(topics), 10):
                ws.send(json.dumps({
                    "req_id": f"arisbybit{batch_index // 10 + 1:02d}",
                    "op": "subscribe",
                    "args": topics[batch_index:batch_index + 10],
                }))
            with lock:
                health["bybit"].update({"connected": True, "pairs": len(mapping), "error": None})
            while True:
                try:
                    raw = ws.recv()
                except websocket.WebSocketTimeoutException:
                    ws.send(json.dumps({"op": "ping"}))
                    continue
                message = json.loads(raw)
                if message.get("success") is False:
                    raise RuntimeError(message.get("ret_msg") or "Bybit subscription error")
                topic = str(message.get("topic", ""))
                if not topic.startswith("orderbook.1."):
                    continue
                symbol = topic.rsplit(".", 1)[1]
                if symbol not in mapping:
                    continue
                item = message.get("data") or {}
                bids, asks = item.get("b") or [], item.get("a") or []
                if not bids or not asks:
                    continue
                best_bid, best_ask = bids[0], asks[0]
                base, quote, constraints = product_details(mapping, symbol)
                update(
                    "bybit", symbol, base, quote,
                    best_bid[0], best_ask[0], best_bid[1], best_ask[1], constraints,
                )
        except Exception as exc:
            with lock:
                health["bybit"].update({"connected": False, "error": f"{type(exc).__name__}: {exc}"})
            time.sleep(5)
        finally:
            if ws:
                try:
                    ws.close()
                except Exception:
                    pass


def discover_okx():
    try:
        payload = request_json(OKX_INFO_URL)
        result = {}
        for item in payload.get("data", []):
            base, quote = norm_asset(item.get("baseCcy")), norm_asset(item.get("quoteCcy"))
            if base in UNIVERSE and quote in UNIVERSE and item.get("state") == "live":
                result[item["instId"]] = {
                    "base": base,
                    "quote": quote,
                    "min_base": item.get("minSz", 0),
                    "min_quote": 0,
                    "qty_step": item.get("lotSz", 0),
                    "filter_source": "OKX_PUBLIC_INSTRUMENTS",
                }
        if result:
            write_atomic(OKX_PRODUCTS_CACHE, result)
            return result
        raise RuntimeError("empty OKX instruments")
    except Exception:
        try:
            cached = json.loads(OKX_PRODUCTS_CACHE.read_text(encoding="utf-8"))
            if cached:
                return cached
        except Exception:
            pass
        snapshot = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
        recovered = {}
        for quote in snapshot.get("quotes", []):
            if str(quote.get("exchange", "")).lower() != "okx":
                continue
            symbol = quote.get("symbol")
            if not symbol:
                continue
            recovered[symbol] = {
                "base": quote.get("base"),
                "quote": quote.get("quote"),
                "min_base": quote.get("min_base", 0),
                "min_quote": quote.get("min_quote", 0),
                "qty_step": quote.get("qty_step", 0),
                "filter_source": "OKX_LAST_PUBLIC_SNAPSHOT",
            }
        if recovered:
            write_atomic(OKX_PRODUCTS_CACHE, recovered)
            return recovered
        raise



def fetch_okx_tickers(mapping):
    payload = request_json(OKX_TICKERS_URL)
    return [{"symbol": item.get("instId"), "bid": item.get("bidPx"), "ask": item.get("askPx"), "bid_size": item.get("bidSz"), "ask_size": item.get("askSz")} for item in payload.get("data", [])]


def okx_loop():
    while True:
        ws = None
        try:
            mapping = discover_okx()
            if not mapping:
                raise RuntimeError("no supported OKX products")
            ws = websocket.create_connection(OKX_WS, timeout=25, enable_multithread=True)
            ws.settimeout(20)
            ws.send(json.dumps({
                "id": "arisokxpublic",
                "op": "subscribe",
                "args": [{"channel": "tickers", "instId": symbol} for symbol in sorted(mapping)],
            }))
            with lock:
                health["okx"].update({"connected": True, "pairs": len(mapping), "error": None})
            while True:
                try:
                    raw = ws.recv()
                except websocket.WebSocketTimeoutException:
                    ws.ping("keepalive")
                    continue
                message = json.loads(raw)
                if message.get("event") == "error":
                    raise RuntimeError(message.get("msg") or "OKX subscription error")
                if message.get("arg", {}).get("channel") != "tickers":
                    continue
                for item in message.get("data", []):
                    symbol = item.get("instId")
                    if symbol not in mapping:
                        continue
                    base, quote, constraints = product_details(mapping, symbol)
                    update(
                        "okx", symbol, base, quote,
                        item.get("bidPx"), item.get("askPx"),
                        item.get("bidSz"), item.get("askSz"), constraints,
                    )
        except Exception as exc:
            with lock:
                health["okx"].update({"connected": False, "error": f"{type(exc).__name__}: {exc}"})
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
    last_signal_signature = None
    last_signal_time = 0.0
    candidate_signature = None
    candidate_streak = 0
    positive_window_active = False
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
        positive_counts = {
            "theoretical": int(cycle_report.get("positive_theoretical_cycles_checked", 0) or 0),
            "simulated": int(cycle_report.get("positive_simulated_cycles_checked", 0) or 0),
            "net": int(cycle_report.get("positive_net_cycles_checked", 0) or 0),
            "executable": int(cycle_report.get("positive_executable_cycles_checked", 0) or 0),
            "signal_threshold": int(cycle_report.get("signal_threshold_cycles_checked", 0) or 0),
        }
        any_positive = any(positive_counts.values())
        if any_positive and not positive_window_active:
            audit_record = {
                "detected_at": payload["generated_at"],
                "event": "POSITIVE_WINDOW_STARTED",
                "counts": positive_counts,
                "best_theoretical_raw_profit_percent": cycle_report.get("best_theoretical_raw_profit_percent"),
                "best_simulated_raw_profit_percent": cycle_report.get("best_simulated_raw_profit_percent"),
                "best_net_profit_percent": (cycle_report.get("best_cycle") or {}).get("profit_percent"),
                "best_executable_net_profit_percent": (cycle_report.get("best_executable_cycle") or {}).get("profit_percent"),
                "real_trading": False,
            }
            with PROFIT_AUDIT.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(audit_record, ensure_ascii=False) + "\n")
        positive_window_active = any_positive
        opportunities = cycle_report.get("opportunities", [])
        threshold_candidates = [item for item in opportunities if item.get("profit_percent", -999) >= SIGNAL_PROFIT_PERCENT]
        actionable = [item for item in threshold_candidates if is_paper_funded(item, FUNDED_PAPER_WALLETS)]
        unfunded_actionable = [item for item in threshold_candidates if not is_paper_funded(item, FUNDED_PAPER_WALLETS)]
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
            "positive_theoretical_cycles": positive_counts["theoretical"],
            "positive_simulated_cycles": positive_counts["simulated"],
            "positive_net_cycles": positive_counts["net"],
            "positive_executable_cycles": positive_counts["executable"],
            "signal_threshold_cycles": positive_counts["signal_threshold"],
            "positive_window_active": positive_window_active,
            "actionable_candidates": len(actionable),
            "unfunded_actionable_candidates": len(unfunded_actionable),
            "funded_paper_wallets": sorted(FUNDED_PAPER_WALLETS),
            "candidate_streak": candidate_streak,
            "required_confirmations": SIGNAL_CONFIRMATIONS,
            "signal_profit_percent": SIGNAL_PROFIT_PERCENT,
            "confirmed_signal_ready": confirmed_signal_ready,
            "signals": 1 if confirmed_signal_ready else 0,
            "best_profit_percent": cycle_report.get("best_cycle", {}).get("profit_percent") if cycle_report.get("best_cycle") else None,
            "exchanges": state,
            "fee_schedule_version": FEE_INFO["version"],
            "fee_schedule_verified_at": FEE_INFO["verified_at"],
            "fee_model": FEE_INFO["mode"],
            "real_trading": False,
        })
        time.sleep(SAVE_SECONDS)

def run_forever():
    threads = [
        threading.Thread(target=coinbase_loop, daemon=True, name="cycle-coinbase"),
        threading.Thread(target=kraken_loop, daemon=True, name="cycle-kraken"),
        threading.Thread(target=binance_loop, daemon=True, name="cycle-binance"),
        threading.Thread(target=bybit_loop, daemon=True, name="cycle-bybit"),
        threading.Thread(target=okx_loop, daemon=True, name="cycle-okx"),
        threading.Thread(target=snapshot_loop, daemon=True, name="cycle-snapshot"),
    ]
    for thread in threads:
        thread.start()
    while True:
        time.sleep(60)

if __name__ == "__main__":
    run_forever()

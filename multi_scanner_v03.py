from pathlib import Path
from datetime import datetime
import csv, json, threading, time
import websocket

VERSION="0.3"
ROOT=Path.home()/"Arbitrage"
JOURNAL=ROOT/"journal"; JOURNAL.mkdir(parents=True,exist_ok=True)
HISTORY=JOURNAL/"multi_history_v03.csv"
COINBASE_URL="wss://advanced-trade-ws.coinbase.com"; KRAKEN_URL="wss://ws.kraken.com/v2"
ASSETS=("BTC","ETH","SOL","XRP")
FEES={"coinbase":{"maker":0.004,"taker":0.006},"kraken":{"maker":0.004,"taker":0.008}}
FRESH_AFTER=8; SAVE_EVERY=60; CHECK_EVERY=1
lock=threading.Lock()
market={a:{e:{"bid":None,"ask":None,"updated":0.0} for e in ("coinbase","kraken")} for a in ASSETS}

def f(v):
    try:return float(v)
    except (TypeError,ValueError):return None

def update(a,e,bid,ask):
    bid,ask=f(bid),f(ask)
    if bid is None or ask is None or bid<=0 or ask<=0 or bid>ask:return
    with lock: market[a][e]={"bid":bid,"ask":ask,"updated":time.time()}

def monitor_coinbase():
    delay=2
    while True:
        ws=None
        try:
            ws=websocket.create_connection(COINBASE_URL,timeout=20,enable_multithread=True); ws.settimeout(15)
            ws.send(json.dumps({"type":"subscribe","product_ids":[f"{a}-USD" for a in ASSETS],"channel":"ticker"}))
            ws.send(json.dumps({"type":"subscribe","channel":"heartbeats"})); delay=2
            while True:
                try: raw=ws.recv()
                except websocket.WebSocketTimeoutException: ws.ping("keepalive"); continue
                if not raw: raise ConnectionError("closed")
                m=json.loads(raw)
                if m.get("channel")!="ticker":continue
                for ev in m.get("events",[]):
                    for t in ev.get("tickers",[]):
                        p=t.get("product_id",""); a=p.split("-")[0]
                        if a in market:update(a,"coinbase",t.get("best_bid"),t.get("best_ask"))
        except Exception as exc:
            print(f"[Coinbase] {type(exc).__name__}; retry {delay}s"); time.sleep(delay); delay=min(delay*2,30)
        finally:
            if ws:
                try:ws.close()
                except Exception:pass

def monitor_kraken():
    delay=2
    while True:
        ws=None
        try:
            ws=websocket.create_connection(KRAKEN_URL,timeout=20,enable_multithread=True); ws.settimeout(15)
            ws.send(json.dumps({"method":"subscribe","params":{"channel":"ticker","symbol":[f"{a}/USD" for a in ASSETS],"event_trigger":"bbo"}})); delay=2
            while True:
                try:raw=ws.recv()
                except websocket.WebSocketTimeoutException:ws.ping("keepalive");continue
                if not raw:raise ConnectionError("closed")
                m=json.loads(raw)
                if m.get("channel")!="ticker":continue
                for t in m.get("data",[]):
                    a=t.get("symbol","").split("/")[0]
                    if a in market:update(a,"kraken",t.get("bid"),t.get("ask"))
        except Exception as exc:
            print(f"[Kraken] {type(exc).__name__}; retry {delay}s");time.sleep(delay);delay=min(delay*2,30)
        finally:
            if ws:
                try:ws.close()
                except Exception:pass

def route(a,buy,sell):
    with lock:b=market[a][buy].copy();s=market[a][sell].copy()
    now=time.time()
    if b["ask"] is None or s["bid"] is None or now-b["updated"]>FRESH_AFTER or now-s["updated"]>FRESH_AFTER:return None
    bp,sp=b["ask"],s["bid"]; scenarios={}
    for bm in ("taker","maker"):
        for sm in ("taker","maker"):
            qty=1/(bp*(1+FEES[buy][bm])); final=qty*sp*(1-FEES[sell][sm]); scenarios[f"{bm.upper()}->{sm.upper()}"]=(final-1)*100
    return {"asset":a,"buy":buy,"sell":sell,"buy_price":bp,"sell_price":sp,"gross":(sp/bp-1)*100,"scenarios":scenarios,"taker_taker":scenarios["TAKER->TAKER"],"best_mode":max(scenarios,key=scenarios.get),"best_net":max(scenarios.values())}

def results():
    out=[]
    for a in ASSETS:
        for b,s in (("coinbase","kraken"),("kraken","coinbase")):
            r=route(a,b,s)
            if r:out.append(r)
    return sorted(out,key=lambda x:x["taker_taker"],reverse=True)

def save(rows):
    exists=HISTORY.exists()
    with HISTORY.open("a",newline="",encoding="utf-8") as fh:
        w=csv.writer(fh)
        if not exists:w.writerow(["timestamp","asset","buy_exchange","sell_exchange","buy_price","sell_price","gross_percent","taker_taker_percent","maker_taker_percent","taker_maker_percent","maker_maker_percent","best_mode","best_net_percent"])
        ts=datetime.now().isoformat(timespec="seconds")
        for r in rows:w.writerow([ts,r["asset"],r["buy"],r["sell"],r["buy_price"],r["sell_price"],r["gross"],r["scenarios"]["TAKER->TAKER"],r["scenarios"]["MAKER->TAKER"],r["scenarios"]["TAKER->MAKER"],r["scenarios"]["MAKER->MAKER"],r["best_mode"],r["best_net"]])

print(f"ARBITRAGE MULTI SCANNER v{VERSION} | MONITORING ONLY | REAL TRADING DISABLED")
threading.Thread(target=monitor_coinbase,daemon=True).start();threading.Thread(target=monitor_kraken,daemon=True).start()
last=0.0
try:
    while True:
        rows=results();print("\n"+datetime.now().strftime("[%Y-%m-%d %H:%M:%S]"))
        if not rows:print("Waiting for fresh prices...")
        else:
            best_by={}
            for r in rows:best_by.setdefault(r["asset"],r)
            for a in ASSETS:
                r=best_by.get(a)
                if r:print(f"{a:4} | {r['buy']:8}->{r['sell']:8} | TT {r['taker_taker']:+.4f}% | best {r['best_mode']} {r['best_net']:+.4f}%")
                else:print(f"{a:4} | waiting...")
            best=rows[0]
            if best["taker_taker"]>0:print(f"*** PAPER TAKER/TAKER OPPORTUNITY: {best['asset']} {best['buy']}->{best['sell']} {best['taker_taker']:+.4f}% ***")
            elif best["best_net"]>0:print(f"PAPER MAKER-DEPENDENT SIGNAL ONLY: {best['best_mode']} {best['best_net']:+.4f}% (fill not guaranteed)")
            else:print("NO PAPER PROFIT AFTER CONFIGURED FEES")
            if time.time()-last>=SAVE_EVERY:save(rows);last=time.time()
        time.sleep(CHECK_EVERY)
except KeyboardInterrupt:print("\nScanner stopped safely.")

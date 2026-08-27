#!/usr/bin/env python3
import json
import websocket

URL = "wss://stream.bybit.com/v5/public/spot"
TOPICS = ["tickers.BTCUSDT", "tickers.ETHUSDT"]

ws = websocket.create_connection(URL, timeout=25, enable_multithread=True)
ws.settimeout(15)
try:
    ws.send(json.dumps({"req_id": "arisprobe01", "op": "subscribe", "args": TOPICS}))
    messages = []
    for _ in range(6):
        raw = ws.recv()
        message = json.loads(raw)
        messages.append({
            "keys": sorted(message),
            "topic": message.get("topic"),
            "type": message.get("type"),
            "success": message.get("success"),
            "ret_msg": message.get("ret_msg"),
            "data_type": type(message.get("data")).__name__,
            "data": message.get("data"),
        })
    print(json.dumps({"ok": True, "messages": messages}, ensure_ascii=False))
finally:
    ws.close()

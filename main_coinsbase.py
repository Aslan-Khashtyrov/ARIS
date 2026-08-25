from datetime import datetime
import json
import time
import websocket

URL = "wss://advanced-trade-ws.coinbase.com"
PRODUCT = "BTC-USD"

print("=" * 45)
print("       ARBITRAGE v0.1")
print("       COINBASE LIVE MONITOR")
print("=" * 45)

print("\nMode: MONITORING ONLY")
print("Real trading: DISABLED")
print("Virtual trading: DISABLED")
print(f"Market: {PRODUCT}")
print("\nPress CTRL+C to stop.\n")

while True:
    try:
        ws = websocket.create_connection(URL, timeout=15)

        subscribe = {
            "type": "subscribe",
            "product_ids": [PRODUCT],
            "channel": "ticker"
        }

        ws.send(json.dumps(subscribe))

        while True:
            message = json.loads(ws.recv())

            if message.get("channel") != "ticker":
                continue

            events = message.get("events", [])

            for event in events:
                tickers = event.get("tickers", [])

                for ticker in tickers:
                    price = ticker.get("price")

                    if not price:
                        continue

                    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                    print(f"[{now}] Coinbase BTC/USD = ${float(price):,.2f}")

                    with open("journal/coinbase.log", "a", encoding="utf-8") as log:
                        log.write(
                            f"{now} | Coinbase | BTC-USD | {price}\n"
                        )

    except KeyboardInterrupt:
        print("\nMonitor stopped.")
        break

    except Exception as error:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{now}] Connection error: {error}")
        print("Reconnecting in 5 seconds...")

        time.sleep(5)

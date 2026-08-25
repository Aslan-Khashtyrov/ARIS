from datetime import datetime
import time
import requests

URL = "https://api.binance.com/api/v3/ticker/price"
SYMBOL = "BTCUSDT"

print("=" * 45)
print("       ARBITRAGE v0.1")
print("       REAL MARKET MONITOR")
print("=" * 45)

print("\nMode: MONITORING ONLY")
print("Real trading: DISABLED")
print("Virtual trading: DISABLED")
print(f"Market: {SYMBOL}")
print("\nPress CTRL+C to stop.\n")

while True:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        response = requests.get(
            URL,
            params={"symbol": SYMBOL},
            timeout=5
        )

        response.raise_for_status()
        data = response.json()
        price = float(data["price"])

        print(f"[{now}] BTC/USDT = ${price:,.2f}")

        with open("journal/market.log", "a", encoding="utf-8") as log:
            log.write(f"{now} | BTCUSDT | {price}\n")

    except Exception as error:
        print(f"[{now}] ERROR: {error}")

    time.sleep(1)

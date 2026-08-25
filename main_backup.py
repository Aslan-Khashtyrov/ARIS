from datetime import datetime
import time

print("=" * 45)
print("       ARBITRAGE v0.1")
print("       Market Monitor")
print("=" * 45)

print("\nSystem started successfully.")
print("Mode: MONITORING ONLY")
print("Real trading: DISABLED")
print("Virtual trading: DISABLED")
print("\nPress CTRL+C to stop.\n")

while True:
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with open("journal/monitor.log", "a", encoding="utf-8") as log:
        log.write(f"{now} | Arbitrage is running | Monitoring\n")

    print(f"[{now}] Monitoring...")

    time.sleep(1)

import csv
import os
from datetime import datetime

HISTORY = "journal/market_history.csv"
LOG = "journal/paper_trades.log"

START_BALANCE = 1000.0
MIN_NET_SPREAD = 0.10

balance = START_BALANCE
trades = 0
wins = 0
losses = 0

def log(msg):
    os.makedirs("journal", exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {msg}\n")

print("=" * 64)
print("ARBITRAGE PAPER TRADER v0.1")
print("REAL TRADING: DISABLED")
print(f"START BALANCE: ${START_BALANCE:.2f}")
print(f"MIN NET SPREAD: {MIN_NET_SPREAD:.2f}%")
print("=" * 64)

with open(HISTORY, newline="", encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

for row in rows:
    try:
        net = float(row["taker_taker_net_percent"])
    except (ValueError, KeyError):
        continue

    if net >= MIN_NET_SPREAD:
        before = balance
        profit = balance * (net / 100.0)
        balance += profit

        trades += 1
        if profit > 0:
            wins += 1
        else:
            losses += 1

        msg = (
            f"PAPER TRADE | {row['timestamp']} | "
            f"{row['buy_exchange']} -> {row['sell_exchange']} | "
            f"net={net:.4f}% | profit=${profit:.4f} | "
            f"balance=${balance:.2f}"
        )

        print(msg)
        log(msg)

print()
print("=== SUMMARY ===")
print(f"Rows analysed: {len(rows)}")
print(f"Paper trades: {trades}")
print(f"Wins: {wins}")
print(f"Losses: {losses}")
print(f"Start balance: ${START_BALANCE:.2f}")
print(f"Final balance: ${balance:.2f}")
print(f"P/L: ${balance - START_BALANCE:.2f}")

import json
import os
import time
from datetime import datetime

STATS = "journal/session_stats.json"
HISTORY = "journal/market_history.csv"
LOG = "journal/guardian.log"

CHECK_EVERY = 10
WARN_AFTER = 150

def age(path):
    try:
        return time.time() - os.path.getmtime(path)
    except OSError:
        return None

def read_stats():
    try:
        with open(STATS, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def write_log(text):
    os.makedirs("journal", exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {text}\n")

print("=" * 60)
print("ARBITRAGE GUARDIAN v0.2")
print("MODE: OBSERVE ONLY")
print("AUTO-RESTART: DISABLED")
print("=" * 60)

last_cycles = None
problem_since = None

while True:
    stats = read_stats()

    cycles = stats.get("cycles")
    stats_age = age(STATS)
    history_age = age(HISTORY)

    healthy = (
        cycles is not None
        and stats_age is not None
        and history_age is not None
        and stats_age < WARN_AFTER
        and history_age < WARN_AFTER
    )

    now = datetime.now().strftime("%H:%M:%S")

    if healthy:
        if problem_since is not None:
            downtime = int(time.time() - problem_since)
            msg = f"RECOVERED after {downtime}s | cycles={cycles}"
            print(f"[{now}] {msg}")
            write_log(msg)
            problem_since = None
        else:
            print(
                f"[{now}] OK | cycles={cycles} | "
                f"stats={stats_age:.0f}s | history={history_age:.0f}s"
            )
    else:
        if problem_since is None:
            problem_since = time.time()
            msg = (
                f"WARNING | cycles={cycles} | "
                f"stats_age={stats_age} | history_age={history_age}"
            )
            write_log(msg)

        print(
            f"[{now}] WARNING | cycles={cycles} | "
            f"stats={stats_age} | history={history_age}"
        )

    if last_cycles is not None and cycles is not None and cycles < last_cycles:
        write_log(f"NOTICE | cycle counter reset {last_cycles} -> {cycles}")

    if cycles is not None:
        last_cycles = cycles

    time.sleep(CHECK_EVERY)

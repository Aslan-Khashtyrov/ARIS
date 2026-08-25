import json
import os
import time
from datetime import datetime

STATS = "journal/session_stats.json"
HISTORY = "journal/market_history.csv"
EVENTS = "journal/events.log"
LOG = "journal/guardian_v03.log"

CHECK_EVERY = 10

DEGRADED_AFTER = 150
HANG_AFTER = 600

def file_age(path):
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

def last_event():
    try:
        with open(EVENTS, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return lines[-1].strip() if lines else "none"
    except Exception:
        return "unavailable"

def log(msg):
    os.makedirs("journal", exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {msg}\n")

print("=" * 68)
print("ARBITRAGE GUARDIAN v0.3")
print("MODE: OBSERVE ONLY")
print("AUTO-RESTART: DISABLED")
print("=" * 68)

state = "STARTING"
problem_since = None
problem_start_cycles = None

while True:
    s = read_stats()

    cycles = s.get("cycles")
    cb = s.get("coinbase_reconnects")
    kr = s.get("kraken_reconnects")

    stats_age = file_age(STATS)
    history_age = file_age(HISTORY)

    stale = (
        stats_age is None
        or history_age is None
        or stats_age >= DEGRADED_AFTER
        or history_age >= DEGRADED_AFTER
    )

    now = datetime.now().strftime("%H:%M:%S")

    if not stale:
        new_state = "OK"

        if state != "OK":
            if problem_since is not None:
                duration = int(time.time() - problem_since)
                msg = (
                    f"RECOVERED | previous={state} | duration={duration}s | "
                    f"cycles={cycles} | CB={cb} | KR={kr}"
                )
                log(msg)
                print(f"[{now}] {msg}")

            problem_since = None
            problem_start_cycles = None

    else:
        if problem_since is None:
            problem_since = time.time()
            problem_start_cycles = cycles

        duration = time.time() - problem_since

        cycles_moved = (
            cycles is not None
            and problem_start_cycles is not None
            and cycles > problem_start_cycles
        )

        if duration >= HANG_AFTER and not cycles_moved:
            new_state = "POSSIBLE_HANG"
        else:
            new_state = "NETWORK_DEGRADED"

    if new_state != state:
        msg = (
            f"STATE {state} -> {new_state} | cycles={cycles} | "
            f"stats_age={stats_age} | history_age={history_age} | "
            f"CB={cb} | KR={kr} | last_event={last_event()}"
        )
        log(msg)

        state = new_state

    if state == "OK":
        print(
            f"[{now}] OK | cycles={cycles} | "
            f"stats={stats_age:.0f}s | history={history_age:.0f}s | "
            f"CB={cb} KR={kr}"
        )

    elif state == "NETWORK_DEGRADED":
        duration = int(time.time() - problem_since)

        print(
            f"[{now}] NETWORK_DEGRADED {duration}s | "
            f"cycles={cycles} | stats={stats_age:.0f}s | "
            f"history={history_age:.0f}s"
        )

    elif state == "POSSIBLE_HANG":
        duration = int(time.time() - problem_since)

        print(
            f"[{now}] POSSIBLE_HANG {duration}s | "
            f"cycles={cycles} | NO RESTART"
        )

    time.sleep(CHECK_EVERY)

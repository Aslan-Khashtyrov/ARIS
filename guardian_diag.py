import json
import os
import time
from datetime import datetime

STATS = "journal/session_stats.json"
HISTORY = "journal/market_history.csv"
EVENTS = "journal/events.log"
LOG = "journal/guardian_diag.log"

CHECK_EVERY = 10
WARN_AFTER = 150

def age(path):
    try:
        return time.time() - os.path.getmtime(path)
    except OSError:
        return None

def read_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def last_event():
    try:
        with open(EVENTS, "r", encoding="utf-8") as f:
            lines = f.readlines()
        return lines[-1].strip() if lines else "no events"
    except Exception:
        return "events unavailable"

def log(text):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now():%Y-%m-%d %H:%M:%S} | {text}\n")

print("=" * 64)
print("GUARDIAN DIAGNOSTICS v0.2.1")
print("MODE: OBSERVE ONLY")
print("AUTO-RESTART: DISABLED")
print("=" * 64)

problem_since = None

while True:
    stats = read_json(STATS)

    cycles = stats.get("cycles")
    cb_reconnects = stats.get("coinbase_reconnects")
    kr_reconnects = stats.get("kraken_reconnects")

    stats_age = age(STATS)
    history_age = age(HISTORY)

    healthy = (
        stats_age is not None
        and history_age is not None
        and stats_age < WARN_AFTER
        and history_age < WARN_AFTER
    )

    now = datetime.now().strftime("%H:%M:%S")

    if healthy:
        if problem_since is not None:
            downtime = int(time.time() - problem_since)
            msg = (
                f"RECOVERED | downtime={downtime}s | cycles={cycles} | "
                f"CB_reconnects={cb_reconnects} | KR_reconnects={kr_reconnects}"
            )
            print(f"[{now}] {msg}")
            log(msg)
            problem_since = None
        else:
            print(
                f"[{now}] OK | cycles={cycles} | "
                f"stats={stats_age:.0f}s | history={history_age:.0f}s | "
                f"CB={cb_reconnects} KR={kr_reconnects}"
            )
    else:
        if problem_since is None:
            problem_since = time.time()

            event = last_event()

            msg = (
                f"PROBLEM START | cycles={cycles} | "
                f"stats_age={stats_age} | history_age={history_age} | "
                f"CB_reconnects={cb_reconnects} | KR_reconnects={kr_reconnects} | "
                f"last_event={event}"
            )

            log(msg)

        duration = int(time.time() - problem_since)

        print(
            f"[{now}] PROBLEM {duration}s | cycles={cycles} | "
            f"stats={stats_age} | history={history_age}"
        )

    time.sleep(CHECK_EVERY)

from pathlib import Path
from datetime import datetime
import json
import os

VERSION = "0.1"

PROJECT = Path.home() / "Arbitrage"
JOURNAL = PROJECT / "journal"
QUEUE = PROJECT / "aris_queue"

HISTORY = JOURNAL / "multi_history_v02.csv"
MAIN_STATS = JOURNAL / "session_stats.json"

ALLOWED_AI_ACTIONS = {
    "STATUS",
    "ANALYZE",
}

SYSTEM_RULES = """
You are A.R.I.S. — Arbitrage Runtime Intelligence System.

Your role:
- inspect the state of the Arbitrage system;
- reason about diagnostics and monitoring;
- choose only from explicitly allowed actions.

Hard rules:
- Never request or perform real trading.
- Never move money.
- Never generate arbitrary shell commands.
- Never delete files.
- Never bypass Guardian or Worker protections.
- Allowed actions only: STATUS, ANALYZE.
- If no action is needed, choose NONE.
"""


def file_info(path):
    try:
        stat = path.stat()
        return {
            "exists": True,
            "size": stat.st_size,
            "modified": datetime.fromtimestamp(
                stat.st_mtime
            ).isoformat(timespec="seconds"),
        }
    except OSError:
        return {
            "exists": False,
            "size": None,
            "modified": None,
        }


def read_main_stats():
    if not MAIN_STATS.exists():
        return None

    try:
        return json.loads(
            MAIN_STATS.read_text(encoding="utf-8")
        )
    except Exception:
        return None


def build_context():
    return {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "aris_version": VERSION,
        "allowed_actions": sorted(ALLOWED_AI_ACTIONS),
        "real_trading": False,
        "shell_access": False,
        "files": {
            "multi_history_v02": file_info(HISTORY),
            "main_stats": file_info(MAIN_STATS),
        },
        "main_stats": read_main_stats(),
    }


def show_context():
    context = build_context()

    print("=" * 64)
    print(f"A.R.I.S. CORE v{VERSION}")
    print("AI CONNECTION : NOT CONNECTED")
    print("SHELL         : DISABLED")
    print("REAL TRADING  : DISABLED")
    print("AI ACTIONS    :", ", ".join(sorted(ALLOWED_AI_ACTIONS)))
    print("=" * 64)

    print(
        json.dumps(
            context,
            indent=2,
            ensure_ascii=False,
        )
    )

    print("=" * 64)
    print("CORE CONTEXT OK")


if __name__ == "__main__":
    show_context()

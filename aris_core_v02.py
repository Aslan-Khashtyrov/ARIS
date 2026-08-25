from pathlib import Path
from datetime import datetime
import json
import os

from openai import OpenAI

VERSION = "0.2"

PROJECT = Path.home() / "Arbitrage"
JOURNAL = PROJECT / "journal"

HISTORY = JOURNAL / "multi_history_v02.csv"
MAIN_STATS = JOURNAL / "session_stats.json"

ALLOWED_AI_ACTIONS = {
    "STATUS",
    "ANALYZE",
}

SYSTEM_RULES = """
You are A.R.I.S. — Arbitrage Runtime Intelligence System.

You monitor an arbitrage research system.

Hard rules:
- Real trading is disabled.
- Never move money.
- Never request arbitrary shell commands.
- Never delete files.
- Never bypass Guardian or Worker protections.
- You may choose only: STATUS, ANALYZE, NONE.
- If there is no clear need for action, choose NONE.

Return EXACTLY one word:
STATUS
ANALYZE
or
NONE
"""


def file_info(path):
    try:
        stat = path.stat()
        return {
            "exists": True,
            "size": stat.st_size,
            "age_seconds": round(
                datetime.now().timestamp() - stat.st_mtime,
                1
            ),
        }
    except OSError:
        return {
            "exists": False,
            "size": None,
            "age_seconds": None,
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
        "allowed_actions": sorted(ALLOWED_AI_ACTIONS),
        "real_trading": False,
        "shell_access": False,
        "multi_history": file_info(HISTORY),
        "main_stats_file": file_info(MAIN_STATS),
        "main_stats": read_main_stats(),
    }


def ask_aris():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY NOT LOADED")

    client = OpenAI()

    context = build_context()

    response = client.responses.create(
        model="gpt-5.6",
        instructions=SYSTEM_RULES,
        input=json.dumps(
            context,
            ensure_ascii=False
        ),
    )

    answer = response.output_text.strip().upper()

    if answer not in {"STATUS", "ANALYZE", "NONE"}:
        return "NONE"

    return answer


print("=" * 64)
print(f"A.R.I.S. CORE v{VERSION}")
print("AI CONNECTION : ENABLED")
print("SHELL         : DISABLED")
print("REAL TRADING  : DISABLED")
print("AI ACTIONS    : ANALYZE, STATUS, NONE")
print("=" * 64)

decision = ask_aris()

print("ARIS DECISION:", decision)
print("=" * 64)

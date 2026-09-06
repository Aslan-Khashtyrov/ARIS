#!/usr/bin/env python3
"""Retired legacy remote agent.

This compatibility module is deliberately inert: it performs no polling, file access,
process control, backup, health check, Git operation, or trading action.
"""

from __future__ import annotations

import json

VERSION = "retired-v0.1"
ALLOWED = frozenset({"PING"})


def execute(action: object) -> dict[str, object]:
    normalized = str(action or "").strip().upper()
    if normalized != "PING":
        raise PermissionError("LEGACY_AGENT_RETIRED_PING_ONLY")
    return {
        "pong": True,
        "version": VERSION,
        "mode": "retired_ping_only",
        "real_trading": False,
        "process_control": False,
    }


def main() -> int:
    print(
        json.dumps(
            {
                "ok": True,
                "state": "retired",
                "version": VERSION,
                "allowed": ["PING"],
                "real_trading": False,
                "process_control": False,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

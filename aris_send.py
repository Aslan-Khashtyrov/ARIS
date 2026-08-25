from pathlib import Path
from datetime import datetime
import json
import sys
import uuid

BASE = Path("aris_queue")
PENDING = BASE / "pending"
RESULTS = BASE / "results"

PENDING.mkdir(parents=True, exist_ok=True)
RESULTS.mkdir(parents=True, exist_ok=True)

ALLOWED_TO_SEND = {
    "STATUS",
    "ANALYZE",
}

if len(sys.argv) < 2:
    print("Usage: python aris_send.py STATUS")
    raise SystemExit(1)

action = sys.argv[1].strip().upper()

if action not in ALLOWED_TO_SEND:
    print("SEND DENIED:", action)
    raise SystemExit(2)

task_id = uuid.uuid4().hex

task = {
    "version": "0.1",
    "task_id": task_id,
    "created_at": datetime.now().isoformat(timespec="seconds"),
    "action": action,
    "source": "COMMAND_CENTER",
    "real_trading": False,
}

path = PENDING / f"{task_id}.json"

path.write_text(
    json.dumps(task, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

print("TASK SENT")
print("ID     :", task_id)
print("ACTION :", action)
print("FILE   :", path)

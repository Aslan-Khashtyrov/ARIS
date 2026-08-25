from pathlib import Path
from datetime import datetime
import json
import uuid

BASE = Path("aris_queue")
PENDING = BASE / "pending"
DONE = BASE / "done"
REJECTED = BASE / "rejected"
RESULTS = BASE / "results"

ALLOWED_ACTIONS = {
    "STATUS",
    "ANALYZE",
    "BACKUP",
}

for folder in (PENDING, DONE, REJECTED, RESULTS):
    folder.mkdir(parents=True, exist_ok=True)

task = {
    "version": "0.1",
    "task_id": uuid.uuid4().hex,
    "created_at": datetime.now().isoformat(timespec="seconds"),
    "action": "STATUS",
    "source": "LAB",
    "real_trading": False,
}

path = PENDING / f"{task['task_id']}.json"

path.write_text(
    json.dumps(task, indent=2, ensure_ascii=False),
    encoding="utf-8",
)

loaded = json.loads(path.read_text(encoding="utf-8"))

assert loaded["action"] in ALLOWED_ACTIONS
assert loaded["real_trading"] is False
assert loaded["task_id"] == task["task_id"]

print("=" * 58)
print("A.R.I.S. TASK QUEUE v0.1")
print("MODE         : SAFE TEST")
print("EXECUTION    : DISABLED")
print("REAL TRADING : DISABLED")
print("-" * 58)
print("TASK CREATED :", loaded["task_id"])
print("ACTION       :", loaded["action"])
print("QUEUE        :", path)
print("-" * 58)
print("TASK QUEUE TEST OK")
print("=" * 58)

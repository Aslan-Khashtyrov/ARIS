#!/usr/bin/env python3
from __future__ import annotations

import subprocess
import sys
from datetime import datetime
from pathlib import Path

VERSION = "0.2"
ROOT = Path.home() / "Arbitrage"
REMOTE = "origin"
BRANCH = "main"

PROTECTED_PREFIXES = (
    ".env",
    "journal/",
    "backups/",
    "aris_queue/",
    "guardian_state/",
)

def run(args, *, check=False):
    return subprocess.run(
        args,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=check,
    )

def out(args):
    p = run(args)
    if p.returncode != 0:
        raise RuntimeError((p.stderr or p.stdout).strip() or "command failed")
    return p.stdout.strip()

def fail(msg):
    print(f"[ERROR] {msg}")
    sys.exit(1)

print("=" * 56)
print(f"ARIS UPDATER v{VERSION}")
print("Time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print("=" * 56)

if not ROOT.exists():
    fail(f"Project not found: {ROOT}")

# 1) Refuse to update over local edits.
status = out(["git", "status", "--porcelain"])
if status:
    print("[STOP] Working tree is not clean.")
    print(status)
    print("No files were changed.")
    sys.exit(2)

# 2) Refresh remote state.
print("[1] Checking GitHub...")
fetch = run(["git", "fetch", REMOTE])
if fetch.returncode != 0:
    fail((fetch.stderr or fetch.stdout).strip())

local = out(["git", "rev-parse", "HEAD"])
remote = out(["git", "rev-parse", f"{REMOTE}/{BRANCH}"])

print("LOCAL :", local[:10])
print("REMOTE:", remote[:10])

if local == remote:
    print("[OK] ARIS is up to date")
    print("=" * 56)
    sys.exit(0)

# 3) Make sure update is fast-forward only.
base = out(["git", "merge-base", local, remote])
if base != local:
    fail("Remote branch is not a fast-forward update. Manual review required.")

# 4) Inspect changed paths before touching files.
changed = out(["git", "diff", "--name-only", f"{local}..{remote}"]).splitlines()
protected = [
    p for p in changed
    if any(p == x.rstrip("/") or p.startswith(x) for x in PROTECTED_PREFIXES)
]
if protected:
    print("[STOP] Update touches protected paths:")
    for p in protected:
        print(" -", p)
    print("No files were changed.")
    sys.exit(3)

print("[2] Update available")
for p in changed[:30]:
    print(" -", p)
if len(changed) > 30:
    print(f" ... and {len(changed) - 30} more")

# 5) Create a local rollback tag pointing to the current known-good commit.
tag = "aris-backup-" + datetime.now().strftime("%Y%m%d-%H%M%S")
tag_result = run(["git", "tag", tag, local])
if tag_result.returncode != 0:
    fail("Could not create rollback tag")

print("[3] Backup tag:", tag)

# 6) Apply update strictly as fast-forward.
pull = run(["git", "merge", "--ff-only", f"{REMOTE}/{BRANCH}"])
if pull.returncode != 0:
    print("[ROLLBACK] Update failed before validation")
    run(["git", "reset", "--hard", local])
    fail((pull.stderr or pull.stdout).strip())

# 7) Validate Python syntax for every tracked .py file.
print("[4] Validating Python files...")
tracked = out(["git", "ls-files", "*.py"]).splitlines()
bad = []

for rel in tracked:
    p = run([sys.executable, "-m", "py_compile", rel])
    if p.returncode != 0:
        bad.append((rel, (p.stderr or p.stdout).strip()))

if bad:
    print("[ROLLBACK] Validation failed:")
    for rel, err in bad:
        print(f" - {rel}")
        if err:
            print("   ", err.replace("\n", "\n    "))
    run(["git", "reset", "--hard", local])
    print("[OK] Restored previous commit:", local[:10])
    sys.exit(4)

new_head = out(["git", "rev-parse", "HEAD"])
print("[5] Validation passed")
print("[OK] ARIS updated safely")
print("OLD :", local[:10])
print("NEW :", new_head[:10])
print("BACKUP TAG:", tag)
print("=" * 56)

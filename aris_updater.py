import subprocess
from datetime import datetime

def run(cmd):
    return subprocess.run(
        cmd,
        shell=True,
        text=True,
        capture_output=True
    )

print("=" * 45)
print("ARIS UPDATER v0.1")
print("Time:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
print("=" * 45)

print("[1] Checking GitHub...")
fetch = run("git fetch origin")

if fetch.returncode != 0:
    print("[ERROR] GitHub check failed")
    print(fetch.stderr)
    raise SystemExit(1)

local = run("git rev-parse HEAD").stdout.strip()
remote = run("git rev-parse origin/main").stdout.strip()

print("LOCAL :", local[:10])
print("REMOTE:", remote[:10])

if local == remote:
    print("[OK] ARIS is up to date")
else:
    print("[UPDATE AVAILABLE]")
    print("New ARIS version found on GitHub.")
    print("No files were changed.")

print("=" * 45)

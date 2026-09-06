from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parent
WORKER = ROOT / "aris_worker_v03.py"


def run_probe(source: str, home: str) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    environment["HOME"] = home
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(source), str(WORKER)],
        cwd=home,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
    )


class WorkerImportSafetyTests(unittest.TestCase):
    def test_import_has_no_runtime_or_thread_side_effects(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            completed = run_probe(
                """
                import importlib.util
                import json
                import sys
                import threading
                from pathlib import Path

                worker_path = Path(sys.argv[1])
                before = sorted(
                    (thread.name, thread.ident) for thread in threading.enumerate()
                )
                spec = importlib.util.spec_from_file_location(
                    "aris_worker_import_probe", worker_path
                )
                module = importlib.util.module_from_spec(spec)
                assert spec.loader is not None
                spec.loader.exec_module(module)
                after = sorted(
                    (thread.name, thread.ident) for thread in threading.enumerate()
                )
                print(
                    json.dumps(
                        {
                            "runtime_root_exists": (Path.home() / "Arbitrage").exists(),
                            "threads_unchanged": before == after,
                            "has_main": callable(getattr(module, "main", None)),
                            "has_start_services": callable(
                                getattr(module, "start_services", None)
                            ),
                        }
                    )
                )
                """,
                home,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            payload = json.loads(completed.stdout)
            self.assertFalse(payload["runtime_root_exists"])
            self.assertTrue(payload["threads_unchanged"])
            self.assertTrue(payload["has_main"])
            self.assertTrue(payload["has_start_services"])

    def test_explicit_service_start_preserves_selected_supervisors(self) -> None:
        with tempfile.TemporaryDirectory() as home:
            completed = run_probe(
                """
                import importlib.util
                import json
                import sys
                from pathlib import Path

                worker_path = Path(sys.argv[1])
                spec = importlib.util.spec_from_file_location(
                    "aris_worker_service_probe", worker_path
                )
                module = importlib.util.module_from_spec(spec)
                assert spec.loader is not None
                spec.loader.exec_module(module)

                started = []

                class FakeThread:
                    def __init__(self, *, target, daemon, name):
                        self.target = target
                        self.daemon = daemon
                        self.name = name

                    def start(self):
                        started.append(
                            {
                                "name": self.name,
                                "daemon": self.daemon,
                                "target": self.target.__name__,
                            }
                        )

                module.threading.Thread = FakeThread
                module.ensure_runtime_dirs()
                module.start_services()
                print(json.dumps(started))
                """,
                home,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)
            started = json.loads(completed.stdout)
            self.assertEqual(
                [item["name"] for item in started],
                [
                    "cycle-collector-supervisor",
                    "paper-ledger-supervisor",
                    "operational-report-supervisor",
                    "cycle-metrics-supervisor",
                    "cross-exchange-supervisor",
                    "cross-paper-ledger-supervisor",
                    "cross-inventory-low-risk-supervisor",
                ],
            )
            self.assertTrue(all(item["daemon"] for item in started))
            self.assertNotIn(
                "cross_inventory_ledger_supervisor",
                [item["target"] for item in started],
            )


if __name__ == "__main__":
    unittest.main()

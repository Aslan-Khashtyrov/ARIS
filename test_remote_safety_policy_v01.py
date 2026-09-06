from pathlib import Path
import unittest

import aris_remote_agent_v01 as legacy_v01
import aris_remote_agent_v02 as legacy_v02


class RetiredRemoteAgentPolicyTests(unittest.TestCase):
    def test_legacy_agents_are_inert_and_ping_only(self):
        for module in (legacy_v01, legacy_v02):
            with self.subTest(module=module.__name__):
                self.assertEqual(module.ALLOWED, frozenset({"PING"}))
                self.assertFalse(module.execute("PING")["process_control"])
                self.assertFalse(module.execute("PING")["real_trading"])
                for action in (
                    "STATUS",
                    "HEALTHCHECK",
                    "BACKUP",
                    "RESTART_COMPONENTS",
                    "EXEC",
                ):
                    with self.assertRaises(PermissionError):
                        module.execute(action)

    def test_legacy_agents_contain_no_process_or_git_execution(self):
        for module in (legacy_v01, legacy_v02):
            source = Path(module.__file__).read_text(encoding="utf-8")
            self.assertNotIn("os.kill", source)
            self.assertNotIn("subprocess", source)
            self.assertNotIn("git fetch", source)
            self.assertNotIn("RESTART_COMPONENTS", source)

    def test_safe_stop_validates_pid_and_process_identity(self):
        source = Path("aris_stop_safe.sh").read_text(encoding="utf-8")
        self.assertIn("*[!0-9]*", source)
        self.assertIn('[ "$pid" -le 1 ]', source)
        self.assertIn('/proc/$pid/cmdline', source)
        self.assertIn("belongs to another process", source)
        self.assertIn('kill -TERM -- "$pid"', source)
        self.assertNotIn("kill -9", source)


if __name__ == "__main__":
    unittest.main()

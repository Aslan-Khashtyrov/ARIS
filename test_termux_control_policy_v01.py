from pathlib import Path
import unittest

import aris_termux_control_v01 as bridge


class TermuxControlPolicyTests(unittest.TestCase):
    def test_allowlist_is_ping_only(self):
        self.assertEqual(bridge.ALLOWED_ACTIONS, frozenset({"PING"}))

    def test_ping_returns_explicit_safe_mode(self):
        command_id, action, result = bridge.execute(
            {
                "id": "unit-test-ping",
                "action": "PING",
                "note": "read-only policy test",
            }
        )
        self.assertEqual(command_id, "unit-test-ping")
        self.assertEqual(action, "PING")
        self.assertTrue(result["pong"])
        self.assertEqual(result["mode"], "github_ping_only")
        self.assertFalse(result["real_trading"])

    def test_mutating_and_process_actions_are_denied(self):
        for action in (
            "EXEC",
            "WRITE_TEXT",
            "RESTART_COMPONENTS",
            "BACKUP",
            "HEALTHCHECK",
            "STATUS",
        ):
            with self.subTest(action=action):
                with self.assertRaises(PermissionError):
                    bridge.execute({"id": f"deny-{action.lower()}", "action": action})

    def test_extra_execution_fields_are_denied_even_for_ping(self):
        with self.assertRaises(PermissionError):
            bridge.execute(
                {
                    "id": "ping-with-payload",
                    "action": "PING",
                    "argv": ["pkill", "-f", "main.py"],
                }
            )

    def test_invalid_command_id_is_denied(self):
        with self.assertRaises(ValueError):
            bridge.execute({"id": "../unsafe", "action": "PING"})

    def test_visible_log_text_removes_terminal_controls(self):
        rendered = bridge.safe_display("\x1b[31mстрока\nдва\x07")
        self.assertNotIn("\x1b", rendered)
        self.assertNotIn("\x07", rendered)
        self.assertNotIn("\n", rendered)
        self.assertIn("строка два", rendered)

    def test_status_publication_uses_a_dedicated_detached_worktree(self):
        self.assertNotEqual(bridge.ROOT, bridge.MAIN_ROOT)
        self.assertTrue(bridge.REPORT_PATH.is_relative_to(bridge.ROOT))
        source = Path(bridge.__file__).read_text(encoding="utf-8")
        self.assertIn('"worktree",', source)
        self.assertIn('"--detach",', source)
        self.assertIn("controller refuses to use the live A.R.I.S. working tree", source)
        self.assertNotIn("controller requires local main branch", source)


if __name__ == "__main__":
    unittest.main()

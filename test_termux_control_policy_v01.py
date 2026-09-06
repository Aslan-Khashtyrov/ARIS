import ast
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

    def test_one_shot_handoff_can_signal_only_verified_parent(self):
        source = Path("aris_controller_handoff_once.py").read_text(encoding="utf-8")
        tree = ast.parse(source)
        kill_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "os"
            and node.func.attr == "kill"
        ]
        self.assertEqual(len(kill_calls), 1)
        self.assertEqual(ast.unparse(kill_calls[0].args[0]), "parent_pid")
        self.assertEqual(ast.unparse(kill_calls[0].args[1]), "signal.SIGTERM")
        self.assertIn('"aris_termux_control_v01.py" not in parent_cmdline', source)
        self.assertNotIn("pkill", source)
        self.assertNotIn("killall", source)
        self.assertNotIn("subprocess", source)


if __name__ == "__main__":
    unittest.main()

import tempfile
import unittest
from pathlib import Path

from relaylab.workspace import (
    Workspace,
    WorkspaceSafetyError,
    run_deterministic_checks,
)


class WorkspaceTests(unittest.TestCase):
    def test_write_and_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Workspace(Path(tmp))
            workspace.write_file("src/hello.txt", "hi")
            self.assertEqual(workspace.snapshot()["src/hello.txt"], "hi")

    def test_rejects_parent_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Workspace(Path(tmp))
            with self.assertRaises(WorkspaceSafetyError):
                workspace.write_file("../escape.txt", "no")

    def test_rejects_absolute_path(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Workspace(Path(tmp))
            with self.assertRaises(WorkspaceSafetyError):
                workspace.write_file("/tmp/escape.txt", "no")

    def test_python_syntax_check(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            workspace = Workspace(Path(tmp))
            workspace.write_file("good.py", "print('hello')\n")
            workspace.write_file("bad.py", "def broken(:\n    pass\n")

            checks = run_deterministic_checks(workspace)
            statuses = {item["check"]: item["status"] for item in checks}

            self.assertEqual(statuses["python_syntax:good.py"], "passed")
            self.assertEqual(statuses["python_syntax:bad.py"], "failed")


if __name__ == "__main__":
    unittest.main()

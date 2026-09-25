from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class WorkspaceSafetyError(ValueError):
    pass


class Workspace:
    def __init__(self, root: Path, max_snapshot_bytes_per_file: int = 40_000) -> None:
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.max_snapshot_bytes_per_file = max_snapshot_bytes_per_file

    def _safe_path(self, relative_path: str) -> Path:
        path = Path(relative_path)
        if path.is_absolute():
            raise WorkspaceSafetyError("Absolute paths are not allowed.")

        resolved = (self.root / path).resolve()
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise WorkspaceSafetyError(
                f"Path escapes the experiment workspace: {relative_path}"
            ) from exc

        return resolved

    def write_file(self, relative_path: str, content: str) -> None:
        target = self._safe_path(relative_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")

    def delete_file(self, relative_path: str) -> None:
        target = self._safe_path(relative_path)
        if target.exists() and target.is_file():
            target.unlink()

    def apply_builder_actions(self, payload: dict[str, Any]) -> dict[str, Any]:
        files = payload.get("files", [])
        deletes = payload.get("deletes", [])

        if not isinstance(files, list) or not isinstance(deletes, list):
            raise WorkspaceSafetyError("'files' and 'deletes' must be arrays.")

        written: list[str] = []
        removed: list[str] = []

        for item in files:
            if not isinstance(item, dict):
                raise WorkspaceSafetyError("Each file action must be an object.")
            path = item.get("path")
            content = item.get("content")
            if not isinstance(path, str) or not isinstance(content, str):
                raise WorkspaceSafetyError(
                    "Each file action requires string 'path' and 'content' fields."
                )
            self.write_file(path, content)
            written.append(path)

        for path in deletes:
            if not isinstance(path, str):
                raise WorkspaceSafetyError("Delete paths must be strings.")
            self.delete_file(path)
            removed.append(path)

        return {"written": written, "deleted": removed}

    def snapshot(self) -> dict[str, str]:
        files: dict[str, str] = {}
        for path in sorted(self.root.rglob("*")):
            if not path.is_file():
                continue

            relative = str(path.relative_to(self.root))
            try:
                raw = path.read_bytes()
            except OSError:
                continue

            if len(raw) > self.max_snapshot_bytes_per_file:
                files[relative] = (
                    raw[: self.max_snapshot_bytes_per_file].decode(
                        "utf-8", errors="replace"
                    )
                    + "\n...[truncated by RelayLab]..."
                )
            else:
                files[relative] = raw.decode("utf-8", errors="replace")

        return files


def run_deterministic_checks(workspace: Workspace) -> list[dict[str, str]]:
    """Inspect generated files without executing model-authored code."""
    results: list[dict[str, str]] = []
    snapshot = workspace.snapshot()

    if not snapshot:
        return [
            {
                "check": "workspace_not_empty",
                "status": "failed",
                "detail": "The Builder produced no files.",
            }
        ]

    results.append(
        {
            "check": "workspace_not_empty",
            "status": "passed",
            "detail": f"{len(snapshot)} file(s) present.",
        }
    )

    for relative, content in snapshot.items():
        suffix = Path(relative).suffix.lower()

        if suffix == ".py":
            try:
                compile(content, relative, "exec")
            except SyntaxError as exc:
                results.append(
                    {
                        "check": f"python_syntax:{relative}",
                        "status": "failed",
                        "detail": f"{exc.msg} at line {exc.lineno}.",
                    }
                )
            else:
                results.append(
                    {
                        "check": f"python_syntax:{relative}",
                        "status": "passed",
                        "detail": "Python syntax compiled successfully.",
                    }
                )

        if suffix == ".json":
            try:
                json.loads(content)
            except json.JSONDecodeError as exc:
                results.append(
                    {
                        "check": f"json_parse:{relative}",
                        "status": "failed",
                        "detail": f"{exc.msg} at line {exc.lineno}.",
                    }
                )
            else:
                results.append(
                    {
                        "check": f"json_parse:{relative}",
                        "status": "passed",
                        "detail": "JSON parsed successfully.",
                    }
                )

    return results

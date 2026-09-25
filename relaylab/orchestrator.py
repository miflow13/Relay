from __future__ import annotations

import json
import re
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from relaylab.agents import BuilderAgent, ReviewerAgent
from relaylab.config import Settings
from relaylab.ollama_client import OllamaClient
from relaylab.workspace import Workspace, run_deterministic_checks


class RelayLab:
    def __init__(self, project_root: Path, settings: Settings) -> None:
        self.project_root = project_root.resolve()
        self.settings = settings

        client = OllamaClient(
            settings.ollama_url,
            timeout_seconds=settings.request_timeout_seconds,
        )

        prompts = self.project_root / "prompts"
        self.builder = BuilderAgent(
            client=client,
            model=settings.builder_model,
            prompt_path=prompts / "builder.md",
        )
        self.reviewer = ReviewerAgent(
            client=client,
            model=settings.reviewer_model,
            prompt_path=prompts / "reviewer.md",
        )

    def run(self, *, task: str, experiment_name: str) -> dict[str, Any]:
        safe_name = self._validate_experiment_name(experiment_name)

        workspace = Workspace(
            self.project_root / "experiments" / safe_name / "workspace",
            max_snapshot_bytes_per_file=self.settings.max_snapshot_bytes_per_file,
        )

        run_id = self._make_run_id(safe_name)
        run_dir = self.project_root / "runs" / run_id
        run_dir.mkdir(parents=True, exist_ok=False)

        manifest = {
            "run_id": run_id,
            "experiment_name": safe_name,
            "task": task,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "settings": asdict(self.settings),
        }
        self._write_json(run_dir / "manifest.json", manifest)

        feedback = "No reviewer feedback yet. Create the first implementation."
        checks: list[dict[str, str]] = []
        final_status = "max_rounds_reached"

        for round_number in range(1, self.settings.max_rounds + 1):
            before = workspace.snapshot()

            builder_payload = self.builder.build(
                task=task,
                feedback=feedback,
                workspace_snapshot=before,
                checks=checks,
            )
            raw_builder = builder_payload.pop("_raw_response")
            actions = workspace.apply_builder_actions(builder_payload)

            checks = run_deterministic_checks(workspace)
            after = workspace.snapshot()

            reviewer_payload = self.reviewer.review(
                task=task,
                builder_summary=builder_payload["summary"],
                workspace_snapshot=after,
                checks=checks,
            )
            raw_reviewer = reviewer_payload.pop("_raw_response")

            round_log = {
                "round": round_number,
                "builder": builder_payload,
                "builder_raw": raw_builder,
                "applied_actions": actions,
                "checks": checks,
                "reviewer": reviewer_payload,
                "reviewer_raw": raw_reviewer,
                "workspace_files": sorted(after.keys()),
            }
            self._write_json(
                run_dir / f"round-{round_number:02d}.json",
                round_log,
            )

            print(
                f"[round {round_number}] builder wrote "
                f"{len(actions['written'])} file(s); reviewer: "
                f"{reviewer_payload['status']}"
            )

            if reviewer_payload["status"] == "approved":
                final_status = "approved"
                feedback = reviewer_payload["feedback"]
                break

            feedback = reviewer_payload["feedback"]

        result = {
            "run_id": run_id,
            "status": final_status,
            "rounds_completed": round_number,
            "reviewer_feedback": feedback,
            "workspace": str(workspace.root),
            "run_log": str(run_dir),
            "checks": checks,
        }
        self._write_json(run_dir / "result.json", result)
        return result

    @staticmethod
    def _validate_experiment_name(name: str) -> str:
        if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", name):
            raise ValueError(
                "Experiment name must be 1-64 characters and contain only "
                "letters, numbers, '.', '_' or '-'."
            )
        return name

    @staticmethod
    def _make_run_id(experiment_name: str) -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        return f"{stamp}-{experiment_name}-{uuid.uuid4().hex[:8]}"

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

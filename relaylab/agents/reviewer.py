from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from relaylab.jsonutil import AgentProtocolError, extract_json_object
from relaylab.ollama_client import OllamaClient


class ReviewerAgent:
    def __init__(
        self,
        *,
        client: OllamaClient,
        model: str,
        prompt_path: Path,
    ) -> None:
        self.client = client
        self.model = model
        self.system_prompt = prompt_path.read_text(encoding="utf-8")

    def review(
        self,
        *,
        task: str,
        builder_summary: str,
        workspace_snapshot: dict[str, str],
        checks: list[dict[str, str]],
    ) -> dict[str, Any]:
        user_message = {
            "task": task,
            "builder_summary": builder_summary,
            "workspace": workspace_snapshot,
            "deterministic_checks": checks,
        }

        response = self.client.chat(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {
                    "role": "user",
                    "content": json.dumps(user_message, indent=2),
                },
            ],
            temperature=0.1,
        )

        payload = extract_json_object(response)
        self._validate(payload)
        payload["_raw_response"] = response
        return payload

    @staticmethod
    def _validate(payload: dict[str, Any]) -> None:
        status = payload.get("status")
        if status not in {"approved", "changes_requested"}:
            raise AgentProtocolError(
                "Reviewer 'status' must be 'approved' or 'changes_requested'."
            )

        if not isinstance(payload.get("feedback"), str):
            raise AgentProtocolError("Reviewer response requires string 'feedback'.")

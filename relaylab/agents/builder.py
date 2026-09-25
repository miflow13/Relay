from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from relaylab.jsonutil import AgentProtocolError, extract_json_object
from relaylab.ollama_client import OllamaClient


class BuilderAgent:
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

    def build(
        self,
        *,
        task: str,
        feedback: str,
        workspace_snapshot: dict[str, str],
        checks: list[dict[str, str]],
    ) -> dict[str, Any]:
        user_message = {
            "task": task,
            "reviewer_feedback": feedback,
            "current_workspace": workspace_snapshot,
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
            temperature=0.2,
        )

        payload = extract_json_object(response)
        self._validate(payload)
        payload["_raw_response"] = response
        return payload

    @staticmethod
    def _validate(payload: dict[str, Any]) -> None:
        if not isinstance(payload.get("summary"), str):
            raise AgentProtocolError("Builder response requires string 'summary'.")

        if not isinstance(payload.get("files", []), list):
            raise AgentProtocolError("Builder 'files' must be an array.")

        if not isinstance(payload.get("deletes", []), list):
            raise AgentProtocolError("Builder 'deletes' must be an array.")

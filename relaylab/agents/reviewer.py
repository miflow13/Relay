from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from relaylab.jsonutil import AgentProtocolError, extract_json_object
from relaylab.ollama_client import OllamaClient


class ReviewerAgent:
    STATUS_ALIASES = {
        "approved": "approved",
        "approve": "approved",
        "accepted": "approved",
        "accept": "approved",
        "pass": "approved",
        "passed": "approved",
        "looks_good": "approved",
        "changes_requested": "changes_requested",
        "change_requested": "changes_requested",
        "request_changes": "changes_requested",
        "requested_changes": "changes_requested",
        "needs_changes": "changes_requested",
        "needs_change": "changes_requested",
        "rejected": "changes_requested",
        "reject": "changes_requested",
        "failed": "changes_requested",
        "fail": "changes_requested",
    }

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
        payload = self._normalize_payload(payload)

        try:
            self._validate(payload)
        except AgentProtocolError:
            # Small local models can understand the review correctly while using
            # a slightly different enum label. Give the Reviewer one cheap,
            # explicit repair turn instead of aborting the whole experiment.
            repair_response = self.client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Repair the JSON protocol only. Return valid JSON and "
                            "do not redo the review."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "invalid_response": payload,
                                "required_schema": {
                                    "status": "approved | changes_requested",
                                    "feedback": "string",
                                },
                                "instruction": (
                                    "Preserve the meaning of the review. Map any "
                                    "positive/pass verdict to 'approved' and any "
                                    "reject/fix/needs-work verdict to "
                                    "'changes_requested'."
                                ),
                            },
                            indent=2,
                        ),
                    },
                ],
                temperature=0.0,
            )
            repaired = extract_json_object(repair_response)
            payload = self._normalize_payload(repaired)
            self._validate(payload)
            response = (
                response
                + "\n\n--- RELAYLAB PROTOCOL REPAIR ---\n"
                + repair_response
            )

        payload["_raw_response"] = response
        return payload

    @classmethod
    def _normalize_payload(cls, payload: dict[str, Any]) -> dict[str, Any]:
        normalized = dict(payload)

        status = normalized.get("status")
        if isinstance(status, str):
            key = re.sub(r"[^a-z0-9]+", "_", status.strip().lower()).strip("_")
            normalized["status"] = cls.STATUS_ALIASES.get(key, key)

        # A few local models prefer semantically equivalent field names.
        if not isinstance(normalized.get("feedback"), str):
            for alias in ("review", "reason", "comments", "message"):
                value = normalized.get(alias)
                if isinstance(value, str):
                    normalized["feedback"] = value
                    break

        return normalized

    @staticmethod
    def _validate(payload: dict[str, Any]) -> None:
        status = payload.get("status")
        if status not in {"approved", "changes_requested"}:
            raise AgentProtocolError(
                "Reviewer 'status' must resolve to 'approved' or "
                f"'changes_requested'; received {status!r}."
            )

        if not isinstance(payload.get("feedback"), str):
            raise AgentProtocolError("Reviewer response requires string 'feedback'.")

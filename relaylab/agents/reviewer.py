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
        "fixes_required": "changes_requested",
        "revision_required": "changes_requested",
    }

    ENVELOPE_KEYS = ("review", "result", "response", "verdict", "decision")
    STATUS_KEYS = ("status", "verdict", "decision", "outcome", "result")
    FEEDBACK_KEYS = (
        "feedback",
        "reason",
        "comments",
        "message",
        "review",
        "issues",
        "changes",
        "required_changes",
        "recommendations",
    )

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

        payload = self._normalize_payload(extract_json_object(response))
        protocol_warning: str | None = None

        try:
            self._validate(payload)
        except AgentProtocolError as first_error:
            repair_response = self.client.chat(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Repair the JSON protocol only. Return ONE top-level JSON "
                            "object with exactly these fields: status and feedback. "
                            "Do not nest the object and do not redo the review."
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

            response = (
                response
                + "\n\n--- RELAYLAB PROTOCOL REPAIR ---\n"
                + repair_response
            )
            repaired = self._normalize_payload(extract_json_object(repair_response))

            try:
                self._validate(repaired)
                payload = repaired
            except AgentProtocolError as repair_error:
                protocol_warning = (
                    "Reviewer protocol could not be normalized after one repair "
                    f"attempt ({first_error}; {repair_error}). RelayLab safely "
                    "treated the review as changes_requested."
                )
                feedback = self._best_effort_feedback(repaired)
                if not feedback:
                    feedback = self._best_effort_feedback(payload)
                if not feedback:
                    feedback = (
                        "The Reviewer produced an invalid response format. Re-check "
                        "the task, deterministic checks, and current implementation "
                        "carefully before the next review."
                    )

                payload = {
                    "status": "changes_requested",
                    "feedback": feedback,
                    "_protocol_fallback": True,
                    "_malformed_payload": repaired,
                }

        if protocol_warning:
            payload["_protocol_warning"] = protocol_warning

        payload["_raw_response"] = response
        return payload

    @classmethod
    def _normalize_payload(cls, payload: dict[str, Any]) -> dict[str, Any]:
        normalized: dict[str, Any] = dict(payload)

        for key in cls.ENVELOPE_KEYS:
            nested = normalized.get(key)
            if isinstance(nested, dict):
                merged = dict(normalized)
                merged.pop(key, None)
                merged.update(nested)
                normalized = merged
                break

        status: Any = normalized.get("status")
        if status is None:
            for alias in cls.STATUS_KEYS:
                value = normalized.get(alias)
                if isinstance(value, (str, bool)):
                    status = value
                    break

        if isinstance(status, bool):
            normalized["status"] = "approved" if status else "changes_requested"
        elif isinstance(status, str):
            key = re.sub(r"[^a-z0-9]+", "_", status.strip().lower()).strip("_")
            normalized["status"] = cls.STATUS_ALIASES.get(key, key)

        if not isinstance(normalized.get("feedback"), str):
            feedback = cls._best_effort_feedback(normalized)
            if feedback:
                normalized["feedback"] = feedback

        return normalized

    @classmethod
    def _best_effort_feedback(cls, payload: dict[str, Any]) -> str:
        for key in cls.FEEDBACK_KEYS:
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
            if isinstance(value, list) and value:
                parts = [str(item).strip() for item in value if str(item).strip()]
                if parts:
                    return "\n".join(f"- {part}" for part in parts)
            if isinstance(value, dict) and value:
                nested = cls._best_effort_feedback(value)
                if nested:
                    return nested

        ignored = {"status", "verdict", "decision", "outcome", "result"}
        strings = [
            value.strip()
            for key, value in payload.items()
            if key not in ignored and isinstance(value, str) and value.strip()
        ]
        return "\n".join(strings)

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

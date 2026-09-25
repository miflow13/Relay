import json
import re
from typing import Any


class AgentProtocolError(ValueError):
    """Raised when an agent does not return the JSON protocol RelayLab expects."""


def extract_json_object(text: str) -> dict[str, Any]:
    """Parse an agent response that should contain exactly one JSON object.

    Models occasionally wrap JSON in Markdown fences, so RelayLab tolerates that
    presentation layer while still requiring the payload itself to be valid JSON.
    """
    candidate = text.strip()

    fenced = re.fullmatch(
        r"\s*\x60\x60\x60(?:json)?\s*(\{.*\})\s*\x60\x60\x60\s*",
        candidate,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if fenced:
        candidate = fenced.group(1)

    try:
        parsed = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise AgentProtocolError(f"Agent returned invalid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise AgentProtocolError("Agent response must be a JSON object.")

    return parsed

import json
import urllib.error
import urllib.request
from typing import Any


class OllamaError(RuntimeError):
    pass


class OllamaClient:
    def __init__(self, base_url: str, timeout_seconds: int = 300) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout_seconds = timeout_seconds

    def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.2,
    ) -> str:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {"temperature": temperature},
        }

        request = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(
                request, timeout=self.timeout_seconds
            ) as response:
                body = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = ""
            try:
                raw = exc.read().decode("utf-8", errors="replace")
                if raw:
                    try:
                        error_body = json.loads(raw)
                        detail = str(error_body.get("error", raw))
                    except json.JSONDecodeError:
                        detail = raw
            except Exception:
                pass

            message = f"Ollama returned HTTP {exc.code}"
            if detail:
                message += f": {detail}"

            if exc.code == 404:
                message += (
                    f"\nModel requested: {model!r}. "
                    "Confirm it appears in 'ollama list'."
                )
            elif exc.code >= 500:
                message += (
                    "\nThe Ollama server was reached, but the model runner failed. "
                    "Try the model directly with 'ollama run' and inspect "
                    "'journalctl -u ollama -n 100 --no-pager' if Ollama runs as a service."
                )

            raise OllamaError(message) from exc
        except urllib.error.URLError as exc:
            raise OllamaError(
                "Could not connect to Ollama. Make sure the Ollama service is running "
                f"and that {self.base_url} is reachable. Underlying error: {exc}"
            ) from exc
        except json.JSONDecodeError as exc:
            raise OllamaError("Ollama returned a non-JSON response.") from exc

        if "error" in body:
            raise OllamaError(f"Ollama error: {body['error']}")

        try:
            return body["message"]["content"]
        except (KeyError, TypeError) as exc:
            raise OllamaError(f"Unexpected Ollama response: {body!r}") from exc

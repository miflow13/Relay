from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    builder_model: str = "qwen2.5-coder:3b"
    reviewer_model: str = "qwen3:4b"
    ollama_url: str = "http://localhost:11434"
    max_rounds: int = 6
    request_timeout_seconds: int = 300
    max_snapshot_bytes_per_file: int = 40_000

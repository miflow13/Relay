from __future__ import annotations

import argparse
import json
from pathlib import Path

from relaylab.config import Settings
from relaylab.orchestrator import RelayLab


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a local two-agent software development experiment."
    )
    parser.add_argument("task", help="What the agents should build.")
    parser.add_argument(
        "--name",
        required=True,
        help="Experiment name (letters, numbers, dot, underscore, dash).",
    )
    parser.add_argument(
        "--builder-model",
        default="qwen2.5-coder:7b",
        help="Ollama model used by the Builder.",
    )
    parser.add_argument(
        "--reviewer-model",
        default="qwen3:8b",
        help="Ollama model used by the Reviewer.",
    )
    parser.add_argument(
        "--max-rounds",
        type=int,
        default=6,
        help="Hard limit on Builder/Reviewer iterations.",
    )
    parser.add_argument(
        "--ollama-url",
        default="http://localhost:11434",
        help="Base URL for the local Ollama server.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if not 1 <= args.max_rounds <= 20:
        raise SystemExit("--max-rounds must be between 1 and 20.")

    settings = Settings(
        builder_model=args.builder_model,
        reviewer_model=args.reviewer_model,
        ollama_url=args.ollama_url,
        max_rounds=args.max_rounds,
    )

    lab = RelayLab(Path(__file__).resolve().parent, settings)
    result = lab.run(task=args.task, experiment_name=args.name)

    print("\n=== RelayLab result ===")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()

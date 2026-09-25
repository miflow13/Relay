# RelayLab 🧪🤖🤖

RelayLab is a local-first experiment in autonomous software development.

Two Ollama-powered agents collaborate on the same isolated workspace:

- **Builder** — implements the requested app by proposing complete file writes/deletes.
- **Reviewer** — independently inspects the resulting workspace and either approves it or sends concrete feedback.
- **Orchestrator** — applies changes, performs deterministic static checks, logs every round, and stops at a hard iteration limit.

No cloud model API is required.

## Status

**v0.1 experimental scaffold**

The first milestone is deliberately constrained. The agents can create/edit files only inside one experiment workspace. **They do not receive shell access in v0.1.** This lets us observe the Builder → Reviewer feedback loop before adding more dangerous capabilities.

## Requirements

- Python 3.11+
- [Ollama](https://ollama.com/)
- Local models:

```bash
ollama pull qwen2.5-coder:7b
ollama pull qwen3:8b
```

Verify Ollama is running:

```bash
ollama list
curl http://localhost:11434/api/tags
```

## Quick start

```bash
git clone https://github.com/miflow13/RelayLab.git
cd RelayLab

python -m venv .venv
source .venv/bin/activate

python -m unittest discover -s tests -v

python relay.py \
  "Build a tiny single-page notes app with add, complete, and delete actions." \
  --name notes-v1
```

RelayLab will create:

```text
experiments/notes-v1/workspace/   # app produced by the agents
runs/<run-id>/                    # full experiment transcript + metadata
```

## Agent loop

```text
task
  ↓
Builder
  ↓
structured file actions
  ↓
RelayLab applies changes
  ↓
static deterministic checks
  ↓
Reviewer
  ├─ changes_requested → Builder
  └─ approved → done
```

The loop stops after 6 rounds by default even if the Reviewer never approves.

## v0.1 protocol

The Builder must return JSON:

```json
{
  "summary": "What changed",
  "files": [
    {
      "path": "index.html",
      "content": "<!doctype html>..."
    }
  ],
  "deletes": []
}
```

The Reviewer must return JSON:

```json
{
  "status": "approved",
  "feedback": "Why this satisfies the task."
}
```

Ollama is requested to return JSON-formatted responses, and RelayLab validates the protocol before applying actions.

## Safety model

v0.1 intentionally does **not** give either model unrestricted computer access.

- Files are resolved against one experiment workspace.
- Absolute paths and `..` path traversal are rejected.
- Model-authored code is not executed.
- Python source is syntax-compiled without running it.
- JSON files are parsed without running generated programs.
- Git operations and pushes are unavailable to the agents.
- Every agent response, applied action, check result, and review is logged.
- Runs have a hard maximum-round limit.

This is still experimental software rather than a hardened security boundary. Keep generated work disposable until stronger process/container isolation is added.

## Default models

| Role | Model |
| --- | --- |
| Builder | `qwen2.5-coder:7b` |
| Reviewer | `qwen3:8b` |

Override either from the CLI:

```bash
python relay.py "Build a pomodoro timer" \
  --name pomodoro \
  --builder-model qwen2.5-coder:7b \
  --reviewer-model qwen3:8b
```

## What we're measuring

RelayLab is meant to become an actual experiment, not just a chatbot demo. Each run records enough information to compare:

- rounds to approval
- reviewer rejection reasons
- deterministic check failures
- model combinations
- final artifacts
- whether a two-agent loop improves over a single-agent baseline

## Repository layout

```text
RelayLab/
├── relaylab/
│   ├── agents/
│   │   ├── builder.py
│   │   └── reviewer.py
│   ├── config.py
│   ├── jsonutil.py
│   ├── ollama_client.py
│   ├── orchestrator.py
│   └── workspace.py
├── prompts/
│   ├── builder.md
│   └── reviewer.md
├── experiments/
├── runs/
├── tests/
├── relay.py
└── pyproject.toml
```

## Roadmap

- [x] Local Ollama client
- [x] Builder / Reviewer role separation
- [x] Structured action protocol
- [x] Workspace path isolation
- [x] Hard iteration limit
- [x] JSON run transcripts
- [x] Deterministic static checks
- [x] GitHub Actions unit tests
- [ ] Strong OS/container sandbox
- [ ] Controlled shell/tool calling
- [ ] Browser-based app verification
- [ ] Git checkpoints per accepted round
- [ ] Single-agent baseline mode
- [ ] Run comparison metrics
- [ ] Live web UI for watching both agents work

## License

Experimental project. Add a license before distributing or incorporating third-party code.

# RelayLab 🧪🤖🤖

RelayLab is a local-first experiment in autonomous software development.

Two Ollama-powered agents collaborate on the same isolated workspace:

- **Builder** — implements the requested app by proposing file writes and safe verification commands.
- **Reviewer** — inspects the resulting workspace and either approves it or sends concrete feedback.
- **Orchestrator** — applies changes, runs deterministic checks, logs every round, and stops at a hard iteration limit.

No cloud model API is required.

## Status

**v0.1 experimental scaffold**

The first milestone is deliberately constrained: the agents can create/edit files only inside an experiment workspace and can request only a small allowlist of verification commands. This makes the conversation observable before we give the agents broader computer access.

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

python relay.py "Build a tiny single-page notes app with add, complete, and delete actions." --name notes-v1
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
safe file actions
  ↓
deterministic checks
  ↓
Reviewer
  ├─ changes_requested → Builder
  └─ approved → done
```

The loop stops after 6 rounds by default even if the reviewer never approves.

## Safety model

v0.1 intentionally does **not** give a model unrestricted shell access.

- Files are resolved against one experiment workspace.
- Absolute paths and `..` path traversal are rejected.
- Requested commands are executed without a shell.
- Only a narrow command allowlist is accepted.
- Destructive Git operations and pushes are unavailable.
- Every agent response, applied action, command result, and review is logged.
- Runs have a hard maximum-round limit.

> **Important:** this is not a hardened OS sandbox. Generated programs may themselves contain network or filesystem code. Use RelayLab only with disposable experiment workspaces until process/container isolation is added.

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

## Roadmap

- [x] Local Ollama client
- [x] Builder / Reviewer role separation
- [x] Structured action protocol
- [x] Workspace path isolation
- [x] Hard iteration limit
- [x] JSON run transcripts
- [ ] Strong OS/container sandbox
- [ ] Rich command/tool calling
- [ ] Git checkpoints per accepted round
- [ ] Single-agent baseline mode
- [ ] Run comparison metrics
- [ ] Live web UI for watching both agents work

## License

Experimental project. Add a license before distributing or incorporating third-party code.

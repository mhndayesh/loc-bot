# Developer Guide 🛠️

This guide explains the architecture of `loc-bot` and how to extend it, deeply focusing on the Infinite Context Memory integrations.

## Architecture Overview

The system consists of three main intelligent components:

1.  **Server (`server.py`)**:
    *   A lightweight HTTP server (Python `http.server`).
    *   Serves the GUI (`gui/`) and exposes a REST API (`/api/...`).
    *   **Asynchronous Embedding Engine**: To prevent Chat Input freezing when users paste 10,000+ characters, `server.py` implements "Paste Protection". It spins off a background Thread that chunks the massive paste according to `config.json` limit (`embedding_trigger`) and pipelines them into the `VectorVault`.

2.  **Engine (`engine.py`)**:
    *   The brain of the agent, executed via `subprocess` by the server for isolation.
    *   **Semantic RAG Builder**: Before building the LLM context, `engine.pulse()` asks the memory module to extract the top `FACTS` semantically relevant to the current `goal`.
    *   **Idle Optimization**: During `/api/heartbeat` sweeps, if there is no goal, `engine.py` dynamically enforces `temporarily_disable_thinking` and injects `stop: ["."]` into the LM payload to completely annihilate deep-thinking hallucination loops when idle, optimizing VRAM/CPU.

3.  **Memory (`memory.py`)**:
    *   Houses the `VectorVault` class, a custom JSON-backed hierarchical database storing semantic embeddings (`memory_vault.json`).
    *   Leverages the LLM inference endpoints asynchronously (simulating Chain-of-Thought json classification) to tag incoming chat and observations strictly as either a `FACT` or `CHATTER`.

## File Structure

```
loc-bot/
├── engine.py           # Core logic (Pulse, Tools, RAG Assembly)
├── server.py           # Web server, Config API, Threaded Embedder
├── memory.py           # VectorVault & Semantic Meta-Classification
├── config.json         # Settings (Theme, embedding limits, routes)
├── state.json          # Current goal, status
├── SOUL.md             # Agent identity (Protected)
├── AGENT_MANUAL.md     # Agent instructions
├── skills/             # Custom tool scripts (.py)
├── gui/                # HTML/JS frontend
└── docs/               # Documentation
```

## Extending the Agent

### Adding a New Custom Skill (in `skills/`)
Create a Python script in `skills/my_skill.py`. The agent auto-detects `skills/*.py` and reads their docstrings to teach itself how to use them.
```python
"""my_skill: Demonstrates how to create a custom ability."""
import sys
args = sys.argv[1:]
print(f"Hello from skill! Args: {args}")
```
The agent can call it via `my_skill("arg1")`.
*   *Pros*: Modular, dynamic (agent can create these itself!).
*   *Cons*: Runs in subprocess, no access to `AgentEngine` instance directly.

## Safeguards 🛡️

The system includes critical runtime safeguards:
*   **Identity Lock**: `write_file` throws an error if target is `SOUL.md` or `RULES.md`.
*   **Path Traversal Prevention**: `_safe_path` ensures file operations stay within the agent root.
*   **Semantic Loop Prevention**: Advanced CoS similarities dynamically detect loop hallucination and aggressively reset the context to break recursive failure states.

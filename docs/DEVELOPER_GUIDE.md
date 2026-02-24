# Developer Guide 🛠️

This guide explains the architecture of `loc-bot` and how to extend it, deeply focusing on the Infinite Context Memory integrations.

## Architecture Overview

The system consists of three main intelligent components:

1.  **Server (`src/api/server.py`)**:
    *   A lightweight HTTP server (Python `http.server`).
    *   Serves the GUI (`frontend/`) and exposes a REST API (`/api/...`).
    *   **Asynchronous Embedding Engine**: Implements "Paste Protection" using a custom high-performance embedding wrapper for ChromaDB. Chunks massive pastes into the `HybridMemorySystem`.

2.  **Engine (`src/core/engine.py`)**:
    *   The brain of the agent, executed via `subprocess` or direct import.
    *   **Agentic Recall**: Dynamically expands queries into dense keywords, performs hybrid ChromaDB + BM25 search, and exhumes 6,000+ character continuous "Session Blocks".
    *   **Idle Optimization**: During `/api/heartbeat`, if idle, the engine enforces thought suppression to optimize local VRAM/CPU usage.

3.  **Memory (`src/core/memory.py`)**:
    *   Houses the `HybridMemorySystem`, combining `chromadb` (semantic) and `rank_bm25` (keyword).
    *   **Parallel Extraction**: Features a Map-Reduce fact extraction pipeline using `asyncio` and `aiohttp` to scan unlimited context for high-precision facts.

## File Structure

```
loc-bot/
├── main.py             # System entry point
├── config/             # Configuration files
├── data/               # Persistent data (ChromaDB, state)
├── docs/               # Documentation
├── frontend/           # HTML/JS frontend
├── logs/               # Application journals
├── scripts/            # Utility and testing scripts
├── src/
│   ├── api/            # Server and API handlers
│   ├── core/           # Brain, Engine, and Memory logic
│   └── utils/          # Shared utilities
└── skills/             # Custom tool scripts (.py)
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

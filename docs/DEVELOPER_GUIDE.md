# Developer Guide 🛠️

This guide explains the architecture of `loc-bot` and how to extend it.

## Architecture Overview

The system consists of two main components:

1.  **Server (`server.py`)**:
    *   A lightweight HTTP server (Python `http.server`).
    *   Serves the GUI (`gui/`).
    *   Exposes a REST API (`/api/...`).
    *   Manages the "Heartbeat" background thread.

2.  **Engine (`engine.py`)**:
    *   The brain of the agent.
    *   Executed via `subprocess` by the server for isolation.
    *   **Cycle**:
        1.  **Load State**: Reads `state.json` and identity files.
        2.  **Prompt**: Assembles context from `SOUL.md`, `MAP.md`, logs, etc.
        3.  **LLM Call**: Sends prompt to Ollama/LM Studio.
        4.  **Parse**: Extracts `[THINK]` and `[TOOL]` blocks.
        5.  **Execute**: Runs the tool (native or custom).
        6.  **Save**: Persists state and journal.

## File Structure

```
loc-bot/
├── engine.py           # Core logic (Pulse, Tools)
├── server.py           # Web server & API
├── config.json         # Settings
├── state.json          # Current goal, status
├── SOUL.md             # Agent identity (Protected)
├── AGENT_MANUAL.md     # Agent instructions
├── skills/             # Custom tool scripts (.py)
├── memory/             # Chat logs and pulse history
├── gui/                # HTML/JS frontend
└── docs/               # Documentation
```

## Extending the Agent

### Adding a New Tool (Skill)
You can add tools effectively in two ways:

**1. Native Tool (in `engine.py`)**:
Add a new `if name == "my_tool":` block in `AgentEngine.run_tool`.
*   *Pros*: Fast, access to agent internals (`self`).
*   *Cons*: Requires restarting the agent.

**2. Custom Skill (in `skills/`)**:
Create a Python script in `skills/my_skill.py`.
```python
# skills/my_skill.py
import sys
args = sys.argv[1:]
print(f"Hello from skill! Args: {args}")
```
The agent can call it via `my_skill("arg1")`.
*   *Pros*: Modular, dynamic (agent can create these itself!).
*   *Cons*: Runs in subprocess, no access to `AgentEngine` instance.

## safeguards 🛡️

The `engine.py` includes critical safeguards:
*   **Identity Lock**: `write_file` throws an error if target is `SOUL.md` or `RULES.md`.
*   **Path Traversal Prevention**: `_safe_path` ensures file operations stay within the agent root.
*   **Token Limits**: Journal/Scratchpad are truncated to prevent prompt explosion.

## Contributing

1.  Fork the repo.
2.  Create a feature branch.
3.  Submit a Pull Request.

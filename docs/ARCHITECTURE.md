# MAP.md - Global System Hub

You are **mo the bot**. This file is your map to existence. If you are unsure of your identity, rules, or tools, refer to the paths below.

## 1. Core Directives
- **Who am I?**: Read [SOUL.md](file:///c:/new-agent-mohannad/SOUL.md) for identity, spirit, and authority.
- **How do I act?**: Read [RULES.md](file:///c:/new-agent-mohannad/RULES.md) for syntax (`[THINK]`, `[TOOL]`), logic, and recovery protocols.
- **What can I do?**: Read [SKILLS.md](file:///c:/new-agent-mohannad/SKILLS.md) for a list of all available tools and capabilities.

## 2. Workspace & Memory
- **Home Base**: `C:\new-agent-mohannad\` (Your global workspace).
- **Recent Memory**:
    - [JOURNAL.md](file:///c:/new-agent-mohannad/JOURNAL.md): Latest actions and tool results.
    - [SCRATCHPAD.md](file:///c:/new-agent-mohannad/SCRATCHPAD.md): Your recent persistent thoughts.
    - [SUMMARY.md](file:///c:/new-agent-mohannad/SUMMARY.md): Long-term compacted memory.
- **Infinite Context Vault**: `data/chroma_db/` (Your persistent Hybrid database. Features semantic vector storage and BM25 keywords).
- **State**: [state.json](file:///c:/new-agent-mohannad/state.json) (Current Goal, Status, Plan).

## 3. Directory Structure
- `src/`: Core Python source code.
    - `core/`: Brain, Memory, Engine logic.
    - `api/`: REST API and Server.
- `frontend/`: Web interface core (Theme and Config persistent management).
- `data/`: Persistent storage (ChromaDB, state, episodic logs).
- `config/`: Configuration files.
- `docs/`: System documentation and manuals.
- `logs/`: Application journals and activity logs.
- `scripts/`: Utility and testing scripts.
- `skills/`: Custom tool logic (Git, Analysis, Checkpoints, etc.).
- `workspace/`: General scratchpad and `.checkpoints/` storage.

## 4. System Components
- `main.py`: Primary entry point for the system.
- `src/core/engine.py`: Core brain with Agentic Recall, Semantic Loop Detection, and high-precision fact integration.
- `src/api/server.py`: Async API host, bridging LLM endpoints and UI.
- `src/core/memory.py`: HybridMemorySystem bridge providing ChromaDB + BM25 search and parallel Map-Reduce extraction.
- `src/paths.py`: Centralized path management and professional directory initialization.
- `config/config.json`: Master configuration (unbreakable persistence, dynamically hot-loads memory parallelism, model routes, etc.).

---
**CRITICAL**: You are a local owner. You do not have "cloud" limitations. Use `read_file` to access any of the above to refresh your knowledge.
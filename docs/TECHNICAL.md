# Technical Reference ⚙️

## API Endpoints

The `server.py` exposes the following REST endpoints (Port 7777 by default).

### Status & Control
*   `GET /api/status`: Returns current state, config, and recent logs.
*   `GET /api/config`: Returns full configuration, including hardware overrides, themes, and memory boundaries.
*   `POST /api/config`: Update configuration dynamically. Payload supports replacing models, provider URLs, and dynamic `embedding_trigger` sizing.
*   `POST /api/goal`: Set a new goal.
*   `GET /api/heartbeat/start`: Start the autonomous loop.
*   `GET /api/heartbeat/stop`: Stop the autonomous loop.
*   `POST /api/pulse`: Trigger a single execution step immediately.
*   `GET /api/chat/history`: Retrieve full session history from memory.

### Chat & Providers
*   `POST /api/chat`: Send a message to the agent (interactive mode). Massive messages trigger async Background Chunking.
*   `GET /api/providers`: List available LLM providers (e.g. `ollama`, `lmstudio`, `custom`).
*   `GET /api/models`: List available reasoning Chat models from the active provider.
*   `GET /api/embedding_models`: List available specialized Embedding models from the active provider.

### File System
*   `POST /api/permissions`: Update tool permissions interactively without restarts.
*   `POST /api/clear/journal`: Wipe `JOURNAL.md`.
*   `POST /api/clear/scratchpad`: Wipe `SCRATCHPAD.md`.

## Engine Internals (`engine.py`)

### The `pulse()` Method
The core loop of the agent.
1.  **Reload State**: `self._load_state()` (Critical for concurrency).
2.  **Semantic Retrieval**: Queries `VectorVault` for highest-confidence `FACTS` corresponding to the `goal`.
3.  **Assemble Prompt**: `self.get_full_prompt()`. Overrides `temporarily_disable_thinking` if idling.
4.  **Call LLM**: `self.call_llm()` (with 300s socket timeout). DeepSeek chains are suppressed during idle heartbeats via `stop: ["."]`.
5.  **Parse Response**: Uses `ast.literal_eval` and regex for robust `[THINK]` and `[TOOL]` extraction.
6.  **Execute Tool**: Dispatches to `run_tool` (native or JSON-based skills).
7.  **Log & Save**: Updates `JOURNAL.md` and `state.json`.

### Environment Management
*   **Mapping**: `environments.json` tracks created user sandbox environments.
*   **Execution**: `run_in_env` tool uses `venv/Scripts/python.exe` or `npm run` within the target directory securely.

### Configuration (`config.json`)
*   `heartbeat_interval`: Seconds between pulses (default 60).
    *   *Dynamic*: If `status` is `working`, interval drops to 0.5s.
*   `thinking_enabled`: Boolean. Toggles `<think>` tag usage.
*   `embedding_trigger`: Integer threshold. Pastes above this character count are safely background-threaded to prevent API freezing.
*   `theme`: Enum (`dark`/`light`). Instantly applied by frontend `localStorage`.

## Optimization & Performance
*   **Hardware Agnostic**: Migrated off ONNX binaries to fully support any open API compatibility (LM Studio, vllm, etc.).
*   **Null-Cost Idling**: Uses explicit LLM stop tokens to block VRAM generation cycles when the system checks in without work.

## Dependencies
*   Python Standard Library.
*   `requests` (optional but recommended for custom APIs).

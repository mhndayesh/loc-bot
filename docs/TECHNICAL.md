# Technical Reference ⚙️

## API Endpoints

The `server.py` exposes the following REST endpoints (Port 7777 by default).

### Status & Control
*   `GET /api/status`: Returns current state, config, and recent logs.
*   `GET /api/config`: Returns full configuration.
*   `POST /api/config`: Update configuration.
*   `POST /api/goal`: Set a new goal.
*   `GET /api/heartbeat/start`: Start the autonomous loop.
*   `GET /api/heartbeat/stop`: Stop the autonomous loop.
*   `POST /api/pulse`: Trigger a single execution step immediately.
*   `GET /api/chat/history`: Retrieve full session history.


### Chat & Providers
*   `POST /api/chat`: Send a message to the agent (interactive mode).
*   `GET /api/providers`: List available LLM providers.
*   `GET /api/models`: List models from the active provider.

### File System
*   `POST /api/permissions`: Update tool permissions.
*   `POST /api/clear/journal`: Wipe `JOURNAL.md`.

## Engine Internals (`engine.py`)

### The `pulse()` Method
The core loop of the agent.
1.  **Reload State**: `self._load_state()` (Critical for concurrency).
2.  **Assemble Prompt**: `self.get_full_prompt()`.
3.  **Call LLM**: `self.call_llm()` (with 300s socket timeout).
4.  **Parse Response**: Uses `ast.literal_eval` and regex for robust `[THINK]` and `[TOOL]` extraction.
5.  **Execute Tool**: Dispatches to `run_tool` (native or JSON-based skills).
6.  **Log & Save**: Updates `JOURNAL.md` and `state.json`.
7.  **Semantic Similarity**: Optional cosine-similarity check on errors to prevent loops.


### Environment Management
*   **Mapping**: `environments.json` tracks created environments.
*   **Execution**: `run_in_env` tool uses `venv/Scripts/python.exe` or `npm run` within the target directory.

### Configuration (`config.json`)
*   `heartbeat_interval`: Seconds between pulses (default 60).
    *   *Dynamic*: If `status` is `working`, interval drops to 0.5s.
*   `thinking_enabled`: Boolean. Toggles `<think>` tag usage.
*   `permissions`: Dict of `tool_name: boolean`.

## Optimization & Performance
*   **Blackwell Acceleration**: Embeddings run via `onnxruntime-directml` in `memory.py`.
*   **Context Scaling**: Memory retrieval limits are relative to defined `num_ctx`.
*   **Socket Timeouts**: Increased to 300s to support heavy reasoning tokens.

## Dependencies
*   Python Standard Library.
*   `requests` (optional).
*   `onnxruntime-directml` (for hardware acceleration).


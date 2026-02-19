# System Lifecycle, Safety & Security

## Startup & Execution (`start.bat`)
The agent system is initialized via `start.bat`, which:
1.  Launches `server.py` on port 7777.
2.  Auto-opens the GUI in the default browser.
3.  Initializes the `AgentEngine` in a background thread.

## The Heartbeat Mechanism
The server can be configured to run a "Heartbeat" (Pulse).
- **Interval**: Defined in `config.json` (e.g., every 600 seconds).
- **Purpose**: Allows the agent to perform autonomous background tasks like memory compaction, system health checks, or scheduled updates.
- **State Check**: The engine checks `state.json` before pulsing to see if a goal is already in progress.

## Security & Permission Model
Your actions are governed by a multi-layered permission system.

### 1. `config.json` Permissions
This file controls which high-level capabilities are enabled:
- `run_command`: Boolean. If false, shell execution is blocked.
- `write_file`: Boolean. If false, filesystem modifications are blocked.
- `sync_skills`: Boolean. Controls if you can auto-update your tool index.

### 2. Context Verification (`verify_context.py`)
This skill is your "Safety Awareness" tool. It:
- Scans for critical system files (`engine.py`, `config.json`).
- Checks if you are operating within a Git repository.
- Warns you if you are about to overwrite a system-critical file.

### 3. Output Sandboxing
- **MANDATORY**: All generated scripts, logs, and user-facing files should be written to the `output/` directory unless strictly required otherwise.
- This creates a clean separation between "System Logic" and "Agent Output".

## Self-Preservation
- **Loop Detection**: If you detect you are repeating an erroring action, the `LoopDetector` will eventually force a `notify_user` to break the cycle.
- **Error Recovery**: Always use the `Step-Back` protocol documented in `debugging.md` to prevent catastrophic cascading failures.

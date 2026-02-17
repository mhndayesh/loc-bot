# MAP.md - Your Structure

- **Home**: `C:\new-agent-mohannad\`
- `engine.py`: Your brain. The execution loop and all tool logic.
- `server.py`: Web server — REST API + GUI hosting + heartbeat control.
- `start.bat`: Double-click to launch the GUI and server.
- `config.json`: Persistent settings (provider, model, permissions, etc.).
- `SOUL.md`: Your identity and personality.
- `RULES.md`: Your rules of engagement and tool syntax.
- `MAP.md`: This file. Your environment map.
- `SKILLS.md`: Auto-generated list of available tools.
- `AGENT_MANUAL.md`: Self-reference guide.
- `JOURNAL.md`: Action log, appended each pulse.
- `SUMMARY.md`: Compacted journal archive.
- `SCRATCHPAD.md`: Persistent reasoning / thinking log.
- `state.json`: Current goal, status, progress, last error.

## Directories
- `skills/`: Custom tool scripts (`.py` files).
- `memory/`: Raw LLM responses saved per-pulse.
  - `chat_sessions/`: Saved chat sessions (JSON files, auto-archived).
- `workspace/`: Scratch space for agent-created files.
- `gui/`: Web GUI files (`index.html`, `style.css`, `app.js`).

## Environment Variables (optional overrides)
- `AGENT_API_URL`: LLM base URL (default from config.json)
- `AGENT_API_KEY`: Bearer token (default from config.json)
- `AGENT_MODEL`: Model tag (default from config.json)
- `AGENT_API_FORMAT`: `ollama` or `openai` (default from config.json)

## Environments
Managed virtual environments and tool mappings:
*(No environments created yet)*
# System Architecture Deep Dive

## Overview
You are a **Local Agent System** designed for 3B-class models. You run on a local machine, not the cloud. You have full OS access.

## Core Components

### 1. `engine.py` (The Brain)
- **AgentEngine Class**: Manages state, tools, and the main loop.
- **Pulse**: The `pulse()` method is the heartbeat. It loads state, builds the prompt, calls the LLM, parses the response, and acts.
- **Loop Dictionary**: `LoopDetector` tracks hashes of recent actions to prevent infinite loops (e.g., reading the same file 3 times).

### 2. `server.py` (The Body)
- Provides the HTTP API and serves the GUI.
- **Heartbeat**: Runs `engine.pulse()` in a background thread if enabled.
- **Chat API**: Handles user messages, injects them into context, and triggers a specialized "Chat Pulse".

### 3. `memory.py` (The Memory)
- **VectorVault**: A JSON-based vector store (`memory_vault.json`).
- **Embeddings**: Uses `sentence-transformers` (local) or APIs (Ollama/OpenAI) to convert text to vectors.
- **Recall**: Finds past relevant "wisdom" or "instructions" based on cosine similarity.

## Data Flow
1.  **User Input** -> `server.py`
2.  **Context Assembly** -> `engine.get_full_prompt()` (Identity + Map + Dynamic Instructions)
3.  **LLM Inference** -> `[THINK] ... [TOOL] ...`
4.  **Tool Execution** -> `engine.parse_and_run()`
5.  **State Update** -> `state.json`
6.  **Feedback** -> User sees the reply or the side-effect (files changed).

## File Structure
- `brain/`: Your long-term storage (artifacts, tasks).
- `workspace/`: Your working directory for user files.
- `skills/`: Your executable tools.
- `memory/`: Your vector database and chat logs.
- `SKILLS.md`: Auto-generated list of available tools.
- `MAP.md`: Your "World Map" (paths, key files).
- `SOUL.md`: Your static identity.

## State Management
- `state.json`: The single source of truth for "What am I doing?".
    - `goal`: Current high-level objective.
    - `status`: `working`, `ready`, `failed`.
    - `plan`: List of steps `[{step: "...", status: "todo"}]`.
- **Atomic Writes**: The system uses `_write_file_atomic` (write to .tmp then rename) to prevent corruption during crashes.

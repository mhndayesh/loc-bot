# User Guide 📘

Welcome to `loc-bot`! This guide helps you interact with and control your AI agent entirely locally, featuring an Infinite Context Memory architecture.

## The GUI

The interface is divided into tabs:

### 1. 📊 Dashboard
*   **Goal**: The current high-level objective the agent is working on.
*   **Status**:
    *   `ready`: Waiting for instructions.
    *   `working`: Actively executing a task.
    *   `recovering`: Fixing a previous error.
    *   `done`: Task completed.
*   **Controls**:
    *   **Theme Toggle**: Click the ☀️ / 🌙 button in the top right header to instantly swap between the Light and Dark mode UI elements.
    *   **Start/Stop Loop**: Toggle the autonomous heartbeat (default 60s, or 1s when working).
    *   **Pulse Now**: Force the agent to take one step immediately.

### 2. 💬 Chat
*   Talk to the agent directly.
*   **Paste Protection**: You can paste thousands of lines of code into the chat. The backend uses the "Embedding Server" to seamlessly chunk, embed, and archive large pastes in the background without freezing the UI or blowing out the context window.
*   **Reasoning**: Toggle "Show Thinking" to see the agent's internal monologue (useful for DeepSeek `r1` models).

### 3. 📝 Activity
*   **Journal**: A log of the agent's recent actions and results.
*   **Scratchpad**: The agent's short-term memory and plans.

### 4. ⚙️ Settings
*   **Provider**: Choose between Ollama (default), LM Studio, Copilot, or Custom API providers.
*   **URL**: Input specific host/port addresses (e.g., `http://localhost:1234/v1` for LM Studio).
*   **Chat Model**: Select your active reasoning model (e.g., `deepseek-r1-0528-qwen3-8b`).
*   **Embedding Model**: Select the dedicated model used to encode your long-term memories (e.g., `nomic-embed-text`).
*   **Embedding Trigger (Chunk Cap)**: Controls Paste Protection. If you paste a message longer than this setting (default 4000 chars), it will automatically be split into semantic chunks and embedded asynchronously in the background. Maximize this if your embedding model handles huge context sizes.
*   **Auto-Save**: Settings save automatically when changed.

## Guiding the Agent

### Setting a Goal
1.  Go to the Dashboard.
2.  Type your goal in the input box (e.g., "Analyze the `src` folder and map the architecture").
3.  Click **Update Goal**.
4.  Ensure the "Heartbeat" is **ON**.

### Monitoring Progress
Watch the **Activity** tab. You'll see the agent:
1.  **[THINK]**: Planning its next move.
2.  **[TOOL]**: Executing a command (e.g., `list_dir`, `read_file`).
3.  **Reflecting**: Saving the result to its memory.

## Capabilities

### Infinite Context (Agentic Session Memory)
You do not need to worry about the agent "forgetting" what happened yesterday. The agent uses an **Extremely Long Context Window Technique** optimized for consumer PCs (built on [mhndayesh/infinite-context-rag](https://github.com/mhndayesh/infinite-context-rag)):
*   **Session Tagging**: Every conversation and massive paste is tracked as a continuous block of time in `memory_vault.json`.
*   **Agentic Search & Routing**: The local AI acts as its own search engine. If you ask a question, it intelligently rewrites your query into dense keywords, searches the vault, and then automatically votes on the best mathematical match.
*   **Context Exhumation**: Instead of giving the AI a fragmented sentence, it pulls the entire 6k+ character historical conversation surrounding that exact memory, granting true continuous context.

### Environment Management 🌍
The agent can create isolated playgrounds for code:
*   "Create a python environment named `data_analysis`."
*   "Install `pandas` in `data_analysis`."
*   "Run this script in `data_analysis`."

### Self-Correction
If the agent encounters an error (e.g., file not found, syntax error), it enters `recovering` mode. The Semantic Loop detection prevents it from making the same exact semantic mistake three times.

## Troubleshooting

*   **Agent is stuck?** Click **Stop**, then **Pulse Now** to nudge it.
*   **"WinError 10061"?** Ensure your LLM provider (Ollama/LM Studio) is running.
*   **Settings not saving?** Refresh the page (Ctrl+F5).

# User Guide 📘

Welcome to `loc-bot`! This guide helps you interact with and control your AI agent.

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
    *   **Start/Stop Loop**: Toggle the autonomous heartbeat (default 60s, or 1s when working).
    *   **Pulse Now**: Force the agent to take one step immediately.

### 2. 💬 Chat
*   Talk to the agent directly.
*   **Attachments**: Upload files (images, code) for the agent to analyze.
*   **Reasoning**: Toggle "Show Thinking" to see the agent's internal monologue.

### 3. 📝 Activity
*   **Journal**: A log of the agent's recent actions and results.
*   **Scratchpad**: The agent's short-term memory and plans.

### 4. ⚙️ Settings
*   **Provider**: Choose between Ollama (default) or LM Studio.
*   **Model**: Select your local LLM model (e.g., `llama3.2`, `deepseek-r1`).
*   **Context Window**: Adjust token limits (up to 1M tokens supported).
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

### File Operations
The agent can read, write, and edit files in its workspace.
*   *Note*: It cannot overwrite `SOUL.md` or `RULES.md` (Self-Protection).

### Environment Management 🌍
The agent can create isolated playgrounds for code:
*   "Create a python environment named `data_analysis`."
*   "Install `pandas` in `data_analysis`."
*   "Run this script in `data_analysis`."

### Self-Correction
If the agent encounters an error (e.g., file not found, syntax error), it enters `recovering` mode. It will analyze the error and try a different approach automatically.

## Troubleshooting

*   **Agent is stuck?** Click **Stop**, then **Pulse Now** to nudge it.
*   **"WinError 10061"?** Ensure your LLM provider (Ollama/LM Studio) is running.
*   **Settings not saving?** Refresh the page (Ctrl+F5).

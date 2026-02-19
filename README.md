# loc-bot 🤖
**A Self-Evolving, Local-First AI Agent System**

`loc-bot` is a powerful, autonomous AI agent designed to run locally on your machine. It can execute complex tasks, manage its own environment, and evolve its capabilities over time.

## 🚀 Quick Start

1.  **Prerequisites**:
    *   Python 3.10+
    *   [Ollama](https://ollama.com/) or [LM Studio](https://lmstudio.ai/) running locally.

2.  **Installation**:
    ```bash
    git clone https://github.com/mhndayesh/loc-bot.git
    cd loc-bot
    pip install -r requirements.txt  # (if applicable, or just standard lib)
    ```

3.  **Run**:
    Double-click `start.bat` or run:
    ```bash
    start.bat
    ```
    The GUI will open at `http://localhost:7777`.

## ✨ Key Features

*   **Short-Term Context Optimization**: Uses a high-efficiency **8,000-character rolling window** to keep the agent fast and lean (token savings of up to 75%).
*   **Episodic Memory**: A local vector database that allows the agent to learn from past experiences and recall successful solutions JIT (Just-In-Time), ensuring no context is lost even with a smaller rolling window.
*   **Dreaming (Self-Optimization)**: Periodically summarizes recent logs and extracts high-level "Wisdom" to improve future performance.
*   **Vivid Session Management**: A high-visibility interface for managing multiple chat sessions, including **Bulk History Deletion** and per-card deletion options.
*   **Workspace Organization**: Strict enforcement of an `output/` directory for all agent-generated content to maintain a clean root.
*   **Tool Use**: Can read/write files, run shell commands, and manage system processes.
*   **High-Visibility GUI**: Bold, high-contrast action buttons (CLEAR HISTORY, Dream Now, STOP) designed for maximum clarity and safety.
*   **Dynamic Settings**: Real-time adjustment of LLM parameters (Context, Tokens, Heartbeat) via the GUI.

## 📚 Documentation

*   [**User Guide**](docs/USER_GUIDE.md): How to use the GUI, configure settings, and guide the agent.
*   [**Developer Guide**](docs/DEVELOPER_GUIDE.md): Architecture, codebase overview, and how to extend the agent.
*   [**Technical Reference**](docs/TECHNICAL.md): API endpoints and engine internals.

## 🛡️ Safety & Security

*   **Local Execution**: All LLM inference happens locally (no data sent to cloud).
*   **Sandboxed Envs**: Use the Environment Manager to run untrusted code in isolated folders.
*   **Identity Lock**: The agent cannot overwrite its core `SOUL.md` or `RULES.md` files.

## License

MIT License.

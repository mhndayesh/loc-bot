# loc-bot 🤖
**A Self-Evolving, Infinite Context AI Agent System**

`loc-bot` is a powerful, autonomous AI agent designed to run strictly locally on your machine. It executes complex tasks, manages its own environment, and leverages a dual-model RAG architecture to achieve infinite short-term memory scaling without blowing out VRAM context limits.

## 🚀 Quick Start

1.  **Prerequisites**:
    *   Python 3.10+
    *   [Ollama](https://ollama.com/) or [LM Studio](https://lmstudio.ai/) running locally.
    *   At least one Chat Model (e.g., `deepseek-r1`) and one Text Embedding model (e.g., `nomic-embed-text`) loaded in your provider.

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

*   **Infinite Context Architecture (RAG)**: The agent dynamically chunks, embeds, and stores every chat message, code paste, and thought process in a persistent lightweight `VectorVault`. It dynamically injects exactly what it needs into the context window, effectively providing infinite memory on small local models.
*   **Semantic Meta-Tagging**: A specialized background engine automatically intercepts raw data and tags it via CoT parsing as a `FACT` or `CHATTER`. The engine explicitly searches for `FACTS` when planning tasks, dramatically increasing retrieval accuracy.
*   **Zero-Overhead Idling**: DeepSeek reasoning (`<think>`) loops are forcefully cut by API stop-tokens during agent heartbeats to prevent massive compute waste when idle.
*   **Autonomous Resilience**: Advanced **Semantic Loop Detection** prevents repetitive error cycles by analyzing the semantic similarity of execution failures.
*   **Task Checkpointing**: Automatically save and restore complex agent states during multi-step missions to `workspace/.checkpoints/`.
*   **Developer Toolkit**: Native skills for **Git Integration** (`git_commit`), **Static Code Analysis** (`flake8`), and **Process Management** (PID tracking/kill).
*   **High-Visibility GUI**: Modern Light & Dark mode persistent web client with granular provider management (Host/Port configs per LLM) and dynamic Paste Protection configurations.

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

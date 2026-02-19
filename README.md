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

*   **Blackwell-Ready Embeddings**: Optimized for high-fidelity local RAG using **ONNX DirectML** (RTX 5070 optimized) for zero-latency retrieval.
*   **Autonomous Resilience**: Advanced **Semantic Loop Detection** prevents repetitive error cycles by analyzing the semantic similarity of execution failures.
*   **Task Checkpointing**: Automatically save and restore complex agent states during multi-step missions to `workspace/.checkpoints/`.
*   **Developer Toolkit**: Native skills for **Git Integration** (`git_commit`), **Static Code Analysis** (`flake8`), and **Process Management** (PID tracking/kill).
*   **Intelligent Context Sizing**: Dynamically balances JIT memory retrieval against the model's native context window (`num_ctx`) to prevent prompt dilution.
*   **Dreaming (Self-Optimization)**: Periodically summarizes `JOURNAL.md` into `SUMMARY.md` while refining pulse logic.
*   **High-Visibility GUI**: Persistent controls for "Stop", "Pulse", and "Dream Now" with real-time status and journal tracking.


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

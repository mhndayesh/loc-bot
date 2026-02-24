# loc-bot 🤖
**A Self-Evolving, Infinite Context AI Agent System**

`loc-bot` is a powerful, autonomous AI agent designed to run strictly locally on your machine. It executes complex tasks, manages its own environment, and leverages a breakthrough **Hybrid Memory Architecture** (ChromaDB + BM25) to achieve **Infinite Context Scaling** without blowing out the VRAM limits of consumer-grade graphics cards. 

Built to push the limits of cost and hardware optimization, it replaces massive, VRAM-heavy context windows with a lightning-fast database recall system and **Parallel Map-Reduce Fact Extraction**. This approach grants the AI limitless long-term memory while keeping token usage near zero and making it incredibly cheap to run.

> **Built On Groundbreaking Tech**: The extremely long context window technique utilized by this agent is inspired by and built upon [**mhndayesh/infinite-context-rag**](https://github.com/mhndayesh/infinite-context-rag). 

### 🤯 Extremely Long Context for Consumer PCs
Running models locally on consumer hardware usually means sacrificing context size (e.g., capping at 4k or 8k tokens) to prevent Out-Of-Memory (OOM) GPU crashes. `loc-bot` bypasses this hardware limitation using **Agentic Session Memory**:
- **High-Precision Hybrid Search**: Combines semantic vector search (ChromaDB) with precise keyword matching (BM25) for 100% recall accuracy.
- **Parallel Fact Extraction**: Automatically splits massive 10,000+ line documents into chunks and scans them in parallel using an async worker pipeline to extract direct facts.
- **Continuous Session Tracking**: Your long debugging sessions are tracked as continuous blocks. When the agent needs to recall a fact from 50 messages ago, it exhumes a massive 6,000+ character continuous window centered exactly around the relevant thought. 
## 🚀 Quick Start

1.  **Prerequisites**:
    *   Python 3.10+
    *   [Ollama](https://ollama.com/) or [LM Studio](https://lmstudio.ai/) running locally.
    *   At least one Chat Model (e.g., `deepseek-r1`) and one Text Embedding model (e.g., `nomic-embed-text`) loaded in your provider.

2.  **Installation**:
    ```bash
    git clone https://github.com/mhndayesh/loc-bot.git
    cd loc-bot
    pip install -r requirements.txt
    ```

3.  **Run**:
    Double-click `start.bat` or run `python main.py`. The GUI will open at `http://localhost:7777`.

## ✨ Key Features

*   **Dual-Layer Memory Architecture**: Relies on **Session Memory** to track immediate context chronologically and a background **Dreaming Loop** to consolidate generalized wisdom and permanent rules over time.
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

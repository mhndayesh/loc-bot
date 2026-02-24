# Infinite Context Memory 🧠

The `loc-bot` memory system is designed to provide high-precision retrieval over massive datasets on local hardware.

## Architecture: Hybrid Retrieval

The system uses a **Hybrid Search** approach, combining two different mathematical techniques to ensure no fact is missed:

1.  **Semantic Vector Search (ChromaDB)**: Handles "vague" or "conceptual" queries. It understands that "how do I fix the bug" is similar to "troubleshoot the error".
2.  **Keyword Search (BM25)**: Handles "precise" identifiers like function names, error codes, or unique terms (e.g., `FLUFFY_PENGUIN_99`).

These results are merged using **Reciprocal Rank Fusion (RRF)** to provide the ultimate top-N context.

## Map-Reduce Fact Extraction

When retrieved context is too large for the LLM's active window (e.g., trying to read 50,000 characters), the system switches to **Parallel Extraction**:

- **Map**: The context is split into optimized chunks and sent to parallel workers.
- **Async Workers**: Using `aiohttp` and `asyncio`, multiple requests hit the local LLM simultaneously, each scanning their chunk for the specific answer.
- **Reduce**: Findings are merged into a concise list of high-precision `[FACT]` blocks.

## Configuration

You can tune the system in `config/config.json`:

- `memory_parallel_extraction`: Enable/Disable the Map-Reduce pipeline.
- `memory_max_workers`: Number of simultaneous extraction workers (Default: 4).
- `memory_context_window`: The safety threshold before triggering parallel extraction (Default: 8192).

## Storage

All memory is stored in `data/chroma_db/`. This is a persistent database that survives system restarts.

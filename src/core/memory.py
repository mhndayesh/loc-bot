import os
import json
import time
import logging
import asyncio
import re
import threading
import uuid
from typing import List, Optional
import numpy as np
import requests
import chromadb
from chromadb.utils import embedding_functions
from rank_bm25 import BM25Okapi
import aiohttp
from openai import AsyncOpenAI

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("memory")

from src.paths import (
    CONFIG_FILE, MEMORY_STORAGE_FILE, INSTRUCTIONS_FILE, 
    CHROMA_DB_PATH, MEMORY_DIR
)
from src.core.concurrency import LLM_LOCK

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

# ═══════════════════════════════════════════════════════════════
#  Hybrid Memory System (Vector + BM25 + Parallel Extraction)
# ═══════════════════════════════════════════════════════════════

class HybridMemorySystem:
    def __init__(self, config):
        self.config = config
        self.chroma_path = CHROMA_DB_PATH
        self.client = chromadb.PersistentClient(path=self.chroma_path)
        
        # Determine embedding model from config
        self.provider = config.get("provider", "ollama")
        p_cfg = config.get("providers", {}).get(self.provider, {})
        self.base_url = p_cfg.get("base_url", "http://localhost:11434")
        self.api_key = p_cfg.get("api_key", "ollama")
        self.embed_model = config.get("embedding_model", "text-embedding-nomic-embed-text-v1.5@f32")
        
        # Custom embedding function to avoid CHROMA_OPENAI_API_KEY requirement
        class CustomEmbeddingFunction(embedding_functions.EmbeddingFunction):
            def __init__(self, base_url, api_key, model_name):
                self.base_url = base_url
                self.api_key = api_key
                self.model_name = model_name

            def __call__(self, input: List[str]) -> List[List[float]]:
                # Fallback to simple requests if Chroma wrapper fails due to env vars
                endpoint = f"{self.base_url.rstrip('/')}/embeddings"
                try:
                    logger.info(f"Custom embedding request: {len(input)} strings to {endpoint}")
                    resp = requests.post(endpoint, headers={"Authorization": f"Bearer {self.api_key}"}, json={
                        "model": self.model_name,
                        "input": input
                    }, timeout=60)
                    
                    if resp.status_code != 200:
                        logger.error(f"Embedding API error {resp.status_code}: {resp.text}")
                        return []
                        
                    data = resp.json().get("data", [])
                    embeddings = [d["embedding"] for d in data]
                    logger.info(f"Successfully retrieved {len(embeddings)} embeddings.")
                    return embeddings
                except Exception as e:
                    logger.error(f"Custom embedding connection failed: {e}")
                    return []

        self.emb_fn = CustomEmbeddingFunction(
            api_key=self.api_key,
            base_url=self.base_url,
            model_name=self.embed_model
        )
        
        self.collection = self.client.get_or_create_collection(
            name="agent_memory", 
            embedding_function=self.emb_fn
        )
        self.instruction_collection = self.client.get_or_create_collection(
            name="instructions", 
            embedding_function=self.emb_fn
        )

        # BM25 Globals
        self.bm25 = None
        self.corpus_docs = []
        self.corpus_ids = []
        self.bm25_last_sync = 0
        
        # Async settings
        self.max_workers = config.get("memory_max_workers", 4)
        self.context_window = config.get("memory_context_window", 8192)
        self.overhead = 1500
        
        # Async Client
        self.async_openai = AsyncOpenAI(
            base_url=self.base_url if "/v1" in self.base_url else f"{self.base_url.rstrip('/')}/v1",
            api_key=self.api_key
        )

    def _sync_bm25(self, force=False):
        """Refreshes the global BM25 index from ChromaDB."""
        count = self.collection.count()
        if count == 0: return

        if not force and count == len(self.corpus_docs) and (time.time() - self.bm25_last_sync) < 60:
            return
            
        try:
            all_data = self.collection.get(include=['documents'])
            self.corpus_docs = all_data['documents']
            self.corpus_ids = all_data['ids']
            tokenized_docs = [doc.lower().split() for doc in self.corpus_docs]
            self.bm25 = BM25Okapi(tokenized_docs)
            self.bm25_last_sync = time.time()
            logger.info(f"BM25 Sync: Re-indexed {count} chunks.")
        except Exception as e:
            logger.error(f"BM25 Sync Error: {e}")

    def add(self, text: str, metadata: dict = None, collection_name: str = "agent_memory"):
        """Ingest text into ChromaDB."""
        target_collection = self.instruction_collection if collection_name == "instructions" else self.collection
        
        # Basic chunking if too large
        chunk_size = 2000
        chunks = [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]
        
        ids = [f"mem_{uuid.uuid4().hex}" for _ in chunks]
        metas = [metadata or {} for _ in chunks]
        
        target_collection.add(
            documents=chunks,
            metadatas=metas,
            ids=ids
        )
        logger.info(f"Memorized {len(chunks)} chunks in {collection_name}.")
        return ids[0]

    async def query(self, query_text: str, n_results: int = 5):
        """Hybrid Search: Vector + BM25."""
        self._sync_bm25()
        
        # 1. Vector Search
        vector_res = self.collection.query(
            query_texts=[query_text], 
            n_results=10
        )
        v_ids = vector_res['ids'][0] if vector_res['ids'] else []
        
        # 2. BM25 Search
        b_ids = []
        if self.bm25:
            query_tokens = query_text.lower().split()
            scores = self.bm25.get_scores(query_tokens)
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:10]
            b_ids = [self.corpus_ids[i] for i in top_indices if scores[i] > 0]

        # 3. RRF Merge (Reciprocal Rank Fusion)
        rrf_scores = {}
        for rank, cid in enumerate(v_ids): rrf_scores[cid] = rrf_scores.get(cid, 0) + 1/(60 + rank + 1)
        for rank, cid in enumerate(b_ids): rrf_scores[cid] = rrf_scores.get(cid, 0) + 1/(60 + rank + 1)
        
        sorted_hits = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:n_results]
        
        # Reconstruct documents
        docs = []
        all_ids = self.collection.get(ids=[h[0] for h in sorted_hits], include=['documents'])
        id_to_doc = {id: doc for id, doc in zip(all_ids['ids'], all_ids['documents'])}
        
        for cid, _ in sorted_hits:
            if cid in id_to_doc:
                docs.append(id_to_doc[cid])
        
        return docs

    async def extract_facts(self, context: str, question: str):
        """Parallel extraction from large context."""
        # Calculate adaptive chunk size
        available_tokens = self.context_window - self.overhead
        page_size = max(available_tokens * 4, 400)
        page_size = min(page_size, 1200) # Stay focused
        
        pages = [context[i:i+page_size] for i in range(0, len(context), page_size)]
        
        logger.info(f"MAP: Firing {len(pages)} extraction workers...")
        semaphore = asyncio.Semaphore(self.max_workers)
        
        async def _worker(chunk):
            async with semaphore:
                try:
                    payload = {
                        "model": self.config.get("model", "llama3.2:3b"),
                        "messages": [
                            {"role": "system", "content": f"""You are a Silicon-Based Intelligence. 
Task: SCAN context for "{question}".
Rules:
1. If found, output the fact inside brackets: [FACT: THE_ANSWER_HERE]
2. If NOT found, output: NOT_FOUND
3. NO reasoning. NO chat. NO thinking. Pure data.

Question: "{question}" """},
                            {"role": "user", "content": f"Context:\n{chunk}"}
                        ],
                        "temperature": 0.0,
                        "max_tokens": 200
                    }
                    
                    endpoint = f"{self.base_url.rstrip('/')}/chat/completions"
                    async with aiohttp.ClientSession() as session:
                        async with session.post(endpoint, json=payload, timeout=60) as resp:
                            if resp.status != 200:
                                logger.error(f"Worker API error {resp.status}: {await resp.text()}")
                                return None
                            res_json = await resp.json()
                            ans = res_json['choices'][0]['message']['content']
                            # Strip thinking
                            ans = re.sub(r'(?i)<think>.*?</think>', '', ans, flags=re.DOTALL).strip()
                            if "NOT_FOUND" in ans or len(ans) < 5:
                                return None
                            return ans
                except Exception as e:
                    logger.error(f"Worker Error: {e}")
                    return None

        results = await asyncio.gather(*[_worker(p) for p in pages])
        findings = [r for r in results if r]
        
        if not findings:
            return None
            
        return "\n".join(findings)

    def recall(self, query_text: str, n_results: int = 5):
        """Bridge to hybrid retrieval."""
        logger.info(f"Hybrid Recall for: {query_text[:50]}...")
        try:
            # Use run_coroutine_threadsafe or run depending on context
            # For simplicity in this threaded app, run() is often acceptable if not in a loop
            docs = asyncio.run(self.query(query_text, n_results))
            if not docs: return None
            
            context = "\n---\n".join(docs)
            
            # Parallel extraction if context is bulky
            if len(context) > 2000:
                facts = asyncio.run(self.extract_facts(context, query_text))
                if facts:
                    # Return extracted facts directly for high precision
                    extracted = re.findall(r'\[FACT:\s*(.*?)\]', facts)
                    if extracted:
                        return "\n".join(extracted)
            
            return context
        except Exception as e:
            logger.error(f"Recall error: {e}")
            return None

    def get_by_group(self, group_id: str):
        """Returns all memory chunks matching a specific group_id, sorted by chunk_index."""
        try:
            res = self.collection.get(
                where={"group_id": group_id},
                include=['documents', 'metadatas']
            )
            docs = res['documents']
            metas = res['metadatas']
            results = []
            for doc, meta in zip(docs, metas):
                results.append({"text": doc, "metadata": meta})
            
            # Sort by chunk_index
            results.sort(key=lambda x: x.get("metadata", {}).get("chunk_index", 0))
            return results
        except Exception as e:
            logger.error(f"Error fetching by group: {e}")
            return []

# Initialize Global System
_sys_instance = None
def get_system():
    global _sys_instance
    if _sys_instance is None:
        _sys_instance = HybridMemorySystem(load_config())
    return _sys_instance

def recall(query_text, n_results=5, similarity_threshold=0.0, max_chars=None):
    """Bridge to hybrid retrieval."""
    return get_system().recall(query_text, n_results)

def memorize(text, metadata=None):
    """Bridge to ChromaDB ingestion."""
    return get_system().add(text, metadata)

def recall_instructions(query_text, n_results=2):
    """Retrieve instructions using ChromaDB."""
    sys = get_system()
    res = sys.instruction_collection.query(
        query_texts=[query_text],
        n_results=n_results
    )
    docs = res['documents'][0] if res['documents'] else []
    return "\n\n".join(docs) if docs else None

def get_by_group(group_id):
    """Retrieve all chunks for a group."""
    return get_system().get_by_group(group_id)

def learn_instruction(text):
    """Add instruction to ChromaDB."""
    return get_system().add(text, {"type": "instruction"}, collection_name="instructions")

def get_stats():
    sys = get_system()
    return {
        "entries": sys.collection.count(),
        "instructions": sys.instruction_collection.count(),
        "provider": sys.provider,
        "model": sys.embed_model
    }

if __name__ == "__main__":
    print(get_stats())

import os
import json
import time
import logging
import numpy as np
import requests

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("memory")

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
MEMORY_STORAGE_FILE = os.path.join(BASE_DIR, "memory_vault.json")

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

class MemoryMaker:
    """Handles text-to-vector encoding via multiple providers."""
    def __init__(self, config):
        self.provider = config.get("embedding_provider", "local")
        self.model_name = config.get("embedding_model", "all-MiniLM-L6-v2")
        self.config = config
        self._local_model = None

    def encode(self, text):
        res = None
        if self.provider == "local":
            res = self._encode_local(text)
        elif self.provider in ["ollama", "openai"] or self.provider in self.config.get("providers", {}):
            res = self._encode_remote(text)
        
        # Timing optimization: wait 1s after heavy embedding to let system breathe before LLM
        if res is not None:
            time.sleep(1)
        return res

    def _encode_local(self, text):
        try:
            if self._local_model is None:
                from sentence_transformers import SentenceTransformer
                logger.info(f"Loading local embedding model: {self.model_name}")
                self._local_model = SentenceTransformer(self.model_name)
            return self._local_model.encode(text).tolist()
        except Exception as e:
            logger.error(f"Local encoding failed: {e}")
            return None

    def _encode_remote(self, text):
        provider_name = self.provider if self.provider in self.config.get("providers", {}) else self.config.get("provider")
        p_cfg = self.config.get("providers", {}).get(provider_name, {})
        
        url = p_cfg.get("base_url", "").rstrip("/")
        api_format = p_cfg.get("api_format", "openai")
        api_key = p_cfg.get("api_key", "")
        model = self.model_name

        for attempt in range(3):
            try:
                if api_format == "ollama":
                    resp = requests.post(f"{url}/api/embeddings", json={
                        "model": model,
                        "prompt": text
                    }, timeout=15)
                    return resp.json().get("embedding")
                else: # OpenAI format
                    headers = {"Authorization": f"Bearer {api_key}"}
                    # ROBUST PATH: If base_url already has /v1, don't add it again
                    endpoint = f"{url}/embeddings" if url.endswith("/v1") else f"{url}/v1/embeddings"
                    
                    resp = requests.post(endpoint, headers=headers, json={
                        "model": model,
                        "input": text
                    }, timeout=15)
                    
                    data = resp.json().get("data", [])
                    if data:
                        return data[0].get("embedding")
                    
                    error = resp.json().get("error", "")
                    if "No models loaded" in str(error) or "Loading" in str(error):
                        logger.warning(f"Embedding Model not ready (Attempt {attempt+1}/3). Waiting 5s...")
                        time.sleep(5)
                        continue
            except Exception as e:
                logger.error(f"Remote encoding attempt {attempt+1} failed: {e}")
                if attempt < 2: time.sleep(2)
        
        return None

# Initialize Global Components
config = load_config()
maker = MemoryMaker(config)

import threading
from contextlib import contextmanager

class VectorVault:
    def __init__(self, storage_path):
        self.storage_path = storage_path
        self.lock = threading.RLock()
        self.data = self._load()

    @contextmanager
    def _file_lock(self):
        """Simple cross-process file lock using a .lock file."""
        lock_path = self.storage_path + ".lock"
        start_time = time.time()
        timeout = 10 # 10 seconds
        
        while os.path.exists(lock_path):
            if time.time() - start_time > timeout:
                # Break stuck lock if older than 30s
                if time.time() - os.path.getmtime(lock_path) > 30:
                    try: os.remove(lock_path)
                    except: pass
                else:
                    raise Exception("Memory vault is locked by another process.")
            time.sleep(0.05)
            
        try:
            with open(lock_path, "w") as f:
                f.write(str(os.getpid()))
            yield
        finally:
            if os.path.exists(lock_path):
                try: os.remove(lock_path)
                except: pass

    def _load(self):
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return []
        return []

    def save(self):
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)

    def add(self, text, metadata=None):
        # 1. Encode outside the lock to keep lock time minimal
        vector = maker.encode(text)
        if vector is None:
            logger.error("Failed to generate embedding. Memory NOT saved.")
            return None
            
        with self.lock:
            with self._file_lock():
                # 2. Reload to get latest data from other processes/threads
                self.data = self._load()
                
                # 2b. Atomic Duplicate Check (check again after reload)
                for existing in self.data:
                    if existing.get("text") == text:
                        logger.info("Atomic check: Skipping duplicate entry.")
                        return existing["id"]

                # 3. Dimension Check
                if self.data and len(self.data[0]["vector"]) != len(vector):
                    logger.warning("Embedding dimension mismatch. Clearing vault.")
                    self.data = []

                entry = {
                    "id": f"mem_{int(time.time() * 1000)}",
                    "text": text,
                    "vector": vector,
                    "metadata": metadata or {},
                    "timestamp": time.time()
                }
                self.data.append(entry)
                self.save()
                return entry["id"]

    def query(self, query_text, n_results=1):
        if not self.data: return []
        
        query_vec = maker.encode(query_text)
        if query_vec is None: return []

        # Dimension Check for Query
        if len(self.data[0]["vector"]) != len(query_vec):
            logger.warning("Query dimension mismatch. Clearing incompatible vault.")
            self.data = []
            self.save()
            return []

        query_vec = np.array(query_vec)
        q_norm = np.linalg.norm(query_vec)
        if q_norm == 0: return []
        
        results = []
        for entry in self.data:
            entry_vec = np.array(entry["vector"])
            e_norm = np.linalg.norm(entry_vec)
            if e_norm == 0: continue
            
            # cosine similarity
            similarity = np.dot(query_vec, entry_vec) / (q_norm * e_norm)
            results.append({
                "entry": entry,
                "score": float(similarity)
            })
        
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:n_results]

vault = VectorVault(MEMORY_STORAGE_FILE)

def recall(query_text, n_results=1, similarity_threshold=0.5):
    logger.info(f"Recalling for: {query_text[:50]}...")
    matches = vault.query(query_text, n_results=n_results)
    if not matches: 
        logger.info("No matches found in vault.")
        return None
    best = matches[0]
    logger.info(f"Best match score: {best['score']:.4f}")
    if best["score"] < similarity_threshold:
        return None
    logger.info(f"💡 [Memory] Found solution (score: {best['score']:.2f})")
    return best["entry"]["text"]

def memorize(problem, solution, rating=5):
    if rating < 4: return
    text = f"Problem: {problem}\nSolution: {solution}"
    
    # Hard Duplicate Check: Don't re-embed what we already know
    for entry in vault.data:
        if entry.get("text") == text:
            logger.info("Skipping memorization — already exists in vault.")
            return entry["id"]

    return vault.add(text, {"rating": rating})

def get_stats():
    return f"Memory (Provider: {maker.provider}). Entries: {len(vault.data)}"

if __name__ == "__main__":
    print(get_stats())

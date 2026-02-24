import os
import sys
import time
import uuid
import logging

# Ensure project root is in path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

from src.core import memory

# Configure logging for the test
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("memory_stress_test")

def run_stress_test():
    logger.info("Starting Memory Stress Test...")
    
    # 1. Ingestion Phase
    num_chunks = 50
    chunk_size = 1000 # chars
    logger.info(f"Phase 1: Ingesting {num_chunks} chunks of noise data (total ~{num_chunks * chunk_size // 1024} KB)...")
    
    noise_data = "This is a noise entry with some random content to fill up the multi-vector database. " * 15
    
    start_ingest = time.perf_counter()
    for i in range(num_chunks):
        memory.memorize(f"[{i}] {noise_data}", metadata={"test_run": "stress_01", "index": i})
        if i % 10 == 0:
            logger.info(f"  Ingested {i}/{num_chunks}...")
    
    # 2. Insert the "Needle"
    needle_fact = "The secret password for the antigravity chamber is 'FLUFFY_PENGUIN_99'."
    memory.memorize(needle_fact, metadata={"test_run": "stress_01", "type": "needle"})
    logger.info("Needle inserted into memory.")
    
    ingest_time = time.perf_counter() - start_ingest
    logger.info(f"Ingestion complete in {ingest_time:.2f}s.")

    # 3. Hybrid Recall Test (Semantic + BM25)
    logger.info("Phase 2: Testing hybrid recall for the needle...")
    start_recall = time.perf_counter()
    result = memory.recall("What is the secret password for the antigravity chamber?")
    recall_time = time.perf_counter() - start_recall
    
    if "FLUFFY_PENGUIN" in str(result):
        logger.info(f"✅ SUCCESS: Needle found! Time: {recall_time:.2f}s")
    else:
        logger.error(f"❌ FAILURE: Needle not found. Result: {result}")

    # 4. Keyword Specific Test (BM25)
    logger.info("Phase 3: Testing keyword-specific recall (BM25 focus)...")
    start_kw = time.perf_counter()
    # Using a keyword that is unique to the noise data but specifically indexed
    result_kw = memory.recall("noise entry multi-vector")
    kw_time = time.perf_counter() - start_kw
    
    if result_kw:
        logger.info(f"✅ SUCCESS: Keyword match found. Time: {kw_time:.2f}s")
    else:
        logger.error("❌ FAILURE: Keyword match failed.")

    # 5. Parallel Extraction / Infinite Context Test
    logger.info("Phase 4: Testing Parallel Fact Extraction (Infinite Context)...")
    # This requires reaching the threshold (2000 chars) to trigger extraction
    large_context_query = "Summarize the noise data entries."
    start_para = time.perf_counter()
    para_result = memory.recall(large_context_query)
    para_time = time.perf_counter() - start_para
    
    logger.info(f"Parallel recall completed in {para_time:.2f}s.")
    logger.info(f"Result Preview: {str(para_result)[:200]}...")

    # Summary
    logger.info("════════════════════════════════════")
    logger.info("STRESS TEST SUMMARY")
    logger.info(f"Ingestion: {ingest_time:.2f}s ({num_chunks} chunks)")
    logger.info(f"Needle Recall: {recall_time:.2f}s")
    logger.info(f"Keyword Recall: {kw_time:.2f}s")
    logger.info(f"Parallel Recall: {para_time:.2f}s")
    logger.info("════════════════════════════════════")

if __name__ == "__main__":
    run_stress_test()
